"""Configuration: environment, model routing table, limits.

Secrets are read from environment variables or an ignored local ``.env`` file:

- ``NEBIUS_API_KEY``      Token Factory key; also the bearer for Sandboxes.
- ``NEBIUS_PROJECT_ID``   Nebius project id (Sandboxes require it as a ``Project`` header).
- ``TAVILY_API_KEY``      Tavily key.

``.env`` is git-ignored and loaded for local development; nothing here writes
secrets anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from dotenv import load_dotenv


# Load a developer's ignored root .env, if present. Existing environment
# variables remain authoritative (python-dotenv does not override by default).
load_dotenv()


# ---------------------------------------------------------------------------
# Verified 2026-10-15 against Token Factory (see docs/00-constraints-and-open-items.md).
# IDs are case-sensitive and inconsistent across models; never guess an ID.
# ---------------------------------------------------------------------------
INFERENCE_BASE_URL = "https://api.tokenfactory.nebius.com/v1"

NEMOTRON_MODELS = {
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "super": "nvidia/nemotron-3-super-120b-a12b",
    "ultra": "nvidia/Nemotron-3-Ultra-550b-a55b",
    "lightning": "nvidia/Nemotron-3_5-Lightning",
}

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# Sandboxes HTTP surface (contree): whoami and images are known-good endpoints.
SANDBOXES_BASE_URL = os.environ.get("SANDBOXES_BASE_URL", "https://api.sandbox.nebius.ai/v1")


class Stage(str, Enum):
    EXTRACT = "extract"
    GROUND = "ground"
    RESEARCH = "research"
    HYPOTHESIZE = "hypothesize"
    BUILD = "build"
    FORK_RUN = "fork_run"
    DIFFERENTIAL = "differential"
    VERDICT = "verdict"
    REPLY = "reply"


# Model routing table (stage -> Nemotron tier). Evaluated in the E3 ablation.
STAGE_MODEL_TABLE: dict[Stage, str] = {
    Stage.EXTRACT: "nano",
    Stage.GROUND: "nano",
    Stage.RESEARCH: "super",
    Stage.HYPOTHESIZE: "ultra",
    Stage.BUILD: "nano",
    Stage.FORK_RUN: "nano",
    Stage.DIFFERENTIAL: "nano",
    Stage.VERDICT: "super",
    Stage.REPLY: "super",
}

# Stages that may escalate to Ultra when evidence is ambiguous (stage 8 rule).
ESCALATION_MODEL = "ultra"


@dataclass
class Settings:
    """Runtime settings. ``from_env`` is the only constructor the app uses."""

    nebius_api_key: Optional[str] = None
    nebius_project_id: Optional[str] = None
    tavily_api_key: Optional[str] = None

    inference_base_url: str = INFERENCE_BASE_URL
    sandboxes_base_url: str = SANDBOXES_BASE_URL
    tavily_url: str = TAVILY_SEARCH_URL

    # Routing overrides for the E3 ablation: force a single model tier.
    force_model: Optional[str] = None

    # Execution limits (security model).
    poc_timeout_s: int = 60
    build_timeout_s: int = 900
    output_cap_bytes: int = 32_768
    max_hypotheses: int = 8
    max_parallel_forks: int = 8
    max_runs_per_report: int = 24
    # Best-effort threshold in raw Contree cost units, not USD. Missing cost
    # telemetry or in-flight work can exceed it; see RunBudget documentation.
    per_report_cost_cap: float = 5.00

    db_path: str = "mimi.db"

    @classmethod
    def from_env(cls, **overrides) -> "Settings":
        s = cls(
            nebius_api_key=os.environ.get("NEBIUS_API_KEY"),
            nebius_project_id=os.environ.get("NEBIUS_PROJECT_ID"),
            tavily_api_key=os.environ.get("TAVILY_API_KEY"),
            force_model=os.environ.get("MIMI_FORCE_MODEL") or None,
            db_path=os.environ.get("MIMI_DB_PATH", "mimi.db"),
        )
        for k, v in overrides.items():
            if not hasattr(s, k):
                raise AttributeError(f"unknown setting: {k}")
            setattr(s, k, v)
        return s

    def model_for(self, stage: Stage) -> str:
        if self.force_model and self.force_model in NEMOTRON_MODELS:
            return self.force_model
        return STAGE_MODEL_TABLE[stage]

    def model_id(self, stage: Stage) -> str:
        return NEMOTRON_MODELS[self.model_for(stage)]

    def require_inference(self) -> None:
        if not self.nebius_api_key:
            raise RuntimeError("NEBIUS_API_KEY is not set (env var only; never paste keys in chat)")

    def require_tavily(self) -> None:
        if not self.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not set (env var only; never paste keys in chat)")

    def require_sandboxes(self) -> None:
        if not self.nebius_api_key or not self.nebius_project_id:
            raise RuntimeError(
                "Sandboxes need NEBIUS_API_KEY and NEBIUS_PROJECT_ID (env vars only)"
            )
