"""Tier assignment — a pure function over evidence.

The tier is decided deterministically from oracle results and the
differential. The LLM never assigns a tier. Grounding evidence alone can
never reject a report (SlopCheck contradicts 29.4% of confirmed vulns and
~90% of its contradictions are wrong; see docs/01-research-and-decision.md E5).

Tiers (docs/02-architecture.md):
- Confirmed:     oracle fired on affected AND did not fire on fixed.
- Likely:        oracle fired, but no fixed-version differential.
- Needs human:   build failed, oracles inconclusive, or coverage too low.
- Contradicted:  N hypotheses tested across K configurations, 0 triggered —
                 with the coverage stated. Never "invalid".
"""

from __future__ import annotations

from typing import Optional

from .schemas import (
    Coverage,
    DifferentialResult,
    OracleResult,
    RunRecord,
    Tier,
)


class TierDecision:
    def __init__(self, tier: Tier, rationale: str, coverage: Coverage):
        self.tier = tier
        self.rationale = rationale
        self.coverage = coverage


def compute_coverage(
    hypotheses_total: int,
    oracle_results: list[OracleResult],
    runs: list[RunRecord],
    versions: Optional[list[str]] = None,
) -> Coverage:
    tested_ids = {r.hypothesis_id for r in oracle_results} | {
        r.hypothesis_id for r in runs if r.phase == "poc"
    }
    fired_ids = {r.hypothesis_id for r in oracle_results if r.fired}
    # One config per hypothesis id (the run config); count distinct ids executed.
    configs_tested = len({r.hypothesis_id for r in runs if r.phase in ("poc", "fixed")})
    cov = Coverage(
        hypotheses_tested=len(tested_ids),
        hypotheses_total=hypotheses_total,
        hypotheses_triggered=len(fired_ids),
        configs_tested=configs_tested if configs_tested else len(tested_ids),
        versions_tested=list(versions or []),
    )
    cov.statement = (
        f"{cov.hypotheses_tested} hypotheses, {cov.configs_tested} configs, "
        f"{cov.hypotheses_triggered} triggered"
    )
    return cov


def assign_tier(
    *,
    oracle_results: list[OracleResult],
    differential: DifferentialResult,
    runs: list[RunRecord],
    hypotheses_total: int,
    coverage: Optional[Coverage] = None,
    min_coverage_to_contradict: int = 3,
    build_failed: bool = False,
    stopped_reason: str = "",
) -> TierDecision:
    """The whole tier table as code. Deterministic, unit-tested."""
    cov = coverage or compute_coverage(hypotheses_total, oracle_results, runs)

    fired = [r for r in oracle_results if r.phase == "affected" and r.fired]
    all_affected = [r for r in oracle_results if r.phase == "affected"]

    # 1. Confirmed: fired on affected and the differential flipped.
    if fired and differential.ran and differential.flipped is True:
        return TierDecision(
            Tier.CONFIRMED,
            (
                f"Oracle fired on the affected version and did not fire on "
                f"{differential.fixed_version or 'the fixed version'} "
                f"({differential.detail or 'differential ran'})."
            ),
            cov,
        )

    # 2. Likely: fired, but no usable differential.
    if fired and not (differential.ran and differential.flipped is False):
        why = (
            "no fixed version known"
            if not differential.ran
            else f"differential did not confirm the flip ({differential.detail or 'no detail'})"
        )
        return TierDecision(Tier.LIKELY, f"Oracle fired on the affected version; {why}.", cov)

    # Fired on affected AND on fixed: the oracle does not measure the bug.
    if fired and differential.ran and differential.flipped is False:
        return TierDecision(
            Tier.NEEDS_HUMAN,
            (
                "Oracle fired on both the affected and the fixed version, so it "
                "is not measuring this bug. Coverage: " + cov.statement
            ),
            cov,
        )

    # 3. Needs human: nothing conclusive to run, or coverage too low to say.
    if build_failed:
        return TierDecision(
            Tier.NEEDS_HUMAN,
            f"Environment build failed, so no hypothesis could be executed. {stopped_reason}".strip(),
            cov,
        )

    if not all_affected:
        return TierDecision(
            Tier.NEEDS_HUMAN,
            f"No hypothesis was executed to an oracle. {stopped_reason}".strip(),
            cov,
        )

    if cov.hypotheses_tested < min_coverage_to_contradict:
        return TierDecision(
            Tier.NEEDS_HUMAN,
            (
                f"Only {cov.hypotheses_tested} hypotheses ran (minimum "
                f"{min_coverage_to_contradict} to call a negative result). "
                f"Coverage: {cov.statement}."
            ),
            cov,
        )

    # 4. Contradicted: quantified negative result. Never "invalid".
    return TierDecision(
        Tier.CONTRADICTED,
        (
            f"Executed evidence against the claim: {cov.statement}, 0 triggered. "
            "This is a negative result with stated coverage, not proof the report is wrong."
        ),
        cov,
    )
