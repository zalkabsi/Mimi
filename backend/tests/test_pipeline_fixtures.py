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
from types import SimpleNamespace

import httpx
import pytest

from mimi.config import Settings, Stage
from mimi.pipeline import Pipeline
from mimi.sandboxes import FixtureExecutor
from mimi.schemas import PublicIdentifiers, ReportSubmission, ResearchFindings, Tier
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
    assert dossier.coverage.statement.startswith("3 hypotheses, 3 configs, 0 triggered")
    assert dossier.coverage.hypotheses_tested == 3
    assert dossier.coverage.hypotheses_triggered == 0
    assert "invalid" not in dossier.tier_rationale.lower()
    assert len(dossier.runs) == 3


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
