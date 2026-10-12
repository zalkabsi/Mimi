# Mimi eval report — suite e2 (pipeline, force_model=routed)

Generated: 2026-10-12T14:09:40.797008+00:00

## Readiness

- NEBIUS_API_KEY set: True
- NEBIUS_PROJECT_ID set: True
- TAVILY_API_KEY set: True
- Sandboxes spawn permission: None

## Sample sizes

- Cases in suite: 10
- Completed: 10
- Errors: 0
- Not run: 0

Every proportion below is stated as k/n over **completed** cases only.

## E2 — Slop discrimination

- false-Contradicted rate on real reports (PRIMARY): 2/5 = 40.0% (Wilson 95% CI 11.8–76.9%)
- grounding-only gate false-Contradicted rate (baseline): 0/5 = 0.0% (Wilson 95% CI 0.0–43.4%)
- fabricated reaching Contradicted with coverage: 3/5 = 60.0% (Wilson 95% CI 23.1–88.2%)
- fabricated routed to Needs human: 2/5 = 40.0% (Wilson 95% CI 11.8–76.9%)

Baseline definition: the grounding-only gate contradicts a report whenever
grounding evidence is against the claim (version mismatch, cited file or symbol
absent). It never runs a PoC. This replicates the failure mode where grounding
alone rejects real vulnerabilities.

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e2-reworded-ansi-regex-3807 | real_reworded | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 5.0.0 | 57.2 | 5904/4976 | $0.0164 |
| e2-reworded-jquery-11023 | real_reworded | ok | Needs human | no | 2 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 97.7 | 22220/16928 | $0.0638 |
| e2-reworded-lodash-23337 | real_reworded | ok | Needs human | yes | 8 hypotheses, 1 configs, 8 triggered, versions: 4.17.20, 4.17.21 | 87.1 | 4579/3469 | $0.0108 |
| e2-reworded-minimist-44906 | real_reworded | ok | Contradicted | no | 8 hypotheses, 1 configs, 0 triggered, versions: 1.2.5 | 37.4 | 4568/3884 | $0.0120 |
| e2-reworded-node-serialize-5941 | real_reworded | ok | Likely | yes | 6 hypotheses, 1 configs, 1 triggered, versions: 0.0.4 | 38.5 | 7397/4780 | $0.0127 |
| e2-synth-chalk-pp-synthetic | synthetic_fabricated | ok | Contradicted | no | 8 hypotheses, 1 configs, 0 triggered, versions: 5.3.0 | 37.2 | 4585/3846 | $0.0123 |
| e2-synth-debug-traversal-synthetic | synthetic_fabricated | ok | Needs human | no | 0 hypotheses, 0 configs, 0 triggered | 18.8 | 4442/3811 | $0.0120 |
| e2-synth-is-even-rce-synthetic | synthetic_fabricated | ok | Contradicted | no | 5 hypotheses, 1 configs, 0 triggered, versions: 1.0.0 | 42.8 | 4487/4093 | $0.0128 |
| e2-synth-left-pad-redos-synthetic | synthetic_fabricated | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 1.3.0 | 56.6 | 4740/7029 | $0.0222 |
| e2-synth-ms-rce-synthetic | synthetic_fabricated | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered, versions: 2.1.3 | 48.9 | 4418/9170 | $0.0272 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
