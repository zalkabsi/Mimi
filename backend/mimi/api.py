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
import queue
import threading
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import Settings
from .db import Database
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
_tasks: dict[str, asyncio.Task] = {}
_event_queues: dict[str, list[queue.Queue]] = {}


def _check_access(x_mimi_key: Optional[str]) -> str:
    """Three tiers. With no MIMI_JUDGE_KEY configured, demo mode only."""
    judge_key = __import__("os").environ.get("MIMI_JUDGE_KEY")
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
    q: queue.Queue = queue.Queue()
    _event_queues.setdefault(report_id, []).append(q)

    def sink(event: dict) -> None:
        q.put(event)

    pipeline = Pipeline(_settings, db=_db, on_event=sink)

    async def _run() -> None:
        try:
            await pipeline.run(submission, source="api", report_id=report_id)
        except Exception as e:
            q.put({"stage": "pipeline", "status": "error", "detail": str(e)})
        finally:
            q.put(None)  # sentinel

    task = asyncio.create_task(_run())
    _tasks[report_id] = task
    return {"report_id": report_id, "status": "running"}


@app.get("/api/reports/{report_id}/stream")
async def stream_events(report_id: str) -> StreamingResponse:
    q: queue.Queue = queue.Queue()
    _event_queues.setdefault(report_id, []).append(q)
    for past in _db.list_events(report_id):
        q.put(past)

    def gen():
        while True:
            try:
                item = q.get(timeout=15.0)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/whoami")
async def whoami(x_mimi_key: Optional[str] = Header(default=None)) -> dict:
    _check_access(x_mimi_key)
    from .sandboxes import whoami as sandbox_whoami

    try:
        return await sandbox_whoami(_settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
