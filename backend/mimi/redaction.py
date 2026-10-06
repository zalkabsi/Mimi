"""Public-identifier extraction and Tavily query building.

Hard rule (docs/02-architecture.md): report text and PoC never leave the
system toward Tavily. Only package name, versions and advisory ids may be
queried. The functions here are deterministic so the redaction unit test can
prove it.
"""

from __future__ import annotations

import re

from .schemas import Claim, PublicIdentifiers

# CVE-YYYY-NNNN… and GHSA-xxxx-xxxx-xxxx
_ADVISORY_RE = re.compile(r"\b(CVE-\d{4}-\d{4,}|GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4})\b")

# Words we allow as extra search terms: vuln-class vocabulary only, not report prose.
_CLASS_TERMS = {
    "rce": "remote code execution",
    "xss": "cross site scripting",
    "path_traversal": "path traversal",
    "prototype_pollution": "prototype pollution",
    "redos": "regex denial of service",
    "sql_injection": "sql injection",
    "command_injection": "command injection",
    "auth_bypass": "auth bypass",
    "ssrf": "server side request forgery",
    "denial_of_service": "denial of service",
}

_MAX_QUERY_LEN = 400

# npm package name (optionally scoped) and a version-ish token. These are the
# only shapes allowed into a query. LLM free text that is not one of them is
# dropped at this boundary — never "cleaned up" into something that could still
# carry report prose.
_PACKAGE_RE = re.compile(r"^@?[A-Za-z0-9][A-Za-z0-9._-]{0,213}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,213})?$")
# Optional comparator, then semver-ish. Capped so a pasted sentence cannot ride along.
_VERSION_RE = re.compile(r"^[~^<>=\s]{0,3}v?\d{1,3}(?:\.\d{1,3}){0,3}(?:[-+][0-9A-Za-z.-]{0,24})?$")

# Fixed query vocabulary — the only non-identifier words a query may contain.
_QUERY_VOCAB = {
    "vulnerability",
    "security",
    "advisory",
    "fixed",
    "version",
    "cve",
    "ghsa",
}
# Multi-word class terms contribute each of their words to the vocabulary.
for _term in _CLASS_TERMS.values():
    _QUERY_VOCAB.update(_term.split())


def sanitize_package(name: str) -> str:
    """Keep only a syntactically valid npm package name; empty otherwise."""
    s = (name or "").strip()
    return s if _PACKAGE_RE.match(s) else ""


def sanitize_version(version: str) -> str:
    """Keep only a version-shaped token; empty otherwise.

    ``claim.affected_versions`` is model output and may hold report prose. The
    only safe move at the Tavily boundary is to drop anything that is not a
    version — never to paraphrase it into a new query term.
    """
    s = (version or "").strip()
    if len(s) > 40:
        return ""
    return s if _VERSION_RE.match(s) else ""


def extract_public_ids(claim: Claim, report_text: str = "") -> PublicIdentifiers:
    """Deterministic ids from the claim (and advisory ids appearing anywhere
    in the report). No prose is copied. Model-supplied package/versions are
    shape-checked and dropped when they are not identifiers."""
    advisories = sorted(set(_ADVISORY_RE.findall(report_text)))
    term = _CLASS_TERMS.get(claim.vuln_class.value, "")
    package = sanitize_package(claim.package)
    versions: list[str] = []
    for v in claim.affected_versions:
        sv = sanitize_version(v)
        if sv and sv not in versions:
            versions.append(sv)
    return PublicIdentifiers(
        package=package,
        ecosystem=claim.ecosystem,
        versions=versions,
        advisory_ids=advisories,
        extra_terms=[term] if term else [],
    )


def build_queries(ids: PublicIdentifiers) -> list[str]:
    """Small fixed query set, built only from public identifiers.

    Each query is short and fully reconstructible from the ids — the
    redaction test asserts no free text can appear here. Identifiers are
    shape-checked again here, so a hand-built PublicIdentifiers cannot smuggle
    prose past the extraction step.
    """
    queries: list[str] = []
    pkg = sanitize_package(ids.package)
    versions = [v for v in (sanitize_version(x) for x in ids.versions) if v]
    ver = versions[0] if versions else ""
    advisories = [a for a in ids.advisory_ids if _ADVISORY_RE.fullmatch(a or "")]
    terms = [t for t in ids.extra_terms if t in _CLASS_TERMS.values()]

    if advisories:
        queries.append(" ".join(advisories[:2]))
        if pkg:
            queries.append(f"{pkg} {advisories[0]}")
    if pkg and ver:
        queries.append(f"{pkg} {ver} vulnerability")
        if len(versions) > 1:
            queries.append(f"{pkg} {' '.join(versions[:3])} security")
    elif pkg:
        queries.append(f"{pkg} vulnerability")
    if pkg and terms:
        queries.append(f"{pkg} {terms[0]}")
    if pkg:
        queries.append(f"{pkg} security advisory fixed version")

    # De-dup, cap length and count.
    out: list[str] = []
    seen: set[str] = set()
    for q in queries:
        q = " ".join(q.split())[:_MAX_QUERY_LEN]
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:6]


def verify_query(query: str, ids: PublicIdentifiers) -> None:
    """Prove a query is reconstructible from public identifiers alone.

    Every token must be a package name, a version, an advisory id, or a word
    from the fixed vuln-class vocabulary. Anything else is a leak — this is a
    whitelist check, not a denylist, so unknown report prose cannot slip
    through a pattern the denylist forgot.
    """
    allowed: set[str] = set(_QUERY_VOCAB)
    if ids.package:
        allowed.add(ids.package.lower())
        allowed.add(ids.package.split("/")[-1].lower())
    for v in ids.versions:
        sv = sanitize_version(v)
        if sv:
            allowed.add(sv.lower())
            # "1.2.3" also contributes "1.2.3" after split on spaces; nothing else.
    for a in ids.advisory_ids:
        allowed.add(a.lower())
    for t in ids.extra_terms:
        allowed.update((t or "").lower().split())

    for token in (query or "").split():
        low = token.lower()
        if low in allowed:
            continue
        # Version-shaped tokens are fine even if the caller forgot to list them.
        if sanitize_version(token):
            continue
        if _ADVISORY_RE.fullmatch(token):
            continue
        raise AssertionError(f"query token {token!r} is not a public identifier: {query!r}")


def assert_no_leak(query: str, report_text: str, min_run: int = 12) -> None:
    """Guard used by the research stage and the tests: any verbatim run of
    report prose (``min_run``+ chars) appearing in a query is a leak."""
    norm_q = " ".join(query.split()).lower()
    norm_r = " ".join(report_text.split()).lower()
    if not norm_r:
        return
    words = norm_r.split()
    for n in range(min_run, min(len(norm_r), 80) + 1):
        # Sliding window on characters of the report. Step of 1 so a short
        # phrase cannot fall between samples (the old n//4 step skipped).
        for i in range(0, max(1, len(norm_r) - n + 1)):
            frag = norm_r[i : i + n]
            if len(frag.split()) < 3:
                continue
            if frag in norm_q:
                raise AssertionError(f"report text leaked into Tavily query: {frag!r}")
    # Long single words from the report (secrets, urls, tokens) — lower the bar
    # to 12 so a pasted API key or path is caught, not just 20+ char monsters.
    for w in words:
        if len(w) >= 12 and w.lower() in norm_q:
            raise AssertionError(f"long report token leaked into query: {w!r}")
        # Anything that looks like a secret or locator must never appear, even short.
        if re.search(r"(https?://|ghp_|sk-|xox[baprs]-|AKIA|-----BEGIN)", w) and w.lower() in norm_q:
            raise AssertionError(f"secret-like report token leaked into query: {w!r}")
