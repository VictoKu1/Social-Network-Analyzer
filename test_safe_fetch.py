"""Guarded transport tests: synthetic DNS and an isolated local HTTP peer only."""
# Test names describe assertions; do_GET is prescribed by BaseHTTPRequestHandler.
# pylint: disable=missing-function-docstring,missing-class-docstring,invalid-name

import gzip
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch

import safe_fetch
from security_limits import SecurityError


PUBLIC_IP = "93.184.216.34"


def dns_answer(address=PUBLIC_IP):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 80))]


class ProfilePeer(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):  # pylint: disable=too-many-branches
        self.server.seen.append((self.path, dict(self.headers)))
        mode = self.path.split("?", 1)[0]
        if mode == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1/private")
            self.end_headers()
            return
        if mode == "/safe-redirect":
            self.send_response(302)
            self.send_header("Location", "/profile")
            self.end_headers()
            return
        if mode == "/private-dns-redirect":
            self.send_response(302)
            self.send_header("Location", "http://sub.github.com/profile")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        body = b"<h1>Public profile</h1><div class='bio'>A normal bio.</div>"
        if mode == "/oversize":
            body = b"x" * 4097
        if mode == "/gzip-bomb":
            body = gzip.compress(b"x" * 100000)
            self.send_header("Content-Encoding", "gzip")
        if mode == "/gzip":
            body = gzip.compress(body)
            self.send_header("Content-Encoding", "gzip")
        if mode == "/chunked":
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                self.wfile.write(b"1001\r\n" + b"x" * 4097 + b"\r\n0\r\n\r\n")
            except OSError:
                pass
            return
        if mode == "/slow":
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.03)
            except OSError:
                pass
            return
        if mode != "/oversize":
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass


class GuardedHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ProfilePeer)
        cls.server.daemon_threads = True
        cls.server.seen = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.seen = []

    def fetch(self, path, **kwargs):
        port = self.server.server_port

        def literal_connect(connection):
            # Replace only the destination with our owned peer; DNS policy and
            # HTTP parsing, redirects, byte caps, deadlines and cleanup stay real.
            connection.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.sock.settimeout(1)
            connection.transport_socket = connection.sock
            connection.sock.connect(("127.0.0.1", port))

        with patch("safe_fetch._PinnedConnection.connect", literal_connect), \
                patch("safe_fetch.socket.getaddrinfo", side_effect=lambda host, port, **_kw: (
                    dns_answer("127.0.0.1") if host == "sub.github.com" else dns_answer())), \
                patch("safe_fetch.MAX_RESPONSE_BYTES", 4096):
            return safe_fetch.fetch_public_url("http://github.com" + path, **kwargs)

    def test_public_html_and_gzip_preserve_legitimate_content(self):
        for path in ("/profile", "/gzip", "/safe-redirect"):
            with self.subTest(path=path):
                self.assertIn("A normal bio", self.fetch(path).text)

    def test_private_redirect_opens_no_second_destination(self):
        for path in ("/redirect", "/private-dns-redirect"):
            self.server.seen = []
            with self.subTest(path=path), self.assertRaises(SecurityError):
                self.fetch(path)
            self.assertEqual(len(self.server.seen), 1)

    def test_oversize_chunked_and_compressed_bodies_are_rejected(self):
        for path in ("/oversize", "/chunked", "/gzip-bomb"):
            with self.subTest(path=path), self.assertRaises(SecurityError) as caught:
                self.fetch(path)
            self.assertEqual(caught.exception.code, "response_too_large")

    def test_continuous_response_has_total_deadline(self):
        start = time.monotonic()
        with patch("safe_fetch.FETCH_DEADLINE_SECONDS", 0.2), self.assertRaises(SecurityError) as caught:
            self.fetch("/slow")
        self.assertEqual(caught.exception.code, "fetch_timeout")
        self.assertLess(time.monotonic() - start, 1.5)

    def test_public_dns_mixed_private_ipv6_and_aliases_fail_closed(self):
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "::ffff:8.8.8.8"):
            with self.subTest(address=address), \
                    patch("safe_fetch.socket.getaddrinfo", return_value=dns_answer() + dns_answer(address)), \
                    patch("safe_fetch._PinnedConnection") as connection, \
                    self.assertRaises(SecurityError):
                safe_fetch.fetch_public_url("https://github.com/profile")
            connection.assert_not_called()

    def test_connection_pins_checked_ip_with_original_tls_hostname(self):
        sock = MagicMock()
        context = MagicMock()
        with patch("safe_fetch.socket.socket", return_value=sock), \
                patch("safe_fetch.socket.getaddrinfo") as resolver, \
                patch("safe_fetch.ssl.create_default_context", return_value=context):
            connection = safe_fetch._PinnedConnection("github.com", 443, [(socket.AF_INET, PUBLIC_IP)],
                                                     True, time.monotonic() + 10)
            connection.connect()
        sock.connect.assert_called_once_with((PUBLIC_IP, 443))
        resolver.assert_not_called()
        context.wrap_socket.assert_called_once_with(sock, server_hostname="github.com", do_handshake_on_connect=False)
        context.wrap_socket.return_value.do_handshake.assert_called_once()

    def test_unreachable_first_public_address_uses_next_checked_address(self):
        first, second = MagicMock(), MagicMock()
        first.connect.side_effect = OSError("Synthetic unreachable first address")
        response = MagicMock(status=200)
        response.getheader.side_effect = lambda name, default=None: {
            "Content-Type": "text/html", "Content-Length": "7",
        }.get(name, default)
        response.headers.get_content_charset.return_value = "utf-8"
        response.read1.side_effect = [b"profile", b""]
        with patch("safe_fetch.socket.getaddrinfo", return_value=dns_answer() + dns_answer("8.8.8.8")), \
                patch("safe_fetch.socket.socket", side_effect=[first, second]), \
                patch("safe_fetch._PinnedConnection.getresponse", return_value=response):
            result = safe_fetch.fetch_public_url("http://github.com/profile")
        self.assertEqual(result.text, "profile")
        first.connect.assert_called_once_with((PUBLIC_IP, 80))
        second.connect.assert_called_once_with(("8.8.8.8", 80))
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_api_token_never_follows_other_hosts(self):
        with patch("safe_fetch._PinnedConnection") as connection, self.assertRaises(SecurityError):
            safe_fetch.fetch_public_url("https://github.com/user", token="synthetic")
        connection.assert_not_called()

    def test_scrape_does_not_inherit_ambient_auth_or_proxy(self):
        with patch.dict("os.environ", {"HTTP_PROXY": "http://127.0.0.1:1", "NETRC": "synthetic-unused"}):
            self.fetch("/profile")
        headers = self.server.seen[0][1]
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)
        self.assertEqual(headers["Host"], "github.com")


if __name__ == "__main__":
    unittest.main()
