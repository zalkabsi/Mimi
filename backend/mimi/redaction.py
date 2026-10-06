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


def extract_public_ids(claim: Claim, report_text: str = "") -> PublicIdentifiers:
    """Deterministic ids from the claim (and advisory ids appearing anywhere
    in the report). No prose is copied."""
    advisories = sorted(set(_ADVISORY_RE.findall(report_text)))
    term = _CLASS_TERMS.get(claim.vuln_class.value, "")
    return PublicIdentifiers(
        package=claim.package,
        ecosystem=claim.ecosystem,
        versions=list(dict.fromkeys(claim.affected_versions)),
        advisory_ids=advisories,
        extra_terms=[term] if term else [],
    )


def build_queries(ids: PublicIdentifiers) -> list[str]:
    """Small fixed query set, built only from public identifiers.

    Each query is short and fully reconstructible from the ids — the
    redaction test asserts no free text can appear here.
    """
    queries: list[str] = []
    pkg = ids.package
    ver = ids.versions[0] if ids.versions else ""

    if ids.advisory_ids:
        queries.append(" ".join(ids.advisory_ids[:2]))
        queries.append(f"{pkg} {ids.advisory_ids[0]}")
    if ver:
        queries.append(f"{pkg} {ver} vulnerability")
        if len(ids.versions) > 1:
            queries.append(f"{pkg} {' '.join(ids.versions[:3])} security")
    else:
        queries.append(f"{pkg} vulnerability")
    if ids.extra_terms:
        queries.append(f"{pkg} {ids.extra_terms[0]}")
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


def assert_no_leak(query: str, report_text: str, min_run: int = 12) -> None:
    """Guard used by the research stage and the tests: any verbatim run of
    report prose (``min_run``+ chars) appearing in a query is a leak."""
    norm_q = " ".join(query.split()).lower()
    norm_r = " ".join(report_text.split()).lower()
    if not norm_r:
        return
    words = norm_r.split()
    for n in range(min_run, min(len(norm_r), 80) + 1):
        # sliding window on characters of the report, skipping tiny accidental hits
        for i in range(0, max(1, len(norm_r) - n + 1), max(1, n // 4)):
            frag = norm_r[i : i + n]
            if len(frag.split()) < 3:
                continue
            if frag in norm_q:
                raise AssertionError(f"report text leaked into Tavily query: {frag!r}")
    # also block long single words from the report (possible secrets/urls)
    for w in words:
        if len(w) >= 20 and w in norm_q:
            raise AssertionError(f"long report token leaked into query: {w!r}")
