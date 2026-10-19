import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, getReport, streamEvents } from "../lib/api";
import type {
  Dossier,
  Oracle,
  OracleResult,
  RunRecord,
  StageEvent,
} from "../types";
import {
  TIER_ACCENT,
  TierBadge,
} from "../components/TierBadge";
import {
  EmptyNote,
  FieldRow,
  Mono,
  SectionCard,
} from "../components/SectionCard";
import { Collapsible } from "../components/Collapsible";
import { CopyableText, PreBlock } from "../components/PreBlock";
import { Timeline } from "../components/Timeline";
import { ReferenceLink } from "../components/ReferenceLink";
import { dash, dashNum, fmtCost, fmtMs, fmtTokens, fmtTs } from "../lib/format";

type LoadState = "loading" | "ready" | "error";

export function ReportView() {
  const { reportId = "" } = useParams();
  return <ReportDetails key={reportId} reportId={reportId} />;
}

function ReportDetails({ reportId }: { reportId: string }) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [load, setLoad] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [fallbackNote, setFallbackNote] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const seen = useRef<Set<string>>(new Set());

  const onEvent = useCallback((ev: StageEvent) => {
    const key = `${ev.ts}|${ev.stage}|${ev.status}|${ev.detail}`;
    if (seen.current.has(key)) return;
    seen.current.add(key);
    setEvents((prev) => [...prev, ev]);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let streamCompleted = false;
    seen.current = new Set();
    setEvents([]);
    setLive(true);
    setFallbackNote(null);

    const stopStream = streamEvents(
      reportId,
      onEvent,
      (reason) => {
        if (!cancelled) setFallbackNote(reason);
      },
      () => {
        streamCompleted = true;
        void getReport(reportId)
          .then((d) => {
            if (cancelled) return;
            setDossier(d);
            setLoad("ready");
          })
          .catch(() => {
            if (!cancelled) {
              setFallbackNote("The run finished, but its final report could not be refreshed.");
            }
          })
          .finally(() => {
            if (!cancelled) setLive(false);
          });
      },
    );

    void (async () => {
      try {
        const d = await getReport(reportId);
        if (cancelled) return;
        // The completion callback may already have fetched the final dossier.
        // Never let this initial response overwrite that newer state.
        if (!streamCompleted) {
          setDossier(d);
          setLoad("ready");
        }
      } catch (e) {
        if (cancelled) return;
        stopStream();
        setLive(false);
        setLoadError(
          e instanceof ApiError && e.status === 404
            ? "No such report. It may have been deleted, or the id is wrong."
            : e instanceof ApiError
              ? e.message
              : "Failed to load the report.",
        );
        setLoad("error");
      }
    })();

    return () => {
      cancelled = true;
      stopStream();
      setLive(false);
    };
  }, [reportId, onEvent]);

  // Stop treating the timeline as live once the pipeline is done.
  const pipelineDone = useMemo(() => {
    if (!dossier) return false;
    return (
      dossier.events.some((e) => e.stage === "reply" && e.status === "ok") ||
      (dossier.tier !== "Needs human" && dossier.reply_draft !== "")
    );
  }, [dossier]);

  if (load === "loading" && !dossier) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-12 text-center">
        <p className="animate-pulse font-mono text-sm text-slate-400">
          Loading report {reportId}…
        </p>
      </div>
    );
  }

  if (load === "error" && !dossier) {
    return (
      <div className="space-y-4">
        <BackLink />
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-6">
          <h2 className="font-mono text-sm font-semibold text-rose-200">
            Report unavailable
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-rose-100/80">{dash(loadError)}</p>
          <p className="mt-3 max-w-2xl text-sm text-slate-300">
            Check that the backend is running and the report id is correct, or
            return to the{" "}
            <Link to="/" className="font-mono text-sky-300 underline underline-offset-2">
              inbox
            </Link>
            .
          </p>
        </div>
      </div>
    );
  }

  const d = dossier;
  if (!d) return null;

  const running = live && !pipelineDone;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink />
        <h1 className="font-mono text-lg font-semibold text-slate-100">
          {d.report_id}
        </h1>
        <TierBadge tier={d.tier} />
        <span className="font-mono text-xs text-slate-500">
          {dash(d.package_spec)} · source {dash(d.source)} · {fmtTs(d.created_at)}
        </span>
        <button
          type="button"
          onClick={() => downloadDossier(d)}
          className="ml-auto rounded border border-slate-700 px-3 py-1.5 font-mono text-xs text-sky-300 hover:bg-slate-800"
        >
          Download dossier
        </button>
        {running ? (
          <span className="inline-flex items-center gap-1.5 rounded border border-sky-500/40 bg-sky-500/10 px-2 py-0.5 font-mono text-[11px] text-sky-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-400" />
            pipeline running
          </span>
        ) : null}
      </div>

      {d.source === "demo" ? (
        <div className="rounded border border-amber-500/40 bg-amber-500/10 px-4 py-3">
          <p className="font-mono text-xs text-amber-200">
            Recorded sample dossier: its evidence and timeline are fixture data, not a live Mimi analysis.
          </p>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3">
        <Timeline
          events={events}
          live={live && running}
          fallbackNote={fallbackNote}
        />
      </div>

      <VerdictPanel d={d} />

      {d.claim ? (
        <SectionCard title="Claim summary" subtitle="What the report asserts, structured.">
          <dl className="divide-y divide-slate-800/60">
            <FieldRow label="package">
              <Mono>{dash(d.claim.package)}</Mono>
            </FieldRow>
            <FieldRow label="affected">
              {d.claim.affected_versions.length > 0 ? (
                <Mono>{d.claim.affected_versions.join(", ")}</Mono>
              ) : (
                <Dash />
              )}
            </FieldRow>
            <FieldRow label="class">
              <Mono>{dash(d.claim.vuln_class)}</Mono>
            </FieldRow>
            <FieldRow label="expected effect">
              {dash(d.claim.expected_effect)}
            </FieldRow>
            <FieldRow label="attack vector">
              {dash(d.claim.attack_vector)}
            </FieldRow>
            <FieldRow label="preconditions">
              {d.claim.preconditions.length > 0 ? (
                <ul className="list-inside list-disc space-y-0.5 text-sm text-slate-300">
                  {d.claim.preconditions.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              ) : (
                <Dash />
              )}
            </FieldRow>
            <FieldRow label="cited files">
              {d.claim.cited_files.length > 0 ? (
                <Mono>{d.claim.cited_files.join(", ")}</Mono>
              ) : (
                <Dash />
              )}
            </FieldRow>
            <FieldRow label="cited symbols">
              {d.claim.cited_symbols.length > 0 ? (
                <Mono>{d.claim.cited_symbols.join(", ")}</Mono>
              ) : (
                <Dash />
              )}
            </FieldRow>
            <FieldRow label="poc command">
              {d.claim.poc_command ? <Mono>{d.claim.poc_command}</Mono> : <Dash />}
            </FieldRow>
          </dl>
          {d.claim.poc_code ? (
            <div className="mt-3 space-y-2">
              <Collapsible label="reporter-supplied PoC code">
                <PreBlock text={d.claim.poc_code} label="poc (from report)" />
              </Collapsible>
            </div>
          ) : null}
          {d.claim.parse_warnings.length > 0 ? (
            <div className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              <p className="font-mono uppercase tracking-wider">parse warnings</p>
              <ul className="mt-1 list-inside list-disc">
                {d.claim.parse_warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {d.claim.notes ? (
            <p className="mt-3 text-xs text-slate-400">{d.claim.notes}</p>
          ) : null}
        </SectionCard>
      ) : (
        <SectionCard title="Claim summary">
          <EmptyNote text="No structured claim yet — the extract stage has not produced one (or it was not run)." />
        </SectionCard>
      )}

      <SectionCard
        title="Grounding evidence"
        subtitle="Cited files/symbols/versions checked against the installed package."
        footnote="Grounding is evidence only. It is never a basis to reject a report."
      >
        {d.grounding.length === 0 ? (
          <EmptyNote text="No grounding evidence recorded." />
        ) : (
          <ul className="space-y-2">
            {d.grounding.map((g, i) => (
              <li
                key={i}
                className="rounded border border-slate-800 bg-slate-950/50 px-3 py-2"
              >
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-300">
                    {g.kind}
                  </span>
                  <Mono>{dash(g.target)}</Mono>
                  {g.source_ref ? (
                    <span className="font-mono text-[11px] text-slate-500">
                      {g.source_ref}
                    </span>
                  ) : null}
                </div>
                {g.detail ? (
                  <p className="mt-1 text-xs text-slate-400">{g.detail}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Research"
        subtitle="Public identifiers only — report text is never sent to external search."
      >
        {d.research.used ? (
          <div className="space-y-4">
            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-slate-500">
                Queries sent
              </h3>
              {d.research.queries.length === 0 ? (
                <EmptyNote text="No queries recorded." />
              ) : (
                <ul className="mt-2 space-y-1">
                  {d.research.queries.map((q, i) => (
                    <li key={i} className="font-mono text-xs text-slate-300">
                      <span className="text-slate-600">›</span> {q}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-slate-500">
                Advisories found
              </h3>
              {d.research.known_advisories.length === 0 ? (
                <EmptyNote text="No advisories found for the public identifiers used." />
              ) : (
                <ul className="mt-2 space-y-2">
                  {d.research.known_advisories.map((a, i) => (
                    <li
                      key={i}
                      className="rounded border border-slate-800 bg-slate-950/50 px-3 py-2"
                    >
                      <p className="text-sm text-slate-200">{dash(a.title)}</p>
                      {a.url ? (
                        <div className="mt-1"><ReferenceLink url={a.url} /></div>
                      ) : null}
                      {a.snippet ? (
                        <p className="mt-1 text-xs text-slate-400">{a.snippet}</p>
                      ) : null}
                      {a.advisory_ids.length > 0 ? (
                        <p className="mt-1 font-mono text-[11px] text-slate-500">
                          ids: {a.advisory_ids.join(", ")}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <dl className="divide-y divide-slate-800/60 border-t border-slate-800 pt-2">
              <FieldRow label="fixed version">
                {d.research.fixed_version ? (
                  <Mono>{d.research.fixed_version}</Mono>
                ) : (
                  <Dash />
                )}
              </FieldRow>
              <FieldRow label="fix commit">
                {d.research.fix_commit ? <Mono>{d.research.fix_commit}</Mono> : <Dash />}
              </FieldRow>
              <FieldRow label="fix url">
                {d.research.fix_url ? (
                  <ReferenceLink url={d.research.fix_url} />
                ) : (
                  <Dash />
                )}
              </FieldRow>
            </dl>
            {d.research.notes ? (
              <p className="text-xs text-slate-400">{d.research.notes}</p>
            ) : null}
          </div>
        ) : (
          <EmptyNote text="Research was skipped (no search key configured). This is stated here rather than silently omitted." />
        )}
      </SectionCard>

      <SectionCard
        title="Hypotheses"
        subtitle="Each one has a declared oracle. The model does not grade what an oracle can grade."
      >
        {d.hypotheses.length === 0 ? (
          <EmptyNote text="No executable hypotheses were generated." />
        ) : (
          <ul className="space-y-3">
            {d.hypotheses.map((h) => (
              <li
                key={h.id}
                className="rounded border border-slate-800 bg-slate-950/50 px-3 py-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold text-sky-300">
                    {h.id}
                  </span>
                  <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                    priority {h.priority}
                  </span>
                  <span className="rounded border border-violet-500/40 bg-violet-500/10 px-1.5 py-0.5 font-mono text-[10px] text-violet-300">
                    oracle: {h.oracle.type}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{dash(h.rationale)}</p>
                <p className="mt-2 text-xs text-slate-400">
                  <span className="font-mono uppercase tracking-wider text-slate-500">
                    test plan:{" "}
                  </span>
                  {dash(h.test_plan)}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  <span className="font-mono uppercase tracking-wider text-slate-500">
                    oracle:{" "}
                  </span>
                  {dash(h.oracle.description) || dash(h.oracle.type)}
                </p>
                <div className="mt-2">
                  <Collapsible label={`harness code · ${h.id}`} badge={<HypothesisBadge />}>
                    <PreBlock text={h.poc_code} label="poc_code (generated)" />
                    <p className="mt-2 text-[11px] italic text-slate-500">
                      Executed only inside a sandbox. Node {dash(h.config.node_version)} ·
                      install: <span className="font-mono">{dash(h.config.install_command)}</span>
                    </p>
                  </Collapsible>
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Runs"
        subtitle="Exact commands and outputs. Collapsed by default; expand for stdout/stderr."
      >
        {d.runs.length === 0 ? (
          <EmptyNote text="No runs recorded. Either the build failed before any fork, Sandboxes grants are missing, or the pipeline stopped early." />
        ) : (
          <ul className="space-y-2">
            {d.runs.map((r, i) => (
              <RunRow key={i} run={r} />
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Oracle results"
        subtitle="Deterministic checks, fired or not fired. No LLM grading of reproduction."
      >
        {d.oracle_results.length === 0 ? (
          <EmptyNote text="No oracle results recorded." />
        ) : (
          <ul className="space-y-2">
            {d.oracle_results.map((o, i) => (
              <OracleRow key={i} result={o} />
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Differential"
        subtitle="Same oracle on the claimed-fixed version: did the result flip?"
      >
        <div className="space-y-3">
          <dl className="divide-y divide-slate-800/60">
            <FieldRow label="ran">{d.differential.ran ? "yes" : "no"}</FieldRow>
            <FieldRow label="fixed version">
              {d.differential.fixed_version ? (
                <Mono>{d.differential.fixed_version}</Mono>
              ) : (
                <Dash />
              )}
            </FieldRow>
            <FieldRow label="flipped">
              {d.differential.flipped === null || d.differential.flipped === undefined ? (
                <Dash />
              ) : d.differential.flipped ? (
                <span className="text-emerald-300">yes — fired on affected, not on fixed</span>
              ) : (
                <span className="text-slate-300">no</span>
              )}
            </FieldRow>
            <FieldRow label="detail">{dash(d.differential.detail)}</FieldRow>
          </dl>
          {d.differential.oracle_results.length > 0 ? (
            <ul className="space-y-2">
              {d.differential.oracle_results.map((o, i) => (
                <OracleRow key={i} result={o} />
              ))}
            </ul>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        title="Reply draft"
        subtitle="Drafted for a maintainer response. Edit before sending — it is a draft, not a decision."
      >
        {d.reply_draft ? (
          <CopyableText text={d.reply_draft}>
            <pre className="overflow-auto rounded border border-slate-800 bg-slate-950 px-3 py-3 font-mono text-xs leading-relaxed text-slate-300">
              {d.reply_draft}
            </pre>
          </CopyableText>
        ) : (
          <EmptyNote text="No reply draft yet — the pipeline has not reached the reply stage." />
        )}
      </SectionCard>

      <SectionCard
        title="Cost, tokens & limitations"
        subtitle="Numbers come from logged runs only. Missing values are shown as not measured."
      >
        <dl className="divide-y divide-slate-800/60">
          <FieldRow label="tokens in">
            <Mono>{fmtTokens(d.cost.inference_tokens_in)}</Mono>
          </FieldRow>
          <FieldRow label="tokens out">
            <Mono>{fmtTokens(d.cost.inference_tokens_out)}</Mono>
          </FieldRow>
          <FieldRow label="inference cost estimate">
            {d.cost.inference_cost_usd === null || d.cost.inference_cost_usd === undefined ? (
              <span className="text-slate-500">not measured</span>
            ) : (
              <Mono>{fmtCost(d.cost.inference_cost_usd, "USD")}</Mono>
            )}
          </FieldRow>
          <FieldRow label="sandbox cost">
            {d.cost.sandbox_cost === null || d.cost.sandbox_cost === undefined ? (
              <span className="text-slate-500">not measured</span>
            ) : (
              <Mono>{fmtCost(d.cost.sandbox_cost, d.cost.sandbox_cost_units)}</Mono>
            )}
          </FieldRow>
          <FieldRow label="elapsed">
            <Mono>{fmtMs(d.cost.elapsed_ms)}</Mono>
          </FieldRow>
          <FieldRow label="cost data complete">
            {d.cost.measured ? (
              "yes"
            ) : (
              <span className="text-slate-500">
                no — one or more usage or cost fields are missing; USD is price-table based and Sandbox values are raw units
              </span>
            )}
          </FieldRow>
        </dl>
        <div className="mt-4">
          <h3 className="font-mono text-xs uppercase tracking-wider text-slate-500">
            Limitations
          </h3>
          {d.limitations.length === 0 ? (
            <EmptyNote text="None recorded." />
          ) : (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-300">
              {d.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/"
      className="rounded border border-slate-700 px-2 py-1 font-mono text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200"
    >
      ← inbox
    </Link>
  );
}

function downloadDossier(dossier: Dossier) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(dossier, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `mimi-${dossier.report_id.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Dash() {
  return <span className="text-slate-600">—</span>;
}

function HypothesisBadge() {
  return (
    <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
      runs in sandbox
    </span>
  );
}

function VerdictPanel({ d }: { d: Dossier }) {
  const isContradicted = d.tier === "Contradicted";
  const isNeedsHuman = d.tier === "Needs human";
  return (
    <SectionCard
      title="Verdict"
      accent={`border-l-4 ${TIER_ACCENT[d.tier]}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <TierBadge tier={d.tier} />
        <span className="font-mono text-xs text-slate-500">
          tier assigned by the harness · never auto-closed
        </span>
      </div>

      {/* Coverage is the product's signature: prominent always, loudest for Contradicted. */}
      <div
        className={`mt-4 rounded border px-4 py-3 ${
          isContradicted
            ? "border-violet-500/50 bg-violet-500/10"
            : "border-slate-800 bg-slate-950/50"
        }`}
      >
        <h3 className="font-mono text-xs uppercase tracking-wider text-slate-400">
          Coverage
        </h3>
        <p
          className={`mt-1 font-mono ${
            isContradicted ? "text-xl text-violet-200" : "text-lg text-slate-200"
          }`}
        >
          {dash(d.coverage.statement) ||
            `${d.coverage.hypotheses_tested} hypotheses, ${d.coverage.configs_tested} configs, ${d.coverage.hypotheses_triggered} triggered`}
        </p>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="tested" value={dashNum(d.coverage.hypotheses_tested)} />
          <Stat label="planned" value={dashNum(d.coverage.hypotheses_total)} />
          <Stat label="triggered" value={dashNum(d.coverage.hypotheses_triggered)} />
          <Stat label="configs" value={dashNum(d.coverage.configs_tested)} />
        </div>
        {d.coverage.versions_tested.length > 0 ? (
          <p className="mt-2 font-mono text-[11px] text-slate-400">
            versions tested: {d.coverage.versions_tested.join(", ")}
          </p>
        ) : null}
      </div>

      <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-300">
        {dash(d.tier_rationale)}
      </p>

      {isNeedsHuman ? (
        <div className="mt-4 rounded border border-amber-500/40 bg-amber-500/10 px-4 py-3">
          <h3 className="font-mono text-sm font-semibold text-amber-200">
            Needs human — designed, not a dead end
          </h3>
          <p className="mt-2 text-sm text-amber-100/80">
            The harness could not reach an automated tier: the evidence is
            incomplete, the environment blocked execution, or the claim needs
            judgement a deterministic oracle cannot make. This is not a
            rejection and the report stays open. A maintainer should read the
            claim summary, grounding and any runs above, then decide.
          </p>
        </div>
      ) : null}

      {isContradicted ? (
        <p className="mt-3 text-xs italic text-slate-400">
          A negative result with stated coverage — not a rejection of the report,
          and never an auto-close.
        </p>
      ) : null}
    </SectionCard>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-950/60 px-2 py-1.5">
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="font-mono text-base text-slate-200">{value}</div>
    </div>
  );
}

function RunRow({ run }: { run: RunRecord }) {
  return (
    <li className="rounded border border-slate-800 bg-slate-950/50">
      <div className="flex flex-wrap items-center gap-2 px-3 py-2">
        <span className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-300">
          {run.phase}
        </span>
        <span className="font-mono text-xs text-slate-400">{run.hypothesis_id}</span>
        <span
          className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${
            run.exit_code === 0
              ? "border-emerald-500/40 text-emerald-300"
              : run.error
                ? "border-rose-500/40 text-rose-300"
                : "border-slate-700 text-slate-400"
          }`}
        >
          exit {dashNum(run.exit_code)}
        </span>
        {run.signal ? (
          <span className="rounded border border-rose-500/40 px-1.5 py-0.5 font-mono text-[10px] text-rose-300">
            signal {run.signal}
          </span>
        ) : null}
        {run.truncated ? (
          <span className="rounded border border-amber-500/40 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
            output truncated
          </span>
        ) : null}
        {run.network_isolated === true ? (
          <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
            network off
          </span>
        ) : run.network_isolated === false ? (
          <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
            network on
          </span>
        ) : null}
        <span className="ml-auto font-mono text-[11px] text-slate-500">
          {fmtMs(run.elapsed_ms)}
          {run.cost !== null && run.cost !== undefined
            ? ` · ${fmtCost(run.cost, run.cost_units)}`
            : ""}
        </span>
      </div>
      <div className="px-3 pb-1">
        <p className="break-all font-mono text-xs text-sky-200/90">
          <span className="text-slate-500">$ </span>
          {dash(run.command)}
        </p>
      </div>
      {run.error ? (
        <p className="px-3 pb-2 text-xs text-rose-300">{run.error}</p>
      ) : null}
      <div className="space-y-2 px-3 pb-3">
        <Collapsible label="stdout">
          <PreBlock text={run.stdout} label="stdout" emptyText="empty" />
        </Collapsible>
        <Collapsible label="stderr">
          <PreBlock text={run.stderr} label="stderr" emptyText="empty" />
        </Collapsible>
        {run.sandbox_run_id || run.sandbox_image_id ? (
          <p className="font-mono text-[10px] text-slate-600">
            image {dash(run.sandbox_image_id)} · run {dash(run.sandbox_run_id)}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function OracleRow({ result }: { result: OracleResult }) {
  const conclusive = result.conclusive === true;
  const label = conclusive ? (result.fired ? "fired" : "not fired") : "inconclusive";
  return (
    <li className="flex flex-wrap items-start gap-2 rounded border border-slate-800 bg-slate-950/50 px-3 py-2">
      <span
        className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${
          !conclusive
            ? "border-amber-500/50 bg-amber-500/10 text-amber-200"
            : result.fired
            ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
            : "border-slate-700 bg-slate-900 text-slate-400"
        }`}
      >
        {label}
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-mono text-xs text-slate-300">
          {result.hypothesis_id} · {result.phase} · {result.oracle.type}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          {result.detail || result.oracle.description || <Dash />}
        </p>
        <OracleSpec oracle={result.oracle} />
      </div>
    </li>
  );
}

function OracleSpec({ oracle }: { oracle: Oracle }) {
  const parts: string[] = [];
  if (oracle.expected_exit !== null && oracle.expected_exit !== undefined)
    parts.push(`expected exit ${oracle.expected_exit}`);
  if (oracle.expect_nonzero_exit) parts.push("expects nonzero exit");
  if (oracle.signal_name) parts.push(`signal ${oracle.signal_name}`);
  if (oracle.marker_path) parts.push(`marker ${oracle.marker_path}`);
  if (oracle.pattern) parts.push(`pattern /${oracle.pattern}/`);
  if (oracle.threshold_ms !== null && oracle.threshold_ms !== undefined)
    parts.push(`threshold ${fmtMs(oracle.threshold_ms)}`);
  if (oracle.expect_traversal_to) parts.push(`must NOT read ${oracle.expect_traversal_to}`);
  if (parts.length === 0) return null;
  return (
    <p className="mt-1 font-mono text-[10px] text-slate-500">{parts.join(" · ")}</p>
  );
}
