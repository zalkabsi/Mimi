"""Deterministic oracle checkers.

Principle (docs/02-architecture.md): the LLM proposes hypotheses and
interprets ambiguous output; it does not grade a reproduction that a
deterministic check can grade. Every oracle here is a pure function over a
RunRecord.

An oracle result is **conclusive** only when the PoC actually ran, the oracle
was correctly configured, and the evidence was complete enough to judge.
Errored runs, misconfigured oracles, missing probe verdicts and truncated
output are inconclusive — they must never be read as "did not fire", or a
broken execution would masquerade as a quantified negative result.

Probe-style oracles read ``RunRecord.probe_output`` (produced by a trusted
post-PoC command) rather than the PoC's own stdout, so the code under test
cannot forge a verdict token.
"""

from __future__ import annotations

import re
from typing import Optional

from .schemas import Oracle, OracleResult, OracleType, RunRecord

# Bound the evidence an output oracle has to scan, and refuse patterns that
# can catastrophically backtrack (a ReDoS in the checker would hang triage).
_MAX_HAY_BYTES = 256_000
_MAX_PATTERN_LEN = 200
# A quantified group that itself contains a quantifier — (a+)* — backtracks
# catastrophically.
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)\s*[+*{]")
# A quantified group with alternation — (a|a)* — is the same trap without an
# inner quantifier token, and was previously let through.
_QUANTIFIED_ALTERNATION = re.compile(r"\([^)]*\|[^)]*\)\s*[+*{]")


def _pattern_is_safe(pattern: str) -> str | None:
    """Return a reason string when the pattern is unusable, else None."""
    if not pattern:
        return "oracle misconfigured: pattern unset"
    if len(pattern) > _MAX_PATTERN_LEN:
        return f"oracle pattern too long ({len(pattern)} > {_MAX_PATTERN_LEN})"
    if _NESTED_QUANTIFIER.search(pattern):
        return "oracle pattern rejected: nested quantifiers can backtrack catastrophically"
    if _QUANTIFIED_ALTERNATION.search(pattern):
        return "oracle pattern rejected: quantified alternation can backtrack catastrophically"
    return None


def _haystack(run: RunRecord) -> tuple[str, bool]:
    """Combined output to scan, plus whether it was cut short."""
    text = (run.stdout or "") + "\n" + (run.stderr or "")
    if len(text.encode("utf-8", "ignore")) > _MAX_HAY_BYTES:
        return text[:_MAX_HAY_BYTES], True
    return text, run.truncated


# Sentinels the trusted probe prints when it could not produce a verdict.
_PROBE_MISSING = "__MIMI_PROBE_MISSING__:"
_PROBE_ERROR = "__MIMI_PROBE_ERROR__:"
_CUSTOM_PROBE_ERROR = "__MIMI_CUSTOM_PROBE_ERROR__:"
_CUSTOM_PROBE_BEGIN = "__MIMI_CUSTOM_PROBE_BEGIN__:"
_CUSTOM_PROBE_END = "__MIMI_CUSTOM_PROBE_END__:"


def _probe_evidence(run: RunRecord) -> tuple[str, Optional[str]]:
    """The probe channel, or a reason it cannot be judged at all.

    Returns ``(probe_output, None)`` when the channel is complete, else
    ``("", reason)``. A missing, errored or truncated probe is never a
    negative — it is inconclusive. That distinction is the whole point: a
    broken execution must not masquerade as "N hypotheses, 0 triggered".
    """
    if run.truncated:
        return "", "probe output was truncated before the oracle could judge it"
    out = run.probe_output or ""
    if _PROBE_ERROR in out:
        return "", f"trusted probe failed: {out.split(_PROBE_ERROR, 1)[1][:160]}"
    if _PROBE_MISSING in out:
        return "", (
            "trusted probe recorded no verdict "
            f"({out.split(_PROBE_MISSING, 1)[1][:80].strip()}) — the shim's exit "
            "write is missing, so in-process state cannot be judged"
        )
    return out, None


_STACK_RE = re.compile(r"(?m)^\s+at .+|Cannot find module|\b(?:Type|Reference|Syntax|Range)Error\b")


def crashed_with_exception(run: RunRecord) -> bool:
    """Nonzero exit with a Node uncaught-exception signature in stderr."""
    return bool(
        run.exit_code not in (0, None)
        and not run.error
        and _STACK_RE.search(run.stderr or "")
    )


def check_oracle(
    oracle: Oracle,
    run: RunRecord,
    *,
    hypothesis_id: str,
    phase: str = "affected",
    run_index: int = 0,
) -> OracleResult:
    """Evaluate ``oracle`` against ``run``. Never raises on bad oracle params —
    returns a non-conclusive result with a detail explaining why it could not
    be judged."""

    if run.error:
        return OracleResult(
            hypothesis_id=hypothesis_id,
            phase=phase,  # type: ignore[arg-type]
            oracle=oracle,
            fired=False,
            conclusive=False,
            detail=f"run errored before oracle: {run.error}",
            run_index=run_index,
        )

    fired, detail, conclusive = _check(oracle, run)
    return OracleResult(
        hypothesis_id=hypothesis_id,
        phase=phase,  # type: ignore[arg-type]
        oracle=oracle,
        fired=fired,
        conclusive=conclusive,
        detail=detail,
        run_index=run_index,
    )


def _check(oracle: Oracle, run: RunRecord) -> tuple[bool, str, bool]:
    """(fired, detail, conclusive)."""
    t = oracle.type

    if t is OracleType.EXIT_CODE:
        if oracle.expected_exit is None and not oracle.expect_nonzero_exit:
            return False, "oracle misconfigured: expected_exit unset", False
        if oracle.expect_nonzero_exit:
            if run.exit_code is None:
                return False, "no exit code recorded — cannot judge", False
            fired = run.exit_code != 0
            return fired, f"exit_code={run.exit_code}, expected nonzero -> {'fired' if fired else 'not fired'}", True
        # A missing exit code is not "not the expected code". Reading it as a
        # clean negative would grade a dead run as evidence.
        if run.exit_code is None:
            return False, "no exit code recorded — cannot judge", False
        fired = run.exit_code == oracle.expected_exit
        return fired, f"exit_code={run.exit_code}, expected {oracle.expected_exit} -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.SIGNAL:
        want = (oracle.signal_name or "").upper().lstrip("SIG")
        got = (run.signal or "").upper().lstrip("SIG")
        if not want:
            return False, "oracle misconfigured: signal_name unset", False
        if not got and run.exit_code is None:
            return False, "no termination recorded — cannot judge", False
        fired = bool(got) and got == want
        return fired, f"signal={run.signal!r}, expected {want} -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.OUTPUT_REGEX:
        pattern = oracle.pattern or ""
        problem = _pattern_is_safe(pattern)
        if problem:
            return False, problem, False
        try:
            rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            return False, f"oracle pattern invalid: {e}", False
        hay, cut = _haystack(run)
        if cut:
            return False, "output was truncated before the oracle could judge it", False
        m = rx.search(hay)
        # No match plus an uncaught crash means the PoC never reached its
        # verdict line (e.g. "x is not a function"). That is a broken PoC, not
        # a negative result, and must not count toward "N tested, 0 triggered".
        if m is None and crashed_with_exception(run):
            return False, "PoC crashed before its verdict (uncaught error); not a negative result", False
        return (
            m is not None,
            (f"output matched {oracle.pattern!r} at {m.start()}" if m else f"pattern {oracle.pattern!r} not found"),
            True,
        )

    if t is OracleType.MARKER_FILE:
        # Verdict comes from the trusted probe channel, never the PoC stdout.
        marker = oracle.marker_path or ""
        if not marker:
            return False, "oracle misconfigured: marker_path unset", False
        out, why = _probe_evidence(run)
        if why:
            return False, why, False
        verdict = f"__MIMI_MARKER_VERDICT__:{marker}:" in out
        if not verdict:
            return False, "marker probe verdict missing from probe output", False
        fired = f"__MIMI_MARKER_VERDICT__:{marker}:present" in out
        return fired, f"marker {marker!r} -> {'present' if fired else 'absent'}", True

    if t is OracleType.TIMING_THRESHOLD:
        if oracle.threshold_ms is None:
            return False, "oracle misconfigured: threshold_ms unset", False
        if oracle.threshold_ms <= 0:
            return False, f"oracle misconfigured: threshold_ms must be > 0 (got {oracle.threshold_ms})", False
        fired = run.elapsed_ms >= oracle.threshold_ms
        return fired, f"elapsed_ms={run.elapsed_ms:.0f}, threshold={oracle.threshold_ms:.0f} -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.PROTOTYPE_POLLUTION_PROBE:
        # In-process verdict from the preloaded shim. A fresh process can never
        # see prototype pollution (heap state dies with the PoC), so a missing
        # verdict is inconclusive — never "not polluted".
        out, why = _probe_evidence(run)
        if why:
            return False, why, False
        if "__MIMI_PROTO_POLLUTED__:" not in out:
            return False, "prototype-pollution probe verdict missing from probe output", False
        fired = "__MIMI_PROTO_POLLUTED__:true" in out
        return fired, f"prototype-pollution probe -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.PATH_TRAVERSAL_FILE_READ:
        expect = oracle.expect_traversal_to or "/etc/passwd"
        out, why = _probe_evidence(run)
        if why:
            return False, why, False
        fired = f"__MIMI_TRAVERSAL__:{expect}:read" in out
        absent = f"__MIMI_TRAVERSAL__:{expect}:blocked" in out
        if fired:
            return True, f"traversal read succeeded for {expect!r}", True
        if absent:
            return False, f"traversal read blocked for {expect!r}", True
        return False, "traversal probe verdict missing from probe output", False

    if t is OracleType.NETWORK_CALL:
        # Fired only by egress calls the PoC itself made (wrapped by the shim),
        # never by the probe's own connectivity check (__MIMI_EGRESS__: is a
        # different question and must not fire this oracle).
        out, why = _probe_evidence(run)
        if why:
            return False, why, False
        token = "__MIMI_NETWORK__:"
        if token not in out:
            return False, "network probe verdict missing from probe output", False
        fired = f"{token}attempted" in out
        return fired, f"network probe -> {'attempted' if fired else 'no attempt recorded'}", True

    if t is OracleType.CUSTOM_PROBE:
        pattern = oracle.pattern or ""
        problem = _pattern_is_safe(pattern)
        if problem:
            return False, problem, False
        try:
            rx = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            return False, f"custom probe pattern invalid: {e}", False
        out, why = _probe_evidence(run)
        if why:
            return False, why, False
        if _CUSTOM_PROBE_ERROR in out:
            return (
                False,
                "custom probe snippet failed: "
                + out.split(_CUSTOM_PROBE_ERROR, 1)[1][:160],
                False,
            )
        begin = out.find(_CUSTOM_PROBE_BEGIN)
        if begin == -1:
            return False, "custom probe snippet produced no output to judge", False
        # Search only the snippet's own output. The fixed probes share this
        # stream, so a pattern like "attempted" would otherwise fire on the
        # network probe's verdict token and grade a different question. The
        # end marker is the real one (emitted after the snippet), so a snippet
        # that prints a fake end still gets the full window.
        end = out.rfind(_CUSTOM_PROBE_END)
        if end == -1:
            return False, "custom probe output was not terminated — cannot judge", False
        start = out.find("\n", begin)
        snippet_out = out[start + 1 : end] if start != -1 else ""
        fired = rx.search(snippet_out) is not None
        return fired, f"custom probe -> {'fired' if fired else 'not fired'}", True

    return False, f"unknown oracle type {t}", False


def summarize(oracle: Oracle) -> str:
    """One-line human description used in dossiers and the UI."""
    t = oracle.type
    if t is OracleType.EXIT_CODE:
        return f"exit code {'!= 0' if oracle.expect_nonzero_exit else '== ' + str(oracle.expected_exit)}"
    if t is OracleType.SIGNAL:
        return f"terminates with {oracle.signal_name}"
    if t is OracleType.OUTPUT_REGEX:
        return f"output matches /{oracle.pattern}/"
    if t is OracleType.MARKER_FILE:
        return f"marker file {oracle.marker_path} appears"
    if t is OracleType.TIMING_THRESHOLD:
        return f"runtime >= {oracle.threshold_ms:.0f} ms"
    if t is OracleType.PROTOTYPE_POLLUTION_PROBE:
        return "prototype pollution probe fires"
    if t is OracleType.PATH_TRAVERSAL_FILE_READ:
        return f"reads {oracle.expect_traversal_to} outside the project"
    if t is OracleType.NETWORK_CALL:
        return "PoC attempts a network call"
    if t is OracleType.CUSTOM_PROBE:
        return f"probe matches /{oracle.pattern}/"
    return "custom check"
