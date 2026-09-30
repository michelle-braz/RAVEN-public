"""Repository-level guarantees: no secrets, consistent versions, a navigable English docs library."""
from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import raven

ROOT = Path(__file__).resolve().parents[1]


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.splitlines() if (ROOT / p).is_file()]


def test_versions_agree():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["version"] == raven.__version__
    assert f"## {raven.__version__}" in (ROOT / "CHANGELOG.md").read_text()


SECRET = re.compile(
    r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_|sk-[A-Za-z0-9]{20,}|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY"
)


def test_no_secrets_or_data_files_are_tracked():
    for path in tracked():
        rel = path.relative_to(ROOT).as_posix()
        assert not rel.endswith(".jsonl"), rel
        assert not re.search(r"(^|/)\.env($|\.)", rel) or rel.endswith(".env.example"), rel
        if path.suffix in {".png", ".txt"} and "THIRD_PARTY" not in rel:
            continue
        if path.suffix == ".png":
            continue
        assert not SECRET.search(path.read_text(errors="ignore")), f"secret-like string in {rel}"


def test_docs_links_resolve_and_index_lists_every_document():
    docs = ROOT / "docs"
    pages = [p for p in list(docs.rglob("*.md")) + [ROOT / n for n in ("README.md", "CHANGELOG.md", "FUTURE.md", "SECURITY.md", "CONTRIBUTING.md")]]
    for page in pages:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", page.read_text()):
            if re.match(r"[a-z]+:", target):
                continue
            assert (page.parent / target).resolve().exists(), f"{page.relative_to(ROOT)} links to missing {target}"
    index = (docs / "README.md").read_text()
    skipped = {"README.md"}
    for page in docs.rglob("*.md"):
        rel = page.relative_to(docs).as_posix()
        if rel in skipped or rel.startswith("decisions/0"):
            continue
        assert rel in index or rel.rsplit("/", 1)[0] + "/" in index, f"{rel} is not in docs/README.md"


def test_every_official_doc_declares_its_class():
    for page in (ROOT / "docs").rglob("*.md"):
        if page.name == "README.md" and page.parent == ROOT / "docs":
            continue
        assert "Classification:" in page.read_text()[:600], page.relative_to(ROOT)


def test_docs_are_english_only():
    assert not list((ROOT / "docs").rglob("*.pt.md"))
