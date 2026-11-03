"""Configuration snapshots; live providers are intentionally unavailable."""

from typing import Literal

from pydantic import Field

from agentguard.schemas import StrictModel


class RunConfig(StrictModel):
    mode: Literal["baseline"] = "baseline"
    provider: Literal["fake"] = "fake"
    model: Literal["scripted-fixture-v1"] = "scripted-fixture-v1"
    prompt_version: str = "baseline-v1"
    max_steps: int = Field(default=8, ge=1, le=100)
    max_requests: int = Field(default=100, ge=1)
    max_cost: float = Field(default=0.0, ge=0)
    trials: int = Field(default=1, ge=1, le=100)
    model_parameters: dict[str, str] = {}
