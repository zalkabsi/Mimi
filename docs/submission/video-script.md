# Demo video script (target 2:40, hard limit 3:00)

Rules (docs/00): text names only, no third-party logos, no music (or licensed), narration must name Nebius Token Factory, Token Factory Sandboxes and the Nemotron models by voice, footage must show the real project working. Pitch, not tutorial. Every number spoken must come from a logged run; items marked `[LOG]` get filled from `docs/eval-logs/` and the recorded run, or are cut.

| Time | On screen | Narration |
|---|---|---|
| 0:00-0:15 | Inbox with a pile of vulnerability reports (recorded demo mode) | "Open-source maintainers get vulnerability reports they cannot cheaply verify. Most get ignored or closed on a guess." |
| 0:15-0:35 | Submit the bundled public report for `minimist@1.2.5` (CVE-2021-44906) | "Mimi reproduces the claim in isolated Nebius Token Factory Sandboxes at the exact affected version, and never auto-closes. It returns a verdict with receipts." |
| 0:35-1:05 | Live stage timeline: extract (Nemotron Nano), research (Tavily, public identifiers only), hypotheses (Nemotron Ultra) | "Nemotron Nano reads the claim. Tavily looks up public advisories using only the package and version, never the report text. Nemotron Ultra writes up to eight hypotheses, each with a predeclared oracle." |
| 1:05-1:35 | Fork-run rows going green in parallel | "The environment is built once. Each hypothesis is a fork of that sandbox, run offline, in parallel. No secrets exist in any sandbox." |
| 1:35-2:00 | Differential on the fixed version; tier badge **Confirmed** | "Hypotheses that fire are re-run on the fixed version. It fires on 1.2.5 and not on 1.2.6, so: Confirmed, with the exact commands and outputs." |
| 2:00-2:25 | A real Contradicted or Needs-human dossier with the coverage statement; point at a crashed-PoC row marked inconclusive | "When it cannot reproduce, it says how hard it tried: N hypotheses tested, M triggered. A script that crashes is inconclusive, never a negative." `[LOG]` use only a recorded run. |
| 2:25-2:45 | Limits slide in plain text | "Today it covers npm only, and results vary between runs: [LOG sample sizes and spread]. Apache-2.0, open source, free for judges until December 15." |

Recording checklist: record from demo mode plus one live run; blur nothing needed (no keys in UI); no browser bookmarks bar; no logos; narration audio only.
