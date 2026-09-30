# RAVEN

**Human-first incident context.** RAVEN turns a raw incident signal into structured context for an analyst:
evidence kept apart from hypothesis, a deterministic risk score, recurrence, and suggested next steps. The
analyst decides; RAVEN records a resolution only when a human approves it.

Part of FOXHUMAN: *complexity behind, simplicity in front.*

## The problem

During an incident, context is scattered across tools, tickets, logs and earlier incidents. Before investigating,
someone has to work out what happened, which facts matter, which statements are assumptions, and where to look
first. RAVEN does that first pass consistently and explainably. It is for SRE, NOC, QA, support and engineering
teams, and for engineers who integrate that context into their own tools.

## What it does

* Normalizes a signal and scores it deterministically (explainable factors, English and Portuguese vocabulary).
* Groups repeats under a stable incident id (recurrence in memory of the running process).
* Returns `evidence` (observed) separately from `hypothesis` (heuristic), plus ordered next steps.
* Records analyst decisions and, with explicit approval, validated resolutions.
* Includes **Cyber Missions**, a daily investigation practice app (33 missions, pt-BR), at `/missions/`.

It uses no machine learning, makes no outbound network calls, and reports only what it observed: no invented
ticket counts, topology or history. The score is a conservative lexical heuristic, not a severity verdict.
Details and per-capability status: [product overview](docs/product/overview.md).

## Architecture

One Python process: FastAPI API layer → deterministic Sentinel pipeline → enrichment; append-only JSONL storage;
static Missions app. Delivered as one container per customer behind an HTTPS proxy.
[Architecture](docs/system/architecture.md).

## Run it

Development:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export RAVEN_API_KEY="choose-a-local-development-key"
python -m uvicorn raven.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` (development only) or `/missions/`. Try it:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze -H "Content-Type: application/json" \
  -H "X-API-Key: choose-a-local-development-key" \
  -d '{"message":"Checkout API returned HTTP 503 after a configuration change in the synthetic staging environment","source":"application"}'
```

Tests: `python -m pytest tests -q`.

Production: `cd deploy && cp .env.example .env`, fill it in, `docker compose --env-file .env up -d --build`.
See [deployment](docs/deployment/deployment.md) and the [runbook](docs/operations/runbook.md).

## Security expectations

Production refuses to start with a weak or missing key. Keys are compared in constant time, failed attempts lock a
client address out, bodies are capped, every response carries security headers, and the container runs unprivileged
with a read-only filesystem. Data files are not encrypted by the application (use an encrypted volume). The service
has **not** been independently audited. Read the [security model](docs/security/security-model.md) and the
[data handling](docs/privacy/data-handling.md) notes before storing real incident text.

## Documentation

Start at [docs/README.md](docs/README.md): product, UX, architecture, API reference, security, privacy,
operations, deployment, legal, licensing, validation, decisions. Also [CHANGELOG](CHANGELOG.md) and
[FUTURE](FUTURE.md).

## Licence

Proprietary, all rights reserved: see [LICENSE](LICENSE). Earlier versions (up to commit `0f66b49`) were MIT.
Third-party components keep their own licences: [inventory](docs/licensing/THIRD_PARTY.md),
[details](docs/licensing/LICENSING.md). RAVEN is not affiliated with or endorsed by any observability provider.

© 2026 Michelle Braz
