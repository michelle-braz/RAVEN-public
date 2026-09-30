# Commercial readiness report

> Classification: Validation. Date: 2026-09-30. Branch `claude/gracious-brahmagupta-grfdm8`, version 1.1.0.
> Scope: this repository (API, Sentinel engine, Cyber Missions, deployment). The multi-user workspace is a
> separate product and is not assessed here.

## Verdict

**Ready for a first paying deployment of the software**, with owner-side items that are outside the code and are
required before charging: a customer agreement and DPA, trademark clearance, a decision on repository visibility,
and enabling private vulnerability reporting ([legal](../legal/README.md)).

## Gate

| Area | Result | Evidence |
|---|---|---|
| Product | Pass | Understandable in [overview](../product/overview.md); every capability marked implemented/validated/configurable/planned; limits of the score stated; response contains no invented data (`test_enrichment_honesty.py`) |
| Technical | Pass | Clean install from `requirements.lock`; container builds and runs; production refuses unsafe configuration |
| UX | Pass, with limits | API errors and fields documented; Missions: 33 missions end to end, 24 accessibility combinations clean. No manual screen-reader or user session |
| Security | Pass, not audited | 18 findings closed with mutation-verified tests ([review](../security/review-2026-09.md)); `pip-audit` clean; no known critical gap open |
| Privacy | Pass | Behaviour documented; export, retention, erasure tools tested in the container |
| Licensing | Pass, pending counsel confirmation | Proprietary notice, MIT history, full third-party inventory with texts, allow-list check |
| Operations | Pass | `/ready`, counters, logs, backup and restore rehearsed on a throwaway stack |
| Documentation | Pass | English library with index, classification of every document, link check in tests |
| Commercial honesty | Pass | Unsupported claims removed (invented figures, unused settings, "production-ready" ambiguity); planned items in [FUTURE.md](../../FUTURE.md) |

## Commands and results

| Command | Result |
|---|---|
| `python -m pytest tests -q` | 141 passed (76 before this work; 65 added), including the docs check |
| `node --test tests/missions/*.test.mjs` | 181 passed, 0 failed |
| `node tests/missions/e2e/flow.e2e.mjs` (33 missions, 390 px) | OK, 3,175 XP, progress persisted |
| `node tests/missions/e2e/a11y.e2e.mjs` | OK: 6 routes × desktop/mobile × light/dark, no axe A/AA violations, no overflow, no console errors (two real defects found and fixed) |
| `pip-audit -r requirements.lock` | No known vulnerabilities (2026-09-30) |
| `python tools/license_inventory.py --check` | OK: 17 runtime and 5 test-only packages, all on the allow-list |
| `python tools/export_openapi.py --check` | Contract current |
| `deploy/smoke.sh` | SMOKE OK: build; 401/403/404 behaviour; docs off; HSTS, nosniff, X-Frame-Options; app port unpublished; non-root; read-only filesystem; analysis flow; persistence across restart; backup, wipe and restore; export, dry-run purge, erasure and key generation in the container; lockout through the proxy with spoofed `X-Forwarded-For` |
| Mutation check of 9 protections (key comparison, surrogate guard, atomic append, lockout, production validation, operator gate, body cap, proxy address, tolerant reads) | 9 of 9 caught by a failing test |

Measured capacity: [architecture](../system/architecture.md#capacity-envelope-measured-single-process).
Screenshots: [`screenshots/`](screenshots/).

## Not verified

Independent penetration test; behaviour under real customer data; screen-reader and user testing; Windows
hosting; the GitHub Actions workflow itself (written to mirror the commands above, first run happens on the PR).
