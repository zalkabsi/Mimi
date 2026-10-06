import type { ReactNode } from "react";

export function SectionCard({
  title,
  subtitle,
  children,
  footnote,
  accent,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footnote?: string;
  accent?: string;
}) {
  return (
    <section
      className={`rounded-lg border border-slate-800 bg-slate-900/70 shadow-sm ${accent ?? ""}`}
    >
      <header className="border-b border-slate-800 px-4 py-3">
        <h2 className="font-mono text-sm font-semibold tracking-wide text-slate-200">
          {title}
        </h2>
        {subtitle ? (
          <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
        ) : null}
      </header>
      <div className="px-4 py-3">{children}</div>
      {footnote ? (
        <footer className="border-t border-slate-800/80 px-4 py-2 text-xs italic text-slate-500">
          {footnote}
        </footer>
      ) : null}
    </section>
  );
}

export function FieldRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 gap-1 py-1.5 sm:grid-cols-4 sm:gap-3">
      <dt className="font-mono text-xs uppercase tracking-wider text-slate-500">
        {label}
      </dt>
      <dd className="min-w-0 break-words text-sm text-slate-200 sm:col-span-3">
        {children}
      </dd>
    </div>
  );
}

export function EmptyNote({ text }: { text: string }) {
  return (
    <p className="rounded border border-dashed border-slate-800 bg-slate-950/40 px-3 py-2 text-sm text-slate-500">
      {text}
    </p>
  );
}

export function Mono({ children }: { children: ReactNode }) {
  return <span className="font-mono text-[13px] text-slate-300">{children}</span>;
}
