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

from .schemas import Oracle, OracleResult, OracleType, RunRecord

# Bound the evidence an output oracle has to scan, and refuse patterns that
# can catastrophically backtrack (a ReDoS in the checker would hang triage).
_MAX_HAY_BYTES = 256_000
_MAX_PATTERN_LEN = 200
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)\s*[+*{]")


def _pattern_is_safe(pattern: str) -> str | None:
    """Return a reason string when the pattern is unusable, else None."""
    if not pattern:
        return "oracle misconfigured: pattern unset"
    if len(pattern) > _MAX_PATTERN_LEN:
        return f"oracle pattern too long ({len(pattern)} > {_MAX_PATTERN_LEN})"
    if _NESTED_QUANTIFIER.search(pattern):
        return "oracle pattern rejected: nested quantifiers can backtrack catastrophically"
    return None


def _haystack(run: RunRecord) -> tuple[str, bool]:
    """Combined output to scan, plus whether it was cut short."""
    text = (run.stdout or "") + "\n" + (run.stderr or "")
    if len(text.encode("utf-8", "ignore")) > _MAX_HAY_BYTES:
        return text[:_MAX_HAY_BYTES], True
    return text, run.truncated


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
        fired = run.exit_code == oracle.expected_exit
        return fired, f"exit_code={run.exit_code}, expected {oracle.expected_exit} -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.SIGNAL:
        want = (oracle.signal_name or "").upper().lstrip("SIG")
        got = (run.signal or "").upper().lstrip("SIG")
        if not want:
            return False, "oracle misconfigured: signal_name unset", False
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
        verdict = f"__MIMI_MARKER_VERDICT__:{marker}:" in (run.probe_output or "")
        if not verdict:
            return False, "marker probe verdict missing from probe output", False
        fired = f"__MIMI_MARKER_VERDICT__:{marker}:present" in (run.probe_output or "")
        return fired, f"marker {marker!r} -> {'present' if fired else 'absent'}", True

    if t is OracleType.TIMING_THRESHOLD:
        if oracle.threshold_ms is None:
            return False, "oracle misconfigured: threshold_ms unset", False
        if oracle.threshold_ms <= 0:
            return False, f"oracle misconfigured: threshold_ms must be > 0 (got {oracle.threshold_ms})", False
        fired = run.elapsed_ms >= oracle.threshold_ms
        return fired, f"elapsed_ms={run.elapsed_ms:.0f}, threshold={oracle.threshold_ms:.0f} -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.PROTOTYPE_POLLUTION_PROBE:
        out = run.probe_output or ""
        if "__MIMI_PROTO_POLLUTED__:" not in out:
            return False, "prototype-pollution probe verdict missing from probe output", False
        fired = "__MIMI_PROTO_POLLUTED__:true" in out
        return fired, f"prototype-pollution probe -> {'fired' if fired else 'not fired'}", True

    if t is OracleType.PATH_TRAVERSAL_FILE_READ:
        expect = oracle.expect_traversal_to or "/etc/passwd"
        out = run.probe_output or ""
        fired = f"__MIMI_TRAVERSAL__:{expect}:read" in out
        absent = f"__MIMI_TRAVERSAL__:{expect}:blocked" in out
        if fired:
            return True, f"traversal read succeeded for {expect!r}", True
        if absent:
            return False, f"traversal read blocked for {expect!r}", True
        return False, "traversal probe verdict missing from probe output", False

    if t is OracleType.NETWORK_CALL:
        out = run.probe_output or ""
        token = "__MIMI_NETWORK__:"
        if token not in out:
            return False, "network probe verdict missing from probe output", False
        fired = f"{token}attempted" in out
        return fired, f"network probe -> {'attempted' if fired else 'not attempted'}", True

    if t is OracleType.CUSTOM_PROBE:
        pattern = oracle.pattern or ""
        problem = _pattern_is_safe(pattern)
        if problem:
            return False, problem, False
        try:
            rx = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            return False, f"custom probe pattern invalid: {e}", False
        out = run.probe_output or ""
        if not out:
            return False, "custom probe produced no probe output to judge", False
        fired = rx.search(out) is not None
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
