from __future__ import annotations

import json
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Literal, TypedDict

from raven.api.auth import key_matches
from raven.api.settings import ConfigError


class BetaEntry(TypedDict):
    name: str
    status: Literal["active", "revoked"]
    created_at: str  # ISO 8601 UTC


def _load_registry_from_env() -> dict[str, BetaEntry]:
    """Populate the beta registry from the BETA_KEYS_JSON environment variable.

    Expected format (compact JSON):
      {"raven_beta_xxx": {"name": "Tester Name", "status": "active", "created_at": "2026-01-01T00:00:00Z"}}

    Returns an empty dict if the variable is unset. A malformed value raises
    ConfigError at startup: silently ignoring it would lock every beta user out.
    Use `python -m raven.admin keys new "<Name>"` to generate new keys.
    """
    raw = os.getenv("BETA_KEYS_JSON", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("BETA_KEYS_JSON is not valid JSON.") from exc
    if not isinstance(data, dict) or not all(
        isinstance(k, str)
        and isinstance(v, dict)
        and isinstance(v.get("name"), str)
        and v.get("status") in ("active", "revoked")
        and isinstance(v.get("created_at"), str)
        for k, v in data.items()
    ):
        raise ConfigError(
            'BETA_KEYS_JSON must map each key to {"name", "status": active|revoked, "created_at"}.'
        )
    return data


# In-memory registry — seeded from BETA_KEYS_JSON at startup.
# Swap is_valid_beta_key() for a DB lookup when the beta graduates.
# Schema and public interface stay the same.
BETA_REGISTRY: dict[str, BetaEntry] = _load_registry_from_env()


# ── Validation ────────────────────────────────────────────────────────────────

def is_valid_beta_key(key: str) -> bool:
    """Return True iff key is present in BETA_REGISTRY with status='active'."""
    active = [k for k, v in BETA_REGISTRY.items() if v["status"] == "active"]
    return key_matches(key, active)


# ── Key generation ────────────────────────────────────────────────────────────

_KEY_ALPHABET = string.ascii_lowercase + string.digits
_KEY_SUFFIX_LEN = 16


def generate_beta_key(prefix: str = "raven_beta") -> str:
    """Return a cryptographically secure beta key string.

    Format: <prefix>_<16 random lowercase-alphanumeric chars>
    Uses secrets.choice — safe for security-sensitive identifiers.
    """
    suffix = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(_KEY_SUFFIX_LEN))
    return f"{prefix}_{suffix}"


# ── Registry management ───────────────────────────────────────────────────────

def add_key(key: str, name: str) -> None:
    """Add an active beta key to the in-memory registry.

    Idempotent: re-adding an existing key updates name and resets status to active.
    """
    BETA_REGISTRY[key] = {
        "name":       name,
        "status":     "active",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def revoke_key(key: str) -> bool:
    """Set a key's status to 'revoked'. Returns False if key not found."""
    entry = BETA_REGISTRY.get(key)
    if entry is None:
        return False
    entry["status"] = "revoked"
    return True


def list_keys(*, active_only: bool = False) -> list[dict[str, str]]:
    """Return registry entries as a list of plain dicts, sorted by created_at."""
    rows = [
        {"key": k, **v}
        for k, v in BETA_REGISTRY.items()
        if not active_only or v["status"] == "active"
    ]
    return sorted(rows, key=lambda r: r["created_at"])
