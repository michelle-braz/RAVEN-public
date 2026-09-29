"""Lightweight operational counters (in-process, no external dependency).

Enough to answer: is it alive, are errors rising, are analyses running, is storage
failing. Counters reset on restart; scrape ``/ops/metrics`` (operator key) and keep
history in whatever monitoring the operator already has.
"""
from __future__ import annotations

import threading
from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()

    def inc(self, name: str, n: int = 1) -> None:
        with self._lock:
            self._counts[name] += n

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(sorted(self._counts.items()))

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


METRICS = Metrics()
