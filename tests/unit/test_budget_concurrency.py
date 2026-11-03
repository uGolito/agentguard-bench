from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from agentguard.config import RunConfig
from agentguard.providers import ProviderError
from agentguard.providers.budget import MODEL, Budget


def budget(max_cost=0.6, max_requests=100):
    return Budget(
        RunConfig(
            provider="anthropic",
            model=MODEL,
            allow_live=True,
            max_cost=max_cost,
            max_requests=max_requests,
        )
    )


def test_concurrent_reservations_cannot_overspend():
    ledger = budget()
    barrier = Barrier(16)

    def attempt(_):
        barrier.wait()
        try:
            return ledger.reserve()
        except ProviderError as exc:
            assert exc.code == "cost_limit"
            return None

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(attempt, range(16)))
    assert sum(item is not None for item in results) == 1
    assert ledger.charged <= ledger.max_cost
    assert ledger.snapshot()["pending_attempts"] == 1


def test_concurrent_request_cap_is_atomic():
    ledger = budget(max_cost=100.0, max_requests=3)

    def attempt(_):
        try:
            return ledger.reserve()
        except ProviderError as exc:
            assert exc.code == "request_limit"
            return None

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(attempt, range(100)))
    assert sum(item is not None for item in results) == 3
    assert ledger.requests == 3


def test_duplicate_concurrent_settlement_refunds_once():
    ledger = budget()
    token = ledger.reserve()

    def settle(_):
        try:
            return ledger.settle(token, {"input_tokens": 100, "output_tokens": 20})
        except ProviderError as exc:
            assert exc.code == "invalid_reservation"
            return None

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(settle, range(32)))
    assert sum(item is not None for item in results) == 1
    assert ledger.charged == Decimal("0.0002")
    assert ledger.reported_cost == ledger.charged
    assert ledger.unknown_attempts == 0


def test_foreign_and_forged_reservations_cannot_refund():
    a, b = budget(), budget()
    token_a, token_b = a.reserve(), b.reserve()
    for invalid in [token_b, Decimal(token_a), Decimal(1000000)]:
        with pytest.raises(ProviderError, match="invalid_reservation"):
            a.settle(invalid, {"input_tokens": 0, "output_tokens": 0})
    assert a.charged == token_a
    assert b.charged == token_b


def test_unknown_finalization_forbids_late_refunds():
    ledger = budget()
    token = ledger.reserve()
    ledger.retain(token)
    assert ledger.snapshot()["pending_attempts"] == 0
    assert ledger.unknown_attempts == 1
    with pytest.raises(ProviderError, match="invalid_reservation"):
        ledger.settle(token, {"input_tokens": 0, "output_tokens": 0})
    assert ledger.charged == token
    with pytest.raises(ProviderError, match="invalid_reservation"):
        budget().attempt_cost(token)
