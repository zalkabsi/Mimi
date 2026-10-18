# Hackathon submission kit

Updated 2026-10-18 for the Nebius × NVIDIA Global AI Hackathon 2026. The live
[Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) were
last re-read on 2026-10-18. The deadline is October 30, 2026 at 10:00 AM
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

Mimi gives open-source maintainers an evidence dossier for npm vulnerability reports:
package grounding, public advisory context, bounded tests, deterministic oracle results,
and explicit coverage. It shows what the checks established and leaves the decision with
a human. The hosted demo is a clearly labelled replay. In a live 11-case pilot, four
oracles fired but none was confirmed against a fixed version. In E2, none of five
fabricated reports was contradicted; one falsely reached Likely after an oracle fired,
and the other four went to human review. These small results do not establish reliable
reproduction or hostile-PoC containment.

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

The hosted demo is a fixed, read-only replay. It makes no provider calls and does not
run a live vulnerability analysis. Separate E1–E4 live evaluations exercised the pipeline;
their small-sample results are published in `docs/evaluation-results.md`. E1 had zero
fixed-version-confirmed reproductions in 11 cases. E2 falsely contradicted 0/5 real
reports and contradicted 0/5 fabricated reports; one fabricated report reached Likely
after an oracle fired, and the other four went to human review.
A read-only Sandboxes permission check returned HTTP 200 with
all six permissions enabled. During the final E2 run, npm package grounding resolved
published tarballs, but Tavily returned HTTP 432 usage-limit errors for every advisory
query, leaving fixed-version research unavailable. A safe no-op run using node:20 and is-number@7.0.0 built
and executed; Mimi confirmed its child network namespace, and an outbound TCP connection
attempt returned ENETUNREACH. The pipeline runs show execution, not reliable reproduction
or useful slop discrimination. Provider-level containment of hostile code remains
unverified. For live analysis, report text is sent to
Nebius Token Factory; Tavily receives only public identifiers, not report prose or PoC
code.

#### How I built it

The backend uses Python, FastAPI, and SQLite; the frontend uses React, TypeScript, Vite,
and Tailwind CSS. Nebius Token Factory runs NVIDIA Nemotron Nano, Super, and Ultra for
language-model tasks, while Tavily searches public advisory sources. Deterministic
backend logic evaluates declared test oracles and reports coverage. Incomplete runs and
missing evidence stay inconclusive; grounding alone cannot produce a negative verdict.
The live execution path is designed to place untrusted PoC code in Nebius Sandboxes. The
safe no-op smoke verified SDK integration, persistent image staging, the child namespace
marker, and Mimi-level egress blocking for one harmless run. E1–E4 live pipeline runs
completed, but E1 had no fixed-version-confirmed reproduction in 11 cases and E2 did not
distinguish real from fabricated reports. These small evaluations do not validate reliable
triage or provider-level security against hostile code.

#### What I learned

Language models can help structure reports and suggest tests, but the verdict
needs explicit, deterministic evidence. I also learned that restricting
advisory searches to public identifiers helps avoid sending report prose to a
search provider. Integration smoke checks showed that each Nemotron model could
complete a sample function-tool call and that Tavily could return advisory
results. A five-case routing comparison matched expected tiers in 5/5 cases for
routed, Ultra, and Super, but is too small to establish a general quality or cost
advantage. E1 and E2 results and their limits are in `docs/evaluation-results.md`.

#### Challenges

The design challenge was making a negative result useful without treating missing
evidence as proof. Mimi requires declared oracles and records coverage; build failures
and incomplete runs cannot become clean negative results. A second challenge was getting
the Sandboxes integration right. The outdated endpoint was corrected, then a safe no-op
run exposed an incorrect SDK client, disposable runs that would discard staged files,
result-type mismatches, and a probe stdin path unsupported in the sandbox. I fixed these
issues and reran the harmless operation. Mimi's namespace probe observed an outbound TCP
attempt blocked with ENETUNREACH. This validates basic integration and the app-level
guard, not a real vulnerability reproduction or provider-level containment of hostile
code. The hosted replay remains clearly labelled fixture data.

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

The repository includes a no-credential, read-only replay demo using an explicitly
labelled fixture. Live E1–E4 evaluations used public npm vulnerability cases and scripted
safety inputs; sample sizes, confidence intervals, and limits are in
`docs/evaluation-results.md`. E1 produced 0/11 fixed-version-confirmed reproductions.
E2 produced no useful real-versus-fabricated separation. A harmless no-op operation also
built and ran successfully; Mimi's child namespace probe observed an outbound TCP attempt
blocked with ENETUNREACH. These results do not establish reliable reproduction or
provider-level isolation against hostile code. In the final E2 run, Tavily rejected every
advisory query with a plan usage-limit error, so the run had no advisory results or
fixed-version research.

### How we built it

The backend is Python, FastAPI, and SQLite. The UI is React, TypeScript, Vite,
and Tailwind. Nebius Token Factory is used for NVIDIA Nemotron 3 Nano, Super,
and Ultra inference; Nebius Token Factory Sandboxes are the intended execution
boundary for reporter-supplied PoCs; Tavily is used for public advisory
research. A deterministic tier layer keeps grounding evidence from becoming
a verdict by itself and treats incomplete runs as inconclusive.

### Challenges

The core challenge is making a negative result interpretable without treating missing
evidence as proof. Mimi requires a declared oracle, records coverage, and will not turn
build errors or incomplete runs into a clean negative. The other major challenge is
safely executing untrusted proof-of-concept code. The October 15 Nebius Sandboxes check
targeted the old API host and returned HTTP 403. After correcting the endpoint, a
harmless no-op Sandbox run exposed and helped fix incompatibilities in the declared SDK
integration and image persistence. The corrected operation built and executed, while
Mimi's namespace probe observed blocked outbound TCP. These checks validate the basic
path only; the repo does not claim reliable vulnerability reproduction or hostile-code
isolation at the provider boundary.

### What we learned

Single-prompt smoke calls showed that Nano, Super, and Ultra each completed a
function-tool call through Token Factory. An earlier Tavily smoke returned advisory
results from public identifiers; the final E2 run reached the plan usage limit and got
no advisory results. The five-case routing comparison matched expected tiers for all three
settings, but is too small to show a general routing benefit. E1 recorded zero
fixed-version-confirmed reproductions in 11 cases, while E2 did not distinguish real
reports. The harmless Sandbox run observed outbound TCP blocked with ENETUNREACH. These
results do not validate reliable vulnerability triage or provider-level security.

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
The hosted demo is a fixed read-only replay and makes no Tavily calls. The
final E2 run received HTTP 432 usage-limit errors for all Tavily queries; its report
contains no advisory results or fixed versions. The current Sandboxes endpoint returned
all permissions in a read-only check. Live E1–E4
pipeline runs have since completed; results and limits are in `docs/evaluation-results.md`.

### Nebius platform capabilities used

The most valuable capability was managed inference through Nebius Token
Factory. The backend calls its OpenAI-compatible Chat Completions API with a
project API key, without deploying model weights or managing GPU instances.
This let Mimi route work among Nemotron Nano, Super, and Ultra through one
service and use structured responses, function calling, and reasoning controls.
The models completed individual integration smoke checks, and the live E1–E4
pipeline evaluations are summarized in `docs/evaluation-results.md`. I did not
configure a GPU instance type, deploy a custom endpoint, or load-test scaling.

Nebius Sandboxes is the intended isolation boundary for untrusted proof-of-concept
execution. A safe no-op operation using node:20 and is-number@7.0.0 built and ran
successfully; Mimi's child namespace probe observed outbound TCP blocked with
ENETUNREACH. This confirms the basic SDK integration and app-level network guard. E1–E4
live pipeline runs completed, but their small samples do not establish reliable
vulnerability triage, and provider-level containment of hostile code remains
unverified. The hosted demo is a fixed replay and makes no Nebius API calls.

### Recommendation rating

**8/10.** I would recommend Nemotron on Token Factory for teams that want a quick API
integration and multiple model sizes for task-based routing. The OpenAI-compatible
endpoint made initial calls straightforward, and all three tested model variants
supported the same function-call smoke test. Developers should use exact model IDs and
budget enough output tokens: Nano can spend a tiny budget on reasoning and return empty
content. Token-usage details vary by model, and our latency and quality checks were too
limited to establish production performance. This rating concerns Token Factory
inference. The small E1–E4 runs did not establish reliable triage, and provider-level
hostile-code containment remains unverified.

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
missing grant from other access failures. The October 15 check used the old
API host and returned 403 without a permission payload; the current Token
Factory endpoint now returns all permissions. A harmless no-op run now verifies basic
execution and app-level egress blocking; an actual vulnerability run and provider-level
isolation review are still needed.

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

Each model completed an individual integration smoke call. A five-case live routing run
matched expected tiers for routed, Ultra, and Super; broader model-routing performance has
not been established. Sandboxes access and a harmless no-op build/run were confirmed;
Mimi's child namespace probe observed blocked outbound TCP. E1/E2 results remain weak,
and the hosted demo is a fixed replay that makes no model calls.

### Nemotron output quality rating

**7/10 (provisional; based on integration smoke checks, not a full evaluation).**
Nano, Super, and Ultra all produced the requested function call in a constrained
advisory-lookup prompt, and reasoning controls worked. One limitation: with a
very small output-token budget, Nano spent the budget on reasoning and returned
empty answer content, so calls need an adequate output budget. Schema-validated
JSON calls retry once on invalid output, expanding the output budget when the
provider reports truncation, then fail rather than inventing a result. Accuracy
on full vulnerability reports, hypothesis quality, general end-to-end reasoning,
and multilingual performance remain uncertain after the small pilot.

### Fine-tuning and prompting

I used the pretrained Nemotron models through Nebius Token Factory without fine-tuning.
I prompt-engineered separate calls for each pipeline stage and constrained outputs with
JSON schemas and tool definitions. Prompts treat report text as untrusted data and tell
the model not to follow instructions inside it. For hypothesis generation, the model
must provide a bounded test plan and a deterministic oracle; backend allowlists validate
proposed operations, and deterministic code evaluates outcomes and coverage. The model
does not issue arbitrary tools or decide the final verdict. I also tuned reasoning and
output-token settings; a tiny token budget can leave Nano with empty answer content.
Schema-validated JSON calls retry once on invalid output and expand the output budget
when a response was truncated. The live pipeline has been evaluated on small public npm
samples; those results do not establish general prompt quality or reliable reproduction.

### Comparison with other models

I did not run a controlled, same-prompt comparison between Nemotron and other
model families on Mimi's vulnerability-triage tasks, so I cannot claim better accuracy,
latency, or cost against them. In integration smoke checks, Nano, Super, and Ultra all
completed the requested advisory-lookup function call. A five-case within-Nemotron
routing check matched expected tiers for each setting, but is too small to rank general
model quality. A tiny output budget caused Nano to return empty answer content with
reasoning enabled.
Codex and Claude Code were used as development assistants, not as runtime
baselines for this workload. A fair comparison still needs a labelled report
set, repeated runs, and live execution access.

Suggested Devpost tags (19 of 25): Nebius Token Factory, Nebius Token
Factory Sandboxes, NVIDIA Nemotron, Tavily, Python, FastAPI, SQLite, React,
TypeScript, Vite, Tailwind CSS, Docker, GitHub Actions, GitHub Pages, npm,
Generative AI, Cybersecurity, Open Source, Vulnerability Management.

## Three-minute demo script

Target length: 2:58 with a hard limit of 3:00. Show only a real app screen and
the actual fixture labels. Do not present fixture timing, cost, or execution
outputs as measured results.

| Time | Shot and narration |
|---|---|
| 0:00–0:18 | **Inbox.** “This is Mimi, a vulnerability report triage workbench for open-source maintainers. Its goal is not an automatic rejection. It assembles a reviewable evidence dossier, while the maintainer makes the final decision. Mimi never auto-closes a report.” |
| 0:18–0:38 | **Open the sample row.** Point out the visible replay label. “This labelled sample is recorded replay data. It lets anyone inspect the interface without credentials, but it is not a live analysis. The public page makes no provider calls. Every timestamp and finding belongs to the fixture.” |
| 0:38–1:15 | **Timeline.** Scroll through extract, grounding, research, hypotheses, build, forks, differential, verdict, and reply. “Here is the recorded pipeline: claim extraction, package grounding, public advisory research, bounded test hypotheses, environment builds, isolated forks, a fixed-version comparison, a verdict, and a reply draft. Everything shown here is fixture data, including timestamps, model labels, durations, and token counts; these are not live measurements. Missing or incomplete evidence stays visible instead of being turned into an estimate.” |
| 1:15–1:55 | **Dossier.** Show claim, research, hypotheses, runs, and oracle results. “The dossier starts with the claim, package version, and symbols shown in the sample. Its advisory reference is public, and report prose is not sent to the search provider. Each planned test names a deterministic oracle before execution. This fixture shows two hypotheses, one configuration, and zero triggers; it cannot tell us whether a real report reproduces. In a real run, Contradicted requires at least three conclusive hypotheses across two distinct configurations. Grounding alone can never reject a report. The reply is a draft, and the maintainer decides what happens next.” |
| 1:55–2:22 | **Architecture.** Show the architecture diagram. “The architecture uses Nebius Token Factory with NVIDIA Nemotron Nano, Super, and Ultra for language-model tasks, and Tavily for research using public identifiers. Nebius Sandboxes is the required boundary for untrusted proof-of-concept code. Deterministic logic packages the evidence dossier and reply for human review. A safe no-op smoke confirmed Mimi's child namespace and observed outbound TCP blocked with ENETUNREACH; provider-level isolation against hostile code remains unverified.” |
| 2:22–2:58 | **Limits and close.** “This is a read-only replay, not a live vulnerability analysis. In an 11-case live pilot, four oracles fired but none was confirmed against a fixed version. In five fabricated reports, none was contradicted. One falsely reached Likely after an oracle fired; the other four went to human review. Tavily's plan limit blocked advisory lookups, so this sample does not establish useful slop discrimination. The replay is fixture data, and provider-level isolation remains unverified. The maintainer decides what happens next; Mimi never auto-closes a report.” |

The harmless no-op Sandbox smoke is complete. Keep the walkthrough focused on the
functioning replay UI and disclose that it is fixture data; do not present the separate
smoke as a vulnerability analysis. Do not reuse fixture timestamps, IDs, outputs, or
costs as live evidence.

After the code, public copy, screenshots, and clean-browser check are settled,
verify the public video supplied by the owner, [Mimi](https://youtu.be/y4rlh4hlkcw),
against the current replay and this script. No video or audio media file is
recorded in this workspace, and this session could not retrieve the video's
duration or transcript. If the existing video is stale, record and export a
replacement under three minutes, review playback, and publish it publicly. Add
the verified current URL to the Devpost draft before submitting the entry.

## Artifact checklist

- [x] Public source repository and Apache-2.0 license file are present; GitHub showed the project description and Apache-2.0 license metadata on 2026-10-17.
- [x] Redacted Gitleaks scans of the current tree and Git history returned zero findings on 2026-10-18.
- [x] Local no-credential replay instructions are documented.
- [x] Current frontend production build passed locally on 2026-10-18; the replay image and prior GitHub Actions production builds passed on 2026-10-16/17.
- [x] Backend test suite passed locally on Python 3.12 after the final code changes (193 tests; one upstream Starlette/httpx deprecation warning). GitHub Actions CI passed on the latest public commit `878709a` for Python 3.12/3.13 and frontend live/replay builds.
- [x] Backend Docker image rebuilt from the current patch on 2026-10-18; no-credential health, inbox, and sample-dossier checks passed. The previous image also passed events, completed SSE, live-ID access denial (401), and submission denial (402) checks on 2026-10-17.
- [x] A replay container smoke check on 2026-10-16 confirmed the inbox, direct dossier route, health endpoint, and built JS/CSS assets return HTTP 200.
- [x] Architecture diagram exported as SVG and updated to distinguish the successful no-op smoke from unverified hostile-PoC containment.
- [x] 3:2 project thumbnail added at `docs/assets/mimi-project-thumbnail.jpg` (1536 × 1024, under 200 KB), within Devpost's 5 MB limit.
- [x] Devpost copy and an honest demo script are drafted above.
- [x] GitHub Actions CI passed on public `master` at `878709a` on 2026-10-18.
- [x] The previous source snapshot, including deletion of `CLAUDE.md`, was merged to public `master` on 2026-10-17.
- [x] The read-only Pages workflow built and deployed the app code from `a476de1` on 2026-10-18. Its public URL returns HTTP 200, and a clean local build with the workflow's exact environment produces a byte-identical JavaScript bundle to the one served publicly; the docs-only `878709a` commit does not change the app. The interactive clean-browser check is still pending.
- [ ] Confirm access in a private/clean browser before final submission; browser-control was unavailable in this cloud session.
- [x] Confirmed the GitHub About description and Apache-2.0 license metadata are visible through repository metadata on 2026-10-17.
- [x] Update the Sandboxes base URL to the current Token Factory endpoint and confirm `whoami` returns HTTP 200 with all six permissions.
- [x] Run a safe no-op Sandbox operation and verify Mimi's child network namespace plus app-level egress block; hostile-PoC and provider-level isolation remain unverified.
- [x] Run and report E1/E2/E3/E4 with sample sizes and uncertainty; see `docs/evaluation-results.md`. E1 is 0/11 confirmed with a fixed-version differential; E2 did not distinguish real from fabricated reports, including one fabricated report that reached Likely after an oracle fired; Tavily returned no advisory results due to its usage limit; one E4 path-read check is `not_run`.
- [ ] Refresh the inbox and dossier screenshots from the corrected fixture before approving the video. The two pre-threshold captures were removed; `docs/assets/demo-evidence.png` remains current because its displayed research and hypotheses were unchanged.
- [x] Draft a 2:58 demo script and captions with fixture disclosures and pilot results. Only the research/hypothesis capture remains; the inbox and dossier captures were removed after the fixture verdict correction. No video export exists in this workspace.
- [ ] Verify [the owner's existing public video](https://youtu.be/y4rlh4hlkcw) against the current script/replay, including visibility, duration, audio, captions, and playback; replace it if stale.
- [ ] Add the verified current video URL and evaluation summary to the Devpost draft. The owner will submit the entry.
- [ ] Re-check clean-browser replay access and resolve the absence of a hosted live-analysis backend or judge credential against the Rules' unrestricted-access requirement.
- [x] Re-read the Official Rules on 2026-10-18; the owner's eligibility and agreement attestations are recorded complete.

The boxes above reflect deliverables only; completion of a checkbox does not
change the documented provider or security limitations.
