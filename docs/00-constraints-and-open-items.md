# Hard constraints and open items

Updated 2026-09-30. Team: **solo**. Project name: **Mimi**.

## Provenance

The Official Rules and the two organiser updates ("How to build a winning project", "Here's how judging works") were pasted in by the owner on 2026-09-30. Those are the primary source for everything marked **[Rules §n]** below. Rules can be amended (§11), so re-read the live Rules page once before submitting. Section 11 says the Official Rules prevail over any other Hackathon material, which settles the judging-start discrepancy: use the Rules' **Dec 1, 2026** (the Schedule page's Nov 2 is not authoritative).

## Dates [Rules §1]

| Event | When |
|---|---|
| Submission period | Aug 26, 2026 9:00 AM PT to **Fri Oct 30, 2026 10:00 AM PT** |
| Judging | Dec 1, 2026 9:00 AM PT to Dec 15, 2026 12:00 PM PT |
| Winners | on or around Jan 11, 2027 12:00 PM PT |

Internal target: submit **Tue Oct 27**. After the deadline the Submission cannot be changed [§5]. Only a portfolio copy may keep evolving.

## Requirements and how Mimi meets them

| # | Requirement | Source | Plan |
|---|---|---|---|
| 1 | Working software that runs on Nebius Token Factory **or** AI Cloud. "Runs on" = makes a **runtime call to the Token Factory inference API**, or is deployed on AI Cloud compute (Serverless Jobs / Endpoints / DevPods) | §4 | Every pipeline stage calls Token Factory inference at runtime. |
| 2 | Uses at least one NVIDIA open-source model | §4 | Nemotron 3 Nano / Super / Ultra with stage routing. |
| 3 | One of four tracks | §4 | Track 2, Best Apps and Agents. The Track 2 text asks for Nemotron via Token Factory, Ultra for serious reasoning, Nano/Super for fast everyday calls. Serverless Endpoints/Jobs are "encouraged", explicitly "neither is required". |
| 4 | Project must function as shown in the video and text | §4 | Video and text are written from measured runs only. |
| 5 | Working demo / hosted app / test build URL | §4 | Hosted demo (see access design). |
| 6 | Text description of features and functionality | §4 | Devpost description drafted in Phase 9. |
| 7 | Public repo on GitHub/GitLab/Bitbucket, all source, assets and instructions | §4 | `zalkabsi/Mimi`. |
| 8 | Open-source license file, **detectable and visible at the top of the repo page (About section)** | §4 | Unmodified Apache-2.0 text in `LICENSE`, so GitHub's detector shows it. |
| 9 | README with setup and run instructions; highlight NVIDIA models, where Token Factory accelerated the workflow, other Nebius services | §4 | README drafted in Phase 9. |
| 10 | Demo video < 3 min, public on YouTube, shows the project functioning, **no third-party trademarks or copyrighted music/material without permission** | §4 | See video rules below. |
| 11 | Identify the track | §4 | Track 2. |
| 12 | **Feedback** on Token Factory, AI Cloud and NVIDIA tools/models used (required field) | §4, update | `docs/feedback-log.md`, kept as we build. |
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
| `NEBIUS_PROJECT_ID` | Nebius project ID. Sandboxes require it (sent as a `Project` header; verified in `contree-sdk` source) | Nebius console |
| `TAVILY_API_KEY` | Tavily key | `app.tavily.com`: sign in (email, Google, GitHub, LinkedIn or Microsoft), copy a key from the dashboard. Free plan reported as 1,000 API credits a month, no card. Extra hackathon credits come through the Nebius Builders Program [Rules §4] (promo `BBDEVPOST` seen in one community repo, unverified). `docs.tavily.com` is blocked in the build environment; `api.tavily.com` is reachable, which is all the code needs. |

Add them as **environment secrets** in the Claude Code cloud environment settings; never in the repo or in chat. `.env` is git-ignored for local use.

## Technical facts still to verify on day 1

| Item | Why it matters | Known so far |
|---|---|---|
| Per-run network isolation in Sandboxes | We execute reporter-supplied PoC code | `contree-sdk 0.3.6` run request has **no network field**. Plan: test `unshare -n` in the microVM. |
| Token Factory inference base URL and exact Nemotron model IDs | Code depends on them | Community repos use an OpenAI-compatible endpoint; ids unverified. |
| Tool calling and reasoning control on Token Factory | Routing design | NVIDIA says supported; unverified on Token Factory. |
| Sandboxes billing | Credits budget | Is it drawn from the same credits as inference? Unknown. |
| `ProcessResources.cost` units | Cost accounting | Field exists; units unknown. |
| Can the backend run as a Serverless Endpoint on CPU? | Optional AI Cloud deployment (encouraged, not required) | Unknown. Decide in week 3 on cost and simplicity. |
