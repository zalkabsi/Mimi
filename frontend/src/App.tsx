import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { API_BASE, USE_MOCK, health } from "./lib/api";
import { InboxView } from "./views/InboxView";
import { ReportView } from "./views/ReportView";

type HealthState = "checking" | "up" | "down";

export function App() {
  const [healthState, setHealthState] = useState<HealthState>("checking");

  useEffect(() => {
    if (USE_MOCK) return;

    let cancelled = false;
    void (async () => {
      const ok = await health();
      if (!cancelled) setHealthState(ok ? "up" : "down");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 pb-16 pt-6 sm:px-6">
      <header className="mb-6">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          <Link to="/" className="group flex items-baseline gap-2">
            <span className="font-mono text-xl font-semibold tracking-tight text-slate-100 group-hover:text-white">
              Mimi
            </span>
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">
              report triage
            </span>
          </Link>
          <p className="max-w-xl text-xs text-slate-400">
            Every vulnerability report gets a verdict with receipts. Mimi never
            auto-closes a report.
          </p>
          <div className="ml-auto flex items-center gap-3">
            {USE_MOCK ? (
              <span
                className="font-mono text-[11px] uppercase tracking-wider text-amber-300"
                title="Fixed sample data; no backend connection is used."
              >
                read-only replay
              </span>
            ) : (
              <>
                <HealthDot state={healthState} />
                <span
                  className="font-mono text-[11px] text-slate-600"
                  title={`Backend base URL: ${API_BASE}`}
                >
                  {API_BASE.replace(/^https?:\/\//, "")}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="mt-3 h-px w-full bg-gradient-to-r from-slate-800 via-slate-700/60 to-transparent" />
      </header>

      {USE_MOCK ? (
        <div
          role="status"
          className="mb-6 rounded border border-amber-500/50 bg-amber-500/10 px-4 py-2.5"
        >
          <p className="font-mono text-xs text-amber-200">
            <span className="mr-2 rounded border border-amber-500/60 bg-amber-500/20 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
              read-only replay
            </span>
            Fixed sample data only. No provider calls or live analysis; report
            submissions and access keys are disabled.
          </p>
        </div>
      ) : null}

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<InboxView />} />
          <Route path="/reports/:reportId" element={<ReportView />} />
          <Route
            path="*"
            element={
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-10 text-center">
                <p className="font-mono text-sm text-slate-300">
                  Page not found.
                </p>
                <p className="mt-2 text-sm text-slate-500">
                  Return to the{" "}
                  <Link
                    to="/"
                    className="font-mono text-sky-300 underline underline-offset-2"
                  >
                    inbox
                  </Link>
                  .
                </p>
              </div>
            }
          />
        </Routes>
      </main>

      <footer className="mt-12 border-t border-slate-800 pt-4">
        <p className="font-mono text-[11px] leading-relaxed text-slate-600">
          Grounding is evidence only — never a rejection basis. Untrusted PoC
          code runs only inside sandboxes. External research uses public
          identifiers only. Report text is sent to Nebius Token Factory for
          inference; it is not sent to Tavily.
        </p>
      </footer>
    </div>
  );
}

function HealthDot({ state }: { state: HealthState }) {
  const meta =
    state === "up"
      ? { cls: "bg-emerald-400", label: "backend up" }
      : state === "down"
        ? { cls: "bg-rose-400", label: "backend unreachable" }
        : { cls: "bg-slate-500 animate-pulse", label: "checking backend" };
  return (
    <span
      className="inline-flex items-center gap-1.5 font-mono text-[11px] text-slate-500"
      title={meta.label}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.cls}`} />
      {meta.label}
    </span>
  );
}
