"""API contract and the SSE fan-out.

Regression cover for two bugs no test caught:
1. live events were published to a queue nobody read, so the timeline was dead;
2. an SSE stream for an unknown report id never terminated.

Pinned here: every subscriber queue receives every published event, ``_finish``
ends every stream, a late subscriber to a finished run gets history and stops,
and an unknown report id is refused instead of hanging.
"""

from __future__ import annotations

import os
import queue
import sys
import uuid
from pathlib import Path

# The API module builds its Database at import time from MIMI_DB_PATH. Point it
# at a scratch file before the import so tests never touch the developer's db.
_TEST_DB = Path(__file__).resolve().parent / "_test_api.db"
os.environ["MIMI_DB_PATH"] = str(_TEST_DB)
os.environ.pop("MIMI_JUDGE_KEY", None)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import mimi.api as api  # noqa: E402
from mimi.events import EventLog  # noqa: E402
from mimi.schemas import Dossier, ReportSubmission  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _scratch_db_cleanup():
    yield
    if _TEST_DB.exists():
        try:
            _TEST_DB.unlink()
        except OSError:
            pass


@pytest.fixture(autouse=True)
def _clean_api_state():
    """Each test starts with no subscribers, no tasks and no finished marks."""
    with api._event_lock:
        api._event_queues.clear()
        api._tasks.clear()
        api._finished.clear()
    yield
    with api._event_lock:
        api._event_queues.clear()
        api._tasks.clear()
        api._finished.clear()


@pytest.fixture
def client():
    return TestClient(api.app)


# ---------------------------------------------------------------------------
# Fan-out: one publish, every subscriber
# ---------------------------------------------------------------------------

def test_publish_reaches_every_subscriber():
    # The original bug: _publish wrote to a single sink nobody read. One event
    # must land in EVERY registered queue.
    q1: queue.Queue = queue.Queue()
    q2: queue.Queue = queue.Queue()
    with api._event_lock:
        api._event_queues["r1"] = [q1, q2]

    api._publish("r1", {"stage": "build", "status": "ok", "detail": "built"})

    for q in (q1, q2):
        ev = q.get_nowait()
        assert ev["stage"] == "build"
        assert q.empty(), "each subscriber gets the event exactly once"


def test_publish_to_unknown_report_is_a_noop():
    api._publish("nope", {"stage": "build", "status": "ok"})  # must not raise


def test_finish_ends_every_stream_and_forgets_the_report():
    q1: queue.Queue = queue.Queue()
    q2: queue.Queue = queue.Queue()
    with api._event_lock:
        api._event_queues["r1"] = [q1, q2]

    api._finish("r1")

    assert q1.get_nowait() is None, "sentinel ends stream 1"
    assert q2.get_nowait() is None, "sentinel ends stream 2"
    with api._event_lock:
        assert "r1" not in api._event_queues
        assert "r1" in api._finished


def test_late_subscriber_to_a_finished_run_gets_no_live_queue():
    api._finish("r1")
    q: queue.Queue = queue.Queue()
    with api._event_lock:
        already = "r1" in api._finished
        if not already:
            api._event_queues.setdefault("r1", []).append(q)
    assert already is True
    with api._event_lock:
        assert "r1" not in api._event_queues


def test_events_published_through_the_event_log_reach_subscribers():
    q: queue.Queue = queue.Queue()
    with api._event_lock:
        api._event_queues["r2"] = [q]

    log = EventLog("r2", sink=lambda ev: api._publish("r2", ev))
    log.emit("extract", "ok", "claim extracted")
    log.emit("research", "skipped", "no Tavily client")

    first = q.get_nowait()
    second = q.get_nowait()
    assert first["stage"] == "extract"
    assert second["stage"] == "research"


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "service": "mimi"}


def test_get_unknown_report_is_404(client):
    assert client.get("/api/reports/does-not-exist").status_code == 404


def test_demo_mode_cannot_submit(client):
    # No MIMI_JUDGE_KEY configured: the inbox is read-only for everyone.
    r = client.post(
        "/api/reports",
        json={"report_text": "something is wrong", "package_spec": "lodash@4.17.20"},
    )
    assert r.status_code == 402


def test_unknown_access_key_is_401(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    r = client.post(
        "/api/reports",
        headers={"X-Mimi-Key": "wrong"},
        json={"report_text": "r", "package_spec": "lodash@4.17.20"},
    )
    assert r.status_code == 401


def test_stream_for_unknown_report_is_404_not_a_hang(client):
    # The old behaviour looped on keep-alives forever. It must be refused.
    r = client.get(f"/api/reports/{uuid.uuid4().hex[:12]}/stream")
    assert r.status_code == 404


def test_stream_for_finished_run_replays_history_and_terminates(client):
    rid = uuid.uuid4().hex[:12]
    dossier = Dossier(report_id=rid, report_text="r", package_spec="lodash@4.17.20")
    api._db.upsert_report(dossier, status="complete")
    log = EventLog(rid, sink=lambda ev: api._db.add_event(rid, ev))
    log.emit("extract", "ok", "claim extracted")
    log.emit("verdict", "ok", "tier=likely")
    api._finish(rid)

    with client.stream("GET", f"/api/reports/{rid}/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())

    # History is replayed, and the stream CLOSED rather than keep-aliving.
    assert "claim extracted" in body
    assert "tier=likely" in body
    # A named terminal event, so the UI does not read the close as an error.
    assert "event: done" in body


def test_stream_for_run_still_running_terminates_after_finish(client):
    rid = uuid.uuid4().hex[:12]
    dossier = Dossier(report_id=rid, report_text="r", package_spec="lodash@4.17.20")
    api._db.upsert_report(dossier, status="running")

    # Something must hold the "running" mark so the id is known to the API.
    with api._event_lock:
        api._tasks[rid] = object()  # type: ignore[assignment]

    # Publish and finish from another thread while the stream is open.
    import threading

    def _drive() -> None:
        import time

        time.sleep(0.2)
        api._publish(rid, {"stage": "build", "status": "ok", "detail": "built base image"})
        api._finish(rid)

    t = threading.Thread(target=_drive, daemon=True)
    t.start()

    with client.stream("GET", f"/api/reports/{rid}/stream") as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())

    assert "built base image" in body


def test_submit_and_get_report_roundtrip_shape(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    # Submitting starts a real Pipeline; with no keys it cannot reach anything
    # external, but it WILL try to run. We only assert the response contract
    # here and stop the task immediately so no work happens.
    r = client.post(
        "/api/reports",
        headers={"X-Mimi-Key": "judge-secret"},
        json={"report_text": "r", "package_spec": "@scope/pkg@1.2.3"},
    )
    assert r.status_code == 200
    payload = r.json()
    assert set(payload) == {"report_id", "status"}
    assert payload["status"] == "running"

    with api._event_lock:
        task = api._tasks.pop(payload["report_id"], None)
    if task is not None and hasattr(task, "cancel"):
        task.cancel()


def test_api_stays_responsive_while_a_blocking_pipeline_runs(client, monkeypatch):
    """The pipeline makes blocking HTTP calls; they must not freeze the API."""
    import time

    class SlowPipeline:
        def __init__(self, *a, **k):
            pass

        async def run(self, submission, *, source="api", report_id=None):
            time.sleep(1.5)  # a blocking call, like a synchronous inference request

    monkeypatch.setattr(api, "Pipeline", SlowPipeline)
    monkeypatch.setattr(api, "_check_access", lambda key: "judge")
    r = client.post("/api/reports", json={"report_text": "x", "package_spec": "a@1.0.0"})
    assert r.status_code == 200
    t0 = time.monotonic()
    assert client.get("/api/health").status_code == 200
    assert time.monotonic() - t0 < 0.7
    time.sleep(1.8)  # let the worker thread finish before the next test
