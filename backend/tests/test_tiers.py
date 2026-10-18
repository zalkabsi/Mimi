"""Tier assignment — the full tier table as tests.

Safety properties pinned here:
- Confirmed only when an oracle fired on the affected version AND the
  fixed-version differential flipped.
- Contradicted only with quantified coverage (>= 3 tested across >= 2
  configurations, 0 triggered), never as "invalid".
- Grounding evidence alone can NEVER produce Contradicted.
"""

from __future__ import annotations

from mimi.schemas import (
    DifferentialResult,
    EvidenceKind,
    GroundingEvidence,
    Oracle,
    OracleResult,
    OracleType,
    RunRecord,
    Tier,
)
from mimi.tiers import assign_tier, compute_coverage

MIN_COV = 3


def oracle_result(hid: str, fired: bool, phase: str = "affected") -> OracleResult:
    return OracleResult(
        hypothesis_id=hid,
        phase=phase,  # type: ignore[arg-type]
        oracle=Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED"),
        fired=fired,
        detail="test",
    )


def poc_run(hid: str, phase: str = "poc", config_key: str = "", error: str | None = None) -> RunRecord:
    return RunRecord(
        hypothesis_id=hid,
        phase=phase,  # type: ignore[arg-type]
        command="node poc.js",
        exit_code=0 if error is None else None,
        config_key=config_key,
        error=error,
    )


def inconclusive(hid: str, phase: str = "affected") -> OracleResult:
    return OracleResult(
        hypothesis_id=hid,
        phase=phase,  # type: ignore[arg-type]
        oracle=Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED"),
        fired=False,
        conclusive=False,
        detail="test: inconclusive",
    )


# ---------------------------------------------------------------------------
# Confirmed
# ---------------------------------------------------------------------------

def test_confirmed_when_fired_and_differential_flipped():
    d = assign_tier(
        oracle_results=[oracle_result("h1", True)],
        differential=DifferentialResult(
            fixed_version="4.17.21", ran=True, flipped=True, detail="0 still fire on fixed"
        ),
        runs=[poc_run("h1")],
        hypotheses_total=1,
    )
    assert d.tier is Tier.CONFIRMED
    assert d.coverage.hypotheses_triggered == 1


def test_confirmed_rationale_names_the_fixed_version():
    d = assign_tier(
        oracle_results=[oracle_result("h1", True)],
        differential=DifferentialResult(fixed_version="1.2.3", ran=True, flipped=True),
        runs=[poc_run("h1")],
        hypotheses_total=1,
    )
    assert "1.2.3" in d.rationale
    assert "invalid" not in d.rationale.lower()


# ---------------------------------------------------------------------------
# Likely
# ---------------------------------------------------------------------------

def test_likely_when_fired_and_no_differential():
    d = assign_tier(
        oracle_results=[oracle_result("h1", True)],
        differential=DifferentialResult(ran=False, detail="no fixed version known"),
        runs=[poc_run("h1")],
        hypotheses_total=1,
    )
    assert d.tier is Tier.LIKELY
    assert "no fixed version" in d.rationale


def test_likely_when_fired_but_flip_unconfirmed():
    # differential ran but flipped is None (inconclusive) -> Likely, not Confirmed.
    d = assign_tier(
        oracle_results=[oracle_result("h1", True)],
        differential=DifferentialResult(fixed_version="9.9.9", ran=True, flipped=None),
        runs=[poc_run("h1")],
        hypotheses_total=1,
    )
    assert d.tier is Tier.LIKELY


# ---------------------------------------------------------------------------
# Needs human
# ---------------------------------------------------------------------------

def test_needs_human_when_fired_on_affected_and_fixed():
    # The oracle fires on both versions: it is not measuring this bug.
    d = assign_tier(
        oracle_results=[oracle_result("h1", True)],
        differential=DifferentialResult(fixed_version="4.17.21", ran=True, flipped=False),
        runs=[poc_run("h1"), poc_run("h1", phase="fixed")],
        hypotheses_total=1,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert "both" in d.rationale.lower()


def test_needs_human_when_build_failed():
    d = assign_tier(
        oracle_results=[],
        differential=DifferentialResult(),
        runs=[],
        hypotheses_total=3,
        build_failed=True,
        stopped_reason="npm install failed",
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert "build" in d.rationale.lower()


def test_needs_human_when_nothing_ran():
    d = assign_tier(
        oracle_results=[],
        differential=DifferentialResult(),
        runs=[],
        hypotheses_total=5,
        stopped_reason="no executable hypotheses were generated",
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert "No hypothesis was executed" in d.rationale


def test_needs_human_when_every_run_errored():
    # Three errored runs must never become a quantified Contradicted — no PoC
    # code ever executed, so "3 tested, 0 triggered" would be invented.
    d = assign_tier(
        oracle_results=[inconclusive(f"h{i}") for i in range(1, 4)],
        differential=DifferentialResult(),
        runs=[poc_run(f"h{i}", error="contree token expired") for i in range(1, 4)],
        hypotheses_total=3,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert d.coverage.hypotheses_tested == 0
    assert "invalid" not in d.rationale.lower()


def test_needs_human_when_only_inconclusive_results():
    # An inconclusive oracle is neither "fired" nor "did not fire".
    d = assign_tier(
        oracle_results=[inconclusive(f"h{i}") for i in range(1, 5)],
        differential=DifferentialResult(),
        runs=[poc_run(f"h{i}") for i in range(1, 5)],
        hypotheses_total=5,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert "inconclusive" in d.rationale.lower() or "no hypothesis was executed" in d.rationale.lower()


def test_inconclusive_results_do_not_count_toward_contradiction():
    # Two conclusive negatives + three inconclusive must not read as "5 tested".
    d = assign_tier(
        oracle_results=[
            oracle_result("h1", False),
            oracle_result("h2", False),
            inconclusive("h3"),
            inconclusive("h4"),
            inconclusive("h5"),
        ],
        differential=DifferentialResult(),
        runs=[poc_run(f"h{i}") for i in range(1, 6)],
        hypotheses_total=5,
    )
    assert d.coverage.hypotheses_tested == 2
    assert d.tier is Tier.NEEDS_HUMAN  # below the minimum of 3


def test_nothing_fired_but_coverage_sufficient_contradicts():
    d = assign_tier(
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 4)],
        differential=DifferentialResult(),
        runs=[poc_run(f"h{i}", config_key=f"cfg{i}") for i in range(1, 4)],
        hypotheses_total=3,
    )
    assert d.tier is Tier.CONTRADICTED
    assert d.coverage.hypotheses_tested == 3
    assert "0 triggered" in d.rationale


def test_needs_human_when_coverage_under_three():
    for n in (1, 2):
        d = assign_tier(
            oracle_results=[oracle_result(f"h{i}", False) for i in range(n)],
            differential=DifferentialResult(),
            runs=[poc_run(f"h{i}") for i in range(n)],
            hypotheses_total=n,
        )
        assert d.tier is Tier.NEEDS_HUMAN
        assert f"Only {n} hypotheses ran" in d.rationale


def test_needs_human_takes_precedence_over_low_coverage_on_build_failure():
    d = assign_tier(
        oracle_results=[oracle_result("h1", False)],
        differential=DifferentialResult(),
        runs=[poc_run("h1")],
        hypotheses_total=1,
        build_failed=True,
    )
    assert d.tier is Tier.NEEDS_HUMAN


# ---------------------------------------------------------------------------
# Contradicted — quantified negative result, never "invalid"
# ---------------------------------------------------------------------------

def test_contradicted_when_three_tested_zero_fired():
    d = assign_tier(
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 4)],
        differential=DifferentialResult(),
        runs=[
            poc_run("h1", config_key="node18"),
            poc_run("h2", config_key="node20"),
            poc_run("h3", config_key="node20"),
        ],
        hypotheses_total=3,
    )
    assert d.tier is Tier.CONTRADICTED
    assert "invalid" not in d.rationale.lower()
    assert "negative result" in d.rationale.lower()
    assert "3 hypotheses" in d.rationale
    assert "2 configs" in d.coverage.statement


def test_contradicted_with_more_than_three():
    d = assign_tier(
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 8)],
        differential=DifferentialResult(),
        runs=[
            poc_run(f"h{i}", config_key="node18" if i < 4 else "node20")
            for i in range(1, 8)
        ],
        hypotheses_total=7,
    )
    assert d.tier is Tier.CONTRADICTED
    assert d.coverage.hypotheses_tested == 7
    assert d.coverage.hypotheses_triggered == 0


def test_contradicted_states_coverage_in_rationale():
    d = assign_tier(
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 5)],
        differential=DifferentialResult(),
        runs=[
            poc_run(f"h{i}", config_key="node18" if i < 3 else "node20")
            for i in range(1, 5)
        ],
        hypotheses_total=4,
    )
    assert d.coverage.statement in d.rationale


def test_single_config_negative_result_needs_human():
    d = assign_tier(
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 8)],
        differential=DifferentialResult(),
        runs=[poc_run(f"h{i}", config_key="node18") for i in range(1, 8)],
        hypotheses_total=7,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert "at least 2" in d.rationale
    assert d.coverage.configs_tested == 1


# ---------------------------------------------------------------------------
# Grounding alone can NEVER reject a report
# ---------------------------------------------------------------------------

def test_grounding_only_never_contradicts():
    # Heavy grounding (even negative: cited file absent at this version) with
    # zero executed hypotheses must land Needs human, never Contradicted.
    grounding = [
        GroundingEvidence(kind=EvidenceKind.FILE_ABSENT, target="lib/merge.js", detail="not in tarball"),
        GroundingEvidence(kind=EvidenceKind.SYMBOL_ABSENT, target="defaultsDeep", detail="symbol not found"),
        GroundingEvidence(kind=EvidenceKind.VERSION_MISMATCH, target="left-pad@9.9.9", detail="no such version"),
        GroundingEvidence(kind=EvidenceKind.NOTE, target="summary", detail="cited code does not exist here"),
    ]
    assert grounding  # the case really is grounding-heavy
    d = assign_tier(
        oracle_results=[],
        differential=DifferentialResult(),
        runs=[],
        hypotheses_total=0,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert d.tier is not Tier.CONTRADICTED
    assert d.coverage.hypotheses_tested == 0


def test_grounding_only_never_contradicts_even_with_high_total():
    d = assign_tier(
        oracle_results=[],
        differential=DifferentialResult(),
        runs=[],
        hypotheses_total=10,
    )
    assert d.tier is Tier.NEEDS_HUMAN
    assert d.coverage.statement == "0 hypotheses, 0 configs, 0 triggered"


# ---------------------------------------------------------------------------
# Coverage statement format
# ---------------------------------------------------------------------------

def test_coverage_statement_format():
    cov = compute_coverage(
        hypotheses_total=3,
        oracle_results=[oracle_result(f"h{i}", fired) for i, fired in enumerate([True, False, False], 1)],
        runs=[poc_run(f"h{i}", config_key=f"cfg{i}") for i in range(1, 4)],
    )
    assert cov.statement == "3 hypotheses, 3 configs, 1 triggered"
    assert cov.hypotheses_tested == 3
    assert cov.hypotheses_triggered == 1
    assert cov.configs_tested == 3
    assert cov.hypotheses_total == 3


def test_coverage_statement_matches_pattern():
    import re

    cov = compute_coverage(
        hypotheses_total=7,
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 5)],
        runs=[poc_run(f"h{i}", config_key=f"cfg{i}") for i in range(1, 5)],
    )
    assert re.fullmatch(r"\d+ hypotheses, \d+ configs, \d+ triggered", cov.statement)
    assert cov.statement == "4 hypotheses, 4 configs, 0 triggered"


def test_coverage_counts_configs_from_runs():
    # two hypotheses, one run only -> 1 config executed
    cov = compute_coverage(
        hypotheses_total=2,
        oracle_results=[oracle_result("h1", False), oracle_result("h2", False)],
        runs=[poc_run("h1")],
    )
    assert cov.configs_tested == 1
    assert cov.hypotheses_tested == 2
    assert cov.statement == "2 hypotheses, 1 configs, 0 triggered"


def test_coverage_configs_mean_environments_not_hypotheses():
    # Three hypotheses in the SAME environment are one configuration.
    cov = compute_coverage(
        hypotheses_total=3,
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 4)],
        runs=[poc_run(f"h{i}", config_key="same-env") for i in range(1, 4)],
    )
    assert cov.hypotheses_tested == 3
    assert cov.configs_tested == 1


def test_coverage_configs_count_distinct_environments():
    cov = compute_coverage(
        hypotheses_total=3,
        oracle_results=[oracle_result(f"h{i}", False) for i in range(1, 4)],
        runs=[
            poc_run("h1", config_key="node18"),
            poc_run("h2", config_key="node20"),
            poc_run("h3", config_key="node18"),
        ],
    )
    assert cov.configs_tested == 2


def test_coverage_errored_runs_are_not_tested():
    # Three errored runs must not become "3 hypotheses tested, 0 triggered".
    cov = compute_coverage(
        hypotheses_total=3,
        oracle_results=[inconclusive(f"h{i}") for i in range(1, 4)],
        runs=[poc_run(f"h{i}", error="sandbox timeout") for i in range(1, 4)],
    )
    assert cov.hypotheses_tested == 0
    assert cov.configs_tested == 0
    assert cov.hypotheses_triggered == 0


def test_coverage_no_executed_runs_means_zero_configs():
    cov = compute_coverage(
        hypotheses_total=2,
        oracle_results=[inconclusive("h1"), inconclusive("h2")],
        runs=[],
    )
    assert cov.configs_tested == 0
    assert cov.statement == "0 hypotheses, 0 configs, 0 triggered"


def test_coverage_versions_recorded_when_passed():
    cov = compute_coverage(
        hypotheses_total=1,
        oracle_results=[oracle_result("h1", True)],
        runs=[poc_run("h1")],
        versions=["4.17.20", "4.17.21"],
    )
    assert cov.versions_tested == ["4.17.20", "4.17.21"]
