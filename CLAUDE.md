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

Docs and repo hygiene are done. **No code yet.** Key check on 2026-09-30:

- **Token Factory inference: works.** Base `https://api.tokenfactory.nebius.com/v1`. Exact Nemotron IDs are in `docs/00-constraints-and-open-items.md`. Nano is a reasoning model: pass `chat_template_kwargs: {"enable_thinking": false}` for cheap calls, and never use a tiny `max_tokens` with reasoning on (empty content).
- **Tavily: works.**
- **Sandboxes: BLOCKED.** The key authenticates but `whoami` shows every permission `false` (`spawn`, `list`, ...). Nothing in Sandboxes can run until the owner gets Sandboxes grants for the project. Note that `token_expiration` in `whoami` is a rolling five-minute value, not the key's lifetime; the key itself must be valid through Dec 15, 2026 (check in the console).

First thing in a new session: run `whoami` (status and permissions only, never print keys). If `spawn` is still `false`, do not start Sandboxes work; work on the parts that do not need it (stages 1-4, the eval harness, UI). Then the week-1 spikes:

1. Token Factory inference call to a Nemotron model: confirm base URL, exact model IDs, tool calling, reasoning control. Log tokens and latency.
2. Sandboxes: build an npm package at a pinned vulnerable version, keep the image, run 5 forks in parallel. Record `cost` units and elapsed time.
3. Test `unshare -n` inside the microVM to get an offline PoC phase. If it fails, say so and adopt the replay-only hosted demo.
4. Tavily call using only public identifiers.
5. First slice: CLI, one real public npm vulnerability, report in, dossier JSON out, with a fixed-version differential.

**Pivot review Sun Oct 5**: see the pivot triggers in `docs/01-research-and-decision.md`. Fallback concept is Envsmith.
