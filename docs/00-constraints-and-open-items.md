# Hard constraints and open items

Updated 2026-10-18. Team: **solo**. Project name: **Mimi**.

## Latest Sandboxes access and smoke check (2026-10-18)

The October 15 probe targeted the old `https://api.sandbox.nebius.ai/v1` endpoint and
returned HTTP 403 without a permissions payload. Nebius's [ConTree migration
guide](https://contree.dev/blog/contree-joins-token-factory/) says the service moved into
Token Factory in May 2026, with the API root
`https://api.tokenfactory.nebius.com/sandboxes`. A read-only `GET /v1/whoami` on October 17
returned HTTP 200 and all six permissions were true (`import`, `spawn`, `spawn_disposable`,
`list`, `cancel`, `set_image_tag`). The project code defaults to this endpoint. A safe no-op
run on October 17 built node:20 with is-number@7.0.0 and executed successfully. Mimi
reported its child network namespace active, and an outbound TCP connection attempt returned
ENETUNREACH. On October 18, the live E1–E4 evaluation suites ran through Token Factory and
Sandboxes; the harness confirmed spawn permission. E1 had 0/11 fixed-version-confirmed
reproductions, E2 did not distinguish the five synthetic reports from the five real ones,
and E4 left one path-read safety check inconclusive. A final E2 rerun completed 10/10 cases,
but Tavily returned HTTP 432 usage-limit errors for every advisory query, so the run had no
advisory results or fixed-version data. A separate read-only `mimi whoami` check returned
`ok: true` and all six permissions. These runs demonstrate the pipeline can execute, not
reliable vulnerability reproduction, useful slop discrimination, or provider-level microVM
isolation.
The September 30 check against the earlier service returned HTTP 200 with all permissions
false; it is historical.

## Provenance

The Official Rules and the two organiser updates ("How to build a winning project", "Here's how judging works") were pasted in by the owner on 2026-09-30. I re-read the live [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) on 2026-10-18. The live page still lists the submission deadline as **Oct 30, 2026 at 10:00 AM Pacific**, the judging period as **Dec 1–15, 2026**, and the public-repository, hosted-demo, public YouTube video under three minutes, track-selection, and product-feedback requirements below. Re-read the page immediately before final submission because the rules can be amended (§11). The Official Rules prevail over other Hackathon material, including the Schedule page.

## Dates [Rules §1]

| Event | When |
|---|---|
| Submission period | Aug 26, 2026 9:00 AM PT to **Fri Oct 30, 2026 10:00 AM PT** |
| Judging | Dec 1, 2026 9:00 AM PT to Dec 15, 2026 12:00 PM PT |
| Winners | on or around Jan 11, 2027 12:00 PM PT |

Internal target: submit **Tue Oct 27**. After the deadline the Submission cannot be changed [§5]. Only a portfolio copy may keep evolving.

## Requirements and current status

| # | Requirement | Source | Status on 2026-10-18 |
|---|---|---|---|
| 1 | Working software that runs on Nebius Token Factory **or** AI Cloud. "Runs on" = makes a **runtime call to the Token Factory inference API**, or is deployed on AI Cloud compute (Serverless Jobs / Endpoints / DevPods) | §4 | Live E1–E4 pipeline runs made runtime calls through Token Factory and Sandboxes. E1 had 0/11 fixed-version-confirmed reproductions; see [evaluation results](evaluation-results.md). There is no hosted live-analysis backend. |
| 2 | Uses at least one NVIDIA open-source model | §4 | Nemotron 3 Nano / Super / Ultra are configured in stage routing and were used in live E1–E4 pipeline and routing runs. |
| 3 | One of four tracks | §4 | Track 2, Best Apps and Agents. The Track 2 text asks for Nemotron via Token Factory, Ultra for serious reasoning, Nano/Super for fast everyday calls. Serverless Endpoints/Jobs are "encouraged", explicitly "neither is required". |
| 4 | Project must function as shown in the video and text | §4 | Final video is not present in this workspace. The script must identify the read-only replay as fixture data and disclose the evaluation results and limits in `docs/evaluation-results.md`. |
| 5 | Working demo / hosted app / test build URL | §4 | GitHub Pages build and deploy run 39055999541 succeeded on 2026-10-17, and the public replay URL returned HTTP 200 on 2026-10-18: `https://zalkabsi.github.io/Mimi/`. A private/clean-browser check is still pending; there is no hosted live-analysis backend or unrestricted judge credential. |
| 6 | Text description of features and functionality | §4 | The description and testing instructions are in `docs/submission-kit.md`; the evaluation results are in `docs/evaluation-results.md`. The final video URL is still pending. |
| 7 | Public repo on GitHub/GitLab/Bitbucket, all source, assets and instructions | §4 | `zalkabsi/Mimi` is public. The submission patch contains the backend fixes, corrected replay fixture, evaluation reports, and current submission copy. |
| 8 | Open-source license file, **detectable and visible at the top of the repo page (About section)** | §4 | GitHub reports the Apache-2.0 license metadata and project description for the public repository (verified 2026-10-17). |
| 9 | README with setup and run instructions; highlight NVIDIA models, where Token Factory accelerated the workflow, other Nebius services | §4 | Root README has setup, model, provider, current-status, and security notes. |
| 10 | Demo video < 3 min, public on YouTube, shows the project functioning, **no third-party trademarks or copyrighted music/material without permission** | §4 | No video media file is present in this workspace. The timed script and captions are drafts. Create and review a final cut, publish it publicly on YouTube, then add its URL to Devpost. |
| 11 | Identify the track | §4 | Track 2. |
| 12 | **Feedback** on Token Factory, AI Cloud and NVIDIA tools/models used (required field) | §4, update | Hands-on Token Factory, Nemotron, Sandboxes, and Tavily notes are in `docs/feedback-log.md`; AI Cloud was not used. Owner attestations are recorded complete. |
| 13 | If the project existed before Aug 26, explain what was significantly updated | §4 | The repo was empty at start (no commits). Keep `CHANGELOG.md` anyway. |
| 14 | English | §4 | Yes. |
| 15 | Original work, solely owned; open-source components allowed if we build meaningful functionality on top and honour licenses | §4 | Third-party licenses tracked below. |
| 16 | No sponsor/administrator funding, contract or commercial license for the project before the period ends | §4 | Standard builder credits offered to all entrants are the only support used. Do not take any sponsor funding, contract or commercial license for Mimi before Oct 30. If unsure whether something counts, ask the organisers in writing before accepting it. |

## Access for judges: the rule that changes our design [§4 Testing]

- The project must be available "**free of charge and without any restriction**" to the Sponsor, Administrator and Judges **until the Judging Period ends (Dec 15, 12:00 PM PT)**. That is about six weeks after submission.
- A private site is allowed if login credentials are in the testing instructions.
- Judges "are not required to test" and may judge from text, images and video alone.

Design consequences:
1. A dedicated **judge credential** with its own reserved budget large enough for realistic testing, no rate limit on that credential, published in the testing instructions.
2. A read-only **demo mode** (seeded inbox with recorded runs) that needs no login and costs nothing, so the product is always demonstrable even if live credits run out.
3. **Hosting that survives to Dec 15** at a cost we can predict. A fixed monthly ceiling must be known before submission.
4. Budget planning needs verified Token Factory prices and Sandbox billing units. Current cost figures are estimates or raw Contree units, so no all-in per-report spending ceiling is established.

## Video rules to design around [§4]

- Third-party trademarks are barred unless permitted. Treat sponsor logos, GitHub/npm logos and any project logos as trademarks. Use **text names** on screen and in narration; keep the UI free of third-party logos and icons.
- No unlicensed music. Use no music, or music we have a license for.
- Narration must name Nebius Token Factory / Sandboxes and the Nemotron models, with audio, not a passing mention.
- Footage must show the project functioning.
- Judges may stop at 3:00. Put the problem and the working product in the first 90 seconds.

## Prize strategy [Rules §8]

- Each project may win **one Overall award OR one Track award, plus one Bonus award** (not several bonuses).
- Bonus candidates: **Best Use of Tavily ($3,000)** needs a functional runtime Tavily API call; City awards need attending an in-person Builders & Brews event; Most Valuable Feedback ($100 + swag, 10 winners) needs a completed feedback section. With one bonus allowed, target **Tavily**. The feedback section is mandatory anyway.
- Judges from Tavily (forward-deployed engineers and developer relations) are on the panel, so the Tavily integration has to be real and visible in the demo.

## Judging [Rules §6 and update]

- **Stage 1**: pass/fail. Reasonable fit with the track theme and genuine use of the required APIs ("not a superficial rebrand").
- **Stage 2**: four **equally weighted** criteria, scored 1-5: Technological Implementation, Design, Potential Impact, Quality of the Idea.
- **Tie-break** goes to the higher score on the first criterion, in this order: Technological Implementation, then Design, then Potential Impact, then Quality of the Idea. **Engineering and product design matter most when scores tie.**
- Organiser hint for Track 2: a "multi-step autonomous workflow that chains tools end to end stands out more" than a single API call.
- Organiser tips: name Token Factory and the NVIDIA model in the description, the Built With section and the video audio; never commit API keys (use `.env` in `.gitignore`); write the video as a pitch, not a tutorial.
- Judges are NVIDIA engineers, Nebius product/DevRel staff and Tavily engineers: assume technical readers who will notice hollow integrations.

## Feedback is required [update]

For each of Token Factory, Sandboxes (AI Cloud is only relevant if we deploy there) and each Nemotron model used, record: what we used it for, what worked, what needs work, onboarding experience (zero to hello world), and whether we would build with it again and why. Name the specific tool and be concrete. Log entries as they happen in `docs/feedback-log.md`.

## Eligibility: owner checks [Rules §3]

The owner recorded the eligibility and agreement attestations complete. Review them
again personally immediately before submission. Confirm all of these yourself; I cannot:
- You are at least the age of majority where you live.
- Your residence is not in an excluded jurisdiction (the Rules list Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea and OFAC-comprehensively-sanctioned places).
- Neither you nor anyone in your immediate family or household works for Nebius, Devpost, or a company that employs a judge (NVIDIA, Nebius, Tavily).
- Winning requires a post-competition affidavit, tax forms and identity verification [§8].

## Third-party components and terms to respect

| Component | License / terms | Status |
|---|---|---|
| `contree-sdk` 0.3.6 (Sandboxes client) | Apache-2.0 (read from package metadata) | OK to use; keep license notices. |
| Token Factory, Tavily | Their service terms | Read before submission; Tavily use must respect its terms. |
| SecBench.js dataset/exploits | not yet checked | Do not vendor data. Provide download scripts. Check the license before redistributing anything. |
| SlopCheck curl set | not yet checked | Same. |
| Public vulnerabilities used in demo and eval | already-public advisories only | No real private or unpatched reports. |

## Credits and cost controls (verify before submission)

- Confirm current Token Factory, Sandboxes, and Tavily credit balances in their official dashboards. Do not rely on promo codes or amounts copied from community pages.
- The available balance and cost of six weeks of judge access are not verified. Sandboxes `ProcessResources.cost` is retained in raw Contree units; the billing conversion is unknown. Mimi's `per_report_cost_cap` is a best-effort threshold in those raw units, not a USD limit. In-flight work can exceed it, and missing cost telemetry cannot be counted. Do not present it as a guaranteed spending ceiling.

## Secrets and environment (names the code will use)

| Variable | What it is | Where it comes from |
|---|---|---|
| `NEBIUS_API_KEY` | Token Factory API key. Used for inference **and** as the bearer token for Sandboxes | Nebius Token Factory console |
| `NEBIUS_PROJECT_ID` | Nebius project ID. Sandboxes require it (sent as a `Project` header; verified live: omitting it returns `400 Missing "Project" header`). Note the **CLI** reads `NEBIUS_AI_PROJECT` / `CONTREE_PROJECT` instead, while the **SDK** reads `NEBIUS_PROJECT_ID`. Mimi uses the SDK | Nebius console |
| `TAVILY_API_KEY` | Tavily key | Tavily dashboard. Confirm any plan or hackathon credit balance directly with Tavily/Nebius. |

For local development, put them in the ignored `.env` file from `.env.example`. For deployment, use the host's secret manager. Never commit keys or paste them into chat.

## Technical facts and remaining open items

| Item | Why it matters | Known so far |
|---|---|---|
| Per-run network isolation in Sandboxes | Reporter-supplied PoC code is untrusted | The SDK run request has no network field. Mimi requires a child user/network namespace and rejects online PoC configurations. A safe no-op smoke confirmed the namespace marker and observed a TCP connection attempt blocked with ENETUNREACH. This tests Mimi's app-level guard for the harmless run only; it does not establish provider-level microVM security or resistance to hostile code. Probe state remains in the same writable VM and is not tamper-proof. |
| ~~Token Factory inference base URL and Nemotron model IDs~~ | Code depends on them | Base `https://api.tokenfactory.nebius.com/v1` is OpenAI-compatible. Re-verified 2026-10-15 with `GET /models` and chat calls for Nano, Super and Ultra. Exact IDs from the live model list: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`, and `nvidia/Nemotron-3_5-Lightning`. The old code had `NVIDIA` uppercase in the Ultra ID and got HTTP 404; the exact ID from `/models` is now in routing and cost accounting, and a retry succeeded for reasoning-on/off and tool calling. Lightning has not been evaluated. |
| Reasoning control and tool calling | Routing design | Re-checked 2026-10-15: Nano, Super and Ultra each accepted a function-tool call and reasoning on/off. On one short prompt, Nano with `max_tokens=20` returned empty content; Super and Ultra returned `ready`. Nano returned `completion_tokens_details: null`; Super and Ultra itemised reasoning tokens. These are smoke checks, not structured-output or routing evaluations. |
| **Sandboxes token permissions and operation** | Sandboxes are Mimi's core | **Access confirmed 2026-10-17:** GET /v1/whoami returned HTTP 200 with all six permissions true. On 2026-10-18, live E1–E4 runs confirmed spawn access and pipeline execution. The separate safe no-op observed Mimi's network namespace and blocked egress. These checks do not validate provider-level microVM isolation; the E4 path-traversal read check was not run. Previous September 30 result (all permissions false) is historical. The SDK reports raw Contree cost units; currency conversion is unknown. |
| Key lifetime for judge access | Judge access must last to Dec 15 | **Corrected 2026-09-30.** `whoami`'s `token_expiration` is a *rolling* value: it read exactly 5 minutes after each call (06:56:55 to 07:01:55, then 07:02:41 to 07:07:41), and the key kept working afterwards for Sandboxes `whoami`, inference and Tavily. It is **not** the key's lifetime. The real lifetime of `NEBIUS_API_KEY` is still unknown. Whatever key the hosted demo uses must be valid through Dec 15, 2026, so check the expiry shown for the key in the console when creating it. |
| Sandboxes billing | Credits budget | Is it drawn from the same credits as inference? Unknown. |
| `ProcessResources.cost` units | Cost accounting | The SDK returns a cost value; its conversion to billing currency is unknown. Mimi reports the raw value as Contree units. |
| Can the backend run as a Serverless Endpoint on CPU? | Optional AI Cloud deployment (encouraged, not required) | Not evaluated. The current public demo is a static GitHub Pages replay; no backend is deployed there. |
