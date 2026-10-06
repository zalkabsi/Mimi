"""EventLog emits typed StageEvents; Database(":memory:") round-trips events.

Never invents numbers: unmeasured fields stay None in both layers.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mimi.db import Database
from mimi.events import EventLog, now_iso
from mimi.schemas import Dossier, StageEvent, Tier


# ---------------------------------------------------------------------------
# EventLog
# ---------------------------------------------------------------------------

def test_eventlog_emits_typed_stage_events():
    log = EventLog("r1")
    ev = log.emit("extract", "ok", "claim extracted")
    assert isinstance(ev, StageEvent)
    assert log.events == [ev]
    assert ev.report_id == "r1"
    assert ev.stage == "extract"
    assert ev.status == "ok"
    assert ev.detail == "claim extracted"


def test_event_keeps_unmeasured_fields_none():
    log = EventLog("r1")
    ev = log.emit("research", "skipped", "no Tavily client")
    assert ev.tokens_in is None
    assert ev.tokens_out is None
    assert ev.model is None
    assert ev.latency_ms is None
    assert ev.cost is None
    assert ev.cost_units is None
    assert ev.sandbox_run_ids == []
    assert ev.data == {}


def test_event_records_measured_fields_exactly():
    log = EventLog("r1")
    ev = log.emit(
        "fork_run",
        "ok",
        "h1: exit=0",
        model="nvidia/nemotron-3-super-120b-a12b",
        tokens_in=100,
        tokens_out=50,
        latency_ms=12.5,
        sandbox_run_ids=["sb-9"],
        cost=0.25,
        cost_units="contree-cost-units",
        data={"oracle_fired": True},
    )
    assert ev.tokens_in == 100
    assert ev.tokens_out == 50
    assert ev.model == "nvidia/nemotron-3-super-120b-a12b"
    assert ev.latency_ms == 12.5
    assert ev.sandbox_run_ids == ["sb-9"]
    assert ev.cost == 0.25
    assert ev.cost_units == "contree-cost-units"
    assert ev.data == {"oracle_fired": True}


def test_event_ts_is_iso_utc():
    ts = now_iso()
    assert ts.endswith("+00:00")
    log = EventLog("r1")
    ev = log.emit("extract", "ok")
    assert ev.ts.endswith("+00:00")


def test_status_helpers_set_status():
    log = EventLog("r1")
    t0 = log.start("build", "building")
    assert log.events[-1].status == "started"
    log.ok("build", t0, "built")
    assert log.events[-1].status == "ok"
    assert log.events[-1].latency_ms is not None
    log.error("build", t0, "failed")
    assert log.events[-1].status == "error"
    log.skip("differential", "no fixed version")
    assert log.events[-1].status == "skipped"


def test_invalid_status_rejected():
    log = EventLog("r1")
    with pytest.raises(ValidationError):
        log.emit("extract", "banana")


def test_sink_receives_json_ready_dict():
    seen: list[dict] = []
    log = EventLog("r1", sink=seen.append)
    log.emit("extract", "ok", "hi", data={"k": 1})
    assert len(seen) == 1
    assert seen[0]["stage"] == "extract"
    assert seen[0]["data"] == {"k": 1}
    # must be plain JSON-serialisable
    assert json.loads(json.dumps(seen[0])) == seen[0]


# ---------------------------------------------------------------------------
# Database(":memory:") round-trips events
# ---------------------------------------------------------------------------

def test_database_memory_round_trips_events():
    db = Database(":memory:")
    try:
        log = EventLog("r1")
        log.emit("extract", "started", "begin")
        log.emit("extract", "ok", "done", tokens_in=10, tokens_out=2, data={"n": 1})
        for ev in log.events:
            payload = json.loads(ev.model_dump_json())
            db.add_event("r1", payload)

        rows = db.list_events("r1")
        assert len(rows) == 2
        assert rows[0]["stage"] == "extract"
        assert rows[0]["status"] == "started"
        assert rows[1]["tokens_in"] == 10
        assert rows[1]["data"] == {"n": 1}
        # round-trip preserves everything the event carried
        assert rows[1] == json.loads(log.events[1].model_dump_json())
    finally:
        db.close()


def test_database_events_ordered_and_isolated_per_report():
    db = Database(":memory:")
    try:
        db.add_event("a", {"ts": "1", "stage": "extract", "status": "ok", "detail": "a1"})
        db.add_event("b", {"ts": "2", "stage": "ground", "status": "ok", "detail": "b1"})
        db.add_event("a", {"ts": "3", "stage": "ground", "status": "ok", "detail": "a2"})
        rows_a = db.list_events("a")
        rows_b = db.list_events("b")
        assert [r["detail"] for r in rows_a] == ["a1", "a2"]
        assert [r["detail"] for r in rows_b] == ["b1"]
    finally:
        db.close()


def test_database_typed_stage_event_round_trips_via_dossier():
    db = Database(":memory:")
    try:
        ev = StageEvent(
            ts=now_iso(),
            report_id="r1",
            stage="verdict",
            status="ok",
            detail="tier=Confirmed",
            data={"oracle_fired": True},
        )
        db.add_event("r1", json.loads(ev.model_dump_json()))

        dossier = Dossier(report_id="r1", tier=Tier.CONFIRMED, events=[ev])
        db.upsert_report(dossier, status="complete")

        stored = db.get_report("r1")
        assert stored is not None
        assert stored.tier is Tier.CONFIRMED
        assert stored.events[0].stage == "verdict"

        rows = db.list_events("r1")
        again = StageEvent.model_validate(rows[0])
        assert again == ev
        assert db.get_status("r1") == "complete"
    finally:
        db.close()


def test_database_missing_report_and_events():
    db = Database(":memory:")
    try:
        assert db.get_report("nope") is None
        assert db.get_status("nope") is None
        assert db.list_events("nope") == []
    finally:
        db.close()
