# 0004: Deterministic analysis, and the response never invents data

> Classification: Decision Record. Status: accepted.

**Context.** The enrichment layer returned figures it could not know: ticket counts, "similar incidents in 30 days",
affected-user numbers and downstream services from a hard-coded map. For a product whose promise is evidence apart
from hypothesis, that is the most damaging kind of defect: plausible numbers that drive decisions.

**Decision.** Return only what is observed (scoring factors, recurrence in the window) or derived from the message
wording, label derived fields (`impact.basis`, response field descriptions) and remove the rest. No machine learning
or language model is used. Tests fail if invented fields return.

**Consequences.** Three keys in `historical_context`, `context` and `impact` changed (see the CHANGELOG). The score
stays a conservative lexical heuristic; documentation says so.
