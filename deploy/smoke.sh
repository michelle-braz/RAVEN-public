#!/usr/bin/env bash
# End-to-end deployment check on a throwaway stack: build → start behind the proxy → exercise the API →
# restart (persistence) → backup → erase → restore → tear down. Needs Docker; touches nothing else.
#   deploy/smoke.sh
# Behind a TLS-inspecting proxy set RAVEN_BUILD_CACERT=/path/to/ca.crt so the build can reach PyPI.
set -euo pipefail
cd "$(dirname "$0")"
export RAVEN_IMAGE="raven:smoke" RAVEN_DATA_VOLUME="raven_smoke_data" RAVEN_HTTP_PORT="${RAVEN_HTTP_PORT:-18080}" RAVEN_HTTPS_PORT="${RAVEN_HTTPS_PORT:-18443}"
export COMPOSE_PROJECT_NAME=ravensmoke
WORK="$(mktemp -d)"
ENV_FILE="$WORK/.env"
OPERATOR="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
CUSTOMER="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
cat > "$ENV_FILE" <<EOT
RAVEN_DOMAIN=http://localhost
RAVEN_API_KEY=$OPERATOR
PRO_API_KEYS=$CUSTOMER
EOT
export RAVEN_ENV_FILE="$ENV_FILE"
DC=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml)
BASE="http://localhost:$RAVEN_HTTP_PORT"   # the proxy routes by host name
fail() { echo "SMOKE FAILED: $*" >&2; "${DC[@]}" logs --tail 40 >&2 || true; exit 1; }
cleanup() { "${DC[@]}" down -v >/dev/null 2>&1 || true; docker volume rm -f "$RAVEN_DATA_VOLUME" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
expect() { local want="$1"; shift; local got; got="$(code "$@")"; [ "$got" = "$want" ] || fail "expected HTTP $want, got $got for: $*"; echo "ok  $want  ${*: -1}"; }

echo "== build"
if [ -n "${RAVEN_BUILD_CACERT:-}" ]; then
  docker build --secret id=cacert,src="$RAVEN_BUILD_CACERT" -f Dockerfile -t "$RAVEN_IMAGE" ..
else
  docker build -f Dockerfile -t "$RAVEN_IMAGE" ..
fi
echo "== start"
"${DC[@]}" up -d
for _ in $(seq 1 60); do [ "$(code "$BASE/ready")" = "200" ] && break; sleep 1; done
expect 200 "$BASE/health"
expect 200 "$BASE/ready"

echo "== security posture in the container"
expect 401 -X POST "$BASE/v1/analyze"
expect 403 -X POST -H "X-API-Key: not-the-key" "$BASE/v1/analyze"
expect 404 "$BASE/docs"
expect 404 "$BASE/openapi.json"
expect 403 -H "X-API-Key: $CUSTOMER" "$BASE/ops/metrics"
expect 200 -H "X-API-Key: $OPERATOR" "$BASE/ops/metrics"
curl -sI "$BASE/health" | grep -qi '^strict-transport-security:' || fail "HSTS header missing"
curl -sI "$BASE/health" | grep -qi '^x-content-type-options: nosniff' || fail "nosniff header missing"
curl -sI "$BASE/health" | grep -qi '^server: caddy' && echo "note: proxy announces its name (harmless)"
published="$("${DC[@]}" port app 8000 2>/dev/null || true)"
case "$published" in ""|*":0") ;; *) fail "app port must not be published (got $published)";; esac
[ "$("${DC[@]}" exec -T app id -u)" = "10001" ] || fail "app must not run as root"
"${DC[@]}" exec -T app sh -c 'touch /app/x 2>/dev/null' && fail "root filesystem must be read-only"

echo "== product flow"
ANALYSIS="$(curl -s -X POST "$BASE/v1/analyze" -H "X-API-Key: $CUSTOMER" -H 'Content-Type: application/json' \
  -d '{"message":"Checkout API returned HTTP 503 after a configuration change in the synthetic staging environment","source":"application"}')"
INCIDENT="$(printf '%s' "$ANALYSIS" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["evidence"] and d["hypothesis"] and d["recommended_steps"]; print(d["incident_id"])')"
REQUEST="$(printf '%s' "$ANALYSIS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request_id"])')"
expect 201 -X POST "$BASE/beta/validate-resolution" -H "X-API-Key: $CUSTOMER" -H 'Content-Type: application/json' \
  -d "{\"incident_id\":\"$INCIDENT\",\"request_id\":\"$REQUEST\",\"decision_taken\":\"INVESTIGATE\",\"action_taken\":\"reviewed\",\"confidence\":4,\"replaced_manual_process\":false,\"time_saved_minutes\":5,\"resolution_text\":\"restored previous configuration\",\"memory_write_approved\":true,\"event_type\":\"deployment_related_failure\",\"source\":\"application\",\"message_normalized\":\"checkout api http error after configuration change\",\"signature\":\"sig-smoke\"}"
expect 200 "$BASE/missions/"

echo "== persistence across restart"
"${DC[@]}" restart app >/dev/null
for _ in $(seq 1 60); do [ "$(code "$BASE/ready")" = "200" ] && break; sleep 1; done
"${DC[@]}" exec -T app python -m raven.admin stats | grep -q 'validated_incidents.jsonl: 1 records' || fail "record lost after restart"

echo "== backup, erase, restore"
./backup.sh "$WORK/backup" >/dev/null
"${DC[@]}" stop app >/dev/null
docker run --rm --user 0 --entrypoint sh -v "$RAVEN_DATA_VOLUME":/data "$RAVEN_IMAGE" -c 'find /data -mindepth 1 -delete'
ENV_FILE="$ENV_FILE" ./restore.sh "$WORK/backup" --yes >/dev/null
for _ in $(seq 1 60); do [ "$(code "$BASE/ready")" = "200" ] && break; sleep 1; done
"${DC[@]}" exec -T app python -m raven.admin stats | grep -q 'validated_incidents.jsonl: 1 records' || fail "restore did not bring the record back"

echo "== brute force is throttled per real client, spoofed X-Forwarded-For does not help"
for i in $(seq 1 12); do code -H "X-API-Key: guess-$i" -H "X-Forwarded-For: 203.0.113.$i" "$BASE/beta/impact-summary" >/dev/null; done
expect 429 -H "X-API-Key: $CUSTOMER" -H "X-Forwarded-For: 198.51.100.7" "$BASE/beta/impact-summary"

echo "SMOKE OK"
