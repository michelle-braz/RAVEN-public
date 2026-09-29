#!/usr/bin/env bash
# Back up the RAVEN data volume (decision records, validated memory, telemetry) with a checksum.
#   deploy/backup.sh [destination-folder]
# The archive contains customer-supplied text: store it encrypted and off the server (docs/operations/runbook.md).
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${RAVEN_IMAGE:-raven:local}"
VOLUME="${RAVEN_DATA_VOLUME:-raven_data}"
OUT="${1:-./backups/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"; chmod 700 "$OUT"; OUT="$(cd "$OUT" && pwd)"
docker run --rm --user 0 --entrypoint tar -v "$VOLUME":/data:ro -v "$OUT":/out "$IMAGE" czf /out/raven-data.tar.gz -C /data .
( cd "$OUT" && sha256sum raven-data.tar.gz > SHA256SUMS && chmod 600 raven-data.tar.gz SHA256SUMS )
echo "Backup written to $OUT"; ls -l "$OUT"
