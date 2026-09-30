"""ASGI middleware: request body cap, request id + access log, security headers."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from raven.api.auth import client_ip
from raven.api.ops import METRICS
from raven.api.settings import Settings

_access = logging.getLogger("raven.access")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_API_CSP = "default-src 'none'; frame-ancestors 'none'"
_HTML_PATHS = ("/docs", "/redoc", "/missions", "/static")


def _safe(text: str, limit: int = 200) -> str:
    """Escape control characters so a crafted path cannot forge log lines."""
    return text.encode("unicode_escape").decode("ascii")[:limit]


_SURROGATES = re.compile("[\ud800-\udfff]")


def _has_surrogate(value) -> bool:
    if isinstance(value, str):
        return bool(_SURROGATES.search(value))
    if isinstance(value, dict):
        return any(_has_surrogate(k) or _has_surrogate(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_has_surrogate(v) for v in value)
    return False


class BodyLimitMiddleware:
    """Reject unusable request bodies before any endpoint sees them.

    * A declared Content-Length above the cap is refused with 413. A body sent without
      Content-Length (chunked) is refused with 411, so the cap cannot be bypassed.
    * JSON that carries lone UTF-16 surrogates (valid JSON escapes, but not encodable
      as UTF-8) is refused with 422: they would otherwise crash response or storage
      encoding deep inside an endpoint.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        headers = {k: v for k, v in scope["headers"]}
        length = headers.get(b"content-length")
        status = code = None
        if length is None:
            if b"transfer-encoding" in headers:
                status, code, msg = 411, "length_required", "Content-Length is required."
        else:
            try:
                too_big = int(length) > self.max_bytes
            except ValueError:
                status, code, msg = 400, "bad_request", "Invalid Content-Length."
            else:
                if too_big:
                    status, code, msg = 413, "payload_too_large", f"Request body exceeds {self.max_bytes} bytes."
        if status is None and headers.get(b"content-type", b"").startswith(b"application/json"):
            chunks: list[bytes] = []
            more = True
            while more:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunks.append(message.get("body", b""))
                more = message.get("more_body", False)
            raw = b"".join(chunks)
            try:
                bad = _has_surrogate(json.loads(raw))
            except (ValueError, RecursionError):
                bad = False  # malformed JSON: the endpoint reports it in its own envelope
            if bad:
                status, code, msg = 422, "validation_error", "Request contains invalid Unicode characters."
            else:
                replayed = False

                async def replay() -> Message:
                    nonlocal replayed
                    if not replayed:
                        replayed = True
                        return {"type": "http.request", "body": raw, "more_body": False}
                    return await receive()

                await self.app(scope, replay, send)
                return
        if status is None:
            await self.app(scope, receive, send)
            return
        METRICS.inc("rejected_body")
        body = json.dumps({"error": msg, "code": code}).encode()
        await send({"type": "http.response.start", "status": status, "headers": [
            (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
            (b"connection", b"close")]})
        await send({"type": "http.response.body", "body": body})


def install_request_context(app, settings: Settings) -> None:
    """Request id, access log, counters and security headers (outermost middleware)."""

    @app.middleware("http")
    async def request_context(request, call_next):
        supplied = request.headers.get("x-request-id", "")
        rid = supplied if _REQUEST_ID.match(supplied) else uuid.uuid4().hex
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            METRICS.inc("responses_5xx")
            _access.error("rid=%s method=%s path=%s status=500 ms=%.1f ip=%s", rid, request.method,
                          _safe(request.url.path), (time.perf_counter() - start) * 1000, client_ip(request))
            raise
        status = response.status_code
        METRICS.inc("requests_total")
        METRICS.inc(f"responses_{status // 100}xx")
        if status == 429:
            METRICS.inc("rate_limited")
        response.headers["X-Request-ID"] = rid
        _apply_security_headers(request.url.path, response, settings)
        level = logging.WARNING if status >= 500 else logging.INFO
        _access.log(level, "rid=%s method=%s path=%s status=%d ms=%.1f ip=%s", rid, request.method,
                    _safe(request.url.path), status, (time.perf_counter() - start) * 1000, client_ip(request))
        return response


def _apply_security_headers(path: str, response, settings: Settings) -> None:
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    h["Cross-Origin-Resource-Policy"] = "same-origin"
    h["X-Frame-Options"] = "DENY"  # legacy twin of frame-ancestors 'none'
    if settings.is_production:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path == "/":
        h["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        h["Cache-Control"] = "no-store, max-age=0"
    elif path.startswith("/missions"):
        h["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        h["Cache-Control"] = "no-cache"
    elif not path.startswith(_HTML_PATHS):
        # Every API response: no framing/scripting context, never cached.
        h.setdefault("Content-Security-Policy", _API_CSP)
        h.setdefault("Cache-Control", "no-store")
