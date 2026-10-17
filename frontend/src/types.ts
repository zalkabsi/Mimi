/**
 * UI mirror of the backend contracts in backend/mimi/schemas.py.
 * Only the fields the UI reads are listed. Do not invent fields here that the
 * backend does not emit — a null field renders as "—" or "not measured".
 */

export type Tier = "Confirmed" | "Likely" | "Needs human" | "Contradicted";

export type VulnClass =
  | "rce"
  | "xss"
  | "path_traversal"
  | "prototype_pollution"
  | "redos"
  | "sql_injection"
  | "command_injection"
  | "auth_bypass"
  | "ssrf"
  | "denial_of_service"
  | "other";

export type EvidenceKind =
  | "file_found"
  | "file_absent"
  | "symbol_found"
  | "symbol_absent"
  | "version_matches"
  | "version_mismatch"
  | "dependency_present"
  | "note";

export type OracleType =
  | "exit_code"
  | "signal"
  | "marker_file"
  | "output_regex"
  | "timing_threshold"
  | "prototype_pollution_probe"
  | "path_traversal_file_read"
  | "network_call"
  | "custom_probe";

export type RunPhase = "build" | "poc" | "fixed" | "other";

export type EventStatus = "started" | "ok" | "error" | "skipped";

export type DossierSource = "cli" | "api" | "eval" | "demo";

export interface Claim {
  package: string;
  ecosystem: string;
  affected_versions: string[];
  vuln_class: VulnClass;
  cited_files: string[];
  cited_symbols: string[];
  poc_code: string | null;
  poc_command: string | null;
  expected_effect: string;
  attack_vector: string | null;
  preconditions: string[];
  notes: string | null;
  parse_warnings: string[];
}

export interface PublicIdentifiers {
  package: string;
  ecosystem: string;
  versions: string[];
  advisory_ids: string[];
  extra_terms: string[];
}

export interface GroundingEvidence {
  kind: EvidenceKind;
  target: string;
  detail: string;
  source_ref: string | null;
}

export interface Advisory {
  source: string;
  title: string;
  url: string;
  snippet: string;
  advisory_ids: string[];
}

export interface ResearchFindings {
  queries: string[];
  known_advisories: Advisory[];
  duplicates: string[];
  fixed_version: string | null;
  fix_commit: string | null;
  fix_url: string | null;
  notes: string;
  used: boolean;
}

export interface Oracle {
  type: OracleType;
  description: string;
  expected_exit: number | null;
  expect_nonzero_exit: boolean;
  signal_name: string | null;
  marker_path: string | null;
  pattern: string | null;
  threshold_ms: number | null;
  expect_traversal_to: string | null;
  probe_snippet: string | null;
}

export interface RunConfig {
  node_version: string;
  package_spec: string | null;
  install_command: string;
  poc_file_name: string;
  poc_command: string;
  env: Record<string, string>;
  setup_commands: string[];
  offline: boolean;
  notes: string;
}

export interface Hypothesis {
  id: string;
  rationale: string;
  test_plan: string;
  config: RunConfig;
  poc_code: string;
  oracle: Oracle;
  priority: number;
}

export interface RunRecord {
  hypothesis_id: string;
  phase: RunPhase;
  command: string;
  exit_code: number | null;
  signal: string | null;
  stdout: string;
  stderr: string;
  elapsed_ms: number;
  cost: number | null;
  cost_units: string | null;
  sandbox_image_id: string | null;
  sandbox_run_id: string | null;
  network_isolated: boolean | null;
  truncated: boolean;
  error: string | null;
}

export interface OracleResult {
  hypothesis_id: string;
  phase: "affected" | "fixed";
  oracle: Oracle;
  fired: boolean;
  conclusive: boolean;
  detail: string;
  run_index: number;
}

export interface DifferentialResult {
  fixed_version: string | null;
  fix_commit: string | null;
  ran: boolean;
  flipped: boolean | null;
  detail: string;
  oracle_results: OracleResult[];
}

export interface Coverage {
  hypotheses_tested: number;
  hypotheses_total: number;
  hypotheses_triggered: number;
  configs_tested: number;
  versions_tested: string[];
  statement: string;
}

export interface CostSummary {
  inference_tokens_in: number;
  inference_tokens_out: number;
  inference_cost_usd: number | null;
  sandbox_cost: number | null;
  sandbox_cost_units: string | null;
  elapsed_ms: number;
  measured: boolean;
}

export interface StageEvent {
  ts: string;
  report_id: string;
  stage: string;
  status: EventStatus;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  sandbox_run_ids: string[];
  cost: number | null;
  cost_units: string | null;
  detail: string;
  data: Record<string, unknown>;
}

export interface Dossier {
  report_id: string;
  created_at: string;
  source: DossierSource;
  report_text: string;
  package_spec: string;
  claim: Claim | null;
  public_ids: PublicIdentifiers | null;
  grounding: GroundingEvidence[];
  research: ResearchFindings;
  hypotheses: Hypothesis[];
  runs: RunRecord[];
  oracle_results: OracleResult[];
  differential: DifferentialResult;
  coverage: Coverage;
  tier: Tier;
  tier_rationale: string;
  reply_draft: string;
  events: StageEvent[];
  cost: CostSummary;
  limitations: string[];
}

/** Row shape of GET /api/reports (db.list_reports). */
export interface ReportListItem {
  id: string;
  created_at: string;
  source: string;
  package_spec: string;
  status: string;
  tier: Tier | null;
}

export interface ReportSubmission {
  report_text: string;
  package_spec: string;
}

export interface SubmitResponse {
  report_id: string;
  status: string;
}
