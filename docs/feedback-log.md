# Product feedback log

The hackathon requires feedback on Nebius Token Factory, AI Cloud and any NVIDIA tools or models we use, and "Most Valuable Feedback" is judged on completeness, viability and potential impact. For each tool: what we used it for, what worked, what needs work, onboarding (zero to hello world), and whether we would build with it again and why.

Rules for this file: log an entry when something happens, with the date. Name the specific tool, version and call. Mark whether an observation came from **hands-on use** or from **reading source/docs only**. Do not write opinions we cannot back up.

## Nebius Token Factory: Sandboxes (`contree-sdk`)

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-10-06 | read docs, `contree-sdk` README (GitHub) | The SDK README documents profiles (`CONTREE_PROFILE`, `~/.config/contree/auth.ini`) and a `ContreeAsyncClient(api_key, base_url, …)` constructor, but not a `whoami`/permissions surface: a permissions probe needs raw HTTP (`GET /v1/whoami`). First-run diagnosis of a permission problem therefore needs two tools, not one. | Expose whoami (and its permission list) in the SDK, and link it from the getting-started page. |
| 2026-10-06 | read docs | The published support range on PyPI is Python 3.10–3.13. This development machine also has 3.14, where `pip install contree-sdk` is refused by metadata unless overridden. | Widen `requires-python` once 3.14 is tested, or state the supported range in the error text. |
| 2026-10-06 | read docs | README examples run commands via `image.run(shell=…)` / `image.run(command=…, args=…, files=…)` and say each run yields a new image UUID only when the filesystem changed. That is elegant for branching, but there is no documented "run this with network disabled" option — the gap we already logged on 2026-09-29, still open. | Per-run network isolation remains the top ask. |
|---|---|---|---|
| 2026-09-29 | read source, `contree-sdk 0.3.6` | The run request (`InstanceSpawnRequest`) has no option to disable outbound network. For products that execute untrusted code (ours runs reporter-supplied proofs of concept), per-run network isolation is a core safety control. | Add a per-run `network: none / restricted` option, or document the recommended pattern. |
| 2026-09-29 | read source | `disposable` defaults differ by layer: `run(...)` in the SDK defaults to `True`, the raw `InstanceSpawnRequest` defaults to `False`, and the MCP guide states the CLI defaults to non-disposable while the MCP tool defaults to disposable. Easy to lose state or keep it unintentionally when moving between layers. | Align defaults or make the argument required. |
| 2026-09-30 | hands-on | **A valid key can authenticate to Sandboxes with zero permissions.** `GET /v1/whoami` returned 200, but every permission (import, spawn, spawn_disposable, list, cancel, set_image_tag) was `false`; every real call then returns `403 Insufficient permissions: <name>`. The error is clear, but neither the docs page I could find nor the error says how to obtain the grants. That was the first thing that stopped us from building. | Say in the error and on the Sandboxes getting-started page exactly where in the console permissions or access are enabled, and whether a default hackathon key should have them. |
| 2026-09-30 | hands-on | `GET /v1/whoami` accepts **any** value in the `Project` header: my real project ID and two fake IDs returned an identical 200 with identical permissions. A wrong project ID therefore gives no early error, and I spent a round changing the ID when the problem was the token's permissions. | Validate the `Project` header in `whoami` (or return the project the token is bound to) so a mismatch is visible immediately. |
| 2026-09-30 | hands-on | `GET /v1/whoami` returns `token_expiration`, which I first read as the key's lifetime (it was minutes away). Re-testing showed it is a rolling value, always 5 minutes after the call, and the key kept working past it. The field name suggests something the API does not mean, and I could not find it explained. I misreported it because of that. | Document what `token_expiration` means, or rename it, and expose the real lifetime of the key. |
| 2026-09-30 | read docs | The CLI and the SDK read different environment variable names for the project ID (`NEBIUS_AI_PROJECT` / `CONTREE_PROJECT` versus `NEBIUS_PROJECT_ID`). | Accept both in both, or unify. |
| 2026-09-29 | read source | Authentication for Token Factory needs both `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (the project ID is sent as a `Project` header). A key alone is not enough. | Say so at the top of the getting-started page and in the error returned when the project header is missing. |

## Nebius Token Factory: inference

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-09-30 | hands-on | **Onboarding was fast.** With an API key, `GET /v1/models` and a first `chat/completions` call both worked immediately (0.4 s and about 1 s). The endpoint is OpenAI-compatible, so no new client was needed. | None. Positive. |
| 2026-09-30 | hands-on | Model IDs are inconsistent in case and separators: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`. Guessing an ID from a sibling model fails. | Normalise IDs, or document a table of exact IDs per model. |
| 2026-09-30 | hands-on | Nano is a reasoning model. With `max_tokens=20` the call returned HTTP 200 with **empty `content`**: the whole budget went to hidden reasoning and nothing signalled it in the payload beyond token counts. Same prompt with `max_tokens=300` returned `content: "ready"` plus a 259-character `message.reasoning`. | Return `finish_reason: "length"` (or a warning field) when the budget ends inside reasoning, and document the `max_tokens` implication for reasoning models. |
| 2026-09-30 | hands-on | `chat_template_kwargs: {"enable_thinking": false}` turns reasoning off on Token Factory: 2 completion tokens versus 62, and 0.75 s versus 1.40 s for the same one-word prompt. It works but I only found it by trying the vLLM convention. | Document the supported way to control reasoning per model (on/off, effort, budget) on the model page. |
| 2026-09-30 | hands-on | `usage.completion_tokens_details` is `null`, so reasoning tokens are not broken out from answer tokens. For a routing design that trades reasoning depth for cost, that split is what we need. | Populate `reasoning_tokens`. |

## Nebius AI Cloud (Serverless Endpoints / Jobs)

_Only if we deploy there._ Record why we did or did not.

## NVIDIA Nemotron 3 (Nano / Super / Ultra)

_No hands-on entries yet._ Record per stage: task, model used, structured-output reliability, tool-calling behaviour, cost and latency, and where routing helped or did not.

## Tavily

_No hands-on entries yet._ (Not part of the required feedback, but useful for the Tavily judges.)
