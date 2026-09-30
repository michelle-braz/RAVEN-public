# Architecture

> Classification: Technical / Architecture

RAVEN is one Python process: a FastAPI application around a deterministic analysis engine, plus a static web
application. There is no database and no outbound network call.

```text
client ──HTTPS──► proxy (Caddy) ──► RAVEN process
                                     ├─ middleware: request id + access log → CORS → body cap → access gate
                                     ├─ api/        authentication, validation, error envelope, routes
                                     ├─ sentinel/   normalize → score → group → (dispatch)   [no HTTP]
                                     ├─ api/v1/enrichment  evidence, hypothesis, steps       [pure functions]
                                     ├─ api/beta/store     append-only JSONL under RAVEN_DATA_DIR
                                     └─ missions/web       static study app (/missions/)
```

## Layers

* **API layer** (`src/raven/api/`): the only place that knows HTTP. Authentication and limits (`auth.py`,
  `ratelimit.py`), configuration (`settings.py`), middleware (`middleware.py`), counters (`ops.py`), routes
  (`main.py`, `v1/`, `beta/`).
* **Sentinel pipeline** (`src/raven/sentinel/`): normalization and volatile-value removal; deterministic scoring
  from lexical, source, recurrence, novelty and volatility factors; severity and stable incident id; bounded
  recurrence window; optional action dispatch. It has no HTTP surface.
* **Enrichment** (`api/v1/enrichment.py`): turns an assessment plus the message into evidence, hypothesis and
  steps. Pure and deterministic. It reports only what is observed or derived from wording.
* **Operator tooling** (`raven.admin`): export, retention, erasure, key generation.

## Request flow for `/v1/analyze`

client address → failed-attempt lockout check → API key check → body cap and Unicode guard → schema validation
(422) → per-client rate limit (429) → pipeline (normalize, window lookup, score, record in window, dispatch) →
enrichment → telemetry line appended (best effort) → response.

## State

| State | Where | Survives restart | Notes |
|---|---|---|---|
| Recurrence window (signature, incident id, tokens; default 5,000 entries / 3,600 s) | Process memory | No | Message text is not kept |
| Rate limits, lockout, counters | Process memory | No | Bounded (10,000 keys per limiter) |
| Decision impacts, validated incidents, analysis telemetry | JSONL files in `RAVEN_DATA_DIR` | Yes | One record per line; see below |

## Persistence

Append-only JSONL, chosen because volume is low, records are immutable and inspectable, and backup is a file copy
([ADR-0002](../decisions/0002-jsonl-persistence.md)). Each record is one `os.write` on an `O_APPEND` descriptor
(concurrent writers cannot interleave inside a record); decision records are `fsync`ed before the API answers;
files are `0600` in a `0700` directory; a corrupt line is skipped and logged instead of failing reads. There are no
transactions, no indexes and no encryption at rest.

## Failure behaviour

| Failure | Behaviour |
|---|---|
| Pipeline buffer full | 429 with retry hint; other requests unaffected |
| Disk full or unwritable, telemetry write | Analysis still returned; `storage_failures` counter incremented |
| Disk full or unwritable, decision write | 503, nothing reported as recorded |
| Corrupt line in a data file | Skipped with a warning; remaining records served |
| Unexpected exception | 500 with a request id only; stack (no message text) in the log; `responses_5xx` incremented |
| Unsafe production configuration | Process refuses to start and logs every problem |
| Restart | Recurrence window and counters reset; stored records intact |

## Capacity envelope (measured, single process)

Measured on the development container (4 vCPU) on 2026-09-29; treat as orders of magnitude, not a guarantee.

| Measure | Result |
|---|---|
| Engine plus enrichment per analysis (2,000 distinct signals) | about 0.2 ms |
| HTTP round trip, `/evaluate`, sequential | p50 1.9 ms, p95 2.2 ms |
| HTTP, 20 concurrent clients, shared connections | about 680 requests/s, p95 40 ms |
| `/beta/impact-summary` with 100,000 decision records (41 MB) | about 0.7 s (reads the whole file) |
| `/v1/analyze` default limit | 30 per minute per client address (`RAVEN_RATE_LIMIT_PER_MINUTE`) |

Beyond roughly 100,000 records per file, run the retention command or move to a database. A single process is
deliberate: the recurrence window and limits live in memory, so a second process would split them. Scale by
running one instance per customer, not by adding workers to one instance.

## Boundaries and extension points

* Key store: replace `auth._tier()` with a lookup (documented in the module).
* Storage: `api/beta/store.py` is the only module that touches the data files.
* Alert channels: `sentinel/pipeline/action_layer/notifier.py` defines the channel protocol; the webhook channel is
  not wired into the API ([FUTURE.md](../../FUTURE.md)).
