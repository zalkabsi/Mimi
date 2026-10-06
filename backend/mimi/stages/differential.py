"""Stage 7 — Differential: the same oracle on the fixed version.

If the oracle fires on the affected version and not on the fixed version, it
measures the bug rather than an artifact. A wrong "fixed" version would
poison this, so the fixed version must come from research evidence, never
from the model's memory.

Flip definition: at least one hypothesis fired on the affected version, and
none of those fired on the fixed version.
"""

from __future__ import annotations

from ..config import Settings
from ..events import EventLog
from ..oracles import check_oracle
from ..sandboxes import Executor
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
) -> tuple[DifferentialResult, list[RunRecord]]:
    """Returns the differential verdict and the fixed-phase runs it produced."""
    t0 = events.start("differential", f"fixed version: {findings.fixed_version or 'unknown'}")

    fixed = findings.fixed_version
    if not fixed:
        result = DifferentialResult(ran=False, detail="no fixed version known from research; skipped")
        events.skip("differential", result.detail)
        return result, []

    fired_ids = [r.hypothesis_id for r in affected_results if r.phase == "affected" and r.fired]
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
    for h in to_check[:3]:  # a flip needs at most a few confirmations
        run = await executor.run_poc(
            build,
            config,
            poc_code=h.poc_code,
            hypothesis_id=h.id,
            timeout_s=settings.poc_timeout_s,
            offline=True,
            phase="fixed",
        )
        run.phase = "fixed"
        run.sandbox_image_id = build.image_id
        runs.append(run)
        results.append(
            check_oracle(h.oracle, run, hypothesis_id=h.id, phase="fixed", run_index=len(runs) - 1)
        )

    fixed_fired = {r.hypothesis_id for r in results if r.fired}
    flipped = len(fixed_fired) == 0 and bool(results)

    result = DifferentialResult(
        fixed_version=fixed,
        fix_commit=findings.fix_commit,
        ran=True,
        flipped=flipped,
        detail=(
            f"{len(results)} hypothesis(es) re-run on {submission.package}@{fixed}: "
            f"{len(fixed_fired)} still fire there"
        ),
        oracle_results=results,
    )
    events.ok("differential", t0, result.detail)
    return result, runs
