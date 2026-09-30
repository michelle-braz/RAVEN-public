# Product overview

> Classification: Product

## What RAVEN is

RAVEN reduces the effort of understanding *what happened* before deciding *what to investigate next*. It receives
one incident signal (a log line, alert text or ticket summary) and returns structured context. It does not
decide, act or remediate: the final decision stays with the analyst, and RAVEN records only resolutions a human
explicitly approves.

RAVEN is the reading and correlation capability of the broader FOXHUMAN approach: complexity behind, clarity in front.

## The problem

Context is scattered across tools, tickets, logs and earlier incidents. Before an investigation can start, someone
has to work out what happened, which information matters, which statements are fact and which are assumption, and
where to look first. RAVEN does that first pass consistently and explainably.

## What you get from one analysis

| You send | RAVEN returns |
|---|---|
| `message` (up to 8,192 characters) and `source` (application, infrastructure, network, iam, audit, unknown) | risk score and severity band; the scoring factors that fired (**evidence**); a keyword-based classification and affected-component guess; a **hypothesis** kept separate from evidence; recurrence seen in the active window; suggested next steps; a stable incident id |

Scoring is deterministic and explainable (`explain.factors`): identical input in identical state gives identical output.
There is no machine-learning or language-model component, and no data leaves the service.

## Delivery model

Self-hosted, **one instance per customer** (single tenant), one container behind a TLS proxy, keys issued per
customer. See [deployment](../deployment/deployment.md). Commercial packaging (price, support terms) is not
defined in this repository.

## Capability status

*Implemented* = exists in code. *Validated* = covered by an automated check in this repository.
*Configurable* = the operator can change it. *Planned* = not built; see [FUTURE.md](../../FUTURE.md).

| Capability | Status | Evidence / note |
|---|---|---|
| Signal normalization (volatile values such as IPs and timestamps removed from the signature) | Implemented, validated | `tests/test_smoke.py` |
| Deterministic risk scoring, English and Portuguese vocabulary | Implemented, validated | `tests/test_smoke.py`, `tests/test_pt_lexical_scoring.py` |
| Recurrence detection and incident grouping | Implemented, validated, configurable | In process memory only: resets on restart. `SENTINEL_WINDOW_*` |
| Evidence separated from hypothesis; suggested next steps | Implemented, validated | `tests/test_enrichment_honesty.py`. Steps are generic playbooks per event type |
| Only observed data in the response (no invented counts, topology or history) | Implemented, validated | `tests/test_enrichment_honesty.py` |
| Analyst feedback and approved-resolution recording | Implemented, validated | `/beta/*` endpoints. Recorded, **not yet used** to influence later analyses (Planned) |
| API keys, tiers, quota, failed-attempt lockout, operator-only endpoints | Implemented, validated, configurable | `tests/test_security_hardening.py` |
| Export, retention, erasure and key generation for the operator | Implemented, validated | `raven-admin`, `tests/test_store_and_admin.py` |
| Health, readiness, request ids, access log, counters | Implemented, validated | `/health`, `/ready`, `/ops/metrics` |
| Container deployment behind HTTPS proxy, backup and restore | Implemented, validated | `deploy/smoke.sh` (see [validation](../validation/readiness-report.md)) |
| Cyber Missions (33 missions) | Implemented, validated | End-to-end run of all 33; accessibility scan |
| Outbound alerting (webhook) | Building block only, **not enabled** in the API | Planned |
| Multi-user workspace, roles, SSO, multi-tenant hosting | Not provided | Design only: [workspace design](foxhuman-workspace-design.md) |
| Connectors to observability platforms | Not provided | Data is supplied through the API |
| Encryption at rest | Not provided by the application | Use disk/volume encryption ([privacy](../privacy/data-handling.md)) |
| High availability, horizontal scaling | Not provided | One process by design ([architecture](../system/architecture.md)) |

## Known limits of the analysis

* The score is a lexical heuristic: keyword density, a prior per source, recurrence and novelty. It ranks and
  groups signals; it is not a severity verdict. It is deliberately conservative: a single terse outage sentence can
  score LOW (for example the synthetic checkout 503 in the API reference scores 0.27 and `group_as_noise`), while
  repeats and stronger wording raise it.
* The calibration was set by the vendor on synthetic and pilot examples. It has not been validated on customer
  data, and RAVEN reports no accuracy figure.
* Classification and component names come from keyword lists (English and Portuguese). Unrecognised wording
  yields `unknown`.
* Recurrence is memory of the running process (default one hour); it is lost on restart.

## What RAVEN does not claim

It is not an incident-management system, not a replacement for observability platforms, not an autonomous
decision-maker, and has not been independently security-audited or certified against any standard.
