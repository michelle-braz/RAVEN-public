# Architecture

RAVEN has two main layers.

## API layer

`src/raven/api/main.py` creates the FastAPI application and initializes one shared Sentinel pipeline during application startup. The API layer owns authentication, request validation, error envelopes, CORS, security headers, and response serialization.

The principal endpoint is `POST /v1/analyze`. `POST /evaluate` exposes the earlier numerical rule engine. The beta routes record explicit analyst feedback and approved resolution context.

## Sentinel pipeline

The pipeline under `src/raven/sentinel/` performs:

1. input normalization and volatile-value removal;
2. deterministic scoring using lexical, source, recurrence, novelty, and volatility factors;
3. severity assignment and stable incident-pattern identification;
4. context enrichment into evidence, a hypothesis, and suggested next steps;
5. optional action dispatch and local observability buffering.

## State

The recurrence window and rate limits are held in process memory. Analyst-approved resolution records and decision-impact records are appended to JSONL files under `RAVEN_DATA_DIR`.

This architecture currently supports local and single-process operation. It does not provide transactional persistence, distributed coordination, or high-availability guarantees.
