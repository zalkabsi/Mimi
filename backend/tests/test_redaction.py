"""Redaction safety: only public identifiers may reach a Tavily query.

Product rule (docs/02-architecture.md): report prose and PoC code never leave
the system. These tests pin ``extract_public_ids`` / ``build_queries`` /
``assert_no_leak`` to that rule.
"""

from __future__ import annotations

import pytest

from mimi.redaction import (
    assert_no_leak,
    build_queries,
    extract_public_ids,
    sanitize_package,
    sanitize_version,
    verify_query,
)
from mimi.schemas import Claim, PublicIdentifiers, VulnClass

REPORT = (
    "The attacker can smuggle arbitrary commands through the merge helper "
    "function when the target object contains a crafted constructor payload. "
    "See https://evil.example.com/aaaaaaaaaaaa for a full write-up."
)


def _claim(**kw) -> Claim:
    base = dict(
        package="lodash",
        affected_versions=["4.17.20"],
        vuln_class=VulnClass.PROTOTYPE_POLLUTION,
        expected_effect="Object.prototype gains an attacker-controlled property",
    )
    base.update(kw)
    return Claim(**base)


# ---------------------------------------------------------------------------
# build_queries uses only public identifiers
# ---------------------------------------------------------------------------

def test_build_queries_uses_only_public_identifiers():
    ids = PublicIdentifiers(
        package="lodash",
        versions=["4.17.20"],
        advisory_ids=["CVE-2021-23337"],
        extra_terms=["prototype pollution"],
    )
    queries = build_queries(ids)
    assert queries
    allowed_words = {
        "lodash", "4.17.20", "cve-2021-23337", "prototype", "pollution",
        "vulnerability", "security", "advisory", "fixed", "version",
    }
    for q in queries:
        for word in q.lower().split():
            assert word in allowed_words, f"non-identifier token in query: {word!r} ({q!r})"


def test_build_queries_never_contains_report_prose():
    claim = _claim()
    ids = extract_public_ids(claim, REPORT)
    queries = build_queries(ids)
    assert queries
    for q in queries:
        assert_no_leak(q, REPORT)  # raises on any verbatim prose run
        for bad in ("attacker", "smuggle", "payload", "write-up", "crafted"):
            assert bad not in q.lower()


def test_queries_are_reconstructible_from_ids():
    ids = PublicIdentifiers(
        package="minimist",
        versions=["1.2.0", "1.2.5"],
        advisory_ids=["GHSA-35jh-r3h4-6jhm"],
        extra_terms=["prototype pollution"],
    )
    queries = build_queries(ids)
    for q in queries:
        tokens = q.split()
        allowed = {"minimist", "1.2.0", "1.2.5", "GHSA-35jh-r3h4-6jhm", "prototype",
                   "pollution", "vulnerability", "security", "advisory", "fixed", "version"}
        assert set(tokens) <= allowed


# ---------------------------------------------------------------------------
# assert_no_leak: report prose and long tokens
# ---------------------------------------------------------------------------

def test_assert_no_leak_raises_on_report_prose_run():
    # A query carrying a verbatim run of report prose is a leak.
    leaky = "lodash the attacker can smuggle arbitrary commands through vulnerability"
    with pytest.raises(AssertionError, match="report text leaked"):
        assert_no_leak(leaky, REPORT)


def test_assert_no_leak_raises_on_full_sentence():
    leaky = "lodash " + REPORT.split(".")[0] + " vulnerability"
    with pytest.raises(AssertionError, match="report text leaked"):
        assert_no_leak(leaky, REPORT)


def test_assert_no_leak_raises_on_long_report_token():
    leaky = "lodash https://evil.example.com/aaaaaaaaaaaa vulnerability"
    with pytest.raises(AssertionError, match="long report token"):
        assert_no_leak(leaky, REPORT)


def test_assert_no_leak_allows_identifier_queries():
    ids = extract_public_ids(_claim(), REPORT)
    for q in build_queries(ids):
        assert_no_leak(q, REPORT)  # must not raise


def test_assert_no_leak_tolerates_short_word_overlap():
    # "the" / "a" appearing in a query is not a leak.
    assert_no_leak("lodash 4.17.20 vulnerability", REPORT)
    assert_no_leak("the lodash security advisory", REPORT)


def test_assert_no_leak_empty_report_is_noop():
    assert_no_leak("anything at all goes here", "")


def test_assert_no_leak_normalizes_whitespace_and_case():
    leaky = "Lodash   The Attacker Can Smuggle Arbitrary Commands Through"
    with pytest.raises(AssertionError):
        assert_no_leak(leaky, REPORT)


# ---------------------------------------------------------------------------
# caps and de-duplication
# ---------------------------------------------------------------------------

def test_queries_are_capped_at_six():
    ids = PublicIdentifiers(
        package="pkg",
        versions=["1.0.0", "1.0.1", "1.0.2", "1.0.3"],
        advisory_ids=["CVE-2020-0001", "CVE-2020-0002", "CVE-2020-0003"],
        extra_terms=["remote code execution"],
    )
    queries = build_queries(ids)
    assert len(queries) <= 6


def test_queries_are_deduplicated():
    # Template collision: "{pkg} {ver} vulnerability" == "{pkg} {extra_terms[0]}".
    ids = PublicIdentifiers(
        package="p",
        versions=["v1"],
        extra_terms=["v1 vulnerability"],
    )
    queries = build_queries(ids)
    assert queries.count("p v1 vulnerability") == 1
    assert len(queries) == len(set(queries))


def test_query_length_is_capped():
    ids = PublicIdentifiers(package="x" * 500, versions=["1.0.0"])
    for q in build_queries(ids):
        assert len(q) <= 400


def test_queries_without_versions_still_built():
    ids = PublicIdentifiers(package="leftpad")
    queries = build_queries(ids)
    assert "leftpad vulnerability" in queries
    assert "leftpad security advisory fixed version" in queries


# ---------------------------------------------------------------------------
# CVE / GHSA extraction
# ---------------------------------------------------------------------------

def test_extract_advisory_ids_from_report():
    text = (
        "This is the same bug as CVE-2021-23337 and GHSA-35jh-r3h4-6jhm. "
        "Duplicate mention CVE-2021-23337."
    )
    ids = extract_public_ids(_claim(), text)
    assert "CVE-2021-23337" in ids.advisory_ids
    assert "GHSA-35jh-r3h4-6jhm" in ids.advisory_ids
    assert len(ids.advisory_ids) == 2  # de-duplicated


def test_extract_advisory_ids_sorted_and_unique():
    text = "GHSA-35jh-r3h4-6jhm then CVE-2020-0001"
    ids = extract_public_ids(_claim(), text)
    assert ids.advisory_ids == sorted(set(ids.advisory_ids))


def test_extract_advisory_ids_empty_without_ids():
    ids = extract_public_ids(_claim(), REPORT)
    assert ids.advisory_ids == []


def test_extract_public_ids_versions_dedup_preserves_order():
    claim = _claim(affected_versions=["4.17.20", "4.17.20", "4.17.15"])
    ids = extract_public_ids(claim, "")
    assert ids.versions == ["4.17.20", "4.17.15"]


def test_extract_public_ids_extra_terms_from_vuln_class():
    ids = extract_public_ids(_claim(vuln_class=VulnClass.REDOS), "")
    assert ids.extra_terms == ["regex denial of service"]


def test_extract_public_ids_other_class_has_no_extra_terms():
    ids = extract_public_ids(_claim(vuln_class=VulnClass.OTHER), "")
    assert ids.extra_terms == []


def test_extract_public_ids_copies_no_prose():
    ids = extract_public_ids(_claim(), REPORT)
    blob = " ".join(
        [ids.package, *ids.versions, *ids.advisory_ids, *ids.extra_terms]
    ).lower()
    for bad in ("attacker", "smuggle", "crafted", "merge helper", "write-up"):
        assert bad not in blob


# ---------------------------------------------------------------------------
# Shape filtering: model free text cannot become a query term
# ---------------------------------------------------------------------------

def test_sanitize_version_keeps_real_versions():
    for good in ("4.17.20", "1.2.3-beta.1", "2.0.0-rc.1", "^1.2.0", ">=1.0.0", "v2.1.0"):
        assert sanitize_version(good) == good


def test_sanitize_version_drops_prose():
    for bad in (
        "the merge helper is vulnerable in production",
        "see https://evil.example.com/aaaaaaaaaaaa",
        "4.17.20 and also the service path /internal/admin",
        "x" * 80,
        "",
    ):
        assert sanitize_version(bad) == ""


def test_sanitize_package_keeps_npm_names():
    assert sanitize_package("lodash") == "lodash"
    assert sanitize_package("@scope/pkg") == "@scope/pkg"
    assert sanitize_package("node-serialize") == "node-serialize"


def test_sanitize_package_drops_prose_and_metacharacters():
    for bad in ("lodash; rm -rf /", "the package name in the report", "a b", "", "$(id)"):
        assert sanitize_package(bad) == ""


def test_llm_free_text_in_affected_versions_never_reaches_queries():
    # The extractor is model output. If it stuffs report prose into
    # affected_versions, that prose must be dropped at the boundary — not
    # cleaned up into a new search term.
    claim = _claim(
        affected_versions=[
            "4.17.20",
            "the merge helper smuggles commands into production",
            "https://evil.example.com/aaaaaaaaaaaa",
        ]
    )
    ids = extract_public_ids(claim, REPORT)
    assert ids.versions == ["4.17.20"]
    for q in build_queries(ids):
        assert_no_leak(q, REPORT)
        for bad in ("smuggle", "merge helper", "production", "evil.example"):
            assert bad not in q.lower()


def test_llm_free_text_package_never_reaches_queries():
    claim = _claim(package="the merge helper in our production service")
    ids = extract_public_ids(claim, REPORT)
    assert ids.package == ""
    # With no usable package name there is nothing legitimate to search for,
    # so no query is built at all rather than one carrying the prose.
    assert build_queries(ids) == []


# ---------------------------------------------------------------------------
# verify_query: whitelist, not denylist
# ---------------------------------------------------------------------------

def test_verify_query_accepts_built_queries():
    ids = extract_public_ids(_claim(), REPORT)
    for q in build_queries(ids):
        verify_query(q, ids)  # must not raise


def test_verify_query_rejects_report_prose():
    ids = extract_public_ids(_claim(), REPORT)
    with pytest.raises(AssertionError):
        verify_query("lodash merge helper smuggles commands", ids)


def test_verify_query_rejects_unknown_urls():
    ids = extract_public_ids(_claim(), REPORT)
    with pytest.raises(AssertionError):
        verify_query("lodash https://evil.example.com/aaaaaaaaaaaa", ids)


def test_verify_query_allows_advisory_ids():
    ids = PublicIdentifiers(package="lodash", versions=["4.17.20"], advisory_ids=["CVE-2021-23337"])
    verify_query("CVE-2021-23337", ids)
    verify_query("lodash CVE-2021-23337", ids)


def test_verify_query_allows_class_vocabulary():
    ids = extract_public_ids(_claim(vuln_class=VulnClass.REDOS), "")
    verify_query("lodash regex denial of service", ids)


# ---------------------------------------------------------------------------
# assert_no_leak tightened
# ---------------------------------------------------------------------------

def test_assert_no_leak_catches_short_phrases():
    # The old sliding window stepped by n//4 and skipped runs; a short phrase
    # must still count as a leak.
    report = "the merge helper is the root cause of this report"
    with pytest.raises(AssertionError):
        assert_no_leak("lodash merge helper is the root cause", report, min_run=12)


def test_assert_no_leak_catches_secret_like_tokens_of_any_length():
    with pytest.raises(AssertionError):
        assert_no_leak("lodash https://evil.example.com/aaaaaaaaaaaa", REPORT)
    with pytest.raises(AssertionError):
        assert_no_leak("lodash ghp_abc123", "the token is ghp_abc123 and it must stay")


def test_long_package_name_is_not_a_leak_next_to_vocabulary():
    # Every English word matches the npm name shape, so "vulnerability" must
    # not count as a second package and leave the real one unexempt. A false
    # positive here silently disables research for long package names.
    report = "node-serialize before 0.1.3 allows remote code execution via the map function."
    assert_no_leak("node-serialize vulnerability", report)
    assert_no_leak("node-serialize security advisory fixed version", report)
    assert_no_leak("node-serialize 0.1.2 vulnerability", report)
    assert_no_leak("@babel/traverse 7.20.0 vulnerability", "@babel/traverse fixed in 7.20.0.")


def test_long_blob_beside_a_real_package_is_still_a_leak():
    # A 12+ char alphanumeric blob looks like a package name. When a real
    # package is already in the query (the build_queries shape), the blob is
    # not the package and must not be exempted as one.
    report = "payload is deadbeefdeadbeefdead and must not travel"
    with pytest.raises(AssertionError, match="long report token"):
        assert_no_leak("lodash deadbeefdeadbeefdead vulnerability", report)
