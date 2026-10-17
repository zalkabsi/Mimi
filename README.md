# Mimi

**Evidence-first npm vulnerability triage for open-source maintainers.**

Mimi turns a vulnerability report into a reviewable dossier: what the package source supports, which checks ran, what they found, and what a maintainer could say next. It is designed to test a report against the affected package version, then give the maintainer the final say. Mimi does not auto-close reports.

![Mimi project thumbnail: a vulnerability report flows through package grounding, bounded checks, and human review. This is artwork, not a live analysis.](docs/assets/mimi-project-thumbnail.jpg)

Mimi is a project for the **Nebius × NVIDIA Global AI Hackathon 2026**, Track 2: Best Apps and Agents. It combines Nebius Token Factory inference, NVIDIA Nemotron models, Tavily advisory research, and Nebius Sandboxes as the boundary for untrusted proof-of-concept code.

## Demo status

The **[hosted read-only demo](https://zalkabsi.github.io/Mimi/)** is live and needs no account, API key, or provider credits. It opens a fixed sample dossier for exploring the interface; it is not the result of a live vulnerability analysis. See the [deployment guide](docs/deployment.md) for hosting details.

Live report analysis needs provider credentials and permissions. The latest Sandboxes access probe returned HTTP 403, so live untrusted-code execution and execution-dependent evaluation results have not been verified. See [constraints and open items](docs/00-constraints-and-open-items.md) for the current record.

For live analysis, report text is sent to Nebius Token Factory for inference. Tavily receives only public identifiers, not report prose or PoC code. Generated PoC code is sent to Nebius Sandboxes when live execution is enabled.

## Run the sample locally

```bash
cd frontend
npm ci
VITE_USE_MOCK=1 npm run dev
```

Open the local URL printed by Vite and select the sample report. Replay mode makes no provider calls, hides the access-key field, and disables report submissions. On Windows PowerShell, set `$env:VITE_USE_MOCK = "1"` before running `npm run dev`.

## How Mimi works

1. **Ground the report.** Nemotron Nano structures the claim. Deterministic checks compare cited files, symbols, and versions with the affected package source. Source grounding is supporting evidence; it cannot reject a report on its own.
2. **Research public advisories.** Tavily searches with public identifiers such as package names, versions, CVE IDs, and GHSA IDs. Report prose and proof-of-concept code are excluded from search queries.
3. **Plan bounded checks.** Nemotron proposes test hypotheses with predeclared deterministic oracles. The backend validates each operation against an allowlist; the model cannot issue arbitrary tool calls.
4. **Run in an isolated boundary.** Mimi builds the affected package and is designed to run each hypothesis in a separate Nebius Sandbox. Runs have time and output limits, and provider credentials are not sent into a sandbox. This live path still needs access verification.
5. **Return a dossier.** Deterministic tier logic reports the verdict, coverage, commands, outputs, and a draft maintainer reply.

Verdicts are **Confirmed**, **Likely**, **Needs human**, and **Contradicted**. A negative verdict requires executed, conclusive checks and reports which hypotheses and configurations were covered. Failed builds, incomplete runs, and unknown fixed-version results cannot become a clean negative. Every report remains under maintainer control.

## Run the application locally

The read-only sample API can run without provider credentials. Live submissions require a Nebius Token Factory key, a Nebius project with Sandboxes permissions, and optionally a Tavily key. Copy `.env.example` to `.env` and keep credentials out of source control.

Prerequisites: Python 3.12 or 3.13, Node.js 18 or 20+, and npm.

Start the backend from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./backend
uvicorn mimi.api:app --app-dir backend --reload --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

The frontend uses `http://localhost:8000` by default. Without `MIMI_JUDGE_KEY`, the API serves only the bundled read-only dossier. For live report access, set the same judge key in the backend environment and enter it in the UI. The UI keeps it in `sessionStorage` for the current tab; **Clear key** removes it. Anyone holding this shared key can read every report on that deployment, so use only public sample reports on a shared demo. The database defaults to `mimi.db`; set `MIMI_DB_PATH` to use another location.

### CLI

After installing the backend, the CLI can analyze a report file and write a JSON dossier:

```bash
mimi report --package minimist@1.2.5 \
  --file backend/mimi/data/sample_report.md \
  --out dossier.json
```

This command uses live providers and Sandboxes. `mimi whoami` checks Sandbox access without printing credentials. `mimi demo` runs the bundled public CVE-2021-44906 sample through the live pipeline; it is not a no-credentials demo.

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEBIUS_API_KEY` | Token Factory inference and Sandboxes access. Store it in an environment secret or ignored `.env` file. |
| `NEBIUS_PROJECT_ID` | Project sent as the Sandboxes `Project` header; the token also needs the required grants. |
| `TAVILY_API_KEY` | Optional live advisory research. Without it, the dossier records that research was skipped. |
| `MIMI_JUDGE_KEY` | Protects API submissions and live report reads through the `X-Mimi-Key` header. |
| `MIMI_DB_PATH` | SQLite database path; defaults to `mimi.db` in the process working directory. |
| `MIMI_CORS_ORIGINS` | Comma-separated browser origins allowed to call the API. Defaults to the local Vite URLs. |
| `MIMI_FORCE_MODEL` | Optional evaluation override: `nano`, `super`, or `ultra`. |
| `VITE_API_BASE` | API URL used by the frontend; defaults to `http://localhost:8000`. |
| `VITE_USE_MOCK` | Set to `1` to browse the bundled read-only sample without the backend. |

## Evaluation and limits

The repository includes an evaluation harness with 27 cases. Cases that cannot run are recorded as `not_run`; missing results are never estimated. See [the evaluation guide](evals/README.md) for suites and commands. The corpus includes public npm vulnerability cases and clearly labelled synthetic reports. Synthetic cases are not real reports, and results do not generalize to C/C++ memory-safety vulnerabilities. The current product scope is npm.

The current environment's Sandboxes `whoami` probe returned HTTP 403 on October 15, 2026, for both supported endpoint paths. The cause could not be narrowed to a specific missing grant. Real Sandbox execution, the fail-closed child user/network namespace guard, and execution-dependent evaluation suites therefore remain unverified. Mimi makes no claim about reproduction rates, model-routing results, Sandbox costs, or live demo results.

## Project links

- [Architecture and evaluation protocol](docs/02-architecture.md)
- [Architecture diagram](docs/assets/architecture.svg)
- [Deployment guide](docs/deployment.md)
- [Constraints and open items](docs/00-constraints-and-open-items.md)
- [Product feedback log](docs/feedback-log.md)
- [Hackathon submission copy and demo script](docs/submission-kit.md)
- [Build log](CHANGELOG.md)
- [Apache-2.0 license](LICENSE)

## Security

Do not run reporter-supplied proof-of-concept code on the application host. Mimi is designed to execute it inside Nebius Sandboxes, but that boundary has not been verified in the current environment. Treat live execution of untrusted reports as blocked until Sandbox access and per-run network isolation are confirmed. Package install and setup scripts also run inside the sandbox as its unprivileged `node` account. Probe-style observations use state in the same writable sandbox VM as the PoC and are not tamper-proof against hostile code; the dossier flags this limitation. Review the [architecture and trust boundaries](docs/02-architecture.md) before exposing a live deployment. Never place provider credentials or private report data in a sandbox.
