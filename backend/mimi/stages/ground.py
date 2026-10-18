"""Stage 2 — Ground the claim in the source at the pinned version.

Deterministic first: npm registry metadata and (when cited) a search of the
package tarball for the claimed files and symbols. Nano only summarises.

Evidence only. Grounding is NEVER a sole basis for rejection — SlopCheck
contradicts 29.4% of confirmed vulnerabilities and ~90% of those
contradictions are wrong (docs/01 E5). It ranks hypotheses instead.
"""

from __future__ import annotations

import io
import re
import tarfile
from typing import Optional

import httpx

from ..config import Stage
from ..events import EventLog
from ..llm import LLMClient
from ..schemas import Claim, EvidenceKind, GroundingEvidence, ReportSubmission

NPM_REGISTRY = "https://registry.npmjs.org"
_TARBALL_CAP = 8 * 1024 * 1024  # refuse to fetch absurd tarballs


def ground_claim(
    submission: ReportSubmission,
    claim: Claim,
    events: EventLog,
    llm: Optional[LLMClient] = None,
    client: Optional[httpx.Client] = None,
) -> list[GroundingEvidence]:
    t0 = events.start("ground", f"{submission.package}@{submission.version}")
    own_client = client is None
    client = client or httpx.Client(timeout=30.0)
    evidence: list[GroundingEvidence] = []
    try:
        evidence.extend(_registry_check(submission, claim, client))
        if claim.cited_files or claim.cited_symbols:
            evidence.extend(_tarball_check(submission, claim, client, events))
    except httpx.HTTPError as e:
        evidence.append(
            GroundingEvidence(
                kind=EvidenceKind.NOTE,
                target="registry",
                detail=f"grounding skipped, registry unreachable: {e}",
            )
        )
    finally:
        if own_client:
            client.close()

    if llm is not None and evidence:
        _summarise(claim, evidence, llm, events)

    events.ok("ground", t0, f"{len(evidence)} evidence items")
    return evidence


def _registry_check(submission: ReportSubmission, claim: Claim, client: httpx.Client) -> list[GroundingEvidence]:
    out: list[GroundingEvidence] = []
    url = f"{NPM_REGISTRY}/{submission.package}/{submission.version}"
    resp = client.get(url)
    if resp.status_code == 404:
        out.append(
            GroundingEvidence(
                kind=EvidenceKind.VERSION_MISMATCH,
                target=submission.package_spec,
                detail="package@version not found on the npm registry",
            )
        )
        return out
    resp.raise_for_status()
    data = resp.json()
    out.append(
        GroundingEvidence(
            kind=EvidenceKind.VERSION_MATCHES,
            target=submission.package_spec,
            detail=f"published {data.get('dist', {}).get('tarball', '')}",
        )
    )
    deps = list((data.get("dependencies") or {}).keys())
    if claim.cited_files:
        for f in claim.cited_files[:5]:
            out.append(
                GroundingEvidence(
                    kind=EvidenceKind.NOTE,
                    target=f,
                    detail=f"to be checked inside tarball (deps: {len(deps)})",
                )
            )
    return out


def _tarball_check(
    submission: ReportSubmission,
    claim: Claim,
    client: httpx.Client,
    events: EventLog,
) -> list[GroundingEvidence]:
    out: list[GroundingEvidence] = []
    meta = client.get(f"{NPM_REGISTRY}/{submission.package}/{submission.version}").json()
    tarball_url = (meta.get("dist") or {}).get("tarball")
    if not tarball_url:
        out.append(GroundingEvidence(kind=EvidenceKind.NOTE, target="tarball", detail="no tarball URL in metadata"))
        return out

    archive = io.BytesIO()
    with client.stream("GET", tarball_url) as resp:
        resp.raise_for_status()
        content_length = resp.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > _TARBALL_CAP:
                    out.append(
                        GroundingEvidence(
                            kind=EvidenceKind.NOTE,
                            target="tarball",
                            detail="tarball exceeds the 8 MiB limit, skipped content search",
                        )
                    )
                    return out
            except ValueError:
                # A malformed length is not trusted; enforce the limit while streaming.
                pass

        downloaded = 0
        for chunk in resp.iter_bytes(chunk_size=64 * 1024):
            if downloaded + len(chunk) > _TARBALL_CAP:
                out.append(
                    GroundingEvidence(
                        kind=EvidenceKind.NOTE,
                        target="tarball",
                        detail="tarball exceeds the 8 MiB limit, skipped content search",
                    )
                )
                return out
            archive.write(chunk)
            downloaded += len(chunk)

    file_index: list[str] = []
    content_hits: dict[str, list[str]] = {}
    try:
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile() or member.size > 512 * 1024:
                    continue
                name = member.name
                file_index.append(name)
                want_content = bool(claim.cited_symbols) and name.endswith((".js", ".mjs", ".cjs", ".ts", ".json"))
                if want_content:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    text = f.read(512 * 1024).decode("utf-8", "ignore")
                    for sym in claim.cited_symbols:
                        if re.search(rf"\b{re.escape(sym)}\b", text):
                            content_hits.setdefault(sym, []).append(name)
    except tarfile.TarError as e:
        out.append(GroundingEvidence(kind=EvidenceKind.NOTE, target="tarball", detail=f"could not read tarball: {e}"))
        return out

    for cited in claim.cited_files:
        suffix = cited.lstrip("./")
        hit = next((n for n in file_index if n.endswith(suffix) or suffix in n), None)
        if hit:
            out.append(
                GroundingEvidence(kind=EvidenceKind.FILE_FOUND, target=cited, detail=hit, source_ref=hit)
            )
        else:
            out.append(
                GroundingEvidence(
                    kind=EvidenceKind.FILE_ABSENT,
                    target=cited,
                    detail="not present in the package tarball at this version",
                )
            )

    for sym in claim.cited_symbols:
        hits = content_hits.get(sym) or []
        if hits:
            out.append(
                GroundingEvidence(
                    kind=EvidenceKind.SYMBOL_FOUND,
                    target=sym,
                    detail=f"in {len(hits)} file(s)",
                    source_ref=hits[0],
                )
            )
        else:
            out.append(
                GroundingEvidence(
                    kind=EvidenceKind.SYMBOL_ABSENT,
                    target=sym,
                    detail="symbol not found in tarball sources at this version",
                )
            )
    return out


def _summarise(claim: Claim, evidence: list[GroundingEvidence], llm: LLMClient, events: EventLog) -> None:
    """Nano adds a one-line reading of the evidence. It cannot change kinds."""
    lines = "\n".join(f"- [{e.kind.value}] {e.target}: {e.detail}" for e in evidence[:20])
    try:
        resp = llm.chat(
            stage=Stage.GROUND,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarise in one sentence what this grounding evidence says about "
                        "whether the cited code exists at this version. Do not judge whether "
                        "the vulnerability is real.\n" + lines
                    ),
                }
            ],
            max_tokens=120,
            enable_thinking=False,
        )
        summary = (resp.content or "").strip()
        if summary:
            evidence.append(GroundingEvidence(kind=EvidenceKind.NOTE, target="summary", detail=summary))
    except Exception as e:  # grounding must not fail because of a summary
        events.emit("ground", "ok", f"summary skipped: {e}")
