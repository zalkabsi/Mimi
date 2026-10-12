import type { EventStatus, StageEvent } from "../types";
import { dash, dashNum, fmtMs, fmtTs } from "../lib/format";

const STAGE_LABELS: Record<string, string> = {
  extract: "1 · Extract claim",
  ground: "2 · Grounding",
  research: "3 · Research",
  hypothesize: "4 · Hypothesize",
  build: "5 · Build base",
  fork_run: "6 · Fork & run",
  repair: "6b · Repair PoCs",
  differential: "7 · Differential",
  verdict: "8 · Verdict",
  reply: "9 · Reply draft",
  pipeline: "Pipeline",
};

const STATUS_STYLES: Record<EventStatus, string> = {
  started: "border-slate-600 bg-slate-800 text-slate-300",
  ok: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  error: "border-rose-500/50 bg-rose-500/10 text-rose-300",
  skipped: "border-slate-700 bg-slate-900 text-slate-500",
};

function eventKey(ev: StageEvent, index: number): string {
  return `${ev.ts}|${ev.stage}|${ev.status}|${ev.detail}|${index}`;
}

export function Timeline({
  events,
  live,
  fallbackNote,
}: {
  events: StageEvent[];
  live: boolean;
  fallbackNote: string | null;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h2 className="font-mono text-sm font-semibold tracking-wide text-slate-200">
          Stage timeline
        </h2>
        {live ? (
          <span className="inline-flex items-center gap-1.5 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            live
          </span>
        ) : (
          <span className="rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 font-mono text-[11px] text-slate-400">
            recorded
          </span>
        )}
        <span className="ml-auto font-mono text-[11px] text-slate-500">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </div>

      {fallbackNote ? (
        <p className="rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {fallbackNote}
        </p>
      ) : null}

      {events.length === 0 ? (
        <p className="rounded border border-dashed border-slate-800 bg-slate-950/40 px-3 py-4 text-center text-sm text-slate-500">
          No stage events recorded yet. Events appear here as the pipeline runs.
        </p>
      ) : (
        <ol className="space-y-1.5">
          {events.map((ev, i) => (
            <li
              key={eventKey(ev, i)}
              className="grid grid-cols-1 gap-1 rounded border border-slate-800 bg-slate-950/50 px-3 py-2 sm:grid-cols-12 sm:items-baseline sm:gap-3"
            >
              <div className="sm:col-span-3">
                <span className="font-mono text-xs text-slate-300">
                  {STAGE_LABELS[ev.stage] ?? ev.stage}
                </span>
              </div>
              <div className="sm:col-span-1">
                <span
                  className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${STATUS_STYLES[ev.status] ?? STATUS_STYLES.ok}`}
                >
                  {ev.status}
                </span>
              </div>
              <div className="min-w-0 sm:col-span-5">
                <p className="break-words text-xs text-slate-400">{dash(ev.detail)}</p>
              </div>
              <div className="font-mono text-[11px] text-slate-500 sm:col-span-3 sm:text-right">
                <div>{fmtTs(ev.ts)}</div>
                <div>
                  {fmtMs(ev.latency_ms)} · in {dashNum(ev.tokens_in)} · out{" "}
                  {dashNum(ev.tokens_out)}
                  {ev.model ? ` · ${ev.model}` : ""}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
