# Product feedback log

The hackathon requires feedback on Nebius Token Factory, AI Cloud and any NVIDIA tools or models we use, and "Most Valuable Feedback" is judged on completeness, viability and potential impact. For each tool: what we used it for, what worked, what needs work, onboarding (zero to hello world), and whether we would build with it again and why.

Rules for this file: log an entry when something happens, with the date. Name the specific tool, version and call. Mark whether an observation came from **hands-on use** or from **reading source/docs only**. Do not write opinions we cannot back up.

## Nebius Token Factory: Sandboxes (`contree-sdk`)

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-09-29 | read source, `contree-sdk 0.3.6` | The run request (`InstanceSpawnRequest`) has no option to disable outbound network. For products that execute untrusted code (ours runs reporter-supplied proofs of concept), per-run network isolation is a core safety control. | Add a per-run `network: none / restricted` option, or document the recommended pattern. |
| 2026-09-29 | read source | `disposable` defaults differ by layer: `run(...)` in the SDK defaults to `True`, the raw `InstanceSpawnRequest` defaults to `False`, and the MCP guide states the CLI defaults to non-disposable while the MCP tool defaults to disposable. Easy to lose state or keep it unintentionally when moving between layers. | Align defaults or make the argument required. |
| 2026-09-29 | read source | Authentication for Token Factory needs both `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (the project ID is sent as a `Project` header). A key alone is not enough. | Say so at the top of the getting-started page and in the error returned when the project header is missing. |

## Nebius Token Factory: inference

_No hands-on entries yet._ Fill in from the first spike: time to first successful call, base URL and model-ID discoverability, tool-calling behaviour, reasoning-control support, latency and token accounting.

## Nebius AI Cloud (Serverless Endpoints / Jobs)

_Only if we deploy there._ Record why we did or did not.

## NVIDIA Nemotron 3 (Nano / Super / Ultra)

_No hands-on entries yet._ Record per stage: task, model used, structured-output reliability, tool-calling behaviour, cost and latency, and where routing helped or did not.

## Tavily

_No hands-on entries yet._ (Not part of the required feedback, but useful for the Tavily judges.)
