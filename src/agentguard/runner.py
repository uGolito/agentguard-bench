"""Scenario discovery and reproducible run manifests."""

import hashlib
import importlib.metadata
import platform
import random
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentguard.agents import execute
from agentguard.config import RunConfig
from agentguard.evaluators import evaluate
from agentguard.guards.oversight import Reviewer
from agentguard.guards.policy import Policy
from agentguard.providers import FakeProvider
from agentguard.providers.anthropic import CLAUDE_API_VERSION, AnthropicProvider, create_client
from agentguard.providers.budget import PRICING, Budget
from agentguard.providers.http import http_mode
from agentguard.providers.reviewer import AnthropicReviewer
from agentguard.schemas import Scenario
from agentguard.tracing import EventLog, Sink


def load_scenarios(root: Path, category: str | None = None) -> list[Scenario]:
    scenarios = [
        Scenario.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(root.glob("*/*.json"))
    ]
    if not scenarios:
        raise ValueError(f"No scenarios found in {root}; pass --scenarios PATH")
    if len({s.id for s in scenarios}) != len(scenarios):
        raise ValueError("Duplicate scenario IDs")
    selected = [s for s in scenarios if category is None or s.category == category]
    if not selected:
        raise ValueError(f"No scenarios for category: {category}")
    return selected


def run(
    scenarios: list[Scenario],
    config: RunConfig,
    *,
    client: Any = None,
    policy: Policy | None = None,
    reviewer: Reviewer | None = None,
    reviewer_client_factory: Any = None,
    budget: Budget | None = None,
    trace_sink: Sink | None = None,
    request_offset: int = 0,
) -> dict[str, Any]:
    config = RunConfig.model_validate(config.model_dump())
    policy = Policy.model_validate_json((policy or Policy()).model_dump_json())
    results = []
    remaining = max(0, config.max_requests - request_offset - (budget.requests if budget else 0))
    budget = (budget or Budget(config)) if config.provider == "anthropic" else None
    if budget and not budget.matches(config):
        raise ValueError("Shared budget does not match the recorded configuration")
    if config.reviewer_provider == "anthropic":
        if reviewer is not None:
            raise ValueError("Choose an injected reviewer or Anthropic review, not both")
        assert budget is not None
        reviewer = AnthropicReviewer(config, budget, reviewer_client_factory)
    owns_client = config.provider == "anthropic" and client is None
    if owns_client:
        client = create_client(config)
    try:
        for trial in range(config.trials):
            ordered = list(scenarios)
            if config.order_seed is not None:
                # Reproducible scheduling/resampling; no secrets or cryptographic use.
                random.Random(config.order_seed + trial).shuffle(ordered)  # nosec B311
            for source in ordered:
                scenario = Scenario.model_validate_json(source.model_dump_json())
                before_requests = budget.requests if budget else 0
                provider = (
                    AnthropicProvider(config, budget, client)
                    if budget is not None
                    else FakeProvider(scenario)
                )

                def episode_sink(event: dict[str, Any], sid=scenario.id, t=trial) -> None:
                    if trace_sink:
                        trace_sink({"scenario_id": sid, "trial": t, "mode": config.mode, **event})

                provider.events = EventLog(episode_sink if trace_sink else None)
                if reviewer is not None and hasattr(reviewer, "events"):
                    reviewer.events = EventLog(episode_sink if trace_sink else None)
                execution = execute(
                    scenario,
                    provider,
                    config,
                    remaining,
                    policy=policy,
                    reviewer=reviewer,
                    trace_sink=episode_sink if trace_sink else None,
                )
                remaining -= execution["requests"]
                if budget:
                    remaining = max(0, config.max_requests - budget.requests)
                    execution["total_requests"] = budget.requests - before_requests
                results.append(
                    {
                        "scenario_id": scenario.id,
                        "version": scenario.version,
                        "category": scenario.category,
                        "trial": trial,
                        "scenario_sha256": hashlib.sha256(
                            scenario.model_dump_json().encode()
                        ).hexdigest(),
                        "execution": execution,
                        "evaluation": evaluate(scenario, execution),
                    }
                )
    finally:
        if owns_client:
            client.close()
    return {
        "schema_version": "1.3.0",
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "package_version": importlib.metadata.version("agentguard-bench"),
        "provider_metadata": {
            "name": config.provider,
            "live": config.provider != "fake",
            "sdk_version": importlib.metadata.version("anthropic") if budget else None,
            "model": config.model,
            "sdk_retries": 0 if budget else None,
            "client_injected": client is not None and not owns_client,
            **({"http_mode": http_mode() if owns_client else "injected"} if budget else {}),
            **({"api_version": CLAUDE_API_VERSION} if budget else {}),
        },
        "budget": budget.snapshot() if budget else None,
        "pricing": PRICING if budget else None,
        "config": config.model_dump(),
        "policy": policy.model_dump(),
        "policy_sha256": hashlib.sha256(policy.model_dump_json().encode()).hexdigest(),
        "reviewer": reviewer.metadata if reviewer else None,
        "execution_order": [[r["scenario_id"], r["trial"]] for r in results],
        "seed_semantics": (
            "order_seed shuffles fixture order only; Anthropic model seeds unsupported"
        ),
        "scenario_snapshots": [s.model_dump() for s in scenarios],
        "results": results,
    }
