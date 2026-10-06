"""Sandboxes permission probe — status and permissions only, never keys.

Run first thing in a new session (CLAUDE.md). Exit codes:
  0  permissions look usable
  2  env vars missing
  3  key authenticates but every permission is false (the known blocker)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from mimi.config import Settings  # noqa: E402
from mimi.sandboxes import whoami  # noqa: E402


def main() -> int:
    missing = [v for v in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID") if not os.environ.get(v)]
    if missing:
        print(f"missing env vars: {', '.join(missing)} (set them in the shell; never paste keys in chat)", file=sys.stderr)
        return 2
    result = asyncio.run(whoami(Settings.from_env()))
    # Never echo the key; the result only carries permissions/status.
    print(json.dumps(result, indent=2))
    perms = result.get("permissions") or {}
    if not perms:
        print("could not read permissions from whoami", file=sys.stderr)
        return 1
    if not any(perms.values()):
        print(
            "\nBLOCKER: key authenticates but every permission is false. "
            "Do not start Sandboxes work (CLAUDE.md). Work on stages 1-4, "
            "the eval harness and the UI instead.",
            file=sys.stderr,
        )
        return 3
    print("\npermissions look usable: " + ", ".join(k for k, v in perms.items() if v), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
