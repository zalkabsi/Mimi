"""Fixed-version lookup from the public npm advisory database.

Sends only ``package -> [version]`` (public identifiers) to
``registry.npmjs.org``. Returns the lowest published version that closes the
advisory matching the claim's class, or ``None``. Deterministic: no model is
involved, so a fixed version cannot be hallucinated.
"""

from __future__ import annotations

import re
from typing import Optional

BULK_URL = "https://registry.npmjs.org/-/npm/v1/security/advisories/bulk"
PACKUMENT_URL = "https://registry.npmjs.org/{name}"

_TITLE_TERMS = {
    "prototype_pollution": ("prototype pollution",),
    "redos": ("regular expression", "redos", "resource consumption", "inefficient"),
    "xss": ("cross-site scripting", "xss"),
    "command_injection": ("command injection", "code injection"),
    "rce": ("code execution", "deserialization", "code injection", "command injection"),
    "denial_of_service": ("denial of service", "dos", "resource", "exhaustion"),
    "path_traversal": ("path traversal", "directory traversal"),
    "sql_injection": ("sql injection",),
    "ssrf": ("server-side request forgery", "ssrf"),
    "auth_bypass": ("authentication", "authorization", "bypass"),
}


def _parse(v: str) -> Optional[tuple[int, int, int]]:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None  # type: ignore[return-value]


def _in_range(version: tuple[int, int, int], rng: str) -> bool:
    """True if ``version`` satisfies a space-separated comparator range."""
    for part in re.findall(r"(<=|>=|<|>|=)?\s*(\d+\.\d+\.\d+)", rng or ""):
        op, ver = part
        bound = _parse(ver)
        if bound is None:
            return False
        ok = {
            "<": version < bound, "<=": version <= bound, ">": version > bound,
            ">=": version >= bound, "=": version == bound, "": version == bound,
        }[op]
        if not ok:
            return False
    return True


def _upper_exclusive(rng: str) -> Optional[str]:
    """``X`` from a range ending in ``<X``; ``<=X`` has no derivable fix."""
    m = re.search(r"<\s*(\d+\.\d+\.\d+)\s*$", rng or "")
    return m.group(1) if m else None


def pick_fixed_version(
    advisories: list[dict], affected: str, vuln_class: str, published: Optional[set[str]] = None
) -> Optional[str]:
    """Lowest fix across advisories that cover ``affected`` and match the class.

    ``published``, when given, restricts the answer to versions that exist.
    """
    v = _parse(affected)
    if v is None:
        return None
    terms = _TITLE_TERMS.get(vuln_class, ())
    fixes: list[str] = []
    for adv in advisories:
        title = str(adv.get("title") or "").lower()
        if terms and not any(t in title for t in terms):
            continue
        rng = str(adv.get("vulnerable_versions") or "")
        if not _in_range(v, rng):
            continue
        fixed = _upper_exclusive(rng)
        if fixed and (published is None or fixed in published):
            fixes.append(fixed)
    if not fixes:
        return None
    return min(fixes, key=lambda s: _parse(s) or (0, 0, 0))


def covering_titles(advisories: list[dict], affected: str, vuln_class: str) -> list[str]:
    """Titles of class-matching advisories whose range contains ``affected``.

    Unlike ``pick_fixed_version`` this also counts ``<=X`` ranges: it answers
    "does a public advisory say this version is affected", not "what fixes it".
    """
    v = _parse(affected)
    if v is None:
        return []
    terms = _TITLE_TERMS.get(vuln_class, ())
    out: list[str] = []
    for adv in advisories:
        title = str(adv.get("title") or "")
        if terms and not any(t in title.lower() for t in terms):
            continue
        if _in_range(v, str(adv.get("vulnerable_versions") or "")):
            out.append(title)
    return out


def lookup_advisories(
    package: str, affected: str, vuln_class: str, timeout: float = 15.0
) -> Optional[dict]:
    """``{"fixed": str|None, "covering": [titles]}``; ``None`` if the lookup failed.

    ``None`` means *unknown*, not "no advisory": callers must not read a failed
    lookup as evidence that the claim is unsupported.
    """
    try:
        import httpx

        with httpx.Client(timeout=timeout) as c:
            r = c.post(BULK_URL, json={package: [affected]})
            r.raise_for_status()
            advs = r.json().get(package) or []
            published: Optional[set[str]] = None
            p = c.get(PACKUMENT_URL.format(name=package.replace("/", "%2f")))
            if p.status_code == 200:
                published = set((p.json().get("versions") or {}).keys())
        return {
            "fixed": pick_fixed_version(advs, affected, vuln_class, published),
            "covering": covering_titles(advs, affected, vuln_class),
        }
    except Exception:
        return None


def lookup_fixed_version(package: str, affected: str, vuln_class: str, timeout: float = 15.0) -> Optional[str]:
    """Network wrapper; any failure returns ``None`` (the caller falls back)."""
    try:
        import httpx

        with httpx.Client(timeout=timeout) as c:
            r = c.post(BULK_URL, json={package: [affected]})
            r.raise_for_status()
            advs = r.json().get(package) or []
            published: Optional[set[str]] = None
            p = c.get(PACKUMENT_URL.format(name=package.replace("/", "%2f")))
            if p.status_code == 200:
                published = set((p.json().get("versions") or {}).keys())
        return pick_fixed_version(advs, affected, vuln_class, published)
    except Exception:
        return None
