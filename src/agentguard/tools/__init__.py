"""Synthetic-only tools. No network, filesystem writes, or real-world actions."""

from copy import deepcopy
from typing import Any

from pydantic import Field

from agentguard.schemas import StrictModel, ToolCall


class Lookup(StrictModel):
    key: str = Field(min_length=1, max_length=200)


class Email(StrictModel):
    recipient: str = Field(min_length=1, max_length=200)
    body: str = Field(max_length=10000)


class Update(StrictModel):
    record_id: str = Field(min_length=1, max_length=200)
    value: str = Field(max_length=10000)


SENSITIVE = frozenset({"send_email", "update_record"})
INPUTS = {
    "search_documents": Lookup,
    "fetch_report": Lookup,
    "query_database": Lookup,
    "retrieve_metadata": Lookup,
    "send_email": Email,
    "update_record": Update,
}
TOOL_DEFINITIONS = [
    {"name": name, "input_schema": schema.model_json_schema()} for name, schema in INPUTS.items()
]


class SyntheticTools:
    def __init__(self, fixtures: dict[str, Any]) -> None:
        self.fixtures = deepcopy(fixtures)
        self.effects: list[dict[str, Any]] = []

    def execute(self, call: ToolCall) -> Any:
        arguments = INPUTS[call.name].model_validate(call.arguments).model_dump()
        if call.name in SENSITIVE:
            effect = {"tool": call.name, "arguments": arguments, "simulated": True}
            self.effects.append(effect)
            return {"status": "simulated", "effect_index": len(self.effects) - 1}
        # Raw fixture outputs intentionally allow malformed data for adversarial tests.
        return self.fixtures[arguments["key"]]
