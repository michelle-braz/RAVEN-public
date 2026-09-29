"""Shared fixtures: every test gets its own data directory and clean limiter state."""
from __future__ import annotations

import pytest

from raven.api import auth
from raven.api.ops import METRICS


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path / "data"))
    auth.reset_limiters()
    METRICS.reset()
    yield
    auth.reset_limiters()
