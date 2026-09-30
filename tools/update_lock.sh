#!/usr/bin/env bash
# Regenerate requirements.lock from the ranges in pyproject.toml, in a throwaway venv.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
python -m venv "$tmp/v"
"$tmp/v/bin/pip" install -q --upgrade pip
"$tmp/v/bin/python" - <<'PY' > "$tmp/reqs.txt"
import tomllib
print("\n".join(tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]))
PY
"$tmp/v/bin/pip" install -q -r "$tmp/reqs.txt"
{
  echo "# Exact runtime dependency versions verified by CI and used by the container image."
  echo "# Regenerate with: tools/update_lock.sh (then run the tests and tools/license_inventory.py --write)."
  "$tmp/v/bin/pip" freeze
} > requirements.lock
echo "requirements.lock updated"
