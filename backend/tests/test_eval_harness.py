from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from harness import run_pipeline_case  # noqa: E402
from mimi import pipeline as pipeline_module


class FailedDossier:
    limitations = ["pipeline error: ValueError"]

    def model_dump(self, mode: str) -> dict:
        return {
            "limitations": self.limitations,
            "coverage": {},
            "cost": {},
            "oracle_results": [],
            "grounding": [],
            "claim": {},
        }


@pytest.mark.asyncio
async def test_eval_marks_pipeline_error_dossier_as_error(monkeypatch):
    class FakePipeline:
        def __init__(self, settings):
            pass

        async def run(self, submission, *, source: str, report_id: str):
            return FailedDossier()

    monkeypatch.setattr(pipeline_module, "Pipeline", FakePipeline)
    case = {
        "id": "pipeline-error",
        "kind": "real_reworded",
        "package_spec": "test-package@1.0.0",
        "report_text": "A test report",
        "expected": {},
    }

    result = await run_pipeline_case(case, SimpleNamespace())

    assert result["status"] == "error"
    assert result["status_reason"] == "pipeline error: ValueError"
