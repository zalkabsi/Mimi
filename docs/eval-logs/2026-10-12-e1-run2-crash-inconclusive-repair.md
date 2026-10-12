# Mimi eval report — suite e1 (pipeline, force_model=routed)

Generated: 2026-10-12T09:58:00.665335+00:00

## Readiness

- NEBIUS_API_KEY set: True
- NEBIUS_PROJECT_ID set: True
- TAVILY_API_KEY set: True
- Sandboxes spawn permission: None

## Sample sizes

- Cases in suite: 11
- Completed: 11
- Errors: 0
- Not run: 0

Every proportion below is stated as k/n over **completed** cases only.

## E1 — Reproduction

- n completed (real_reproduction): 11
- reproduction rate (oracle fired): 7/11 = 63.6% (Wilson 95% CI 35.4–84.8%)
- confirmed-with-differential rate: 1/11 = 9.1% (Wilson 95% CI 1.6–37.7%)
- Median wall time per case: 41.5 s
- Mean tokens in per case: 6407
- Mean inference cost per case: $0.0196 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 5.0.0 | 60.2 | 5777/6513 | $0.0203 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 79.9 | 9182/15252 | $0.0456 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Likely | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 4.17.15 | 40.7 | 7486/5170 | $0.0141 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Needs human | no | 2 hypotheses, 1 configs, 0 triggered, versions: 4.17.20 | 38.1 | 7497/4834 | $0.0127 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Likely | yes | 8 hypotheses, 1 configs, 8 triggered, versions: 4.0.9 | 39.9 | 7279/5496 | $0.0149 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Needs human | yes | 8 hypotheses, 1 configs, 5 triggered, versions: 1.2.0, 1.2.2 | 63.5 | 5314/4388 | $0.0138 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 1.2.5, 1.2.6 | 41.5 | 4800/3605 | $0.0107 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Likely | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 0.0.4 | 33.6 | 4464/3348 | $0.0095 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 3.0.0 | 78.4 | 6465/14336 | $0.0446 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Likely | yes | 8 hypotheses, 1 configs, 3 triggered, versions: 1.12.0 | 39.4 | 7463/5271 | $0.0148 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Likely | yes | 6 hypotheses, 1 configs, 6 triggered, versions: 7.4.5 | 41.8 | 4750/4873 | $0.0152 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
