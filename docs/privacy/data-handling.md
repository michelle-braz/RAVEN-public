# Data handling and privacy

> Classification: Privacy. This describes what the software actually does. It is not legal advice and makes no
> claim of compliance with GDPR or any other regulation; see [legal](../legal/README.md).

## What RAVEN processes

RAVEN analyses text the customer sends. That text may contain confidential or personal data (host names, user
names, IP addresses); RAVEN does not detect or redact it. **Data minimisation is the sender's job**: send only
what the analysis needs.

| Data | Where it lives | How long | Contains customer text? |
|---|---|---|---|
| Analysed message | In the request and the response only. Not written to disk, not logged | Not retained. Its normalized tokens stay in process memory for the recurrence window (default 1 hour, max 5,000 entries) and vanish on restart | Tokens only, in memory |
| Analysis telemetry (`analyze_calls.jsonl`): time, incident id, request id | Data volume | Until purged | No |
| Decision impacts (`decision_impacts.jsonl`): incident and request ids, decision, `action_taken`, `comments`, `resolution_text`, confidence, minutes saved | Data volume | Until purged | Analyst-written free text |
| Validated incidents (`validated_incidents.jsonl`), **only if the analyst approves**: normalized message text, tokens, resolution text, `validated_by` | Data volume | Until purged | Yes, and possibly a person's name |
| Access log: time, method, path, status, duration, request id, client address | Container stdout | Set by the operator's log retention | No (no body, no query, no keys). The client address is personal data under some regimes |
| Backups | Wherever the operator puts them | Set by the operator | Yes |

Nothing is sent to any third party: the service makes no outbound network calls and has no analytics.
Cyber Missions stores progress only in the learner's browser and collects nothing.

## Separation between customers

One instance, one data volume and one set of keys per customer. There is no shared database and no multi-tenant
code path, so one customer's data cannot be reached through another's key. Do not point two customers at one instance.

## Access

Anyone holding a valid key can call the API; the operator key additionally reads counters and vendor metrics. There
is no per-person identity. Data files are readable only by the service user (`0600`, directory `0700`). Access to
the host, the volume and backups is the operator's to control.

## Export, retention and erasure (provided as software)

```bash
docker compose exec app python -m raven.admin stats                       # counts and date ranges
docker compose exec app python -m raven.admin export --out /data/export.json
docker compose exec app python -m raven.admin purge --before 2026-01-01           # dry run
docker compose exec app python -m raven.admin purge --before 2026-01-01 --yes     # retention
docker compose exec app python -m raven.admin delete --incident-id LOW-B0F578 --yes   # erase one incident
```

`purge` and `delete` are dry runs unless `--yes` is given, rewrite files atomically and keep `0600`. Stop the
service first (the runbook shows how) so no append is lost during a rewrite. Erasure covers the live files; copies
already in backups are erased only when those backups expire or are rewritten.

## Encryption

In transit: TLS at the proxy (automatic certificates), HSTS in production. At rest: **not provided by the
application**. Use an encrypted disk or volume and encrypt backups.

## Defaults

Closed CORS, no docs in production, no telemetry, no outbound calls, no memory write without explicit approval
(`memory_write_approved`).

## What needs the operator or counsel

| Software provides | Operator must configure | Needs legal or business policy |
|---|---|---|
| Export, retention and erasure tools; no third-party sharing; minimal logs; private file permissions; explicit approval before storing a resolution | Disk and backup encryption; log retention; a retention schedule that is actually run; access to the host; sending only necessary data | Privacy notice; data processing agreement with each customer; legal basis and roles (controller or processor); international transfer position; response procedure for data-subject requests and breaches |
