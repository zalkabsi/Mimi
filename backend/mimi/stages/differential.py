"""Stage 7 — Differential: the same oracle on the fixed version.

If the oracle fires on the affected version and not on the fixed version, it
measures the bug rather than an artifact. A wrong "fixed" version would
poison this, so the fixed version must come from research evidence, never
from the model's memory.

Flip definition: at least one hypothesis fired on the affected version, and
none of those fired on the fixed version.
"""

from __future__ import annotations

from typing import Optional

from ..config import Settings
from ..events import EventLog
from ..oracles import check_oracle
from ..probe import probe_env_for
from ..sandboxes import Executor, RunBudget
from ..schemas import (
    DifferentialResult,
    Hypothesis,
    OracleResult,
    ReportSubmission,
    ResearchFindings,
    RunConfig,
    RunRecord,
)


async def run_differential(
    submission: ReportSubmission,
    hypotheses: list[Hypothesis],
    affected_results: list[OracleResult],
    findings: ResearchFindings,
    executor: Executor,
    settings: Settings,
    events: EventLog,
    budget: Optional[RunBudget] = None,
) -> tuple[DifferentialResult, list[RunRecord]]:
    """Returns the differential verdict and the fixed-phase runs it produced.

    Each fixed-version re-run is one PoC execution and draws from ``budget`` —
    the same allowance the affected-phase forks used. A re-check stopped early
    by the budget leaves the flip UNKNOWN: claiming a flip over a subset would
    be a coverage lie if a skipped hypothesis still fires on the fixed version.
    """
    t0 = events.start("differential", f"fixed version: {findings.fixed_version or 'unknown'}")

    fixed = findings.fixed_version
    if not fixed:
        result = DifferentialResult(ran=False, detail="no fixed version known from research; skipped")
        events.skip("differential", result.detail)
        return result, []

    fired_ids = [
        r.hypothesis_id
        for r in affected_results
        if r.phase == "affected" and r.conclusive and r.fired
    ]
    by_id = {h.id: h for h in hypotheses}
    to_check = [by_id[hid] for hid in fired_ids if hid in by_id]

    if not to_check:
        result = DifferentialResult(
            fixed_version=fixed,
            ran=False,
            detail="no hypothesis fired on the affected version, so there is no flip to confirm",
        )
        events.skip("differential", result.detail)
        return result, []

    proto = to_check[0].config
    config = RunConfig(
        node_version=proto.node_version,
        package_spec=f"{submission.package}@{fixed}",
        install_command=proto.install_command,
        poc_command=proto.poc_command,
        setup_commands=list(proto.setup_commands),
        offline=True,
    )

    build = await executor.build(
        config,
        package_spec=config.package_spec or f"{submission.package}@{fixed}",
        build_timeout_s=settings.build_timeout_s,
    )
    if not build.ok:
        result = DifferentialResult(
            fixed_version=fixed,
            ran=False,
            detail=f"fixed-version build failed: {build.detail}",
        )
        events.error("differential", t0, result.detail)
        return result, []

    runs: list[RunRecord] = []
    results: list[OracleResult] = []
    if budget is None:
        budget = RunBudget(settings.max_runs_per_report)
    skipped_budget = 0
    # Deterministic order, and every hypothesis that fired is re-checked — not
    # "the first three to finish". A flip claimed over a subset would be a
    # coverage lie if a later hypothesis still fires on the fixed version.
    for index, h in enumerate(to_check):
        if not budget.take():
            skipped_budget += 1
            events.skip(
                "differential",
                f"{h.id}: run budget exhausted; fixed-version re-check skipped",
            )
            continue
        run = await executor.run_poc(
            build,
            config,
            poc_code=h.poc_code,
            hypothesis_id=h.id,
            timeout_s=settings.poc_timeout_s,
            offline=True,
            phase="fixed",
            probe_env=probe_env_for(h.oracle),
        )
        run.phase = "fixed"
        run.sandbox_image_id = build.image_id
        runs.append(run)
        results.append(
            check_oracle(h.oracle, run, hypothesis_id=h.id, phase="fixed", run_index=index)
        )

    if skipped_budget and not results:
        result = DifferentialResult(
            fixed_version=fixed,
            fix_commit=findings.fix_commit,
            ran=False,
            detail=(
                f"run budget exhausted before any fixed-version re-check "
                f"({len(to_check)} hypothesis(es) were queued on {submission.package}@{fixed})"
            ),
        )
        events.skip("differential", result.detail)
        return result, []

    conclusive = [r for r in results if r.conclusive]
    fixed_fired = {r.hypothesis_id for r in conclusive if r.fired}
    errored = [r for r in results if not r.conclusive]

    # Flip definition (honest): every hypothesis that fired on the affected
    # version was re-checked to a judgment on the fixed one, and none of those
    # judgments fired. Anything less — a re-run that errored, or one skipped on
    # the run budget — leaves the flip UNKNOWN, not False and certainly not
    # True. An unknown flip must never upgrade the tier.
    if skipped_budget or errored:
        reasons = []
        if skipped_budget:
            reasons.append(f"{skipped_budget} skipped on the run budget")
        if errored:
            reasons.append(f"{len(errored)} did not reach a judgment")
        flipped = None
        detail = (
            f"{len(results)} of {len(to_check)} hypothesis(es) re-run on "
            f"{submission.package}@{fixed} ({'; '.join(reasons)}), so the flip is unconfirmed"
        )
    else:
        flipped = bool(conclusive) and len(fixed_fired) == 0
        detail = (
            f"{len(conclusive)} hypothesis(es) re-run on {submission.package}@{fixed}: "
            f"{len(fixed_fired)} still fire there"
        )

    result = DifferentialResult(
        fixed_version=fixed,
        fix_commit=findings.fix_commit,
        ran=True,
        flipped=flipped,
        detail=detail,
        oracle_results=results,
    )
    events.ok("differential", t0, result.detail)
    return result, runs
