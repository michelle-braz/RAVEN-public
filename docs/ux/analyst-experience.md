# Analyst experience

> Classification: UX

RAVEN's design rule is **complexity behind, simplicity in front**. This repository ships an API and the Cyber
Missions app; it does not ship an analyst workspace UI (that layer is described in the
[workspace design](../product/foxhuman-workspace-design.md) and is a separate product). This document therefore
covers the experience of the API contract and of Missions.

## How the human-first principle shows in the API

| Principle | Where it is enforced |
|---|---|
| Evidence and hypothesis never mix | Separate `evidence` (observed scoring factors) and `hypothesis` (heuristic, to verify) fields |
| The system does not present guesses as facts | No invented counts, topology or history in the response; each field's basis is in the [API reference](../api/reference.md) and in `openapi.json`; `impact.basis` says the label is derived |
| The next action is clear | `recommended_action` (ignore, group_as_noise, monitor, investigate, escalate) and ordered `recommended_steps` |
| The analyst can see why | `explain.factors` lists each factor with weight and detail |
| The human decides and history is only kept with approval | `/beta/validate-resolution` stores context only when `memory_write_approved` is true |
| Errors are actionable and never leak internals | One envelope `{"error","code"}` for every failure; 500s return only a request id; validation errors say which rule failed |
| Status is unambiguous | Distinct codes: 401 missing key, 403 invalid key or not permitted, 413/411 body, 422 validation, 429 limit (with `Retry-After` on lockout), 503 storage |

## Integrator flow

1. Send the signal to `POST /v1/analyze`.
2. Show `evidence`, `hypothesis`, `recommended_action` and `recommended_steps` in that order, visibly separated.
3. Let the analyst decide.
4. Send `POST /beta/validate-resolution` with the `incident_id` and `request_id` from step 1, and set
   `memory_write_approved` only when the analyst approves keeping the resolution.

## Cyber Missions

Flow: open → today's mission → ticket → situation → evidence → question → hypothesis (up to three hints)
→ feedback → explain in own words → next mission. Empty states, errors and confirmations are in the
interface's language (pt-BR).

Validated (see [validation report](../validation/readiness-report.md)):

* all 33 missions completed end to end on a 390 px viewport, with progress persisted;
* six routes × desktop and mobile × light and dark (24 combinations): no WCAG 2.x A/AA violations reported by
  axe-core, no horizontal scroll, no console errors;
* the check found two real defects, fixed: the progress bar had no accessible name and the two backup text
  areas had no label.

Screenshots: [`docs/validation/screenshots`](../validation/screenshots/).

Limits: automated checks cover a fraction of accessibility; no manual screen-reader or usability session with
real users has been run.
