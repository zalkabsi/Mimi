import { useState, type ReactNode } from "react";

export function PreBlock({
  text,
  label,
  maxHeight = "16rem",
  emptyText = "—",
}: {
  text: string | null | undefined;
  label?: string;
  maxHeight?: string;
  emptyText?: string;
}) {
  const [copied, setCopied] = useState(false);
  const value = text ?? "";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="rounded border border-slate-800 bg-slate-950">
      <div className="flex items-center justify-between border-b border-slate-800 px-2 py-1">
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-500">
          {label ?? "output"}
        </span>
        <button
          type="button"
          onClick={() => void copy()}
          disabled={value === ""}
          className="rounded px-2 py-0.5 font-mono text-[11px] text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      {value === "" ? (
        <p className="px-3 py-2 font-mono text-xs text-slate-600">{emptyText}</p>
      ) : (
        <pre
          className="overflow-auto px-3 py-2 font-mono text-xs leading-relaxed text-slate-300"
          style={{ maxHeight }}
        >
          {value}
        </pre>
      )}
    </div>
  );
}

export function CopyableText({ text, children }: { text: string; children?: ReactNode }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => void copy()}
        className="absolute right-2 top-2 rounded border border-slate-700 bg-slate-800/80 px-2 py-0.5 font-mono text-[11px] text-slate-300 hover:bg-slate-700"
      >
        {copied ? "copied" : "copy"}
      </button>
      {children}
    </div>
  );
}
