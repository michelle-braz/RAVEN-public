"""Regression tests for Portuguese-language incident scoring."""

from __future__ import annotations

from raven.api.v1.enrichment import enrich
from raven.sentinel.pipeline.data_layer.schemas import RawEvent, Severity, SourceType
from raven.sentinel.pipeline.intelligence_layer.engine import ScoringContext, build_engine
from raven.sentinel.pipeline.signal_layer.normalizer import normalize

ACTIVE_FAILURE = (
    "Apos a alteracao de configuracao, a API de inventario apresenta aumento "
    "de erros HTTP 500. Varios utilizadores recebem falhas e o problema continua ativo."
)
SUCCESSFUL_CHANGE = (
    "Alteracao da API de inventario concluida com sucesso. Nenhum erro identificado."
)
ISOLATED_ERROR = (
    "Foi observado um unico erro HTTP 500 na API de inventario. "
    "O servico continua operacional e nao ha utilizadores afetados."
)


def _analyze(message: str):
    engine = build_engine()
    signal = normalize(RawEvent(message=message, source=SourceType.UNKNOWN))
    assessment = engine.assess(signal, ScoringContext())
    return assessment, enrich(assessment, message, SourceType.UNKNOWN)


def test_active_failure_ranks_above_isolated_error():
    active, _ = _analyze(ACTIVE_FAILURE)
    isolated, _ = _analyze(ISOLATED_ERROR)
    assert active.risk_score > isolated.risk_score


def test_successful_change_is_not_escalated():
    _, enriched = _analyze(SUCCESSFUL_CHANGE)
    assert enriched.recommended_action in {"ignore", "group_as_noise"}


def test_isolated_error_stays_bounded():
    assessment, enriched = _analyze(ISOLATED_ERROR)
    assert assessment.risk_score < 0.60
    assert enriched.recommended_action not in {"investigate", "escalate"}


def test_low_context_stays_low():
    assessment, enriched = _analyze("banana cadeira janela")
    assert assessment.severity == Severity.LOW
    assert enriched.recommended_action in {"ignore", "group_as_noise"}


def test_zero_percent_errors_latency_notice_stays_low_priority():
    message = "Routine notice: latency above SLO limit, 0% errors, requests completing successfully."
    engine = build_engine()
    signal = normalize(RawEvent(message=message, source=SourceType.APPLICATION))
    assessment = engine.assess(signal, ScoringContext())
    enriched = enrich(assessment, message, SourceType.APPLICATION)
    assert enriched.event_type == "latency_spike"
    assert assessment.severity == Severity.LOW


def test_diacritic_folding_recovers_portuguese_tokens():
    signal = normalize(RawEvent(message="Nao ha erro no servico", source=SourceType.UNKNOWN))
    assert "erro" in signal.tokens


def test_http_5xx_is_not_collapsed_into_generic_number():
    signal = normalize(RawEvent(message="erro HTTP 500 no servico", source=SourceType.UNKNOWN))
    assert "<httperr>" in signal.tokens
    assert "<num>" not in signal.tokens
