# Mimi eval report — suite e1 (pipeline, force_model=routed)

Generated: 2026-10-12T09:46:29.578258+00:00

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
- reproduction rate (oracle fired): 3/11 = 27.3% (Wilson 95% CI 9.7–56.6%)
- confirmed-with-differential rate: 2/11 = 18.2% (Wilson 95% CI 5.1–47.7%)
- Median wall time per case: 42.4 s
- Mean tokens in per case: 6014
- Mean inference cost per case: $0.0137 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 5.0.0 | 31.3 | 4300/3072 | $0.0092 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 51.3 | 7866/6470 | $0.0181 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 4.17.15, 4.17.20 | 42.4 | 4666/3358 | $0.0105 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Needs human | no | 0 hypotheses, 0 configs, 0 triggered | 21.2 | 4448/3602 | $0.0105 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Confirmed | yes | 5 hypotheses, 1 configs, 1 triggered, versions: 4.0.9, 4.0.10 | 74.4 | 4535/3225 | $0.0100 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Likely | yes | 8 hypotheses, 1 configs, 7 triggered, versions: 1.2.0 | 45.2 | 7849/5336 | $0.0152 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Needs human | no | 0 hypotheses, 0 configs, 0 triggered | 20.1 | 4429/3288 | $0.0092 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 0.0.4 | 36.8 | 7196/4926 | $0.0131 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 3.0.0 | 43.6 | 8380/8085 | $0.0231 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 1.12.0 | 34.7 | 7845/4268 | $0.0115 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 7.4.5 | 44.5 | 4644/6569 | $0.0200 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
