/** Display helpers. A missing value is never rendered as a made-up one. */

export const DASH = "—";

/** Em dash for null/undefined/empty; otherwise the string. */
export function dash(value: string | null | undefined): string {
  if (value === null || value === undefined) return DASH;
  const s = String(value).trim();
  return s === "" ? DASH : s;
}

/** Em dash for null/undefined numbers. */
export function dashNum(value: number | null | undefined): string {
  if (value === null || value === undefined) return DASH;
  return String(value);
}

export function fmtTokens(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  return n.toLocaleString("en-US");
}

export function fmtMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return DASH;
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const mins = Math.floor(ms / 60_000);
  const secs = Math.round((ms % 60_000) / 1000);
  return `${mins} min ${secs} s`;
}

/** ISO-8601 -> compact UTC display; falls back to the raw string. */
export function fmtTs(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");
}

export function fmtCost(
  value: number | null | undefined,
  units?: string | null,
): string {
  if (value === null || value === undefined) return "not measured";
  return units ? `${value} ${units}` : String(value);
}
