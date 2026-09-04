# RAVEN

**Operational Context Prototype for Incident Investigation**

RAVEN is a functional technical prototype designed to reduce the effort required to understand what happened before deciding what to investigate next.

It organizes scattered operational information, separates evidence from hypotheses, highlights recurring signals, and keeps the final decision with the human analyst.

RAVEN is part of the broader **FOXHUMAN** approach to human-centered operational systems.

---

## 🎯 Why RAVEN exists

During conversations and validation with professionals across:

**QA • Engineering • Observability • Security • Support • SRE • NOC • Operations**

a recurring operational problem became clear:

important context is often fragmented across tools, tickets, logs, alerts, and previous incidents.

Before a technical investigation can even begin, the person often needs to:

- understand what happened;
- identify which information matters;
- separate facts from assumptions;
- search across multiple sources;
- decide where to investigate first.

RAVEN was created to explore a simpler operational flow for that problem.

> **Understand the context first. Investigate with more direction.**

---

## ⚙️ What RAVEN does

RAVEN receives an incident signal and returns a structured investigation context.

The public implementation can:

- normalize individual incident signals;
- apply deterministic, rule-based risk scoring;
- group recurring signals under stable incident identifiers;
- organize available evidence;
- separate evidence from an investigation hypothesis;
- suggest possible investigation steps;
- keep the final decision with the human analyst;
- record only explicitly approved resolution context.

The goal is not to automate the analyst's decision.

The goal is to reduce the effort required to understand the situation before that decision is made.

---

## 🧭 Example investigation flow

```text
Incident signal
      ↓
Normalize information
      ↓
Identify recurrence and risk
      ↓
Organize evidence
      ↓
Separate evidence from hypothesis
      ↓
Suggest investigation steps
      ↓
Human review and decision
      ↓
Optional approved resolution memory
```

This reflects the core principle behind the project:

**complexity behind the scenes, clearer context in front of the analyst.**

---

## 🚧 Status

RAVEN is under active development.

The following parts are functional in the public repository:

- analysis pipeline;
- REST API;
- structured investigation output;
- recurrence detection;
- deterministic scoring;
- evidence and hypothesis separation;
- suggested next steps;
- human-approved resolution memory;
- automated tests.

The public repository contains only synthetic examples and no third-party operational data.

RAVEN is not presented as:

- a finished commercial platform;
- a production-ready incident-management system;
- a replacement for observability platforms;
- an autonomous decision-making system.

---

## 🛠️ Technical implementation

RAVEN is built with:

`Python` • `FastAPI` • `REST APIs` • `JSONL` • `Pytest`

The current public architecture follows this flow:

```text
FastAPI request validation
        ↓
Signal normalization
        ↓
Scoring and recurrence detection
        ↓
Context enrichment
        ↓
Evidence / hypothesis / next steps
        ↓
Human review
        ↓
Explicit approval
        ↓
Validated local memory
```

The API layer handles HTTP validation, authentication, and response models.

The Sentinel package contains:

- normalization;
- deterministic scoring;
- recurrence detection;
- action dispatch.

Approved resolution records are stored locally in JSONL format.

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`SECURITY.md`](SECURITY.md)

---

## 🚀 Getting started

### ✅ Requirements

- Python 3.11 or newer

Clone the repository and create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create the local configuration:

### macOS / Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Set a local API key:

### macOS / Linux

```bash
export RAVEN_API_KEY="choose-a-local-development-key"
```

### Windows PowerShell

```powershell
$env:RAVEN_API_KEY="choose-a-local-development-key"
```

Start the API:

```bash
python -m uvicorn raven.api.main:app --host 127.0.0.1 --port 8000
```

Open:

- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Run the test suite:

```bash
python -m pytest tests -q
```

---

## 🧪 Synthetic example

```bash
curl -X POST "http://127.0.0.1:8000/v1/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: choose-a-local-development-key" \
  -d '{
    "message": "Checkout API returned HTTP 503 after a configuration change in the synthetic staging environment",
    "source": "application"
  }'
```

The response includes:

- risk score;
- available evidence;
- investigation hypothesis;
- context;
- suggested next steps.

A complete synthetic workflow is available in:

[`examples/synthetic-investigation.http`](examples/synthetic-investigation.http)

Additional synthetic log samples are available in:

[`examples/logs`](examples/logs/README.md)

---

## 📁 Project structure

```text
src/raven/api/        FastAPI application, authentication, and HTTP routes
src/raven/sentinel/   Normalization, scoring, recurrence, and action pipeline
tests/                Automated tests
docs/                 Architecture and API notes
examples/             Synthetic investigation examples
```

---

## 🔒 Security and privacy

All committed examples are synthetic.

Never commit:

- `.env`;
- API keys;
- real incident logs;
- local JSONL resolution data;
- information copied from a real investigation.

See [`SECURITY.md`](SECURITY.md).

---

## ⚠️ Limitations

This public implementation intentionally has clear boundaries:

- scoring and enrichment use deterministic heuristics, not learned models;
- recurrence windows and rate limits are process-local;
- validated memory uses local JSONL storage;
- there are no durability, horizontal-scaling, or high-availability guarantees;
- hypotheses and suggested next steps require human verification;
- external observability data must be supplied to the API;
- no vendor-specific connector is included;
- security controls are intended for local experimentation, not production hardening.

---

## 🧠 How this project reflects my work

RAVEN is not only a technical implementation.

It demonstrates the way I approach operational problems:

**understand the operation → identify the bottleneck → organize requirements → validate the problem → build and test a possible solution**

My current focus is on:

- Process Improvement
- Business Analysis
- Product Operations
- Digital Transformation
- Technology Operations

Technology is a tool in that process — not the starting point.

---

## 🦊 FOXHUMAN

RAVEN is part of **FOXHUMAN**, an independent project focused on reducing operational complexity and improving the path from information to decision.

**Complexity behind. Simplicity in front.**

---

## 👤 Author

**Michelle Braz**

[LinkedIn](https://www.linkedin.com/in/michelle-braz-perfil/)

---

## 📄 License

MIT
