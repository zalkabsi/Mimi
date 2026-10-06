# Changelog

All work in this repository was created during the hackathon Submission Period (Aug 26 - Oct 30, 2026). The repository was empty before the first commit on 2026-09-29; no pre-existing code was imported.

## Unreleased

### 2026-10-06 (week 2: eval harness)
- Built the evaluation harness under `evals/`: `harness.py` runs case files through the real Pipeline and writes results JSON plus a markdown report to `evals/out/` with the E1-E4 metrics of `docs/02-architecture.md` (Wilson intervals implemented in-repo, no scipy). Cases that cannot execute (no keys, no Sandboxes `spawn`) are recorded as `not run` with a reason — never estimated.
- Case corpus `evals/cases/`: 27 committed JSON cases — 11 real reproductions (advisory-style, exploit withheld; prototype pollution, command injection, RCE, XSS, ReDoS, DoS; public CVEs only), 5 real reworded, 5 synthetic fabricated (prompts published and labelled synthetic in `evals/cases/_schema.md`), 6 safety (egress, fork bomb, huge output, path escape, prompt injection).
- E1 baselines built in: `--mode single_shot` (one Ultra call, no sandbox feedback) and `--mode linear` (no parallel forks). E2 baseline: deterministic grounding-only gate. E3: `--force-model routed|ultra|super` plus `--compare`.
- Wrappers `evals/run_e1.sh`, `evals/run_e2.sh`, `evals/run_e3.sh`, `evals/run_e4.sh`; `evals/README.md` documents budget (~$50 credits) and the public limits (SecBench.js is npm only; synthetic slop is not real slop; no C/C++ memory-safety claims).

### 2026-10-06 (week 2 start: pipeline code)
- Pivot review (scheduled 2026-10-05) recorded: the three triggers cannot be evaluated while Sandboxes permissions are missing (no spikes ran, so no 10-case pilot). Decision: continue Mimi, build the layers that do not need Sandboxes, re-evaluate triggers the day `spawn` becomes available. See `docs/00-constraints-and-open-items.md`.
- Built the backend pipeline (no live API calls yet): claim extraction, grounding, research, hypothesis generation, build-once/fork-per-hypothesis execution, differential, tier assignment, reply draft. Deterministic tier logic and oracle checkers are pure functions with unit-testable surfaces; grounding can never reject a report on its own.
- LLM client with stage routing (Nano/Super/Ultra), reasoning control (`chat_template_kwargs.enable_thinking`) and per-stage token/latency logging into structured events.
- Tavily client with the public-identifiers-only rule enforced before every query (report text never leaves the system).
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
