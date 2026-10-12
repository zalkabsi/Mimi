# Devpost text draft (fill `[LOG]` only from logged runs)

**Track:** Track 2, Best Apps and Agents. **Bonus target:** Best Use of Tavily.

## Inspiration
Maintainers receive vulnerability reports they cannot cheaply verify, and a wrong "not reproduced" can leave a real bug open. Mimi is built around saying how much was tested, not just whether it worked.

## What it does
Mimi reproduces a report's claim in isolated Token Factory Sandboxes at the exact affected version and returns an evidence dossier and a triage tier: Confirmed, Likely, Needs human, or Contradicted with coverage. It never auto-closes a report. Its core idea is negative-result coverage: build the environment once, fork a sandbox per hypothesis, and report "N hypotheses tested, M triggered" with the commands and outputs.

## How we built it
- **Nemotron on Nebius Token Factory** with stage routing: Nano for extraction and grounding, Super for research synthesis and drafts, Ultra for hypothesis generation and ambiguous verdicts.
- **Token Factory Sandboxes**: one build, one fork per hypothesis, offline PoC runs (`unshare -n`), a differential run on the fixed version.
- **Tavily** for research, with a leak guard that guarantees only public identifiers (package, version, CVE/GHSA id) are ever sent.
- Deterministic oracles and tier logic; the model never assigns the tier. FastAPI, SQLite, React/Vite. Apache-2.0.

## Challenges
- PoCs written by the model often crash on an API that does not exist. Early on this made real CVEs look "Contradicted". We now treat a crash as inconclusive and give each crashed PoC one repair round against the package's measured API surface.
- Trusting search snippets for the fixed version was flaky; it now comes from the public npm advisory database.
- Run-to-run variance is large; we report it instead of hiding it.

## Accomplishments
`[LOG]` E1 results with n, spread and intervals; baselines (single-shot, linear) `[LOG]`; safety suite `[LOG]`.

## Limitations
npm only. Synthetic slop is not real slop. No C/C++ memory-safety claims. Sandbox cost per run is not exposed by the SDK. Small samples.

## What's next
More ecosystems, stronger hypothesis generation, maintainer-side integrations.

## Built with
Nebius Token Factory, Token Factory Sandboxes, NVIDIA Nemotron 3 (Nano, Super, Ultra), Tavily, FastAPI, SQLite, React, Vite.

## Testing instructions
Demo mode needs no login (recorded runs). Judge credential for live runs: `[provided in the submission form]`. Self-host steps are in the README.

## Feedback
See `docs/feedback-log.md`.
