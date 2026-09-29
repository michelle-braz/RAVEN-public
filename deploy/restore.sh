#!/usr/bin/env bash
# Restore the data volume from a backup made by backup.sh. Replaces the current contents.
#   deploy/restore.sh <backup-folder> --yes
set -euo pipefail
cd "$(dirname "$0")"
SRC="${1:?usage: restore.sh <backup-folder> --yes}"
[ "${2:-}" = "--yes" ] || { echo "This replaces the current data. Re-run with --yes." >&2; exit 2; }
SRC="$(cd "$SRC" && pwd)"
IMAGE="${RAVEN_IMAGE:-raven:local}"
VOLUME="${RAVEN_DATA_VOLUME:-raven_data}"
ENV_FILE="${ENV_FILE:-.env}"; export RAVEN_ENV_FILE="$ENV_FILE"
( cd "$SRC" && sha256sum -c SHA256SUMS )
docker compose --env-file "$ENV_FILE" stop app 2>/dev/null || true
docker run --rm --user 0 --entrypoint sh -v "$VOLUME":/data -v "$SRC":/in:ro "$IMAGE" \
  -c 'find /data -mindepth 1 -delete && tar xzf /in/raven-data.tar.gz -C /data && chown -R 10001:10001 /data && chmod 700 /data'
docker compose --env-file "$ENV_FILE" up -d app 2>/dev/null || true
echo "Restored from $SRC"
