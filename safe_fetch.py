"""Public-destination HTTP reads with pinned DNS, finite bytes and a hard deadline.

This transport is deliberately separate from operator-configured inference endpoints.
It does not use ambient proxies, netrc, cookies or shared authenticated sessions.
"""

import http.client
import ipaddress
import json
import queue
import re
import socket
import ssl
import threading
import time
import zlib
from dataclasses import dataclass
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from security_limits import MAX_URL_LENGTH, SecurityError

SOCIAL_DOMAINS = {
    "facebook.com": "Facebook", "instagram.com": "Instagram", "twitter.com": "Twitter",
    "x.com": "X", "threads.net": "Threads", "linkedin.com": "LinkedIn",
    "pinterest.com": "Pinterest", "snapchat.com": "Snapchat", "tiktok.com": "TikTok",
    "youtube.com": "YouTube", "reddit.com": "Reddit", "tumblr.com": "Tumblr",
    "github.com": "GitHub", "stackoverflow.com": "Stack Overflow", "medium.com": "Medium",
    "wordpress.com": "WordPress", "blogger.com": "Blogger", "twitch.tv": "Twitch",
    "soundcloud.com": "SoundCloud", "spotify.com": "Spotify", "apple.com": "Apple",
    "amazon.com": "Amazon", "ebay.com": "eBay", "etsy.com": "Etsy", "patreon.com": "Patreon",
}
MAX_RESPONSE_BYTES = 1024 * 1024
FETCH_DEADLINE_SECONDS = 15.0
MAX_REDIRECTS = 3
_DNS_SLOTS = threading.BoundedSemaphore(2)


def parse_profile_url(url):
    """Pure classification shared by UI validation, analysis and HTTP consumers."""
    if (not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH
            or re.search(r"[\x00-\x20\x7f\\]", url)):
        raise SecurityError("invalid_url", "Enter a complete supported profile URL without spaces or credentials.")
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or parts.username is not None or parts.password is not None:
            raise ValueError("Invalid scheme or authority")
        host = (parts.hostname or "").encode("idna").decode("ascii").lower()
        if not host or host.endswith(".."):
            raise ValueError("Invalid hostname")
        host = host[:-1] if host.endswith(".") else host
        if not re.fullmatch(r"[a-z0-9.-]+", host):
            raise ValueError("Invalid hostname")
        port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
        if port != (443 if parts.scheme == "https" else 80):
            raise ValueError("Unexpected port")
        platform = next((name for domain, name in SOCIAL_DOMAINS.items()
                         if host == domain or host.endswith("." + domain)), None)
        if platform is None:
            raise ValueError("Unsupported hostname")
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        query = quote(parts.query, safe="/%?:@!$&'()*+,;=-._~")
        return urlunsplit((parts.scheme, host, path, query, "")), host, port, platform
    except (ValueError, UnicodeError) as exc:
        raise SecurityError("invalid_url",
                            "Use a supported public profile URL on its standard HTTP or HTTPS port.") from exc


def _public_address(address):
    ip = ipaddress.ip_address(address)
    return (ip.is_global and not ip.is_multicast and not ip.is_reserved
            and not ip.is_unspecified and not ip.is_loopback
            and not getattr(ip, "ipv4_mapped", None)
            and not getattr(ip, "sixtofour", None) and not getattr(ip, "teredo", None))


def _resolve_public(host, port, deadline):
    """Bound resolver workers; a timed-out OS lookup cannot grow an unbounded pool."""
    # The resolver thread releases this reservation, including after caller timeout.
    if not _DNS_SLOTS.acquire(blocking=False):  # pylint: disable=consider-using-with
        raise SecurityError("fetch_busy", "Profile lookup is busy. Try again shortly.", 503)
    result = queue.Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError as exc:
            result.put(exc)
        finally:
            _DNS_SLOTS.release()

    threading.Thread(target=resolve, daemon=True).start()
    try:
        answers = result.get(timeout=max(0.001, min(3.0, deadline - time.monotonic())))
    except queue.Empty as exc:
        raise SecurityError("fetch_timeout", "Profile lookup timed out.", 504) from exc
    if isinstance(answers, Exception):
        raise SecurityError("fetch_failed", "The profile hostname could not be resolved.", 502) from answers
    if not answers or any(not _public_address(item[4][0]) for item in answers):
        raise SecurityError("unsafe_destination", "Profile URLs must resolve only to public Internet addresses.")
    # Try a bounded set of distinct, already checked addresses (e.g. IPv6 then IPv4).
    return list(dict.fromkeys((item[0], item[4][0]) for item in answers))[:4]


class _PinnedConnection(http.client.HTTPConnection):
    """Dial a validated literal address, preserving the original Host and TLS name."""

    def __init__(self, host, port, addresses, secure, deadline):
        super().__init__(host, port, timeout=max(0.001, deadline - time.monotonic()))
        self.addresses, self.secure, self.deadline = addresses, secure, deadline
        self.transport_socket = None
        self.expired = threading.Event()

    def abort(self):
        """Interrupt an active socket when the total download deadline expires."""
        self.expired.set()
        active_socket = self.transport_socket
        if active_socket is not None:
            try:
                active_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            active_socket.close()

    def connect(self):
        for index, (family, address) in enumerate(self.addresses):
            if self.expired.is_set() or time.monotonic() >= self.deadline:
                raise TimeoutError("Deadline exceeded")
            self.sock = socket.socket(family, socket.SOCK_STREAM)
            self.transport_socket = self.sock
            self.sock.settimeout(max(0.001, min(5.0, self.deadline - time.monotonic())))
            try:
                if self.expired.is_set():
                    raise TimeoutError("Deadline exceeded")
                # No second hostname lookup occurs after address validation.
                self.sock.connect((address, self.port))
                if self.secure:
                    self.sock = ssl.create_default_context().wrap_socket(
                        self.sock, server_hostname=self.host, do_handshake_on_connect=False)
                    self.transport_socket = self.sock
                    if self.expired.is_set():
                        raise TimeoutError("Deadline exceeded")
                    self.sock.do_handshake()
                return
            except OSError:
                self.sock.close()
                self.sock = self.transport_socket = None
                if self.expired.is_set() or index == len(self.addresses) - 1:
                    raise


@dataclass
class FetchedResponse:
    """A detached, bounded response that cannot perform more network reads."""
    status_code: int
    body: bytes
    charset: str = "utf-8"

    @property
    def text(self):
        """Decode profile text with a safe fallback for unknown charsets."""
        try:
            return self.body.decode(self.charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")

    def json(self):
        """Decode JSON without exposing upstream content in errors."""
        try:
            return json.loads(self.body)
        except (ValueError, UnicodeError) as exc:
            raise SecurityError("invalid_response", "The profile service returned invalid JSON.", 502) from exc


def _read_body(response, deadline, max_bytes):
    length = response.getheader("Content-Length")
    if length is not None and (not length.isdecimal() or int(length) > max_bytes):
        raise SecurityError("response_too_large", "The profile response exceeds the download limit.", 502)
    encoding = response.getheader("Content-Encoding", "identity").lower().strip()
    if encoding not in ("identity", "gzip"):
        raise SecurityError("invalid_response", "The profile uses an unsupported response encoding.", 502)
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    body = bytearray()
    wire_size = 0
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Deadline exceeded")
        chunk = response.read1(min(65536, max_bytes - wire_size + 1))
        if not chunk:
            break
        wire_size += len(chunk)
        if wire_size > max_bytes:
            raise SecurityError("response_too_large", "The profile response exceeds the download limit.", 502)
        body.extend(decoder.decompress(chunk, max_bytes - len(body) + 1) if decoder else chunk)
        if len(body) > max_bytes or (decoder and decoder.unconsumed_tail):
            raise SecurityError("response_too_large", "The decoded profile exceeds the download limit.", 502)
    if decoder and (not decoder.eof or decoder.unused_data):
        raise SecurityError("invalid_response", "The profile returned an invalid compressed response.", 502)
    return bytes(body)


# Keep redirect policy and connection cleanup in the same auditable control flow.
def fetch_public_url(url, *, token=None, json_response=False):  # pylint: disable=too-many-locals,too-many-branches
    """Fetch only approved public hosts, with the same checks on every redirect."""
    deadline = time.monotonic() + FETCH_DEADLINE_SECONDS
    for hop in range(MAX_REDIRECTS + 1):
        normalized, host, port, _ = parse_profile_url(url)
        secure = normalized.startswith("https:")
        if token and (host != "api.github.com" or not secure):
            raise SecurityError("unsafe_destination", "API credentials require the approved HTTPS API host.")
        addresses = _resolve_public(host, port, deadline)
        connection = _PinnedConnection(host, port, addresses, secure, deadline)
        timer = threading.Timer(max(0.001, deadline - time.monotonic()), connection.abort)
        timer.daemon = True
        timer.start()
        response = None
        try:
            parts = urlsplit(normalized)
            target = parts.path + ("?" + parts.query if parts.query else "")
            headers = {"User-Agent": "SocialNetworkAnalyzer/1.0", "Accept-Encoding": "gzip, identity",
                       "Accept": "application/json" if json_response else "text/html,application/xhtml+xml"}
            if token:
                headers["Authorization"] = "Bearer " + token
            connection.request("GET", target, headers=headers)
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location or hop == MAX_REDIRECTS:
                    raise SecurityError("invalid_redirect", "The profile redirected too many times.", 502)
                url = urljoin(normalized, location)
                continue
            if response.status != 200:
                return FetchedResponse(response.status, b"")
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            allowed = ("application/json",) if json_response else ("text/html", "application/xhtml+xml")
            if content_type not in allowed:
                raise SecurityError("invalid_response", "The profile returned an unsupported content type.", 502)
            body = _read_body(response, deadline, MAX_RESPONSE_BYTES)
            if connection.expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("Deadline exceeded")
            return FetchedResponse(200, body, response.headers.get_content_charset() or "utf-8")
        except (TimeoutError, socket.timeout) as exc:
            raise SecurityError("fetch_timeout", "Profile retrieval exceeded its time limit.", 504) from exc
        except (OSError, http.client.HTTPException, zlib.error) as exc:
            if connection.expired.is_set():
                raise SecurityError("fetch_timeout", "Profile retrieval exceeded its time limit.", 504) from exc
            raise SecurityError("fetch_failed", "The profile could not be retrieved safely.", 502) from exc
        finally:
            timer.cancel()
            if response is not None:
                response.close()
            connection.close()
    raise SecurityError("invalid_redirect", "The profile redirected too many times.", 502)
