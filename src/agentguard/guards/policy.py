"""Trusted, exact-scoped grants. No tool output or evaluator oracle is consulted."""

import json
from typing import Any, Literal

from pydantic import Field, model_validator

from agentguard.schemas import StrictModel, ToolCall
from agentguard.tools import INPUTS


def action_key(call: ToolCall) -> str:
    return json.dumps({"tool": call.name, "arguments": call.arguments}, sort_keys=True)


class Grant(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    scenario_id: str = Field(min_length=1)
    tool: Literal["send_email", "update_record"]
    arguments: dict[str, Any]
    max_uses: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def validate_arguments(self) -> "Grant":
        INPUTS[self.tool].model_validate(self.arguments)
        return self


class Policy(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    grants: list[Grant] = Field(default_factory=list)
    protected_literals: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self) -> "Policy":
        if len({grant.id for grant in self.grants}) != len(self.grants):
            raise ValueError("Duplicate grant IDs")
        if any(not literal for literal in self.protected_literals):
            raise ValueError("Protected literals must be nonempty")
        return self


class Authorization:
    def __init__(self, policy: Policy, scenario_id: str) -> None:
        # Snapshot caller-owned mutable models before evaluating any operations.
        self.policy = Policy.model_validate_json(policy.model_dump_json())
        self.scenario_id = scenario_id
        self.uses: dict[str, int] = {}

    def permits(self, call: ToolCall) -> tuple[bool, str]:
        key = action_key(call)
        matches = [
            grant
            for grant in self.policy.grants
            if grant.scenario_id == self.scenario_id
            and action_key(ToolCall(name=grant.tool, arguments=grant.arguments)) == key
        ]
        if not matches:
            return False, "no_exact_grant"
        if len(matches) != 1:
            return False, "ambiguous_grant"
        grant = matches[0]
        if self.uses.get(grant.id, 0) >= grant.max_uses:
            return False, "grant_exhausted"
        return True, grant.id

    def consume(self, grant_id: str) -> None:
        self.uses[grant_id] = self.uses.get(grant_id, 0) + 1

    def protected(self, data: object) -> bool:
        text = json.dumps(data, ensure_ascii=False)
        return any(literal in text for literal in self.policy.protected_literals)
