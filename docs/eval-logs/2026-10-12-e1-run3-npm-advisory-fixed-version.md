# Mimi eval report — suite e1 (pipeline, force_model=routed)

Generated: 2026-10-12T10:11:38.444196+00:00

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
- confirmed-with-differential rate: 3/11 = 27.3% (Wilson 95% CI 9.7–56.6%)
- Median wall time per case: 68.9 s
- Mean tokens in per case: 6736
- Mean inference cost per case: $0.0227 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 5.0.0 | 40.5 | 4651/5326 | $0.0155 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 71.4 | 6107/8090 | $0.0257 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Confirmed | yes | 5 hypotheses, 1 configs, 1 triggered, versions: 4.17.15, 4.17.19 | 41.5 | 4895/3345 | $0.0101 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Likely | yes | 3 hypotheses, 1 configs, 3 triggered, versions: 4.17.20, 4.17.21 | 102.0 | 17078/14239 | $0.0550 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 4.0.9 | 43.8 | 4544/4288 | $0.0121 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 6 triggered, versions: 1.2.0, 1.2.3 | 102.3 | 9021/7828 | $0.0232 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 1.2.5 | 38.8 | 4433/3399 | $0.0104 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Likely | yes | 6 hypotheses, 1 configs, 4 triggered, versions: 0.0.4 | 43.0 | 4536/3634 | $0.0113 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Confirmed | yes | 8 hypotheses, 1 configs, 1 triggered, versions: 3.0.0, 3.0.1 | 85.7 | 8089/10518 | $0.0343 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Needs human | yes | 8 hypotheses, 1 configs, 5 triggered, versions: 1.12.0, 1.12.1 | 108.6 | 5701/13616 | $0.0416 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 7.4.5, 7.4.6 | 68.9 | 5043/3388 | $0.0106 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
