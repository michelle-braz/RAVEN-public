# Operations runbook

> Classification: Operations. Commands assume `cd deploy` on the host and a Compose project using `.env`.

## Is it alive, and is it healthy?

| Question | Check | Healthy |
|---|---|---|
| Alive | `GET /health` | 200 |
| Able to serve | `GET /ready` | 200 (503 means the pipeline is down or the data directory is not writable) |
| Container health | `docker compose ps` | app `healthy` |
| Errors rising | `GET /ops/metrics` with the operator key: `responses_5xx`, `storage_failures` | flat at 0 |
| Abuse or misuse | same: `auth_failures`, `rate_limited`, `rejected_body` | low and steady |
| Load | same: `requests_total`, `analyses`, `pipeline_buffer.utilization` | buffer well below 1.0 |

Counters restart at zero when the process restarts; scrape `/ops/metrics` (JSON) every minute from your monitoring
and alert on the changes. Suggested alerts: `/ready` not 200 for two minutes; any increase of `responses_5xx` or
`storage_failures`; `pipeline_buffer.utilization` above 0.8; a sudden rise in `auth_failures`.

## Logs

`docker compose logs -f app`. One line per request: `rid`, method, path, status, milliseconds, client address.
No bodies, queries or keys. To follow one failure: take `request_id` from the 500 response and grep for `rid=`.
The proxy writes its own JSON access log (`docker compose logs proxy`). Set retention in Docker's logging driver.

## Backup and restore

```bash
./backup.sh /secure/path/2026-10-01          # tar of the data volume + SHA256SUMS
./restore.sh /secure/path/2026-10-01 --yes   # verifies the checksum, replaces the data, restarts the app
```

Back up before every upgrade and on a schedule (data is small and append-only). The archive contains customer
text: encrypt it and keep a copy off the server. **Rehearse a restore** on a scratch host before relying on it;
`deploy/smoke.sh` does a backup, erase and restore on a throwaway stack.

## Retention and erasure

See [data handling](../privacy/data-handling.md). To rewrite files safely, stop the app, run the command in a one-off
container, start the app:

```bash
docker compose stop app
docker compose run --rm --no-deps app python -m raven.admin purge --before 2026-01-01 --yes
docker compose up -d app
```

## Keys

* New customer key: `docker compose run --rm --no-deps app python -m raven.admin keys new "Customer"` prints the key
  once and a `BETA_KEYS_JSON` entry; merge the entry into `.env` and `docker compose up -d app`. Or add a long random
  value to `PRO_API_KEYS`.
* Revoke: set the entry's `"status": "revoked"` (or delete the key from `PRO_API_KEYS`) and restart. The key stops
  working on restart; there is no cache.
* Rotate the operator key: change `RAVEN_API_KEY`, restart, update your monitoring.
* Suspected leak: rotate that key, review `auth_failures` and the access log around the suspected time.

## Incident response (short form)

1. Confirm scope with `/ready`, `/ops/metrics`, logs.
2. Contain: revoke or rotate affected keys; if needed stop the proxy (`docker compose stop proxy`).
3. Preserve: copy logs and take a backup before changing anything.
4. Recover: fix, redeploy, verify with the checks above.
5. Notify: customers and authorities as your contracts and law require (see [legal](../legal/README.md)).
6. Record what happened and what changed.

## Common situations

| Symptom | Likely cause and action |
|---|---|
| App will not start | `docker compose logs app`: it lists every unsafe setting; fix `.env` |
| `/ready` 503, `data_dir_writable` false | Volume full or permissions; free space or fix the volume; the app runs as uid 10001 |
| Clients get 429 | Per-client limit (`RAVEN_RATE_LIMIT_PER_MINUTE`), free-tier quota, lockout after failed keys, or buffer full |
| Every client seems to be one address | `RAVEN_TRUSTED_PROXY_HOPS` is 0 behind a proxy; set it to the number of proxies |
| Recurrence context missing after a restart | By design: the window is in memory |
| Summary endpoints slow | Data files large; run the retention command |

## Capacity

See [architecture](../system/architecture.md#capacity-envelope-measured-single-process). One process per customer.

## Updating dependencies

Dependabot proposes updates weekly. For each: run the tests, `tools/update_lock.sh`,
`python tools/license_inventory.py --write`, `python tools/export_openapi.py`, and `deploy/smoke.sh`.
