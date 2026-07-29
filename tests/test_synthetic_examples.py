"""Safety and shape checks for committed synthetic log examples."""

from __future__ import annotations

import json
import re
from pathlib import Path

LOG_DIR = Path(__file__).parents[1] / "examples" / "logs"
LOG_FILES = (
    LOG_DIR / "clear-incident.txt",
    LOG_DIR / "normal-operation.txt",
    LOG_DIR / "ambiguous-signal.txt",
)

FORBIDDEN = re.compile(
    r"https?://|(?:\d{1,3}\.){3}\d{1,3}|token|api[_-]?key|authorization|"
    r"customer|client",
    re.IGNORECASE,
)


def _records(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_log_examples_are_valid_standalone_json():
    for path in LOG_FILES:
        records = _records(path)
        assert records
        assert all(
            {"timestamp", "level", "service", "environment", "message"} <= record.keys()
            for record in records
        )


def test_log_examples_contain_no_forbidden_identifiers():
    for path in LOG_FILES:
        assert FORBIDDEN.search(path.read_text(encoding="utf-8")) is None


def test_log_examples_are_explicitly_synthetic():
    for path in LOG_FILES:
        records = _records(path)
        assert all(record["environment"] == "synthetic-staging" for record in records)
