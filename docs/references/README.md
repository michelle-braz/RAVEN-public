# References

> Classification: Reference. Sources checked on 2026-09-29; used as benchmarks, not as claims of conformance.

| Topic | Source | Used for |
|---|---|---|
| API security risks | [OWASP API Security Top 10, 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) | Control mapping in the [security model](../security/security-model.md) |
| Application security checklist | [OWASP ASVS 5.0.0 (May 2025)](https://github.com/OWASP/ASVS) | Review checklist; no level claimed |
| REST hardening | [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) | `Cache-Control: no-store`, `frame-ancestors 'none'`, `X-Frame-Options`, status codes |
| Containers | [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) | Non-root user, dropped capabilities, read-only filesystem |
| Secure development | [NIST SP 800-218 SSDF v1.1](https://csrc.nist.gov/pubs/sp/800/218/final) | Dependency audit, tests, reproducible builds |
| Privacy by design and security of processing | [GDPR Articles 25 and 32](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) | Data minimisation, defaults, export/erasure tooling; no compliance claim |
| Accessibility | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) (checked with axe-core against the 2.0 and 2.1 A/AA rule tags) | Cyber Missions checks |
| Licence metadata | [PEP 639](https://peps.python.org/pep-0639/) | SPDX expression in `pyproject.toml` |
