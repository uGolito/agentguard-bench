"""Mocked SDK errors only: no authentication probes or benchmark executions."""

import json
import logging

import anthropic
import httpx2
import pytest

from agentguard.config import RunConfig
from agentguard.guards.oversight import ReviewRequest, review_action
from agentguard.providers import ProviderError
from agentguard.providers.anthropic import AnthropicProvider
from agentguard.providers.budget import MODEL, Budget
from agentguard.providers.reviewer import AnthropicReviewer

DUMMY = "unit-test-opaque-placeholder"
PRIVATE = "UNIT-TEST-PRIVATE-ERROR-CONTENT"
REQUEST_ID = "req_0123456789AbCdEfabcdef"
MESSAGES = [
    {"role": "system", "content": "Synthetic probe", "tools": []},
    {"role": "user", "content": "Return the requested JSON."},
]


def config(**changes):
    return RunConfig(
        **{
            "provider": "anthropic",
            "model": MODEL,
            "allow_live": True,
            "max_cost": 5,
            "max_requests": 5,
            "max_retries": 3,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "body,content_type,category,shape",
    [
        (
            {"type": "error", "error": {"type": "invalid_request_error", "message": PRIVATE}},
            "application/json",
            "invalid_request_error",
            "anthropic_error_envelope",
        ),
        (
            {"error": {"type": "proxy_error", "message": PRIVATE}},
            "application/json",
            "unknown",
            "other_json",
        ),
        (f"<html>Proxy rejection {PRIVATE} {DUMMY}</html>", "text/html", "unknown", "unstructured"),
        (
            {"type": "error", "error": {"type": PRIVATE, "message": PRIVATE}},
            "application/json",
            "unknown",
            "other_json",
        ),
        (
            {"type": "error", "error": {"type": [PRIVATE], "message": PRIVATE}},
            "application/json",
            "unknown",
            "other_json",
        ),
    ],
)
def test_http_400_safe_diagnostics_no_retry_or_sensitive_logs(
    body, content_type, category, shape, caplog, capsys
):
    sent = []

    def handler(request):
        sent.append(request)
        headers = {
            "request-id": REQUEST_ID,
            "content-type": content_type + "; private=" + PRIVATE,
            "x-proxy-debug": PRIVATE,
            "anthropic-workspace-id": PRIVATE,
        }
        return httpx2.Response(
            400, headers=headers, content=json.dumps(body) if isinstance(body, dict) else body
        )

    caplog.set_level(logging.DEBUG)
    client = anthropic.Anthropic(
        api_key=DUMMY,
        max_retries=3,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler), trust_env=False),
    )
    cfg = config()
    ledger = Budget(cfg)
    provider = AnthropicProvider(cfg, ledger, client)
    try:
        with pytest.raises(ProviderError, match="provider_error"):
            provider.next_turn(MESSAGES)
    finally:
        client.close()
    assert len(sent) == 1 and provider.requests == 1 and ledger.requests == 1
    assert ledger.unknown_attempts == 1 and ledger.charged == ledger.reservation
    assert ledger.reported_cost == 0 and not provider.usage_complete
    event = next(e for e in provider.events if e["event"] == "api_error")
    assert event["data"]["diagnostics"] == {
        "http_status": 400,
        "error_category": category,
        "request_id": REQUEST_ID,
        "response_content_type": content_type,
        "response_shape": shape,
        "origin": "unknown",
    }
    exported = json.dumps(provider.events) + caplog.text + capsys.readouterr().out
    assert PRIVATE not in exported and DUMMY not in exported
    assert not any(e["event"] == "api_response" for e in provider.events)


@pytest.mark.parametrize("html", [False, True])
def test_async_reviewer_http_400_has_same_safe_policy_and_retains_charge(html, caplog):
    seen = []

    async def handler(request):
        seen.append(request)
        headers = {"request-id": REQUEST_ID, "x-private-header": PRIVATE}
        if html:
            return httpx2.Response(
                400, text=PRIVATE, headers={**headers, "content-type": "text/html"}
            )
        return httpx2.Response(
            400,
            json={
                "type": "error",
                "request_id": REQUEST_ID,
                "error": {"type": "invalid_request_error", "message": PRIVATE},
            },
            headers=headers,
        )

    def factory():
        return anthropic.AsyncAnthropic(
            api_key=DUMMY,
            max_retries=3,
            http_client=httpx2.AsyncClient(
                transport=httpx2.MockTransport(handler), trust_env=False
            ),
        )

    caplog.set_level(logging.DEBUG)
    cfg = config(mode="guarded_oversight", reviewer_provider="anthropic")
    ledger = Budget(cfg)
    reviewer = AnthropicReviewer(cfg, ledger, factory)
    record = review_action(
        reviewer,
        ReviewRequest(
            scenario_id="pi-010",
            objective="Synthetic review",
            action_json='{"tool":"send_email","arguments":{"body":"Synthetic"}}',
            grant_id="unit",
        ),
        2,
    )
    assert not record["allowed"] and record["decision"] is None
    assert len(seen) == 1 and ledger.unknown_attempts == 1
    assert ledger.snapshot()["pending_attempts"] == 0
    assert record["accounting"]["conservative_charge_usd"] == pytest.approx(0.5016)
    diagnostic = next(
        e["data"]["diagnostics"] for e in record["trace"] if e["event"] == "reviewer_api_error"
    )
    assert diagnostic["http_status"] == 400 and diagnostic["origin"] == "unknown"
    assert diagnostic["error_category"] == ("unknown" if html else "invalid_request_error")
    assert PRIVATE not in json.dumps(record) + caplog.text
    assert DUMMY not in json.dumps(record) + caplog.text


def test_non_model_http_200_error_body_is_not_a_raw_model_trace():
    def handler(request):
        return httpx2.Response(
            200,
            json={"type": "error", "error": {"type": "authentication_error", "message": PRIVATE}},
        )

    client = anthropic.Anthropic(
        api_key=DUMMY,
        _strict_response_validation=True,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler), trust_env=False),
    )
    cfg = config()
    ledger = Budget(cfg)
    provider = AnthropicProvider(cfg, ledger, client)
    try:
        with pytest.raises(ProviderError, match="invalid_response"):
            provider.next_turn(MESSAGES)
    finally:
        client.close()
    assert PRIVATE not in json.dumps(provider.events)
    assert not any(e["event"] == "api_response" for e in provider.events)
    assert ledger.halted and ledger.unknown_attempts == 1
