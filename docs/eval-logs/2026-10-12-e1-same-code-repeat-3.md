# Mimi eval report — suite e1 (pipeline, force_model=routed)

Generated: 2026-10-12T13:36:39.036929+00:00

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
- Median wall time per case: 67.8 s
- Mean tokens in per case: 7898
- Mean inference cost per case: $0.0231 (measured on 11/11 cases; prices from docs/01, flagged measured until invoice-verified)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Contradicted | no | 8 hypotheses, 1 configs, 0 triggered, versions: 5.0.0 | 63.3 | 10346/6677 | $0.0214 |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 103.9 | 23681/23153 | $0.0838 |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Confirmed | yes | 5 hypotheses, 1 configs, 4 triggered, versions: 4.17.15, 4.17.19 | 93.3 | 4405/4557 | $0.0137 |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 2 triggered, versions: 4.17.20, 4.17.21 | 63.1 | 7422/7131 | $0.0203 |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 1 triggered, versions: 4.0.9, 4.0.10 | 67.8 | 7902/6027 | $0.0169 |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 6 triggered, versions: 1.2.0, 1.2.3 | 84.2 | 5342/3299 | $0.0106 |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Needs human | yes | 8 hypotheses, 1 configs, 2 triggered, versions: 1.2.5, 1.2.6 | 62.2 | 4854/5048 | $0.0152 |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 0.0.4 | 51.1 | 4581/3610 | $0.0102 |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Confirmed | yes | 6 hypotheses, 1 configs, 3 triggered, versions: 3.0.0, 3.0.1 | 96.5 | 5259/5303 | $0.0169 |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Needs human | yes | 5 hypotheses, 1 configs, 2 triggered, versions: 1.12.0, 1.12.1 | 53.5 | 7798/4583 | $0.0125 |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Contradicted | no | 3 hypotheses, 1 configs, 0 triggered, versions: 7.4.5 | 70.5 | 5286/10662 | $0.0330 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
