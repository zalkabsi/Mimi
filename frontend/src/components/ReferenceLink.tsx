/** Research is external evidence; only absolute HTTP(S) references are links. */
export function ReferenceLink({ url }: { url: string }) {
  let href: string | null = null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "https:" || parsed.protocol === "http:") href = parsed.href;
  } catch {
    // Preserve malformed provider output as text so it remains reviewable.
  }
  return href ? (
    <a href={href} target="_blank" rel="noreferrer" className="break-all font-mono text-xs text-sky-300 hover:underline">
      {url}
    </a>
  ) : (
    <span className="break-all font-mono text-xs text-slate-400">{url}</span>
  );
}
