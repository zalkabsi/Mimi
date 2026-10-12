"""FastAPI app: submit reports, watch the live timeline, read dossiers.

Access tiers (docs/02-architecture.md):
1. demo mode — no login, seeded inbox with recorded runs, read-only, free.
2. judge credential — published in testing instructions, own budget, no rate limit.
3. try-your-own — per-session budget cap.

SSE carries stage events as the pipeline runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import Settings
from .db import Database
from .seed import seed_demo
from .pipeline import Pipeline
from .schemas import Dossier, ReportSubmission

app = FastAPI(title="Mimi", description="Every vulnerability report gets a verdict with receipts.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings = Settings.from_env()
_db = Database(_settings.db_path)
seed_demo(_db)
_tasks: dict[str, asyncio.Task] = {}
# Live SSE fan-out: one list of subscriber queues per report. The pipeline
# publishes to every queue in the list; each stream owns one queue.
_event_queues: dict[str, list[queue.Queue]] = {}
_event_lock = threading.Lock()
# Reports whose pipeline has finished, so a late subscriber still terminates.
_finished: set[str] = set()


def _publish(report_id: str, event: dict) -> None:
    with _event_lock:
        subscribers = list(_event_queues.get(report_id, ()))
    for q in subscribers:
        q.put(event)


def _finish(report_id: str) -> None:
    """Mark the run finished and tell every subscriber to stop."""
    with _event_lock:
        _finished.add(report_id)
        subscribers = list(_event_queues.get(report_id, ()))
        _event_queues.pop(report_id, None)
        _tasks.pop(report_id, None)
    for q in subscribers:
        q.put(None)  # sentinel: end this stream


def _check_access(x_mimi_key: Optional[str]) -> str:
    """Three tiers. With no MIMI_JUDGE_KEY configured, demo mode only."""
    judge_key = os.environ.get("MIMI_JUDGE_KEY")
    if judge_key and x_mimi_key == judge_key:
        return "judge"
    if x_mimi_key:
        raise HTTPException(status_code=401, detail="unknown access key")
    return "demo"


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "mimi"}


@app.get("/api/reports")
def list_reports(limit: int = 50) -> list[dict]:
    return _db.list_reports(limit=limit)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str) -> dict:
    dossier = _db.get_report(report_id)
    if dossier is None:
        raise HTTPException(status_code=404, detail="no such report")
    return json.loads(dossier.model_dump_json())


@app.get("/api/reports/{report_id}/events")
def get_events(report_id: str) -> list[dict]:
    return _db.list_events(report_id)


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
        _finished.discard(report_id)
        task = asyncio.create_task(_run())
        _tasks[report_id] = task
    return {"report_id": report_id, "status": "running"}


@app.get("/api/reports/{report_id}/stream")
async def stream_events(report_id: str) -> StreamingResponse:
    q: queue.Queue = queue.Queue()
    with _event_lock:
        already_finished = report_id in _finished
        is_running = report_id in _tasks
        if not already_finished:
            _event_queues.setdefault(report_id, []).append(q)

    if not already_finished and not is_running and _db.get_report(report_id) is None:
        # Nothing will ever publish to this id. Ending in a keep-alive loop
        # would hang the client forever — refuse it instead.
        with _event_lock:
            subscribers = _event_queues.get(report_id)
            if subscribers and q in subscribers:
                subscribers.remove(q)
        raise HTTPException(status_code=404, detail="no such report")

    # Replay whatever is already recorded, then follow live events. A run that
    # finished before this subscriber connected gets its history and stops.
    # So does a row stuck at "running" with no live task (process restart,
    # cancelled run): keep-aliving forever would tell the client to wait for
    # events that will never come.
    for past in _db.list_events(report_id):
        q.put(past)
    with _event_lock:
        live_now = report_id in _tasks
        finished_now = report_id in _finished
    if already_finished or not live_now or finished_now:
        q.put(None)

    def gen():
        try:
            while True:
                try:
                    item = q.get(timeout=15.0)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            with _event_lock:
                subscribers = _event_queues.get(report_id)
                if subscribers and q in subscribers:
                    subscribers.remove(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/whoami")
async def whoami(x_mimi_key: Optional[str] = Header(default=None)) -> dict:
    _check_access(x_mimi_key)
    from .sandboxes import whoami as sandbox_whoami

    try:
        return await sandbox_whoami(_settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# Single-container hosting: serve the built UI from the same origin when a
# build exists (see Dockerfile). Mounted last so /api/* routes win.
_DIST = os.environ.get("MIMI_FRONTEND_DIST", "")
if _DIST and os.path.isdir(_DIST):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")
