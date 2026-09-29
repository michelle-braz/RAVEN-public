"""
RAVEN API — Authentication and Rate Limiting
============================================
All auth and rate-limiting logic lives here so the key store can be
swapped (env-var → DB → OAuth) by changing only this module.

Every key comparison is constant-time. Keys are never logged.

Migration path to DB-backed keys:
  Replace the body of _tier() with a DB lookup. The rest of the auth
  flow (HTTPException codes, rate limit enforcement) stays the same.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from raven.api.ratelimit import SlidingWindowLimiter

# ── Key store (env-var backed) ────────────────────────────────────────────────

def _load_keys(env_var: str, default: str) -> frozenset[str]:
    return frozenset(k.strip() for k in os.getenv(env_var, default).split(",") if k.strip())


def key_matches(candidate: str, keys) -> bool:
    """Constant-time membership test (no early exit on the first match)."""
    probe = candidate.encode("utf-8")
    matched = False
    for key in keys:
        if hmac.compare_digest(probe, key.encode("utf-8")):
            matched = True
    return matched


# Populate FREE_API_KEYS / PRO_API_KEYS env vars with comma-separated keys
# for multi-key deployments. For single-key deployments use RAVEN_API_KEY only.
FREE_KEYS: frozenset[str] = _load_keys("FREE_API_KEYS", "")
PRO_KEYS: frozenset[str] = _load_keys("PRO_API_KEYS", "")

# RAVEN_API_KEY is the operator (master) key — always accepted as pro tier and the
# only key allowed to read operator endpoints (/ops/metrics, /beta/business-proof).
_master_key = os.getenv("RAVEN_API_KEY") or None
if _master_key:
    PRO_KEYS = PRO_KEYS | frozenset({_master_key})

_DAILY_LIMITS: dict[str, int] = {"free": 100, "pro": 10_000}
_DAY = 86_400.0
_MINUTE = 60.0
_IP_LIMIT = 30
AUTH_FAILURE_LIMIT = 10  # failed key attempts per IP per minute before 429

_key_limiter = SlidingWindowLimiter(limit=max(_DAILY_LIMITS.values()), window_seconds=_DAY)
_ip_limiter = SlidingWindowLimiter(limit=_IP_LIMIT, window_seconds=_MINUTE)
_failure_limiter = SlidingWindowLimiter(limit=AUTH_FAILURE_LIMIT, window_seconds=_MINUTE)


def reset_limiters() -> None:
    """Clear all in-memory limiter state (used by tests and admin tooling)."""
    _key_limiter.clear()
    _ip_limiter.clear()
    _failure_limiter.clear()


def _tier(api_key: str) -> str | None:
    """Return plan tier for a key, or None if unrecognised.

    DB-migration point: replace this body with a database lookup.
    Signature and return type must not change.
    """
    if key_matches(api_key, PRO_KEYS):
        return "pro"
    # Beta keys are read from the live registry on every call, so a revoked key
    # stops working immediately. Late import avoids the beta_keys → auth cycle.
    from raven.api.beta_keys import is_valid_beta_key
    if is_valid_beta_key(api_key):
        return "pro"
    if key_matches(api_key, FREE_KEYS):
        return "free"
    return None


def configured_key_tier(api_key: str) -> str | None:
    """Return the configured env-var tier for an API key, if any."""
    return _tier(api_key)


def is_operator_key(api_key: str) -> bool:
    return bool(_master_key) and hmac.compare_digest(api_key.encode("utf-8"), _master_key.encode("utf-8"))


# ── Client address ────────────────────────────────────────────────────────────

def client_ip(request: Request) -> str:
    """Best-effort client address.

    ``RAVEN_TRUSTED_PROXY_HOPS`` is the number of reverse proxies in front of the
    app that append to X-Forwarded-For. With 0 (default) the header is ignored, so
    a client cannot spoof its address to dodge the limits.
    """
    peer = request.client.host if request.client else "unknown"
    settings = getattr(request.app.state, "settings", None)
    hops = settings.trusted_proxy_hops if settings else 0
    if hops <= 0:
        return peer
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return parts[-hops] if len(parts) >= hops else peer


# ── Failed-attempt throttle (brute-force protection) ──────────────────────────

def auth_attempts_blocked(ip: str) -> bool:
    return _failure_limiter.is_blocked(ip)


def record_auth_failure(ip: str) -> None:
    _failure_limiter.record(ip)


# ── Per-key daily quota / per-IP per-minute limits ────────────────────────────

def _check_key_limit(api_key: str, tier: str) -> None:
    limit = _DAILY_LIMITS[tier]
    if not _key_limiter.hit(f"{tier}:{api_key}", limit=limit):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({limit} req/day for the configured tier).",
        )


def check_ip_rate_limit(ip: str) -> None:
    """Enforce 30 req/min per source IP. Raises HTTP 429 on breach."""
    if not _ip_limiter.hit(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({_IP_LIMIT} req/min per IP).",
        )


# ── FastAPI auth dependency ───────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Depends(_api_key_header),
) -> dict[str, str]:
    """FastAPI dependency: authenticate via X-API-Key.

    Production (RAVEN_API_KEY set): master/pro/beta keys → tier="pro";
    configured free keys → tier="free" with daily quota.
    Dev fallback (RAVEN_API_KEY unset): configured keys accepted with daily quota.
    All auth failures raise HTTP 401.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if _master_key:
        configured_tier = _tier(api_key)
        if is_operator_key(api_key) or configured_tier == "pro":  # includes active beta keys
            return {"key": api_key, "tier": "pro"}
        if configured_tier == "free":
            _check_key_limit(api_key, "free")
            return {"key": api_key, "tier": "free"}
        raise HTTPException(status_code=401, detail="Invalid API key.")
    # Dev fallback: accept demo keys with quota enforcement.
    tier = _tier(api_key)
    if tier is None:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    _check_key_limit(api_key, tier)
    return {"key": api_key, "tier": tier}
