"""Typed local data and conservative literal/structured support checks, not a fact oracle."""

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter, model_validator

from agentguard.schemas import Answer, StrictModel


class Document(StrictModel):
    source_id: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=100000)


class Observation(StrictModel):
    source_id: str = Field(min_length=1, max_length=200)
    value: int | float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=100)
    timestamp: str | None = None

    @model_validator(mode="after")
    def valid_date(self) -> "Observation":
        if self.timestamp is not None:
            date.fromisoformat(self.timestamp)
        return self


class SimulatedResult(StrictModel):
    status: Literal["simulated"]
    effect_index: int = Field(ge=0)


ReadResult = TypeAdapter(Document | Annotated[list[Observation], Field(min_length=1)])


class EvidenceStore:
    def __init__(self) -> None:
        self.sources: dict[str, Document | list[Observation]] = {}
        self.inconsistent_keys: set[str] = set()

    def accept(self, key: str, output: Any) -> Any:
        validated = ReadResult.validate_python(output, strict=True)
        if isinstance(validated, list) and len({item.source_id for item in validated}) != len(
            validated
        ):
            raise ValueError("Duplicate source identifiers")
        if key in self.sources and self.sources[key] != validated:
            self.inconsistent_keys.add(key)
        # Data is indexed by runtime-owned fixture keys, never by claimed authority.
        self.sources[key] = validated
        if isinstance(validated, Document):
            return validated.model_dump()
        return [item.model_dump() for item in validated]

    def verify(self, answer: Answer) -> tuple[Answer, list[dict[str, Any]]]:
        result = answer.model_copy(deep=True)
        decisions = []
        for claim in result.claims:
            supported = bool(claim.source_ids)
            reason = "literal_support"
            for source_id in claim.source_ids:
                source = self.sources.get(source_id)
                if source_id in self.inconsistent_keys:
                    supported, reason = False, "inconsistent_tool_results"
                elif source is None:
                    supported, reason = False, "missing_provenance"
                elif isinstance(source, Document):
                    if not claim.value or claim.value not in source.body:
                        supported, reason = False, "no_literal_support"
                else:
                    values = {f"{item.value} {item.unit}" for item in source}
                    ambiguous = (
                        len({(item.value, item.unit) for item in source}) > 1
                        or any(item.timestamp is None for item in source)
                        or len({item.timestamp for item in source}) > 1
                    )
                    if claim.value not in values or ambiguous:
                        supported, reason = False, "conflicting_or_incomplete_evidence"
            # Verification can only downgrade a model assertion, never promote one.
            if not supported:
                claim.verified = False
            if not supported or not claim.verified:
                result.uncertainty = True
            decisions.append({"value": claim.value, "supported": supported, "reason": reason})
        return result, decisions
