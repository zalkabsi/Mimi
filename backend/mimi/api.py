"""FastAPI app: submit reports, watch the live timeline, read dossiers.

Access modes:
1. demo mode — no login, seeded inbox with recorded runs, read-only, free.
2. judge credential — protected live submissions, configured by the operator.

SSE carries stage events as the pipeline runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import secrets
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import Settings
from .db import Database
from .events import now_iso
from .pipeline import Pipeline
from .schemas import Dossier, ReportSubmission

app = FastAPI(title="Mimi", description="Every vulnerability report gets a verdict with receipts.")
_cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "MIMI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings = Settings.from_env()
_db = Database(_settings.db_path)
_DEMO_DOSSIER = Dossier.model_validate_json(
    (Path(__file__).resolve().parent / "data" / "sample_dossier.json").read_text(encoding="utf-8")
)
_DEMO_REPORT_ID = _DEMO_DOSSIER.report_id
_tasks: dict[str, asyncio.Task] = {}
# Live SSE fan-out: one list of subscriber queues per report. The pipeline
# publishes to every queue in the list; each stream owns one queue.
_event_queues: dict[str, list[queue.Queue]] = {}
_event_lock = threading.Lock()


def _publish(report_id: str, event: dict) -> None:
    with _event_lock:
        # Keep event writes ordered with _finish's sentinel. Otherwise a
        # publisher can copy the subscriber list, lose the lock, and enqueue
        # an event after _finish has already told the stream to stop.
        for q in _event_queues.get(report_id, ()):
            q.put(event)


def _finish(report_id: str) -> None:
    """Mark the run finished and tell every subscriber to stop."""
    with _event_lock:
        subscribers = list(_event_queues.get(report_id, ()))
        _event_queues.pop(report_id, None)
        _tasks.pop(report_id, None)
        for q in subscribers:
            q.put(None)  # sentinel: end this stream, after all prior events


def _check_access(x_mimi_key: Optional[str]) -> str:
    """With no MIMI_JUDGE_KEY configured, only read-only demo mode is available."""
    judge_key = os.environ.get("MIMI_JUDGE_KEY")
    if judge_key and x_mimi_key and secrets.compare_digest(
        x_mimi_key.encode("utf-8"), judge_key.encode("utf-8")
    ):
        return "judge"
    if x_mimi_key:
        raise HTTPException(status_code=401, detail="unknown access key")
    return "demo"


def _require_judge_access(x_mimi_key: Optional[str]) -> None:
    if _check_access(x_mimi_key) != "judge":
        raise HTTPException(status_code=401, detail="judge access key required")


def _demo_row() -> dict:
    return {
        "id": _DEMO_REPORT_ID,
        "created_at": _DEMO_DOSSIER.created_at,
        "source": "demo",
        "package_spec": _DEMO_DOSSIER.package_spec,
        "status": "complete",
        "tier": _DEMO_DOSSIER.tier.value,
    }


def _report_events(report_id: str) -> list[dict]:
    """Recorded history plus a terminal event only after the dossier is saved."""
    if report_id == _DEMO_REPORT_ID:
        return [event.model_dump(mode="json") for event in _DEMO_DOSSIER.events]

    status = _db.get_status(report_id)
    if status == "running":
        with _event_lock:
            active = report_id in _tasks
        if not active:
            # A process restart leaves no worker to finish this job.
            _db.update_status(report_id, "error")
            status = "error"

    events = _db.list_events(report_id)
    if status in {"complete", "error"} and not any(
        (event.get("data") or {}).get("final") is True for event in events
    ):
        events.append(
            {
                "ts": now_iso(),
                "report_id": report_id,
                "stage": "pipeline",
                "status": "error" if status == "error" else "ok",
                "detail": "report finished",
                "data": {"final": True},
            }
        )
    return events


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "mimi"}


@app.get("/api/reports")
def list_reports(
    limit: int = 50,
    x_mimi_key: Optional[str] = Header(default=None),
) -> list[dict]:
    if limit == 0:
        return []
    tier = _check_access(x_mimi_key)
    if tier == "demo":
        return [_demo_row()]
    # Fetch one extra row to allow for a bundled demo ID already persisted in
    # the database, then place the canonical fixture first without duplicates.
    db_limit = limit + 1 if limit > 0 else limit
    reports = _db.list_reports(limit=db_limit)
    reports = [item for item in reports if item["id"] != _DEMO_REPORT_ID]
    with _event_lock:
        active_reports = set(_tasks)
    for item in reports:
        if item["status"] == "running" and item["id"] not in active_reports:
            # Jobs and SSE fan-out are process-local. A row left running after
            # a restart has no worker that can finish it, so expose that state
            # as an error instead of leaving the inbox spinner stuck forever.
            _db.update_status(item["id"], "error")
            item["status"] = "error"
    combined = [_demo_row(), *reports]
    return combined if limit < 0 else combined[:limit]


@app.get("/api/reports/{report_id}")
def get_report(
    report_id: str,
    x_mimi_key: Optional[str] = Header(default=None),
) -> dict:
    if report_id == _DEMO_REPORT_ID:
        return json.loads(_DEMO_DOSSIER.model_dump_json())
    # Authenticate before looking up live IDs so unauthenticated callers
    # cannot distinguish a stored report from a missing one.
    _require_judge_access(x_mimi_key)
    dossier = _db.get_report(report_id)
    if dossier is None:
        raise HTTPException(status_code=404, detail="no such report")
    return json.loads(dossier.model_dump_json())


@app.get("/api/reports/{report_id}/events")
def get_events(
    report_id: str,
    x_mimi_key: Optional[str] = Header(default=None),
) -> list[dict]:
    if report_id == _DEMO_REPORT_ID:
        return [event.model_dump(mode="json") for event in _DEMO_DOSSIER.events]
    _require_judge_access(x_mimi_key)
    if _db.get_report(report_id) is None:
        raise HTTPException(status_code=404, detail="no such report")
    return _report_events(report_id)


@app.post("/api/reports")
async def submit_report(
    submission: ReportSubmission,
    x_mimi_key: Optional[str] = Header(default=None),
) -> dict:
    tier = _check_access(x_mimi_key)
    if tier == "demo":
        raise HTTPException(
            status_code=402,
            detail="demo mode is read-only; use the judge credential or self-host to run live reports",
        )
    report_id = uuid.uuid4().hex[:12]

    def sink(event: dict) -> None:
        _publish(report_id, event)

    pipeline = Pipeline(_settings, db=_db, on_event=sink)

    async def _run() -> None:
        try:
            await pipeline.run(submission, source="api", report_id=report_id)
        except Exception as e:
            _publish(report_id, {"stage": "pipeline", "status": "error", "detail": str(e)})
        finally:
            _finish(report_id)

    # Register under the same lock _finish takes, so a pipeline that completes
    # immediately cannot leave a stale entry behind after _finish popped it.
    with _event_lock:
        task = asyncio.create_task(_run())
        _tasks[report_id] = task
    return {"report_id": report_id, "status": "running"}


@app.get("/api/reports/{report_id}/stream")
async def stream_events(
    report_id: str,
    x_mimi_key: Optional[str] = Header(default=None),
) -> StreamingResponse:
    is_demo_report = report_id == _DEMO_REPORT_ID
    if not is_demo_report:
        _require_judge_access(x_mimi_key)
        if _db.get_report(report_id) is None:
            raise HTTPException(status_code=404, detail="no such report")
    q: queue.Queue = queue.Queue()
    with _event_lock:
        is_running = report_id in _tasks
        if is_running:
            _event_queues.setdefault(report_id, []).append(q)
    if not is_running and _db.get_status(report_id) == "running":
        _db.update_status(report_id, "error")

    # Snapshot recorded events after registering the queue. Events published
    # during this read may appear in both places; the client de-duplicates
    # them. Yield the snapshot before draining the queue so a concurrent
    # finish sentinel cannot discard the initial history.
    # So does a row stuck at "running" with no live task (process restart,
    # cancelled run): keep-aliving forever would tell the client to wait for
    # events that will never come.
    past_events = _report_events(report_id)
    with _event_lock:
        live_now = report_id in _tasks
    if not live_now:
        q.put(None)

    def gen():
        try:
            for past in past_events:
                yield f"data: {json.dumps(past)}\n\n"
            while True:
                try:
                    item = q.get(timeout=15.0)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                if item is None:
                    yield "event: done\ndata: {}\n\n"
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            with _event_lock:
                subscribers = _event_queues.get(report_id)
                if subscribers and q in subscribers:
                    subscribers.remove(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/whoami")
async def whoami(x_mimi_key: Optional[str] = Header(default=None)) -> dict:
    _require_judge_access(x_mimi_key)
    from .sandboxes import whoami as sandbox_whoami

    try:
        return await sandbox_whoami(_settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
