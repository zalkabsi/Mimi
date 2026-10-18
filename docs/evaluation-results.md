# Evaluation results — 2026-10-18

These are exploratory live runs of the isolated checkout based on `e404cdd` and
the submission patch summarized here. They cover public npm cases only. They do not establish
production accuracy, general slop detection, or provider-level sandbox isolation.
The detailed reports are in [`docs/evaluations/`](evaluations/). Raw event JSON is
not bundled here because it contains model-generated PoC code; rerun the suites to
regenerate it under the ignored `evals/out/` directory.

## Summary

| Evaluation | Completed | Result |
|---|---:|---|
| E1 — routed reproduction | 11/11 | Oracle fired on 4/11; fixed-version differential confirmed 0/11 (95% Wilson interval 0–25.9%). |
| E2 — real and fabricated reports | 10/10 | False Contradicted on real reports: 0/5 (0–43.4%). Fabricated reports reaching Contradicted: 0/5 (0–43.4%); all 5/5 went to Needs human (56.6–100%). |
| E3 — model routing | 5/5 per setting | Expected-tier accuracy was 5/5 for routed, Ultra, and Super (each 56.6–100%) on the same five real cases. Median time: 34.4s, 74.3s, and 18.9s respectively. |
| E4 — scripted safety | 6 cases | Five cases with complete checks passed. The path-escape case's `no_traversal_read` check was `not_run`, so that check provides no safety evidence. |

## Interpretation

E1's 0/11 confirmed differential reproductions is below the project's earlier
5-of-10 numerical pilot target. The original criterion specified Ultra with
unrestricted retries; this E1 run was routed, and the all-Ultra comparison covered
only five cases, so that exact criterion was not fully tested. The corpus is still
far short of the planned 60–100 cases, and the confidence interval is wide. Do not
present this as a general reproduction rate.

E2 did not distinguish the five fabricated reports from the five real reports:
none was contradicted, and all fabricated reports were routed to Needs human.
That is cautious behavior, not useful slop discrimination. All 10 runs completed;
four of five real reports and three of five synthetic reports produced at least one
hypothesis. The others stopped with no executable hypotheses and remained for
human review. npm grounding resolved package versions to published tarball URLs,
but Tavily returned HTTP 432 usage-limit errors for every query, so the run had no
advisory results or fixed-version data. This further limits what the E2 results show.

The initial E2 run exposed six hypothesis responses cut off at the provider's
output-token limit. After the adaptive retry fix, the final 10-case rerun completed
without pipeline errors. A separate read-only `mimi whoami` check after that run
returned `ok: true` with all six Sandboxes permissions enabled; provider-level
hostile-code isolation remains unverified.

E3 measures whether a run's tier falls inside the case's allowed expected tiers;
it is not a reproduction-accuracy metric. Five cases per setting are too few to
claim a model-quality or cost advantage. E4 covers application-level scripted
checks. It does not verify hostile-code containment at the provider's microVM
boundary. One path traversal check was inconclusive.

The dataset is npm-only, includes already-public vulnerability cases, and uses
synthetic fabricated reports rather than naturally occurring slop. No results
generalize to other ecosystems or C/C++ memory-safety bugs. Sandbox billing units
are not converted to an invoice-verified total.

## Detailed run reports

- [E1 routed reproduction](evaluations/e1-routed-2026-10-18.md)
- [E2 routed slop discrimination](evaluations/e2-routed-2026-10-18.md)
- [E3 routed arm](evaluations/e3-routed-5-2026-10-18.md)
- [E3 Ultra arm](evaluations/e3-ultra-5-2026-10-18.md)
- [E3 Super arm](evaluations/e3-super-5-2026-10-18.md)
- [E3 comparison](evaluations/e3-comparison-5-2026-10-18.md)
- [E4 safety checks](evaluations/e4-safety-2026-10-18.md)
