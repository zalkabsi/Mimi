"""Stage 8 — Verdict tier + dossier, and stage 9 — reply draft.

The tier is assigned by pure code (``tiers.assign_tier``). Super (escalating
to Ultra only when oracles disagree or are inconclusive) writes the rationale
and the reply; it never changes the tier.
"""

from __future__ import annotations

from typing import Optional

from ..config import ESCALATION_MODEL, Stage
from ..events import EventLog
from ..llm import LLMClient
from ..schemas import (
    Claim,
    Coverage,
    DifferentialResult,
    Dossier,
    GroundingEvidence,
    Hypothesis,
    OracleResult,
    ReportSubmission,
    ResearchFindings,
    Tier,
)
from ..tiers import TierDecision, assign_tier


def adjudicate(
    submission: ReportSubmission,
    *,
    claim: Claim,
    grounding: list[GroundingEvidence],
    findings: ResearchFindings,
    hypotheses: list[Hypothesis],
    oracle_results: list[OracleResult],
    differential: DifferentialResult,
    runs,
    build_failed: bool = False,
    stopped_reason: str = "",
    llm: Optional[LLMClient] = None,
    events: Optional[EventLog] = None,
) -> TierDecision:
    """Assign the tier deterministically; optionally let the model narrate."""
    t0 = events.start("verdict") if events else None

    decision = assign_tier(
        oracle_results=oracle_results,
        differential=differential,
        runs=runs,
        hypotheses_total=len(hypotheses),
        build_failed=build_failed,
        stopped_reason=stopped_reason,
        advisory_titles=findings.registry_advisories if findings is not None else None,
    )

    # Versions actually executed — measured, never inferred. The submitted
    # version counts only if a PoC run really happened against it; the fixed
    # version counts only if the differential actually ran there.
    versions: list[str] = []
    ran_affected = any(r.phase in ("poc", "affected") and not r.error for r in runs)
    if ran_affected and submission.version:
        versions.append(submission.version)
    if differential.ran and differential.fixed_version:
        versions.append(differential.fixed_version)
    decision.coverage.versions_tested = versions
    decision.coverage.statement = (
        f"{decision.coverage.hypotheses_tested} hypotheses, "
        f"{decision.coverage.configs_tested} configs, "
        f"{decision.coverage.hypotheses_triggered} triggered"
        + (f", versions: {', '.join(versions)}" if versions else "")
    )

    if llm is not None:
        ambiguous = _is_ambiguous(oracle_results, differential)
        force = ESCALATION_MODEL if ambiguous else None
        try:
            resp = llm.chat(
                stage=Stage.VERDICT,
                force_model=force,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Write a 2-3 sentence evidence rationale for a maintainer. "
                            "Do not change the assigned tier and do not say the report is invalid. "
                            "State what was proven or not proven and the coverage.\n\n"
                            f"Tier (fixed): {decision.tier.value}\n"
                            f"Coverage: {decision.coverage.statement}\n"
                            f"Oracle results: {[(r.hypothesis_id, r.fired, r.detail) for r in oracle_results][:8]}\n"
                            f"Differential: {differential.detail or differential.model_dump_json()[:400]}\n"
                            f"Auto rationale: {decision.rationale}"
                        ),
                    }
                ],
                max_tokens=1200,
                enable_thinking=ambiguous,
            )
            text = (resp.content or "").strip()
            finish = ((resp.raw or {}).get("choices") or [{}])[0].get("finish_reason")
            # A cut-off rationale ("...on versions 1.") reads as a verdict
            # statement the harness never made. Keep the deterministic one.
            if text and finish == "length":
                if events:
                    events.emit("verdict", "ok", "rationale draft cut off; kept the harness rationale")
            elif text:
                decision.rationale = text
        except Exception as e:
            if events:
                events.emit("verdict", "ok", f"rationale draft skipped: {e}")

    if events and t0 is not None:
        events.ok("verdict", t0, f"tier={decision.tier.value}")
    return decision


def _is_ambiguous(oracle_results: list[OracleResult], differential: DifferentialResult) -> bool:
    fired = [r for r in oracle_results if r.fired]
    if fired and differential.ran and differential.flipped is None:
        return True
    if len(fired) > 1 and len({r.fired for r in oracle_results}) > 1:
        return True
    return False


def draft_reply(
    submission: ReportSubmission,
    claim: Claim,
    decision: TierDecision,
    findings: ResearchFindings,
    llm: LLMClient,
    events: EventLog,
    missing_info: Optional[list[str]] = None,
) -> str:
    """Stage 9 — maintainer-ready reply. Never sends anything; it is a draft."""
    t0 = events.start("reply", f"draft for tier {decision.tier.value}")
    needs = decision.tier == Tier.NEEDS_HUMAN
    missing = missing_info or []
    if needs and not missing:
        missing = [
            "exact package name and version tested",
            "a minimal PoC we can run (script or exact commands)",
            "the expected observable effect",
            "environment details (Node version, OS) if relevant",
        ]
    try:
        resp = llm.chat(
            stage=Stage.REPLY,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Draft a short, respectful reply to a vulnerability reporter on behalf of "
                        "a maintainer. No threats, no dismissals. Never say the report is invalid.\n\n"
                        f"Tier: {decision.tier.value}\n"
                        f"What we found: {decision.rationale}\n"
                        f"Coverage: {decision.coverage.statement}\n"
                        f"Package: {submission.package_spec}\n"
                        + (f"Ask for specifically: {', '.join(missing)}\n" if missing else "")
                        + ("Acknowledge the reproduction and share the evidence summary.\n" if decision.tier == Tier.CONFIRMED else "")
                        + ("Ask for the missing information listed above so we can continue.\n" if needs else "")
                    ),
                }
            ],
            max_tokens=500,
            enable_thinking=False,
        )
        text = (resp.content or "").strip()
    except Exception as e:
        text = f"(reply draft unavailable: {e})"
    events.ok("reply", t0, f"{len(text)} chars")
    return text
