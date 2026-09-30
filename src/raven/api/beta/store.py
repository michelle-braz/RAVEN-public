"""Append-only JSONL persistence under ``RAVEN_DATA_DIR``.

Guarantees:
* one record = one line, written with a single ``os.write`` on an ``O_APPEND``
  descriptor, so concurrent writers cannot interleave inside a record;
* decision records are ``fsync``ed before the API answers; analysis telemetry is not;
* files are created ``0600`` inside a ``0700`` directory;
* a torn or corrupt line is skipped (and logged) instead of failing every read.

This is deliberately simple. It suits one instance per customer at pilot volume;
see docs/system/architecture.md for the supported envelope.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, TypeVar

from pydantic import BaseModel, ValidationError

from .models import DecisionImpact, ValidatedIncident

_log = logging.getLogger("raven.store")
M = TypeVar("M", bound=BaseModel)

ANALYZE_CALLS = "analyze_calls.jsonl"
DECISION_IMPACTS = "decision_impacts.jsonl"
VALIDATED_INCIDENTS = "validated_incidents.jsonl"
ALL_FILES = (ANALYZE_CALLS, DECISION_IMPACTS, VALIDATED_INCIDENTS)


def data_dir() -> Path:
    d = Path(os.getenv("RAVEN_DATA_DIR", "data"))
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)
    return d


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append(name: str, line: str, *, durable: bool) -> None:
    payload = (line.replace("\n", " ") + "\n").encode("utf-8")
    fd = os.open(data_dir() / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, payload)
        if durable:
            os.fsync(fd)
    finally:
        os.close(fd)


def _lines(name: str) -> Iterator[str]:
    path = data_dir() / name
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                yield line


def _load(name: str, model: type[M]) -> list[M]:
    out: list[M] = []
    for n, line in enumerate(_lines(name), start=1):
        try:
            out.append(model.model_validate_json(line))
        except ValidationError:
            _log.warning("skipping unreadable record file=%s line=%d", name, n)
    return out


# ── Analyze call tracking (telemetry; best effort) ────────────────────────────

def record_analyze_call(incident_id: str, request_id: str) -> None:
    _append(
        ANALYZE_CALLS,
        json.dumps({"ts": _utc_now(), "incident_id": incident_id, "request_id": request_id}),
        durable=False,
    )


def count_analyze_calls() -> int:
    return sum(1 for _ in _lines(ANALYZE_CALLS))


# ── Decision impact persistence ───────────────────────────────────────────────

def append_impact(impact: DecisionImpact) -> None:
    _append(DECISION_IMPACTS, impact.model_dump_json(), durable=True)


def load_impacts() -> list[DecisionImpact]:
    return _load(DECISION_IMPACTS, DecisionImpact)


# ── Validated incident memory persistence ─────────────────────────────────────

def append_validated_incident(record: ValidatedIncident) -> None:
    _append(VALIDATED_INCIDENTS, record.model_dump_json(), durable=True)


def load_validated_incidents() -> list[ValidatedIncident]:
    return _load(VALIDATED_INCIDENTS, ValidatedIncident)


def get_validated_incident_by_id(record_id: str) -> ValidatedIncident | None:
    for record in load_validated_incidents():
        if record.id == record_id:
            return record
    return None


def get_validated_incidents_by_incident_id(incident_id: str) -> list[ValidatedIncident]:
    return [r for r in load_validated_incidents() if r.incident_id == incident_id]
