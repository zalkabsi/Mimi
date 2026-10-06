"""CLI: report in, dossier JSON out.

    mimi report --package lodash@4.17.20 --file report.txt --out dossier.json
    mimi report --package lodash@4.17.20 --stdin < report.txt
    mimi whoami          # Sandboxes permission probe (never prints keys)
    mimi demo            # run a bundled sample report through the pipeline

Untrusted PoC code runs only in Sandboxes, never here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .config import Settings
from .db import Database
from .events import stderr_sink
from .pipeline import Pipeline
from .sandboxes import whoami as sandboxes_whoami
from .schemas import ReportSubmission


def _read_report(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    raise SystemExit("provide --file or --stdin")


def cmd_report(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    submission = ReportSubmission(report_text=_read_report(args), package_spec=args.package)
    db = Database(settings.db_path) if not args.no_db else None
    pipeline = Pipeline(settings, db=db, on_event=stderr_sink)
    try:
        dossier = asyncio.run(pipeline.run(submission, source="cli"))
    finally:
        if db is not None:
            db.close()

    payload = json.loads(dossier.model_dump_json())
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"dossier written to {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    print(f"tier: {dossier.tier.value} — {dossier.tier_rationale}", file=sys.stderr)
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    try:
        result = asyncio.run(sandboxes_whoami(settings))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    # A probe that failed to reach the API is not a pass. Exit non-zero so a
    # script or CI step cannot treat "no answer" as "all good".
    if not result.get("ok"):
        print("\nwhoami did not reach a working endpoint.", file=sys.stderr)
        return 4
    perms = result.get("permissions") or {}
    if not perms:
        print("\nwhoami returned no permissions block.", file=sys.stderr)
        return 4
    if not any(perms.values()):
        print(
            "\nBLOCKER: the key authenticates but every permission is false. "
            "Do not start Sandboxes work; see docs/00-constraints-and-open-items.md.",
            file=sys.stderr,
        )
        return 3
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    sample = Path(__file__).resolve().parent / "data" / "sample_report.md"
    if not sample.exists():
        print(f"sample report missing at {sample}", file=sys.stderr)
        return 1
    args.file = str(sample)
    args.stdin = False
    args.package = args.package or "minimist@1.2.5"
    return cmd_report(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimi", description="Vulnerability report triage with receipts.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("report", help="run one report through the pipeline")
    p.add_argument("--package", required=True, help="package@version (npm)")
    p.add_argument("--file", help="path to the report text")
    p.add_argument("--stdin", action="store_true", help="read the report from stdin")
    p.add_argument("--out", help="write the dossier JSON here")
    p.add_argument("--no-db", action="store_true", help="do not persist to SQLite")
    p.set_defaults(func=cmd_report)

    w = sub.add_parser("whoami", help="Sandboxes permission probe (status and permissions only)")
    w.set_defaults(func=cmd_whoami)

    d = sub.add_parser("demo", help="run the bundled sample report")
    d.add_argument("--package", help="override package@version")
    d.add_argument("--out", help="write the dossier JSON here")
    d.add_argument("--no-db", action="store_true")
    d.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
