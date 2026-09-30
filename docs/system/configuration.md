# Configuration

> Classification: Technical

All configuration is by environment variable, read once at start. `.env.example` (development) and
`deploy/.env.example` (production) are templates. Never commit real values.

## Access

| Variable | Default | Production rule | Effect |
|---|---|---|---|
| `RAVEN_API_KEY` | none | **required, at least 32 characters** | Operator key: full access; the only key for `/ops/metrics` and `/beta/business-proof` |
| `PRO_API_KEYS` | empty | each at least 24 characters | Customer keys, full analysis access, no daily quota |
| `FREE_API_KEYS` | empty | each at least 24 characters | Customer keys with a quota of 100 requests per day |
| `BETA_KEYS_JSON` | empty | each key at least 24 characters | Named keys (`{"key": {"name","status","created_at"}}`); malformed value stops startup. Generate with `python -m raven.admin keys new "Name"`; revoke by setting `"status": "revoked"` and restarting |

With no `RAVEN_API_KEY` and no other key configured, every key is rejected (fail closed).

## Runtime

| Variable | Default | Effect |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` or `production` (anything else stops startup). Production enforces the rules in this table, disables `/docs` and `/openapi.json`, and sends HSTS |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Bind address for `python -m raven.api.main`. The container binds `0.0.0.0` and is reached only through the proxy |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | dev: localhost; production: none | Comma-separated browser origins allowed to call the API. `*` is refused in production |
| `RAVEN_DATA_DIR` | `data` | Where the JSONL files live. Production: must exist and be writable |
| `RAVEN_ENABLE_DOCS` | dev on, production off | Serve interactive docs and the OpenAPI document |
| `RAVEN_MAX_BODY_BYTES` | `262144` | Largest accepted request body (minimum 1,024) |
| `RAVEN_RATE_LIMIT_PER_MINUTE` | `30` | Analyses per minute per client address on `/v1/analyze` (1 to 100,000) |
| `RAVEN_TRUSTED_PROXY_HOPS` | `0` | Number of reverse proxies that append to `X-Forwarded-For`. `0` ignores the header (cannot be spoofed); the shipped compose file sets `1` |

## Sentinel pipeline

| Variable | Default | Effect |
|---|---|---|
| `SENTINEL_BUFFER_MAXSIZE` | `256` | In-flight analyses before 429 |
| `SENTINEL_BUFFER_POLICY` | `DROP_NEWEST` | `DROP_NEWEST` or `BLOCK` |
| `SENTINEL_WINDOW_MAXLEN` | `5000` | Entries kept in the recurrence window |
| `SENTINEL_WINDOW_TTL` | `3600` | Seconds an entry stays in the window |
| `SENTINEL_DEBUG`, `SENTINEL_STRICT_MODE` | `0` | Engine diagnostics and runtime contract guard |

Invalid numeric values stop startup with a clear message; nothing silently falls back.

## Compose-only (`deploy/.env`)

`RAVEN_DOMAIN` (public host name; `http://localhost` for local evaluation), `RAVEN_IMAGE`, `RAVEN_DATA_VOLUME`,
`RAVEN_HTTP_PORT`, `RAVEN_HTTPS_PORT`, `RAVEN_ENV_FILE`.
