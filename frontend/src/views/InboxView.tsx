import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, USE_MOCK, listReports, submitReport } from "../lib/api";
import type { ReportListItem } from "../types";
import { TierBadge } from "../components/TierBadge";
import { dash, fmtTs } from "../lib/format";

type LoadState = "loading" | "ready" | "error";

export function InboxView() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<ReportListItem[]>([]);
  const [load, setLoad] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);

  const [packageSpec, setPackageSpec] = useState("");
  const [reportText, setReportText] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [specError, setSpecError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoad("loading");
    setLoadError(null);
    try {
      const list = await listReports();
      setRows(list);
      setLoad("ready");
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : "Failed to load reports.");
      setLoad("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSpecError(null);

    const spec = packageSpec.trim();
    if (!spec.includes("@") || spec.split("@", 1)[0].trim() === "") {
      setSpecError("package_spec must look like package@version (e.g. lodash@4.17.19)");
      return;
    }
    if (reportText.trim() === "") {
      setSubmitError("Report text is required — paste the report body.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await submitReport(
        { report_text: reportText.trim(), package_spec: spec },
        accessKey,
      );
      navigate(`/reports/${res.report_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setSubmitError(
            "Demo mode is read-only. Enter the judge access key to run live reports, or self-host the backend and run without a key cap.",
          );
        } else if (err.status === 401) {
          setSubmitError("Unknown access key. Check the credential and try again.");
        } else {
          setSubmitError(err.message);
        }
      } else {
        setSubmitError("Submission failed.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70">
            <header className="border-b border-slate-800 px-4 py-3">
              <h2 className="font-mono text-sm font-semibold tracking-wide text-slate-200">
                Submit a report
              </h2>
              <p className="mt-1 text-xs text-slate-400">
                Triage only. Mimi never auto-closes a report — every submission
                ends in a tier with receipts.
              </p>
            </header>
            <form onSubmit={onSubmit} className="space-y-4 px-4 py-4">
              <div>
                <label
                  htmlFor="package-spec"
                  className="mb-1 block font-mono text-xs uppercase tracking-wider text-slate-500"
                >
                  package@version
                </label>
                <input
                  id="package-spec"
                  type="text"
                  value={packageSpec}
                  onChange={(e) => setPackageSpec(e.target.value)}
                  placeholder="lodash@4.17.19"
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
                />
                {specError ? (
                  <p className="mt-1 text-xs text-amber-300">{specError}</p>
                ) : null}
              </div>
              <div>
                <label
                  htmlFor="report-text"
                  className="mb-1 block font-mono text-xs uppercase tracking-wider text-slate-500"
                >
                  Report text
                </label>
                <textarea
                  id="report-text"
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                  rows={8}
                  placeholder="Paste the vulnerability report body. It never leaves the system toward external search — only public identifiers (package, versions, CVE/GHSA ids) do."
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm leading-relaxed text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
                />
              </div>
              <div>
                <label
                  htmlFor="access-key"
                  className="mb-1 block font-mono text-xs uppercase tracking-wider text-slate-500"
                >
                  Access key <span className="normal-case text-slate-600">(optional)</span>
                </label>
                <input
                  id="access-key"
                  type="password"
                  value={accessKey}
                  onChange={(e) => setAccessKey(e.target.value)}
                  autoComplete="off"
                  placeholder="judge credential, sent as X-Mimi-Key"
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
                />
              </div>

              {submitError ? (
                <div className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                  {submitError}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-sky-600 px-4 py-2 font-mono text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Submitting…" : "Run triage"}
              </button>
            </form>
          </div>
        </div>

        <aside className="lg:col-span-2">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-4">
            <h2 className="font-mono text-sm font-semibold tracking-wide text-slate-200">
              How tiers work
            </h2>
            <ul className="mt-3 space-y-3 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <TierBadge tier="Confirmed" size="sm" />
                <span>Reproduced on the claimed version, with an oracle firing.</span>
              </li>
              <li className="flex items-start gap-2">
                <TierBadge tier="Likely" size="sm" />
                <span>Consistent with the claim, but evidence is partial.</span>
              </li>
              <li className="flex items-start gap-2">
                <TierBadge tier="Needs human" size="sm" />
                <span>
                  The harness could not decide. Not a rejection — a person needs
                  to look.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <TierBadge tier="Contradicted" size="sm" />
                <span>
                  Negative result with coverage stated: N hypotheses tested, K
                  triggered.
                </span>
              </li>
            </ul>
            <p className="mt-4 border-t border-slate-800 pt-3 text-xs italic text-slate-500">
              Grounding alone never rejects a report. Untrusted PoC code runs
              only inside sandboxes.
            </p>
          </div>
        </aside>
      </section>

      <section>
        <div className="mb-3 flex items-center gap-3">
          <h2 className="font-mono text-sm font-semibold tracking-wide text-slate-200">
            Inbox
          </h2>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded border border-slate-700 px-2 py-0.5 font-mono text-[11px] text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            refresh
          </button>
          <span className="ml-auto font-mono text-[11px] text-slate-500">
            {load === "ready" ? `${rows.length} report${rows.length === 1 ? "" : "s"}` : ""}
          </span>
        </div>

        {load === "loading" ? (
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-8 text-center">
            <p className="animate-pulse font-mono text-sm text-slate-400">
              Loading reports…
            </p>
          </div>
        ) : null}

        {load === "error" ? (
          <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-6">
            <h3 className="font-mono text-sm font-semibold text-rose-200">
              Inbox unreachable
            </h3>
            <p className="mt-2 max-w-2xl text-sm text-rose-100/80">{dash(loadError)}</p>
            <p className="mt-3 max-w-2xl text-sm text-slate-300">
              Start the backend from <span className="font-mono text-slate-100">backend/</span>{" "}
              (<span className="font-mono text-slate-100">
                uvicorn mimi.api:app --reload --port 8000
              </span>
              ), point the UI at it with{" "}
              <span className="font-mono text-slate-100">VITE_API_BASE</span>, or develop
              offline with <span className="font-mono text-slate-100">VITE_USE_MOCK=1</span>.
            </p>
            <button
              type="button"
              onClick={() => void refresh()}
              className="mt-4 rounded border border-rose-400/50 px-3 py-1.5 font-mono text-xs text-rose-100 hover:bg-rose-500/20"
            >
              Retry
            </button>
          </div>
        ) : null}

        {load === "ready" && rows.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-800 bg-slate-900/40 px-4 py-10 text-center">
            <p className="font-mono text-sm text-slate-300">Inbox is empty.</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              No reports have been triaged yet. Submit one above — demo mode is
              read-only, so a judge credential or a self-hosted backend is
              needed for live runs.
            </p>
          </div>
        ) : null}

        {load === "ready" && rows.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80 font-mono text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-2.5 font-medium">Report</th>
                  <th className="px-4 py-2.5 font-medium">Package</th>
                  <th className="px-4 py-2.5 font-medium">Tier</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => navigate(`/reports/${r.id}`)}
                    className="cursor-pointer border-b border-slate-800/70 bg-slate-950/40 hover:bg-slate-800/50"
                  >
                    <td className="px-4 py-2.5 font-mono text-sm text-sky-300">
                      {r.id}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-sm text-slate-300">
                      {dash(r.package_spec)}
                    </td>
                    <td className="px-4 py-2.5">
                      <TierBadge tier={r.tier} size="sm" />
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusChip status={r.status} />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                      {fmtTs(r.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {USE_MOCK ? (
          <p className="mt-3 font-mono text-[11px] text-amber-300/80">
            Mock mode: the inbox lists the fixture dossier only. Submissions are
            disabled.
          </p>
        ) : null}
      </section>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const style =
    status === "running"
      ? "border-sky-500/50 bg-sky-500/10 text-sky-300"
      : status === "error"
        ? "border-rose-500/50 bg-rose-500/10 text-rose-300"
        : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[11px] ${style}`}>
      {status}
    </span>
  );
}
