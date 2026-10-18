"""Data contracts: ReportSubmission validation, Dossier round-trip, Claim defaults."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mimi.schemas import (
    Advisory,
    Claim,
    CostSummary,
    Coverage,
    DifferentialResult,
    Dossier,
    EvidenceKind,
    GroundingEvidence,
    Hypothesis,
    Oracle,
    OracleResult,
    OracleType,
    PublicIdentifiers,
    ReportSubmission,
    ResearchFindings,
    RunConfig,
    RunRecord,
    StageEvent,
    Tier,
    VulnClass,
)


# ---------------------------------------------------------------------------
# ReportSubmission package_spec parsing / validation
# ---------------------------------------------------------------------------

def test_package_spec_parses_package_and_version():
    s = ReportSubmission(report_text="r", package_spec="lodash@4.17.20")
    assert s.package == "lodash"
    assert s.version == "4.17.20"


def test_package_spec_scoped_package_accepted():
    # Scoped names are real npm packages ("@scope/pkg@1.2.3"). The validator
    # must split on the LAST "@" of the spec so the leading "@" of the scope
    # is part of the name, not a version separator.
    s = ReportSubmission(report_text="r", package_spec="@scope/pkg@1.2.3")
    assert s.package == "@scope/pkg"
    assert s.version == "1.2.3"


def test_package_spec_scoped_package_without_version_rejected():
    # A name with no pinned version cannot be reproduced at "the exact affected
    # version", so it is refused rather than silently accepted.
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="@scope/pkg")


def test_package_spec_empty_version_rejected():
    # "lodash@" parses to a name with an empty version — refuse it.
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="lodash@")


def test_package_spec_unscoped_name_with_separator_rejected():
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="scope/pkg@1.2.3")


def test_package_spec_is_stripped():
    s = ReportSubmission(report_text="r", package_spec="  lodash@4.17.20  ")
    assert s.package_spec == "lodash@4.17.20"
    assert s.package == "lodash"
    assert s.version == "4.17.20"


def test_package_spec_missing_at_sign_rejected():
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="lodash")


def test_package_spec_empty_name_rejected():
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="@4.17.20")


def test_package_spec_blank_name_rejected():
    with pytest.raises(ValidationError):
        ReportSubmission(report_text="r", package_spec="   @1.0.0")


def test_report_text_is_required():
    with pytest.raises(ValidationError):
        ReportSubmission(package_spec="lodash@4.17.20")


# ---------------------------------------------------------------------------
# Claim defaults
# ---------------------------------------------------------------------------

def test_claim_defaults():
    c = Claim(package="lodash", expected_effect="prototype polluted")
    assert c.ecosystem == "npm"
    assert c.affected_versions == []
    assert c.vuln_class is VulnClass.OTHER
    assert c.cited_files == []
    assert c.cited_symbols == []
    assert c.poc_code is None
    assert c.poc_command is None
    assert c.attack_vector is None
    assert c.preconditions == []
    assert c.notes is None
    assert c.parse_warnings == []


def test_claim_requires_expected_effect():
    with pytest.raises(ValidationError):
        Claim(package="lodash")


def test_claim_vuln_class_roundtrip_from_string():
    c = Claim(package="p", expected_effect="e", vuln_class="prototype_pollution")
    assert c.vuln_class is VulnClass.PROTOTYPE_POLLUTION
    assert json.loads(c.model_dump_json())["vuln_class"] == "prototype_pollution"


def test_claim_unwraps_singleton_vuln_class_list():
    c = Claim(package="p", expected_effect="e", vuln_class=["redos"])
    assert c.vuln_class is VulnClass.REDOS


def test_claim_rejects_multiple_vuln_classes():
    with pytest.raises(ValidationError):
        Claim(package="p", expected_effect="e", vuln_class=["redos", "xss"])


# ---------------------------------------------------------------------------
# Dossier JSON round-trip
# ---------------------------------------------------------------------------

def _full_dossier() -> Dossier:
    return Dossier(
        report_id="abc123",
        created_at="2026-10-06T00:00:00+00:00",
        source="cli",
        report_text="reporter prose stays local",
        package_spec="lodash@4.17.20",
        claim=Claim(
            package="lodash",
            affected_versions=["4.17.20"],
            vuln_class=VulnClass.PROTOTYPE_POLLUTION,
            expected_effect="Object.prototype polluted",
        ),
        public_ids=PublicIdentifiers(
            package="lodash", versions=["4.17.20"], advisory_ids=["CVE-2021-23337"]
        ),
        grounding=[
            GroundingEvidence(kind=EvidenceKind.VERSION_MATCHES, target="lodash@4.17.20", detail="ok")
        ],
        research=ResearchFindings(
            queries=["lodash 4.17.20 vulnerability"],
            known_advisories=[Advisory(title="t", url="u", snippet="s")],
            fixed_version="4.17.21",
        ),
        hypotheses=[
            Hypothesis(
                id="h1",
                rationale="r",
                test_plan="t",
                config=RunConfig(),
                poc_code="console.log(1)",
                oracle=Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED"),
            )
        ],
        runs=[
            RunRecord(hypothesis_id="h1", phase="poc", command="node poc.js", exit_code=0)
        ],
        oracle_results=[],
        differential=DifferentialResult(ran=False, detail="skipped"),
        coverage=Coverage(hypotheses_tested=1, statement="1 hypotheses, 1 configs, 0 triggered"),
        tier=Tier.NEEDS_HUMAN,
        tier_rationale="why",
        reply_draft="draft",
        events=[
            StageEvent(ts="2026-10-06T00:00:00+00:00", report_id="abc123", stage="extract", status="ok")
        ],
        cost=CostSummary(),
        limitations=["Research (Tavily) was not available for this run."],
    )


def test_dossier_json_round_trip():
    d = _full_dossier()
    blob = d.model_dump_json()
    again = Dossier.model_validate_json(blob)
    assert again.model_dump() == d.model_dump()
    assert again.tier is Tier.NEEDS_HUMAN
    assert again.claim is not None and again.claim.vuln_class is VulnClass.PROTOTYPE_POLLUTION


def test_dossier_round_trip_via_stdlib_json():
    d = _full_dossier()
    via_dict = json.loads(d.model_dump_json())
    again = Dossier.model_validate(via_dict)
    assert again.report_id == "abc123"
    assert again.hypotheses[0].oracle.type is OracleType.OUTPUT_REGEX
    assert again.runs[0].command == "node poc.js"
    assert again.research.fixed_version == "4.17.21"


def test_dossier_minimal_defaults():
    d = Dossier(report_id="x")
    assert d.tier is Tier.NEEDS_HUMAN
    assert d.runs == []
    assert d.oracle_results == []
    assert d.events == []
    assert d.limitations == []
    assert d.cost.measured is False
    assert d.cost.inference_cost_usd is None
    assert d.cost.sandbox_cost is None


def test_dossier_json_round_trip_preserves_event_data_payload():
    d = Dossier(
        report_id="x",
        events=[
            StageEvent(
                ts="2026-10-06T00:00:00+00:00",
                report_id="x",
                stage="fork_run",
                status="ok",
                data={"oracle_fired": True},
                sandbox_run_ids=["sb-1"],
            )
        ],
    )
    again = Dossier.model_validate_json(d.model_dump_json())
    assert again.events[0].data == {"oracle_fired": True}
    assert again.events[0].sandbox_run_ids == ["sb-1"]


# ---------------------------------------------------------------------------
# Other contract details the pipeline depends on
# ---------------------------------------------------------------------------

def test_tier_values_are_display_strings():
    assert Tier.CONFIRMED.value == "Confirmed"
    assert Tier.LIKELY.value == "Likely"
    assert Tier.NEEDS_HUMAN.value == "Needs human"
    assert Tier.CONTRADICTED.value == "Contradicted"


def test_run_record_cost_stays_none_when_unmeasured():
    r = RunRecord(hypothesis_id="h1", command="node poc.js")
    assert r.cost is None
    assert r.cost_units is None
    assert r.network_isolated is None
    assert r.truncated is False
    assert r.error is None


def test_oracle_result_phase_literal():
    o = Oracle(type=OracleType.EXIT_CODE, expected_exit=0)
    OracleResult(hypothesis_id="h1", phase="affected", oracle=o, fired=False)
    OracleResult(hypothesis_id="h1", phase="fixed", oracle=o, fired=False)
    with pytest.raises(ValidationError):
        OracleResult(hypothesis_id="h1", phase="wrong", oracle=o, fired=False)
