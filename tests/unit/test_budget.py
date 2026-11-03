from decimal import Decimal

import pytest

from agentguard.config import RunConfig
from agentguard.providers import ProviderError
from agentguard.providers.budget import MODEL, Budget, usage_cost


def config(**changes):
    return RunConfig(provider="anthropic", model=MODEL, allow_live=True, max_cost=1.0, **changes)


def test_decimal_cost_and_cache_accounting():
    assert usage_cost(
        {
            "input_tokens": 100,
            "output_tokens": 20,
            "cache_creation_input_tokens": 100,
            "cache_read_input_tokens": 100,
        }
    ) == (Decimal("0.00041"))


@pytest.mark.parametrize(
    "usage",
    [
        {},
        {"input_tokens": 1},
        {"input_tokens": -1, "output_tokens": 0},
        {"input_tokens": True, "output_tokens": 0},
        {"input_tokens": 1, "output_tokens": "1"},
    ],
)
def test_unknown_usage_halts_and_retains_reservation(usage):
    budget = Budget(config())
    reserved = budget.reserve()
    with pytest.raises(ProviderError, match="invalid_usage"):
        budget.settle(reserved, usage)
    assert budget.charged == reserved
    assert budget.unknown_attempts == 1
    with pytest.raises(ProviderError, match="accounting_halted"):
        budget.reserve()


def test_unexpected_bill_exceeding_reservation_halts():
    budget = Budget(config())
    reserved = budget.reserve()
    with pytest.raises(ProviderError, match="reservation_exceeded"):
        budget.settle(reserved, {"input_tokens": 1_000_000, "output_tokens": 0})
    assert budget.halted
    assert budget.reported_cost == Decimal(1)


def test_request_limit_before_reserving():
    budget = Budget(config(max_requests=1))
    budget.reserve()
    with pytest.raises(ProviderError, match="request_limit"):
        budget.reserve()
    assert budget.requests == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"server_tool_use": {"web_search_requests": 1}},
        {"service_tier": "priority"},
        {"speed": "fast"},
        {"future_paid_feature": 12},
        {"inference_geo": "us"},
    ],
)
def test_unsupported_billing_is_not_silently_ignored(extra):
    with pytest.raises(ProviderError, match="unsupported_billing"):
        usage_cost({"input_tokens": 100, "output_tokens": 20, **extra})


@pytest.mark.parametrize(
    "changes",
    [
        {"allow_live": False},
        {"max_cost": 0.0},
        {"model": "claude-haiku-4-5"},
        {"max_cost": float("nan")},
        {"timeout_seconds": 0.0},
        {"max_retries": 4},
        {"max_tokens": 100000},
    ],
)
def test_invalid_live_config(changes):
    settings = {"provider": "anthropic", "model": MODEL, "allow_live": True, "max_cost": 1.0}
    settings.update(changes)
    with pytest.raises(ValueError):
        RunConfig(**settings)
