"""SQLite storage (WAL) for reports, dossiers and stage events.

Single file, no server. The same events feed the UI timeline and the eval
report. Nothing here stores secrets.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from .schemas import Dossier

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    package_spec TEXT NOT NULL,
    status TEXT NOT NULL,
    tier TEXT,
    dossier_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_report ON events(report_id, id);
"""


class Database:
    """One SQLite connection, serialized by a lock.

    FastAPI runs sync handlers in a threadpool while the pipeline runs on the
    event loop, so this connection is used from several threads at once.
    ``check_same_thread=False`` permits that but does not make concurrent
    ``execute`` calls safe — without the lock two threads can interleave on one
    connection and read each other's rows. Every method here takes ``_lock``.
    """

    def __init__(self, path: str = "mimi.db"):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    # -- reports ------------------------------------------------------
    def upsert_report(self, dossier: Dossier, status: str = "complete") -> None:
        with self._lock:
            self.conn.execute(
                """INSERT INTO reports (id, created_at, source, package_spec, status, tier, dossier_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     status=excluded.status, tier=excluded.tier, dossier_json=excluded.dossier_json""",
                (
                    dossier.report_id,
                    dossier.created_at or "",
                    dossier.source,
                    dossier.package_spec,
                    status,
                    dossier.tier.value,
                    dossier.model_dump_json(),
                ),
            )
            self.conn.commit()

    def update_status(self, report_id: str, status: str, dossier: Optional[Dossier] = None) -> None:
        with self._lock:
            if dossier is not None:
                self.conn.execute(
                    "UPDATE reports SET status=?, tier=?, dossier_json=? WHERE id=?",
                    (status, dossier.tier.value, dossier.model_dump_json(), report_id),
                )
            else:
                self.conn.execute("UPDATE reports SET status=? WHERE id=?", (status, report_id))
            self.conn.commit()

    def get_report(self, report_id: str) -> Optional[Dossier]:
        with self._lock:
            row = self.conn.execute(
                "SELECT dossier_json FROM reports WHERE id=?", (report_id,)
            ).fetchone()
        if not row:
            return None
        return Dossier.model_validate_json(row["dossier_json"])

    def get_status(self, report_id: str) -> Optional[str]:
        with self._lock:
            row = self.conn.execute("SELECT status FROM reports WHERE id=?", (report_id,)).fetchone()
        return row["status"] if row else None

    def list_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                """SELECT id, created_at, source, package_spec, status, tier
                   FROM reports ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_report(self, report_id: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
            self.conn.execute("DELETE FROM events WHERE report_id=?", (report_id,))
            self.conn.commit()

    # -- events -------------------------------------------------------
    def add_event(self, report_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO events (report_id, ts, stage, status, payload) VALUES (?, ?, ?, ?, ?)",
                (
                    report_id,
                    event.get("ts", ""),
                    event.get("stage", ""),
                    event.get("status", ""),
                    json.dumps(event),
                ),
            )
            self.conn.commit()

    def list_events(self, report_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT payload FROM events WHERE report_id=? ORDER BY id", (report_id,)
            ).fetchall()
        return [json.loads(r["payload"]) for r in rows]
