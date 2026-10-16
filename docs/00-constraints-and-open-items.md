# Hard constraints and open items

Updated 2026-10-15. Team: **solo**. Project name: **Mimi**.

## Current build-environment check (2026-10-15)

The Sandboxes `whoami` probe returned HTTP 403 for both `/whoami` and `/v1/whoami` at `https://api.sandbox.nebius.ai/v1`. The response did not include a permissions block, so this check does **not** distinguish a missing grant from another access or endpoint issue. The managed environment reports the Nebius key and project bindings as ready and Sandboxes egress as enforced; those are setup signals, not proof the service accepts the key. No sandbox execution or execution-dependent evaluation can proceed until a usable permission response is available. The previous 2026-09-30 check returned HTTP 200 with every permission set to `false`; that is historical and is not the result of today's check.

## Provenance

The Official Rules and the two organiser updates ("How to build a winning project", "Here's how judging works") were pasted in by the owner on 2026-09-30. I re-read the live [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) on 2026-10-16. The live page still lists the submission deadline as **Oct 30, 2026 at 10:00 AM Pacific**, the judging period as **Dec 1–15, 2026**, and the public-repository, hosted-demo, public YouTube video under three minutes, track-selection, and product-feedback requirements below. Re-read the page immediately before final submission because the rules can be amended (§11). The Official Rules prevail over other Hackathon material, including the Schedule page.

## Dates [Rules §1]

| Event | When |
|---|---|
| Submission period | Aug 26, 2026 9:00 AM PT to **Fri Oct 30, 2026 10:00 AM PT** |
| Judging | Dec 1, 2026 9:00 AM PT to Dec 15, 2026 12:00 PM PT |
| Winners | on or around Jan 11, 2027 12:00 PM PT |

Internal target: submit **Tue Oct 27**. After the deadline the Submission cannot be changed [§5]. Only a portfolio copy may keep evolving.

## Requirements and current status

| # | Requirement | Source | Status on 2026-10-16 |
|---|---|---|---|
| 1 | Working software that runs on Nebius Token Factory **or** AI Cloud. "Runs on" = makes a **runtime call to the Token Factory inference API**, or is deployed on AI Cloud compute (Serverless Jobs / Endpoints / DevPods) | §4 | Pipeline inference is implemented; direct runtime smoke calls to Nano, Super, and Ultra succeeded. A live end-to-end Mimi run is not verified. |
| 2 | Uses at least one NVIDIA open-source model | §4 | Nemotron 3 Nano / Super / Ultra are configured in stage routing and were used in direct smoke calls. |
| 3 | One of four tracks | §4 | Track 2, Best Apps and Agents. The Track 2 text asks for Nemotron via Token Factory, Ultra for serious reasoning, Nano/Super for fast everyday calls. Serverless Endpoints/Jobs are "encouraged", explicitly "neither is required". |
| 4 | Project must function as shown in the video and text | §4 | Final video and final copy are pending; record only from the actual demo path and distinguish replay from live execution. |
| 5 | Working demo / hosted app / test build URL | §4 | A GitHub Pages workflow now builds the read-only replay; public deployment and a clean-browser check are pending. Expected URL: `https://zalkabsi.github.io/Mimi/`. |
| 6 | Text description of features and functionality | §4 | Draft is in `docs/submission-kit.md`; it still needs the final URL and evidence-based status. |
| 7 | Public repo on GitHub/GitLab/Bitbucket, all source, assets and instructions | §4 | GitHub metadata reports `zalkabsi/Mimi` is **private**. The source is present, but this requirement is not met until visibility changes. |
| 8 | Open-source license file, **detectable and visible at the top of the repo page (About section)** | §4 | Unmodified Apache-2.0 text is in `LICENSE`; GitHub About metadata is not confirmed. |
| 9 | README with setup and run instructions; highlight NVIDIA models, where Token Factory accelerated the workflow, other Nebius services | §4 | Root README has setup, model, provider, current-status, and security notes. |
| 10 | Demo video < 3 min, public on YouTube, shows the project functioning, **no third-party trademarks or copyrighted music/material without permission** | §4 | A 2:40 script is drafted in `docs/submission-kit.md`; no recording or upload yet. |
| 11 | Identify the track | §4 | Track 2. |
| 12 | **Feedback** on Token Factory, AI Cloud and NVIDIA tools/models used (required field) | §4, update | Hands-on Token Factory, Nemotron, Sandboxes, and Tavily notes are in `docs/feedback-log.md`; AI Cloud was not used. |
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
4. Budget planning uses measured cost per report (Token Factory tokens plus Sandboxes runs), never estimates.

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

Confirm all of these yourself; I cannot:
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

## Credits (still to verify by you)

- ~$25 Token Factory credit via the Devpost/Nebius form, code `NEBIUS-DEVPOST-GLOBAL26`; ~$25 more (plus Tavily credit) via the Nebius Builders Program [Rules §4 confirms the Builder Program credits; the code itself came from community pages]. Tavily promo `BBDEVPOST` was seen in a community repo.
- **Budget risk**: about $50 of credits must cover development, the evaluation runs, and six weeks of judge access. I will measure tokens and Sandboxes cost per report in the first spike and size the evaluation to what the credits allow.

## Secrets and environment (names the code will use)

| Variable | What it is | Where it comes from |
|---|---|---|
| `NEBIUS_API_KEY` | Token Factory API key. Used for inference **and** as the bearer token for Sandboxes | Nebius Token Factory console |
| `NEBIUS_PROJECT_ID` | Nebius project ID. Sandboxes require it (sent as a `Project` header; verified live: omitting it returns `400 Missing "Project" header`). Note the **CLI** reads `NEBIUS_AI_PROJECT` / `CONTREE_PROJECT` instead, while the **SDK** reads `NEBIUS_PROJECT_ID`. Mimi uses the SDK | Nebius console |
| `TAVILY_API_KEY` | Tavily key | `app.tavily.com`: sign in (email, Google, GitHub, LinkedIn or Microsoft), copy a key from the dashboard. Free plan reported as 1,000 API credits a month, no card. Extra hackathon credits come through the Nebius Builders Program [Rules §4] (promo `BBDEVPOST` seen in one community repo, unverified). `docs.tavily.com` is blocked in the build environment; `api.tavily.com` is reachable, which is all the code needs. |

Add them as **environment secrets** in the Claude Code cloud environment settings; never in the repo or in chat. `.env` is git-ignored for local use.

## Technical facts and remaining open items

| Item | Why it matters | Known so far |
|---|---|---|
| Per-run network isolation in Sandboxes | We execute reporter-supplied PoC code | `contree-sdk 0.3.6` run request has **no network field**. The executor now requires a child user and network namespace (`unshare --user --map-root-user --net`) and rejects configs that request online PoC execution. This guard fails closed but remains unverified in a real microVM because the Sandboxes access check returns HTTP 403. |
| ~~Token Factory inference base URL and Nemotron model IDs~~ | Code depends on them | Base `https://api.tokenfactory.nebius.com/v1` is OpenAI-compatible. Re-verified 2026-10-15 with `GET /models` and chat calls for Nano, Super and Ultra. Exact IDs from the live model list: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`, and `nvidia/Nemotron-3_5-Lightning`. The old code had `NVIDIA` uppercase in the Ultra ID and got HTTP 404; the exact ID from `/models` is now in routing and cost accounting, and a retry succeeded for reasoning-on/off and tool calling. Lightning has not been evaluated. |
| Reasoning control and tool calling | Routing design | Re-checked 2026-10-15: Nano, Super and Ultra each accepted a function-tool call and reasoning on/off. On one short prompt, Nano with `max_tokens=20` returned empty content; Super and Ultra returned `ready`. Nano returned `completion_tokens_details: null`; Super and Ultra itemised reasoning tokens. These are smoke checks, not structured-output or routing evaluations. |
| **Sandboxes token permissions** | Sandboxes are Mimi's core | **BLOCKED (2026-10-15).** Latest `whoami` returned HTTP 403 for both supported endpoint paths and no permissions block, so the cause is not established. Previous hands-on result (2026-09-30): HTTP 200 with all permissions false, and `/v1/images` returned `403 Insufficient permissions: list`; changing the project ID did not change that result. Neither result allows execution. Limits previously reported: 50 concurrent instances, 3600 s max timeout, 12 GiB max layer. Re-check once access is corrected; do not claim spawn permission based on credentials being present. |
| Key lifetime for judge access | Judge access must last to Dec 15 | **Corrected 2026-09-30.** `whoami`'s `token_expiration` is a *rolling* value: it read exactly 5 minutes after each call (06:56:55 to 07:01:55, then 07:02:41 to 07:07:41), and the key kept working afterwards for Sandboxes `whoami`, inference and Tavily. It is **not** the key's lifetime. The real lifetime of `NEBIUS_API_KEY` is still unknown. Whatever key the hosted demo uses must be valid through Dec 15, 2026, so check the expiry shown for the key in the console when creating it. |
| Sandboxes billing | Credits budget | Is it drawn from the same credits as inference? Unknown. |
| `ProcessResources.cost` units | Cost accounting | Field exists; units unknown. |
| Can the backend run as a Serverless Endpoint on CPU? | Optional AI Cloud deployment (encouraged, not required) | Unknown. Decide in week 3 on cost and simplicity. |
