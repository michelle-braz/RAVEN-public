# Contributing

RAVEN is proprietary ([LICENSE](LICENSE)). External contributions are accepted only after the contributor signs an
assignment or licence agreement with the owner; open an issue first.

Working rules:

1. Examples and tests use synthetic data only. Never commit credentials, logs, transcripts or JSONL data.
2. Business logic lives in `src/raven/sentinel/`, HTTP concerns in `src/raven/api/`; keep them separate.
3. The analysis response must contain only observed or derived values; never invent figures.
4. Install: `pip install -e ".[dev]"`. Run `python -m pytest tests -q` before proposing a change.
5. When you change dependencies: `tools/update_lock.sh`, `python tools/license_inventory.py --write`.
   When you change the API: `python tools/export_openapi.py`. CI fails if either is stale.
6. Deployment changes: run `deploy/smoke.sh` (needs Docker).
