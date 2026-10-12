"""Extraction tolerates a model that echoes the enum list for vuln_class."""

from __future__ import annotations

from mimi.events import EventLog
from mimi.schemas import ReportSubmission, VulnClass
from mimi.stages.extract import _SCHEMA_HINT, extract_claim


class _FakeLLM:
    def __init__(self, data):
        self.data = data

    def chat_json(self, **_):
        return dict(self.data)


def _run(vuln_class):
    data = {"vuln_class": vuln_class, "expected_effect": "x"}
    sub = ReportSubmission(report_text="report", package_spec="minimist@1.2.5")
    return extract_claim(sub, _FakeLLM(data), EventLog("r1"))


def test_list_vuln_class_is_coerced():
    assert _run(["prototype_pollution"]).vuln_class is VulnClass.PROTOTYPE_POLLUTION


def test_unknown_list_falls_back_to_other():
    assert _run(["nonsense"]).vuln_class is VulnClass.OTHER


def test_schema_hint_asks_for_one_value():
    assert "exactly ONE" in _SCHEMA_HINT
