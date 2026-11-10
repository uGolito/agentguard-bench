"""Regression contract from Anthropic's API-version migration guide; no network."""

import json

import anthropic
import httpx2
import pytest

from agentguard.config import RunConfig
from agentguard.guards.oversight import ReviewRequest, review_action
from agentguard.providers.anthropic import CLAUDE_API_VERSION, AnthropicProvider, create_client
from agentguard.providers.budget import MODEL, Budget
from agentguard.providers.reviewer import AnthropicReviewer, create_review_client
from agentguard.tools import TOOL_DEFINITIONS


def config(**changes):
    return RunConfig(
        **{
            "provider": "anthropic",
            "model": MODEL,
            "allow_live": True,
            "max_cost": 1,
            "max_requests": 1,
            "max_retries": 0,
            **changes,
        }
    )


def reject_removed_sampling(request):
    body = json.loads(request.content)
    if request.headers["anthropic-version"] == "2026-10-21" and "temperature" in body:
        return httpx2.Response(
            400,
            json={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "temperature: Extra inputs are not permitted",
                },
            },
        )
    return None


def response(text):
    return {
        "id": "msg_offline",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


def test_primary_pins_legacy_api_and_preserves_zero_temperature_and_budget():
    cfg = config()
    seen = []

    def handler(request):
        seen.append(request)
        rejected = reject_removed_sampling(request)
        return (
            rejected
            if rejected is not None
            else httpx2.Response(
                200, json=response('{"claims":[],"uncertainty":true,"refused":false}')
            )
        )

    # The old contract is guaranteed invalid by the documented version rule.
    old = httpx2.Request(
        "POST",
        "https://api.anthropic.com/v1/messages",
        headers={"anthropic-version": "2026-10-21"},
        json={"temperature": 0},
    )
    assert reject_removed_sampling(old).status_code == 400
    client = anthropic.Anthropic(
        api_key="offline-test",
        max_retries=3,
        default_headers={"anthropic-version": "2026-10-21"},
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler), trust_env=False),
    )
    budget = Budget(cfg)
    provider = AnthropicProvider(cfg, budget, client)
    try:
        turn = provider.next_turn(
            [
                {"role": "system", "content": "Synthetic", "tools": TOOL_DEFINITIONS},
                {"role": "user", "content": "Synthetic"},
            ]
        )
    finally:
        client.close()
    assert turn.answer is not None and len(seen) == 1
    assert seen[0].headers["anthropic-version"] == CLAUDE_API_VERSION == "2023-06-01"
    payload = json.loads(seen[0].content)
    assert payload["temperature"] == 0 and payload["service_tier"] == "standard_only"
    assert payload["tools"] == TOOL_DEFINITIONS and payload["model"] == MODEL
    assert budget.requests == 1 and budget.unknown_attempts == 0
    assert budget.snapshot()["estimated_cost_usd"] == pytest.approx(0.0002)
    assert provider.client.max_retries == 0


def test_reviewer_clone_also_pins_legacy_api_without_changing_review_role():
    seen = []

    async def handler(request):
        seen.append(request)
        rejected = reject_removed_sampling(request)
        return (
            rejected
            if rejected is not None
            else httpx2.Response(
                200, json=response('{"allowed":true,"reason":"Synthetic approved action"}')
            )
        )

    def factory():
        return anthropic.AsyncAnthropic(
            api_key="offline-test",
            max_retries=3,
            default_headers={"anthropic-version": "2026-10-21"},
            http_client=httpx2.AsyncClient(
                transport=httpx2.MockTransport(handler), trust_env=False
            ),
        )

    cfg = config(mode="guarded_oversight", reviewer_provider="anthropic")
    budget = Budget(cfg)
    reviewer = AnthropicReviewer(cfg, budget, factory)
    record = review_action(
        reviewer,
        ReviewRequest(
            scenario_id="pi-010",
            objective="Synthetic",
            action_json='{"tool":"send_email","arguments":{}}',
            grant_id="unit",
        ),
        2,
    )
    assert record["allowed"] and len(seen) == 1
    assert seen[0].headers["anthropic-version"] == "2023-06-01"
    payload = json.loads(seen[0].content)
    assert payload["temperature"] == 0 and "tools" not in payload
    assert "independent safety reviewer" in payload["system"]
    assert reviewer.metadata["api_version"] == "2023-06-01"
    assert budget.requests == 1 and budget.snapshot()["estimated_cost_usd"] == pytest.approx(0.0002)


def test_default_factories_pin_header_without_sending_requests(monkeypatch):
    import asyncio

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test")
    monkeypatch.setenv("AGENTGUARD_HTTP_MODE", "direct")
    primary = create_client(config())
    review = create_review_client(config(mode="guarded_oversight", reviewer_provider="anthropic"))
    try:
        for client in (primary, review):
            assert client.default_headers["anthropic-version"] == "2023-06-01"
            assert client.auth_headers == {"Authorization": "Bearer offline-test"}
    finally:
        primary.close()
        asyncio.run(review.close())
