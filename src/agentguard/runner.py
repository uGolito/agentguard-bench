"""Scenario discovery and reproducible run manifests."""

import hashlib
import platform
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentguard.agents import execute
from agentguard.config import RunConfig
from agentguard.evaluators import evaluate
from agentguard.providers import FakeProvider
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


def run(scenarios: list[Scenario], config: RunConfig) -> dict[str, Any]:
    results = []
    remaining = config.max_requests
    for trial in range(config.trials):
        for scenario in scenarios:
            execution = execute(scenario, FakeProvider(scenario), config, remaining)
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
    return {
        "schema_version": "1.0.0",
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "provider_metadata": {"name": "fake", "live": False, "version": "1"},
        "config": config.model_dump(),
        "scenario_snapshots": [s.model_dump() for s in scenarios],
        "results": results,
    }
