"""Deterministic oracle checkers.

Principle (docs/02-architecture.md): the LLM proposes hypotheses and
interprets ambiguous output; it does not grade a reproduction that a
deterministic check can grade. Every oracle here is a pure function over a
RunRecord.
"""

from __future__ import annotations

import re
from typing import Optional

from .schemas import Oracle, OracleResult, OracleType, RunRecord


def check_oracle(oracle: Oracle, run: RunRecord, *, hypothesis_id: str, phase: str = "affected", run_index: int = 0) -> OracleResult:
    """Evaluate ``oracle`` against ``run``. Never raises on bad oracle params —
    returns fired=False with a detail explaining why it could not run."""

    if run.error:
        return OracleResult(
            hypothesis_id=hypothesis_id,
            phase=phase,  # type: ignore[arg-type]
            oracle=oracle,
            fired=False,
            detail=f"run errored before oracle: {run.error}",
            run_index=run_index,
        )

    fired, detail = _check(oracle, run)
    return OracleResult(
        hypothesis_id=hypothesis_id,
        phase=phase,  # type: ignore[arg-type]
        oracle=oracle,
        fired=fired,
        detail=detail,
        run_index=run_index,
    )


def _check(oracle: Oracle, run: RunRecord) -> tuple[bool, str]:
    t = oracle.type

    if t is OracleType.EXIT_CODE:
        if oracle.expected_exit is None and not oracle.expect_nonzero_exit:
            return False, "oracle misconfigured: expected_exit unset"
        if oracle.expect_nonzero_exit:
            fired = run.exit_code is not None and run.exit_code != 0
            return fired, f"exit_code={run.exit_code}, expected nonzero -> {'fired' if fired else 'not fired'}"
        fired = run.exit_code == oracle.expected_exit
        return fired, f"exit_code={run.exit_code}, expected {oracle.expected_exit} -> {'fired' if fired else 'not fired'}"

    if t is OracleType.SIGNAL:
        want = (oracle.signal_name or "").upper().lstrip("SIG")
        got = (run.signal or "").upper().lstrip("SIG")
        if not want:
            return False, "oracle misconfigured: signal_name unset"
        fired = bool(got) and got == want
        return fired, f"signal={run.signal!r}, expected {want} -> {'fired' if fired else 'not fired'}"

    if t is OracleType.OUTPUT_REGEX:
        if not oracle.pattern:
            return False, "oracle misconfigured: pattern unset"
        try:
            rx = re.compile(oracle.pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            return False, f"oracle pattern invalid: {e}"
        hay = (run.stdout or "") + "\n" + (run.stderr or "")
        m = rx.search(hay)
        return (m is not None), (f"output matched {oracle.pattern!r} at {m.start()}" if m else f"pattern {oracle.pattern!r} not found")

    if t is OracleType.MARKER_FILE:
        # Marker checks are decided by the sandbox probe: the run's stdout must
        # carry the probe's verdict line. Fixed command set — the PoC cannot
        # forge this line because the probe wrapper prints it after the PoC.
        marker = oracle.marker_path or ""
        token = f"__MIMI_MARKER__:{marker}"
        present = token in (run.stdout or "")
        verdict = f"__MIMI_MARKER_VERDICT__:{marker}:" in (run.stdout or "")
        if not present and not verdict:
            return False, "marker probe verdict line missing from run output"
        fired = f"__MIMI_MARKER_VERDICT__:{marker}:present" in (run.stdout or "")
        return fired, f"marker {marker!r} -> {'present' if fired else 'absent'}"

    if t is OracleType.TIMING_THRESHOLD:
        if oracle.threshold_ms is None:
            return False, "oracle misconfigured: threshold_ms unset"
        fired = run.elapsed_ms >= oracle.threshold_ms
        return fired, f"elapsed_ms={run.elapsed_ms:.0f}, threshold={oracle.threshold_ms:.0f} -> {'fired' if fired else 'not fired'}"

    if t is OracleType.PROTOTYPE_POLLUTION_PROBE:
        token = "__MIMI_PROTO_POLLUTED__:true"
        fired = token in (run.stdout or "")
        return fired, f"prototype-pollution probe -> {'fired' if fired else 'not fired'}"

    if t is OracleType.PATH_TRAVERSAL_FILE_READ:
        # The probe wrapper prints this verdict after attempting the read.
        expect = oracle.expect_traversal_to or "/etc/passwd"
        token = f"__MIMI_TRAVERSAL__:{expect}:read"
        fired = token in (run.stdout or "")
        absent = f"__MIMI_TRAVERSAL__:{expect}:blocked" in (run.stdout or "")
        if fired:
            return True, f"traversal read succeeded for {expect!r}"
        return False, (f"traversal read blocked for {expect!r}" if absent else "traversal probe verdict missing")

    if t is OracleType.NETWORK_CALL:
        token = "__MIMI_NETWORK__:"
        if token not in (run.stdout or ""):
            return False, "network probe verdict missing"
        fired = f"{token}attempted" in (run.stdout or "")
        return fired, f"network probe -> {'attempted' if fired else 'not attempted'}"

    if t is OracleType.CUSTOM_PROBE:
        # Probe snippet must print its own verdict line matching the pattern.
        if not oracle.pattern:
            return False, "custom probe needs a pattern for its verdict line"
        try:
            rx = re.compile(oracle.pattern, re.MULTILINE)
        except re.error as e:
            return False, f"custom probe pattern invalid: {e}"
        fired = rx.search(run.stdout or "") is not None
        return fired, f"custom probe -> {'fired' if fired else 'not fired'}"

    return False, f"unknown oracle type {t}"


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
