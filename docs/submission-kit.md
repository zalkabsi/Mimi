# Hackathon submission kit

Updated 2026-10-19 for the Nebius × NVIDIA Global AI Hackathon 2026. The live
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
a human. The public Pages demo is a clearly labelled replay. In a live 11-case pilot, four
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

The public Pages demo is a fixed, read-only replay. It makes no provider calls and does not
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
The public Pages demo is a fixed read-only replay and makes no Tavily calls. The
final E2 run received HTTP 432 usage-limit errors for all Tavily queries; its report
contains no advisory results or fixed versions. The current Sandboxes endpoint returned
all permissions in a read-only check. Live E1–E4
pipeline runs have since completed; results and limits are in `docs/evaluation-results.md`.

On October 19, the owner restored Tavily funding. The configured key then
returned a successful direct search, and Mimi's actual backend client completed
four public-identifier queries with three unique advisory records and no error
notes. The account reports a 625-credit pay-as-you-go limit. This recovery does
not change the historical E2 measurements.

Later on October 19, the combined frontend/API was deployed to
[Render Free](https://mimi-judge.onrender.com) with a shared judge credential.
After fixing two query-guard false positives, a hosted public minimist report
completed five Tavily queries (17 advisory records), eight Sandbox runs, and a
saved Needs human dossier and reply without stage errors. It triggered no
hypotheses in one configuration; this is an integration check, not a new
accuracy benchmark. The URL and key belong in Devpost's private testing field;
copy the [prepared judge instructions](judge-access.md#private-devpost-testing-instructions)
and obtain the key directly from Render.

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
unverified. The public Pages demo is a fixed replay and makes no Nebius API calls.

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
and the public Pages demo is a fixed replay that makes no model calls.

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

## Current demo and submission artifacts

The current local export is `docs/video/mimi-demo.mp4`: a 720p screen recording
with original synthetic narration and burned-in English captions, about 2:38.
It shows the working production replay, a hypothesis expansion, and the reply,
then the architecture diagram and the published pilot limits. The first shots
identify fixed sample data and no provider calls. No fixture timing or result
is presented as live evidence.

The authoritative narration and shot sources are
[`scenes.json`](video/scenes.json), [`voiceover-script.txt`](video/voiceover-script.txt),
and [`captions.srt`](video/captions.srt). See the [video guide](video/README.md)
for regeneration and publishing instructions. These replace the earlier 2:58
draft; use the exported video's audio and captions together.

| Approximate time | Shot |
| --- | --- |
| 0:00–0:21 | Inbox: maintainer problem and evidence-first triage. |
| 0:21–0:41 | Open the working replay and explain fixed sample data. |
| 0:41–1:05 | Timeline, Needs human, coverage, and negative-verdict thresholds. |
| 1:05–1:29 | Hypotheses, declared oracles, and expanded harness code. |
| 1:29–1:45 | Maintainer reply draft and missing measurements. |
| 1:45–2:11 | Architecture: Token Factory, Nemotron, Tavily, Sandboxes, trust limits. |
| 2:11–2:38 | Published pilot results, the quota limit at recording time, human decision. See the later Tavily recovery above. |

`make submission` builds a portable read-only replay and writes
`artifacts/submission/` with source and demo ZIPs, MP4, SRT, screenshots,
submission copy, readiness review, and SHA-256 hashes. The demo ZIP needs only
an HTTP static server; it makes no provider calls. It is a fixture replay.

The owner-approved submission video remains [Mimi](https://youtu.be/y4rlh4hlkcw),
as recorded in upstream `0dd530a`. This session did not independently recheck
YouTube playback. The new local export is an optional updated cut; upload and
verify a new public URL only if replacing the approved video.

## Current artifact checklist

- [x] Public repository URL and Apache-2.0 license are present.
- [x] Cross-platform no-credential replay launch and portable build are documented.
- [x] 201 backend tests pass on Python 3.12, including hosted access and the bundled-report research regression; ordinary test sockets are guarded and the isolated web smoke has no provider credentials.
- [x] Live and replay production builds pass; seven Chromium checks cover core UI behavior and reference URL handling.
- [x] Frontend npm audit and local Python dependency audit report zero known advisories.
- [x] API/replay images and the combined judge image build; access controls, sample SSE completion, replay navigation, same-origin routing, and the custom host port pass their smoke checks.
- [x] The updated public Pages replay opens, downloads its dossier, and refreshes in a fresh signed-out Chromium context using TLS-verified forwarding; direct browser proxy-CA trust was unavailable.
- [x] Three current screenshots, architecture diagram, and project thumbnail are present.
- [x] Narrated, captioned demo MP4 under three minutes is exported locally.
- [x] Devpost copy, product-feedback fields, evaluation summary, and demo script are prepared.
- [x] Bounded live Nemotron inference and Sandbox permissions checks pass.
- [x] E1–E4 pilot results and uncertainty are published without claiming broad accuracy or hostile-PoC containment.
- [x] Readiness PR #6 and hosting PR #7 are merged with passing required CI; the updated Pages deployment is verified.
- [x] The active master ruleset blocks force pushes/deletion and requires PRs and all three CI checks, with no bypass actors.
- [x] Preserve the owner-approved public YouTube submission link; an optional updated MP4 is prepared locally.
- [x] Tavily funding is restored: a direct search and the actual backend research client both succeed; the account reports a 625-credit paid-usage limit.
- [x] The combined app is deployed on Render Free at [mimi-judge.onrender.com](https://mimi-judge.onrender.com); hosted assets, sample dossier, events/SSE, authentication, and anonymous-access denials pass HTTP checks.
- [x] A complete hosted public-package report passes inference, advisory research, Sandbox execution, dossier/reply persistence, authenticated event history, and SSE completion without stage errors.
- [ ] Copy the generated judge key into Devpost's private testing instructions and maintain provider funding and credentials through December 15.
- [ ] Recheck the Official Rules, complete the remaining Devpost fields, and submit the entry.

See [the readiness review](readiness-review.md) for every fixed issue, validation
scope, current provider results, and the remaining owner/account steps. The
Pages release and the combined Render host are deployed, and the live pipeline
is verified. See [judge access](judge-access.md) for the evidence, private
credential handoff, and hosting limits.
