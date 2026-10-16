# Mimi: project context for Claude

Solo entry to the **Nebius x NVIDIA Global AI Hackathon 2026**, Track 2 (Best Apps and Agents). Deadline **Fri Oct 30, 2026 10:00 AM PT**; internal target Tue Oct 27. Judge access must stay free and unrestricted until Dec 15, 12:00 PM PT.

## What Mimi is

Open-source maintainers get vulnerability reports they cannot cheaply verify. Mimi reproduces a report's claim in isolated Token Factory Sandboxes at the exact affected version and returns an **evidence dossier and a triage tier**. It never auto-closes. Its non-obvious idea is **negative-result coverage**: build the environment once, fork the sandbox per hypothesis, and report "N hypotheses tested, 0 triggered" instead of a bare "not reproduced".

Read in this order: `docs/01-research-and-decision.md` (why), `docs/02-architecture.md` (design, eval protocol, 4-week plan), `docs/00-constraints-and-open-items.md` (rules and open checks).

## Non-negotiable rules

- **Never commit secrets.** Keys come from env vars: `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID` (Sandboxes need both), `TAVILY_API_KEY`. Never ask the user to paste a key into chat.
- **No Claude attribution in git history.** Never add a `Co-Authored-By` trailer, a session link, or any other Claude attribution to commit messages or PR descriptions. The owner asked for this explicitly.
- **Never invent a metric.** Every number in the README, Devpost text or video comes from a logged run. State sample sizes and limits (SecBench.js is npm only; synthetic slop is not real slop).
- **Never auto-close a report.** Tiers: Confirmed, Likely, Needs human, Contradicted (with coverage). Grounding alone must never reject a report.
- Run untrusted PoC code **only inside Sandboxes**, never on the app host. No secrets in any sandbox. Tavily queries use public identifiers only.
- Demo and eval use **already-public** vulnerabilities only.
- Video and UI: no third-party logos, no unlicensed music. Use text names.
- Keep `LICENSE` as the unmodified Apache-2.0 text. Keep `CHANGELOG.md` and `docs/feedback-log.md` current as work happens.
- Smallest architecture that works: FastAPI, SQLite, React/Vite. No queue, no vector store.

## Where we are

Week 3 (Oct 13-19). The backend pipeline (`backend/mimi/`), API + CLI, React UI (`frontend/`), eval harness, 27-case corpus (`evals/`), and backend unit tests are in the repo. Current Sandboxes check (2026-10-15) returned HTTP 403 for both whoami paths, with no permission details; live sandbox runs and execution-dependent evaluations remain blocked. A prior 2026-09-30 check returned 200 with all permissions false. Do not describe either state as a successful sandbox run. Token Factory inference and Tavily were re-checked live on 2026-10-15; the feedback log records results for Nano, Super, Ultra, and five public-identifier-only Tavily queries.

- **Token Factory inference: works.** Base `https://api.tokenfactory.nebius.com/v1`. Exact Nemotron IDs are in `docs/00-constraints-and-open-items.md`. Nano is a reasoning model: pass `chat_template_kwargs: {"enable_thinking": false}` for cheap calls, and never use a tiny `max_tokens` with reasoning on (empty content).
- **Tavily: works.**
- **Sandboxes: BLOCKED.** The latest check returned HTTP 403 without permission details; the cause is unknown. The 2026-09-30 check returned 200 with every permission false. Do not infer a grant issue from the new response alone. `token_expiration` in the older `whoami` response was a rolling five-minute value, not the key's lifetime; check the real key expiry in the console for judge access through Dec 15, 2026.
- A local root `.env` is now loaded by `python-dotenv`; `.env.example` lists the expected variables. Never paste keys into chat. Latest Sandboxes 403 does not establish whether the cause is a token grant, endpoint access, or another provider-side issue.

First thing in a new session: run `python scripts/check_sandboxes_whoami.py` (status and permissions only, never print keys). If the response is 403 or `spawn` is false, do not start Sandboxes work; work on the parts that do not need it (stages 1-4, the eval harness, UI). Token Factory inference and Tavily were re-checked on 2026-10-15. After Sandboxes access returns, continue with these blocked steps:

1. Re-run `python scripts/spike_inference.py` if model routing changes; current Nano, Super and Ultra results are in `docs/feedback-log.md`.
2. Sandboxes: build an npm package at a pinned vulnerable version, keep the image, run 5 forks in parallel. Record `cost` units and elapsed time. (`scripts/` + `mimi/sandboxes.py` already implement build-once/fork.)
3. Test `unshare -n` inside the microVM to get an offline PoC phase (the executor wraps PoC runs with `unshare -n` and records `network_isolated`). If it fails, say so and adopt the replay-only hosted demo.
4. Re-run `python scripts/spike_tavily.py` if query construction or the provider integration changes; current results are in `docs/feedback-log.md`.
5. First slice: CLI, one real public npm vulnerability, report in, dossier JSON out, with a fixed-version differential.

**Pivot review (recorded 2026-10-06)**: see the update in `docs/01-research-and-decision.md`. No trigger could be evaluated without Sandboxes; decision is to continue Mimi and re-review within 48h of `spawn` being granted. Fallback concept is Envsmith.
