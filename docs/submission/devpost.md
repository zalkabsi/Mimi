# Devpost submission text (ready to paste)

Fields marked **[OWNER]** are the only things left to fill in; everything else is final and every number comes from a logged run (`docs/eval-logs/`, `CHANGELOG.md`).

**Project name:** Mimi
**Tagline:** Every vulnerability report gets a verdict with receipts.
**Track:** Track 2, Best Apps and Agents
**Bonus target:** Best Use of Tavily

## Inspiration

Maintainers of open-source packages receive vulnerability reports they cannot cheaply verify. Some are real, some are mistaken, some are fabricated by tools. Closing a real one on a guess leaves users exposed; chasing a fake one wastes a weekend. Existing tools can say "reproduced". We wanted one that says something honest when it cannot: how many ways it tried, and what happened.

## What it does

Paste a report and a package version. Mimi reproduces the claim in isolated Nebius Token Factory Sandboxes at that exact version and returns an **evidence dossier and a triage tier**: Confirmed, Likely, Needs human, or Contradicted with coverage. It never auto-closes a report.

Its central idea is **negative-result coverage**. Mimi builds the environment once, forks the sandbox for each hypothesis, and reports "N hypotheses tested, K triggered" with the exact commands and outputs instead of a bare "not reproduced". A test script that crashes is recorded as inconclusive, never as a negative. When a test fires on the affected version, Mimi re-runs it on the fixed version; only a fire that disappears on the fix is Confirmed. If a public npm advisory names the same package, version and bug class, a run where nothing fired cannot contradict the report; it goes to a human with the advisory attached.

## How we built it

An eight-stage pipeline in which every stage calls **Nebius Token Factory** at runtime:

1. **Nemotron 3 Nano** extracts a structured claim from the report (the report is treated as data, not instructions) and grounds cited files and symbols.
2. **Tavily** looks up public advisories using only the package name, version and CVE/GHSA id. A leak guard fails closed if any report text could reach a query.
3. **Nemotron 3 Ultra** writes up to eight hypotheses, each with a small test script and a pass/fail rule fixed in advance. Commands come from a fixed allowlist.
4. **Token Factory Sandboxes** build the package once and fork one sandbox per hypothesis. Test scripts run offline (`unshare -n`), in parallel, with no secrets present.
5. Scripts that crashed get one repair round against the package's measured exports; only the script may change, never the pass/fail rule.
6. Hypotheses that fired are re-run on the fixed version, taken from the public npm advisory database.
7. **Nemotron 3 Super** writes the rationale and a reply draft; the **tier itself is assigned by deterministic code**.

FastAPI, SQLite, React and Vite. Apache-2.0.

## Challenges we ran into

- **Model-written test scripts often crash** on an API that does not exist. In our first evaluation pass, most "Contradicted" verdicts on real vulnerabilities came from crashed scripts being counted as negatives. We now treat a crash as inconclusive and measure the package's real API for a repair round.
- **A search-snippet fixed version was flaky**, so it now comes from the public npm advisory database.
- **Generated tests missed real bugs.** On our slop-discrimination set, 2 of 5 real reworded reports were wrongly Contradicted before we added the advisory check; 0 of 5 after (n=5, 95% CI 0-43%, and the check was designed against those same cases).
- **Results vary between runs.** The same report can change tier between identical passes, so we report the spread instead of one headline number.

## Accomplishments

- A complete, working end-to-end pipeline on live Token Factory inference, Sandboxes and Tavily.
- On 11 real npm vulnerabilities, three same-code passes (one run per case): an oracle fired on 7 of 11 in every pass and 2-3 of 11 were confirmed against the fixed version. A single-shot baseline fired 6 of 11 and cannot confirm; a sequential baseline fired 6 of 11 and confirmed 1 (about 94 s median vs about 68 s with parallel forks).
- Safety cases: network stayed blocked, runs stayed time-bounded, and none was ever Confirmed on hostile input.
- Everything is logged: failed ideas and bugs included.

## What we learned

Reproduction rate was not clearly better than the simple baselines (7/11 vs 6/11, intervals overlap). What the build-once/fork design and the fixed-version check add is the ability to Confirm, speed, and quantified negative coverage. That is the claim we make.

## Limitations (we state these up front)

npm only; no C/C++ memory-safety claims; synthetic slop is not real slop; small samples and one run per case; sandbox cost per run is not exposed by the SDK; cost figures for inference use an assumed rate table, not an invoice; output-pattern tests are printed by the script itself, so the fixed-version check and trusted probes are what guard against self-reported success (one fabricated report still reached Likely).

## What's next

More ecosystems, stronger hypothesis generation, seeded evaluations with more repeats, and maintainer-side integrations that attach the dossier to an advisory.

## Built with

Nebius Token Factory, Token Factory Sandboxes, NVIDIA Nemotron 3 (Nano, Super, Ultra), Tavily, Python, FastAPI, SQLite, React, Vite, Playwright (UI checks and demo recording).

## Try it

- **Demo URL: [OWNER: hosted URL]**. Demo mode needs no login and shows recorded real runs: a Confirmed minimist vulnerability, a fabricated report that stays Contradicted with coverage, and a case where Mimi refuses to confirm.
- **Judge credential for live runs: [OWNER: key, as `X-Mimi-Key` / "Access key" field]**.
- Repository, setup and self-hosting steps: the README. Hosted for judges free of charge until December 15.

## Feedback on Nebius and NVIDIA tools

See `docs/feedback-log.md` in the repository; the summary table at its top is written for the organisers.
