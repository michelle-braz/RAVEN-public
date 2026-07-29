# Contributing

RAVEN is a functional incident-analysis engine under active development. Small, focused contributions are welcome.

1. Keep incident examples entirely synthetic.
2. Do not commit credentials, logs, transcripts, third-party material, or local JSONL data.
3. Keep business logic under `src/raven/sentinel/` and HTTP concerns under `src/raven/api/`.
4. Install development dependencies with `python -m pip install -e ".[dev]"`.
5. Run `python -m pytest tests -q` before proposing a change.

Open an issue before making broad architectural or product-scope changes.
