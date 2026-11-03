"""Counterbalanced paired episodes with per-mode budgets and a declared total ceiling."""

import math
import random
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agentguard.config import RunConfig
from agentguard.guards.oversight import FakeReviewer
from agentguard.guards.policy import Policy
from agentguard.providers.budget import Budget
from agentguard.runner import run
from agentguard.schemas import Scenario
from agentguard.tracing import Sink


def run_paired(
    scenarios: list[Scenario],
    config: RunConfig,
    policy: Policy,
    *,
    oversight: bool = False,
    reviewer_kind: str = "fake-allow",
    max_total_cost: float = 0.0,
    client_factory: Any = None,
    reviewer_client_factory: Any = None,
    trace_sink: Sink | None = None,
    stop_on_error: bool = False,
) -> dict[str, Any]:
    modes = ["baseline", "guarded"] + (["guarded_oversight"] if oversight else [])
    config = RunConfig.model_validate(config.model_dump())
    if (
        not scenarios
        or not math.isfinite(max_total_cost)
        or max_total_cost < 0
        or Decimal(str(config.max_cost)) * len(modes) > Decimal(str(max_total_cost))
    ):
        raise ValueError("Declared total cap must cover all identical per-mode caps")
    if reviewer_kind not in ("fake-allow", "fake-deny", "anthropic"):
        raise ValueError("Unsupported reviewer")
    configs = {
        mode: RunConfig.model_validate(
            {
                **config.model_dump(),
                "mode": mode,
                "reviewer_provider": "anthropic"
                if mode == "guarded_oversight" and reviewer_kind == "anthropic"
                else "injected",
            }
        )
        for mode in modes
    }
    budgets = {
        mode: Budget(cfg) if cfg.provider == "anthropic" else None for mode, cfg in configs.items()
    }
    used = dict.fromkeys(modes, 0)
    collected: dict[str, dict[str, Any]] = {}
    schedule = []
    experiment_id = str(uuid.uuid4())
    stop_reason = None
    for trial in range(config.trials):
        if stop_reason:
            break
        ordered = list(scenarios)
        # Reproducible scheduling/resampling; no secrets or cryptographic use.
        random.Random((config.order_seed or 0) + trial).shuffle(ordered)  # nosec B311
        for index, scenario in enumerate(ordered):
            if stop_reason:
                break
            offset = (index + trial + (config.order_seed or 0)) % len(modes)
            mode_order = modes[offset:] + modes[:offset]
            for mode in mode_order:
                cfg = configs[mode]
                episode_cfg = RunConfig.model_validate({**cfg.model_dump(), "trials": 1})
                reviewer = (
                    FakeReviewer("allow" if reviewer_kind == "fake-allow" else "deny")
                    if mode == "guarded_oversight" and reviewer_kind != "anthropic"
                    else None
                )

                def sink(event: dict[str, Any], t=trial) -> None:
                    if trace_sink:
                        trace_sink({**event, "trial": t, "experiment_id": experiment_id})

                piece = run(
                    [scenario],
                    episode_cfg,
                    policy=policy,
                    reviewer=reviewer,
                    client=client_factory(mode, scenario.id, trial) if client_factory else None,
                    reviewer_client_factory=reviewer_client_factory,
                    budget=budgets[mode],
                    request_offset=used[mode] if budgets[mode] is None else 0,
                    trace_sink=sink if trace_sink else None,
                )
                row = piece["results"][0]
                row["trial"] = trial
                row["episode_run_id"] = piece["run_id"]
                used[mode] += row["execution"]["requests"]
                if mode not in collected:
                    collected[mode] = {**piece, "run_id": str(uuid.uuid4()), "results": []}
                collected[mode]["results"].append(row)
                schedule.append(
                    {
                        "trial": trial,
                        "scenario_id": scenario.id,
                        "mode": mode,
                        "episode_run_id": piece["run_id"],
                    }
                )
                execution = row["execution"]
                review_failure = any(r["decision"] is None for r in execution.get("reviews", []))
                if stop_on_error and (
                    execution["status"] not in ("completed", "answer_blocked", "step_limit")
                    or review_failure
                ):
                    stop_reason = {
                        "mode": mode,
                        "scenario_id": scenario.id,
                        "trial": trial,
                        "status": execution["status"],
                        "review_failure": review_failure,
                    }
                    break
    for mode, result in collected.items():
        result["config"] = configs[mode].model_dump()
        result["scenario_snapshots"] = [s.model_dump() for s in scenarios]
        result["execution_order"] = [[r["scenario_id"], r["trial"]] for r in result["results"]]
        result["budget"] = budgets[mode].snapshot() if budgets[mode] else None
        result["experiment_id"] = experiment_id
        result["experiment_complete"] = stop_reason is None
    return {
        "experiment_id": experiment_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "max_total_estimated_cost_usd": max_total_cost,
        "design": "counterbalanced mode order within scenario/trial; shuffled scenario clusters",
        "schedule": schedule,
        "complete": stop_reason is None,
        "stop_reason": stop_reason,
        "planned_episodes": len(scenarios) * config.trials * len(modes),
        "runs": collected,
    }
