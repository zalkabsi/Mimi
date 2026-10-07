"""The run budget is shared by every stage that executes a PoC.

``max_runs_per_report`` bounds *executions*, not hypotheses. Before it was
threaded through the differential, a report with many firing hypotheses ran
up to twice the cap: each fixed-version re-check was free. Worse, a flip
claimed after a budget-truncated re-check would have been a coverage lie —
a skipped hypothesis might still fire on the fixed version.

Pinned here: one shared ``RunBudget`` charges affected forks and fixed
re-checks alike, a partial re-check never reports ``flipped=True``, and the
pipeline cannot exceed ``max_runs_per_report`` run records.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from mimi.config import Settings
from mimi.events import EventLog
from mimi.sandboxes import BuildResult, RunBudget
from mimi.schemas import Hypothesis, Oracle, OracleType, ReportSubmission, ResearchFindings, RunRecord
from mimi.stages.differential import run_differential
from mimi.stages.execute import run_hypotheses


# ---------------------------------------------------------------------------
# A counting executor: records every run_poc call, fires when asked to.
# ---------------------------------------------------------------------------

class CountingExecutor:
    name = "counting"

    def __init__(self, *, fire_on_poc: bool = True, fire_on_fixed: bool = False, fail_fixed: bool = False):
        self.calls: list[str] = []  # phase of each run_poc
        self.fire_on_poc = fire_on_poc
        self.fire_on_fixed = fire_on_fixed
        self.fail_fixed = fail_fixed

    async def build(self, config, *, package_spec: str, build_timeout_s: int) -> BuildResult:
        return BuildResult(image_id="img-budget", ok=True, detail="fixture build")

    async def run_poc(
        self,
        build: BuildResult,
        config,
        *,
        poc_code: str,
        hypothesis_id: str,
        timeout_s: int,
        offline: bool = True,
        phase: str = "poc",
        probe_env=None,
        probe_snippet: str | None = None,
    ) -> RunRecord:
        self.calls.append(phase)
        if phase == "fixed" and self.fail_fixed:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase="fixed",
                command=config.poc_command,
                error="fixed run failed",
            )
        fired = self.fire_on_poc if phase != "fixed" else self.fire_on_fixed
        return RunRecord(
            hypothesis_id=hypothesis_id,
            phase="fixed" if phase == "fixed" else "poc",
            command=config.poc_command,
            exit_code=0,
            stdout="VULN_TRIGGERED\n" if fired else "clean\n",
        )

    async def close(self) -> None:
        return None


def hypothesis(hid: str) -> Hypothesis:
    return Hypothesis(
        id=hid,
        rationale="one shape of the reported bug",
        test_plan="run the PoC shape in the sandbox",
        poc_code="console.log('VULN_TRIGGERED')",
        oracle=Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED"),
    )


def submission() -> ReportSubmission:
    return ReportSubmission(report_text="report body", package_spec="lodash@4.17.20")


def findings(fixed: str | None) -> ResearchFindings:
    return ResearchFindings(queries=["lodash 4.17.20 vulnerability"], fixed_version=fixed)


# ---------------------------------------------------------------------------
# The budget object itself
# ---------------------------------------------------------------------------

def test_run_budget_take_until_exhausted():
    budget = RunBudget(2)
    assert budget.take() is True
    assert budget.take() is True
    assert budget.take() is False
    assert budget.remaining == 0


def test_run_budget_refuses_when_started_empty():
    budget = RunBudget(0)
    assert budget.take() is False
    assert budget.remaining == 0


# ---------------------------------------------------------------------------
# Stage 5-6: affected-phase forks draw from the budget
# ---------------------------------------------------------------------------

def test_hypotheses_stop_at_the_budget():
    budget = RunBudget(2)
    executor = CountingExecutor()
    events = EventLog("budget-1")
    runs, results = asyncio.run(
        run_hypotheses(
            [hypothesis(f"h{i}") for i in range(4)],
            BuildResult(image_id="img", ok=True),
            executor,
            Settings(),
            events,
            budget=budget,
        )
    )
    assert len(runs) == 2
    assert len(results) == 2
    assert executor.calls == ["poc", "poc"]
    assert budget.remaining == 0
    skipped = [ev for ev in events.events if ev.status == "skipped" and "budget" in ev.detail]
    assert len(skipped) == 2, "the two hypotheses that never ran are recorded as skipped"


def test_hypotheses_without_a_budget_use_the_settings_cap():
    settings = Settings(max_runs_per_report=1)
    executor = CountingExecutor()
    runs, _ = asyncio.run(
        run_hypotheses(
            [hypothesis("h1"), hypothesis("h2")],
            BuildResult(image_id="img", ok=True),
            executor,
            settings,
            EventLog("budget-2"),
        )
    )
    assert len(runs) == 1
    assert executor.calls == ["poc"]


# ---------------------------------------------------------------------------
# Stage 7: the differential draws from the SAME budget
# ---------------------------------------------------------------------------

def test_differential_draws_from_the_shared_budget():
    # 3 firing hypotheses consume the whole allowance; the fixed-version
    # re-checks are then unaffordable and must not run.
    budget = RunBudget(3)
    executor = CountingExecutor(fire_on_poc=True, fire_on_fixed=False)
    events = EventLog("budget-3")
    settings = Settings()
    hyps = [hypothesis(f"h{i}") for i in range(1, 4)]
    runs, results = asyncio.run(
        run_hypotheses(hyps, BuildResult(image_id="img", ok=True), executor, settings, events, budget=budget)
    )
    assert len(runs) == 3

    diff, fixed_runs = asyncio.run(
        run_differential(
            submission(), hyps, results, findings("4.17.21"), executor, settings, events, budget=budget
        )
    )
    assert fixed_runs == []
    assert executor.calls == ["poc", "poc", "poc"], "no free fixed-version executions"
    assert diff.ran is False
    assert diff.flipped is None
    assert "budget" in diff.detail
    assert budget.remaining == 0


def test_differential_charges_each_fixed_run():
    budget = RunBudget(10)
    executor = CountingExecutor(fire_on_poc=True, fire_on_fixed=False)
    events = EventLog("budget-4")
    settings = Settings()
    hyps = [hypothesis("h1"), hypothesis("h2")]
    _, results = asyncio.run(
        run_hypotheses(hyps, BuildResult(image_id="img", ok=True), executor, settings, events, budget=budget)
    )
    assert budget.remaining == 8

    diff, fixed_runs = asyncio.run(
        run_differential(
            submission(), hyps, results, findings("4.17.21"), executor, settings, events, budget=budget
        )
    )
    assert len(fixed_runs) == 2
    assert diff.ran is True
    assert diff.flipped is True
    assert budget.remaining == 6, "2 affected forks + 2 fixed re-checks charged once each"
    assert executor.calls == ["poc", "poc", "fixed", "fixed"]


def test_partial_recheck_is_not_a_flip():
    # Room for exactly one of two re-checks. The flip is UNKNOWN: the skipped
    # hypothesis might still fire on the fixed version.
    budget = RunBudget(3)  # 2 poc + 1 fixed
    executor = CountingExecutor(fire_on_poc=True, fire_on_fixed=False)
    events = EventLog("budget-5")
    settings = Settings()
    hyps = [hypothesis("h1"), hypothesis("h2")]
    _, results = asyncio.run(
        run_hypotheses(hyps, BuildResult(image_id="img", ok=True), executor, settings, events, budget=budget)
    )
    assert budget.remaining == 1

    diff, fixed_runs = asyncio.run(
        run_differential(
            submission(), hyps, results, findings("4.17.21"), executor, settings, events, budget=budget
        )
    )
    assert len(fixed_runs) == 1
    assert diff.ran is True
    assert diff.flipped is None, "a flip claimed over a subset is a coverage lie"
    assert "budget" in diff.detail
    assert "unconfirmed" in diff.detail


def test_errored_recheck_is_also_not_a_flip():
    budget = RunBudget(10)
    executor = CountingExecutor(fire_on_poc=True, fire_on_fixed=False, fail_fixed=True)
    events = EventLog("budget-6")
    settings = Settings()
    hyps = [hypothesis("h1")]
    _, results = asyncio.run(
        run_hypotheses(hyps, BuildResult(image_id="img", ok=True), executor, settings, events, budget=budget)
    )
    diff, _ = asyncio.run(
        run_differential(
            submission(), hyps, results, findings("4.17.21"), executor, settings, events, budget=budget
        )
    )
    assert diff.ran is True
    assert diff.flipped is None
    assert "judgment" in diff.detail


# ---------------------------------------------------------------------------
# End-to-end: the pipeline never exceeds max_runs_per_report run records
# ---------------------------------------------------------------------------

def test_pipeline_respects_max_runs_per_report():
    from mimi.pipeline import Pipeline
    from mimi.schemas import Dossier, Tier

    class ScriptedLLM:
        def chat_json(self, *, stage, messages, schema_hint, **kwargs):
            from mimi.config import Stage

            if stage is Stage.EXTRACT:
                return {
                    "package": "lodash",
                    "affected_versions": ["4.17.20"],
                    "vuln_class": "prototype_pollution",
                    "cited_files": [],
                    "cited_symbols": [],
                    "poc_code": None,
                    "poc_command": None,
                    "expected_effect": "Object.prototype gains a key",
                    "attack_vector": "merge",
                    "preconditions": [],
                    "notes": None,
                    "parse_warnings": [],
                }
            if stage is Stage.HYPOTHESIZE:
                return {
                    "hypotheses": [
                        {
                            "id": f"h{i}",
                            "rationale": "shape of the bug",
                            "test_plan": "run the PoC",
                            "poc_code": "console.log('VULN_TRIGGERED')",
                            "oracle": {"type": "output_regex", "pattern": "VULN_TRIGGERED"},
                            "priority": i,
                        }
                        for i in range(1, 5)
                    ]
                }
            return {
                "known_advisories": [],
                "duplicates": [],
                "fixed_version": "4.17.21",
                "fix_commit": None,
                "notes": "",
            }

        def chat(self, *, stage, messages, **kwargs):
            return SimpleNamespace(content="scripted", model="fake", usage={}, latency_ms=1.0, raw={})

        def close(self) -> None:
            pass

    class NoResearch:
        def search(self, *a, **kw):
            return ResearchFindings(used=False)

        def close(self) -> None:
            pass

    import httpx

    class NoHttp:
        def __init__(self, *a, **kw):
            pass

        def get(self, url, **kw):
            return SimpleNamespace(status_code=200, json=lambda: {}, raise_for_status=lambda: None)

        def close(self) -> None:
            pass

    real_client = httpx.Client
    httpx.Client = NoHttp  # grounding must not reach the registry
    try:
        settings = Settings(max_runs_per_report=2)  # 4 hypotheses, only 2 may execute
        executor = CountingExecutor(fire_on_poc=True, fire_on_fixed=False)
        pipeline = Pipeline(
            settings,
            executor=executor,
            llm=ScriptedLLM(),
            tavily=NoResearch(),
        )
        dossier = asyncio.run(pipeline.run(submission(), source="cli"))
    finally:
        httpx.Client = real_client

    assert isinstance(dossier, Dossier)
    assert len(dossier.runs) == 2, "the cap binds on executions, not on hypotheses"
    assert executor.calls == ["poc", "poc"], "the differential had no budget left"
    assert dossier.tier in list(Tier)
    # Coverage must not claim four tested hypotheses when only two ran.
    assert dossier.coverage.hypotheses_tested <= 2
