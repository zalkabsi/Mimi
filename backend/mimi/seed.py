"""Seed the read-only demo inbox with recorded dossiers.

Demo mode must be free and need no keys, so the inbox is filled from real
recorded runs committed under ``mimi/data/demo/`` (already-public
vulnerabilities only). They are labelled ``source: demo`` and never
re-run. Existing rows are left untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

from .db import Database
from .schemas import Dossier

DEMO_DIR = Path(__file__).resolve().parent / "data" / "demo"


def seed_demo(db: Database, directory: Path = DEMO_DIR) -> int:
    """Insert recorded dossiers that are not in the DB yet; return how many."""
    added = 0
    for path in sorted(directory.glob("*.json")):
        dossier = Dossier.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if db.get_report(dossier.report_id) is None:
            db.upsert_report(dossier, status="complete")
            added += 1
    return added
