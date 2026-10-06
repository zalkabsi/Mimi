"""Tavily research client.

Privacy rule (docs/02-architecture.md): report text and PoC never leave the
system. Only ``PublicIdentifiers`` are queried, and every query is checked
with ``redaction.assert_no_leak`` before it is sent. Queries are logged into
the dossier so the maintainer can see exactly what left the system.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .config import Settings
from .redaction import assert_no_leak, build_queries, verify_query
from .schemas import Advisory, PublicIdentifiers, ResearchFindings


class TavilyError(RuntimeError):
    pass


class TavilyClient:
    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        self.settings = settings
        self._client = client or httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def search(self, ids: PublicIdentifiers, report_text: str = "", max_results: int = 5) -> ResearchFindings:
        """Run the fixed query set and return structured findings.

        ``report_text`` is used only for the leak assertion — never sent.
        """
        self.settings.require_tavily()
        queries = build_queries(ids)
        for q in queries:
            # Whitelist first: every token must be a public identifier or a word
            # from the fixed vocabulary. Then the prose-run check, which still
            # applies even to identifiers if they were quoted from the report.
            verify_query(q, ids)
            assert_no_leak(q, report_text)

        findings = ResearchFindings(queries=queries, used=True)
        for q in queries:
            try:
                results = self._search_one(q, max_results=max_results)
            except TavilyError as e:
                findings.notes += f"query failed ({q!r}): {e}; "
                continue
            for r in results:
                title = str(r.get("title") or "")
                url = str(r.get("url") or "")
                content = str(r.get("content") or r.get("snippet") or "")[:400]
                findings.known_advisories.append(
                    Advisory(source="tavily", title=title, url=url, snippet=content)
                )
                lowered = f"{title} {content}".lower()
                if "fixed in" in lowered or "patched in" in lowered:
                    findings.fix_url = findings.fix_url or url
        findings.known_advisories = _dedup_advisories(findings.known_advisories)
        return findings

    def _search_one(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        # Tavily accepts the key either as a bearer token or in the body; we
        # send both-compatible header form and the body field is omitted so the
        # key never appears in logged request bodies.
        resp = self._client.post(
            self.settings.tavily_url,
            headers={
                "Authorization": f"Bearer {self.settings.tavily_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            },
        )
        if resp.status_code == 401:
            # older key-in-body form
            resp = self._client.post(
                self.settings.tavily_url,
                json={"api_key": self.settings.tavily_api_key, "query": query, "max_results": max_results},
            )
        if resp.status_code != 200:
            raise TavilyError(f"HTTP {resp.status_code}: {resp.text[:160]}")
        data = resp.json()
        return list(data.get("results") or [])


def _dedup_advisories(items: list[Advisory]) -> list[Advisory]:
    seen: set[str] = set()
    out: list[Advisory] = []
    for a in items:
        key = a.url or a.title
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out
