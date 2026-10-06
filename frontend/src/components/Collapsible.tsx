import { useState, type ReactNode } from "react";

export function Collapsible({
  label,
  children,
  defaultOpen = false,
  badge,
}: {
  label: string;
  children: ReactNode;
  defaultOpen?: boolean;
  badge?: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded border border-slate-800 bg-slate-950/50">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-800/40"
      >
        <span className="font-mono text-xs text-slate-500">{open ? "▾" : "▸"}</span>
        <span className="flex-1 font-mono text-xs text-slate-300">{label}</span>
        {badge}
      </button>
      {open ? <div className="border-t border-slate-800 px-3 py-2">{children}</div> : null}
    </div>
  );
}
