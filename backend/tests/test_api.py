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
import threading
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
    for path in (_TEST_DB, Path(f"{_TEST_DB}-wal"), Path(f"{_TEST_DB}-shm")):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def _clean_api_state():
    """Each test starts with no live subscribers or tasks."""
    with api._event_lock:
        api._event_queues.clear()
        api._tasks.clear()
    yield
    with api._event_lock:
        api._event_queues.clear()
        api._tasks.clear()


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
        assert "r1" not in api._tasks


def test_late_subscriber_to_a_finished_run_gets_no_live_queue():
    api._finish("r1")
    with api._event_lock:
        assert "r1" not in api._event_queues
        assert "r1" not in api._tasks


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


def test_live_job_keeps_http_responsive_and_is_readable_before_completion(monkeypatch):
    """A blocking model call must not freeze the API or the first report read."""
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")

    class BlockingPipeline:
        def __init__(self, settings, *, db, on_event):
            self.db = db
            self.on_event = on_event

        async def run(self, submission, *, source, report_id):
            entered.set()
            try:
                # Represents the synchronous HTTP clients used in extraction,
                # grounding and research. No real provider calls in this test.
                assert release.wait(timeout=5), "test never released the model call"
                dossier = self.db.get_report(report_id)
                assert dossier is not None
                self.db.upsert_report(dossier, status="complete")
            finally:
                finished.set()

    monkeypatch.setattr(api, "Pipeline", BlockingPipeline)
    headers = {"X-Mimi-Key": "judge-secret"}
    rid = None
    try:
        with TestClient(api.app) as live_client:
            response = live_client.post(
                "/api/reports",
                headers=headers,
                json={"report_text": "A public test report", "package_spec": "lodash@4.17.20"},
            )
            assert response.status_code == 200
            rid = response.json()["report_id"]
            assert entered.wait(timeout=2)
            assert not finished.is_set(), "the response waited for the blocking model call"
            assert live_client.get("/api/health").status_code == 200
            initial = live_client.get(f"/api/reports/{rid}", headers=headers)
            assert initial.status_code == 200
            assert initial.json()["package_spec"] == "lodash@4.17.20"
            assert api._db.get_status(rid) == "running"
            release.set()
            assert finished.wait(timeout=2)
            with live_client.stream("GET", f"/api/reports/{rid}/stream", headers=headers) as stream:
                assert "event: done" in stream.read().decode()
    finally:
        release.set()
        if rid:
            api._db.delete_report(rid)


def test_unexpected_worker_failure_saves_a_readable_error_and_ends_the_stream(monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")

    class ExplodingPipeline:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, *args, **kwargs):
            raise RuntimeError("simulated worker failure")

    monkeypatch.setattr(api, "Pipeline", ExplodingPipeline)
    headers = {"X-Mimi-Key": "judge-secret"}
    rid = None
    try:
        with TestClient(api.app) as live_client:
            response = live_client.post(
                "/api/reports", headers=headers,
                json={"report_text": "Public test report", "package_spec": "lodash@4.17.20"},
            )
            rid = response.json()["report_id"]
            with live_client.stream("GET", f"/api/reports/{rid}/stream", headers=headers) as stream:
                assert "event: done" in stream.read().decode()
            dossier = live_client.get(f"/api/reports/{rid}", headers=headers).json()
            assert dossier["tier"] == "Needs human"
            assert "simulated worker failure" in dossier["tier_rationale"]
            events = live_client.get(f"/api/reports/{rid}/events", headers=headers).json()
            assert events[-1]["data"]["final"] is True
            assert events[-1]["status"] == "error"
            assert api._db.get_status(rid) == "error"
    finally:
        if rid:
            api._db.delete_report(rid)


def test_unknown_report_id_is_hidden_until_authenticated(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    assert client.get("/api/reports/does-not-exist").status_code == 401
    r = client.get(
        "/api/reports/does-not-exist", headers={"X-Mimi-Key": "judge-secret"}
    )
    assert r.status_code == 404


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


def test_stream_hides_unknown_report_id_until_authenticated(client, monkeypatch):
    # Refuse unauthenticated ID probes before distinguishing a missing report.
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    report_id = uuid.uuid4().hex[:12]
    r = client.get(f"/api/reports/{report_id}/stream")
    assert r.status_code == 401
    r = client.get(
        f"/api/reports/{report_id}/stream", headers={"X-Mimi-Key": "judge-secret"}
    )
    assert r.status_code == 404


def test_stream_for_finished_run_replays_history_and_terminates(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    rid = uuid.uuid4().hex[:12]
    dossier = Dossier(report_id=rid, report_text="r", package_spec="lodash@4.17.20")
    api._db.upsert_report(dossier, status="complete")
    log = EventLog(rid, sink=lambda ev: api._db.add_event(rid, ev))
    log.emit("extract", "ok", "claim extracted")
    log.emit("verdict", "ok", "tier=likely")
    api._finish(rid)

    with client.stream(
        "GET", f"/api/reports/{rid}/stream", headers={"X-Mimi-Key": "judge-secret"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())

    # History is replayed, and the stream CLOSED rather than keep-aliving.
    assert "claim extracted" in body
    assert "tier=likely" in body


def test_stream_for_run_still_running_terminates_after_finish(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
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

    with client.stream(
        "GET", f"/api/reports/{rid}/stream", headers={"X-Mimi-Key": "judge-secret"}
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())

    assert "built base image" in body


def test_submit_and_get_report_roundtrip_shape(client, monkeypatch):
    monkeypatch.setenv("MIMI_JUDGE_KEY", "judge-secret")
    # The worker may start immediately, including when the developer has live
    # credentials configured. Stub it rather than relying on cancellation to
    # prevent this HTTP-contract test from spending credits.
    class NoProviderPipeline:
        def __init__(self, settings, *, db, on_event):
            self.db = db

        async def run(self, submission, *, source, report_id):
            self.db.update_status(report_id, "complete")

    monkeypatch.setattr(api, "Pipeline", NoProviderPipeline)
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
