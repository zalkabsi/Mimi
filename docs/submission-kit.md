# Hackathon submission kit

Updated 2026-10-16 for the Nebius × NVIDIA Global AI Hackathon 2026. The live
[Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) were
re-read on this date. The deadline is October 30, 2026 at 10:00 AM Pacific.
Replace bracketed fields only after the linked artifact is real. Keep the
hosted replay demo, live provider checks, and end-to-end sandbox execution
clearly distinguished in public copy.

## Devpost fields

### Project name

Mimi

### Tagline

Every vulnerability report gets a verdict with receipts.

### Short description

Mimi helps open-source maintainers triage npm vulnerability reports with an
evidence dossier: package grounding, public advisory research, bounded test
hypotheses, oracle outcomes, coverage, and a human-review reply draft. It never
auto-closes a report.

### Inspiration

Maintainers can spend hours separating a real vulnerability report from an
incomplete or incorrect claim. A negative answer is especially risky when it
does not say what was tested. Mimi is designed around that gap: it records the
evidence and the limits of each run so a maintainer can make the decision.

### What it does

Mimi turns a public npm vulnerability report into a structured dossier. It
extracts the claim, checks the cited package version and symbols, searches
public advisory sources using public identifiers, and asks Nemotron to propose
bounded hypotheses with declared oracles. Its pipeline is designed to build
the affected package once, fork isolated runs, and compare a fixed version
when the evidence supports that check. The dossier reports exact commands,
outputs, cost and latency only when measured, and the number of hypotheses and
configurations covered. Every result remains for human review; Mimi takes no
external action.

The repository includes a no-credential, read-only replay demo using an
explicitly labelled fixture. Live inference and Tavily calls were exercised
individually. At the latest status check, Sandboxes returned HTTP 403, so live
untrusted-code execution and the execution-dependent evaluations remain
blocked. No live reproduction rate or end-to-end sandbox result is claimed.

### How we built it

The backend is Python, FastAPI, and SQLite. The UI is React, TypeScript, Vite,
and Tailwind. Nebius Token Factory is used for NVIDIA Nemotron 3 Nano, Super,
and Ultra inference; Nebius Token Factory Sandboxes are the intended execution
boundary for reporter-supplied PoCs; Tavily is used for public advisory
research. A deterministic tier layer keeps grounding evidence from becoming
a verdict by itself and treats incomplete runs as inconclusive.

### Challenges

The core challenge is making a negative result interpretable without treating
missing evidence as proof. Mimi requires a declared oracle, records coverage,
and will not turn build errors or incomplete runs into a clean negative. The
other major challenge is safely executing untrusted proof-of-concept code.
Our current Nebius Sandboxes credential receives HTTP 403, so the live
execution boundary has not yet been validated in this environment. The
repository and demo disclose that limitation instead of substituting fixture
data for a real run.

### What we learned

Single-prompt smoke calls showed that Nano, Super, and Ultra each completed a
function-tool call through Token Factory, while reasoning usage and latency
varied by model and prompt. These are onboarding observations, not a routing
benchmark. Tavily returned 14 results from five queries made only from public
identifiers; report prose was checked out of the search path. We also found
that valid-looking Sandboxes credentials can fail before exposing a usable
permission response, which makes a small `whoami` access check essential
before promising live execution.

### Built with

- Nebius Token Factory
- Nebius Token Factory Sandboxes
- NVIDIA Nemotron 3 Nano, Super, and Ultra
- Tavily Search API
- Python, FastAPI, SQLite
- React, TypeScript, Vite, Tailwind CSS

### Try it

- Hosted demo: **[add the public URL after deployment and a clean-browser check]**
- Demo mode: open the hosted read-only replay and use the labelled sample
  report. This static replay never accepts submissions; the separate live API
  path requires a judge key and working Sandboxes access.
- Source: https://github.com/zalkabsi/Mimi
- Setup: see the repository README.

### Testing instructions (use after the hosted URL is verified)

Open the demo URL in a browser. No account, key, or payment is needed. Select
the labelled sample report to view its dossier and recorded timeline. This is
a fixed read-only replay: it makes no provider calls, runs no proof-of-concept
code, and does not accept report submissions. The README explains how to run
the project locally and distinguishes the replay from live analysis.

## Three-minute demo script

Target length: 2:40, leaving room for an intro/outro. Show only a real app
screen and the actual fixture labels. Do not present fixture timing, cost, or
execution outputs as measured results.

| Time | Shot and narration |
|---|---|
| 0:00–0:18 | **Inbox.** “This is Mimi, a vulnerability-report triage workbench for open-source maintainers. The goal is not an automatic reject button; it is a reviewable evidence dossier.” |
| 0:18–0:38 | **Open the sample row.** Point out the visible demo/fixture label. “This sample is replay data. It lets a judge inspect the interface without credentials, and it is not a live run.” |
| 0:38–1:15 | **Timeline.** Scroll through extract, grounding, research, hypotheses, build, forks, differential, and verdict. “Each stage records what it did. The UI distinguishes recorded fixture values from measurements, and missing cost or incomplete execution stays missing.” |
| 1:15–1:55 | **Dossier.** Show the report, claim, advisory reference, declared hypotheses and oracles, exact commands, oracle results, coverage, tier rationale, and reply draft. “A Contradicted tier requires executed evidence and coverage; grounding alone cannot reject a report. A negative result is bounded by what was actually tested.” |
| 1:55–2:22 | **Architecture.** Show a simple diagram or the architecture page. “Token Factory routes extraction, research, and hypothesis work across Nemotron Nano, Super, and Ultra. Tavily receives public identifiers only. Sandboxes is the required boundary for reporter PoCs.” |
| 2:22–2:40 | **Limits and close.** “The current Sandboxes access check returns HTTP 403, so this walkthrough is replay-only and we do not claim an end-to-end reproduction result. Mimi keeps that limitation visible. Every report stays open for a maintainer to decide.” |

If Sandboxes access becomes available before recording, replace the replay-only
section with a fresh run on an already-public report, show its actual event
timeline and dossier, and update this script and all public claims from the
recorded evidence. Do not reuse fixture timestamps, IDs, outputs, or costs as
live evidence.

## Artifact checklist

- [x] Public source repository and Apache-2.0 license are present.
- [x] Redacted Gitleaks scans of the current tree and Git history returned zero findings on 2026-10-15.
- [x] Local no-credential replay instructions are documented.
- [x] Static replay frontend build, backend Docker image, and read-only frontend replay image built on 2026-10-16.
- [x] Backend test suite passes: 183 tests on 2026-10-16 (one upstream Starlette/httpx deprecation warning).
- [x] Started the current backend image without provider credentials: health, inbox, sample dossier, events, and completed SSE stream worked; a live-ID lookup returned 401 and submission returned 402.
- [x] Started the replay container locally and confirmed the inbox, direct dossier route, health endpoint, and built JS/CSS assets return HTTP 200; the container health status is healthy after disabling proxy use for its loopback health probe.
- [x] Architecture diagram exported as SVG and visibly labels the live Sandbox access limit.
- [x] Devpost copy and an honest demo script are drafted above.
- [x] Push the final source changes and confirm the latest GitHub Actions CI run is green (2026-10-16).
- [ ] Publish a hosted URL and test access from a clean browser.
- [ ] Verify Sandboxes access and child user/network namespace isolation before live
  PoC execution.
- [ ] Run and report the planned E1/E2/E3/E4 results with sample sizes; keep
  blocked cases marked `not_run`.
- [ ] Capture real inbox and dossier screenshots from the running app.
- [ ] Record and upload the final video (under three minutes).
- [ ] Submit the Devpost entry with the live URL, screenshots, and video.
- [ ] Confirm the judge access key and provider credits remain valid and free
  through the judging period.

The boxes above reflect deliverables only; completion of a checkbox does not
change the documented provider or security limitations.
