import pytest

from mimi.events import EventLog
from mimi.schemas import ReportSubmission, VulnClass
from mimi.stages.extract import extract_claim


class FakeExtractLLM:
    def __init__(self, vuln_class):
        self.vuln_class = vuln_class

    def chat_json(self, **kwargs):
        return {
            "vuln_class": self.vuln_class,
            "expected_effect": "The claimed vulnerable behavior occurs.",
        }


@pytest.mark.parametrize(
    ("raw_class", "expected_class", "warning"),
    [
        (["redos", "denial_of_service"], VulnClass.REDOS, "multiple vulnerability classes"),
        ([], VulnClass.OTHER, "no vulnerability class"),
    ],
)
def test_extract_claim_normalizes_list_vuln_class_and_records_warning(
    raw_class, expected_class, warning
):
    events = EventLog("extract-test")
    claim = extract_claim(
        ReportSubmission(report_text="A public test report", package_spec="pkg@1.0.0"),
        FakeExtractLLM(raw_class),
        events,
    )

    assert claim.vuln_class is expected_class
    assert any(warning in item for item in claim.parse_warnings)
    assert events.events[-1].status == "ok"
