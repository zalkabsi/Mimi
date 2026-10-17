"""Stage 7 — Differential: the same oracle on the fixed version.

If the oracle fires on the affected version and not on the fixed version, it
measures the bug rather than an artifact. A wrong "fixed" version would
poison this, so the fixed version must come from research evidence, never
from the model's memory.

Flip definition: at least one hypothesis fired on the affected version, and
none of those fired on the fixed version.

Each hypothesis is re-run under **its own** configuration (node version,
install command, setup, PoC file name, env), pinned to the fixed package
version. Re-running every hypothesis under one prototype config would
confound the flip: a result that stayed quiet could be due to the different
environment rather than the fix.
"""

from __future__ import annotations

from typing import Optional

from ..config import Settings
from ..events import EventLog
from ..oracles import check_oracle
from ..probe import probe_env_for
from ..sandboxes import BuildResult, Executor, RunBudget, build_group_key as image_group_key
from ..schemas import (
    DifferentialResult,
    Hypothesis,
    OracleResult,
    OracleType,
    ReportSubmission,
    ResearchFindings,
    RunConfig,
    RunRecord,
)


def build_group_key(h: Hypothesis) -> str:
    """Fingerprint of the parts of a config that affect the built image.

    Only node version, install command and setup matter to the image. PoC
    file/command/env do not, so hypotheses that differ only in those share one
    fixed-version build while still re-running under their own full config.
    """
    return image_group_key(h.config)


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

    if budget is None:
        budget = RunBudget(settings.max_runs_per_report)

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

    # Each hypothesis keeps its own environment; only the package version
    # moves to the fixed one. Builds are grouped by the parts of the config
    # that affect the image (node version, install, setup) so one image serves
    # every hypothesis that would have shared it in the affected phase.
    groups: dict[str, list[Hypothesis]] = {}
    for h in to_check:
        groups.setdefault(build_group_key(h), []).append(h)

    # Do not build fixed-version images for hypotheses that cannot fit in the
    # remaining execution allowance. Several hypotheses can still share one
    # build, so derive the needed groups from the first eligible run slots.
    buildable_groups = {
        build_group_key(h) for h in to_check[:budget.remaining]
    }
    builds: dict[str, "BuildResult"] = {}
    for key, members in groups.items():
        if key not in buildable_groups or not budget.can_continue():
            continue
        proto = members[0].config
        config = RunConfig(
            node_version=proto.node_version,
            package_spec=f"{submission.package}@{fixed}",
            install_command=proto.install_command,
            poc_file_name=proto.poc_file_name,
            poc_command=proto.poc_command,
            env=dict(proto.env),
            setup_commands=list(proto.setup_commands),
            offline=True,
        )
        build_t0 = events.start(
            "differential", f"build fixed version for {submission.package}@{fixed}",
            data={"sandbox_operation": "build"},
        )
        build = await executor.build(
            config,
            package_spec=config.package_spec or f"{submission.package}@{fixed}",
            build_timeout_s=settings.build_timeout_s,
        )
        budget.charge(build.cost)
        if not build.ok:
            events.error(
                "differential",
                build_t0,
                f"fixed-version build failed for {submission.package}@{fixed}: {build.detail}",
                cost=build.cost,
                cost_units=build.cost_units,
                data={"sandbox_operation": "build"},
            )
        else:
            events.ok(
                "differential",
                build_t0,
                f"fixed-version image ready for {submission.package}@{fixed}",
                cost=build.cost,
                cost_units=build.cost_units,
                data={"sandbox_operation": "build"},
            )
        builds[key] = build

    ok_builds = {k: b for k, b in builds.items() if getattr(b, "ok", False)}
    if not ok_builds:
        budget_blocked = not budget.can_continue() or len(buildable_groups) < len(groups)
        detail = (
            f"fixed-version build was skipped or stopped at the measured run budget for "
            f"{submission.package}@{fixed}"
            if budget_blocked
            else f"fixed-version build failed on {submission.package}@{fixed}"
        )
        result = DifferentialResult(
            fixed_version=fixed,
            ran=False,
            detail=detail,
        )
        if budget_blocked:
            events.skip("differential", result.detail)
        else:
            events.error("differential", t0, result.detail)
        return result, []

    runs: list[RunRecord] = []
    results: list[OracleResult] = []
    skipped_budget = 0
    skipped_build = 0
    # Deterministic order, and every hypothesis that fired is re-checked — not
    # "the first three to finish". A flip claimed over a subset would be a
    # coverage lie if a later hypothesis still fires on the fixed version.
    for h in to_check:
        fixed_build = ok_builds.get(build_group_key(h))
        if fixed_build is None:
            skipped_build += 1
            events.skip(
                "differential",
                f"{h.id}: fixed-version build failed for its environment; re-check skipped",
            )
            continue
        if not budget.take():
            skipped_budget += 1
            events.skip(
                "differential",
                f"{h.id}: run budget exhausted; fixed-version re-check skipped",
            )
            continue
        proto = h.config
        config = RunConfig(
            node_version=proto.node_version,
            package_spec=f"{submission.package}@{fixed}",
            install_command=proto.install_command,
            poc_file_name=proto.poc_file_name,
            poc_command=proto.poc_command,
            env=dict(proto.env),
            setup_commands=list(proto.setup_commands),
            offline=True,
        )
        run_t0 = events.start(
            "differential", f"fixed-version run {h.id}",
            data={"sandbox_operation": "run"},
        )
        run = await executor.run_poc(
            fixed_build,
            config,
            poc_code=h.poc_code,
            hypothesis_id=h.id,
            timeout_s=settings.poc_timeout_s,
            offline=True,
            phase="fixed",
            probe_env=probe_env_for(h.oracle),
            probe_snippet=(
                h.oracle.probe_snippet if h.oracle.type is OracleType.CUSTOM_PROBE else None
            ),
        )
        budget.charge(run.cost)
        run.phase = "fixed"
        run.sandbox_image_id = fixed_build.image_id  # type: ignore[attr-defined]
        runs.append(run)
        if run.error:
            events.error(
                "differential",
                run_t0,
                f"fixed-version run {h.id}: {run.error}",
                cost=run.cost,
                cost_units=run.cost_units,
                sandbox_run_ids=[run.sandbox_run_id] if run.sandbox_run_id else [],
                data={"sandbox_operation": "run"},
            )
        else:
            events.ok(
                "differential",
                run_t0,
                f"fixed-version run {h.id}: exit={run.exit_code} in {run.elapsed_ms:.0f}ms",
                cost=run.cost,
                cost_units=run.cost_units,
                sandbox_run_ids=[run.sandbox_run_id] if run.sandbox_run_id else [],
                data={"sandbox_operation": "run"},
            )
        results.append(
            check_oracle(
                h.oracle, run, hypothesis_id=h.id, phase="fixed", run_index=len(runs) - 1
            )
        )

    if (skipped_budget or skipped_build) and not results:
        bits = []
        if skipped_budget:
            bits.append(f"{skipped_budget} skipped on the run budget")
        if skipped_build:
            bits.append(f"{skipped_build} whose fixed-version build failed")
        result = DifferentialResult(
            fixed_version=fixed,
            fix_commit=findings.fix_commit,
            ran=False,
            detail=(
                f"no fixed-version re-check ran ({'; '.join(bits)}) for "
                f"{len(to_check)} hypothesis(es) queued on {submission.package}@{fixed}"
            ),
        )
        events.skip("differential", result.detail)
        return result, []

    conclusive = [r for r in results if r.conclusive]
    fixed_fired = {r.hypothesis_id for r in conclusive if r.fired}
    errored = [r for r in results if not r.conclusive]

    # Flip definition (honest): every hypothesis that fired on the affected
    # version was re-checked to a judgment on the fixed one, and none of those
    # judgments fired. Anything less — a re-run that errored, one skipped on
    # the run budget, or one whose fixed-version build failed — leaves the flip
    # UNKNOWN, not False and certainly not True. An unknown flip must never
    # upgrade the tier.
    if skipped_budget or skipped_build or errored:
        reasons = []
        if skipped_budget:
            reasons.append(f"{skipped_budget} skipped on the run budget")
        if skipped_build:
            reasons.append(f"{skipped_build} whose fixed-version build failed")
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
