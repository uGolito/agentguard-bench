"""Sequential run-wide accounting; reserve before every attempt, including retries."""

from decimal import Decimal
from typing import Any

from agentguard.config import RunConfig
from agentguard.providers import ProviderError

MODEL = "claude-haiku-4-5-20251001"
PRICING = {
    "model": MODEL,
    "input_usd_per_million": "1",
    "output_usd_per_million": "5",
    "cache_write_usd_per_million": "2",  # Conservative 1-hour write rate.
    "cache_read_usd_per_million": "0.10",
    "context_tokens": 200_000,
    "safety_multiplier": "1.25",
    "checked_on": "2026-11-03",
    "source": "https://platform.claude.com/docs/en/models/haiku-4-5/overview",
}
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def usage_cost(usage: dict[str, Any]) -> Decimal:
    """Validate billing counts; missing/non-integer usage must never become a zero bill."""
    known_fields = set(TOKEN_FIELDS) | {
        "cache_creation",
        "inference_geo",
        "output_tokens_details",
        "server_tool_use",
        "service_tier",
        "speed",
    }
    if any(name not in known_fields and value is not None for name, value in usage.items()):
        raise ProviderError("unsupported_billing")
    if (
        usage.get("service_tier") not in (None, "standard")
        or usage.get("speed") not in (None, "standard")
        or usage.get("inference_geo") not in (None, "global", "not_available")
    ):
        raise ProviderError("unsupported_billing")
    server_tools = usage.get("server_tool_use")
    if server_tools is not None and (
        not isinstance(server_tools, dict) or any(server_tools.values())
    ):
        raise ProviderError("unsupported_billing")
    for name in TOKEN_FIELDS:
        value = usage.get(name, 0 if name.startswith("cache_") else None)
        if type(value) is not int or value < 0:
            raise ProviderError("invalid_usage")
    return sum(
        (
            Decimal(usage.get(name, 0)) * Decimal(rate)
            for name, rate in zip(
                TOKEN_FIELDS,
                (
                    PRICING["input_usd_per_million"],
                    PRICING["output_usd_per_million"],
                    PRICING["cache_write_usd_per_million"],
                    PRICING["cache_read_usd_per_million"],
                ),
                strict=True,
            )
        ),
        Decimal(0),
    ) / Decimal(1_000_000)


class Budget:
    """Estimates, not a provider billing guarantee. Unknown attempts retain full reservation."""

    def __init__(self, config: RunConfig) -> None:
        self.max_requests = config.max_requests
        self.max_cost = Decimal(str(config.max_cost))
        self.requests = 0
        self.charged = Decimal(0)
        self.reported_cost = Decimal(0)
        self.unknown_attempts = 0
        self.halted = False
        # Reserve a full context, maximum output, worst cache-write rate, plus 25%.
        # No token-counting endpoint or byte/token heuristic is needed.
        self.reservation = (
            (
                Decimal(PRICING["context_tokens"]) * Decimal(PRICING["cache_write_usd_per_million"])
                + Decimal(config.max_tokens) * Decimal(PRICING["output_usd_per_million"])
            )
            / Decimal(1_000_000)
            * Decimal(PRICING["safety_multiplier"])
        )

    def reserve(self) -> Decimal:
        if self.halted:
            raise ProviderError("accounting_halted")
        if self.requests >= self.max_requests:
            raise ProviderError("request_limit")
        if self.charged + self.reservation > self.max_cost:
            raise ProviderError("cost_limit")
        self.requests += 1
        self.charged += self.reservation
        self.unknown_attempts += 1
        return self.reservation

    def settle(self, reservation: Decimal, usage: dict[str, Any]) -> Decimal:
        try:
            cost = usage_cost(usage)
        except ProviderError:
            self.halted = True
            raise
        self.reported_cost += cost
        self.charged += cost - reservation
        self.unknown_attempts -= 1
        if cost > reservation:
            self.halted = True
            raise ProviderError("reservation_exceeded")
        return cost

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "estimated_cost_usd": float(self.reported_cost),
            "conservative_charge_usd": float(self.charged),
            "unknown_billing_attempts": self.unknown_attempts,
            "next_attempt_reservation_usd": float(self.reservation),
            "halted": self.halted,
        }
