# Research, candidates and decision (Phases 1-4)

Date of research: 2026-09-29. Deadline: 2026-10-30 10:00 AM PT (about 4 weeks).

## How to read this

- **Provenance.** Every web fact below came from a search-tool summary. I could not open primary pages (egress blocked) except the `contree-sdk` / `contree-mcp` wheels from PyPI, which I read directly. Treat numbers as "reported by", and re-check the ones we quote publicly.
- **Scores are judgments, not measurements.** The matrix uses check / partial / cross, with the deciding evidence beside it.
- **No metric for our own system exists yet.** Nothing here claims a result for the product we have not built.

## Evidence log

| # | Fact | Source (via search summary) |
|---|---|---|
| E1 | curl ended its bug bounty on 2026-01-31 after AI-generated reports; confirmed-vulnerability rate fell to about 5% (1 in 20-30 by late 2025); reports now go through GitHub Security Advisories, no rewards | [Stenberg blog](https://daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty/), [The Register](https://www.theregister.com/security/2026/01/21/curl-shutters-bug-bounty-program-to-stop-ai-slop/5063039), [BleepingComputer](https://www.bleepingcomputer.com/news/security/curl-ending-bug-bounty-program-after-flood-of-ai-slop-reports/) |
| E2 | curl's 7-person security team spends 30 min to 3 h per report, 3-4 people each; HackerOne reports 60-80% of submissions invalid; Node.js received 30+ slop reports over a holiday; Stenberg's April 2026 peer survey confirmed the pattern at Apache httpd, BIND, Django, Elasticsearch, Firefox, git, glibc, Linux kernel, Python, Ruby, urllib3, Wireshark, wolfSSL and others | [secondary summaries](https://danielusurelu.medium.com/ai-cve-slop-the-crisis-drowning-open-source-security), [Seth Larson](https://sethmlarson.dev/slop-security-reports) |
| E3 | GitHub private vulnerability reports rose from a few hundred a week in January 2026 to more than 3,000 a week through most of May; some are AI-generated with no human review, others "describe real behavior but mischaracterize it as a vulnerability"; validating one poor report can take hours; GitHub Security Lab has a Taskflow triage agent (GitHub Actions and JS projects) | [Help Net Security](https://www.helpnetsecurity.com/2026/06/30/github-advisory-database-review/), [GitHub blog](https://github.blog/security/ai-supported-vulnerability-triage-with-the-github-security-lab-taskflow-agent/) |
| E4 | Elastic runs an internal AI triage pipeline for HackerOne reports: 85% agreement with human analysts, analysis about $0.50-1.15 per report, reproduction about $0.80-4.90 extra, roughly 70% of reports rejected at analysis and never reproduced; reproduction runs on ephemeral VMs (chosen over containers because "containers share a kernel"); human approval for all external actions. Built on Claude; internal, not an open tool | [Elastic Security Labs](https://www.elastic.co/security-labs/ai-vulnerability-triage-bug-bounty-hackerone) |
| E5 | **SlopCheck** (open source) grounds a report's stated facts against the source tree. On 557 labelled, publicly disclosed curl reports it **contradicts 29.4% of confirmed vulnerabilities**, and only **10% of its contradictions are correct**; its author says it does not work as a gate | [SlopCheck](https://github.com/GaganGanesh98/SlopCheck) |
| E6 | CVE-Genie (academic, CCS 2026): reproduces 51% (428/841) of 2024-25 CVEs, mean $2.77 and median 18 min per CVE; web-centric ecosystems (TS/JS/PHP/Ruby) and input-validation classes reproduce more often than C/C++/Go and access-control bugs. Assumes the CVE is real (no slop handling) | [arXiv 2509.01835](https://arxiv.org/abs/2509.01835) |
| E7 | CyberGym (1,507 vulns, 188 projects): original best about 17.9-22%; later leaderboard entries claim above 90% (vendor claims). C/C++ fuzz-crash oriented | [arXiv 2506.02548](https://arxiv.org/abs/2506.02548) |
| E8 | SecBench.js: 600 npm vulnerabilities across 5 classes, each with CVE id, package/version, executable exploit and a success oracle | [SecBench.js](https://github.com/saleha-muzammil/SecBench.js) |
| E9 | Only about 1 in 10 AI-generated PRs meets the bar; GitHub is weighing PR kill switches; Jazzband shut down citing AI spam | [The New Stack](https://thenewstack.io/ai-generated-code-crisis/), [InfoWorld](https://www.infoworld.com/article/4127156/github-eyes-restrictions-on-pull-requests-to-rein-in-ai-based-code-deluge-on-maintainers.html) |
| E10 | Token Factory **Sandboxes** (ConTree): microVM per run with its own kernel, git-like branching (fork from a checkpoint, parallel runs, rollback), 50 simultaneous operations, no inbound network, 180-day image retention, ~2-5 s microVM start | [docs overview](https://docs.tokenfactory.nebius.com/sandboxes/overview), [SDK](https://github.com/nebius/contree-sdk) |
| E11 | `contree-sdk 0.3.6` source (read directly): run request fields are `command, image, hostname, args, shell, env, cwd, disposable, stdin, timeout, truncate_output_at, files, preserve_env`. **No network-isolation option.** `disposable=false` returns a result image UUID (a snapshot); runs from the same image UUID are independent forks. Per-run `resources.cost` and `elapsed_time` are returned | PyPI wheel `contree_sdk-0.3.6` |
| E12 | Nemotron 3: Nano 30B, Super 120B (12B active), Ultra 550B (55B active, released 2026-06-04, up to 1M context, hybrid Mamba-Transformer MoE). Reasoning on/off/low-effort with optional budget; tool calling supported. Reported Token Factory prices per 1M tokens (input/output): Ultra $1.00/$3.00, Super $0.30/$0.90, Nano $0.06/$0.24 | [NVIDIA blog](https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/), [Token Factory endpoints page](https://tokenfactory.nebius.com/endpoints) |
| E13 | Official Rules §8: "Best Use of Tavily" ($3,000) is open to eligible submissions "that make a functional, runtime call to the Tavily API as part of its solution". Tavily engineers are on the judging panel. Only one Bonus award per project | Official Rules (pasted by owner, 2026-09-30) |
| E14 | ClawHavoc: 1,184 malicious OpenClaw skills reported; 135,000+ exposed instances. Scanners already exist: Cisco Skill Scanner, Snyk Agent Scan, VirusTotal Code Insight, Permiso SandyClaw (dynamic sandbox detonation), NVIDIA Skill-Spector, SkillSentry | [SC World](https://www.scworld.com/news/openclaw-agents-targeted-with-341-malicious-clawhub-skills), [Snyk](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) |
| E15 | Agent observability and failure attribution is crowded: LangSmith, Braintrust, Langfuse, Arize, Galileo, Docent, Microsoft AgentRx, and AgentDebugX (literally Detect, Attribute, Recover, Rerun) | [AgentRx](https://www.microsoft.com/en-us/research/blog/systematic-debugging-for-ai-agents-introducing-the-agentrx-framework/), [AgentDebugX](https://arxiv.org/html/2607.18754) |
| E16 | Health-insurance denials: 64-80% overturned when challenged, under 1% appealed (one study: 11.5% of Medicare Advantage denials appealed, 80.7% overturned). Already served by Counterforce Health, Claimable, and open-source FightHealthInsurance | [Healthcare Dive](https://www.healthcaredive.com/news/insurance-denials-overturned-appeal-new-york-study-JAMA/817490/), [Counterforce](https://www.counterforcehealth.org/) |
| E17 | Environment setup for repos is hard: EnvBench SOTA 6.69% (Python) and 29.47% (JVM); Repo2Run reports 86% on 420 Python repos (avg 29 min); SetupBench 34-62% | [EnvBench](https://arxiv.org/pdf/2503.14443), [Repo2Run](https://arxiv.org/html/2502.13681v2) |
| E18 | Flaky tests: Meta FlakyFix, FlakyGuard, FlakyDoctor (58% repaired) exist; commercial detection is mature; Atlassian figure of 150,000 dev hours a year is from a secondary blog | [FlakyGuard](https://arxiv.org/abs/2511.14002) |
| E19 | HS tariff classification: best benchmark baseline 46.8% at 10 digits; crowded commercial field (GingerControl, Tarifflo, Gaia Dynamics backed by AI Fund) | [gingercontrol](https://gingercontrol.com/blog/hts-classification-accuracy) |
| E20 | Scouting inside this hackathon (public GitHub only, Devpost gallery unreadable): **at least six** Track 1 repos use Sandboxes branching for CI repair / patch tournaments (SandForge, Arborist, RepoMedic, PQC Factory, SandCoder, PatchScout). Security-adjacent: The Courtroom (audits your own Python file, exploit + patch in sandbox), CVE Triage Agent (retrieval + search, no sandbox), NullPoint Agent (CVE exploitability vs network telemetry), ProofPatch (issue-posted design spec, states it is not deployed; issue + repo to failing test to patch to evidence bundle) | GitHub search results, then page reads of ProofPatch, CVE Triage Agent, The Courtroom |

## Killed early (with the reason)

| Idea | Killed because |
|---|---|
| CI repair / patch tournament / tree search over fixes | E20: at least six public entries already, same architecture |
| Flaky-test root-cause with statistical proof | E18 prior art plus E20 adjacent crowding; weak differentiation |
| Blackbox (agent failure debugger; my first suggestion) | E15: the whole loop already exists as open toolkits and funded products. Also unsound: replaying recorded tool outputs against a *patched* agent diverges, so the "verified replay" claim does not hold |
| Skill / agent-policy security scanner (Personal AI) | E14: static, LLM and dynamic-sandbox scanners all exist, including one from NVIDIA; also depends on alpha OpenShell APIs |
| Insurance-denial appeal agent | E16: three live products including an open-source one; regulated health data; no way to evaluate honestly with real data |
| HS tariff classification | E19: crowded; accuracy gap versus experts is large and hard to close in 4 weeks |
| Physical AI | Needs hardware and a physical-operation demo minute. Not evaluated; only worth it if the team already has a robot or rig |

## Candidate matrix (finalists and near-misses)

Legend: yes / partial / no.

| Concept | Real problem (evidence) | Differentiated | Demo in 3 min | Feasible in 4 wks | Uncrowded here | Track |
|---|---|---|---|---|---|---|
| **A. Mimi**: execution-based verification of vulnerability reports for maintainers | **yes** (E1-E3, E9) | **partial** (E4 closed, E5 static, E6 assumes true) | **yes** | **partial** | **yes** (E20: nothing doing this) | 2 (or 1) |
| B. Envsmith: branching sandbox env bootstrapper, measured on EnvBench-style repos | yes (E17) | partial (research prior art; product gap) | partial (installs are not dramatic) | partial | partial | 1 |
| C. Flakeproof | yes | no (E18) | yes | partial | no | 1 |
| D. CI repair | yes | no | yes | yes | **no** (E20) | 1 |
| E. Skill guard | yes (E14) | no | yes | no | partial | 3 |
| F. Blackbox | yes | **no** (E15) | partial | yes | no | 1 |
| G. Appeals agent | yes (E16) | no | yes | yes | no | 2 |
| H. Tariff classifier | yes | no (E19) | yes | partial | partial | 2 |

### Finalist A: Mimi (full profile)

- **Problem.** Maintainers get vulnerability reports they cannot cheaply verify. Valid rate about 5% at curl; GitHub's private reports up more than 10x in five months; each bad report costs 30 minutes to hours of several people (E1-E3). Volunteer projects cannot buy closed triage SaaS.
- **Target user.** Open-source maintainers and small security teams who receive reports by GitHub advisory, email or a bounty platform. Secondary: bounty-program triagers.
- **Existing alternatives.** Elastic internal pipeline (closed, Claude, own product only, E4). HackerOne Hai Triage / Bugcrowd AI Triage (platform SaaS). GitHub Taskflow agent (GitHub-run, limited scope, E3). SlopCheck (static grounding; **wrong on 29.4% of confirmed vulns**, E5). CVE-Genie (research; assumes the CVE is true, E6).
- **Gap.** No open, self-hostable tool that (1) *executes* the claim against the exact affected version, (2) is safe to run reporter-supplied PoC code, and (3) treats "could not reproduce" as a **quantified negative result** instead of a verdict. E5 shows why (3) matters: a wrong "this is slop" verdict on a real bug is the costly error.
- **Product.** A maintainer inbox. Paste or forward a report; Mimi returns an **evidence dossier** and a triage tier, never an auto-close. Tiers: Confirmed (PoC works on affected version and stops working on the fixed version), Likely, Needs human (could not build or inconclusive), Contradicted (executed evidence against the claim, with stated hypothesis coverage). It also drafts the reply (ask for the missing info, or acknowledge with the repro).
- **Non-obvious idea.** *Negative-result coverage.* The system enumerates the ways the claim could be true (versions, configs, inputs, code paths), builds one image per image-affecting configuration, forks that image for each matching hypothesis, and reports "0 of N hypotheses triggered the claimed behavior, covering these configurations" instead of "not reproduced." Sandboxes branching supports those repeated runs (E10, E11).
- **AI architecture.** Routed Nemotron pipeline: Nano for claim extraction and log summarisation, Super for research synthesis / oracle interpretation / reply drafting, Ultra (reasoning on) for hypothesis generation and adjudicating ambiguous evidence. Model output is schema-guided; the backend invokes Tavily and Sandboxes through controlled code paths. Deterministic oracles (exit code, signal, marker file, output regex) decide wherever possible; the LLM does not grade its own reproduction if a deterministic check exists.
- **NVIDIA role.** Nemotron 3 is the reasoning and tool-using core, with the Nano/Super/Ultra split as a real cost/latency lever (E12). The eval includes an all-Ultra versus routed ablation, so any claim is measured.
- **Nebius role.** Token Factory: inference for all stages. Sandboxes: untrusted-code isolation (own kernel per run, the same reason Elastic chose VMs, E4) and branching (build once, fork per hypothesis). Not used: Serverless Endpoints/Jobs and AI Cloud VMs; they would be decoration here. Documented option: run inference in the maintainer's own Nebius tenancy for private reports.
- **Tavily.** Load-bearing: finds existing advisories / duplicates, and the upstream fix commit or fixed version, which supplies the fixed-version half of the differential test. Queries are built only from public identifiers (package, version, CVE/GHSA ids); report prose and PoC code are excluded from Tavily queries. Report text is sent to Nebius Token Factory for inference, and generated PoC code is sent to Nebius Sandboxes when execution is enabled.
- **MVP.** npm, then PyPI. One command: report text + `package@version` in, dossier out.
- **Demo.** Inbox of 5 reports (mix of real, already-public vulnerabilities and fabricated ones). "Verify all": live per-report timeline (extract, research, hypothesise, fork and run in parallel, differential, verdict), each dossier openable with the exact commands and outputs. Ends on measured numbers: time and cost per report from actual runs, and the routed-versus-all-Ultra comparison.
- **Difficulty.** Medium-high. Environment building varies by repo; oracle design per vulnerability class; safe execution.
- **Risks.**
  1. Builds fail on many repos (E6: variance by ecosystem). Mitigation: npm/PyPI first, "Needs human" is a legitimate tier, and we report the coverage honestly.
  2. **No per-run network isolation in the SDK (E11).** Mitigation: require `unshare --user --map-root-user --net` inside the microVM for the PoC phase; no secrets in the sandbox; public-only demo data; and if the namespace cannot be created, refuse the run and say so in the README.
  3. **Eval data.** Real slop for npm/PyPI does not exist as a labelled set. Real curl reports (E5) are C and out of MVP scope. Plan uses SecBench.js for real vulnerabilities and *synthetic* fabricated reports for slop, labelled synthetic everywhere. Public vulnerabilities may be memorised by Nemotron, so add a small post-cutoff set from recent advisories.
  4. Moderate novelty. The pattern is validated (E4), so judges may see it as an application, not an invention. The differentiators must be shown, not asserted: negative-result coverage, open/self-hostable, measured false-reject rate.
  5. GitHub may ship a native version. Answer: forge-agnostic, self-hostable, judged today on what works today.
  6. Ethics. Executing PoCs for vulnerabilities is defensive only here. Demo and eval use already-public vulnerabilities; no offensive tooling; no real private reports.

### Runner-up: Envsmith (kept as fallback)

Given a repo URL, an agent brings up a working, tested environment in a branching sandbox (fork on each failed install, roll back, try the next hypothesis) and emits a reusable, verified recipe. Measured against a baseline linear agent on an EnvBench-style repo set (E17). Stronger as a research claim, weaker as a product and a demo. Risk: the measured improvement over a linear agent may simply not appear.

## Decision

**Build Mimi. Recommended track: Track 2 (Best Apps and Agents).**

Why A over B: it has a verified, recent, accelerating problem (E1-E3), a named user, a demo with a clear "this used to take hours" moment, an evaluation with public ground truth (E8) and a measurable safety property (false-reject rate on real vulnerabilities), and a technical idea (negative-result coverage via forked sandboxes) that maps directly onto what Sandboxes do differently from a plain container.

Why Track 2 rather than Track 1: the user of Mimi is a maintainer running an inbox, not a developer driving a coding agent; the Track 2 brief explicitly rewards Nemotron model routing and we have real cost data to show for it; Track 1 holds at least six near-identical sandbox repair entries (E20). The trade-off is a wider Track 2 field. The track is chosen at submission, so this can be revisited.

### Pivot triggers (decide by end of week 1, Oct 5)

Switch to Envsmith, or narrow Mimi, if any of these hold after the day-1 spikes and a 10-case pilot:

- Fewer than 5 of 10 real public npm vulnerabilities reach a confirmed reproduction with an oracle, using Ultra with unrestricted retries.
- Per-hypothesis fork runs cannot be made offline *and* we judge the residual risk unacceptable for the hosted demo (then the hosted demo becomes replay-only and the live path is documented for self-hosting).
- Sandboxes cannot fork from a saved image at the concurrency we need (50 operations) without failures.

### Update 2026-10-17: pivot review (was due Oct 5)

The pivot triggers that depend on the 10-case pilot and concurrency still cannot be evaluated. Since the October 17 access check, a harmless node:20 / is-number@7.0.0 Sandbox smoke has built and executed successfully. Mimi confirmed its child network namespace, and a TCP connection attempt was blocked with ENETUNREACH. This is basic integration evidence, not a vulnerability reproduction or proof of provider-level isolation against hostile code. Status of each trigger:

1. **Fewer than 5 of 10 real npm vulns confirmed** — *undetermined*. No real vulnerability reproduction runs have been completed.
2. **Fork runs cannot be made offline / residual risk unacceptable** — *partially checked*. Mimi's child network namespace blocked an outbound connection attempt during a harmless smoke. Hostile-code behavior and provider-level containment remain unverified.
3. **Sandboxes cannot fork at the needed concurrency** — *undetermined*. No concurrency evaluation has run.

**Decision: continue with Mimi.** No pivot trigger is confirmed. Run a reviewed, public-case pilot and security assessment before claiming end-to-end triage or exposing live report submissions.

### Update 2026-09-30: owner confirmations and what the Rules changed

- **Confirmed by owner:** build this project; team is solo; license Apache-2.0; project name is **Mimi** (same as the repo).
- **Track 2 fits the official text well.** The Rules describe Track 2 as Nemotron via Token Factory, "Ultra when you need serious reasoning, and let Nano or Super handle the fast, everyday calls". Mimi's stage routing is that. The organisers also say a "multi-step autonomous workflow that chains tools end to end stands out more", which is what the pipeline is.
- **Tie-break order favours engineering and design** (Technological Implementation, then Design, then Impact, then Idea). Given the moderate novelty noted above, the plan leans on rigor and a finished product rather than on a novelty claim.
- **Judge access until Dec 15 "free and without any restriction"** forces a judge credential, a costless demo mode, and predictable hosting. See `00-constraints-and-open-items.md`.
- **One bonus award only.** Target Best Use of Tavily. Feedback is still mandatory.
- **Solo scope cuts:** npm only, one UI flow, evaluation sized to about $50 of credits. See `02-architecture.md`.

### What would change my mind about the decision itself

- Devpost's Rules or gallery (currently unreadable) show a direct competitor with a working product.
- A judging-criteria detail that penalises applications built around a sponsor's proprietary service (unlikely: Nebius and NVIDIA are the sponsors).
