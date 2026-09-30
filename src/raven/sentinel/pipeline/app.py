"""
Sentinel — Orchestration Core
=============================
Sequences the four decoupled layers (normalize → context → assess → act) and
holds the bounded recurrence window. It has no HTTP surface: the only public
entry point is the authenticated API in ``raven.api``.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass

from raven.sentinel.observability import BackpressurePolicy, BufferFull, EventBuffer
from raven.sentinel.pipeline.action_layer.notifier import ActionDispatcher
from raven.sentinel.pipeline.data_layer.schemas import (
    IngestionBatch,
    IngestionResult,
    RawEvent,
    RiskAssessment,
    Severity,
)
from raven.sentinel.pipeline.intelligence_layer.engine import (
    KnownIncident,
    RiskEngine,
    ScoringContext,
)
from raven.sentinel.pipeline.signal_layer.normalizer import normalize

# ── Mutable orchestration state ───────────────────────────────────────────────


@dataclass(slots=True)
class _WindowEntry:
    signature: str
    incident_id: str
    tokens: frozenset[str]
    ts: float


class SignalWindow:
    """Bounded, time-windowed memory of recent signals."""

    def __init__(
        self,
        *,
        maxlen: int = 5000,
        ttl_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._entries: deque[_WindowEntry] = deque(maxlen=maxlen)
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        # Injectable clock so tests and replay scenarios can control time-based
        # eviction without patching builtins (FM-2).
        self._clock = clock

    def _evict(self, now: float) -> None:
        cutoff = now - self._ttl
        while self._entries and self._entries[0].ts < cutoff:
            self._entries.popleft()

    async def context_for(self, signature: str) -> ScoringContext:
        now = self._clock()
        async with self._lock:
            self._evict(now)
            recurrence = sum(1 for e in self._entries if e.signature == signature)
            seen = recurrence > 0
            known: dict[str, KnownIncident] = {}
            for entry in reversed(self._entries):
                if entry.incident_id not in known:
                    known[entry.incident_id] = KnownIncident(
                        incident_id=entry.incident_id, tokens=entry.tokens
                    )
                if len(known) >= 100:
                    break
        # Sort by incident_id so the tuple order — and therefore cluster
        # tiebreaking — is deterministic regardless of window insertion order (FM-4).
        return ScoringContext(
            recurrence_count=recurrence + 1,
            seen_signature=seen,
            known_incidents=tuple(sorted(known.values(), key=lambda ki: ki.incident_id)),
        )

    async def record(
        self, signature: str, incident_id: str, tokens: frozenset[str]
    ) -> None:
        now = self._clock()
        async with self._lock:
            self._evict(now)
            self._entries.append(_WindowEntry(signature, incident_id, tokens, now))


# ── Orchestration pipeline ────────────────────────────────────────────────────

_DEFAULT_BUFFER_MAXSIZE = 256


class IngestionPipeline:
    """Sequences the four layers: normalize → context → assess → record → act."""

    def __init__(
        self,
        *,
        engine: RiskEngine,
        dispatcher: ActionDispatcher,
        window: SignalWindow,
        buf: EventBuffer[RawEvent] | None = None,
        policy: BackpressurePolicy = BackpressurePolicy.DROP_NEWEST,
    ) -> None:
        self._engine = engine
        self._dispatcher = dispatcher
        self._window = window
        self._buf: EventBuffer[RawEvent] = buf if buf is not None else EventBuffer(maxsize=_DEFAULT_BUFFER_MAXSIZE)
        self._policy = policy

    def buffer_metrics(self) -> dict[str, object]:
        m = self._buf.metrics()
        return {
            "capacity": m.capacity,
            "pending": m.pending,
            "accepted": m.accepted,
            "dropped": m.dropped,
            "utilization": round(m.utilization, 4),
        }

    async def process_event(self, event: RawEvent) -> tuple[RiskAssessment, int]:
        # Admission gate: raises BufferFull (DROP_NEWEST) or suspends (BLOCK).
        # The try block is only entered after a slot is successfully claimed,
        # so the finally always pairs exactly one get_nowait with the put above.
        if self._policy is BackpressurePolicy.BLOCK:
            await self._buf.put(event, policy=BackpressurePolicy.BLOCK)
        else:
            self._buf.put_nowait(event)  # raises BufferFull if at capacity

        try:
            signal = normalize(event)
            context = await self._window.context_for(signal.signature)
            assessment = self._engine.assess(signal, context)
            await self._window.record(
                assessment.signature, assessment.incident_id, frozenset(signal.tokens)
            )
            outcomes = await self._dispatcher.dispatch(assessment, event)
            dispatched = sum(1 for o in outcomes if o.status == o.status.DISPATCHED)
            return assessment, dispatched
        finally:
            self._buf.get_nowait()
            self._buf.task_done()

    async def process_batch(self, batch: IngestionBatch) -> IngestionResult:
        assessments: list[RiskAssessment] = []
        breakdown: Counter[Severity] = Counter()
        actions_total = 0
        for event in batch.events:
            try:
                assessment, dispatched = await self.process_event(event)
            except BufferFull:
                continue
            assessments.append(assessment)
            breakdown[assessment.severity] += 1
            actions_total += dispatched

        return IngestionResult(
            accepted=len(assessments),
            assessments=tuple(assessments),
            severity_breakdown={sev: breakdown.get(sev, 0) for sev in Severity},
            actions_dispatched=actions_total,
        )
