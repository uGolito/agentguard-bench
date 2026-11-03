"""Independent reviewer contract. No provider dependency or tool handles are exposed."""

import asyncio
from time import perf_counter
from typing import Any, Literal, Protocol

from pydantic import ConfigDict, Field

from agentguard.schemas import StrictModel


class ReviewRequest(StrictModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    scenario_id: str
    objective: str
    action_json: str
    grant_id: str


class ReviewDecision(StrictModel):
    allowed: bool
    reason: str = Field(min_length=1, max_length=500)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0, allow_inf_nan=False)


class Reviewer(Protocol):
    @property
    def metadata(self) -> dict[str, Any]: ...

    async def review(self, request: ReviewRequest) -> ReviewDecision: ...


class FakeReviewer:
    def __init__(self, behavior: Literal["allow", "deny", "error", "timeout"] = "allow") -> None:
        self.behavior = behavior

    @property
    def metadata(self) -> dict[str, Any]:
        return {"kind": "deterministic_fake", "version": "1", "behavior": self.behavior}

    async def review(self, request: ReviewRequest) -> ReviewDecision:
        if self.behavior == "error":
            raise RuntimeError("Synthetic reviewer failure")
        if self.behavior == "timeout":
            await asyncio.sleep(60)
        return ReviewDecision(allowed=self.behavior == "allow", reason=f"fake_{self.behavior}")


def review_action(
    reviewer: Reviewer | None, request: ReviewRequest, timeout: float
) -> dict[str, Any]:
    started = perf_counter()
    record: dict[str, Any] = {
        "allowed": False,
        "reason": "reviewer_unavailable",
        "decision": None,
        "request": request.model_dump(),
        "invoked": False,
    }
    if reviewer is not None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            record.update(reason="reviewer_context_error", latency_seconds=perf_counter() - started)
            return record

        async def bounded_review() -> ReviewDecision:
            return await asyncio.wait_for(reviewer.review(request), timeout=timeout)

        try:
            record["invoked"] = True
            raw = asyncio.run(bounded_review())
            decision = ReviewDecision.model_validate(
                raw.model_dump(warnings="error") if isinstance(raw, ReviewDecision) else raw,
                strict=True,
            )
            if perf_counter() - started > timeout:
                record["reason"] = "reviewer_timeout"
            else:
                record.update(
                    allowed=decision.allowed, reason=decision.reason, decision=decision.model_dump()
                )
        except TimeoutError:
            record["reason"] = "reviewer_timeout"
        except asyncio.CancelledError:
            record["reason"] = "reviewer_cancelled"
        except Exception as exc:
            # Never log exception text: a reviewer may include private context in it.
            record["reason"] = "reviewer_error"
            record["error_type"] = type(exc).__name__
    record["latency_seconds"] = perf_counter() - started
    return record
