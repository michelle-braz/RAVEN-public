"""Cyber Missions — daily, ticket-based cybersecurity practice on top of RAVEN.

The missions reuse RAVEN's investigation structure (evidence, hypothesis,
impact, next steps, recurrence) in a simple study interface. The front-end is
static (``web/``) so it can be served by the RAVEN API at ``/missions/`` or
deployed on its own as a static site.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MISSIONS_WEB_DIR = Path(__file__).parent / "web"
MISSIONS_FILE = MISSIONS_WEB_DIR / "missions.json"


def load_missions() -> dict[str, Any]:
    return json.loads(MISSIONS_FILE.read_text(encoding="utf-8"))
