"""Runtime configuration, read once from the environment.

Production is fail-closed: ``validate()`` returns every problem that would leave a
production deployment unsafe, and the API refuses to start while any remain.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ENVIRONMENTS = ("development", "production")
MIN_MASTER_KEY_LEN = 32
MIN_KEY_LEN = 24
DEFAULT_MAX_BODY_BYTES = 256 * 1024


class ConfigError(RuntimeError):
    """Raised at startup when the configuration is unsafe or invalid."""


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer.") from exc


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    cors_origins: tuple[str, ...] = ()
    docs_enabled: bool = True
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    trusted_proxy_hops: int = 0
    rate_limit_per_minute: int = 30
    data_dir: Path = Path("data")
    log_level: str = "info"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate(self, *, master_key: str | None, other_keys: frozenset[str]) -> list[str]:
        """Return the problems that make this configuration unsafe for production."""
        problems: list[str] = []
        if not self.is_production:
            return problems
        if not master_key:
            problems.append("RAVEN_API_KEY must be set.")
        elif len(master_key) < MIN_MASTER_KEY_LEN:
            problems.append(f"RAVEN_API_KEY must be at least {MIN_MASTER_KEY_LEN} characters.")
        if any(len(k) < MIN_KEY_LEN for k in other_keys):
            problems.append(f"Every FREE/PRO/beta API key must be at least {MIN_KEY_LEN} characters.")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must list explicit origins, not '*'.")
        if not self.data_dir.is_dir() or not os.access(self.data_dir, os.W_OK):
            problems.append(f"RAVEN_DATA_DIR ({self.data_dir}) must exist and be writable.")
        if not 1 <= self.rate_limit_per_minute <= 100_000:
            problems.append("RAVEN_RATE_LIMIT_PER_MINUTE must be between 1 and 100000.")
        if self.trusted_proxy_hops < 0:
            problems.append("RAVEN_TRUSTED_PROXY_HOPS must not be negative.")
        return problems


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    environment = env.get("ENVIRONMENT", "development").strip().lower() or "development"
    if environment not in ENVIRONMENTS:
        raise ConfigError(f"ENVIRONMENT must be one of {ENVIRONMENTS}, got {environment!r}.")
    production = environment == "production"
    origins_raw = env.get("CORS_ORIGINS")
    if origins_raw is None:
        origins: tuple[str, ...] = () if production else ("http://127.0.0.1:8000", "http://localhost:8000")
    else:
        origins = tuple(o.strip() for o in origins_raw.split(",") if o.strip())
    max_body = _int(env, "RAVEN_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES)
    if max_body < 1024:
        raise ConfigError("RAVEN_MAX_BODY_BYTES must be at least 1024.")
    return Settings(
        environment=environment,
        cors_origins=origins,
        docs_enabled=_flag(env, "RAVEN_ENABLE_DOCS", not production),
        max_body_bytes=max_body,
        trusted_proxy_hops=_int(env, "RAVEN_TRUSTED_PROXY_HOPS", 0),
        rate_limit_per_minute=_int(env, "RAVEN_RATE_LIMIT_PER_MINUTE", 30),
        data_dir=Path(env.get("RAVEN_DATA_DIR", "data")),
        log_level=env.get("LOG_LEVEL", "info").strip().lower() or "info",
    )
