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
    lines = [
        "# Offline infrastructure report",
        "",
        f"Run: {run['run_id']}",
        "",
        "Scripted fake provider only. These are not live LLM benchmark findings.",
        "",
    ]
    for name, value in aggregate(run).items():
        lines.append(f"- {name}: {value['numerator']}/{value['denominator']}")
    return "\n".join(lines) + "\n"


def write_run(run: dict[str, Any], output: Path) -> None:
    # Exclusive directory creation avoids silently replacing raw experimental data.
    output.mkdir(parents=True, exist_ok=False)
    (output / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    with (output / "traces.jsonl").open("w", encoding="utf-8") as stream:
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
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "numerator", "denominator", "rate"])
        writer.writeheader()
        for name, value in aggregate(run).items():
            writer.writerow({"metric": name, **value})
    (output / "report.md").write_text(markdown(run), encoding="utf-8")
