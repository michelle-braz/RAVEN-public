#!/usr/bin/env python3
"""Export the API contract to docs/api/openapi.json (or verify it is current with --check)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TARGET = ROOT / "docs" / "api" / "openapi.json"


def render() -> str:
    from raven.api.main import create_app
    from raven.api.settings import Settings

    return json.dumps(create_app(Settings(docs_enabled=True)).openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    fresh = render()
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != fresh:
            print("docs/api/openapi.json is stale: run tools/export_openapi.py", file=sys.stderr)
            raise SystemExit(1)
        print("openapi.json is current")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(fresh, encoding="utf-8")
        print(f"wrote {TARGET.relative_to(ROOT)}")
