# RAVEN documentation

RAVEN turns a raw incident signal into structured context for a human analyst: evidence kept apart from
hypothesis, a deterministic risk score, recurrence, and suggested next steps. The analyst decides.
It is delivered as a self-hosted service (one container, one instance per customer) with an authenticated
REST API, plus **Cyber Missions**, a static study application built on the same investigation structure.

**Who it is for:** SRE, NOC, QA, support and engineering teams that want incident context before
they start investigating, and the engineers who integrate that context into their own tools.

**Start here:** [Product overview](product/overview.md) → [API reference](api/reference.md) →
[Deployment](deployment/deployment.md).

## Library map

| Document | Class | What it answers |
|---|---|---|
| [product/overview.md](product/overview.md) | Product | What RAVEN is, what it does, what it does not do; status of every capability |
| [product/cyber-missions.md](product/cyber-missions.md) | Product | The daily study application |
| [product/foxhuman-workspace-design.md](product/foxhuman-workspace-design.md) | Product (design only) | Design of the workspace layer built on RAVEN; not part of this repository |
| [ux/analyst-experience.md](ux/analyst-experience.md) | UX | How the human-first principle shows up in the API and Missions; accessibility results |
| [system/architecture.md](system/architecture.md) | Technical / Architecture | Components, request flow, state, failure behaviour, measured capacity |
| [system/configuration.md](system/configuration.md) | Technical | Every environment variable |
| [api/reference.md](api/reference.md) | Technical | Endpoints, authentication, limits, errors, response semantics |
| [api/openapi.json](api/openapi.json) | Technical | Machine-readable contract (generated) |
| [security/security-model.md](security/security-model.md) | Security | Threats, controls, tests, residual risk |
| [security/review-2026-09.md](security/review-2026-09.md) | Security | Findings of the pre-commercial review and how each was closed |
| [privacy/data-handling.md](privacy/data-handling.md) | Privacy | What is stored, where, for how long; export, erasure; what the operator must decide |
| [deployment/deployment.md](deployment/deployment.md) | Deployment | Install, configure, upgrade, roll back |
| [operations/runbook.md](operations/runbook.md) | Operations | Monitoring, backup and restore, retention, key rotation, incidents |
| [legal/README.md](legal/README.md) | Legal | What the software provides versus what counsel must supply |
| [licensing/LICENSING.md](licensing/LICENSING.md) | Licensing | Ownership, licence history, third-party obligations |
| [licensing/THIRD_PARTY.md](licensing/THIRD_PARTY.md) | Licensing | Generated inventory of every dependency and its licence |
| [validation/readiness-report.md](validation/readiness-report.md) | Validation | Evidence for the commercial readiness gate |
| [decisions/](decisions/README.md) | Decision records | Why the system is shaped this way |
| [references/README.md](references/README.md) | Reference | External standards this work was measured against |

Also at the repository root: [README](../README.md), [CHANGELOG](../CHANGELOG.md), [FUTURE](../FUTURE.md),
[SECURITY](../SECURITY.md), [CONTRIBUTING](../CONTRIBUTING.md), [LICENSE](../LICENSE).

All documentation is in English. The Cyber Missions interface and its mission content are in Brazilian Portuguese
by design: they are product content, not documentation.
