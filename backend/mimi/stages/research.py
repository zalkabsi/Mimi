"""Stage 3 — Research (Tavily + Nemotron Super).

Queries are built from public identifiers only (package, versions, CVE/GHSA
ids). Report text and PoC never leave the system — enforced in
``redaction.assert_no_leak`` before every request. Super synthesises the
results into known advisories, duplicates and the fixed version / fix commit,
which supply the fixed half of the differential test.
"""

from __future__ import annotations

import re
import json
from typing import Optional

from ..config import Stage
from ..events import EventLog
from ..llm import LLMClient
from ..redaction import extract_public_ids
from ..schemas import Claim, PublicIdentifiers, ReportSubmission, ResearchFindings
from ..tavily_client import TavilyClient

_SYNTH_HINT = json.dumps(
    {
        "known_advisories": [{"title": "str", "url": "str", "advisory_ids": ["CVE-… or GHSA-…"]}],
        "duplicates": ["str"],
        "fixed_version": "string or null",
        "fix_commit": "string or null",
        "notes": "string",
    },
    indent=2,
)


_FIXED_RE = re.compile(
    r"(?:fixed in|upgrade to|patched in|update to|fixed by upgrading to)\s+(?:version\s+)?v?(\d+\.\d+\.\d+)",
    re.IGNORECASE,
)


def _regex_fixed_version(text: str) -> str | None:
    """Most common version following a 'fixed in' phrase, else None."""
    found = _FIXED_RE.findall(text or "")
    if not found:
        return None
    return max(set(found), key=found.count)


def research(
    submission: ReportSubmission,
    claim: Claim,
    events: EventLog,
    llm: Optional[LLMClient] = None,
    tavily: Optional[TavilyClient] = None,
) -> tuple[PublicIdentifiers, ResearchFindings]:
    t0 = events.start("research", "Tavily queries from public identifiers only")
    ids = extract_public_ids(claim, submission.report_text)

    if tavily is None:
        findings = ResearchFindings(used=False, notes="research skipped: no Tavily client configured")
        events.skip("research", "no Tavily client")
        return ids, findings

    try:
        findings = tavily.search(ids, report_text=submission.report_text)
    except Exception as e:
        findings = ResearchFindings(used=False, notes=f"research failed: {e}")
        events.error("research", t0, f"Tavily failed: {e}")
        return ids, findings

    if llm is not None and findings.known_advisories:
        _synthesise(findings, llm, events)

    events.ok(
        "research",
        t0,
        f"{len(findings.queries)} queries, {len(findings.known_advisories)} results, "
        f"fixed={findings.fixed_version or 'unknown'}",
    )
    return ids, findings


def _synthesise(findings: ResearchFindings, llm: LLMClient, events: EventLog) -> None:
    """Super turns search results into structured advisory facts.

    The model may only restate what appears in the results; it never invents
    a fixed version (a wrong fixed version would poison the differential).
    """
    corpus = "\n".join(
        f"- {a.title} | {a.url} | {a.snippet[:400]}" for a in findings.known_advisories[:12]
    )
    try:
        data = llm.chat_json(
            stage=Stage.RESEARCH,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "From these search results only, extract advisory facts. "
                        "If a fixed version or fix commit is not stated in the results, "
                        "use null. Do not guess.\n\n" + corpus
                    ),
                }
            ],
            schema_hint=_SYNTH_HINT,
            max_tokens=800,
            enable_thinking=False,
        )
    except Exception as e:
        findings.notes += f"synthesis failed: {e}; "
        return

    claimed = str(data.get("fixed_version") or "").strip()
    if claimed and claimed not in corpus:
        findings.notes += f"model fixed_version {claimed!r} not in the results; ignored; "
        claimed = ""
    # Deterministic backstop: the model sometimes answers null on a result set
    # that plainly says "fixed in 1.2.6".
    findings.fixed_version = claimed or _regex_fixed_version(corpus) or findings.fixed_version
    if data.get("fix_commit"):
        findings.fix_commit = str(data["fix_commit"])
    findings.notes += str(data.get("notes") or "")
