"""Local-only defaults, optional shared credentials, and atomic work admission."""

from collections import deque
from contextlib import contextmanager
import hmac
import ipaddress
import os
import threading
import time
from urllib.parse import urlsplit

from security_limits import SecurityError


def _loopback(value):
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def shared_access_enabled():
    """Whether the operator has enabled credential-protected shared access."""
    return bool(os.getenv("APP_ACCESS_TOKEN", "").strip())


def authorize_request(request):
    """No forwarded-header trust: host, peer and origin each have their own check."""
    token = os.getenv("APP_ACCESS_TOKEN", "").strip()
    try:
        host = urlsplit(request.host_url).hostname
        allowed = {"localhost", "127.0.0.1", "::1"}
        if token:
            configured = os.getenv("APP_ALLOWED_HOSTS", "").split(",")
            allowed.update(item.strip().lower() for item in configured if item.strip())
        if host not in allowed:
            raise ValueError("Untrusted host")
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            raise ValueError("Untrusted origin")
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise ValueError("Cross-site request")
    except ValueError as exc:
        raise SecurityError("access_denied", "This host or request origin is not allowed.", 403) from exc
    local = _loopback(request.remote_addr or "") and host in {"localhost", "127.0.0.1", "::1"}
    if not token:
        if not local or any(name.lower() == "forwarded" or name.lower().startswith("x-forwarded-")
                            for name in request.headers.keys()):
            raise SecurityError("access_denied",
                                "Remote access is disabled. Configure authenticated shared access first.", 403)
        return
    if len(token) < 32:
        raise SecurityError("access_unconfigured", "APP_ACCESS_TOKEN must contain at least 32 characters.", 503)
    if not local and not request.is_secure:
        raise SecurityError("https_required", "Shared access requires HTTPS.", 403)
    auth = request.authorization
    if (auth is None or auth.type.lower() != "basic" or auth.username != "operator"
            or not hmac.compare_digest((auth.password or "").encode(), token.encode())):
        raise SecurityError("authentication_required", "Sign in with the operator credential.", 401)


class WorkAdmission:
    """Single-process quota and concurrency budget for one operator account."""

    def __init__(self, per_minute=30, concurrent=2):
        self.per_minute = per_minute
        self.concurrent = concurrent
        self.calls = deque()
        self.active = 0
        self.lock = threading.Lock()

    @contextmanager
    def acquire(self):
        """Reserve a work slot atomically and release it on success or failure."""
        with self.lock:
            now = time.monotonic()
            while self.calls and self.calls[0] <= now - 60:
                self.calls.popleft()
            if self.active >= self.concurrent or len(self.calls) >= self.per_minute:
                raise SecurityError("work_limit", "The analysis limit was reached. Try again shortly.", 429)
            self.calls.append(now)
            self.active += 1
        try:
            yield
        finally:
            with self.lock:
                self.active -= 1
