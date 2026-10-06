import type { Tier } from "../types";

const STYLES: Record<Tier, string> = {
  Confirmed: "border-emerald-500/60 bg-emerald-500/15 text-emerald-300",
  Likely: "border-sky-500/60 bg-sky-500/15 text-sky-300",
  "Needs human": "border-amber-500/60 bg-amber-500/15 text-amber-300",
  Contradicted: "border-violet-500/60 bg-violet-500/15 text-violet-300",
};

export function TierBadge({ tier, size = "md" }: { tier: Tier | null; size?: "sm" | "md" }) {
  if (!tier) {
    return (
      <span className="inline-flex items-center rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 font-mono text-xs text-slate-400">
        unassigned
      </span>
    );
  }
  const pad = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";
  return (
    <span
      className={`inline-flex items-center rounded border font-mono ${pad} ${STYLES[tier]}`}
      title={`Triage tier: ${tier}. Mimi never auto-closes a report.`}
    >
      {tier}
    </span>
  );
}

/** Colored left-rail accent for a tier, used on the verdict panel. */
export const TIER_ACCENT: Record<Tier, string> = {
  Confirmed: "border-l-emerald-500",
  Likely: "border-l-sky-500",
  "Needs human": "border-l-amber-500",
  Contradicted: "border-l-violet-500",
};
