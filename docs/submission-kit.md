# Hackathon submission kit

Updated 2026-10-17 for the Nebius × NVIDIA Global AI Hackathon 2026. The live
[Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) were
last re-read on 2026-10-16. The deadline is October 30, 2026 at 10:00 AM
Pacific; re-read the rules again immediately before submission.
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

### Elevator pitch

Mimi gives open-source maintainers an evidence dossier for npm vulnerability
reports: package grounding, public advisory context, bounded tests,
deterministic oracle results, and explicit coverage. It shows what the checks
established and leaves the decision with a human. The hosted demo is a clearly
labelled replay; live sandbox execution remains unverified.

### About the project

#### Inspiration

Open-source maintainers can spend hours deciding whether a vulnerability
report is real. A negative result is especially hard to trust when it does not
say what was tested or how much of the claim was covered. I built Mimi to make
that investigation easier to review and to keep the final decision with the
maintainer.

#### What I built

Mimi turns an npm vulnerability report into an evidence dossier. It structures
the claim, checks the package version and cited symbols, searches public
advisories using identifiers, and proposes bounded test hypotheses with
predeclared deterministic oracles. The dossier is designed to show commands,
outputs, and coverage alongside a draft maintainer response. Mimi never
auto-closes a report.

The hosted demo is a fixed, read-only replay. It makes no provider calls and
does not run a live vulnerability analysis. Live inference and advisory-search
integrations were exercised individually, but the latest recorded Nebius
Sandboxes check (2026-10-15) returned HTTP 403. No end-to-end PoC execution or
sandbox-isolation result is claimed. For
live analysis, report text is sent to Nebius Token Factory; Tavily receives
only public identifiers, not report prose or PoC code.

#### How I built it

The backend uses Python, FastAPI, and SQLite; the frontend uses React,
TypeScript, Vite, and Tailwind CSS. Nebius Token Factory runs NVIDIA Nemotron
Nano, Super, and Ultra for language-model tasks, while Tavily searches public
advisory sources. Deterministic backend logic evaluates declared test oracles
and reports coverage. Incomplete runs and missing evidence stay inconclusive;
grounding alone cannot produce a negative verdict. The live execution path is
designed to place untrusted PoC code in isolated Nebius Sandboxes, but that
boundary still needs access verification.

#### What I learned

Language models can help structure reports and suggest tests, but the verdict
needs explicit, deterministic evidence. I also learned that restricting
advisory searches to public identifiers helps avoid sending report prose to a
search provider. Integration smoke checks showed that each Nemotron model could
complete a sample function-tool call and that Tavily could return advisory
results; these checks were not a routing benchmark or an end-to-end evaluation.

#### Challenges

The main design challenge was making a negative result useful without treating
missing evidence as proof. Mimi requires declared oracles and records coverage;
build failures and incomplete runs cannot become clean negative results. The
other challenge was validating safe execution of untrusted PoC code. The latest
recorded Sandboxes access check (2026-10-15) returned HTTP 403, so I could not
verify live execution or isolation. I kept that limitation visible in the app
and submission materials instead of
presenting the replay fixture as a real run.

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
individually. At the latest recorded Sandboxes check (2026-10-15), the service
returned HTTP 403, so live
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
The latest recorded Nebius Sandboxes check (2026-10-15) returned HTTP 403, so
the live execution boundary has not been validated. The review environment's
key/project binding readiness is currently unknown. The
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

### Tavily usage qualification

Yes. The live backend integrates a Tavily client in Mimi's research stage and
makes runtime `/search` requests using public package and advisory identifiers.
A live API smoke run returned 14 results from five identifier-only queries.
The hosted demo is a fixed read-only replay and makes no Tavily calls; the
end-to-end path remains unverified because Nebius Sandboxes access returned
HTTP 403.

### Nebius platform capabilities used

The most valuable capability was managed inference through Nebius Token
Factory. The backend calls its OpenAI-compatible Chat Completions API with a
project API key, without deploying model weights or managing GPU instances.
This let Mimi route work among Nemotron Nano, Super, and Ultra through one
service and use structured responses, function calling, and reasoning controls.
The models completed individual integration smoke checks. I did not configure
a GPU instance type, deploy a custom endpoint, load-test scaling, or complete a
live end-to-end report run.

Nebius Sandboxes is the intended isolation boundary for untrusted proof-of-
concept execution, but access returned HTTP 403. The live sandbox path could
not be validated. The hosted demo is a fixed replay and makes no Nebius API
calls.

### Recommendation rating

**8/10.** I would recommend Nemotron on Token Factory for teams that want a
quick API integration and multiple model sizes for task-based routing. The
OpenAI-compatible endpoint made initial calls straightforward, and all three
tested model variants supported the same function-call smoke test. Developers
should use exact model IDs and budget enough output tokens: Nano can spend a
tiny budget on reasoning and return empty content. Token-usage details vary by
model, and our latency and quality checks were too limited to establish
production performance. This rating is for Token Factory inference; Sandboxes
access was blocked separately and is not covered by it.

### Experience compared with other environments

**8/10 (developer experience; not a performance benchmark).** The managed
Token Factory endpoint let me integrate Nemotron without downloading model
weights or provisioning a GPU server, and its OpenAI-compatible API made the
first calls straightforward. I did not run the same workload on a local GPU or
another cloud, so I cannot compare speed, cost, or output quality directly.
The main rough edges were inconsistent model-ID casing, Nano's empty response
when the output budget was too small, model-dependent usage metadata, and
variable one-shot latency.

### Improvements that would help

Canonical, consistent model IDs and a capability table would make model
selection safer; the exact casing of the Ultra ID caused a 404 until corrected.
The API should report reasoning-token usage consistently across variants and
warn clearly when a token budget is exhausted before visible answer content is
returned. Practical examples for reasoning controls and output-budget sizing
would also help developers avoid Nano's empty-content case. For Mimi's broader
workflow, actionable Sandboxes permission errors would help distinguish a
missing grant from other access failures; the recorded HTTP 403 did not include
a permissions payload, blocking live PoC execution at that time.

### What I hope to see next from the Nemotron team

I’d like consistent reasoning and output-token accounting across Nano, Super,
and Ultra, plus an explicit signal when a request uses its token budget on
reasoning before returning answer content. A maintained, case-consistent model
catalog with tested guidance for function calling, schema-constrained JSON,
reasoning controls, and token-budget sizing would make it easier to choose and
route models reliably in production.

### Models used and why

Mimi routes NVIDIA Nemotron 3 Nano 30B-A3B, Super 120B-A12B, and Ultra
550B-A55B through Nebius Token Factory. Nano handles frequent structured
tasks such as claim extraction; Super synthesizes advisory research and
supports verdict and reply drafting; Ultra generates bounded test hypotheses
that need deeper reasoning. This stage-based design reserves the larger model
for the most reasoning-intensive task while using smaller variants for routine
work. Model outputs are constrained, deterministic checks evaluate declared
oracles, and a maintainer makes the final decision.

Each model completed an individual integration smoke call, but the full live
pipeline and its model-routing performance have not been evaluated end to end.
Nebius Sandboxes returned HTTP 403, so execution-dependent tests remain
unverified. The hosted demo is a fixed replay and makes no model calls.

### Nemotron output quality rating

**7/10 (provisional; based on integration smoke checks, not a full evaluation).**
Nano, Super, and Ultra all produced the requested function call in a constrained
advisory-lookup prompt, and reasoning controls worked. One limitation: with a
very small output-token budget, Nano spent the budget on reasoning and returned
empty answer content, so calls need an adequate output budget. Schema-validated
JSON calls retry once on invalid output, then fail rather than inventing a
result. Accuracy on full vulnerability reports, hypothesis quality, end-to-end
reasoning, and multilingual performance have not been evaluated.

### Fine-tuning and prompting

I used the pretrained Nemotron models through Nebius Token Factory without
fine-tuning. I prompt-engineered separate calls for each pipeline stage and
constrained outputs with JSON schemas and tool definitions. Prompts treat
report text as untrusted data and tell the model not to follow instructions
inside it. For hypothesis generation, the model must provide a bounded test
plan and a deterministic oracle; backend allowlists validate proposed
operations, and deterministic code evaluates outcomes and coverage. The model
does not issue arbitrary tools or decide the final verdict. I also tuned
reasoning and output-token settings; a tiny token budget can leave Nano with
empty answer content. Schema-validated JSON calls retry once on invalid output
and then fail rather than inventing a result. Full end-to-end prompt quality
remains unverified while Sandboxes access is blocked.

### Comparison with other models

I did not run a controlled, same-prompt comparison between Nemotron and other
models on Mimi's vulnerability-triage tasks, so I cannot claim better accuracy,
latency, or cost. In integration smoke checks, Nano, Super, and Ultra all
completed the requested advisory-lookup function call. A tiny output budget
caused Nano to return empty answer content with reasoning enabled, and the
single-call latency samples were too limited and variable to rank the models.
Codex and Claude Code were used as development assistants, not as runtime
baselines for this workload. A fair comparison still needs a labelled report
set, repeated runs, and live execution access.

Suggested Devpost tags (19 of 25): Nebius Token Factory, Nebius Token
Factory Sandboxes, NVIDIA Nemotron, Tavily, Python, FastAPI, SQLite, React,
TypeScript, Vite, Tailwind CSS, Docker, GitHub Actions, GitHub Pages, npm,
Generative AI, Cybersecurity, Open Source, Vulnerability Management.

## Three-minute demo script

Target length: 2:40, leaving room for an intro/outro. Show only a real app
screen and the actual fixture labels. Do not present fixture timing, cost, or
execution outputs as measured results.

| Time | Shot and narration |
|---|---|
| 0:00–0:18 | **Inbox.** “This is Mimi, a vulnerability report triage workbench for open-source maintainers. Its goal is not an automatic rejection. It assembles a reviewable evidence dossier, while the maintainer makes the final decision. Mimi never auto-closes a report.” |
| 0:18–0:38 | **Open the sample row.** Point out the visible replay label. “This labelled sample is recorded replay data. It lets anyone inspect the interface without credentials, but it is not a live analysis. The public page makes no provider calls. Every timestamp and finding belongs to the fixture.” |
| 0:38–1:15 | **Timeline.** Scroll through extract, grounding, research, hypotheses, build, forks, differential, verdict, and reply. “Here is the recorded pipeline: claim extraction, package grounding, public advisory research, bounded test hypotheses, environment builds, isolated forks, a fixed-version comparison, a verdict, and a reply draft. Everything shown here is fixture data, including timestamps, model labels, durations, and token counts; these are not live measurements. Missing or incomplete evidence stays visible instead of being turned into an estimate.” |
| 1:15–1:55 | **Dossier.** Show claim, research, hypotheses, runs, and oracle results. “The dossier starts with the claim, package version, and symbols shown in the sample. Its advisory reference is public, and report prose is not sent to the search provider. Each planned test names a deterministic oracle before execution. This fixture shows two hypotheses, one configuration, and zero triggers; it cannot tell us whether a real report reproduces. In a real run, Contradicted requires completed execution and stated coverage. Grounding alone can never reject a report. The reply is a draft, and the maintainer decides what happens next.” |
| 1:55–2:22 | **Architecture.** Show the architecture diagram. “The architecture uses Nebius Token Factory with NVIDIA Nemotron Nano, Super, and Ultra for language-model tasks, and Tavily for research using public identifiers. Nebius Sandboxes is the required boundary for untrusted proof-of-concept code. Deterministic logic packages the evidence dossier and reply for human review. The planned isolation has not been verified here.” |
| 2:22–2:40 | **Limits and close.** “The latest recorded Sandboxes access check returned HTTP 403. This walkthrough is replay-only: we do not claim an end-to-end reproduction or verified network isolation. Mimi reports evidence and its limits, and every report remains open for a maintainer to decide.” |

If Sandboxes access becomes available before recording, replace the replay-only
section with a fresh run on an already-public report, show its actual event
timeline and dossier, and update this script and all public claims from the
recorded evidence. Do not reuse fixture timestamps, IDs, outputs, or costs as
live evidence.

After the code, public copy, screenshots, and clean-browser check are settled,
record and export the final video as the last project deliverable. Upload that
cut to YouTube, add its link to Devpost, then complete the owner's rule and
eligibility confirmations and submit the entry.

## Artifact checklist

- [x] Public source repository and Apache-2.0 license file are present; GitHub showed the project description and Apache-2.0 license metadata on 2026-10-17.
- [x] Redacted Gitleaks scans of the tree and Git history returned zero findings on 2026-10-15; this predates the latest code changes, so rerun before final submission.
- [x] Local no-credential replay instructions are documented.
- [x] Static replay frontend build and replay image built on 2026-10-16; the merged frontend also passed live and read-only production builds in GitHub Actions on 2026-10-17.
- [x] Backend test suite passed: 183 tests on Python 3.12 and 3.13 in GitHub Actions on 2026-10-17 (one upstream Starlette/httpx deprecation warning).
- [x] Backend Docker image rebuilt from the reviewed source on 2026-10-17; no-credential health, inbox, sample dossier, events, completed SSE, live-ID access denial (401), and submission denial (402) smoke checks passed.
- [x] A replay container smoke check on 2026-10-16 confirmed the inbox, direct dossier route, health endpoint, and built JS/CSS assets return HTTP 200.
- [x] Architecture diagram exported as SVG and visibly labels the live Sandbox access limit.
- [x] 3:2 project thumbnail added at `docs/assets/mimi-project-thumbnail.jpg` (1536 × 1024, under 200 KB), within Devpost's 5 MB limit.
- [x] Devpost copy and an honest demo script are drafted above.
- [x] GitHub Actions CI passed on the merged `master` revision on 2026-10-17.
- [x] Workspace changes, including deletion of `CLAUDE.md`, were merged to the latest public `master` on 2026-10-17.
- [x] The read-only Pages workflow built and deployed the merged frontend successfully on 2026-10-17. The owner confirmed the public URL loads on 2026-10-16; check again in a private/clean browser before submission.
- [ ] Confirm access in a private/clean browser before final submission.
- [x] Confirmed the GitHub About description and Apache-2.0 license metadata are visible through repository metadata on 2026-10-17.
- [ ] Ask Nebius to confirm Sandboxes access for the project; current review environment binding readiness is unknown, and no new `whoami` probe was run.
- [ ] Verify Sandbox access and child user/network namespace isolation before live PoC execution.
- [ ] Run and report the planned E1/E2/E3/E4 results with sample sizes; keep
  blocked cases marked `not_run`.
- [ ] Capture real inbox and dossier screenshots from the running app.
- [x] Create a 2:40 draft demo with interactive replay footage, architecture, captions, and the Sandboxes HTTP 403 disclosure.
- [ ] After all other artifacts are final, replace the robotic narration with a natural voice, export the final video, upload it publicly to YouTube, and add the URL to Devpost.
- [ ] Re-read the Official Rules, confirm eligibility and agreement statements, then submit Devpost with the public replay URL, screenshots, and video.

The boxes above reflect deliverables only; completion of a checkbox does not
change the documented provider or security limitations.
