from __future__ import annotations

from fastapi.testclient import TestClient

import raven.api.auth as auth
import raven.api.main as main


def test_configured_free_key_works_when_master_key_is_set(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_master_key", "raven-production-key")
    monkeypatch.setattr(auth, "PRO_KEYS", frozenset({"raven-production-key"}))
    monkeypatch.setattr(auth, "FREE_KEYS", frozenset({"test-free-key"}))
    monkeypatch.setattr(main, "_BETA_MASTER", "raven-production-key")

    with TestClient(main.app) as client:
        response = client.post(
            "/evaluate",
            headers={"X-API-Key": "test-free-key"},
            json={"message": "user viewed dashboard", "source": "application"},
        )

    assert response.status_code == 200
    assert response.json()["plan"] == "free"


def test_invalid_key_still_blocked_by_beta_gate(monkeypatch) -> None:
    monkeypatch.setattr(auth, "_master_key", "raven-production-key")
    monkeypatch.setattr(auth, "PRO_KEYS", frozenset({"raven-production-key"}))
    monkeypatch.setattr(auth, "FREE_KEYS", frozenset({"test-free-key"}))
    monkeypatch.setattr(main, "_BETA_MASTER", "raven-production-key")

    with TestClient(main.app) as client:
        response = client.post(
            "/evaluate",
            headers={"X-API-Key": "not-a-real-key"},
            json={"message": "user viewed dashboard", "source": "application"},
        )

    assert response.status_code == 403
    assert response.json()["error"] == "invalid_api_key"
