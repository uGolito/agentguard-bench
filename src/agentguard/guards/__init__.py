"""Provider-independent deterministic controls and optional independent review."""

from typing import Any

from pydantic import ValidationError

from agentguard.guards.evidence import EvidenceStore, SimulatedResult
from agentguard.guards.oversight import Reviewer, ReviewRequest, review_action
from agentguard.guards.policy import Authorization, Policy, action_key
from agentguard.schemas import Answer, ToolCall
from agentguard.tools import INPUTS, SENSITIVE


class Controls:
    def __init__(
        self,
        policy: Policy,
        scenario_id: str,
        objective: str,
        oversight: bool,
        reviewer: Reviewer | None,
        timeout: float,
    ) -> None:
        self.authorization = Authorization(policy, scenario_id)
        self.evidence = EvidenceStore()
        self.scenario_id = scenario_id
        self.objective = objective
        self.oversight = oversight
        self.reviewer = reviewer
        self.timeout = timeout

    def before(self, call: ToolCall) -> tuple[bool, str, list[dict[str, Any]]]:
        try:
            INPUTS[call.name].model_validate(call.arguments)
        except ValidationError:
            return False, "invalid_input_schema", []
        if self.authorization.protected(call.arguments):
            return False, "protected_literal", []
        if call.name not in SENSITIVE:
            return True, "read_only", []
        allowed, reason = self.authorization.permits(call)
        reviews = []
        if allowed and self.oversight:
            request = ReviewRequest(
                scenario_id=self.scenario_id,
                objective=self.objective,
                action_json=action_key(call),
                grant_id=reason,
            )
            review = review_action(self.reviewer, request, self.timeout)
            reviews.append(review)
            if not review["allowed"]:
                return False, review["reason"], reviews
        return allowed, reason, reviews

    def after(self, call: ToolCall, output: Any, effect_count: int) -> Any:
        if call.name in SENSITIVE:
            validated = SimulatedResult.model_validate(output)
            if validated.effect_index != effect_count - 1:
                raise ValueError("Inconsistent simulated confirmation")
            return validated.model_dump()
        data = self.evidence.accept(call.arguments["key"], output)
        return {"trust": "untrusted", "fixture_key": call.arguments["key"], "data": data}

    def answer(self, proposed: Answer) -> tuple[Answer, list[dict[str, Any]], bool]:
        if self.authorization.protected(proposed.model_dump()):
            return Answer(claims=[], refused=True), [{"reason": "protected_literal"}], True
        answer, decisions = self.evidence.verify(proposed)
        return answer, decisions, False
