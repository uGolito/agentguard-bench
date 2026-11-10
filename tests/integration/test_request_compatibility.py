"""Pinned SDK/schema/wire facts; these assertions cannot prove remote acceptance."""

import json
import typing

import anthropic
import httpx2
import pytest
from anthropic._constants import ANTHROPIC_API_VERSION
from anthropic.types.message_create_params import MessageCreateParamsBase
from anthropic.types.model import Model
from anthropic.types.tool_param import ToolParam

from agentguard.config import RunConfig
from agentguard.providers import ProviderError
from agentguard.providers.anthropic import CLAUDE_API_VERSION, AnthropicProvider
from agentguard.providers.budget import MODEL, Budget
from agentguard.tools import TOOL_DEFINITIONS


def test_pinned_sdk_declares_version_model_tier_and_required_tool_fields():
    assert anthropic.__version__ == "2.4.0"
    assert ANTHROPIC_API_VERSION == "2026-10-21"
    assert MODEL in typing.get_args(typing.get_args(Model)[0])
    hints = typing.get_type_hints(MessageCreateParamsBase)
    assert "standard_only" in typing.get_args(hints["service_tier"])
    assert "temperature" not in hints  # Untyped extra_body is not proof of server support.
    tool_hints = typing.get_type_hints(ToolParam, include_extras=True)
    assert all(
        typing.get_origin(tool_hints[key]) is typing.Required for key in ("name", "input_schema")
    )


def test_actual_wire_request_preserves_parameters_and_single_authentication_header():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(
            400,
            json={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "Synthetic rejection, not a live finding",
                },
            },
        )

    cfg = RunConfig(provider="anthropic", model=MODEL, allow_live=True, max_cost=1, max_requests=1)
    client = anthropic.Anthropic(
        api_key="offline-test",
        max_retries=3,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler), trust_env=False),
    )
    provider = AnthropicProvider(cfg, Budget(cfg), client)
    try:
        with pytest.raises(ProviderError):
            provider.next_turn(
                [
                    {
                        "role": "system",
                        "content": "Synthetic system instruction",
                        "tools": TOOL_DEFINITIONS,
                    },
                    {"role": "user", "content": "Synthetic user request"},
                ]
            )
    finally:
        client.close()
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.method == "POST"
    assert request.headers["anthropic-version"] == CLAUDE_API_VERSION == "2023-06-01"
    assert request.headers["Authorization"] == "Bearer offline-test"
    assert len([k for k, _ in request.headers.multi_items() if k.lower() == "authorization"]) == 1
    assert "x-api-key" not in request.headers and "proxy-authorization" not in request.headers
    payload = json.loads(request.content)
    assert payload["temperature"] == 0
    assert payload["service_tier"] == "standard_only" and payload["model"] == MODEL
    assert payload["max_tokens"] == 512 and "extra_body" not in payload
    assert payload["system"] == "Synthetic system instruction"
    assert payload["messages"] == [{"role": "user", "content": "Synthetic user request"}]
    assert len(payload["tools"]) == 6
    assert len({t["name"] for t in payload["tools"]}) == 6
    for tool in payload["tools"]:
        assert set(tool) == {"name", "input_schema"}
        assert tool["input_schema"]["type"] == "object"
        assert tool["input_schema"]["additionalProperties"] is False
