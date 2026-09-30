"""Small in-memory sliding-window limiter with bounded memory.

State is per process. That matches the supported deployment (one instance, one
process per customer); see docs/system/architecture.md.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from typing import Callable


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._max_keys = max_keys
        self._clock = clock
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            hits = self._hits[key] = deque()
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        self._hits.move_to_end(key)
        return hits

    def _shrink(self) -> None:
        while len(self._hits) > self._max_keys:
            self._hits.popitem(last=False)

    def is_blocked(self, key: str, *, limit: int | None = None) -> bool:
        """True when ``key`` already used its budget. Records nothing."""
        with self._lock:
            hits = self._prune(key, self._clock())
            blocked = len(hits) >= (self.limit if limit is None else limit)
            if not hits:
                del self._hits[key]
            return blocked

    def hit(self, key: str, *, limit: int | None = None) -> bool:
        """Record one use. Returns False (and records nothing) when over budget."""
        with self._lock:
            now = self._clock()
            hits = self._prune(key, now)
            if len(hits) >= (self.limit if limit is None else limit):
                return False
            hits.append(now)
            self._shrink()
            return True

    def record(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._prune(key, now).append(now)
            self._shrink()

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
