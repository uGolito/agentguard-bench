"""Raw counts and separate metric denominators."""

import csv
import json
from pathlib import Path
from typing import Any


def aggregate(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = run["results"]
    evaluations = [r["evaluation"] for r in rows]
    attacks = [e for e in evaluations if e["attack_success"] is not None]
    pairs = {
        "attack_success_rate": (sum(e["attack_success"] for e in attacks), len(attacks)),
        "task_completion_rate": (sum(e["task_completed"] for e in evaluations), len(rows)),
        "unauthorized_action_rate": (
            sum(e["unauthorized_actions"] > 0 for e in evaluations),
            len(rows),
        ),
        "false_refusal_rate": (sum(e["false_refusal"] for e in evaluations), len(rows)),
    }
    return {
        name: {"numerator": n, "denominator": d, "rate": n / d if d else None}
        for name, (n, d) in pairs.items()
    }


def markdown(run: dict[str, Any]) -> str:
    metadata = run["provider_metadata"]
    notice = "Scripted fake provider only. These are not live LLM benchmark findings."
    if metadata.get("live"):
        notice = (
            "Injected-client infrastructure execution; not evidence of live LLM performance."
            if metadata.get("client_injected")
            else "Anthropic API execution. Narrow deterministic criteria; no safety guarantee."
        )
    lines = [
        "# AgentGuard execution report",
        "",
        f"Run: {run['run_id']}",
        "",
        notice,
        "",
    ]
    for name, value in aggregate(run).items():
        lines.append(f"- {name}: {value['numerator']}/{value['denominator']}")
    if run.get("budget"):
        lines.extend(["", "## API accounting", "", json.dumps(run["budget"], sort_keys=True)])
    return "\n".join(lines) + "\n"


def write_run(run: dict[str, Any], output: Path, *, directory_prepared: bool = False) -> None:
    # Exclusive directory creation avoids silently replacing raw experimental data.
    if not directory_prepared:
        output.mkdir(parents=True, exist_ok=False)
    with (output / "run.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(run, indent=2) + "\n")
    with (output / "traces.jsonl").open("x", encoding="utf-8") as stream:
        for row in run["results"]:
            for event in row["execution"]["trace"]:
                stream.write(
                    json.dumps(
                        {
                            "run_id": run["run_id"],
                            "scenario_id": row["scenario_id"],
                            "trial": row["trial"],
                            **event,
                        }
                    )
                    + "\n"
                )
    with (output / "metrics.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "numerator", "denominator", "rate"])
        writer.writeheader()
        for name, value in aggregate(run).items():
            writer.writerow({"metric": name, **value})
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(markdown(run))
