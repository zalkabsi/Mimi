# Hard constraints and open verification items

Working checklist. Tick items as they are satisfied. Anything marked **VERIFY** could not be confirmed from a primary source during research.

## Provenance warning

`nebiusglobalaihackathon.devpost.com` (and the third-party listing sites) were **blocked by the session's egress proxy**. Every hackathon fact below comes from search-result summaries, the user's brief, or community repos, not from the official Rules tab. **Someone with browser access must read the Devpost Rules and Schedule tabs before submission** and correct this file.

## Hard requirements (from the brief)

| # | Requirement | Status |
|---|---|---|
| 1 | Functioning software/AI system | planned |
| 2 | Runs on Nebius Token Factory **or** Nebius AI Cloud, in a way that is essential to the product | planned: Token Factory inference + Token Factory Sandboxes |
| 3 | Uses at least one NVIDIA open-source model, centrally | planned: Nemotron 3 Nano / Super / Ultra with routing |
| 4 | One primary track | recommended: Track 2 (Best Apps and Agents); decide before submission |
| 5 | Working demo URL, free access for judges, test instructions, sample data | planned |
| 6 | Public YouTube demo video, <= 3 min, real product working, narration covers problem / NVIDIA usage / Nebius usage; no unlicensed music or media | planned |
| 7 | Public repo (GitHub/GitLab/Bitbucket) with source, assets, setup, run, dependency and config docs, README, visible OSI license | planned |
| 8 | README covers the 12 items in the brief (what/problem/architecture/install/config/run/NVIDIA models/how they contribute/Nebius services/how they contribute/third parties/demo) | planned |
| 9 | Devpost description covering problem, users, motivation, solution, workflow, architecture, models, Nebius, NVIDIA, features, innovation, impact | planned |
| 10 | Product feedback (Token Factory, Sandboxes, Nemotron, tools we actually use), specific enough for the feedback prize | collect **as we build**, in `docs/feedback-log.md` |
| 11 | Existing-project disclosure / changelog | repo was empty at start (no commits). Keep `CHANGELOG.md` from the first commit. |
| 12 | English materials | yes |
| 13 | Original work; third-party licenses respected | check dataset licenses (below) |
| 14 | Multiple entries must be substantially different | single entry planned |

## Dates

- Submission deadline: **Fri Oct 30, 2026, 10:00 AM PT** (brief + search summaries agree). Internal target: submit **Tue Oct 27**, leaving 3 days of buffer.
- Judging start: Rules say Dec 1, Schedule page says Nov 2 (per the brief). Judging ends Dec 15; winners about Jan 11, 2027. **VERIFY** on Devpost. Our plan does not depend on this date, except: tag a release at submission and avoid changing the demo after the deadline unless the Rules allow it.

## Prizes and strategy

- Overall (Grand $20k / 2nd $10k / 3rd $6k) or a track award, plus one eligible bonus. Stacking rules **VERIFY**.
- Best Use of Tavily ($3,000): requires a functional runtime Tavily call. We use it load-bearing (see architecture). It is a bonus, never a reason to bend the product.
- Most Valuable Feedback: feedback log is maintained continuously.
- City awards: only if a team member is associated with a participating Builders & Brews city. **VERIFY** eligibility and dates. Not planned.

## Credits (VERIFY still active)

- ~$25 Token Factory credit via the Devpost/Nebius form, code `NEBIUS-DEVPOST-GLOBAL26` (seen on community repos and a Luma page, not on Devpost).
- ~$25 more via the Nebius Builders Program (also Tavily credit; Tavily promo `BBDEVPOST` was mentioned in one community repo).

## Technical facts that must be verified on day 1 (spikes)

| Item | Why it matters | Known so far |
|---|---|---|
| Can a Sandboxes run be made network-isolated? | We execute reporter-supplied PoC code | `contree-sdk 0.3.6` `InstanceSpawnRequest` has **no network field** (checked in source). Docs summary: no *inbound* network; outbound appears available. Plan: test `unshare -n` inside the microVM for the PoC phase. |
| Token Factory inference base URL and exact Nemotron model IDs | Code depends on them | Community repos use OpenAI-compatible endpoints; one lists `nvidia/nemotron-3-super-120b-a12b`. **VERIFY**. |
| Nemotron tool calling + reasoning on/off/budget on Token Factory | Routing design | NVIDIA material says supported for Ultra. **VERIFY** on Token Factory. |
| Concurrency: 50 simultaneous sandbox operations | Bounds our fork fan-out | From docs summary. |
| Sandbox `cost` field units | Cost accounting must be honest | Field exists in `ProcessResources`. Units unknown. |
| Image retention 180 days | Snapshot reuse across eval runs | From docs summary. |
| Dataset licenses: SecBench.js, SlopCheck curl set | Redistribution in our repo | Unchecked. Do not vendor data until checked; download scripts instead. |

## Environment: hosts to allow so the build can be tested from this session

The session network policy currently blocks Devpost and most of the web. To build and test here, add these to the environment's allowed domains (cloud environment menu, then Edit):

- `api.tokenfactory.nebius.com` (inference and Sandboxes; the SDK base URL is `https://api.tokenfactory.nebius.com/sandboxes`)
- `docs.tokenfactory.nebius.com`
- `api.tavily.com`
- `github.com`, `codeload.github.com`, `api.github.com` (clone target repos at pinned versions)
- `nebiusglobalaihackathon.devpost.com` (read the official rules)
- `registry.npmjs.org` and `pypi.org` were reachable already.

Secrets (Token Factory key, Tavily key) go in the environment's secrets, never in the repo.
