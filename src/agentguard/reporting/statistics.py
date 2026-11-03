"""Scenario-cluster percentile intervals, conditional on the fixed selected corpus."""

import random
from collections import defaultdict
from typing import Any

ENDPOINTS = {
    "model_attack_success": "model_attack_success",
    "runtime_attack_success": "runtime_attack_success",
    "task_completion": "task_completed",
    "false_refusal": "false_refusal",
}


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def intervals(
    run: dict[str, Any],
    candidate: dict[str, Any] | None = None,
    *,
    resamples: int = 2000,
    seed: int = 1729,
) -> dict[str, Any]:
    """Repeated trials stay clustered. Paired comparisons resample the same scenario IDs."""
    if resamples < 100:
        raise ValueError("Use at least 100 bootstrap resamples")
    real = run.get("provider_metadata", {}).get("live") and not run.get(
        "provider_metadata", {}
    ).get("client_injected")
    if candidate is not None:
        real = (
            real
            and candidate.get("provider_metadata", {}).get("live")
            and not candidate.get("provider_metadata", {}).get("client_injected")
        )
    if not real:
        return {
            "available": False,
            "reason": "fake_or_injected_client; no inferential model evidence",
        }
    if run.get("experiment_complete") is False or (
        candidate and candidate.get("experiment_complete") is False
    ):
        return {"available": False, "reason": "qualification stopped early; incomplete design"}
    a, b = defaultdict(list), defaultdict(list)
    for row in run["results"]:
        a[row["scenario_id"]].append(row["evaluation"])
    if candidate is not None:
        for row in candidate["results"]:
            b[row["scenario_id"]].append(row["evaluation"])
        if a.keys() != b.keys():
            raise ValueError("Paired scenario clusters differ")
    output: dict[str, Any] = {
        "available": True,
        "method": "scenario-cluster paired percentile bootstrap"
        if candidate
        else "scenario-cluster percentile bootstrap",
        "confidence": 0.95,
        "seed": seed,
        "resamples": resamples,
        "scope": "descriptive conditional-on-corpus; no population/significance claim",
        "endpoints": {},
    }
    for label, field in ENDPOINTS.items():
        if candidate:
            left_eligibility = {
                (r["scenario_id"], r["trial"]): r["evaluation"].get(field) is not None
                for r in run["results"]
            }
            right_eligibility = {
                (r["scenario_id"], r["trial"]): r["evaluation"].get(field) is not None
                for r in candidate["results"]
            }
            if left_eligibility != right_eligibility:
                raise ValueError("Paired trial or endpoint eligibility differs")
        ids = [
            identity for identity in sorted(a) if any(e.get(field) is not None for e in a[identity])
        ]
        if len(ids) < 2:
            output["endpoints"][label] = {
                "interval": None,
                "reason": "fewer_than_two_eligible_scenarios",
            }
            continue

        def rate(groups, draw, field=field):
            values = [
                e[field] for identity in draw for e in groups[identity] if e.get(field) is not None
            ]
            return sum(values) / len(values)

        # Reproducible scheduling/resampling; no secrets or cryptographic use.
        rng = random.Random(seed)  # nosec B311
        values = []
        for _ in range(resamples):
            draw = rng.choices(ids, k=len(ids))
            values.append(rate(b, draw) - rate(a, draw) if candidate is not None else rate(a, draw))
        output["endpoints"][label] = {
            "interval": [_quantile(values, 0.025), _quantile(values, 0.975)]
            if len(set(values)) > 1
            else None,
            "warning": None
            if len(set(values)) > 1
            else "degenerate bootstrap; no informative uncertainty bound",
            "eligible_scenarios": len(ids),
        }
    return output
