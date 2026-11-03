"""Provider boundary. Fake behavior is infrastructure testing, never model evidence."""

from typing import Any, Protocol

from agentguard.schemas import Scenario, Turn


class Provider(Protocol):
    def next_turn(self, messages: list[dict[str, Any]]) -> Turn: ...


class FakeProvider:
    def __init__(self, scenario: Scenario) -> None:
        self.script = iter(scenario.fake_script)

    def next_turn(self, messages: list[dict[str, Any]]) -> Turn:
        # Deliberately ignores content: this is a deterministic test double.
        return next(self.script, Turn())
