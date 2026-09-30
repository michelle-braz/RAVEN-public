"""The response must contain only what RAVEN can observe or derive — never invented figures."""
from __future__ import annotations

import asyncio

from raven.api.v1.enrichment import enrich
from raven.sentinel.pipeline.action_layer.notifier import ActionDispatcher
from raven.sentinel.pipeline.app import IngestionPipeline, SignalWindow
from raven.sentinel.pipeline.data_layer.schemas import RawEvent, SourceType
from raven.sentinel.pipeline.intelligence_layer.engine import build_engine

MSG = "Checkout API returned HTTP 503 after a configuration change in the synthetic staging environment"


def analyse(message: str, pipeline: IngestionPipeline | None = None, source=SourceType.APPLICATION):
    pipeline = pipeline or IngestionPipeline(engine=build_engine(), dispatcher=ActionDispatcher([]), window=SignalWindow())
    assessment, _ = asyncio.run(pipeline.process_event(RawEvent(message=message, source=source)))
    return enrich(assessment, message, source)


def test_no_invented_figures_are_returned():
    result = analyse(MSG)
    assert "related_tickets" not in result.context
    assert "similar_incidents_last_30d" not in result.historical_context
    assert "known_resolution" not in result.historical_context
    assert "affected_users" not in result.impact
    assert result.impact["basis"].startswith("derived from severity")


def test_affected_services_lists_only_the_detected_object():
    result = analyse(MSG)
    assert result.monitored_object == "payment-service"
    assert result.context["affected_services"] == ["payment-service"]  # no guessed downstream topology
    assert analyse("something odd happened").context["affected_services"] == ["application-service"]  # source fallback
    unknown = analyse("something odd happened", source=SourceType.UNKNOWN)
    assert unknown.context["affected_services"] == []


def test_configuration_change_wording_counts_as_a_change():
    assert analyse(MSG).context["recent_deployment"] is True
    assert analyse("Background job completed successfully").context["recent_deployment"] is False


def test_history_is_what_was_observed_in_the_window():
    pipeline = IngestionPipeline(engine=build_engine(), dispatcher=ActionDispatcher([]), window=SignalWindow())
    first = analyse(MSG, pipeline)
    assert first.historical_context["occurrences_in_active_window"] == 1
    assert first.historical_context["last_occurrence"] == "first occurrence in the active window"
    for _ in range(2):
        again = analyse(MSG, pipeline)
    assert again.historical_context["occurrences_in_active_window"] == 3
    assert again.context["related_alerts"] == 2
    assert again.historical_context["suggested_playbook"]


def test_analysis_is_deterministic():
    a, b = analyse(MSG), analyse(MSG)
    assert a == b
