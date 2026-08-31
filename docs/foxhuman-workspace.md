# FOXHUMAN Operational Workspace — the design

> Translation. Primary version: [`foxhuman-workspace.pt.md`](foxhuman-workspace.pt.md).
>
> This document describes the **design** of the workspace layer FOXHUMAN builds
> on top of RAVEN. The implementation is not part of this public edition. Every
> example here is synthetic.

## The problem

Research with QA professionals showed the bottleneck is not a missing tool. It
is the cost of rebuilding context:

- hunting for evidence across several tools;
- repeating a check somebody else already ran;
- re-running a test because no record exists of what was already tested;
- completing a ticket that came back from development;
- explaining the same context again to the next person.

When a ticket comes back from development, the reasons repeat: it cannot be
reproduced, logs or evidence are missing, the steps are unclear, the expected
result was not stated, environment and version are missing, and it is unclear
what was already tested.

That is QA talking, but it describes the work of SRE, support and engineering
just as well: gather context, separate evidence from hypothesis, see what is
missing, decide, and do not lose what was learned.

## The hypothesis

An operational workspace that turns fragmented information into actionable
context, with **one base** for different technical professionals.

**Permanent rule:** do not segment the product by profession. Segment the
experience by the work that profession needs to execute.

## The cycle

```
a signal or task arrives
   → context is gathered
   → evidence is organized
   → gaps are identified
   → the next action is presented
   → a human decides
   → history is preserved
```

One entity travels the cycle: the **Case**. Its stage is derived from what the
case holds, never assigned, so an invalid state cannot exist.

Exactly one transition depends on the kind of work: leaving "gaps identified"
for "next action ready". The rest of the cycle is identical for every role.

## Work profiles

A profile declares four things: which signals start the work, which gaps count,
which of them block a handoff, and how the result is framed when it leaves.

| Profile | Intake | Output |
| --- | --- | --- |
| Reproduce and hand off | bug, ticket | context ready for development |
| Stabilize and prioritize | alert, metric | priority and next action |
| Assist and route | report, ticket | correct routing |
| Investigate and fix | incident, ticket | technical investigation |

The same case evaluated under two profiles produces different gap sets and
different positions in the cycle — never different cycles. Adding a fifth kind
of work is adding a declaration, not branching the product.

## What RAVEN contributes

Everything below already exists in RAVEN and is reused unchanged:

| Piece | Contribution |
| --- | --- |
| Sentinel pipeline | risk score, severity, stable incident identifier, recurrence detection |
| Enrichment layer | event type, monitored object, priority, evidence, hypothesis, next steps, impact |
| Validated memory | analyst-approved resolutions |
| Impact log | every decision taken counts toward decisions influenced |

The workspace layer **re-scores nothing**. It turns what RAVEN returns into work
that is ready to move.

## Cause classification

RAVEN's `event_type` is an SRE vocabulary. The operator triages by a different
question: who should look at this?

| Category | Derives from |
| --- | --- |
| Security suspicion | suspicious activity |
| Configuration error | deployment-related failure, change correlation, config/secret terms |
| Infra / network | infrastructure or network origin, latency with no deployment, timeout or saturation |
| Backend bug | error rate increase, unavailability, 5xx, exception, traceback |
| Incorrect usage | a low-risk signal with no error class in any rule above |

The order carries decisions. Security is never folded into another bucket. A 500
right after a rollout is a change story before it is a bug. "Incorrect usage" —
the only category that means "nothing is broken" — comes last so it never
swallows a real defect.

None of this alters the `risk_score` or the severity RAVEN produced.

## Gaps

Each reason work comes back becomes a check. A gap also records **how** it was
closed: by the analysis, on its own, or by a person who had to fill it in. That
distinction is the product's argument, so it is data rather than prose.

When a required item is missing, the handoff is **refused** and names what is
missing — instead of letting it leave incomplete, which is the number one cause
of rework.

## Command bar

One line in, one answer out. Risk is classified in auditable code, never by a
model:

- reading runs immediately;
- a reversible write runs and offers undo;
- a destructive action runs nothing until the person confirms.

The parser is deterministic and requires no language model. One can be added in
front of it to widen what it understands; never to decide whether an action is
safe.

## Honesty about integrations

A connector that does not exist is never presented as connected. The real state
of each connection stays visible, with the reason written out when it is dim.

## Limitations

- This document describes a design. The implementation is not in this public
  edition.
- Classification and gaps are deterministic heuristics, not learned models. The
  decision stays with the person.
- Hypotheses, next steps and categories require human verification.
- Every example is synthetic. No real operational data appears here.
