# Mimi eval report — suite e1 (single_shot, force_model=routed)

Generated: 2026-10-12T13:38:42.124901+00:00

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
- confirmed-with-differential rate: 0/11 = 0.0% (Wilson 95% CI 0.0–25.9%)
- Median wall time per case: 11.2 s
- Mean tokens in per case: 336
- Cost per case: not run (no measured cost fields)

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e1-ansi-regex-redos-cve-2021-3807 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 10.6 | 331/289 | — |
| e1-jquery-xss-cve-2020-11022 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 11.4 | 360/515 | — |
| e1-lodash-pp-cve-2020-8203 | real_reproduction | ok | Needs human | no | 1 hypotheses, 1 configs, 0 triggered | 11.4 | 323/393 | — |
| e1-lodash-tpl-cve-2021-23337 | real_reproduction | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered | 11.7 | 363/369 | — |
| e1-marked-redos-cve-2022-21680 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 11.2 | 321/455 | — |
| e1-minimist-pp-cve-2020-7598 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 10.0 | 316/202 | — |
| e1-minimist-pp-cve-2021-44906 | real_reproduction | ok | Needs human | no | 1 hypotheses, 1 configs, 0 triggered | 10.4 | 303/247 | — |
| e1-node-serialize-rce-cve-2017-5941 | real_reproduction | ok | Needs human | no | 1 hypotheses, 1 configs, 0 triggered | 10.8 | 347/273 | — |
| e1-trim-newlines-redos-cve-2021-33623 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 12.4 | 323/301 | — |
| e1-underscore-tpl-cve-2021-23358 | real_reproduction | ok | Needs human | no | 1 hypotheses, 1 configs, 0 triggered | 11.5 | 339/475 | — |
| e1-ws-dos-cve-2021-32640 | real_reproduction | ok | Likely | yes | 1 hypotheses, 1 configs, 1 triggered | 11.0 | 366/446 | — |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
