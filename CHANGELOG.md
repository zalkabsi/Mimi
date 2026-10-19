# Changelog

All work in this repository was created during the hackathon Submission Period (Aug 26 - Oct 30, 2026). The repository was empty before the first commit on 2026-09-29; no pre-existing code was imported.

## Unreleased

### 2026-10-19 (free live hosting and research regression)

- Deployed the combined frontend/API at https://mimi-judge.onrender.com on
  Render Free with one Frankfurt instance, provider secrets, and a generated
  judge credential. Removed the shutdown-delay setting unsupported by Free.
- Fixed research being skipped when the report contained the template word
  "vulnerability" or code whose normalized prefix matched part of a query word.
  Fixed vocabulary remains allowed; query prose and secret guards remain tested.
- All 201 backend tests pass, including a bundled-report client regression.
  The hosted retest completed five Tavily queries with 17 advisory records,
  eight Sandbox runs, and a saved dossier/reply with terminal SSE. Its verdict
  was Needs human, with zero triggered hypotheses in one configuration; no new
  reproduction-accuracy or hostile-code containment claim is made.
- Updated deployment evidence and private judge-testing instructions, preserving
  the public Pages replay and approved video.

### 2026-10-17 (Sandboxes SDK smoke and runtime fixes)
- Replaced the incompatible ContreeAsyncClient usage with the async Contree client and IAMAuth
  configuration exposed by contree-sdk 0.3.6. Made staged image runs persistent for PoC
  setup and execution; kept the independent probe disposable.
- Normalized SDK UUID values before storing run records, read cost and elapsed time from the
  SDK result shape, and changed Node probe input from /dev/stdin to stdin's supported dash
  form.
- Completed a safe no-op run using node:20 and is-number@7.0.0. The image built and the
  command ran; Mimi reported its child network namespace active, and a TCP connection
  attempt to 1.1.1.1:80 returned ENETUNREACH. The SDK reported 0.00826591 raw Contree cost
  units for the build and 0.00069384 for the run; currency conversion is unknown.
- This was a basic integration and app-level egress smoke check only. No vulnerability PoC,
  hostile payload, end-to-end triage, provider-level isolation assessment, or evaluation
  suite was run.

### 2026-10-17 (Sandboxes endpoint correction)
- Updated the Sandboxes base URL to the current Token Factory endpoint documented by Nebius. The previous October 15 check targeted the former host and returned 403; the corrected read-only `whoami` check returned HTTP 200 with all six permissions enabled. No sandbox execution or PoC run has been claimed.

### 2026-10-17 (submission review)
- Updated project status to reflect the owner-confirmed public GitHub repository and read-only Pages replay; live backend execution remains unverified. Sandboxes endpoint permissions were checked later on 2026-10-17 after correcting the API base URL.
- Removed review findings that could let reporter-controlled PoC code replace the post-PoC probe source, and moved the trusted probe and custom snippets to stdin. The isolation marker now comes from the same namespace invocation that runs the PoC.
- Made oracle result rendering require explicit conclusive evidence, and corrected scoped npm package validation and final SSE dossier refresh behavior in the frontend.
- Changed E4 safety evaluation so missing execution/oracle evidence is `not_run`, not a pass, and excluded undetermined cases from the completed-case pass-rate denominator.
- Built affected-version images per image-affecting Node/install/setup configuration and routed each hypothesis to its matching image; setup order now remains part of the image key.
- Corrected privacy wording: report text is sent to Token Factory for inference, while only public identifiers are sent to Tavily.
- Documented Sandbox cost as raw Contree units and the per-report threshold as best-effort rather than USD or a hard spending cap; measured build and run costs now share the budget accounting.
- Updated GitHub Actions to Node 24-compatible action releases and pinned Ubuntu 24.04 to remove the current runtime deprecation and upcoming `ubuntu-latest` migration warnings.

### 2026-10-16 (submission readiness)
- Added GitHub Actions CI for Python 3.12/3.13 backend tests plus live and read-only frontend production builds, with read-only repository permissions and no secrets.
- Rebuilt and started the current backend image in read-only mode; verified the fixture dossier and SSE completion, and confirmed unauthenticated live lookups/submissions return 401/402.
- Added a manually triggered GitHub Pages workflow for the no-credential replay, with a repo-prefixed asset path and hash routing; local build and static-path checks pass. The first Actions build completed, but publication is waiting on the owner to enable Pages in repository settings.
- Re-read the live Official Rules and updated the Devpost copy and final checklist. The complete source is on `master`; the latest CI run passed on 2026-10-16.

### 2026-10-15 (week 3: onboarding and access status)
- Protected live report metadata, contents, events, and streams behind the judge key while leaving the fixed public replay available. The browser keeps the key only for the current tab; the shared-key limitation is documented. Fixed SSE completion ordering, explicit completion signaling, and stopped fallback polling at terminal events.
- Made PoC network isolation mandatory: hypothesis configs cannot request online execution, and the executor refuses direct calls that disable isolation. The wrapper requires `unshare --user --map-root-user --net` and records a refused run as inconclusive if that namespace cannot be created. Live isolation remains unverified until Sandboxes access is available.
- Changed live report endpoints to authenticate before looking up report IDs, preventing unauthenticated callers from distinguishing valid IDs from missing ones; the public fixture remains readable.
- Replaced the placeholder root README with the read-only fixture quick start, live local setup, CLI examples, configuration table, pipeline summary, and current limitations. It explicitly labels the bundled dossier as fixture data rather than a measured run.
- Made the documented ignored root `.env` workflow real: backend settings load it with `python-dotenv`, and added safe `.env.example` files for backend and frontend configuration.
- Fixed backend package metadata to include its build README and the bundled sample report, and bounded the supported Python range to the `contree-sdk` range used by this project.
- Completed the API-backed read-only demo promised in the architecture: the FastAPI inbox now includes the bundled fixture dossier and its recorded event stream without provider credentials. The UI labels fixture evidence clearly; submission behavior stays read-only unless a judge key is configured.
- Restricted browser API access to configured frontend origins (local Vite origins by default) and added a `MIMI_CORS_ORIGINS` setting for deployment.
- Drafted the Devpost description and a three-minute, fixture-honest demo script; added an original illustrative SVG thumbnail. Hosted URL, screenshots, recording, and final submission remain open.
- Added a non-root Python backend container and a non-root Nginx container for the self-contained static replay. Both images build locally; no production host, registry push, or public URL is configured.
- Fixed the replay container's Nginx config permissions so its unprivileged server can read the copied config. Started the rebuilt image locally and confirmed the inbox, deep report route, and health endpoint return HTTP 200.
- Disabled proxy use in the replay container's health probe so loopback checks reach Nginx directly in proxied environments; the first runtime smoke check showed the previous probe was receiving a proxy 403 while the app itself served successfully.
- Updated API test teardown to remove its SQLite WAL and shared-memory sidecars; rerunning the full suite no longer leaves untracked database artifacts in the checkout.
- Exported an architecture SVG that visibly marks the current Sandboxes access block and unverified network isolation.
- Set the Vite dev port to match the API's default CORS allowlist and excluded local credentials, caches, and generated output from Docker build contexts.
- Ran redacted Gitleaks scans on the current tree and Git history; neither found credential patterns. GitHub metadata reports the source repository is private, so public visibility is still required for submission.
- Re-ran live Token Factory and Tavily spikes. Nano, Super, and Ultra each completed reasoning on/off calls and a function-tool call; Tavily returned 14 results from five public-identifier-only queries. The Ultra call exposed a case error in the configured model ID (HTTP 404); corrected the ID in model routing and cost accounting, then retried successfully. Recorded per-model observations and the query count in `docs/feedback-log.md`.
- Re-ran the Sandboxes `whoami` probe against the then-configured host. Both attempted paths returned HTTP 403 without a permission payload; at that point, live sandbox execution remained unverified and no live reproduction or evaluation result was claimed. The endpoint correction is recorded above.

### 2026-10-07 (week 2: honesty contracts re-verified and pinned)
- Re-verified the 2026-10-06 honesty round against source and fixed what it still got wrong. 205 tests pass under `backend/tests/`; `mypy backend/mimi` is clean.
- **`assert_no_leak` no longer self-exempts.** The previous exemption treated *any* query token as public, so a leaky query that contained report prose made those words exempt and the guard went quiet. Public words are now derived from identifier shape (advisory-id pieces, version pieces, fixed vocabulary) plus at most one package-shaped token — the shape `build_queries` emits. Separately, a CVE id appearing in both the report and the query used to be flagged as "report text leaked", which **silently disabled research** for every report that cites an advisory (no fixed version → no differential → cannot reach Confirmed). That false positive is gone; report prose, URLs and `ghp_`-shaped tokens still raise.
- **The long-token check cannot be tricked in either direction.** A long alphanumeric blob is package-name shaped, so it used to ride along as "the package" — `lodash deadbeef…` passed. The exemption now requires the token to actually be the query's public identifier. The opposite error also had to go: fixed vocabulary (`vulnerability`, `security`, …) is every bit as package-shaped as a real npm name, so a long real package like `node-serialize` or `@babel/traverse` next to ordinary query vocabulary was flagged as a leak — another silent research shutoff. Vocabulary is not a package candidate.
- **Trusted probe is two-channel and fail-closed.** A `SHIM_JS` preloaded into the PoC's Node process snapshots `Object.prototype` natives and wraps `net`/`http`/`dns`/`fetch`, writing real egress attempts to a state file at exit; `PROBE_JS` runs fresh afterwards for filesystem checks and optional egress measurement. A missing or half-written state is `__MIMI_PROBE_MISSING__`, and every probe oracle is then inconclusive — never "did not trigger". Residual forge risk (a PoC that removes exit listeners and writes fake state) is documented in `probe.py`, not hidden.
- **A custom probe pattern can no longer fire on a sibling probe's verdict.** The fixed probes and the hypothesis-declared snippet share one output stream, so a pattern like `attempted` used to match `__MIMI_NETWORK__:attempted` and grade a question the hypothesis never asked. The pattern now searches only the text between the snippet's own begin/end markers, and unterminated snippet output is inconclusive.
- **`network_isolated` is first-marker-wins.** The wrapper prints its `__MIMI_NET__:` token *before* the PoC starts, and only the first occurrence is trusted. A PoC that prints `__MIMI_NET__:open` can no longer flip its own isolation record.
- **Differential keeps each hypothesis's environment.** The fixed-version re-check builds per image-group (`node|install|setup`) but re-runs each hypothesis under its own `RunConfig` (env, `poc_file_name`, `poc_command`, node version). `install_command` now actually reaches `build()`; previously it sat in `config_key` while every build ran the same hardcoded install — fake configuration diversity.
- **Command allowlist enforced in code.** `validate_run_config` rejects a `poc_command`/`poc_file_name` mismatch (a dead run that would read as a clean negative) and executor-owned env keys (`NODE_OPTIONS`, `MIMI_*`) that could disable the observation shim.
- **Missing evidence is never a negative.** `EXIT_CODE` with `exit_code=None` is inconclusive; quantified alternation (`(a|a)*`) is rejected alongside nested quantifiers, so a ReDoS oracle pattern cannot hang the checker.
- **Status and storage honesty.** `asyncio.CancelledError` (a `BaseException`) used to miss the crash arm and persist `status: "complete"` for a run that never reached a verdict — now stored as `"error"`. SQLite access is serialized behind a lock. A stale `status="running"` row with no live task ends its SSE stream instead of keep-aliving forever.
- **An unknown flip is disclosed in the limitations panel.** When a re-check is skipped, errors, or cannot build, `flipped` stays `None` (never `False`) and the dossier now states that in `limitations` as well as the one-line tier rationale — the same class of disclosure as the unmeasured-cost cap.
- **Cost cap is honest about measurement.** `RunBudget` charges measured sandbox cost units (never USD); when every run reports no cost the dossier states the cap could not be enforced, rather than implying it held.
- Tests: 20 new honesty contracts in `backend/tests/test_honesty_contracts.py` (probe forgery, fail-closed probe, environment preservation, command allowlist, `install_command` reach, cancelled-run status, advisory-id research continuity, unconfirmed-flip disclosure) plus repaired fixtures in `test_oracles.py` and `test_run_budget.py`, two-way redaction cover in `test_redaction.py` (long package names must not trip the guard; long blobs must), and custom-probe scoping cover in `test_oracles.py` (a pattern cannot fire on a sibling probe token; unterminated snippet output is inconclusive).

### 2026-10-06 (week 2: evidence-honesty hardening)
- Adversarial review of the pipeline surfaced 28 confirmed defects in the honesty core (3 critical). Fixed as one chain: schemas → oracles → probe → sandboxes → tiers → differential → execute → verdict.
- **Conclusive vs inconclusive results.** An oracle result is conclusive only when the PoC ran, the oracle was correctly configured and the evidence was complete. Errored runs, missing probe verdicts, truncated output and rejected ReDoS patterns are inconclusive — never read as "did not fire". Coverage (`N hypotheses, K configs, 0 triggered`) now counts only conclusive executions, so a negative result is always real.
- **Trusted probe channel** (`backend/mimi/probe.py`). Probe oracles (marker file, prototype pollution, path traversal, network call, custom probe) read `RunRecord.probe_output` from a post-PoC command that inspects real state, never the PoC's stdout, which could forge any `__MIMI_*__:` token.
- **Fixed the execution bug that failed every PoC.** `shlex.quote` around the whole runner made `unshare -n -- 'cd /work && node poc.js'` exec a literal path. Commands now come from a fixed allowlist and are interpolated unquoted; anything else is rejected at validation time, which is the prompt-injection boundary in code (not just in the prompt). `network_isolated` is recorded from the marker the wrapper actually printed, not from the request flag.
- **Differential honesty.** Every hypothesis that fired is re-checked on the fixed version in deterministic order (was "the first three to finish"). `flipped` is `None` when any fixed run is inconclusive — an unknown flip can never upgrade the tier. A missing fixture no longer fabricates a clean fixed run.
- **Run budget is a real cap.** `max_runs_per_report` now bounds *executions* across the whole report: affected-phase forks and fixed-version re-checks draw from one shared `RunBudget`, so a report with many firing hypotheses can no longer run up to twice the configured number of untrusted PoCs. A re-check stopped early by the budget leaves the flip unconfirmed — a flip claimed over a subset would be a coverage lie.
- **Tier table tightening.** A flip is only real when fixed runs executed; "fired on both sides" is Needs human; `versions_tested` lists only versions that really ran; `configs_tested` counts environments, not hypotheses (three hypotheses in one image are one configuration).
- **Privacy boundary.** Model-supplied package names and versions are shape-checked at the Tavily boundary and dropped when they are not identifiers; `verify_query` is a whitelist check that every query token is a public identifier or fixed vocabulary; `assert_no_leak` no longer skips short phrases and also blocks secret-like tokens.
- **Cost and status honesty.** An unpriced model yields `inference_cost_usd: null`, never `$0.00`; `elapsed_ms` is the run's wall clock, not the last stage's latency; a crashed pipeline persists `status: "error"` and still returns a Needs human dossier.
- **SSE live timeline fixed.** Events now fan out to every subscriber queue (they previously went to a queue nobody read); the stream terminates for late subscribers; an unknown report id returns 404 instead of keep-aliving forever.
- **Scoped npm packages accepted.** `@scope/pkg@1.2.3` parses correctly (split on the last `@`); empty versions like `lodash@` are refused.
- Tests: 179 passing under `backend/tests/`, including new API/SSE regression cover (`test_api.py`), shared-budget cover (`test_run_budget.py`) and anti-forgery cases proving stdout tokens cannot fire a probe oracle. `mypy backend/mimi` is clean; `npm run build` and `npm run typecheck` pass.

### 2026-10-06 (week 2: frontend and unit tests)
- Built the React UI under `frontend/` (Vite + React + TypeScript + Tailwind): inbox with submit form, report detail with live SSE timeline (polling fallback), and the dossier view (tier badge, coverage statement, claim, grounding with the evidence-only footnote, research queries sent, hypotheses, runs with exact commands and collapsed outputs, oracle results, differential, reply draft, cost and limitations). `npm run build` and `npm run typecheck` both pass.
- Designed states instead of blanks: "Needs human" is a panel that says what to send next; unmeasured numbers render as "not measured" or an em dash, never a guess. Contradicted shows the coverage count prominently. No third-party logos or icon fonts — text names only.
- Dev-only mock mode (`VITE_USE_MOCK=1`) serves a real-shaped `src/mocks/dossier.json` and labels itself in the header, so the UI can be developed without the backend.
- Unit tests under `backend/tests/` (117 passing): redaction leak guards, every oracle type fired/not-fired/misconfigured, the full tier table including "grounding alone never contradicts", schema round-trips, an end-to-end pipeline on `FixtureExecutor` with a socket guard that fails the test on any network attempt, and cost fields asserted `None` when unmeasured.

### 2026-10-06 (week 2: eval harness)
- Built the evaluation harness under `evals/`: `harness.py` runs case files through the real Pipeline and writes results JSON plus a markdown report to `evals/out/` with the E1-E4 metrics of `docs/02-architecture.md` (Wilson intervals implemented in-repo, no scipy). Cases that cannot execute (no keys, no Sandboxes `spawn`) are recorded as `not run` with a reason — never estimated.
- Case corpus `evals/cases/`: 27 committed JSON cases — 11 real reproductions (advisory-style, exploit withheld; prototype pollution, command injection, RCE, XSS, ReDoS, DoS; public CVEs only), 5 real reworded, 5 synthetic fabricated (prompts published and labelled synthetic in `evals/cases/_schema.md`), 6 safety (egress, fork bomb, huge output, path escape, prompt injection).
- E1 baselines built in: `--mode single_shot` (one Ultra call, no sandbox feedback) and `--mode linear` (no parallel forks). E2 baseline: deterministic grounding-only gate. E3: `--force-model routed|ultra|super` plus `--compare`.
- Wrappers `evals/run_e1.sh`, `evals/run_e2.sh`, `evals/run_e3.sh`, `evals/run_e4.sh`; `evals/README.md` documents budget (~$50 credits) and the public limits (SecBench.js is npm only; synthetic slop is not real slop; no C/C++ memory-safety claims).

### 2026-10-06 (week 2 start: pipeline code)
- Pivot review (scheduled 2026-10-05) recorded: the three triggers cannot be evaluated while Sandboxes permissions are missing (no spikes ran, so no 10-case pilot). Decision: continue Mimi, build the layers that do not need Sandboxes, re-evaluate triggers the day `spawn` becomes available. See `docs/00-constraints-and-open-items.md`.
- Built the backend pipeline (no live API calls yet): claim extraction, grounding, research, hypothesis generation, build-once/fork-per-hypothesis execution, differential, tier assignment, reply draft. Deterministic tier logic and oracle checkers are pure functions with unit-testable surfaces; grounding can never reject a report on its own.
- LLM client with stage routing (Nano/Super/Ultra), reasoning control (`chat_template_kwargs.enable_thinking`) and per-stage token/latency logging into structured events.
- Tavily client with the public-identifiers-only rule enforced before every query (report prose is excluded from Tavily queries).
- Executor layer: `SandboxExecutor` (contree-sdk, build once then fork) and `FixtureExecutor` (recorded replay for tests/CI — never presented as real results).
- FastAPI app (reports, SSE timeline, dossier, whoami) and CLI (`mimi report|whoami|demo`) with three access tiers (demo / judge credential / try-your-own).
- Week-1 spike scripts staged under `scripts/`: Sandboxes `whoami` probe, Token Factory inference checks (tool calling, reasoning control), Tavily redaction spike. Not run yet — keys are not present in this session's environment.
- Bundled demo input: `backend/mimi/data/sample_report.md`, already-public CVE-2021-44906.

### 2026-09-30 (key check)
- Verified Token Factory inference and Tavily with the owner's keys. Recorded exact Nemotron model IDs and how to turn reasoning off.
- Found that the Sandboxes token has no permissions; recorded as a blocker in `docs/00-constraints-and-open-items.md`. (An initial reading of a short key expiry was wrong: `token_expiration` is a rolling five-minute value. Corrected in the docs.)
- Added the no-attribution-in-commits rule to `CLAUDE.md`.
- Added hands-on entries to `docs/feedback-log.md`.

### 2026-09-30
- Project named Mimi; team confirmed solo; Apache-2.0 chosen.
- Added `LICENSE` (standard Apache-2.0 text), `.gitignore` (keeps `.env` and keys out), README stub, this changelog and `docs/feedback-log.md`.
- Constraints file rebuilt from the official Rules; architecture updated for judge access until Dec 15, hosting, and solo scope.

### 2026-09-29
- Added research, decision and architecture drafts under `docs/`.
