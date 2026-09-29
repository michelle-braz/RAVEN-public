from __future__ import annotations

import logging
import os
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from raven import __version__
from raven.api import auth as _auth
from raven.api.auth import (
    auth_attempts_blocked,
    client_ip,
    configured_key_tier,
    is_operator_key,
    key_matches,
    record_auth_failure,
    require_api_key,
)
from raven.api.beta.router import router as beta_router
from raven.api.beta_keys import BETA_REGISTRY, is_valid_beta_key
from raven.api.middleware import BodyLimitMiddleware, _safe, install_request_context
from raven.api.ops import METRICS
from raven.api.settings import ConfigError, Settings, load_settings
from raven.api.v1.router import router as v1_router
from raven.missions import MISSIONS_WEB_DIR
from raven.sentinel.core.engine import evaluate as sentinel_evaluate
from raven.sentinel.observability import BackpressurePolicy, EventBuffer
from raven.sentinel.pipeline.action_layer.notifier import ActionDispatcher, LogChannel
from raven.sentinel.pipeline.app import IngestionPipeline, SignalWindow
from raven.sentinel.pipeline.data_layer.schemas import RawEvent, Severity, SourceType
from raven.sentinel.pipeline.intelligence_layer.engine import build_engine

_log = logging.getLogger(__name__)
PRODUCT_NAME = "RAVEN"

# ── Error code mapping ────────────────────────────────────────────────────────

_HTTP_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    411: "length_required",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limit_exceeded",
    500: "internal_server_error",
    503: "service_unavailable",
}

_DESCRIPTION = (
    f"## {PRODUCT_NAME} Incident Intelligence API\n\n"
    "Two independent scoring engines are available:\n\n"
    "| Endpoint | Engine | Score range | Severity bands |\n"
    "|---|---|---|---|\n"
    "| `POST /evaluate` | Rule-based (legacy) | Integer **0 – 100** | LOW / MEDIUM / HIGH |\n"
    "| `POST /v1/analyze` | Sentinel 4-layer pipeline | Float **0.0 – 1.0** | LOW / MEDIUM / HIGH / CRITICAL |\n\n"
    "All protected endpoints require the `X-API-Key` header.\n\n"
    "All error responses share the envelope `{\"error\": \"...\", \"code\": \"...\"}`."
)

# ── Access gate ───────────────────────────────────────────────────────────────

_PUBLIC_PATHS: frozenset[str] = frozenset({
    "/", "/openapi.json", "/health", "/ready", "/status", "/favicon.ico",
})
_PUBLIC_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/static", "/missions")
# Readable only with the operator key (RAVEN_API_KEY), never with customer keys.
_OPERATOR_PATHS: frozenset[str] = frozenset({"/ops/metrics", "/beta/business-proof"})
_BETA_MASTER: str | None = os.getenv("RAVEN_API_KEY") or None


def _err(status: int, code: str, message: str, **extra: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": code, "code": code, "message": message},
        headers=extra.get("headers"),
    )


def _startup_problems(settings: Settings) -> list[str]:
    beta_keys = frozenset(k for k, v in BETA_REGISTRY.items() if v["status"] == "active")
    master = _auth._master_key
    others = (_auth.FREE_KEYS | _auth.PRO_KEYS | beta_keys) - ({master} if master else set())
    return settings.validate(master_key=master, other_keys=others)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Validate configuration, then create shared pipeline state once."""
        problems = _startup_problems(settings)
        if problems:
            for problem in problems:
                _log.critical("unsafe production configuration: %s", problem)
            raise ConfigError("Refusing to start: " + " ".join(problems))
        app.state.settings = settings
        app.state.started_at = time.monotonic()
        try:
            policy = BackpressurePolicy[os.getenv("SENTINEL_BUFFER_POLICY", "DROP_NEWEST").upper()]
            window = SignalWindow(
                maxlen=int(os.getenv("SENTINEL_WINDOW_MAXLEN", "5000")),
                ttl_seconds=float(os.getenv("SENTINEL_WINDOW_TTL", "3600")),
            )
            buffer: EventBuffer[RawEvent] = EventBuffer(
                maxsize=int(os.getenv("SENTINEL_BUFFER_MAXSIZE", "256"))
            )
        except (KeyError, ValueError) as exc:
            raise ConfigError("Invalid SENTINEL_* pipeline setting.") from exc
        app.state.pipeline = IngestionPipeline(
            engine=build_engine(),
            dispatcher=ActionDispatcher([LogChannel(min_severity=Severity.LOW)]),
            window=window,
            buf=buffer,
            policy=policy,
        )
        _log.info("raven started version=%s environment=%s", __version__, settings.environment)
        yield

    app = FastAPI(
        title="RAVEN Incident Intelligence API",
        version=__version__,
        description=_DESCRIPTION,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.include_router(v1_router)
    app.include_router(beta_router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    # Cyber Missions: study front-end built on RAVEN's investigation structure
    # (evidence → hypothesis → next step). Static and public; no API key needed.
    app.mount("/missions", StaticFiles(directory=MISSIONS_WEB_DIR, html=True), name="missions")

    # Middleware order (innermost first): access gate → body cap → CORS → request context.
    # CORS wraps the gate so 401/403/413 responses still carry correct CORS headers.

    @app.middleware("http")
    async def access_gate(request: Request, call_next):
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or path in _PUBLIC_PATHS
            or any(path.startswith(p) for p in _PUBLIC_PREFIXES)
        ):
            return await call_next(request)
        ip = client_ip(request)
        if auth_attempts_blocked(ip):
            return _err(429, "rate_limit_exceeded", "Too many failed authentication attempts. Retry later.",
                        headers={"Retry-After": "60"})
        api_key = request.headers.get("x-api-key")  # Starlette normalises headers to lowercase
        if not api_key:
            return _err(401, "missing_api_key", "API key required (beta access)")
        if not (
            (_BETA_MASTER and key_matches(api_key, [_BETA_MASTER]))
            or is_valid_beta_key(api_key)
            or configured_key_tier(api_key) is not None
        ):
            record_auth_failure(ip)
            METRICS.inc("auth_failures")
            return _err(403, "invalid_api_key", "Invalid or inactive beta key")
        if path in _OPERATOR_PATHS and not is_operator_key(api_key):
            return _err(403, "forbidden", "Operator key required.")
        return await call_next(request)

    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        allow_credentials=False,
    )
    install_request_context(app, settings)

    # ── Exception handlers — consistent {"error": ..., "code": ...} envelope ──

    @app.exception_handler(404)
    async def _not_found(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "Not found.", "code": "not_found"})

    @app.exception_handler(429)
    async def _rate_limited(_: Request, exc: Exception) -> JSONResponse:
        detail = getattr(exc, "detail", "Too many requests.")
        return JSONResponse(
            status_code=429,
            content={
                "error": detail,
                "code": "rate_limit_exceeded",
                "hint": "Back off and retry with exponential delay.",
            },
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "code": _HTTP_CODES.get(exc.status_code, "error")},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "Request validation failed.", "code": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
        # Log the call stack and exception type only: exception messages can echo
        # request content, which must not reach the logs.
        _log.error(
            "Unhandled %s request_id=%s method=%s path=%s\n%s",
            type(exc).__name__,
            request_id,
            request.method,
            _safe(request.url.path),
            "".join(traceback.format_tb(exc.__traceback__)),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "An unexpected error occurred. Please contact support.",
                "code": "internal_server_error",
                "request_id": request_id,
            },
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )

    # ── Endpoints ─────────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def landing() -> HTMLResponse:
        html = Path(__file__).parent / "landing.html"
        if html.exists():
            return HTMLResponse(content=html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<html><body><h1>Service unavailable</h1></body></html>")

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "raven-incident-api", "version": __version__}

    @app.get("/ready", tags=["ops"], summary="Readiness probe (storage writable, pipeline up)")
    async def ready(request: Request) -> JSONResponse:
        data_dir = settings.data_dir
        checks = {
            "pipeline": hasattr(request.app.state, "pipeline"),
            "data_dir_writable": data_dir.is_dir() and os.access(data_dir, os.W_OK),
        }
        ok = all(checks.values())
        return JSONResponse(
            status_code=200 if ok else 503,
            content={"status": "ready" if ok else "not_ready", "checks": checks},
        )

    @app.get(
        "/status",
        tags=["ops"],
        summary="Service status",
        description="Returns service version and uptime. No auth required. Suitable for load-balancer probes.",
    )
    async def status(request: Request) -> dict[str, object]:
        return {
            "service": "raven-incident-api",
            "version": request.app.version,
            "uptime_seconds": int(time.monotonic() - getattr(request.app.state, "started_at", time.monotonic())),
        }

    @app.get(
        "/ops/metrics",
        tags=["ops"],
        summary="Operational counters (operator key only)",
        description=(
            "In-process counters since start: requests, 4xx/5xx, rate-limited and failed-auth "
            "requests, analyses and storage failures, plus pipeline buffer state."
        ),
    )
    async def ops_metrics(request: Request) -> dict[str, Any]:
        return {
            "uptime_seconds": int(time.monotonic() - getattr(request.app.state, "started_at", time.monotonic())),
            "counters": METRICS.snapshot(),
            "pipeline_buffer": request.app.state.pipeline.buffer_metrics(),
        }

    @app.post(
        "/evaluate",
        summary="Score an event (rule-based legacy engine)",
        description=(
            "Rule-based scoring engine. Returns an **integer** risk score (0 – 100) "
            "and a level band.\n\n"
            "**Score thresholds:** LOW < 40 · MEDIUM 40–69 · HIGH ≥ 70\n\n"
            "**Scoring rules:**\n"
            "- `action=login_failed` → +30\n"
            "- `attempts ≥ 3` → +40\n"
            "- Known suspicious IP → +10\n\n"
            "For pipeline-based multi-factor scoring with float scores (0.0 – 1.0), "
            "four severity bands, and recurrence detection, use `POST /v1/analyze`."
        ),
        tags=["evaluate"],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string", "description": "Event description."},
                                "action": {"type": "string", "description": "Event action (e.g. login_failed, page_view)."},
                                "attempts": {"type": "integer", "description": "Number of attempts.", "default": 0},
                                "ip": {"type": "string", "description": "Source IP address."},
                                "user_id": {"type": "string", "description": "User identifier."},
                                "source": {"type": "string", "description": "Signal origin.", "default": "unknown"},
                            },
                        },
                        "examples": {
                            "high_risk": {
                                "summary": "High-risk login attempt (score 80, HIGH)",
                                "value": {
                                    "message": "failed login from suspicious IP",
                                    "action": "login_failed",
                                    "attempts": 5,
                                    "ip": "192.168.1.1",
                                    "user_id": "user_001",
                                    "source": "application",
                                },
                            },
                            "low_risk": {
                                "summary": "Low-risk page view (score 0, LOW)",
                                "value": {
                                    "message": "user viewed dashboard",
                                    "action": "page_view",
                                    "attempts": 0,
                                    "ip": "8.8.8.8",
                                    "user_id": "user_002",
                                    "source": "application",
                                },
                            },
                        },
                    }
                },
            }
        },
    )
    async def evaluate_event(
        request: Request,
        auth: dict[str, str] = Depends(require_api_key),
    ) -> dict[str, Any]:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body.")
        if not isinstance(body, dict):
            raise HTTPException(status_code=422, detail="Body must be a JSON object.")

        # Validate source; default to UNKNOWN for backward compatibility.
        raw_source = body.get("source", SourceType.UNKNOWN.value)
        try:
            source_value = SourceType(raw_source).value
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid source. Must be one of: {[s.value for s in SourceType]}",
            )
        attempts = body.get("attempts", 0)
        if isinstance(attempts, bool) or not isinstance(attempts, int) or not 0 <= attempts <= 1_000_000:
            raise HTTPException(status_code=422, detail="attempts must be an integer between 0 and 1000000.")
        for field, limit in (("message", 8192), ("action", 256), ("ip", 64)):
            value = body.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > limit):
                raise HTTPException(status_code=422, detail=f"{field} must be a string up to {limit} characters.")
        user_id = body.get("user_id")
        if user_id is not None and (
            isinstance(user_id, bool) or not isinstance(user_id, (str, int)) or len(str(user_id)) > 256
        ):
            raise HTTPException(status_code=422, detail="user_id must be a string or integer up to 256 characters.")

        result = sentinel_evaluate(body)
        result["message"] = str(body.get("message", ""))
        result["source"] = source_value
        result["plan"] = auth["tier"]
        return result

    return app


app = create_app()


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "info").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        "raven.api.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=False,
        proxy_headers=False,
        server_header=False,
        reload=False,
    )
