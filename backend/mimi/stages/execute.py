"""Stages 5-6 — Build per image configuration, then fork matching hypotheses.

Each distinct image configuration is built with network on for install only;
each hypothesis then runs as an independent fork from its matching image UUID.
The PoC phase is refused unless a child user and network namespace can be
created successfully.
Concurrency is
bounded (start with 8; the API caps at 50 concurrent instances).
"""

from __future__ import annotations

import asyncio
from typing import Mapping, Optional

from ..config import Settings
from ..events import EventLog
from ..oracles import check_oracle
from ..probe import probe_env_for
from ..sandboxes import BuildResult, Executor, RunBudget, build_group_key
from ..schemas import Hypothesis, OracleResult, OracleType, ReportSubmission, RunRecord


async def build_environments(
    submission: ReportSubmission,
    hypotheses: list[Hypothesis],
    executor: Executor,
    settings: Settings,
    events: EventLog,
    budget: Optional[RunBudget] = None,
) -> dict[str, BuildResult]:
    """Build one affected-version image per image-affecting configuration."""
    groups: dict[str, list[Hypothesis]] = {}
    for hypothesis in hypotheses:
        groups.setdefault(build_group_key(hypothesis.config), []).append(hypothesis)

    # Each required run needs an image, but hypotheses with identical image
    # settings share one build. Do not build groups beyond the remaining run
    # slots, and stop starting builds once measured cost reaches its threshold.
    eligible_groups = (
        {build_group_key(h.config) for h in hypotheses[:budget.remaining]}
        if budget is not None
        else set(groups)
    )
    builds: dict[str, BuildResult] = {}
    for key, members in groups.items():
        if key not in eligible_groups:
            events.skip("build", f"{key}: no run slot remains for this configuration")
            continue
        if budget is not None and not budget.can_continue():
            events.skip("build", f"{key}: measured cost/run threshold reached")
            continue

        config = members[0].config.model_copy(
            update={"package_spec": submission.package_spec, "offline": True}
        )
        t0 = events.start(
            "build", f"install {submission.package_spec} ({key})",
            data={"sandbox_operation": "build"},
        )
        result = await executor.build(
            config,
            package_spec=submission.package_spec,
            build_timeout_s=settings.build_timeout_s,
        )
        if budget is not None:
            budget.charge(result.cost)
        if not result.ok:
            events.error(
                "build", t0, result.detail or "build failed",
                cost=result.cost, cost_units=result.cost_units,
                data={"sandbox_operation": "build"},
            )
        else:
            events.ok(
                "build", t0, f"image {result.image_id[:8]} ready ({key})",
                cost=result.cost, cost_units=result.cost_units,
                data={"sandbox_operation": "build"},
            )
        builds[key] = result
    return builds


async def run_hypotheses(
    hypotheses: list[Hypothesis],
    build: BuildResult | Mapping[str, BuildResult],
    executor: Executor,
    settings: Settings,
    events: EventLog,
    budget: Optional[RunBudget] = None,
) -> tuple[list[RunRecord], list[OracleResult]]:
    """Fork once per hypothesis, bounded concurrency, oracle each run.

    ``budget`` is the report-wide allowance shared with the differential;
    pass the same object so every PoC execution is charged once. When omitted
    a fresh allowance of ``max_runs_per_report`` is used, which is the correct
    contract for a caller that only runs this stage. A mapping supplies a
    separate build for each image-affecting configuration; a single
    ``BuildResult`` remains supported for stage-level callers.
    """
    if isinstance(build, BuildResult) and not build.ok:
        events.skip("fork_run", "base build failed")
        return [], []

    if budget is None:
        budget = RunBudget(settings.max_runs_per_report)
    sem = asyncio.Semaphore(max(1, settings.max_parallel_forks))
    runs: list[RunRecord] = []
    results: list[OracleResult] = []

    async def one(h: Hypothesis, index: int) -> None:
        async with sem:
            image = (
                build
                if isinstance(build, BuildResult)
                else build.get(build_group_key(h.config))
            )
            if image is None:
                events.skip("fork_run", f"{h.id}: no built image for its configuration")
                return
            if not image.ok:
                events.skip("fork_run", f"{h.id}: its configuration build failed")
                return
            if not budget.take():
                events.skip("fork_run", f"{h.id}: run budget exhausted")
                return
            t0 = events.start(
                "fork_run", f"{h.id}: {h.test_plan[:80]}",
                data={"sandbox_operation": "run"},
            )
            run = await executor.run_poc(
                image,
                h.config,
                poc_code=h.poc_code,
                hypothesis_id=h.id,
                timeout_s=settings.poc_timeout_s,
                offline=h.config.offline,
                phase="poc",
                probe_env=probe_env_for(h.oracle),
                probe_snippet=(
                    h.oracle.probe_snippet
                    if h.oracle.type is OracleType.CUSTOM_PROBE
                    else None
                ),
            )
            budget.charge(run.cost)
            run.phase = "poc"
            runs.append(run)
            if run.error:
                events.error(
                    "fork_run", t0, f"{h.id}: {run.error}",
                    cost=run.cost, cost_units=run.cost_units,
                    sandbox_run_ids=[run.sandbox_run_id] if run.sandbox_run_id else [],
                    data={"sandbox_operation": "run"},
                )
            else:
                events.ok(
                    "fork_run",
                    t0,
                    f"{h.id}: exit={run.exit_code} in {run.elapsed_ms:.0f}ms",
                    cost=run.cost,
                    cost_units=run.cost_units,
                    sandbox_run_ids=[run.sandbox_run_id] if run.sandbox_run_id else [],
                    data={"sandbox_operation": "run"},
                )
            res = check_oracle(
                h.oracle,
                run,
                hypothesis_id=h.id,
                phase="affected",
                run_index=len(runs) - 1,
            )
            results.append(res)
            if res.conclusive:
                verdict = "FIRED" if res.fired else "not fired"
            else:
                verdict = "inconclusive"
            events.emit(
                "fork_run",
                "ok",
                f"{h.id}: oracle {verdict} — {res.detail}",
                data={"oracle_fired": res.fired, "conclusive": res.conclusive},
            )

    await asyncio.gather(*(one(h, i) for i, h in enumerate(hypotheses)))
    return runs, results
