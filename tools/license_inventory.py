#!/usr/bin/env python3
"""Third-party licence inventory for RAVEN (standard library only).

    python tools/license_inventory.py --check    # CI: fail if the inventory is stale or a licence is not allowed
    python tools/license_inventory.py --write    # regenerate docs/licensing/THIRD_PARTY.md and THIRD_PARTY_LICENSES.txt

Run it in an environment installed from requirements.lock (plus the dev extra).
The closure is computed from the dependency ranges in pyproject.toml, so nothing
that is not really depended on is listed, and nothing is missed.
"""
from __future__ import annotations

import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "licensing"
TABLE = OUT_DIR / "THIRD_PARTY.md"
TEXTS = OUT_DIR / "THIRD_PARTY_LICENSES.txt"

# Permissive licences: no obligation beyond keeping the notice.
ALLOWED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "0BSD", "Unlicense"}
# File-level copyleft: fine when used unmodified and unbundled-in-source; flagged in the report.
REVIEWED = {"MPL-2.0": "File-level copyleft. Used unmodified as a dependency; changes to its own files would have to be published."}
CLASSIFIERS = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "ISC License (ISCL)": "ISC",
    "Python Software Foundation License": "PSF-2.0",
}


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(line: str) -> tuple[str, bool]:
    """(normalised name, is_conditional_on_extra_or_marker)"""
    head = re.split(r"[;\s(<>=!~\[]", line.strip(), maxsplit=1)[0]
    return norm(head), "extra ==" in line


def closure(roots: list[str]) -> dict[str, metadata.Distribution]:
    found: dict[str, metadata.Distribution] = {}
    todo = [requirement_name(r)[0] for r in roots]
    while todo:
        name = todo.pop()
        if name in found:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # marker-gated (other platform/python) or extra: not installed here
        found[name] = dist
        for req in dist.requires or []:
            dep, conditional = requirement_name(req)
            if not conditional:
                todo.append(dep)
    return found


def licence_of(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr.strip()
    for c in md.get_all("Classifier") or []:
        if c.startswith("License :: OSI Approved :: "):
            mapped = CLASSIFIERS.get(c.split("::")[-1].strip())
            if mapped:
                return mapped
    lic = (md.get("License") or "").strip()
    return lic if 0 < len(lic) < 60 and "\n" not in lic else "UNKNOWN"


def is_allowed(expr: str) -> bool:
    options = [o.strip("() ") for o in re.split(r"\s+OR\s+", expr)]
    return any(o in ALLOWED or o in REVIEWED for o in options)


def homepage(dist: metadata.Distribution) -> str:
    md = dist.metadata
    if md.get("Home-page"):
        return md["Home-page"]
    for entry in md.get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if label.strip().lower() in {"homepage", "home", "source", "repository", "documentation"}:
            return url.strip()
    return ""


def license_files(dist: metadata.Distribution) -> list[tuple[str, str]]:
    out = []
    for f in dist.files or []:
        in_dist_info = bool(f.parts) and f.parts[0].endswith(".dist-info")
        if in_dist_info and f.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
            try:
                out.append((str(f), dist.locate_file(f).read_text(encoding="utf-8", errors="replace").strip()))
            except OSError:
                pass
    return out


def build() -> tuple[str, str, list[str]]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    runtime = closure(project["dependencies"])
    dev = {k: v for k, v in closure(project["optional-dependencies"]["dev"]).items() if k not in runtime}
    problems: list[str] = []

    lock = {}
    for line in (ROOT / "requirements.lock").read_text().splitlines():
        if "==" in line and not line.startswith("#"):
            n, v = line.split("==")
            lock[norm(n)] = v.strip()
    for name, dist in runtime.items():
        if lock.get(name) != dist.version:
            problems.append(f"{name}: installed {dist.version} but requirements.lock says {lock.get(name)}")
    for name in set(lock) - set(runtime):
        problems.append(f"{name}: in requirements.lock but not a runtime dependency of pyproject.toml")

    rows, texts = [], []
    for scope, group in (("runtime", runtime), ("development/test only", dev)):
        for name in sorted(group):
            dist = group[name]
            expr = licence_of(dist)
            if not is_allowed(expr):
                problems.append(f"{name} {dist.version}: licence {expr!r} is not on the allowed list")
            note = next((REVIEWED[o] for o in re.split(r"\s+OR\s+", expr) if o in REVIEWED and o not in ALLOWED), "")
            rows.append((dist.metadata["Name"], dist.version, expr, scope, homepage(dist), note))
            for fname, text in license_files(dist):
                texts.append(f"{'=' * 78}\n{dist.metadata['Name']} {dist.version} — {expr} — {fname}\n{'=' * 78}\n{text}\n")

    md = [
        "# Third-party software inventory",
        "",
        "> Classification: Licensing. Generated by `tools/license_inventory.py --write`; do not edit by hand.",
        "",
        "Every package below is a dependency of RAVEN (directly or transitively). Runtime packages ship in the",
        "container image, together with their full licence texts (`THIRD_PARTY_LICENSES.txt`). Development/test",
        "packages are used only to run the test suite and are not distributed.",
        "",
        "| Package | Version | Licence (SPDX) | Scope | Source |",
        "|---|---|---|---|---|",
    ]
    for name, version, expr, scope, url, _ in rows:
        md.append(f"| {name} | {version} | {expr} | {scope} | {url} |")
    obligations = sorted({(n, note) for n, _, _, _, _, note in rows if note})
    md += ["", "## Obligations", "",
           "Permissive licences (MIT, BSD, Apache-2.0, ISC, PSF-2.0) require that the copyright notice and licence text",
           "stay with redistributed copies. The container image does this (`/usr/share/doc/raven/THIRD_PARTY_LICENSES.txt`).", ""]
    for name, note in obligations:
        md.append(f"* **{name}** — {note}")
    md += ["", "No dependency is under a strong copyleft licence (GPL/AGPL/SSPL) and none restricts commercial use.", ""]
    return "\n".join(md), "\n".join(texts), problems


def main(argv: list[str]) -> int:
    table, texts, problems = build()
    if "--write" in argv:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        TABLE.write_text(table, encoding="utf-8")
        TEXTS.write_text(texts, encoding="utf-8")
        print(f"wrote {TABLE.relative_to(ROOT)} and {TEXTS.relative_to(ROOT)}")
    elif "--check" in argv:
        for path, fresh in ((TABLE, table), (TEXTS, texts)):
            if not path.exists() or path.read_text(encoding="utf-8") != fresh:
                problems.append(f"{path.relative_to(ROOT)} is stale: run tools/license_inventory.py --write")
    else:
        print(table)
    for p in problems:
        print("ERROR:", p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
