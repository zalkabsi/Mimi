"""End-to-end pipeline over FixtureExecutor + scripted fakes.

No network anywhere: a socket guard trips on any real connection, the
registry is served by a stub httpx.Client, and the LLM / Tavily / sandbox
layers are fakes. Safety properties asserted here:

- the dossier tier is always one of the four display values,
- events are non-empty typed StageEvents,
- cost fields stay None when nothing was measured (a metric is never invented),
- report prose never reaches the research layer.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from mimi.config import Settings, Stage
from mimi.db import Database
from mimi.pipeline import Pipeline
from mimi.sandboxes import FixtureExecutor
from mimi.schemas import Dossier, PublicIdentifiers, ReportSubmission, ResearchFindings, Tier
from mimi.redaction import build_queries

REPORT_TEXT = (
    "Our production service merges untrusted user objects into defaults and "
    "we observed prototype pollution through the merge helper at runtime. "
    "A minimal PoC follows in the report body; expected effect is a polluted "
    "Object.prototype after merging a crafted payload."
)

CLAIM = {
    "package": "lodash",
    "affected_versions": ["4.17.20"],
    "vuln_class": "prototype_pollution",
    "cited_files": [],
    "cited_symbols": [],
    "poc_code": None,
    "poc_command": None,
    "expected_effect": "Object.prototype gains an attacker-controlled key",
    "attack_vector": "merge of an untrusted object",
    "preconditions": [],
    "notes": None,
    "parse_warnings": [],
}


# ---------------------------------------------------------------------------
# Fakes: scripted LLM, scripted Tavily, stub registry httpx client
# ---------------------------------------------------------------------------

class FakeLLM:
    """Scripted stand-in for LLMClient (chat + chat_json). No network."""

    def __init__(self, *, claim: dict, hypotheses: list[dict], chat_text: str = "Scripted evidence rationale."):
        self.claim = claim
        self.hypotheses = hypotheses
        self.chat_text = chat_text
        self.chat_json_stages: list = []
        self.chat_stages: list = []

    def chat_json(self, *, stage, messages, schema_hint, **kwargs):
        self.chat_json_stages.append(stage)
        if stage is Stage.EXTRACT:
            return dict(self.claim)
        if stage is Stage.HYPOTHESIZE:
            return {"hypotheses": [dict(h) for h in self.hypotheses]}
        if stage is Stage.RESEARCH:
            return {
                "known_advisories": [],
                "duplicates": [],
                "fixed_version": None,
                "fix_commit": None,
                "notes": "",
            }
        raise AssertionError(f"unexpected chat_json stage: {stage}")

    def chat(self, *, stage, messages, **kwargs):
        self.chat_stages.append(stage)
        return SimpleNamespace(
            content=self.chat_text,
            model="fake-model",
            usage={},
            latency_ms=1.0,
            raw={},
        )

    def close(self) -> None:
        pass


class FakeTavily:
    """Scripted stand-in for TavilyClient. Records what would have been sent."""

    def __init__(self, findings: ResearchFindings):
        self.findings = findings
        self.calls: list[dict] = []

    def search(self, ids: PublicIdentifiers, report_text: str = "", max_results: int = 5) -> ResearchFindings:
        self.calls.append({"ids": ids, "report_text": report_text})
        return self.findings.model_copy(deep=True)

    def close(self) -> None:
        pass


class FakeRegistryResponse:
    def __init__(self, status_code: int = 200, data: dict | None = None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self) -> dict:
        return self._data

    def raise_for_status(self) -> None:
        return None


class FakeHttpClient:
    """httpx.Client stand-in for the npm-registry grounding check."""

    def __init__(self, *args, **kwargs):
        self.requests: list[str] = []

    def get(self, url: str, **kwargs) -> FakeRegistryResponse:
        self.requests.append(url)
        return FakeRegistryResponse(200, {"dist": {"tarball": ""}, "dependencies": {}})

    def close(self) -> None:
        pass


def hypothesis(hid: str, priority: int = 1) -> dict:
    return {
        "id": hid,
        "rationale": "test one shape of the reported merge bug",
        "test_plan": "run the reporter's PoC shape in the sandbox",
        "poc_code": "console.log('VULN_TRIGGERED')",
        "oracle": {
            "type": "output_regex",
            "description": "PoC prints the marker when the claim holds",
            "pattern": "VULN_TRIGGERED",
        },
        "priority": priority,
    }


def run_pipeline(
    monkeypatch,
    fixtures_dir,
    fixture_name: str,
    *,
    hypotheses: list[dict],
    findings: ResearchFindings,
    chat_text: str = "Scripted evidence rationale.",
):
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)
    settings = Settings()  # no env keys; nothing may go out anyway
    executor = FixtureExecutor(str(fixtures_dir / fixture_name))
    llm = FakeLLM(claim=CLAIM, hypotheses=hypotheses, chat_text=chat_text)
    tavily = FakeTavily(findings)
    pipeline = Pipeline(settings, executor=executor, llm=llm, tavily=tavily)
    submission = ReportSubmission(report_text=REPORT_TEXT, package_spec="lodash@4.17.20")
    dossier = asyncio.run(pipeline.run(submission, source="cli"))
    return dossier, llm, tavily


def assert_no_invented_metrics(dossier) -> None:
    """Unmeasured stays None — never a fabricated number."""
    assert dossier.cost.measured is False
    assert dossier.cost.inference_cost_usd is None
    assert dossier.cost.sandbox_cost is None
    assert dossier.cost.sandbox_cost_units is None
    assert dossier.cost.inference_tokens_in == 0
    assert dossier.cost.inference_tokens_out == 0
    for r in dossier.runs:
        assert r.cost is None
        assert r.cost_units is None


def assert_core_properties(dossier) -> None:
    assert dossier.tier in list(Tier)
    assert dossier.events, "events must not be empty"
    for ev in dossier.events:
        assert ev.report_id == dossier.report_id
        assert ev.stage
        assert ev.status in ("started", "ok", "error", "skipped")
    assert_no_invented_metrics(dossier)


# ---------------------------------------------------------------------------
# Scenario: fired on affected, not on fixed -> Confirmed
# ---------------------------------------------------------------------------

def test_pipeline_confirmed_flipped_differential(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(
        queries=["lodash 4.17.20 vulnerability"],
        known_advisories=[],
        fixed_version="4.17.21",
        used=True,
    )
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "confirmed.json",
        hypotheses=[hypothesis("h1")],
        findings=findings,
    )
    assert_core_properties(dossier)
    assert dossier.tier is Tier.CONFIRMED
    assert dossier.differential.ran is True
    assert dossier.differential.flipped is True
    assert dossier.differential.fixed_version == "4.17.21"

    phases = {r.phase for r in dossier.runs}
    assert "poc" in phases and "fixed" in phases
    fired = [r for r in dossier.oracle_results if r.fired]
    assert fired and all(r.phase == "affected" for r in fired)

    stages = {ev.stage for ev in dossier.events}
    for expected in ("extract", "ground", "research", "hypothesize", "build", "fork_run", "verdict", "reply"):
        assert expected in stages
    assert Stage.EXTRACT in llm.chat_json_stages
    assert Stage.HYPOTHESIZE in llm.chat_json_stages
    assert "VULN_TRIGGERED" in dossier.reply_draft or llm.chat_text == dossier.reply_draft


def test_pipeline_report_prose_never_reaches_research(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version="4.17.21")
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "confirmed.json",
        hypotheses=[hypothesis("h1")],
        findings=findings,
    )
    assert tavily.calls, "research layer must have been exercised"
    for call in tavily.calls:
        ids = call["ids"]
        assert isinstance(ids, PublicIdentifiers)
        blob = " ".join([ids.package, *ids.versions, *ids.advisory_ids, *ids.extra_terms]).lower()
        # the only non-identifier tokens allowed are vuln-class vocabulary
        for word in ("merge", "untrusted", "polluted", "payload", "production", "service"):
            assert word not in blob
        # the queries that would leave the system contain no report prose
        for q in build_queries(ids):
            for word in ("merge", "untrusted", "service", "payload"):
                assert word not in q.lower()


# ---------------------------------------------------------------------------
# Scenario: 3 hypotheses, 0 triggered -> Contradicted with coverage
# ---------------------------------------------------------------------------

def test_pipeline_contradicted_with_coverage(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=None, used=True)
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "contradicted.json",
        hypotheses=[hypothesis("h1"), hypothesis("h2", 2), hypothesis("h3", 3)],
        findings=findings,
    )
    assert_core_properties(dossier)
    assert dossier.tier is Tier.CONTRADICTED
    # All three hypotheses used the default RunConfig, so they are ONE
    # environment — "3 configs" would invent diversity that never ran.
    assert dossier.coverage.statement.startswith("3 hypotheses, 1 configs, 0 triggered")
    assert dossier.coverage.hypotheses_tested == 3
    assert dossier.coverage.configs_tested == 1
    assert dossier.coverage.hypotheses_triggered == 0
    assert "invalid" not in dossier.tier_rationale.lower()
    assert len(dossier.runs) == 3


def test_pipeline_configs_are_counted_per_environment(no_network, monkeypatch, fixtures_dir):
    # Same three hypotheses, but each pinned to a different Node version: the
    # coverage statement must then claim three configurations, because three
    # distinct environments really were exercised.
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=None, used=True)
    hs = []
    for i, node in enumerate(("16", "18", "20"), start=1):
        h = hypothesis(f"h{i}", i)
        h["node_version"] = node
        hs.append(h)
    dossier, llm, tavily = run_pipeline(
        monkeypatch, fixtures_dir, "contradicted.json", hypotheses=hs, findings=findings
    )
    assert dossier.tier is Tier.CONTRADICTED
    assert dossier.coverage.configs_tested == 3
    assert dossier.coverage.statement.startswith("3 hypotheses, 3 configs, 0 triggered")


def test_pipeline_contradicted_rationale_states_negative_result(no_network, monkeypatch, fixtures_dir):
    # When the narrating model contributes nothing, the deterministic
    # assign_tier rationale lands in the dossier: a coverage-quantified
    # negative result, never "invalid".
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=None, used=True)
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "contradicted.json",
        hypotheses=[hypothesis("h1"), hypothesis("h2", 2), hypothesis("h3", 3)],
        findings=findings,
        chat_text="",
    )
    assert dossier.tier is Tier.CONTRADICTED
    assert "negative result" in dossier.tier_rationale.lower()
    assert "3 hypotheses" in dossier.tier_rationale
    assert "invalid" not in dossier.tier_rationale.lower()


# ---------------------------------------------------------------------------
# Scenario: oracle fires on affected AND fixed -> Needs human
# ---------------------------------------------------------------------------

def test_pipeline_fired_on_both_versions_needs_human(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(
        queries=["lodash 4.17.20 vulnerability"],
        fixed_version="4.17.21",
        used=True,
    )
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "fired_both.json",
        hypotheses=[hypothesis("h1")],
        findings=findings,
    )
    assert_core_properties(dossier)
    assert dossier.tier is Tier.NEEDS_HUMAN
    assert dossier.differential.ran is True
    assert dossier.differential.flipped is False


# ---------------------------------------------------------------------------
# Scenario: build failed -> Needs human, nothing executed
# ---------------------------------------------------------------------------

def test_pipeline_build_failed_needs_human(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=None)
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "build_failed.json",
        hypotheses=[hypothesis("h1"), hypothesis("h2", 2)],
        findings=findings,
    )
    assert_core_properties(dossier)
    assert dossier.tier is Tier.NEEDS_HUMAN
    assert dossier.runs == []
    assert dossier.oracle_results == []
    build_events = [ev for ev in dossier.events if ev.stage == "build"]
    assert any(ev.status == "error" for ev in build_events)
    assert dossier.differential.ran is False


# ---------------------------------------------------------------------------
# Cross-cutting: network ban and honest cost
# ---------------------------------------------------------------------------

def test_pipeline_makes_no_network_calls(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version="4.17.21")
    dossier, llm, tavily = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "confirmed.json",
        hypotheses=[hypothesis("h1")],
        findings=findings,
    )
    # the only HTTP surface used is the stubbed registry client
    assert dossier.report_id
    assert llm.chat_stages  # LLM was the fake, not a real client
    assert tavily.calls


def test_pipeline_cost_stays_none_when_unmeasured(no_network, monkeypatch, fixtures_dir):
    findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version="4.17.21")
    dossier, _, _ = run_pipeline(
        monkeypatch,
        fixtures_dir,
        "confirmed.json",
        hypotheses=[hypothesis("h1")],
        findings=findings,
    )
    assert_no_invented_metrics(dossier)
    # events also carry no invented token counts
    for ev in dossier.events:
        assert ev.tokens_in is None
        assert ev.tokens_out is None
        assert ev.cost is None


def test_pipeline_tier_is_always_one_of_four(no_network, monkeypatch, fixtures_dir):
    cases = [
        ("confirmed.json", [hypothesis("h1")], "4.17.21"),
        ("contradicted.json", [hypothesis("h1"), hypothesis("h2", 2), hypothesis("h3", 3)], None),
        ("fired_both.json", [hypothesis("h1")], "4.17.21"),
        ("build_failed.json", [hypothesis("h1")], None),
    ]
    for fixture_name, hyps, fixed in cases:
        findings = ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=fixed)
        dossier, _, _ = run_pipeline(
            monkeypatch, fixtures_dir, fixture_name, hypotheses=hyps, findings=findings
        )
        assert dossier.tier in (Tier.CONFIRMED, Tier.LIKELY, Tier.NEEDS_HUMAN, Tier.CONTRADICTED)
        assert dossier.events


# ---------------------------------------------------------------------------
# Cost accounting must not invent dollars or milliseconds
# ---------------------------------------------------------------------------

def _event_dossier(events) -> Dossier:
    d = Dossier(report_id="c1", report_text="r", package_spec="lodash@4.17.20")
    d.events = list(events)
    return d


def test_cost_invented_zero_dollars_for_unpriced_model():
    # A model with no listed price means "unknown", not "$0.00". Reporting a
    # measured zero would be an invented metric.
    from mimi.schemas import StageEvent

    ev = StageEvent(
        ts="2026-10-06T00:00:00+00:00",
        report_id="c1",
        stage="extract",
        status="ok",
        model="nvidia/NVIDIA-Nemotron-3_5-Lightning",  # no price in the table
        tokens_in=1_000,
        tokens_out=200,
    )
    pipeline = Pipeline(Settings(), executor=FixtureExecutor("/dev/null"))
    cost = pipeline._cost_summary(_event_dossier([ev]), wall_clock_ms=12.0)
    assert cost.inference_tokens_in == 1_000
    assert cost.inference_tokens_out == 200
    assert cost.inference_cost_usd is None
    assert cost.measured is False


def test_cost_partial_pricing_is_not_summed_into_a_single_number():
    from mimi.schemas import StageEvent

    priced = StageEvent(
        ts="2026-10-06T00:00:00+00:00",
        report_id="c1",
        stage="extract",
        status="ok",
        model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        tokens_in=1_000_000,
        tokens_out=0,
    )
    unpriced = StageEvent(
        ts="2026-10-06T00:00:01+00:00",
        report_id="c1",
        stage="hypothesize",
        status="ok",
        model="nvidia/NVIDIA-Nemotron-3_5-Lightning",
        tokens_in=500_000,
        tokens_out=0,
    )
    pipeline = Pipeline(Settings(), executor=FixtureExecutor("/dev/null"))
    cost = pipeline._cost_summary(_event_dossier([priced, unpriced]), wall_clock_ms=5.0)
    # Half the tokens have no price: the total is unknown.
    assert cost.inference_cost_usd is None
    assert cost.measured is False


def test_cost_priced_models_are_summed_and_marked_measured():
    from mimi.schemas import StageEvent

    ev = StageEvent(
        ts="2026-10-06T00:00:00+00:00",
        report_id="c1",
        stage="extract",
        status="ok",
        model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        tokens_in=1_000_000,
        tokens_out=1_000_000,
    )
    pipeline = Pipeline(Settings(), executor=FixtureExecutor("/dev/null"))
    cost = pipeline._cost_summary(_event_dossier([ev]), wall_clock_ms=9.0)
    assert cost.inference_cost_usd == pytest.approx(0.06 + 0.24)
    assert cost.measured is True


def test_cost_elapsed_is_the_run_wall_clock_not_the_last_stage():
    from mimi.schemas import StageEvent

    evs = [
        StageEvent(ts="2026-10-06T00:00:00+00:00", report_id="c1", stage="extract", status="ok", latency_ms=3.0),
        StageEvent(ts="2026-10-06T00:00:05+00:00", report_id="c1", stage="verdict", status="ok", latency_ms=7.0),
    ]
    pipeline = Pipeline(Settings(), executor=FixtureExecutor("/dev/null"))
    cost = pipeline._cost_summary(_event_dossier(evs), wall_clock_ms=5000.0)
    assert cost.elapsed_ms == 5000.0
    assert cost.elapsed_ms != 7.0  # the last stage's own latency is not the run's


# ---------------------------------------------------------------------------
# A crashed run must not be stored as "complete"
# ---------------------------------------------------------------------------

def test_crashed_pipeline_persists_error_status(no_network, monkeypatch):
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)
    # A scratch db next to the tests: pytest's tmp_path is unavailable on this
    # Windows host (the shared temp root is not writable).
    db_path = Path(__file__).resolve().parent / "_test_crash.db"
    if db_path.exists():
        db_path.unlink()
    db = Database(str(db_path))
    try:
        settings = Settings(db_path=str(db_path))
        executor = FixtureExecutor("nonexistent.json")
        llm = FakeLLM(claim=CLAIM, hypotheses=[hypothesis("h1")])
        tavily = FakeTavily(ResearchFindings(used=False))
        pipeline = Pipeline(settings, executor=executor, llm=llm, tavily=tavily, db=db)

        def _explode(*a, **kw):
            raise RuntimeError("simulated stage crash")

        monkeypatch.setattr("mimi.pipeline.extract_claim", _explode)

        submission = ReportSubmission(report_text=REPORT_TEXT, package_spec="lodash@4.17.20")
        dossier = asyncio.run(pipeline.run(submission, source="cli"))

        # The dossier is still handed back as a Needs human result — a crash is
        # never a verdict.
        assert dossier.tier is Tier.NEEDS_HUMAN
        assert "simulated stage crash" in dossier.tier_rationale
        assert any("pipeline error" in lim for lim in dossier.limitations)

        assert db.get_report(dossier.report_id) is not None
        assert db.get_status(dossier.report_id) == "error"
    finally:
        db.close()
        if db_path.exists():
            db_path.unlink()
