"""Deterministic oracle checkers.

Safety property: ``check_oracle`` is a pure function over a RunRecord. It
never raises — a misconfigured or invalid oracle returns ``fired=False`` with
an explanatory detail. Every OracleType gets a fired case and a not-fired case.

Evidence honesty: a result is conclusive only when the PoC ran, the oracle was
correctly configured, and the evidence was complete. Truncated output, missing
probe verdicts and misconfigured oracles are inconclusive — never "did not
fire". Probe oracles read ``RunRecord.probe_output`` (the trusted post-PoC
channel), never the PoC's own stdout, which can forge any token.
"""

from __future__ import annotations

import pytest

from mimi.oracles import check_oracle, summarize
from mimi.schemas import Oracle, OracleType, RunRecord


def run(**kw) -> RunRecord:
    base = dict(
        hypothesis_id="h1",
        phase="poc",
        command="node poc.js",
        exit_code=0,
        stdout="",
        stderr="",
        probe_output="",
        elapsed_ms=10.0,
    )
    base.update(kw)
    return RunRecord(**base)


def check(oracle: Oracle, r: RunRecord, phase: str = "affected"):
    return check_oracle(oracle, r, hypothesis_id="h1", phase=phase, run_index=0)


# ---------------------------------------------------------------------------
# exit_code
# ---------------------------------------------------------------------------

def test_exit_code_fired():
    o = Oracle(type=OracleType.EXIT_CODE, expected_exit=2)
    res = check(o, run(exit_code=2))
    assert res.fired is True
    assert "fired" in res.detail
    assert res.hypothesis_id == "h1"
    assert res.phase == "affected"


def test_exit_code_not_fired():
    o = Oracle(type=OracleType.EXIT_CODE, expected_exit=2)
    res = check(o, run(exit_code=0))
    assert res.fired is False
    assert "not fired" in res.detail


def test_exit_code_nonzero_fired():
    o = Oracle(type=OracleType.EXIT_CODE, expect_nonzero_exit=True)
    assert check(o, run(exit_code=1)).fired is True
    assert check(o, run(exit_code=0)).fired is False


def test_exit_code_misconfigured_not_fired_with_detail():
    o = Oracle(type=OracleType.EXIT_CODE)  # no expected_exit, no expect_nonzero_exit
    res = check(o, run(exit_code=2))
    assert res.fired is False
    assert "misconfigured" in res.detail


# ---------------------------------------------------------------------------
# signal
# ---------------------------------------------------------------------------

def test_signal_fired():
    o = Oracle(type=OracleType.SIGNAL, signal_name="SIGSEGV")
    res = check(o, run(exit_code=None, signal="SIGSEGV"))
    assert res.fired is True


def test_signal_fired_case_insensitive():
    o = Oracle(type=OracleType.SIGNAL, signal_name="segv")
    assert check(o, run(exit_code=None, signal="SIGSEGV")).fired is True


def test_signal_not_fired_wrong_signal():
    o = Oracle(type=OracleType.SIGNAL, signal_name="SIGSEGV")
    assert check(o, run(exit_code=None, signal="SIGABRT")).fired is False


def test_signal_not_fired_no_signal():
    o = Oracle(type=OracleType.SIGNAL, signal_name="SIGSEGV")
    assert check(o, run(exit_code=1, signal=None)).fired is False


def test_signal_misconfigured():
    o = Oracle(type=OracleType.SIGNAL)  # signal_name unset
    res = check(o, run(signal="SIGSEGV"))
    assert res.fired is False
    assert "misconfigured" in res.detail


# ---------------------------------------------------------------------------
# output_regex
# ---------------------------------------------------------------------------

def test_output_regex_fired_on_stdout():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    assert check(o, run(stdout="start\nVULN_TRIGGERED\n")).fired is True


def test_output_regex_fired_on_stderr():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    assert check(o, run(stderr="boom VULN_TRIGGERED")).fired is True


def test_output_regex_not_fired():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    assert check(o, run(stdout="nothing to see")).fired is False


def test_output_regex_invalid_pattern_not_fired_with_detail():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="[unclosed(")
    res = check(o, run(stdout="VULN_TRIGGERED"))
    assert res.fired is False
    assert "pattern invalid" in res.detail


def test_output_regex_misconfigured_unset_pattern():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern=None)
    res = check(o, run(stdout="x"))
    assert res.fired is False
    assert "misconfigured" in res.detail


# ---------------------------------------------------------------------------
# marker_file (trusted probe channel)
# ---------------------------------------------------------------------------

def test_marker_file_fired():
    o = Oracle(type=OracleType.MARKER_FILE, marker_path="/tmp/pwned")
    r = run(probe_output="__MIMI_MARKER_VERDICT__:/tmp/pwned:present\n")
    res = check(o, r)
    assert res.fired is True
    assert res.conclusive is True


def test_marker_file_not_fired_when_absent():
    o = Oracle(type=OracleType.MARKER_FILE, marker_path="/tmp/pwned")
    r = run(probe_output="__MIMI_MARKER_VERDICT__:/tmp/pwned:absent\n")
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is True
    assert "absent" in res.detail


def test_marker_file_inconclusive_when_verdict_line_missing():
    o = Oracle(type=OracleType.MARKER_FILE, marker_path="/tmp/pwned")
    res = check(o, run(probe_output="no probe output at all"))
    assert res.fired is False
    assert res.conclusive is False
    assert "verdict missing" in res.detail


def test_marker_file_not_forgeable_from_stdout():
    # A PoC that prints the verdict token must not be able to claim the marker.
    o = Oracle(type=OracleType.MARKER_FILE, marker_path="/tmp/pwned")
    r = run(stdout="__MIMI_MARKER_VERDICT__:/tmp/pwned:present\n", probe_output="")
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is False


# ---------------------------------------------------------------------------
# timing_threshold
# ---------------------------------------------------------------------------

def test_timing_threshold_fired():
    o = Oracle(type=OracleType.TIMING_THRESHOLD, threshold_ms=100.0)
    assert check(o, run(elapsed_ms=150.0)).fired is True


def test_timing_threshold_not_fired():
    o = Oracle(type=OracleType.TIMING_THRESHOLD, threshold_ms=100.0)
    assert check(o, run(elapsed_ms=20.0)).fired is False


def test_timing_threshold_misconfigured():
    o = Oracle(type=OracleType.TIMING_THRESHOLD, threshold_ms=None)
    res = check(o, run(elapsed_ms=9999.0))
    assert res.fired is False
    assert res.conclusive is False
    assert "misconfigured" in res.detail


def test_timing_threshold_rejects_nonpositive():
    # A zero/negative threshold would fire on every run, inventing evidence.
    o = Oracle(type=OracleType.TIMING_THRESHOLD, threshold_ms=0)
    res = check(o, run(elapsed_ms=1.0))
    assert res.fired is False
    assert res.conclusive is False
    assert "threshold_ms must be > 0" in res.detail


# ---------------------------------------------------------------------------
# prototype_pollution_probe (trusted probe channel)
# ---------------------------------------------------------------------------

def test_proto_probe_fired():
    o = Oracle(type=OracleType.PROTOTYPE_POLLUTION_PROBE)
    res = check(o, run(probe_output="__MIMI_PROTO_POLLUTED__:true"))
    assert res.fired is True
    assert res.conclusive is True


def test_proto_probe_not_fired():
    o = Oracle(type=OracleType.PROTOTYPE_POLLUTION_PROBE)
    res = check(o, run(probe_output="__MIMI_PROTO_POLLUTED__:false"))
    assert res.fired is False
    assert res.conclusive is True
    assert "not fired" in res.detail


def test_proto_probe_not_forgeable_from_stdout():
    o = Oracle(type=OracleType.PROTOTYPE_POLLUTION_PROBE)
    res = check(o, run(stdout="__MIMI_PROTO_POLLUTED__:true", probe_output=""))
    assert res.fired is False
    assert res.conclusive is False


# ---------------------------------------------------------------------------
# path_traversal_file_read (trusted probe channel)
# ---------------------------------------------------------------------------

def test_traversal_fired():
    o = Oracle(type=OracleType.PATH_TRAVERSAL_FILE_READ, expect_traversal_to="/etc/passwd")
    r = run(probe_output="__MIMI_TRAVERSAL__:/etc/passwd:read\n")
    assert check(o, r).fired is True


def test_traversal_not_fired_when_blocked():
    o = Oracle(type=OracleType.PATH_TRAVERSAL_FILE_READ, expect_traversal_to="/etc/passwd")
    res = check(o, run(probe_output="__MIMI_TRAVERSAL__:/etc/passwd:blocked\n"))
    assert res.fired is False
    assert res.conclusive is True
    assert "blocked" in res.detail


def test_traversal_inconclusive_when_verdict_missing():
    o = Oracle(type=OracleType.PATH_TRAVERSAL_FILE_READ, expect_traversal_to="/etc/passwd")
    res = check(o, run(probe_output="nothing"))
    assert res.fired is False
    assert res.conclusive is False
    assert "verdict missing" in res.detail


def test_traversal_not_forgeable_from_stdout():
    o = Oracle(type=OracleType.PATH_TRAVERSAL_FILE_READ, expect_traversal_to="/etc/passwd")
    res = check(o, run(stdout="__MIMI_TRAVERSAL__:/etc/passwd:read\n", probe_output=""))
    assert res.fired is False
    assert res.conclusive is False


# ---------------------------------------------------------------------------
# network_call (trusted probe channel)
# ---------------------------------------------------------------------------

def test_network_call_fired():
    o = Oracle(type=OracleType.NETWORK_CALL)
    assert check(o, run(probe_output="__MIMI_NETWORK__:attempted")).fired is True


def test_network_call_not_fired():
    o = Oracle(type=OracleType.NETWORK_CALL)
    res = check(o, run(probe_output="__MIMI_NETWORK__:not attempted"))
    assert res.fired is False
    assert res.conclusive is True


def test_network_call_inconclusive_without_probe_line():
    o = Oracle(type=OracleType.NETWORK_CALL)
    res = check(o, run(stdout="socket created", probe_output=""))
    assert res.fired is False
    assert res.conclusive is False
    assert "verdict missing" in res.detail


def test_network_call_not_forgeable_from_stdout():
    o = Oracle(type=OracleType.NETWORK_CALL)
    res = check(o, run(stdout="__MIMI_NETWORK__:attempted", probe_output=""))
    assert res.fired is False
    assert res.conclusive is False


# ---------------------------------------------------------------------------
# custom_probe (trusted probe channel)
# ---------------------------------------------------------------------------

def test_custom_probe_fired():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="PROBE_OK")
    res = check(o, run(probe_output="__MIMI_CUSTOM_PROBE_BEGIN__:\nstep 1\nPROBE_OK\n__MIMI_CUSTOM_PROBE_END__:ran"))
    assert res.fired is True
    assert res.conclusive is True


def test_custom_probe_not_fired():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="PROBE_OK")
    res = check(o, run(probe_output="__MIMI_CUSTOM_PROBE_BEGIN__:\nstep 1\nPROBE_FAIL\n__MIMI_CUSTOM_PROBE_END__:ran"))
    assert res.fired is False
    assert res.conclusive is True


def test_custom_probe_not_forgeable_from_stdout():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="PROBE_OK")
    res = check(
        o,
        run(
            stdout="PROBE_OK",
            probe_output="__MIMI_CUSTOM_PROBE_BEGIN__:\nstep 1\nPROBE_FAIL\n__MIMI_CUSTOM_PROBE_END__:ran",
        ),
    )
    # stdout is ignored; the trusted channel decides.
    assert res.fired is False


def test_custom_probe_pattern_cannot_match_a_sibling_probe_token():
    # The fixed probes share this stream. A pattern like "attempted" must not
    # fire on the network probe's verdict — that would grade a different
    # question than the one the hypothesis declared.
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="attempted")
    res = check(
        o,
        run(
            probe_output=(
                "__MIMI_NETWORK__:attempted\n"
                "__MIMI_CUSTOM_PROBE_BEGIN__:\nstep 1\nnothing here\n"
                "__MIMI_CUSTOM_PROBE_END__:ran\n"
            ),
        ),
    )
    assert res.fired is False
    assert res.conclusive is True


def test_custom_probe_unterminated_output_is_inconclusive():
    # No end marker means the snippet's window cannot be delimited. Reading
    # that as "did not fire" would grade missing evidence as a negative.
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="PROBE_OK")
    res = check(o, run(probe_output="__MIMI_CUSTOM_PROBE_BEGIN__:\nstep 1\nPROBE_OK"))
    assert res.fired is False
    assert res.conclusive is False
    assert "terminated" in res.detail


def test_custom_probe_invalid_pattern_not_fired():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="*bad(")
    res = check(o, run(probe_output="PROBE_OK"))
    assert res.fired is False
    assert res.conclusive is False
    assert "pattern invalid" in res.detail


def test_custom_probe_misconfigured_unset_pattern():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern=None)
    res = check(o, run(probe_output="anything"))
    assert res.fired is False
    assert res.conclusive is False
    assert "pattern unset" in res.detail


def test_custom_probe_inconclusive_without_probe_output():
    o = Oracle(type=OracleType.CUSTOM_PROBE, pattern="PROBE_OK")
    res = check(o, run(probe_output=""))
    assert res.fired is False
    assert res.conclusive is False


# ---------------------------------------------------------------------------
# errored / truncated runs
# ---------------------------------------------------------------------------

def test_errored_run_never_fires():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    r = run(stdout="VULN_TRIGGERED", error="sandbox timeout")
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is False
    assert "run errored before oracle" in res.detail


def test_errored_run_never_fires_even_on_exit_code_oracle():
    o = Oracle(type=OracleType.EXIT_CODE, expected_exit=0)
    r = run(exit_code=0, error="transport died")
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is False
    assert "run errored before oracle" in res.detail


def test_truncated_run_is_inconclusive_not_a_negative():
    # Truncated output means the checker may have missed a match — reading it
    # as "did not fire" would turn a cut-off run into false negative evidence.
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    r = run(stdout="noise noise\nVULN_TRIGGERED", truncated=True)
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is False
    assert "truncated" in res.detail


def test_truncated_run_without_marker_is_also_inconclusive():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    r = run(stdout="noise noise", truncated=True)
    res = check(o, r)
    assert res.fired is False
    assert res.conclusive is False


def test_untruncated_run_without_match_is_a_real_negative():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="VULN_TRIGGERED")
    res = check(o, run(stdout="noise noise", truncated=False))
    assert res.fired is False
    assert res.conclusive is True


# ---------------------------------------------------------------------------
# result plumbing and summarize()
# ---------------------------------------------------------------------------

def test_result_carries_phase_and_run_index():
    o = Oracle(type=OracleType.EXIT_CODE, expected_exit=0)
    res = check_oracle(o, run(), hypothesis_id="h9", phase="fixed", run_index=7)
    assert res.phase == "fixed"
    assert res.run_index == 7
    assert res.hypothesis_id == "h9"
    assert res.oracle.type is OracleType.EXIT_CODE


def test_all_oracle_types_have_a_summary():
    for t in OracleType:
        o = Oracle(type=t, expected_exit=1, signal_name="SIGSEGV", pattern="x",
                   marker_path="/tmp/x", threshold_ms=5.0, expect_traversal_to="/etc/passwd")
        s = summarize(o)
        assert isinstance(s, str) and s


@pytest.mark.parametrize("bad_pattern_type", [OracleType.OUTPUT_REGEX, OracleType.CUSTOM_PROBE])
def test_invalid_regex_never_raises(bad_pattern_type):
    for pattern in ("(", "[z-a]", "(?P<1>x)", "*", "\\"):
        o = Oracle(type=bad_pattern_type, pattern=pattern)
        res = check(o, run(stdout="anything"))
        assert res.fired is False
        assert res.detail


@pytest.mark.parametrize("slow_type", [OracleType.OUTPUT_REGEX, OracleType.CUSTOM_PROBE])
def test_catastrophic_patterns_are_rejected(slow_type):
    # (a+)+$ style patterns can hang the checker; refuse them up front.
    o = Oracle(type=slow_type, pattern=r"^(a+)+$")
    res = check(o, run(stdout="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!", probe_output="x"))
    assert res.fired is False
    assert res.conclusive is False
    assert "backtrack" in res.detail


def test_oversized_pattern_rejected():
    o = Oracle(type=OracleType.OUTPUT_REGEX, pattern="x" * 400)
    res = check(o, run(stdout="x"))
    assert res.fired is False
    assert res.conclusive is False
    assert "too long" in res.detail


def test_output_regex_uncaught_exception_is_inconclusive_not_negative():
    from mimi.oracles import check_oracle
    from mimi.schemas import Oracle, OracleType, RunRecord

    o = Oracle(type=OracleType.OUTPUT_REGEX, description="d", pattern="VULN_TRIGGERED")
    crashed = RunRecord(
        hypothesis_id="h1", phase="poc", command="node poc.js", exit_code=1,
        stderr="TypeError: x.strip is not a function\n    at Object.<anonymous> (/work/poc.js:4:11)",
    )
    r = check_oracle(o, crashed, hypothesis_id="h1")
    assert r.conclusive is False and r.fired is False

    clean = RunRecord(hypothesis_id="h1", phase="poc", command="node poc.js", exit_code=0, stdout="SAFE")
    assert check_oracle(o, clean, hypothesis_id="h1").conclusive is True
