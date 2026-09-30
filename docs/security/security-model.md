# Security model

> Classification: Security

RAVEN has not been independently audited and claims no certification or ASVS level. This document states what
was built, how it was verified in this repository, and what remains the operator's responsibility. Benchmarks used:
[OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) and
[OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS) as a checklist, [NIST SP 800-218 (SSDF)](https://csrc.nist.gov/pubs/sp/800/218/final)
for the build process ([references](../references/README.md)).

## Assets and boundaries

| Asset | Where | Sensitivity |
|---|---|---|
| Customer incident text (in requests and responses) | In transit, and in process memory as tokens for the recurrence window | Potentially confidential |
| Decision records and approved resolutions | JSONL files in the data volume | Potentially confidential; may name people (`validated_by`) |
| API keys | Environment variables of the container | Secret |

Trust boundary: the network edge (TLS proxy) and the API key. There is no per-user identity: a key identifies a
customer integration, not a person. The service makes no outbound calls.

## Controls, mapped to OWASP API Security Top 10 (2023)

| Risk | What RAVEN does | Verified by |
|---|---|---|
| API1 Broken object level authorization | Not applicable by design: one instance per customer, no object ids that select other tenants' data | Architecture ([ADR-0001](../decisions/0001-single-tenant-self-hosted.md)) |
| API2 Broken authentication | Constant-time key comparison; keys never logged; missing/invalid keys rejected before any parsing; ten failed attempts per minute per client address lock that address out; production refuses keys under 24 characters (operator key 32); revoked beta keys stop working immediately | `test_security_hardening.py` (auth, lockout, revocation, log redaction, proxy address) |
| API3 Broken object property level authorization | Response fields are an explicit model; request models bound every field and reject unknown enum values | `test_security_hardening.py`, `test_v1_analyze_validation.py` |
| API4 Unrestricted resource consumption | Body cap (256 KiB; 413, and 411 for chunked bodies), per-field length limits, per-client rate limit, daily quota for free keys, bounded pipeline buffer (429), bounded limiter memory | `test_security_hardening.py` |
| API5 Broken function level authorization | Operator-only `/ops/metrics` and `/beta/business-proof`; all other routes require a key; deny by default | `test_operator_endpoints_reject_customer_keys`, `test_beta_endpoints_require_a_key` |
| API6 Unrestricted access to sensitive business flows | Rate limit and quota on analysis; decisions only recorded on explicit request | as API4 |
| API7 SSRF | No endpoint fetches a URL; the webhook channel is not wired into the API | Code inspection |
| API8 Security misconfiguration | Production refuses to start with a weak or missing key, `*` CORS or an unwritable data directory; docs and OpenAPI off in production; HSTS; CSP and `nosniff` on every response; closed CORS by default; container runs as non-root, read-only filesystem, all capabilities dropped, no published app port | `test_security_hardening.py`, `deploy/smoke.sh` |
| API9 Improper inventory management | One versioned API (`/v1`), contract generated to `docs/api/openapi.json` and checked in CI; no debug endpoints | CI step |
| API10 Unsafe consumption of APIs | No third-party API is consumed | Code inspection |

## Other controls

* **Injection / deserialization:** no SQL, shell or template evaluation; JSON only; data files are written through
  typed models. Path traversal is not reachable (no user-controlled file paths).
* **XSS:** the API returns JSON; Cyber Missions builds its DOM with `textContent` only and ships a CSP of
  `default-src 'self'`, no inline script, no framing.
* **CSRF:** no cookies or ambient credentials; authentication is a header.
* **Input robustness:** JSON containing unpaired UTF-16 surrogates (valid JSON, unencodable) is refused with 422;
  before this control they produced 500s on four endpoints.
* **Logging:** access log carries method, path (control characters escaped), status, duration, request id and
  client address only. Keys, bodies and query strings are never logged; the error log holds the call stack and
  exception type, not its message.
* **Supply chain:** exact versions in `requirements.lock`; `pip-audit` reported no known vulnerabilities on
  2026-09-29 and runs in CI; licence allow-list check; Dependabot configured; plain `uvicorn` instead of
  `uvicorn[standard]` removed six unused packages; the image is small (slim base, one process).

## Residual risks the operator should know

| Risk | Mitigation available |
|---|---|
| Keys are shared secrets in environment variables; there is no per-user identity or audit of who did what | Issue one key per customer integration; rotate by editing the environment and restarting ([runbook](../operations/runbook.md)) |
| Data files are not encrypted by the application | Use an encrypted volume or disk; encrypt backups |
| Limits and lockout are per process and reset on restart | Run one process; front with a network-level limit if exposed to the internet at scale |
| Lockout is per client address: many users behind one address share it | Set `RAVEN_TRUSTED_PROXY_HOPS` correctly; an attacker behind a shared address can lock it out |
| No independent penetration test, no formal threat-model review by a third party | Commission one before regulated use |
| Interactive docs in development load Swagger UI assets from a public CDN | Off in production |

## Reporting a vulnerability

See [SECURITY.md](../../SECURITY.md).
