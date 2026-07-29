# API examples

All payloads on this page are synthetic.

## Health

```http
GET /health
```

## Analyze an incident signal

```http
POST /v1/analyze
Content-Type: application/json
X-API-Key: choose-a-local-development-key

{
  "message": "Checkout API returned HTTP 503 after a configuration change in the synthetic staging environment",
  "source": "application"
}
```

The response contains separate `evidence` and `hypothesis` fields, plus a risk score, operational context, and recommended investigation steps.

## Record an approved resolution

Use the `incident_id` and `request_id` returned by the analysis:

```http
POST /beta/validate-resolution
Content-Type: application/json
X-API-Key: choose-a-local-development-key

{
  "incident_id": "replace-with-returned-incident-id",
  "request_id": "replace-with-returned-request-id",
  "decision_taken": "INVESTIGATE",
  "action_taken": "Reviewed the synthetic service configuration",
  "confidence": 4,
  "replaced_manual_process": false,
  "time_saved_minutes": 0,
  "hypothesis_correct": true,
  "resolution_text": "Restored the previous synthetic configuration and confirmed recovery",
  "memory_write_approved": true,
  "event_type": "service_unavailable",
  "source": "application",
  "message_normalized": "checkout api returned http error after configuration change",
  "tokens": ["checkout", "api", "error", "configuration", "change"],
  "validated_by": "synthetic-analyst"
}
```

Memory is written only when `memory_write_approved` is true and resolution text is present.

