"""Stages 5-6 — Build once, then fork per hypothesis.

The base environment is built a single time with network on (install only);
each hypothesis then runs as an independent fork from the kept image UUID,
with the PoC phase offline when ``unshare -n`` is available. Concurrency is
bounded (start with 8; the API caps at 50 concurrent instances).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..config import Settings
from ..events import EventLog
from ..oracles import check_oracle
from ..sandboxes import BuildResult, Executor
from ..schemas import Hypothesis, OracleResult, ReportSubmission, RunRecord


async def build_base(
    submission: ReportSubmission,
    hypotheses: list[Hypothesis],
    executor: Executor,
    settings: Settings,
    events: EventLog,
) -> BuildResult:
    """Build the pinned environment once. Network is on here only."""
    t0 = events.start("build", f"install {submission.package_spec}")
    config = hypotheses[0].config if hypotheses else None
    if config is None:
        from ..schemas import RunConfig

        config = RunConfig()
    result = await executor.build(
        config,
        package_spec=submission.package_spec,
        build_timeout_s=settings.build_timeout_s,
    )
    if not result.ok:
        events.error("build", t0, result.detail or "build failed")
    else:
        events.ok("build", t0, f"base image {result.image_id[:8]}", cost=result.cost, cost_units=result.cost_units)
    return result


async def run_hypotheses(
    hypotheses: list[Hypothesis],
    build: BuildResult,
    executor: Executor,
    settings: Settings,
    events: EventLog,
) -> tuple[list[RunRecord], list[OracleResult]]:
    """Fork once per hypothesis, bounded concurrency, oracle each run."""
    if not build.ok:
        events.skip("fork_run", "base build failed")
        return [], []

    sem = asyncio.Semaphore(max(1, settings.max_parallel_forks))
    runs: list[RunRecord] = []
    results: list[OracleResult] = []
    budget_left = settings.max_runs_per_report

    async def one(h: Hypothesis, index: int) -> None:
        nonlocal budget_left
        async with sem:
            if budget_left <= 0:
                events.skip("fork_run", f"{h.id}: run budget exhausted")
                return
            budget_left -= 1
            t0 = events.start("fork_run", f"{h.id}: {h.test_plan[:80]}")
            run = await executor.run_poc(
                build,
                h.config,
                poc_code=h.poc_code,
                hypothesis_id=h.id,
                timeout_s=settings.poc_timeout_s,
                offline=h.config.offline,
                phase="poc",
            )
            run.phase = "poc"
            runs.append(run)
            if run.error:
                events.error("fork_run", t0, f"{h.id}: {run.error}")
            else:
                events.ok(
                    "fork_run",
                    t0,
                    f"{h.id}: exit={run.exit_code} in {run.elapsed_ms:.0f}ms",
                    cost=run.cost,
                    cost_units=run.cost_units,
                    sandbox_run_ids=[run.sandbox_run_id] if run.sandbox_run_id else [],
                )
            idx = next((i for i, r in enumerate(runs) if r is run), 0)
            res = check_oracle(h.oracle, run, hypothesis_id=h.id, phase="affected", run_index=idx)
            results.append(res)
            events.emit(
                "fork_run",
                "ok",
                f"{h.id}: oracle {'FIRED' if res.fired else 'not fired'} — {res.detail}",
                data={"oracle_fired": res.fired},
            )

    await asyncio.gather(*(one(h, i) for i, h in enumerate(hypotheses)))
    return runs, results
