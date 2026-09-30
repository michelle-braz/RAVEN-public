# Changelog

## 1.1.0 — commercial readiness

### Changed (behaviour you may notice)
* `POST /v1/analyze` no longer returns invented figures. Removed: `context.related_tickets`,
  `historical_context.similar_incidents_last_30d`, `impact.affected_users`. Renamed: `historical_context.known_resolution`
  → `suggested_playbook`. New: `historical_context.occurrences_in_active_window`, `impact.basis`.
  `context.affected_services` lists only the detected object. "configuration change" wording now counts as a change.
* `/beta/business-proof` and `/ops/metrics` need the operator key.
* Production (`ENVIRONMENT=production`) refuses weak keys, `CORS_ORIGINS=*` and missing keys; docs and OpenAPI are off;
  CORS is closed unless origins are listed.
* Ten failed key attempts a minute lock a client address out (429). Request bodies are capped at 256 KiB.
* Malformed `BETA_KEYS_JSON` or `SENTINEL_*` values stop startup instead of being ignored. `SENTINEL_*` now apply.
* `/status` no longer reports the environment. Module entry point binds `127.0.0.1`.
* Removed the unauthenticated standalone Sentinel app and the unused `SENTINEL_WEBHOOK_URL`.
* `uvicorn[standard]` → `uvicorn` (six unused packages dropped).

### Added
* `/ready`, request ids, access log, `/ops/metrics`; `RAVEN_RATE_LIMIT_PER_MINUTE`, `RAVEN_TRUSTED_PROXY_HOPS`,
  `RAVEN_MAX_BODY_BYTES`, `RAVEN_ENABLE_DOCS`.
* `raven-admin`: stats, export, retention, erasure, key generation.
* Docker image, Compose with HTTPS proxy, backup and restore scripts, end-to-end deployment check.
* Documentation library, generated OpenAPI contract and third-party inventory, CI.

### Fixed
* Revoked beta keys kept working until restart. 500 errors on malformed `/evaluate` bodies and on JSON with unpaired
  surrogates. Data files readable by other users; one corrupt line broke summaries.
* Cyber Missions: progress bar and backup fields lacked accessible names.

### Licence
* Proprietary, all rights reserved (earlier versions remain MIT).

## 1.0.0
Initial public release (MIT).
