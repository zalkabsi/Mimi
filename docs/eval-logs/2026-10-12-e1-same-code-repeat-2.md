# Mimi eval report — suite e1 (pipeline, force_model=routed)

Generated: 2026-10-12T13:23:08.890931+00:00

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
- confirmed-with-differential rate: 2/11 = 18.2% (Wilson 95% CI 5.1–47.7%)
- Median wall time per case: 68.2 s
- Mean tokens in per case: 8380
- Mean inference cost per case: $0.0260 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Needs human | yes | 6 hypotheses, 1 configs, 6 triggered, versions: 5.0.0, 5.0.1 | 87.1 | 4716/3945 | $0.0114 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 108.7 | 18731/18571 | $0.0692 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 4.17.15, 4.17.19 | 50.1 | 7650/4762 | $0.0129 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered, versions: 4.17.20, 4.17.21 | 109.8 | 21690/23286 | $0.0829 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Needs human | yes | 8 hypotheses, 1 configs, 8 triggered, versions: 4.0.9, 4.0.10 | 88.9 | 7478/6114 | $0.0166 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Confirmed | yes | 8 hypotheses, 1 configs, 8 triggered, versions: 1.2.0, 1.2.3 | 97.5 | 5512/4868 | $0.0153 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Contradicted | no | 8 hypotheses, 1 configs, 0 triggered, versions: 1.2.5 | 39.2 | 4781/3534 | $0.0107 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Likely | yes | 6 hypotheses, 1 configs, 5 triggered, versions: 0.0.4 | 61.9 | 5079/7371 | $0.0235 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 3.0.0, 3.0.1 | 68.2 | 4957/3297 | $0.0100 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered, versions: 1.12.0 | 39.6 | 4741/4237 | $0.0122 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 7.4.5 | 59.7 | 6849/6079 | $0.0209 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
