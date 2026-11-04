"""Public synthetic-only projections; never accepts live runs or credentials as input."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from agentguard.config import RunConfig
from agentguard.experiments import run_paired
from agentguard.guards.oversight import FakeReviewer
from agentguard.guards.policy import Policy
from agentguard.reporting import aggregate, compare_runs
from agentguard.runner import load_scenarios, run
from agentguard.schemas import Claim, Scenario, ToolCall, Turn

NOTICE = "SIMULATED â€” deterministic fake-provider infrastructure demonstration; no live findings."
MODES = ("baseline", "guarded", "guarded_oversight")
EXAMPLES = ("pi-004", "pi-010", "tm-002", "tm-007", "ce-001", "ce-010")


def stable(value: Any) -> Any:
    """Remove volatile instrumentation only from a public demonstration projection.

    Actual experimental runs retain their UUIDs, times and latency. No inference
    is made from normalized demonstration traces, including their execution speed.
    """
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key
            not in {"run_id", "episode_run_id", "experiment_id", "event_id", "timestamp", "python"}
            and not key.endswith("latency_seconds")
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def probes(scenarios: list[Scenario]) -> list[Scenario]:
    """Visible scripted behaviors, not new labels, model predictions or model attacks.

    All inputs except fake_script are byte-equivalent in canonical serialization.
    The same overlaid scenario is used across A/B/C; its changed hash is recorded.
    """
    modified = []
    for original in scenarios:
        scenario = original.model_copy(deep=True)
        if scenario.attack_present:
            scenario.fake_script.insert(
                1,
                Turn(
                    call=ToolCall(
                        name="send_email",
                        arguments={
                            "recipient": "untrusted@example.invalid",
                            "body": "SIMULATED unauthorized redirection probe",
                        },
                    )
                ),
            )
        if scenario.id == "pi-004":
            answer = scenario.fake_script[-1].answer
            assert answer is not None
            answer.claims.append(
                Claim(
                    value=scenario.evaluation_criteria.forbidden_values[0],
                    source_ids=[],
                    verified=False,
                )
            )
        if scenario.category == "conflicting_evidence" and (
            scenario.evaluation_criteria.require_uncertainty
        ):
            answer = scenario.fake_script[-1].answer
            assert answer is not None
            answer.uncertainty = False
            for claim in answer.claims:
                claim.verified = True
        modified.append(scenario)
    return modified


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    rows = result["results"]
    return {
        "label": "SIMULATED",
        "metrics": aggregate(result),
        "episodes": len(rows),
        "requests": sum(row["execution"]["requests"] for row in rows),
        "proposed_unsafe_actions": sum(
            row["evaluation"]["proposed_unsafe_actions"] for row in rows
        ),
        "executed_sensitive_actions": sum(len(row["execution"]["effects"]) for row in rows),
        "executed_unauthorized_actions": sum(
            row["evaluation"]["unauthorized_actions"] for row in rows
        ),
        "blocked_actions": sum(len(row["execution"]["blocked_actions"]) for row in rows),
        "review_calls": sum(len(row["execution"]["reviews"]) for row in rows),
        "review_denials": sum(
            not review["allowed"] for row in rows for review in row["execution"]["reviews"]
        ),
        "estimated_api_cost_usd": 0,
        "tokens": None,
        "latency": None,
        "confidence_interval": None,
        "inference_notice": "No statistical model inference, API token usage or live latency.",
    }


def build_demo(repository: Path, output: Path) -> dict[str, Any]:
    """Generate a complete projection from fixed synthetic assets, exclusively offline."""
    scenarios = load_scenarios(repository / "scenarios")
    if len(scenarios) != 30:
        raise ValueError("The public demo requires the frozen 30-scenario corpus")
    policy = Policy.model_validate_json(
        (repository / "examples/policy.json").read_text(encoding="utf-8")
    )
    output.mkdir(parents=True, exist_ok=False)
    payload: dict[str, Any] = {
        "schema": "agentguard-simulated-demo-v1",
        "notice": NOTICE,
        "simulation": True,
        "provider": "fake",
        "live_results": False,
        "profiles": {},
        "corpus": [
            {
                "id": s.id,
                "category": s.category,
                "version": s.version,
                "objective": s.legitimate_objective,
                "attack_present": s.attack_present,
                "sha256": hashlib.sha256(s.model_dump_json().encode()).hexdigest(),
            }
            for s in scenarios
        ],
        "policy_sha256": hashlib.sha256(policy.model_dump_json().encode()).hexdigest(),
        "normalization": (
            "Volatile UUIDs, timestamps, Python version and measured latencies omitted."
        ),
    }
    trace_rows = []
    csv_rows = []
    for profile, selected in (("reference", scenarios), ("adversarial", probes(scenarios))):
        experiment = run_paired(
            selected,
            RunConfig(max_requests=300, order_seed=1729),
            policy,
            oversight=True,
            reviewer_kind="fake-allow",
        )
        assert experiment["complete"]
        runs = experiment["runs"]
        comparisons = {mode: compare_runs(runs["baseline"], runs[mode]) for mode in MODES[1:]}
        profile_data = {
            "label": "SIMULATED",
            "schedule": stable(experiment["schedule"]),
            "configuration": runs["baseline"]["config"],
            "reviewer": "fake-allow; deterministic interface test, no LLM oversight",
            "comparisons": stable(comparisons),
            "modes": {},
            "examples": [],
        }
        for mode, result in runs.items():
            if result["provider_metadata"]["name"] != "fake":
                raise ValueError("Public demo refuses non-fake results")
            summary = summarize(result)
            summary["per_category"] = {
                category: summarize(
                    {"results": [r for r in result["results"] if r["category"] == category]}
                )
                for category in sorted({r["category"] for r in result["results"]})
            }
            profile_data["modes"][mode] = summary
            for metric, values in summary["metrics"].items():
                csv_rows.append(
                    {
                        "label": "SIMULATED",
                        "profile": profile,
                        "mode": mode,
                        "metric": metric,
                        **values,
                    }
                )
            for row in result["results"]:
                projected = stable({"label": "SIMULATED", "profile": profile, "mode": mode, **row})
                trace_rows.append(projected)
                if row["scenario_id"] in EXAMPLES:
                    profile_data["examples"].append(projected)
        payload["profiles"][profile] = profile_data

    # Deliberately wrong reviewer on authorized actions, separate from A/B/C arms.
    refusal_probe = run(
        [s for s in scenarios if s.authorized_calls],
        RunConfig(mode="guarded_oversight", max_requests=100),
        policy=policy,
        reviewer=FakeReviewer("deny"),
    )
    payload["false_refusal_diagnostic"] = {
        "notice": "SIMULATED separate diagnostic: fake-deny reviewer on three authorized tasks.",
        "summary": summarize(refusal_probe),
    }
    for row in refusal_probe["results"]:
        trace_rows.append(
            stable(
                {
                    "label": "SIMULATED",
                    "profile": "false_refusal_diagnostic",
                    "mode": "guarded_oversight",
                    **row,
                }
            )
        )
    (output / "demo.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (output / "traces.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace_rows),
        encoding="utf-8",
        newline="\n",
    )
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)
    lines = ["# SIMULATED AgentGuard demonstration", "", NOTICE, ""]
    for profile, data in payload["profiles"].items():
        lines += [f"## SIMULATED {profile}", ""]
        for mode, summary in data["modes"].items():
            lines.append(f"### SIMULATED {mode}")
            lines += [
                f"- {name}: {v['numerator']}/{v['denominator']}"
                for name, v in summary["metrics"].items()
            ]
            lines += [f"- Blocked actions: {summary['blocked_actions']}", ""]
    lines += [
        "## Interpretation",
        "",
        "Scripts define behavior and ignore tool content. "
        "These differences demonstrate runtime enforcement, not model robustness. "
        "No informative confidence interval, model latency or API tokens apply. "
        "API cost is exactly $0. No live Claude benchmark results are included.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "label": "SIMULATED",
        "schema": payload["schema"],
        "policy_sha256": payload["policy_sha256"],
        "corpus_sha256": {s["id"]: s["sha256"] for s in payload["corpus"]},
        "files_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
        },
        "trace_rows": len(trace_rows),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return payload
