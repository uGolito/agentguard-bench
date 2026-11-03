"""Official SDK adapter. No SDK tool runner, hidden retries, or external tool effects."""

import json
import os
from time import perf_counter, sleep
from typing import Any

import anthropic
import httpx2
from pydantic import ValidationError

from agentguard.config import RunConfig
from agentguard.providers import ProviderError, ProviderState
from agentguard.providers.budget import TOKEN_FIELDS, Budget
from agentguard.schemas import Answer, ToolCall, Turn


def create_client(config: RunConfig) -> anthropic.Anthropic:
    """Only called after live opt-in; never load keys from files or alternate endpoints."""
    if not config.allow_live or config.provider != "anthropic":
        raise ValueError("Live provider requires explicit opt-in")
    if os.environ.get("CI"):
        raise ValueError("Live evaluations are disabled in CI")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is not set; no request was sent")
    return anthropic.Anthropic(
        api_key=key,
        base_url="https://api.anthropic.com",
        max_retries=0,
        timeout=config.timeout_seconds,
        _strict_response_validation=True,
        http_client=httpx2.Client(
            timeout=config.timeout_seconds, follow_redirects=False, trust_env=False
        ),
    )


def translate_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group parallel tool results into one user message and preserve tool-use IDs."""
    translated: list[dict[str, Any]] = []
    for message in messages[1:]:
        if message["role"] == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message["tool_use_id"],
                "content": json.dumps(message["content"], ensure_ascii=False),
                "is_error": message.get("is_error", False),
            }
            if (
                translated
                and translated[-1]["role"] == "user"
                and isinstance(translated[-1]["content"], list)
            ):
                translated[-1]["content"].append(block)
            else:
                translated.append({"role": "user", "content": [block]})
        else:
            translated.append({"role": message["role"], "content": message["content"]})
    return translated


class AnthropicProvider(ProviderState):
    def __init__(self, config: RunConfig, budget: Budget, client: anthropic.Anthropic) -> None:
        super().__init__()
        # Revalidate to prevent a mutated or unchecked config from bypassing opt-in.
        self.config = RunConfig.model_validate(config.model_dump())
        if config.provider != "anthropic":
            raise ValueError("AnthropicProvider requires provider=anthropic")
        self.budget = budget
        # SDK 2.4 copy() does not inherit its strict-validation flag.
        # Reapply it explicitly; the wire tests cover this pinned SDK behavior.
        self.client = client.with_options(
            max_retries=0,
            timeout=config.timeout_seconds,
            _extra_kwargs={"_strict_response_validation": True},
        )
        self.tokens = dict.fromkeys(TOKEN_FIELDS, 0)
        self.usage_complete = True

    def next_turn(self, messages: list[dict[str, Any]]) -> Turn:
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "service_tier": "standard_only",
            "system": messages[0]["content"],
            "tools": messages[0]["tools"],
            "messages": translate_messages(messages),
        }
        for attempt in range(self.config.max_retries + 1):
            reserved = self.budget.reserve()
            self.requests += 1
            self.budget_charge_usd += float(reserved)
            self.events.append(
                {
                    "event": "api_request",
                    "data": {
                        "attempt": attempt + 1,
                        "request": payload,
                        "reservation_usd": float(reserved),
                    },
                }
            )
            started = perf_counter()
            try:
                # SDK 2 removed the typed temperature argument; the supported
                # legacy snapshot still accepts it through official extra_body.
                parameters = {key: value for key, value in payload.items() if key != "temperature"}
                response = self.client.messages.create(
                    **parameters, extra_body={"temperature": self.config.temperature}
                )
            except anthropic.APIError as exc:
                self.usage_complete = False
                status_code = getattr(exc, "status_code", None)
                self.events.append(
                    {
                        "event": "api_error",
                        "data": {
                            "type": type(exc).__name__,
                            "status_code": status_code,
                            "latency_seconds": perf_counter() - started,
                            "billing": "unknown; full reservation retained",
                        },
                    }
                )
                if isinstance(exc, anthropic.APIResponseValidationError):
                    # Preserve malformed HTTP-200 model output, but never an auth/error body.
                    if isinstance(exc.body, dict):
                        if isinstance(exc.body.get("usage"), dict):
                            self._observe_usage(exc.body["usage"])
                        self.events.append(
                            {
                                "event": "api_response",
                                "data": {
                                    "response": exc.body,
                                    "sdk_validation_failed": True,
                                },
                            }
                        )
                    self.budget.halted = True
                    raise ProviderError("invalid_response") from None
                retryable = isinstance(exc, anthropic.APIConnectionError) or (
                    status_code in (408, 409, 429)
                    or (isinstance(status_code, int) and status_code >= 500)
                )
                if retryable and attempt < self.config.max_retries:
                    delay = min(self.config.retry_delay_seconds * (2**attempt), 10)
                    header = getattr(exc, "response", None)
                    retry_after = header.headers.get("retry-after") if header else None
                    if retry_after is not None:
                        try:
                            advised = float(retry_after)
                        except ValueError:
                            advised = float("inf")
                        if not 0 <= advised <= 10:
                            raise ProviderError("retry_after_limit") from None
                        delay = max(delay, advised)
                    self.events.append({"event": "retry_wait", "data": {"seconds": delay}})
                    sleep(delay)
                    continue
                code = "timeout" if isinstance(exc, anthropic.APITimeoutError) else "provider_error"
                raise ProviderError(code) from None
            raw = response.model_dump(mode="json")
            self.events.append(
                {
                    "event": "api_response",
                    "data": {
                        "response": raw,
                        "request_id": response._request_id,
                        "latency_seconds": perf_counter() - started,
                    },
                }
            )
            usage = self._observe_usage(raw.get("usage") or {})
            charge_before = self.budget.charged
            reported_before = self.budget.reported_cost
            try:
                self.budget.settle(reserved, usage)
            except ProviderError:
                self.usage_complete = False
                raise
            finally:
                self.budget_charge_usd += float(self.budget.charged - charge_before)
                self.estimated_cost_usd += float(self.budget.reported_cost - reported_before)
            if response.model != self.config.model:
                self.budget.halted = True
                raise ProviderError("model_mismatch")
            try:
                return self._parse(raw)
            except (ValidationError, ValueError, KeyError, TypeError):
                raise ProviderError("invalid_response") from None
        raise AssertionError("Unreachable retry loop")

    def _observe_usage(self, raw_usage: dict[str, Any]) -> dict[str, Any]:
        usage = dict(raw_usage)
        for name in TOKEN_FIELDS[2:]:
            if usage.get(name) is None:
                usage[name] = 0
        assert self.tokens is not None
        for name in TOKEN_FIELDS:
            value = usage.get(name)
            if type(value) is int and value >= 0:
                self.tokens[name] += value
        return usage

    @staticmethod
    def _parse(raw: dict[str, Any]) -> Turn:
        content = raw["content"]
        stop = raw["stop_reason"]
        if stop == "max_tokens":
            raise ProviderError("output_limit")
        if stop == "refusal":
            return Turn(answer=Answer(claims=[], refused=True), assistant_content=content)
        tool_blocks = [block for block in content if block["type"] == "tool_use"]
        if stop == "tool_use" and tool_blocks:
            calls = [
                ToolCall(name=block["name"], arguments=block["input"], call_id=block["id"])
                for block in tool_blocks
            ]
            ids = [call.call_id for call in calls]
            if any(not identity for identity in ids) or len(set(ids)) != len(ids):
                raise ValueError("Invalid tool-use IDs")
            return Turn(calls=calls, assistant_content=content)
        if stop != "end_turn" or tool_blocks:
            raise ProviderError("unsupported_stop_reason")
        if any(block["type"] != "text" for block in content):
            raise ValueError("Unsupported content block")
        text = "".join(block["text"] for block in content)
        return Turn(answer=Answer.model_validate_json(text), assistant_content=content)
