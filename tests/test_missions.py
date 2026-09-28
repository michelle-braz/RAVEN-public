"""Cyber Missions: content contract, serving through the RAVEN API, and the JS engine suite."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raven.api.main import app
from raven.missions import MISSIONS_WEB_DIR, load_missions

ROOT = Path(__file__).parents[1]
DATA = load_missions()
MISSIONS = DATA["missions"]
MODULES = {m["id"]: m for m in DATA["modules"]}

REQUIRED = (
    "id", "ticket", "module", "date", "title", "difficulty", "skill", "situation",
    "evidence", "question", "hints", "rubric", "factsKnown", "keyEvidence",
    "meaning", "remember", "nextStep", "conclusion",
)
EXPECTED_PER_MODULE = {"redes": 6, "sistemas": 6, "seguranca": 6, "logs": 7, "wireshark": 4, "portfolio": 4}


def test_every_mission_follows_the_fixed_structure():
    for m in MISSIONS:
        for key in REQUIRED:
            assert m.get(key), f"{m.get('id')}: missing {key}"
        assert m["module"] in MODULES
        assert 1 <= len(m["hints"]) <= 3, m["id"]
        assert any(c.get("required") for c in m["rubric"]), f"{m['id']}: no central concept"
        for c in m["rubric"]:
            assert c["patterns"] and c["praise"] and c["missFeedback"], (m["id"], c["id"])
            for p in c["patterns"]:
                re.compile(p)
        for mc in m.get("misconceptions", []):
            for p in mc["patterns"]:
                re.compile(p)
        # Situation stays short: a few lines, never a lecture.
        assert len(m["situation"]) <= 520, f"{m['id']}: situation too long"
        # "O que lembrar" is a single sentence-sized memory.
        assert len(m["remember"]) <= 170, f"{m['id']}: remember too long"


def test_ids_and_tickets_are_unique_and_sequential():
    assert len({m["id"] for m in MISSIONS}) == len(MISSIONS)
    assert [m["ticket"] for m in MISSIONS] == [f"#{i:03d}" for i in range(1, len(MISSIONS) + 1)]


def test_first_three_missions_are_ip_ports_http():
    assert [m["id"] for m in MISSIONS[:3]] == ["redes-01", "redes-02", "redes-03"]
    assert all(len(m["hints"]) == 3 for m in MISSIONS[:3])


@pytest.mark.skipif(len(MISSIONS) < 33, reason="full schedule not generated yet")
def test_full_schedule_matches_master_plan():
    assert len(MISSIONS) == 33
    counts: dict[str, int] = {}
    for m in MISSIONS:
        counts[m["module"]] = counts.get(m["module"], 0) + 1
    assert counts == EXPECTED_PER_MODULE
    # One mission per day, 29/09 → 31/10, in order.
    start = date(2026, 9, 29)
    assert [m["date"] for m in MISSIONS] == [(start + timedelta(days=i)).isoformat() for i in range(33)]
    bosses = [m["id"] for m in MISSIONS if m.get("boss")]
    assert bosses == ["redes-06", "sistemas-06", "seguranca-06", "wireshark-04"]
    milestone = [m for m in MISSIONS if m.get("milestone")]
    assert [m["date"] for m in milestone] == ["2026-10-17"]
    assert "CANDIDATURAS" in milestone[0]["milestone"]


def test_committed_missions_contain_only_simulated_data():
    text = (MISSIONS_WEB_DIR / "missions.json").read_text(encoding="utf-8").lower()
    for forbidden in ("api_key", "bearer ", "begin rsa", "password=", "@gmail.com"):
        assert forbidden not in text


def test_missions_are_served_publicly_by_raven():
    with TestClient(app) as client:
        page = client.get("/missions/")
        assert page.status_code == 200
        assert "Cyber Missions" in page.text
        assert "script-src 'self'" in page.headers["content-security-policy"]
        for asset in ("app.js", "engine.js", "style.css", "missions.json"):
            assert client.get(f"/missions/{asset}").status_code == 200, asset
        # The rest of RAVEN keeps its access gate.
        assert client.post("/v1/analyze", json={"message": "x"}).status_code == 401
        assert "/missions/" in client.get("/").text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_engine_suite():
    result = subprocess.run(
        ["node", "--test", *sorted(str(p) for p in (ROOT / "tests" / "missions").glob("*.test.mjs"))],
        capture_output=True, text=True, cwd=ROOT, timeout=120,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
