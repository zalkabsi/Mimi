"""The real research client must accept public reports without sending their prose."""

import json
from pathlib import Path

import httpx

from mimi.config import Settings
from mimi.redaction import extract_public_ids
from mimi.schemas import Claim, VulnClass
from mimi.tavily_client import TavilyClient


def test_bundled_report_reaches_tavily_with_only_public_queries():
    report = (Path(__file__).parents[1] / "mimi/data/sample_report.md").read_text()
    ids = extract_public_ids(Claim(
        package="minimist",
        affected_versions=["1.2.5"],
        vuln_class=VulnClass.PROTOTYPE_POLLUTION,
        expected_effect="Object.prototype gains an attacker-controlled property",
    ), report)
    payloads = []

    def search(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"results": [{
            "title": "CVE-2021-44906",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44906",
            "content": "Public minimist advisory",
        }]})

    with httpx.Client(transport=httpx.MockTransport(search)) as http:
        findings = TavilyClient(Settings(tavily_api_key="test-key"), client=http).search(
            ids, report_text=report,
        )

    assert findings.used
    assert len(findings.known_advisories) == 1
    assert [p["query"] for p in payloads] == [
        "CVE-2021-44906",
        "minimist CVE-2021-44906",
        "minimist 1.2.5 vulnerability",
        "minimist prototype pollution",
        "minimist security advisory fixed version",
    ]
    for payload in payloads:
        assert set(payload) == {"query", "max_results", "search_depth", "include_answer"}
        assert "__proto__" not in payload["query"]
        assert "attacker-controlled" not in payload["query"]
