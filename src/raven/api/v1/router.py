"""Public API routes for RAVEN incident analysis."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from raven.api.auth import check_ip_rate_limit, require_api_key
from raven.api.beta.store import record_analyze_call
from raven.api.v1.enrichment import EnrichedAnalysis, enrich
from raven.sentinel.observability import BufferFull
from raven.sentinel.pipeline.app import IngestionPipeline
from raven.sentinel.pipeline.data_layer.schemas import RawEvent, SourceType

_log = logging.getLogger("raven.api.v1")

router = APIRouter(prefix="/v1", tags=["v1"])


class AnalyzeRequest(BaseModel):
    """A single incident signal to assess."""

    message: str = Field(
        min_length=1,
        max_length=8192,
        description="Raw event message to assess.",
    )
    source: SourceType = Field(
        default=SourceType.UNKNOWN,
        description=(
            "Signal origin. One of: application, infrastructure, network, "
            "iam, audit, unknown."
        ),
    )

    @field_validator("message", mode="before")
    @classmethod
    def _validate_message(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("message must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty or whitespace-only")
        return stripped


class AnalyzeResponse(BaseModel):
    """Structured incident context produced by the Sentinel pipeline."""

    request_id: str
    incident_id: str
    analysis_scope: str
    event_type: str
    monitored_object: str
    message: str
    source: str
    risk_score: float
    severity: str
    priority: str
    confidence: int
    recommended_action: str
    evidence: list[str]
    context: dict[str, Any]
    historical_context: dict[str, Any]
    impact: dict[str, Any]
    hypothesis: str
    recommended_steps: list[str]
    feedback: dict[str, Any]
    explain: dict[str, Any] | None = None
    tier: str
    impact_feedback_endpoint: str


def _ip_guard(request: Request) -> None:
    """Apply the in-memory request limit before scoring work begins."""

    ip = request.client.host if request.client else "unknown"
    check_ip_rate_limit(ip)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze an incident signal",
    description=(
        "Normalizes and scores one incident signal, then returns structured "
        "evidence, an investigation hypothesis, context, and suggested next steps. "
        "The result supports human investigation and is not an automated verdict."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "synthetic_service_failure": {
                            "summary": "Synthetic service failure",
                            "value": {
                                "message": (
                                    "Checkout API returned HTTP 503 after a configuration "
                                    "change in the synthetic staging environment"
                                ),
                                "source": "application",
                            },
                        },
                        "synthetic_normal_operation": {
                            "summary": "Synthetic normal operation",
                            "value": {
                                "message": "Background job completed successfully",
                                "source": "application",
                            },
                        },
                    }
                }
            }
        }
    },
)
async def analyze(
    body: AnalyzeRequest,
    request: Request,
    auth: dict[str, str] = Depends(require_api_key),
    _ip: None = Depends(_ip_guard),
) -> AnalyzeResponse:
    pipeline: IngestionPipeline = request.app.state.pipeline

    try:
        assessment, _ = await pipeline.process_event(
            RawEvent(message=body.message, source=body.source)
        )
    except BufferFull:
        raise HTTPException(status_code=429, detail="Pipeline buffer full. Retry later.")

    request_id = str(uuid.uuid4())
    explain: dict[str, Any] | None = None
    if assessment.factors:
        explain = {
            "factors": [
                {"name": factor.name, "weight": round(factor.weight, 4), "detail": factor.detail}
                for factor in assessment.factors
            ]
        }

    enriched: EnrichedAnalysis = enrich(assessment, body.message, body.source)
    record_analyze_call(assessment.incident_id, request_id)

    _log.info(
        "endpoint=/v1/analyze ts=%s risk_score=%.4f severity=%s action=%s "
        "event_type=%s incident_id=%s tier=%s",
        datetime.now(timezone.utc).isoformat(),
        assessment.risk_score,
        assessment.severity.value,
        enriched.recommended_action,
        enriched.event_type,
        assessment.incident_id,
        auth["tier"],
    )

    return AnalyzeResponse(
        request_id=request_id,
        incident_id=assessment.incident_id,
        analysis_scope=enriched.analysis_scope,
        event_type=enriched.event_type,
        monitored_object=enriched.monitored_object,
        message=body.message,
        source=body.source.value,
        risk_score=round(assessment.risk_score, 4),
        severity=assessment.severity.value,
        priority=enriched.priority,
        confidence=enriched.confidence,
        recommended_action=enriched.recommended_action,
        evidence=enriched.evidence,
        context=enriched.context,
        historical_context=enriched.historical_context,
        impact=enriched.impact,
        hypothesis=enriched.hypothesis,
        recommended_steps=enriched.recommended_steps,
        feedback=enriched.feedback,
        explain=explain,
        tier=auth["tier"],
        impact_feedback_endpoint="/beta/decision-impact",
    )
