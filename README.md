# Mimi

**Every vulnerability report gets a verdict with receipts.**

Open-source maintainers receive vulnerability reports they cannot cheaply verify. Mimi reproduces a report's claim in isolated sandboxes at the exact affected version and returns an **evidence dossier and a triage tier**. It never auto-closes a report; the maintainer decides.

Built solo for the Nebius x NVIDIA Global AI Hackathon 2026 (Track 2, Best Apps and Agents), on Nebius Token Factory (Nemotron models and Sandboxes) with Tavily for research.

## The idea: negative-result coverage

Most tools can say "reproduced". Mimi is built to say something honest when it cannot: it builds the environment once, forks the sandbox per hypothesis, and reports **"N hypotheses tested, 0 triggered"** with the commands and outputs, instead of a bare "not reproduced". A PoC that crashes before judging is recorded as inconclusive, never as a negative.

Tiers: **Confirmed**, **Likely**, **Needs human**, **Contradicted (with coverage)**. Grounding (does the cited file or symbol exist) ranks hypotheses but can never reject a report on its own.

## How it works

1. **Extract** the claim from the report (Nemotron Nano, schema-validated; the report is treated as data, not instructions).
2. **Ground** cited files and symbols (Nano).
3. **Research** with Tavily using public identifiers only (package, version, CVE/GHSA ids). Report text never leaves the system; a leak guard fails closed before every query. The fixed version comes from the public npm advisory database, not from a model.
4. **Hypothesize** (Nemotron Ultra): up to 8 ways the claim could hold, each with a self-contained PoC and a predeclared deterministic oracle. Commands come from a fixed allowlist.
5. **Build once, fork per hypothesis** in Token Factory Sandboxes. PoC phases run offline (`unshare -n`, recorded as `network_isolated`). No secrets exist in any sandbox.
6. **Repair round**: PoCs that crashed before judging get one rewrite against the package's measured API surface. Only `poc_code` may change, never the oracle.
7. **Differential**: hypotheses that fired are re-run on the fixed version. Confirmed means it fires on the affected version and not on the fixed one.
8. **Verdict and reply draft** (Nemotron Super; Ultra when evidence is ambiguous). The tier is assigned by deterministic code; the model only writes the rationale.

Untrusted PoC code runs only inside Sandboxes, never on the app host.

## Run it

Requires Python 3.12+ and Node 20+. Keys come from environment variables only; never commit them.

```bash
export NEBIUS_API_KEY=...       # Token Factory inference and Sandboxes bearer token
export NEBIUS_PROJECT_ID=...    # Sandboxes need both
export TAVILY_API_KEY=...       # research stage

pip install -e "backend[dev]"
python scripts/check_sandboxes_whoami.py     # permissions only, never prints keys
python -m pytest backend/tests               # no network, no keys needed

# CLI: one bundled public CVE end to end
python -m mimi.cli demo
# or your own report
python -m mimi.cli report --package minimist@1.2.5 --file report.txt --out dossier.json

# API and UI
cd backend && uvicorn mimi.api:app --port 8000
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Access tiers for the hosted app: read-only demo mode (no login, recorded runs), a judge credential for live runs, and self-hosting. See `docs/02-architecture.md`.

## Evaluation

The harness lives in `evals/` (see `evals/README.md`): a 27-case corpus of already-public npm vulnerabilities, reworded reports, clearly labelled synthetic fabricated reports, and safety cases. Every number must come from a logged run; reports are in `docs/eval-logs/`.

**Current state (development runs, one run per case, small n; see `CHANGELOG.md`):**

| What | Result | n |
|---|---|---|
| E1, oracle fired (pipeline, 3 passes) | 7/11 each pass | 11 real npm CVEs |
| E1, confirmed with fixed-version differential | 3/11, 2/11, 3/11 | 11 |
| E1 baselines: linear / single-shot oracle fired | 6/11 / 6/11 (single-shot cannot confirm) | 11 |
| E2, real reports wrongly Contradicted (after advisory gate) | 0/5 (95% CI 0-43%) | 5 |
| E2, fabricated reports Contradicted / reached Likely | 4/5 / 1/5 | 5 |

Honest reading: reproduction rate is not clearly better than the simple baselines; what the pipeline adds is the fixed-version differential, parallel speed and quantified negative coverage. Tiers for the same case can change between runs, so treat any single verdict as evidence to review, not a ruling.

Limits, stated up front:

- SecBench.js-style cases are **npm only**. No other ecosystem is covered.
- Synthetic slop is not real slop; those cases are published prompts, not naturally occurring bad reports.
- No claims for C/C++ memory-safety reports.
- Sample sizes are small; intervals are Wilson 95%.
- Sandbox cost per run is not exposed by the SDK and is recorded as not measured.

## Repository map

- `backend/mimi/`: pipeline stages, oracles, executor, redaction guard, API, CLI
- `backend/tests/`: unit and fixture-replay tests (no network)
- `frontend/`: React + Vite UI (inbox, live timeline, dossier)
- `evals/`: harness and case corpus
- `scripts/`: spikes and the Sandboxes permission probe
- `docs/`: research and decision, architecture and eval protocol, constraints, feedback log, eval logs

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
