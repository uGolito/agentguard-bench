"""Provider boundary. Fake behavior is infrastructure testing, never model evidence."""

from typing import Any, Protocol

from agentguard.schemas import Scenario, Turn


class Provider(Protocol):
    requests: int
    events: list[dict[str, Any]]
    tokens: dict[str, int] | None
    estimated_cost_usd: float
    budget_charge_usd: float
    usage_complete: bool | None

    def next_turn(self, messages: list[dict[str, Any]]) -> Turn: ...


class ProviderError(Exception):
    """Sanitized failure with a stable runtime status; never an HTTP body or key."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ProviderState:
    def __init__(self) -> None:
        self.requests = 0
        self.events: list[dict[str, Any]] = []
        self.tokens: dict[str, int] | None = None
        self.estimated_cost_usd = 0.0
        self.budget_charge_usd = 0.0
        self.usage_complete: bool | None = None


class FakeProvider(ProviderState):
    def __init__(self, scenario: Scenario) -> None:
        super().__init__()
        self.script = iter(scenario.fake_script)

    def next_turn(self, messages: list[dict[str, Any]]) -> Turn:
        # Deliberately ignores content: this is a deterministic test double.
        self.requests += 1
        return next(self.script, Turn())
