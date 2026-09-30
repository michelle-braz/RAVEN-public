# 0001: One instance per customer, self-hosted

> Classification: Decision Record. Status: accepted.

**Context.** Customers send potentially confidential incident text. Multi-tenancy needs identity, per-tenant
storage, authorization on every object and operational isolation: a large build for an unproven market.

**Decision.** Deliver one container per customer with its own keys and data volume. No tenant concept in code.

**Consequences.** Isolation is physical, the attack surface stays small, and the recurrence window and limits can
live in process memory. Cost: operating many instances; no shared analytics. Revisit when customer count makes
operations the bottleneck ([FUTURE.md](../../FUTURE.md)).
