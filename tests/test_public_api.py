"""Public-entrypoint checks for the documented local workflow."""

from fastapi.testclient import TestClient

import raven.api.auth as auth
from raven.api.main import app


def test_health_and_central_analysis_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "FREE_KEYS", frozenset({"synthetic-test-key"}))
    monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        response = client.post(
            "/v1/analyze",
            headers={"X-API-Key": "synthetic-test-key"},
            json={
                "message": (
                    "Checkout API returned HTTP 503 after a configuration "
                    "change in the synthetic staging environment"
                ),
                "source": "application",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence"]
    assert body["hypothesis"]
    assert body["recommended_steps"]
