# Deployment

> Classification: Deployment

Supported topology: one container behind an HTTPS proxy, one instance per customer, Docker with the Compose
plugin. Files are in `deploy/`.

## What you need

A Linux host with Docker Compose v2, a DNS name pointing at it (ports 80 and 443 open), and about 300 MB of disk
for images plus the data volume.

## Install

```bash
cd deploy
cp .env.example .env
# edit .env: RAVEN_DOMAIN, RAVEN_API_KEY (>= 32 chars), customer keys (>= 24 chars)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"      # a suitable key
docker compose --env-file .env up -d --build
```

Check:

```bash
curl -fsS https://YOUR_DOMAIN/ready                                   # {"status":"ready",...}
curl -fsS -X POST https://YOUR_DOMAIN/v1/analyze -H "X-API-Key: <customer key>" \
  -H "Content-Type: application/json" -d '{"message":"service down after deploy","source":"application"}'
```

What the stack enforces: the app container has no published port (only the proxy reaches it), runs as an
unprivileged user with a read-only root filesystem, no capabilities and `no-new-privileges`, keeps data in the
named volume `raven_data`, and refuses to start on an unsafe configuration (`docker compose logs app` names the
problem).

Without a domain (evaluation only): set `RAVEN_DOMAIN=http://localhost` and call `http://localhost/...`. There is
no TLS in that mode; do not use it beyond a trial.

## Without Docker

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock && pip install --no-deps .
ENVIRONMENT=production RAVEN_API_KEY=... RAVEN_DATA_DIR=/var/lib/raven RAVEN_TRUSTED_PROXY_HOPS=1 \
  uvicorn raven.api.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-server-header --no-proxy-headers
```

Put a TLS-terminating proxy in front, run it under a service manager, and keep it to a single process.

## Verify a deployment package before shipping it

`deploy/smoke.sh` builds the image and, on a throwaway stack, checks the security posture (401/403/404 behaviour, no
docs, HSTS, non-root, read-only filesystem, unpublished app port), the product flow, persistence across a restart, a
backup, an erase and a restore, and the lockout through the proxy. It removes everything afterwards.

## Upgrade

1. Read the [CHANGELOG](../../CHANGELOG.md) for behaviour changes.
2. `deploy/backup.sh` (see the [runbook](../operations/runbook.md)).
3. `git pull` (or unpack the new release), then `docker compose --env-file .env up -d --build`.
4. Check `/ready` and `/ops/metrics`.

## Roll back

Data files are append-only JSONL and additive between minor versions, so the previous version reads them.
Tag images before upgrading (`RAVEN_IMAGE=raven:1.1.0`); to go back, set the previous tag and run
`docker compose up -d`. If a release ever changes the data format, its CHANGELOG entry says so and the backup
taken in step 2 is the way back (`deploy/restore.sh`).

## Environments

Use separate `.env` files, keys and volumes per environment; never reuse production keys elsewhere. Configuration
reference: [configuration](../system/configuration.md).
