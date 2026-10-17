"""Structured JSON events per stage — the single source for the UI timeline,
cost accounting and the eval report. Never invents numbers: fields stay None
when nothing was measured."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .schemas import StageEvent


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLog:
    """Collects StageEvents for one report and optionally streams them."""

    def __init__(self, report_id: str, sink: Optional[Callable[[dict], None]] = None):
        self.report_id = report_id
        self.events: list[StageEvent] = []
        self._sink = sink
        self._t0 = time.monotonic()

    def emit(
        self,
        stage: str,
        status: str = "ok",
        detail: str = "",
        *,
        model: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        latency_ms: Optional[float] = None,
        sandbox_run_ids: Optional[list[str]] = None,
        cost: Optional[float] = None,
        cost_units: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> StageEvent:
        ev = StageEvent(
            ts=now_iso(),
            report_id=self.report_id,
            stage=stage,
            status=status,  # type: ignore[arg-type]
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            sandbox_run_ids=sandbox_run_ids or [],
            cost=cost,
            cost_units=cost_units,
            detail=detail,
            data=data or {},
        )
        self.events.append(ev)
        if self._sink is not None:
            self._sink(json.loads(ev.model_dump_json()))
        return ev

    def start(self, stage: str, detail: str = "", **kw: Any) -> float:
        self.emit(stage, "started", detail, **kw)
        return time.monotonic()

    def ok(self, stage: str, t0: float, detail: str = "", **kw: Any) -> StageEvent:
        return self.emit(stage, "ok", detail, latency_ms=(time.monotonic() - t0) * 1000.0, **kw)

    def error(self, stage: str, t0: float, detail: str = "", **kw: Any) -> StageEvent:
        return self.emit(stage, "error", detail, latency_ms=(time.monotonic() - t0) * 1000.0, **kw)

    def skip(self, stage: str, detail: str = "") -> StageEvent:
        return self.emit(stage, "skipped", detail)

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._t0) * 1000.0


def stderr_sink(event: dict) -> None:
    """Human-readable progress lines on stderr (CLI)."""
    stage = event.get("stage", "?")
    status = event.get("status", "?")
    detail = (event.get("detail") or "")[:120]
    print(f"[{status:7}] {stage:12} {detail}", file=sys.stderr)
