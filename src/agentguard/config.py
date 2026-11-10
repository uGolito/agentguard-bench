"""Explicit live opt-in and reproducible generation/budget settings."""

from typing import Literal

from pydantic import Field, model_validator

from agentguard.schemas import StrictModel


class RunConfig(StrictModel):
    mode: Literal["baseline", "guarded", "guarded_oversight"] = "baseline"
    provider: Literal["fake", "anthropic"] = "fake"
    model: str = "scripted-fixture-v1"
    prompt_version: Literal["baseline-v3"] = "baseline-v3"
    output_protocol: Literal["prompt-json-v1", "anthropic-json-schema-v1"] = "prompt-json-v1"
    max_steps: int = Field(default=8, ge=1, le=100)
    max_requests: int = Field(default=100, ge=1)
    max_cost: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    trials: int = Field(default=1, ge=1, le=100)
    allow_live: bool = False
    max_tokens: int = Field(default=512, ge=64, le=4096)
    temperature: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    timeout_seconds: float = Field(default=30.0, gt=0, le=120, allow_inf_nan=False)
    max_retries: int = Field(default=0, ge=0, le=3)
    retry_delay_seconds: float = Field(default=1.0, ge=0, le=10, allow_inf_nan=False)
    reviewer_timeout_seconds: float = Field(default=2.0, gt=0, le=30, allow_inf_nan=False)
    reviewer_provider: Literal["injected", "anthropic"] = "injected"
    reviewer_model: str = "claude-haiku-4-5-20251001"
    reviewer_max_tokens: int = Field(default=256, ge=64, le=4096)
    order_seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    model_seed: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_live_settings(self) -> "RunConfig":
        if self.output_protocol != "prompt-json-v1" and self.provider != "anthropic":
            raise ValueError("Native JSON schema output requires provider=anthropic")
        if self.provider == "anthropic":
            if self.model_seed is not None:
                raise ValueError(
                    "Anthropic does not expose a supported model seed; use --order-seed"
                )
            if not self.allow_live or self.max_cost <= 0:
                raise ValueError("Anthropic requires --allow-live and --max-cost > 0")
            if self.model != "claude-haiku-4-5-20251001":
                raise ValueError("Supported priced snapshot: claude-haiku-4-5-20251001")
        elif self.model != "scripted-fixture-v1":
            raise ValueError("Fake provider requires model scripted-fixture-v1")
        if self.reviewer_provider == "anthropic" and (
            self.provider != "anthropic"
            or self.mode != "guarded_oversight"
            or self.reviewer_model != "claude-haiku-4-5-20251001"
        ):
            raise ValueError(
                "Real review requires opted-in Anthropic oversight and a priced snapshot"
            )
        return self
