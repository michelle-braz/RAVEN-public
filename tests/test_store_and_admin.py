"""Persistence guarantees and the operator data tools (export, retention, erasure, keys)."""
from __future__ import annotations

import json
import multiprocessing
import os
import stat

import pytest

from raven import admin
from raven.api.beta import store
from raven.api.beta.models import DecisionImpact, ValidatedIncident


def _impact(incident="inc-1", ts="2026-03-01T00:00:00Z") -> DecisionImpact:
    return DecisionImpact(incident_id=incident, request_id="r", decision_taken="ACCEPT", action_taken="a",
                          confidence=3, replaced_manual_process=False, time_saved_minutes=1, timestamp=ts)


def _validated(incident="inc-1", ts="2026-03-01T00:00:00Z") -> ValidatedIncident:
    return ValidatedIncident(incident_id=incident, request_id="r", signature="s", event_type="e", source="application",
                             message_normalized="m", resolution_text="fixed", hypothesis_validated=True,
                             analyst_confidence=4, timestamp=ts)


def _worker(args):
    data_dir, n = args
    os.environ["RAVEN_DATA_DIR"] = data_dir
    for i in range(n):
        store.append_validated_incident(_validated(f"inc-{os.getpid()}-{i}"))


def test_files_are_private(tmp_path):
    store.append_impact(_impact())
    d = store.data_dir()
    assert stat.S_IMODE(d.stat().st_mode) == 0o700
    assert stat.S_IMODE((d / store.DECISION_IMPACTS).stat().st_mode) == 0o600


def test_concurrent_writers_never_interleave_records(tmp_path):
    workers, per = 4, 60
    with multiprocessing.get_context("spawn").Pool(workers) as pool:
        pool.map(_worker, [(os.environ["RAVEN_DATA_DIR"], per)] * workers)
    lines = (store.data_dir() / store.VALIDATED_INCIDENTS).read_text().splitlines()
    assert len(lines) == workers * per
    assert all(json.loads(line)["resolution_text"] == "fixed" for line in lines)
    assert len(store.load_validated_incidents()) == workers * per


def test_corrupt_or_torn_line_does_not_break_reads(caplog):
    store.append_impact(_impact("a"))
    with open(store.data_dir() / store.DECISION_IMPACTS, "ab") as fh:
        fh.write(b'{"incident_id": "torn-by-a-crash\n\xff\xfe garbage\n')
    store.append_impact(_impact("b"))
    assert [i.incident_id for i in store.load_impacts()] == ["a", "b"]
    assert "skipping unreadable record" in caplog.text


def test_analyze_telemetry_failure_does_not_lose_the_analysis(monkeypatch):
    from fastapi.testclient import TestClient
    import raven.api.auth as auth
    import raven.api.main as main
    import raven.api.v1.router as v1

    def full_disk(*_):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(v1, "record_analyze_call", full_disk)
    monkeypatch.setattr(auth, "FREE_KEYS", frozenset({"k" * 24}))
    with TestClient(main.app) as c:
        r = c.post("/v1/analyze", json={"message": "service down", "source": "application"},
                   headers={"X-API-Key": "k" * 24})
    assert r.status_code == 200


def test_decision_write_failure_is_a_clean_503(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from raven.api.beta import router as beta

    def full_disk(_):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(beta, "append_impact", full_disk)
    app = FastAPI()
    app.include_router(beta.router)
    r = TestClient(app).post("/beta/decision-impact", json={
        "incident_id": "i", "request_id": "r", "decision_taken": "ACCEPT", "action_taken": "a",
        "confidence": 3, "replaced_manual_process": False, "time_saved_minutes": 0})
    assert r.status_code == 503 and "No space" not in r.text


# ── Operator tools ────────────────────────────────────────────────────────────

@pytest.fixture
def seeded():
    store.append_impact(_impact("old", "2025-01-01T00:00:00Z"))
    store.append_impact(_impact("new", "2026-06-01T00:00:00Z"))
    store.append_validated_incident(_validated("old", "2025-01-01T00:00:00Z"))
    store.append_validated_incident(_validated("new", "2026-06-01T00:00:00Z"))
    store.record_analyze_call("new", "r1")


def test_stats_and_export(seeded, tmp_path, capsys):
    assert admin.main(["stats"]) == 0
    assert "decision_impacts.jsonl: 2 records" in capsys.readouterr().out
    out = tmp_path / "export.json"
    assert admin.main(["export", "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert len(payload["files"][store.VALIDATED_INCIDENTS]) == 2
    assert stat.S_IMODE(out.stat().st_mode) == 0o600


def test_purge_is_a_dry_run_until_confirmed(seeded, capsys):
    assert admin.main(["purge", "--before", "2026-01-01"]) == 0
    assert "dry run" in capsys.readouterr().out
    assert len(store.load_impacts()) == 2
    assert admin.main(["purge", "--before", "2026-01-01", "--yes"]) == 0
    assert [i.incident_id for i in store.load_impacts()] == ["new"]
    assert [v.incident_id for v in store.load_validated_incidents()] == ["new"]
    assert store.count_analyze_calls() == 1  # recent telemetry kept
    assert stat.S_IMODE((store.data_dir() / store.DECISION_IMPACTS).stat().st_mode) == 0o600
    assert not [p for p in store.data_dir().iterdir() if p.name.startswith(".rewrite-")]


def test_purge_rejects_a_bad_date(seeded, capsys):
    assert admin.main(["purge", "--before", "yesterday"]) == 2


def test_erasure_by_incident_touches_every_file(seeded):
    assert admin.main(["delete", "--incident-id", "new", "--yes"]) == 0
    assert [i.incident_id for i in store.load_impacts()] == ["old"]
    assert [v.incident_id for v in store.load_validated_incidents()] == ["old"]
    assert store.count_analyze_calls() == 0


def test_erasure_dry_run_changes_nothing(seeded):
    admin.main(["delete", "--incident-id", "new"])
    assert len(store.load_impacts()) == 2


def test_key_generation_output_is_loadable(capsys, monkeypatch):
    from raven.api import beta_keys
    from raven.api.settings import MIN_KEY_LEN
    assert admin.main(["keys", "new", "Acme Corp"]) == 0
    lines = capsys.readouterr().out.splitlines()
    key = lines[0].removeprefix("key: ")
    assert len(key) >= MIN_KEY_LEN
    monkeypatch.setenv("BETA_KEYS_JSON", lines[-1])
    assert key in beta_keys._load_registry_from_env()
