"""Scenario discovery and reproducible run manifests."""

import hashlib
import importlib.metadata
import platform
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
from agentguard.providers.anthropic import AnthropicProvider, create_client
from agentguard.providers.budget import PRICING, Budget
from agentguard.schemas import Scenario


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
) -> dict[str, Any]:
    config = RunConfig.model_validate(config.model_dump())
    policy = Policy.model_validate_json((policy or Policy()).model_dump_json())
    results = []
    remaining = config.max_requests
    budget = Budget(config) if config.provider == "anthropic" else None
    owns_client = config.provider == "anthropic" and client is None
    if owns_client:
        client = create_client(config)
    try:
        for trial in range(config.trials):
            for scenario in scenarios:
                provider = (
                    AnthropicProvider(config, budget, client)
                    if budget is not None
                    else FakeProvider(scenario)
                )
                execution = execute(
                    scenario, provider, config, remaining, policy=policy, reviewer=reviewer
                )
                remaining -= execution["requests"]
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
        "schema_version": "1.2.0",
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
        },
        "budget": budget.snapshot() if budget else None,
        "pricing": PRICING if budget else None,
        "config": config.model_dump(),
        "policy": policy.model_dump(),
        "policy_sha256": hashlib.sha256(policy.model_dump_json().encode()).hexdigest(),
        "reviewer": reviewer.metadata if reviewer else None,
        "scenario_snapshots": [s.model_dump() for s in scenarios],
        "results": results,
    }
