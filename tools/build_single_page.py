"""Bundle the Cyber Missions web app into one self-contained HTML body.

Used to publish the app on hosts that serve a single page (no module
imports, no fetch of sibling files). Output: path given as argv[1].
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).parents[1] / "src" / "raven" / "missions" / "web"


def build() -> str:
    engine = re.sub(r"^export ", "", (WEB / "engine.js").read_text(encoding="utf-8"), flags=re.M)
    app = (WEB / "app.js").read_text(encoding="utf-8")
    app, n = re.subn(r"^import \{.*?\} from \"\./engine\.js\";\n", "", app, count=1, flags=re.S | re.M)
    assert n == 1, "engine import not found"
    data = json.dumps(json.loads((WEB / "missions.json").read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":"))
    fetch_block = re.compile(r"  try \{\n    const res = await fetch\(\"missions\.json\".*?\n  \}\n", re.S)
    assert fetch_block.search(app), "fetch block not found"
    app = fetch_block.sub("  DATA = window.__MISSIONS__;\n", app, count=1)
    html = (WEB / "index.html").read_text(encoding="utf-8")
    body = re.search(r"<body>(.*?)<script", html, re.S).group(1)
    css = (WEB / "style.css").read_text(encoding="utf-8")
    safe_data = data.replace("</", "<\\/")
    return (
        "<title>Cyber Missions</title>\n"
        '<meta name="description" content="Uma missão prática de cibersegurança por dia.">\n'
        f"<style>\n{css}</style>\n{body}"
        f"<script>window.__MISSIONS__ = {safe_data};</script>\n"
        f"<script>\n(() => {{\n{engine}\n{app}\n}})();\n</script>\n"
    )


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(build(), encoding="utf-8")
