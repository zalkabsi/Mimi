"""Week-1 spike 4 — Tavily call using only public identifiers.

Proves the redaction rule end to end: a real query is built from
package/version/CVE ids and checked with assert_no_leak before it is sent.
Report text is never transmitted.

    python scripts/spike_tavily.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from mimi.config import Settings  # noqa: E402
from mimi.redaction import assert_no_leak, build_queries, extract_public_ids  # noqa: E402
from mimi.schemas import Claim, VulnClass  # noqa: E402
from mimi.tavily_client import TavilyClient  # noqa: E402

# A realistic report body that must NEVER reach Tavily.
FAKE_REPORT = (
    "Hi, I found a nasty bug. The function merge() in your lodash build lets me "
    "write arbitrary properties onto Object.prototype when I pass a crafted object. "
    "Please fix ASAP, here is my exploit script and my email attacker@evil.example."
)


def main() -> int:
    settings = Settings.from_env()
    if not settings.tavily_api_key:
        print("TAVILY_API_KEY not set (env var only; never paste keys in chat)", file=sys.stderr)
        return 2

    claim = Claim(
        package="minimist",
        affected_versions=["1.2.5"],
        vuln_class=VulnClass.PROTOTYPE_POLLUTION,
        expected_effect="Object.prototype gains attacker-controlled properties",
    )
    ids = extract_public_ids(claim, report_text=FAKE_REPORT + " CVE-2021-44906")
    queries = build_queries(ids)
    print("public ids:", ids.model_dump())
    print("queries to send:", json.dumps(queries, indent=2))

    for q in queries:
        assert_no_leak(q, FAKE_REPORT)  # raises on any leak

    client = TavilyClient(settings)
    try:
        findings = client.search(ids, report_text=FAKE_REPORT)
    finally:
        client.close()

    print(f"\nsent {len(findings.queries)} queries, got {len(findings.known_advisories)} results")
    for a in findings.known_advisories[:5]:
        print(f"- {a.title[:80]} | {a.url[:80]}")
    print("\nredaction check: PASS (no report text left the system)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
