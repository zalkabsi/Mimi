"""Stage 6b — One repair round for PoCs that crashed before judging.

The first live eval (2026-10-12) showed most "not triggered" runs were not
negatives at all: the model's PoC called an API that does not exist
(``ansiRegex.strip is not a function``) and died before printing a verdict.
Those runs are inconclusive. This stage gives the model one look at the
package's real API surface plus each crash's stderr and reruns the fixed PoC.

Rules that keep it honest:
- Only hypotheses whose run crashed and whose oracle was inconclusive are
  touched. A PoC that ran to completion and did not fire is never "repaired"
  toward a positive.
- Repair edits ``poc_code`` only. Config and oracle stay as declared, so a
  repair cannot move the goalposts.
- The crashed run stays in ``runs``; the repaired run is added beside it.
- Repair runs draw from the same run budget.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional

from ..config import Settings, Stage
from ..events import EventLog
from ..llm import LLMClient
from ..oracles import check_oracle, crashed_with_exception
from ..probe import probe_env_for
from ..redaction import sanitize_package
from ..sandboxes import BuildResult, Executor, RunBudget
from ..schemas import Hypothesis, OracleResult, OracleType, RunConfig, RunRecord

_API_PROBE = r"""
const name = %NAME%;
try {
  const m = require(name);
  const out = { type: typeof m, keys: [], ownOnFunction: [] };
  if (m && (typeof m === 'object' || typeof m === 'function')) out.keys = Object.keys(m).slice(0, 40);
  if (typeof m === 'function') out.ownOnFunction = Object.getOwnPropertyNames(m).filter(k => !['length','name','prototype','caller','arguments'].includes(k)).slice(0, 40);
  const pj = require(name + '/package.json');
  out.version = pj.version; out.main = pj.main; out.exports = pj.exports ? Object.keys(pj.exports).slice(0, 10) : null;
  console.log('MIMI_API:' + JSON.stringify(out));
} catch (e) { console.log('MIMI_API_ERR:' + String(e.message).slice(0, 200)); }
"""

_HINT = json.dumps({"repairs": [{"id": "h1", "poc_code": "string"}]}, indent=2)

_PROMPT = """Some proof-of-concept scripts crashed before reaching their verdict line,
so they tested nothing. Fix ONLY the script bugs. Do not change what is being
tested, do not invent behaviour, and do not make a script print the success
marker unless the vulnerable behaviour really occurred.

Package: {package}
Real API surface of the installed package (measured, trust this over memory):
{api}

For each crashed script you get its code, its oracle pattern and the stderr.
Rules:
- Use only exports that appear in the API surface. If the package needs a
  browser or other global, set that up with built-in Node features only.
- Keep the same oracle: the script must still print the marker exactly when
  the vulnerable behaviour is observed.
- Under 25 lines each. Return corrected poc_code for every id.

{items}"""


def crashed_before_verdict(run: RunRecord) -> bool:
    return crashed_with_exception(run)


async def api_surface(
    build: BuildResult, config: RunConfig, package: str, executor: Executor, settings: Settings,
    budget: RunBudget,
) -> str:
    name = sanitize_package(package)
    if not name or not budget.take():
        return "(unavailable)"
    code = _API_PROBE.replace("%NAME%", json.dumps(name))
    try:
        run = await executor.run_poc(
            build, config, poc_code=code, hypothesis_id="_api",
            timeout_s=min(30, settings.poc_timeout_s), offline=True, phase="poc",
        )
    except Exception as e:  # an unavailable probe must not stop the pipeline
        return f"(unavailable: {e})"
    budget.charge(run.cost)
    m = re.search(r"MIMI_API:(.*)", run.stdout or "")
    return m.group(1)[:1500] if m else "(unavailable)"


async def repair_round(
    hypotheses: list[Hypothesis],
    runs: list[RunRecord],
    results: list[OracleResult],
    build: BuildResult,
    package: str,
    executor: Executor,
    llm: LLMClient,
    settings: Settings,
    events: EventLog,
    budget: RunBudget,
) -> tuple[list[RunRecord], list[OracleResult]]:
    by_id = {h.id: h for h in hypotheses}
    inconclusive = {r.hypothesis_id: r for r in results if not r.conclusive and r.phase == "affected"}
    targets: list[tuple[Hypothesis, RunRecord]] = []
    for hid, res in inconclusive.items():
        h = by_id.get(hid)
        if h is None or h.oracle.type is not OracleType.OUTPUT_REGEX:
            continue
        run = runs[res.run_index] if 0 <= res.run_index < len(runs) else None
        if run is not None and crashed_before_verdict(run):
            targets.append((h, run))
    if not targets:
        return runs, results

    t0 = events.start("repair", f"{len(targets)} PoC(s) crashed before judging; one repair round")
    api = await api_surface(build, targets[0][0].config, package, executor, settings, budget)
    items = "\n\n".join(
        f"id: {h.id}\noracle pattern: {h.oracle.pattern}\ncode:\n{h.poc_code}\nstderr:\n{(r.stderr or '')[:700]}"
        for h, r in targets
    )
    try:
        data = llm.chat_json(
            stage=Stage.HYPOTHESIZE,
            messages=[{"role": "user", "content": _PROMPT.format(package=package, api=api, items=items)}],
            schema_hint=_HINT,
            max_tokens=9000,
            enable_thinking=True,
            temperature=0.0,
        )
    except Exception as e:
        events.error("repair", t0, f"repair failed: {e}")
        return runs, results

    fixes = {
        str(x.get("id")): str(x.get("poc_code") or "").strip()
        for x in (data.get("repairs") or [])
        if isinstance(x, dict)
    }
    sem = asyncio.Semaphore(max(1, settings.max_parallel_forks))
    new_runs: list[RunRecord] = []
    new_results: list[OracleResult] = []

    async def one(h: Hypothesis) -> None:
        code = fixes.get(h.id)
        if not code or code == h.poc_code:
            return
        async with sem:
            if not budget.take():
                return
            run = await executor.run_poc(
                build, h.config, poc_code=code, hypothesis_id=h.id,
                timeout_s=settings.poc_timeout_s, offline=h.config.offline, phase="poc",
                probe_env=probe_env_for(h.oracle),
            )
            budget.charge(run.cost)
            run.phase = "poc"
            h.poc_code = code
            h.rationale = (h.rationale + " [PoC repaired once after a crash]").strip()
            new_runs.append(run)
            idx = len(runs) + len(new_runs) - 1
            new_results.append(
                check_oracle(h.oracle, run, hypothesis_id=h.id, phase="affected", run_index=idx)
            )

    await asyncio.gather(*(one(h) for h, _ in targets))
    repaired_ids = {r.hypothesis_id for r in new_results}
    # The crashed attempt is superseded for the same hypothesis; keep it in
    # runs as evidence but drop its inconclusive result so counts are per
    # hypothesis, not per attempt.
    kept = [r for r in results if r.hypothesis_id not in repaired_ids or r.conclusive]
    events.ok(
        "repair", t0,
        f"{len(new_results)} repaired and rerun; "
        f"{sum(1 for r in new_results if r.conclusive and r.fired)} fired, "
        f"{sum(1 for r in new_results if not r.conclusive)} still inconclusive",
    )
    return runs + new_runs, kept + new_results
