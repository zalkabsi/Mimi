"""Pipeline orchestrator: report in → dossier out.

One report is one async job with bounded concurrency (no queue service).
Every stage emits structured events; the dossier is persisted to SQLite as
soon as it exists so the UI timeline can watch it.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from .config import Settings
from .db import Database
from .events import EventLog, now_iso
from .llm import LLMClient
from .sandboxes import Executor, RunBudget, SandboxExecutor, build_group_key
from .schemas import (
    CostSummary,
    DifferentialResult,
    Dossier,
    OracleResult,
    ReportSubmission,
    ResearchFindings,
    RunRecord,
    Tier,
)
from .stages.differential import run_differential
from .stages.execute import build_environments, run_hypotheses
from .stages.extract import extract_claim
from .stages.ground import ground_claim
from .stages.hypothesize import hypothesize
from .stages.research import research
from .stages.verdict import adjudicate, draft_reply
from .tavily_client import TavilyClient


class Pipeline:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        executor: Optional[Executor] = None,
        db: Optional[Database] = None,
        llm: Optional[LLMClient] = None,
        tavily: Optional[TavilyClient] = None,
        on_event=None,
    ):
        self.settings = settings or Settings.from_env()
        self.db = db
        self.executor = executor
        self._llm = llm
        self._tavily = tavily
        self.on_event = on_event

    def _db_event_sink(self, report_id: str):
        db = self.db
        if db is None:
            return self.on_event

        def sink(event: dict) -> None:
            try:
                db.add_event(report_id, event)
            except Exception:
                pass
            if self.on_event:
                self.on_event(event)

        return sink

    async def run(self, submission: ReportSubmission, *, source: str = "api", report_id: Optional[str] = None) -> Dossier:
        rid = report_id or uuid.uuid4().hex[:12]
        events = EventLog(rid, sink=self._db_event_sink(rid))
        dossier = Dossier(
            report_id=rid,
            created_at=now_iso(),
            source=source,  # type: ignore[arg-type]
            report_text=submission.report_text,
            package_spec=submission.package_spec,
        )
        if self.db is not None:
            self.db.upsert_report(dossier, status="running")

        llm = self._llm or LLMClient(self.settings, events=events)
        tavily = self._tavily
        if tavily is None and self.settings.tavily_api_key:
            tavily = TavilyClient(self.settings)
        executor = self.executor or SandboxExecutor(self.settings)

        build_failed = False
        stopped_reason = ""
        final_status = "complete"
        try:
            # --- stages 1-4: no sandbox needed -------------------------
            dossier.claim = extract_claim(submission, llm, events)
            dossier.grounding = ground_claim(submission, dossier.claim, events, llm=llm)
            dossier.public_ids, dossier.research = research(submission, dossier.claim, events, llm=llm, tavily=tavily)
            dossier.hypotheses = hypothesize(
                dossier.claim,
                dossier.grounding,
                dossier.research,
                llm,
                events,
                max_hypotheses=self.settings.max_hypotheses,
            )
            if not dossier.hypotheses:
                stopped_reason = "no executable hypotheses were generated"

            # --- stages 5-6: build per image config, fork hypotheses ---
            runs: list[RunRecord] = []
            oracle_results: list[OracleResult] = []
            # One allowance for the whole report: affected-phase forks and the
            # fixed-version differential re-runs share it, so the configured
            # max_runs_per_report is a real cap on untrusted executions. The
            # measured-cost threshold rides on the same budget. It is a
            # best-effort Contree-unit threshold, not a hard USD spending cap.
            budget = RunBudget(
                self.settings.max_runs_per_report,
                cost_cap=self.settings.per_report_cost_cap,
            )
            if dossier.hypotheses:
                builds = await build_environments(
                    submission, dossier.hypotheses, executor, self.settings, events, budget=budget
                )
                successful_builds = [b for b in builds.values() if b.ok]
                build_failed = bool(builds) and not successful_builds
                failed_count = len(builds) - len(successful_builds)
                all_build_groups = {build_group_key(h.config) for h in dossier.hypotheses}
                missing_count = len(all_build_groups - builds.keys())
                stop_reasons = []
                if failed_count:
                    stop_reasons.append(f"{failed_count} configuration build(s) failed")
                if missing_count:
                    stop_reasons.append(
                        f"{missing_count} configuration image(s) were skipped by the run/cost threshold"
                    )
                stopped_reason = "; ".join(stop_reasons)
                if successful_builds:
                    runs, oracle_results = await run_hypotheses(
                        dossier.hypotheses, builds, executor, self.settings, events, budget=budget
                    )
            dossier.runs = runs
            dossier.oracle_results = oracle_results

            # --- stage 7: differential --------------------------------
            if oracle_results and not build_failed:
                diff, fixed_runs = await run_differential(
                    submission,
                    dossier.hypotheses,
                    oracle_results,
                    dossier.research,
                    executor,
                    self.settings,
                    events,
                    budget=budget,
                )
                dossier.differential = diff
                # Fixed-phase oracle results index the fixed runs as 0..n-1;
                # rebase them onto Dossier.runs, where the affected runs come
                # first. A run_index that pointed at the wrong row would send
                # the UI to the wrong evidence.
                base = len(dossier.runs)
                dossier.runs.extend(fixed_runs)
                for i, r in enumerate(dossier.differential.oracle_results):
                    r.run_index = base + i
            else:
                dossier.differential = DifferentialResult(
                    ran=False, detail="skipped: nothing executed" if build_failed else "skipped: no oracle results"
                )

            # --- stages 8-9: verdict + reply --------------------------
            decision = adjudicate(
                submission,
                claim=dossier.claim,
                grounding=dossier.grounding,
                findings=dossier.research,
                hypotheses=dossier.hypotheses,
                oracle_results=dossier.oracle_results,
                differential=dossier.differential,
                runs=dossier.runs,
                build_failed=build_failed,
                stopped_reason=stopped_reason,
                llm=llm,
                events=events,
            )
            dossier.coverage = decision.coverage
            dossier.tier = decision.tier
            dossier.tier_rationale = decision.rationale

            try:
                dossier.reply_draft = draft_reply(
                    submission, dossier.claim, decision, dossier.research, llm, events
                )
            except Exception as e:
                dossier.reply_draft = f"(reply draft unavailable: {e})"

        except Exception as e:
            # A crash is not a verdict. Persist it as an error, hand back a
            # Needs human dossier, and never let the stored row claim "complete"
            # (that would read as "the pipeline finished and this is the answer").
            events.emit("pipeline", "error", f"pipeline stopped: {e}")
            dossier.tier = Tier.NEEDS_HUMAN
            dossier.tier_rationale = f"Pipeline stopped before a verdict: {e}"
            dossier.limitations.append(f"pipeline error: {type(e).__name__}")
            final_status = "error"
        except asyncio.CancelledError:
            # Cancellation is a BaseException: without this arm the finally
            # below would persist status="complete" for a run that never
            # reached a verdict. Persist the unfinished state, then re-raise.
            events.emit("pipeline", "error", "pipeline cancelled before a verdict")
            dossier.tier = Tier.NEEDS_HUMAN
            dossier.tier_rationale = "Pipeline was cancelled before a verdict"
            dossier.limitations.append("pipeline cancelled before a verdict")
            final_status = "error"
            raise
        finally:
            dossier.events = list(events.events)
            dossier.cost = self._cost_summary(dossier, wall_clock_ms=events.elapsed_ms)
            self._fill_limitations(dossier)
            if self.db is not None:
                try:
                    self.db.upsert_report(dossier, status=final_status)
                except Exception:
                    # Never let a storage failure mask the real outcome (and
                    # never let it replace a CancelledError in flight).
                    pass
            if tavily is not None and self._tavily is None:
                tavily.close()
            if self._llm is None:
                llm.close()
            if self.executor is None:
                try:
                    await executor.close()
                except Exception:
                    pass
        return dossier

    def _cost_summary(self, dossier: Dossier, *, wall_clock_ms: float = 0.0) -> CostSummary:
        tin = sum(e.tokens_in or 0 for e in dossier.events)
        tout = sum(e.tokens_out or 0 for e in dossier.events)
        sandbox_cost = [e.cost for e in dossier.events if e.cost is not None]
        # Price-table figures from docs/01 E12 are estimates, not invoice
        # amounts. Sandbox values remain raw Contree units without a verified
        # billing conversion; `measured` only reports telemetry completeness.
        prices = {
            "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06, 0.24),
            "nvidia/nemotron-3-super-120b-a12b": (0.30, 0.90),
            "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
        }
        cost = 0.0
        model_events = [e for e in dossier.events if e.model]
        complete_price_events = 0
        for e in model_events:
            p = prices.get(e.model)
            if p is None or e.tokens_in is None or e.tokens_out is None:
                continue
            complete_price_events += 1
            cost += (e.tokens_in / 1e6) * p[0] + (e.tokens_out / 1e6) * p[1]

        sandbox_events = [
            e for e in dossier.events
            if e.data.get("sandbox_operation") in {"build", "run"}
        ]
        sandbox_results = [e for e in sandbox_events if e.status in {"ok", "error"}]

        # Report a price-table estimate only when every model call has a listed
        # price and both token counts. Never use a partial sum as the run cost.
        if model_events and complete_price_events == len(model_events):
            inference_cost: Optional[float] = round(cost, 6)
        else:
            inference_cost = None

        return CostSummary(
            inference_tokens_in=tin,
            inference_tokens_out=tout,
            inference_cost_usd=inference_cost,
            sandbox_cost=sum(sandbox_cost) if sandbox_cost else None,
            sandbox_cost_units="contree-cost-units" if sandbox_cost else None,
            elapsed_ms=float(wall_clock_ms or 0.0),
            measured=bool(model_events or sandbox_events)
            and complete_price_events == len(model_events)
            and len(sandbox_results) == sum(e.status == "started" for e in sandbox_events)
            and all(e.cost is not None for e in sandbox_results),
        )

    @staticmethod
    def _fill_limitations(dossier: Dossier) -> None:
        if not dossier.research.used:
            dossier.limitations.append("Research (Tavily) was not available for this run.")
        probe_types = {
            "marker_file",
            "prototype_pollution_probe",
            "path_traversal_file_read",
            "network_call",
            "custom_probe",
        }
        probe_hypotheses = {
            h.id for h in dossier.hypotheses if h.oracle.type.value in probe_types
        }
        if probe_hypotheses and any(
            run.hypothesis_id in probe_hypotheses and not run.error
            for run in dossier.runs
        ):
            dossier.limitations.append(
                "Probe-style observations are collected in the same writable sandbox VM as the PoC. "
                "Hostile code could forge or alter them, so treat these results as supporting evidence and corroborate them manually."
            )
        if not dossier.differential.ran and dossier.tier in (Tier.CONTRADICTED, Tier.LIKELY):
            if "no fixed version" in (dossier.differential.detail or ""):
                dossier.limitations.append("No fixed version was known, so the differential is missing.")
        if dossier.differential.ran and dossier.differential.flipped is None:
            # The flip is unknown, not false. Say so in the panel a maintainer
            # reads for caveats, not only in the one-line tier rationale.
            dossier.limitations.append(
                "The fixed-version differential did not reach a judgment on every "
                "hypothesis that fired, so the flip is unconfirmed: "
                f"{dossier.differential.detail or 'no detail'}."
            )
        if any(getattr(r, "network_isolated", None) is False for r in dossier.runs):
            dossier.limitations.append(
                "At least one PoC run could not establish network isolation; that run was refused or is inconclusive."
            )
        if dossier.runs and all(r.cost is None for r in dossier.runs):
            dossier.limitations.append(
                "Sandbox run cost was not reported for these runs, so their "
                "contribution could not be counted against the best-effort "
                "Contree-unit threshold."
            )
