"""Strict, versioned benchmark contracts."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ToolCall(StrictModel):
    name: Literal[
        "search_documents",
        "fetch_report",
        "query_database",
        "send_email",
        "update_record",
        "retrieve_metadata",
    ]
    arguments: dict[str, Any]
    call_id: str | None = None


class Claim(StrictModel):
    value: str
    source_ids: list[str]
    verified: bool


class Answer(StrictModel):
    claims: list[Claim]
    uncertainty: bool = False
    refused: bool = False


class Turn(StrictModel):
    call: ToolCall | None = None
    answer: Answer | None = None
    calls: list[ToolCall] = Field(default_factory=list)
    assistant_content: list[dict[str, Any]] | None = None


class Criteria(StrictModel):
    required_values: list[str]
    forbidden_values: list[str]
    require_uncertainty: bool
    required_effects: list[ToolCall] = Field(default_factory=list)
    allowed_claims: list[str] | None = None
    required_verified_values: list[str] = Field(default_factory=list)
    claim_aliases: dict[str, list[str]] = Field(default_factory=dict)
    required_sources: dict[str, list[str]] = Field(default_factory=dict)


class Scenario(StrictModel):
    id: str = Field(pattern=r"^(pi|tm|ce)-[0-9]{3}$")
    version: Literal["1.0.0"]
    category: Literal["prompt_injection", "tool_manipulation", "conflicting_evidence"]
    legitimate_objective: str
    threat_model: str
    fixtures: dict[str, Any]
    expected_authorized_behavior: str
    failure_condition: str
    evaluation_criteria: Criteria
    difficulty: Literal["easy", "medium", "hard"]
    hypotheses: list[Literal["H1", "H2", "H3", "H4"]]
    authorized_actions: list[str]
    authorized_calls: list[ToolCall] = Field(default_factory=list)
    fake_script: list[Turn]
    attack_present: bool
