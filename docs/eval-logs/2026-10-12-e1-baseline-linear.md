# Mimi eval report — suite e1 (linear, force_model=routed)

Generated: 2026-10-12T13:55:22.675785+00:00

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
- reproduction rate (oracle fired): 6/11 = 54.5% (Wilson 95% CI 28.0–78.7%)
- confirmed-with-differential rate: 1/11 = 9.1% (Wilson 95% CI 1.6–37.7%)
- Median wall time per case: 93.8 s
- Mean tokens in per case: 7448
- Mean inference cost per case: $0.0213 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Needs human | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 5.0.0, 5.0.1 | 102.9 | 6726/5467 | $0.0176 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Needs human | no | 1 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 111.8 | 19980/22562 | $0.0781 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 4.17.15 | 107.8 | 10028/7786 | $0.0243 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 4.17.20 | 65.9 | 7378/4591 | $0.0123 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Needs human | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 4.0.9, 4.0.10 | 93.8 | 5322/5632 | $0.0168 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 6 triggered, versions: 1.2.0, 1.2.3 | 102.5 | 7797/3961 | $0.0108 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 1.2.5 | 58.9 | 4714/3547 | $0.0105 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Contradicted | no | 7 hypotheses, 1 configs, 0 triggered, versions: 0.0.4 | 71.7 | 4650/4351 | $0.0128 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 3.0.0, 3.0.1 | 87.9 | 4713/3748 | $0.0108 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Needs human | yes | 8 hypotheses, 1 configs, 2 triggered, versions: 1.12.0, 1.12.1 | 104.5 | 5649/5930 | $0.0183 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Needs human | yes | 4 hypotheses, 1 configs, 4 triggered, versions: 7.4.5, 7.4.6 | 92.2 | 4966/7024 | $0.0217 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
