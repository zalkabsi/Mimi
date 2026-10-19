"""Public-identifier extraction and Tavily query building.

Hard rule (docs/02-architecture.md): report text and PoC are never sent to
Tavily. Only package names, versions and advisory ids may be queried. The
functions here are deterministic so the redaction unit test can prove it.
"""

from __future__ import annotations

import re

from .schemas import Claim, PublicIdentifiers

# CVE-YYYY-NNNN and GHSA-xxxx-xxxx-xxxx. The CVE tail is capped at 8 digits
# (real ids are 4-7) so a report cannot smuggle a 400-digit blob into a query
# as an "advisory id".
_ADVISORY_RE = re.compile(r"\b(CVE-\d{4}-\d{4,8}|GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4})\b")

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

# npm package name (optionally scoped with @scope/name) and a version-ish
# token. These are the only shapes allowed into a query. LLM free text that is
# not one of them is dropped at this boundary — never "cleaned up" into
# something that could still carry report prose. A slash form without the
# leading @ is refused: "example.com/steal" is not an npm name.
_PACKAGE_RE = re.compile(
    r"^(?:@[A-Za-z0-9][A-Za-z0-9._-]{0,213}/)?[A-Za-z0-9][A-Za-z0-9._-]{0,213}$"
)
# Optional comparator, then semver-ish. The prerelease/build suffix is capped
# at three short dot-separated identifiers — the shape real prereleases have
# ("1.2.3-beta.1", "2.0.0-rc.1", "1.0.0-20240101"). A blob suffix
# ("1.0.0-somesecrettoken") and a dotted sentence ("1.0.0-and.then.the.keys")
# are refused: both are valid semver and both are report prose in a version
# costume, and letting them through published their words as "version pieces",
# which disarmed the very prose-run check below.
_VERSION_RE = re.compile(
    r"^[~^<>=\s]{0,3}v?\d{1,3}(?:\.\d{1,3}){0,3}"
    r"(?:[-+][0-9A-Za-z]{1,12}(?:\.[0-9A-Za-z]{1,12}){0,2})?$"
)

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


# Zero-width and formatting characters a report could use to hide a phrase.
_ZERO_WIDTH = re.compile("​‌‍⁠﻿")
# Markdown/code fencing and quotes. Stripped before comparison so
# ```the keys` `` cannot hide from "the keys".
_MARKUP = re.compile(r"[`*~_\"'()\[\]{}<>|\\]")
# Separators folded to spaces, so "please-send-me" cannot hide from
# "please send me". Underscores fold too, for phrase matching; secret shapes
# like ``ghp_`` are checked on raw words before this runs.
_SEPARATORS = re.compile(r"[-_./+]+")
# Trailing sentence punctuation, stripped from raw words before the
# long/secret check. Keeps URLs and identifiers intact.
_EDGE_PUNCT = ".,;:!?\"'()[]{}<>"
_SECRET_RE = re.compile(r"(https?://|ghp_|sk-|xox[baprs]-|akia|-----begin)")


def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = _ZERO_WIDTH.sub("", t)
    t = _MARKUP.sub(" ", t)
    t = _SEPARATORS.sub(" ", t)
    return " ".join(t.split())


def _version_pieces(version: str) -> set[str]:
    """Public words of a version: its numeric core only.

    The prerelease/build suffix is shape-valid but arbitrary text
    (``1.0.0-and.then.the.keys``), and publishing its words would exempt the
    exact prose run this guard exists to catch. ``4.17.20`` -> ``{4, 17, 20}``.
    """
    core = re.split(r"[-+]", (version or "").lstrip("~^<>= \t"), maxsplit=1)[0]
    return set(_normalize(core).split())


def _public_words(query: str) -> tuple[set[str], set[str]]:
    """Two sets, for two different checks.

    ``phrase_public`` — words that may appear as *pieces* of a matched run:
    fixed vocabulary, plus the pieces of an advisory id and the numeric core
    of a version. Those are the shapes a report legitimately cites, so
    ``CVE-2021-44906`` or ``4.17.20`` on both sides is not a leak.

    ``whole_public`` — the complete identifier tokens the query may carry.
    The long-token check exempts only these (and spellings of them).

    Deliberately NOT "every token that appears in the query": report prose
    that made it into a query must not become exempt by being there, which is
    exactly how an earlier version of this guard stopped catching leaks.

    A package name is never expanded into pieces. npm names allow unlimited
    hyphens, so hyphen-joined prose (``please-send-me-the-keys``) has package
    shape; publishing its pieces would exempt the very run being checked. Only
    the whole token is public. Fixed vocabulary is not a package candidate:
    every English word matches the npm name shape, so ``node-serialize
    vulnerability`` must not read as two packages.
    """
    phrase_public: set[str] = set(_QUERY_VOCAB)
    whole_public: set[str] = set()
    package_like: list[str] = []
    for tok in (query or "").split():
        if _ADVISORY_RE.fullmatch(tok):
            phrase_public.update(_normalize(tok).split())
            whole_public.add(tok.lower())
        elif sanitize_version(tok):
            phrase_public.update(_version_pieces(tok))
            whole_public.add(tok.lower())
        elif tok.lower() in _QUERY_VOCAB:
            continue
        elif sanitize_package(tok):
            package_like.append(tok)
    if len(package_like) == 1:
        # The shape build_queries emits: at most one package per query.
        phrase_public.add(package_like[0].lower())
        whole_public.add(package_like[0].lower())
    return phrase_public, whole_public


def _identifier_spellings(whole_public: set[str]) -> set[str]:
    """Every spelling of a public identifier a report may reasonably use.

    Advisories routinely drop the ``@`` of a scoped package ("the bug in
    babel/traverse"), and the query still carries ``@babel/traverse``. That
    is the same identifier, not a leak — treat the ``@``-stripped form as a
    spelling of it. Bare ``name`` is deliberately NOT included: it is too
    ambiguous to claim.
    """
    out: set[str] = set(whole_public)
    for tok in whole_public:
        if tok.startswith("@") and "/" in tok:
            out.add(tok[1:])
    return out


def assert_no_leak(query: str, report_text: str, min_run: int = 12) -> None:
    """Guard used by the research stage and the tests.

    Fails when the query carries **report prose**. Checks, in order:

    1. Long report words (blobs, urls) present in the query, unless the word
       is fixed query vocabulary or itself a package name, version or advisory id.
    2. Secret-shaped report words present in the query — never exempt; a
       ``ghp_…`` token is not a public identifier.
    3. Runs of 2+ report words that appear in the query and contain at least
       one non-public word (see ``_public_words``).

    Checks 1-2 run on raw words, before separator folding, so ``ghp_abc123``
    and ``https://…`` are seen intact. ``min_run`` is the minimum phrase
    length in characters for check 3. Identifier runs are exempt via
    ``_public_words``, so citing an advisory in a report never disables
    research (that false positive used to fire silently).
    """
    if not (report_text or "").strip() or not (query or "").strip():
        return
    norm_q = _normalize(query)
    norm_r = _normalize(report_text)
    if not norm_r or not norm_q:
        return
    # Match complete normalized words: report code containing "minimist proto"
    # must not match the template phrase "minimist prototype pollution".
    padded_query = f" {norm_q} "

    q_low = (query or "").lower()
    phrase_public, whole_public = _public_words(query)
    spellings = _identifier_spellings(whole_public)

    def _is_identifier(raw: str) -> bool:
        """A report token that *is* a public identifier (or a spelling of one),
        not merely a piece of one."""
        return (
            raw.lower() in spellings
            or bool(_ADVISORY_RE.fullmatch(raw))
            or bool(sanitize_version(raw))
        )

    # Check 3 has to know raw-token boundaries. `_normalize` folds separators,
    # so the single report token ``node-serialize`` becomes the two words
    # ``node serialize`` — one identifier, not prose. Conversely five separate
    # report words that a query joined with hyphens really are prose. Judge a
    # window by the raw tokens it spans, not by its folded words alone.
    groups: list[tuple[str, list[str]]] = []
    for raw in (report_text or "").split():
        w = raw.strip(_EDGE_PUNCT)
        if not w:
            continue
        words = _normalize(w).split()
        if words:
            groups.append((w, words))
    flat: list[str] = []
    owner: list[int] = []
    for gi, (_, words) in enumerate(groups):
        for word in words:
            flat.append(word)
            owner.append(gi)

    for raw, _ in groups:
        if not raw.lower() in q_low:
            continue
        low = raw.lower()
        # 2: long blobs first — a pasted url is also secret-shaped, and the
        # long-token diagnostic is the more precise one. A long identifier is
        # exempt only when it *is* one of the query's public identifiers (or a
        # spelling of one). A piece of one is not: a blob smuggled as a version
        # suffix is not the version. Fixed vocabulary such as "vulnerability"
        # was chosen by the query template, even if the report uses it too.
        if len(raw) >= 12 and low not in _QUERY_VOCAB and not _is_identifier(raw):
            raise AssertionError(f"long report token leaked into query: {raw!r}")
        # 1: secrets of any length. Never exempt: ``ghp_…`` is not an
        # identifier, whatever shape it has.
        if _SECRET_RE.search(low):
            raise AssertionError(f"secret-like report token leaked into query: {raw!r}")

    # 3: multi-word prose runs.
    max_n = min(len(flat), 12)
    for n in range(2, max_n + 1):
        for i in range(0, len(flat) - n + 1):
            run_owners = set(owner[i : i + n])
            if all(_is_identifier(groups[g][0]) for g in run_owners):
                continue  # every raw token is a public identifier, not prose
            run = flat[i : i + n]
            if all(w in phrase_public for w in run):
                continue  # built from public identifier pieces and vocabulary
            phrase = " ".join(run)
            if len(phrase) < min_run:
                continue
            if f" {phrase} " in padded_query:
                raise AssertionError(f"report text leaked into Tavily query: {phrase!r}")
