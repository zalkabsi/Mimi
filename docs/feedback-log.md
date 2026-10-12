# Product feedback log

Feedback on Nebius Token Factory (inference and Sandboxes), NVIDIA Nemotron 3 and Tavily, from building Mimi (Aug 26 - Oct 30, 2026). Each entry says whether it came from **hands-on use** or from **reading source/docs only**, with the date. Everything marked hands-on was observed on a real call; numbers come from logged runs (`docs/eval-logs/`, `CHANGELOG.md`) and measure single calls, not benchmarks.

## Summary for the organisers

| Tool | Used for | Worked well | Needs work | Would we build with it again? |
|---|---|---|---|---|
| Token Factory inference | Every pipeline stage at runtime (extract, ground, research synthesis, hypotheses, verdict text, reply) | OpenAI-compatible, first call in minutes, fast (about 0.5-3 s for small Nano/Super calls) | Reasoning tokens eat `max_tokens` silently; reasoning tokens not broken out in `usage`; inconsistent model ID spelling | Yes. It is the reason the whole pipeline is one client. |
| Token Factory Sandboxes | Build a package once, fork one sandbox per hypothesis, run untrusted PoCs offline, re-run on the fixed version | Fork model fits the "N hypotheses" idea exactly; 8 parallel forks of an installed package took 5-9 s each; `unshare -n` works | No cost on the run result; no per-run network switch; the first-contact docs sent me to a host that looked like "no permissions" | Yes. Build-once/fork is the core of the product. |
| NVIDIA Nemotron 3 (Nano, Super, Ultra) | Nano: extract and ground. Super: research synthesis, verdict and reply text. Ultra: hypothesis generation and ambiguous verdicts | Routing kept a full report at roughly one to five US cents of inference at the rates I assumed; Ultra proposes varied, sensible hypotheses | Structured output slips (see below); generated PoCs often call APIs that do not exist | Yes, with schema repair and a deterministic gate in code. |
| Tavily | Public advisory search from package, version and CVE/GHSA id only | One simple HTTPS call; fast enough for five queries per report | Generic queries return generic pages; I filter results for the package name | Yes. |
| AI Cloud (Serverless Endpoints / Jobs) | Not used | n/a | n/a | n/a. The rules say neither is required, and the app needs only a plain container host. |

## Nebius Token Factory: Sandboxes (`contree-sdk`)

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-10-12 | hands-on | **The same key showed two different permission pictures.** On 2026-09-30 a probe of `api.sandbox.nebius.ai` (`/v1/whoami`) returned 200 with every permission `false`, and I treated Sandboxes as blocked for twelve days. On 2026-10-12, `get_token_info()` through the SDK's default endpoint (`https://api.tokenfactory.nebius.com/sandboxes/`) returned `import, spawn, spawn_disposable, list, cancel, set_image_tag` all `true`. I cannot say whether the key changed or the two hosts report differently. | Put the one correct base URL and a `get_token_info()` hello-world at the top of the Sandboxes page, and make wrong or legacy hosts say so. |
| 2026-10-12 | hands-on | **Import then fork works, and it is fast.** Importing `docker.io/library/node:20` with `images.oci(...)` took about 30 s once. Each fork (write a PoC file, run it, run a probe) took 4.5-9 s with 8 forks in parallel. The 50-concurrent-instance limit from `get_token_info()` was never an issue. | None. Positive. |
| 2026-10-12 | hands-on | `unshare -n -- /bin/true` succeeds inside the microVM (as root), so PoC phases can run without network even though the run request has no network option. | Offer a first-class per-run `network: off`; an in-guest workaround is easy to get subtly wrong. |
| 2026-10-12 | hands-on | `image.run()` is disposable by default, and running on a disposable result fails with "Disposable image run cannot be used for running", which does not name `disposable` or say how to chain. | Name the parameter in the error, or document chaining (`disposable=False`) in the README example. |
| 2026-10-12 | hands-on | The run result (`ContreeImage`) exposes `stdout`, `stderr`, `exit_code`, `elapsed` and `uuid`, but no cost or resources. I could not report sandbox cost per report, which the hackathon budget planning needs. | Return cost or resource usage on every run result. |
| 2026-10-12 | hands-on | A bare tag such as `node:20` fails with a not-found error until the image has been imported; `images.oci("docker.io/library/node:20")` imports on first use and reuses afterwards. | Document `oci()` as the way to get a base image, and make the not-found error mention import. |
| 2026-09-30 | hands-on | `GET /v1/whoami` accepts any value in the `Project` header: my real project ID and two fake IDs returned the same 200 and permissions. A wrong project ID gives no early error. | Validate the project, or say it is only checked on real calls. |
| 2026-09-30 | hands-on | `whoami`'s `token_expiration` is a rolling value (5 minutes after each call), not the key's lifetime; the key kept working past it. The name suggests something the API does not mean. | Rename it, or add the real key expiry. |
| 2026-09-30 | read docs | The CLI and the SDK read different variable names for the project ID (`NEBIUS_AI_PROJECT` / `CONTREE_PROJECT` vs `NEBIUS_PROJECT_ID`). | Accept both in both. |
| 2026-09-29 | read source | Authentication needs both `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (the latter sent as a `Project` header); the error for a missing header is `400 Missing "Project" header`. | Say so on the getting-started page. |
| 2026-09-29 | read source | `disposable` defaults differ by layer: `run(...)` defaults to `True`, the raw `InstanceSpawnRequest` to `False`, the CLI to non-disposable, the MCP tool to disposable. | Align the defaults or label them. |

## Nebius Token Factory: inference

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-09-30 | hands-on | **Onboarding was fast.** With an API key, `GET /v1/models` and a first `chat/completions` call both worked immediately. The endpoint is OpenAI-compatible, so no new client was needed. | None. Positive. |
| 2026-10-12 | hands-on | Tool calling works (`scripts/spike_inference.py`): one tool call returned in about 0.9 s on Nano. | None. Positive. |
| 2026-09-30 | hands-on | Model IDs are inconsistent in case and separators: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`. Guessing an ID from a sibling fails; I first guessed the Ultra ID with the Nano prefix's capitalisation and got HTTP 404 ("model does not exist"). | Normalise IDs, or list the exact IDs in the quickstart. |
| 2026-09-30 | hands-on | Nano is a reasoning model. With `max_tokens=20` the call returned HTTP 200 with **empty `content`**: the whole budget went to hidden reasoning. | Return a clear finish reason or warning when reasoning exhausts the budget. |
| 2026-10-12 | hands-on | Reasoning tokens count against `max_tokens` on Ultra too: a 3000-token cap cut the hypothesis JSON in the middle of a string (`finish_reason: length`). I raised the cap to 9000 and keep a deterministic fallback when a draft is cut off. | Document that the cap covers reasoning plus answer. |
| 2026-09-30 | hands-on | `chat_template_kwargs: {"enable_thinking": false}` turns reasoning off (2 completion tokens vs 62, 0.75 s vs 1.40 s for the same one-word prompt). It works, but I found it by trying the vLLM convention. | Document the supported way to control reasoning. |
| 2026-09-30 | hands-on | `usage.completion_tokens_details` is `null`, so reasoning tokens are not broken out from answer tokens. | Populate `reasoning_tokens`. |
| 2026-10-12 | hands-on | I could not confirm per-model prices from the API; the cost figures in Mimi's dossiers use an assumed rate table and are labelled as such. | Return prices from `/models`, or link a price page from the response. |

## NVIDIA Nemotron 3 (Nano / Super / Ultra)

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-10-12 | hands-on | **Routing by stage works.** Nano for extraction and grounding (about 0.5-3 s), Super for research synthesis and verdict text (about 3 s), Ultra for hypotheses (about 30-60 s with reasoning). A full report cost roughly $0.01-0.05 of inference at my assumed rates across the 11-case E1 passes. | None. Positive. |
| 2026-10-12 | hands-on | **Structured output is mostly right and needs a validator.** Observed slips, all caught in code: Nano returned `vuln_class` as a list (it echoed the enum from the prompt); Ultra numbered script names (`node poc3.js`) against a fixed command allowlist, appended a package spec to an allowed install command, and wrapped an enum value in a list (`["marker_file"]`). In one eval case that produced zero usable hypotheses. | Prompt-side, "exactly ONE of" wording helped; a JSON-schema / constrained decoding option would remove the class of error. |
| 2026-10-12 | hands-on | **Ultra's proof-of-concept scripts often call APIs that do not exist** (`ansiRegex.strip is not a function`, `$.parseHTML is not a function` in a bare Node process). Early on these crashes looked like negative results. Giving the model the package's measured exports and one repair round roughly doubled how often an oracle fired (3/11 to 7/11 real CVEs; n=11, one run per case). | n/a (our side). It suggests PoC-writing benefits from tool access to the installed package. |
| 2026-10-12 | hands-on | Run-to-run variance is large: the same case changed tier between identical passes (only 2 of 11 real CVEs were Confirmed in all three). Temperature was low but sampling was not seeded. | A seed parameter would make evals reproducible. |
| 2026-10-12 | hands-on | I did not evaluate `Nemotron-3_5-Lightning`. | n/a |

## Tavily

| Date | Source | Observation | Suggested change |
|---|---|---|---|
| 2026-10-12 | hands-on | One HTTPS call with a bearer key; five queries per report finished in roughly 9 s total. Simple to integrate and easy to wrap with a leak guard that guarantees only public identifiers (package, version, CVE/GHSA id) are sent. | None. Positive. |
| 2026-10-12 | hands-on | A query like `minimist prototype pollution` returns many generic pages ("Pollution - Wikipedia", land and ocean pollution). Mimi now keeps only results that name the package or an advisory id and counts the dropped ones. | A domain or topic filter, or a security-advisory search mode, would remove this step. |
| 2026-10-12 | hands-on | Snippets are enough to find "fixed in X" phrases but were not reliable enough to extract a fixed version through a model (it varied run to run). Mimi now takes the fixed version from the public npm advisory database and uses Tavily results as evidence for the reader. | n/a |

## Nebius AI Cloud (Serverless Endpoints / Jobs)

Not used. The Rules call it encouraged but not required, and Mimi needs only a plain container host plus Token Factory runtime calls. If we deploy the hosted demo there later, this section gets entries.
