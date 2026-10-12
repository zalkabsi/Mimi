# Mimi eval report — suite e2 (pipeline, force_model=routed)

Generated: 2026-10-12T14:21:58.302191+00:00

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

- false-Contradicted rate on real reports (PRIMARY): 0/5 = 0.0% (Wilson 95% CI 0.0–43.4%)
- grounding-only gate false-Contradicted rate (baseline): 0/5 = 0.0% (Wilson 95% CI 0.0–43.4%)
- fabricated reaching Contradicted with coverage: 4/5 = 80.0% (Wilson 95% CI 37.6–96.4%)
- fabricated routed to Needs human: 0/5 = 0.0% (Wilson 95% CI 0.0–43.4%)

Baseline definition: the grounding-only gate contradicts a report whenever
grounding evidence is against the claim (version mismatch, cited file or symbol
absent). It never runs a PoC. This replicates the failure mode where grounding
alone rejects real vulnerabilities.

## Per-case results

| case id | kind | status | tier | oracle fired | coverage | wall s | tokens in/out | cost |
|---|---|---|---|---|---|---|---|---|
| e2-reworded-ansi-regex-3807 | real_reworded | ok | Needs human | yes | 5 hypotheses, 1 configs, 5 triggered, versions: 5.0.0, 5.0.1 | 67.2 | 4869/3460 | $0.0103 |
| e2-reworded-jquery-11023 | real_reworded | ok | Needs human | no | 0 hypotheses, 1 configs, 0 triggered, versions: 3.4.1 | 128.4 | 22915/29130 | $0.1010 |
| e2-reworded-lodash-23337 | real_reworded | ok | Needs human | yes | 6 hypotheses, 1 configs, 3 triggered, versions: 4.17.20, 4.17.21 | 63.7 | 7405/4636 | $0.0127 |
| e2-reworded-minimist-44906 | real_reworded | ok | Needs human | no | 6 hypotheses, 1 configs, 0 triggered, versions: 1.2.5 | 32.6 | 5004/3927 | $0.0111 |
| e2-reworded-node-serialize-5941 | real_reworded | ok | Needs human | no | 4 hypotheses, 1 configs, 0 triggered, versions: 0.0.4 | 35.7 | 4671/3357 | $0.0092 |
| e2-synth-chalk-pp-synthetic | synthetic_fabricated | ok | Contradicted | no | 6 hypotheses, 1 configs, 0 triggered, versions: 5.3.0 | 74.6 | 5205/11213 | $0.0350 |
| e2-synth-debug-traversal-synthetic | synthetic_fabricated | ok | Likely | yes | 5 hypotheses, 1 configs, 1 triggered, versions: 4.3.4 | 37.4 | 4250/3174 | $0.0102 |
| e2-synth-is-even-rce-synthetic | synthetic_fabricated | ok | Contradicted | no | 4 hypotheses, 1 configs, 0 triggered, versions: 1.0.0 | 40.9 | 4829/4253 | $0.0134 |
| e2-synth-left-pad-redos-synthetic | synthetic_fabricated | ok | Contradicted | no | 3 hypotheses, 1 configs, 0 triggered, versions: 1.3.0 | 85.7 | 15070/14061 | $0.0539 |
| e2-synth-ms-rce-synthetic | synthetic_fabricated | ok | Contradicted | no | 3 hypotheses, 1 configs, 0 triggered, versions: 2.1.3 | 56.6 | 14902/14610 | $0.0549 |

## Limits (state these publicly)

- SecBench.js is npm only — no other ecosystem is covered.
- Synthetic slop is not real slop: fabricated cases are published prompts, not naturally occurring bad reports.
- Results do not extend to C/C++ memory-safety reports.
- Every number in this report comes from a logged run; 'not run' cases are listed and excluded from denominators.
- The corpus uses already-public vulnerabilities only (demo and eval rule).
