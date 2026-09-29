"""Operator tooling: data export, retention, erasure and key generation.

    python -m raven.admin stats
    python -m raven.admin export --out export.json
    python -m raven.admin purge --before 2026-01-01          # dry run
    python -m raven.admin purge --before 2026-01-01 --yes    # apply
    python -m raven.admin delete --incident-id ID --yes
    python -m raven.admin keys new "Customer name"

Reads and writes ``RAVEN_DATA_DIR``. ``purge`` and ``delete`` rewrite files, so
stop the API first (see docs/operations/runbook.md); they never touch a file
unless ``--yes`` is given.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from raven.api.beta import store
from raven.api.beta_keys import generate_beta_key
from raven.api.settings import MIN_KEY_LEN


def _read(name: str) -> list[dict]:
    rows: list[dict] = []
    for line in store._lines(name):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write_atomic(path: Path, rows: list[dict]) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".rewrite-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _stamp(row: dict) -> str | None:
    return row.get("timestamp") or row.get("ts")


def cmd_stats(_: argparse.Namespace) -> int:
    for name in store.ALL_FILES:
        rows = _read(name)
        stamps = sorted(s for s in map(_stamp, rows) if s)
        span = f"{stamps[0]} .. {stamps[-1]}" if stamps else "n/a"
        print(f"{name}: {len(rows)} records, {span}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    payload = {
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {name: _read(name) for name in store.ALL_FILES},
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"exported to {args.out}")
    else:
        print(text)
    return 0


def _apply(keep, args: argparse.Namespace, verb: str) -> int:
    changed = 0
    for name in store.ALL_FILES:
        rows = _read(name)
        kept = [r for r in rows if keep(r)]
        drop = len(rows) - len(kept)
        if drop:
            print(f"{name}: {drop} of {len(rows)} records would be {verb}")
            if args.yes:
                _write_atomic(store.data_dir() / name, kept)
            changed += drop
    if not changed:
        print("nothing to do")
    elif not args.yes:
        print("dry run — re-run with --yes to apply")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    try:
        cutoff = datetime.strptime(args.before, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        print("--before must be YYYY-MM-DD", file=sys.stderr)
        return 2
    return _apply(lambda r: (_stamp(r) is None) or _stamp(r) >= cutoff, args, "purged")


def cmd_delete(args: argparse.Namespace) -> int:
    return _apply(lambda r: r.get("incident_id") != args.incident_id, args, "deleted")


def cmd_keys_new(args: argparse.Namespace) -> int:
    key = generate_beta_key()
    assert len(key) >= MIN_KEY_LEN
    entry = {key: {"name": args.name, "status": "active",
                   "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}}
    print(f"key: {key}")
    print("Merge this entry into BETA_KEYS_JSON, then restart:")
    print(json.dumps(entry, separators=(",", ":")))
    print("Give the key to its owner once; it is not stored anywhere else.", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raven.admin", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="record counts and date range per file").set_defaults(fn=cmd_stats)
    p = sub.add_parser("export", help="dump every stored record as JSON")
    p.add_argument("--out", help="write to this file (mode 0600) instead of stdout")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("purge", help="delete records older than a date (retention)")
    p.add_argument("--before", required=True, metavar="YYYY-MM-DD")
    p.add_argument("--yes", action="store_true", help="apply (default is a dry run)")
    p.set_defaults(fn=cmd_purge)
    p = sub.add_parser("delete", help="erase every record linked to one incident")
    p.add_argument("--incident-id", required=True)
    p.add_argument("--yes", action="store_true", help="apply (default is a dry run)")
    p.set_defaults(fn=cmd_delete)
    keys = sub.add_parser("keys", help="API key helpers").add_subparsers(dest="keys_command", required=True)
    p = keys.add_parser("new", help="generate a customer key")
    p.add_argument("name")
    p.set_defaults(fn=cmd_keys_new)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
