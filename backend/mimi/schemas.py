"""Core data contracts: claim, hypothesis, oracle, run records, dossier, tiers.

Everything the pipeline passes between stages is one of these models. The
dossier is the product's evidence object and is serialised to JSON for the
CLI, the API and the eval harness.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def split_package_spec(spec: str) -> tuple[str, str]:
    """Split an npm spec into (name, version).

    Scoped packages put an ``@`` in the name (``@scope/name@1.2.3``), so the
    name is everything before the *last* ``@`` that is followed by a version,
    and the leading ``@`` of a scope is part of the name. Returns ``""`` for
    whichever side is absent.
    """
    s = (spec or "").strip()
    if not s:
        return "", ""
    if s.startswith("@"):
        # @scope/name or @scope/name@version — split on the last "@".
        if "@" not in s[1:]:
            return s, ""
        name, _, version = s.rpartition("@")
        return name.strip(), version.strip()
    if "@" not in s:
        return s, ""
    name, _, version = s.partition("@")
    return name.strip(), version.strip()


_NPM_NAME_RE = re.compile(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*")
_SEMVER_RE = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def validate_package_spec(spec: str) -> tuple[str, str]:
    """Accept one canonical npm name pinned to an exact semantic version."""
    value = (spec or "").strip()
    name, version = split_package_spec(value)
    if (
        not name
        or len(name) > 214
        or not _NPM_NAME_RE.fullmatch(name)
        or not _SEMVER_RE.fullmatch(version)
        or value != f"{name}@{version}"
    ):
        raise ValueError("package_spec must be a canonical npm package name pinned to an exact version")
    return name, version


# ---------------------------------------------------------------------------
# Claim (stage 1 output)
# ---------------------------------------------------------------------------

class VulnClass(str, Enum):
    RCE = "rce"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    PROTOTYPE_POLLUTION = "prototype_pollution"
    REDOS = "redos"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    AUTH_BYPASS = "auth_bypass"
    SSRF = "ssrf"
    DENIAL_OF_SERVICE = "denial_of_service"
    OTHER = "other"


class Claim(BaseModel):
    """What the report asserts, in structured form."""

    package: str = Field(description="npm package name")
    ecosystem: Literal["npm"] = "npm"
    affected_versions: list[str] = Field(default_factory=list)
    vuln_class: VulnClass = VulnClass.OTHER
    cited_files: list[str] = Field(default_factory=list)
    cited_symbols: list[str] = Field(default_factory=list)
    poc_code: Optional[str] = Field(default=None, description="reporter-supplied PoC, if any")
    poc_command: Optional[str] = Field(default=None, description="how the report says to invoke the PoC")
    expected_effect: str = Field(description="observable effect if the claim is true")
    attack_vector: Optional[str] = None
    preconditions: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    parse_warnings: list[str] = Field(default_factory=list)


class PublicIdentifiers(BaseModel):
    """The only report facts allowed to leave the system toward Tavily.

    Built deterministically from the claim (package, versions, CVE/GHSA ids).
    Free-text report content never appears here; the redaction test enforces it.
    """

    package: str
    ecosystem: str = "npm"
    versions: list[str] = Field(default_factory=list)
    advisory_ids: list[str] = Field(default_factory=list)  # CVE-…, GHSA-…
    extra_terms: list[str] = Field(default_factory=list)  # e.g. vuln class words


# ---------------------------------------------------------------------------
# Grounding (stage 2)
# ---------------------------------------------------------------------------

class EvidenceKind(str, Enum):
    FILE_FOUND = "file_found"
    FILE_ABSENT = "file_absent"
    SYMBOL_FOUND = "symbol_found"
    SYMBOL_ABSENT = "symbol_absent"
    VERSION_MATCHES = "version_matches"
    VERSION_MISMATCH = "version_mismatch"
    DEPENDENCY_PRESENT = "dependency_present"
    NOTE = "note"


class GroundingEvidence(BaseModel):
    kind: EvidenceKind
    target: str
    detail: str = ""
    source_ref: Optional[str] = None  # path:line when applicable


# ---------------------------------------------------------------------------
# Research (stage 3)
# ---------------------------------------------------------------------------

class Advisory(BaseModel):
    source: str = "tavily"
    title: str = ""
    url: str = ""
    snippet: str = ""
    advisory_ids: list[str] = Field(default_factory=list)


class ResearchFindings(BaseModel):
    queries: list[str] = Field(default_factory=list)  # exactly what was sent to Tavily
    known_advisories: list[Advisory] = Field(default_factory=list)
    duplicates: list[str] = Field(default_factory=list)
    fixed_version: Optional[str] = None
    fix_commit: Optional[str] = None
    fix_url: Optional[str] = None
    notes: str = ""
    used: bool = True  # False when research was skipped (no key) — stated in the dossier


# ---------------------------------------------------------------------------
# Hypotheses and oracles (stage 4)
# ---------------------------------------------------------------------------

class OracleType(str, Enum):
    EXIT_CODE = "exit_code"
    SIGNAL = "signal"
    MARKER_FILE = "marker_file"
    OUTPUT_REGEX = "output_regex"
    TIMING_THRESHOLD = "timing_threshold"
    PROTOTYPE_POLLUTION_PROBE = "prototype_pollution_probe"
    PATH_TRAVERSAL_FILE_READ = "path_traversal_file_read"
    NETWORK_CALL = "network_call"
    CUSTOM_PROBE = "custom_probe"


class Oracle(BaseModel):
    """Predeclared deterministic check. The LLM does not grade a reproduction
    that one of these can grade."""

    type: OracleType
    description: str = ""
    expected_exit: Optional[int] = None
    expect_nonzero_exit: bool = False
    signal_name: Optional[str] = None
    marker_path: Optional[str] = None
    pattern: Optional[str] = None  # regex over combined stdout+stderr
    threshold_ms: Optional[float] = None
    expect_traversal_to: Optional[str] = None  # path that must NOT be readable
    probe_snippet: Optional[str] = Field(
        default=None,
        max_length=16_384,
        description="small untrusted Node snippet for isolated custom-probe oracles",
    )

    @field_validator("marker_path")
    @classmethod
    def marker_is_workspace_filename(cls, value: Optional[str]) -> Optional[str]:
        """Marker checks are confined to a clean file directly under /work."""
        if value is None:
            return None
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}", value)
            or value.startswith(".mimi_")
        ):
            raise ValueError("marker_path must be a simple non-reserved filename in /work")
        return value


class RunConfig(BaseModel):
    """How to execute one hypothesis. Commands come from this fixed shape —
    never free-form strings parsed out of the report text (prompt-injection
    rule in docs/02-architecture.md)."""

    node_version: str = "20"
    package_spec: Optional[str] = None  # e.g. "lodash@4.17.20"; defaults to claim
    install_command: str = "npm install --no-audit --no-fund"
    poc_file_name: str = "poc.js"
    poc_command: str = "node poc.js"
    env: dict[str, str] = Field(default_factory=dict)
    setup_commands: list[str] = Field(default_factory=list)  # from a fixed allowlist
    offline: bool = True  # online PoC execution is rejected by the executor
    notes: str = ""


class Hypothesis(BaseModel):
    id: str = Field(description="stable id, e.g. h1")
    rationale: str
    test_plan: str
    config: RunConfig = Field(default_factory=RunConfig)
    poc_code: str = Field(description="the code to execute inside the sandbox")
    oracle: Oracle
    priority: int = 1  # 1 = try first


# ---------------------------------------------------------------------------
# Execution records (stages 5-7)
# ---------------------------------------------------------------------------

class RunRecord(BaseModel):
    hypothesis_id: str
    phase: Literal["build", "poc", "fixed", "other"] = "poc"
    command: str
    exit_code: Optional[int] = None
    signal: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    # Fixed-source probe output from a separate post-PoC command. Probe oracles
    # read this field instead of stdout, but shared-VM state is not tamper-proof.
    probe_output: str = ""
    elapsed_ms: float = 0.0
    cost: Optional[float] = None
    cost_units: Optional[str] = None  # ProcessResources.cost units are unknown; keep raw
    sandbox_image_id: Optional[str] = None
    sandbox_run_id: Optional[str] = None
    network_isolated: Optional[bool] = None
    truncated: bool = False
    error: Optional[str] = None
    # Fingerprint of the RunConfig this ran under — what "K configs" counts.
    config_key: str = ""


class OracleResult(BaseModel):
    hypothesis_id: str
    phase: Literal["affected", "fixed"] = "affected"
    oracle: Oracle
    fired: bool
    detail: str = ""
    run_index: int = 0  # index into Dossier.runs
    # True only when this is a real determination: the PoC actually ran, the
    # oracle was correctly configured, and the evidence was complete enough to
    # judge. False for errored runs, misconfigured oracles, missing probe
    # verdicts and truncated output — those are inconclusive, NOT "did not fire".
    conclusive: bool = True


class DifferentialResult(BaseModel):
    fixed_version: Optional[str] = None
    fix_commit: Optional[str] = None
    ran: bool = False
    flipped: Optional[bool] = None  # True: fired on affected, not on fixed
    detail: str = ""
    oracle_results: list[OracleResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

class Tier(str, Enum):
    CONFIRMED = "Confirmed"
    LIKELY = "Likely"
    NEEDS_HUMAN = "Needs human"
    CONTRADICTED = "Contradicted"


class Coverage(BaseModel):
    hypotheses_tested: int = 0
    hypotheses_total: int = 0
    hypotheses_triggered: int = 0
    configs_tested: int = 0
    versions_tested: list[str] = Field(default_factory=list)
    statement: str = ""  # e.g. "7 hypotheses, 3 configs, 0 triggered"


class CostSummary(BaseModel):
    inference_tokens_in: int = 0
    inference_tokens_out: int = 0
    inference_cost_usd: Optional[float] = None  # current values use an unverified price table
    sandbox_cost: Optional[float] = None
    sandbox_cost_units: Optional[str] = None
    elapsed_ms: float = 0.0
    measured: bool = False  # True when all attempted cost components have complete telemetry


# ---------------------------------------------------------------------------
# Timeline events (observability)
# ---------------------------------------------------------------------------

class StageEvent(BaseModel):
    """One structured event per stage step; the UI timeline and the eval
    report both read these."""

    ts: str  # ISO-8601 UTC
    report_id: str
    stage: str
    status: Literal["started", "ok", "error", "skipped"] = "ok"
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[float] = None
    sandbox_run_ids: list[str] = Field(default_factory=list)
    cost: Optional[float] = None
    cost_units: Optional[str] = None
    detail: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dossier (the product's output)
# ---------------------------------------------------------------------------

class Dossier(BaseModel):
    report_id: str
    created_at: str = ""
    source: Literal["cli", "api", "eval", "demo"] = "cli"
    report_text: str = ""  # kept locally; never sent to Tavily
    package_spec: str = ""  # "package@version" as submitted

    claim: Optional[Claim] = None
    public_ids: Optional[PublicIdentifiers] = None
    grounding: list[GroundingEvidence] = Field(default_factory=list)
    research: ResearchFindings = Field(default_factory=ResearchFindings)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    runs: list[RunRecord] = Field(default_factory=list)
    oracle_results: list[OracleResult] = Field(default_factory=list)
    differential: DifferentialResult = Field(default_factory=DifferentialResult)

    coverage: Coverage = Field(default_factory=Coverage)
    tier: Tier = Tier.NEEDS_HUMAN
    tier_rationale: str = ""
    reply_draft: str = ""

    events: list[StageEvent] = Field(default_factory=list)
    cost: CostSummary = Field(default_factory=CostSummary)
    limitations: list[str] = Field(default_factory=list)  # stated honestly in the UI


class ReportSubmission(BaseModel):
    """Input to the pipeline."""

    report_text: str
    package_spec: str = Field(description="package@version, e.g. lodash@4.17.20")

    @field_validator("package_spec")
    @classmethod
    def _check_spec(cls, v: str) -> str:
        spec = (v or "").strip()
        validate_package_spec(spec)
        return spec

    @property
    def package(self) -> str:
        return split_package_spec(self.package_spec)[0]

    @property
    def version(self) -> str:
        return split_package_spec(self.package_spec)[1]
