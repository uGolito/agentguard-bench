"""Explicitly offline command line interface."""

import json
from pathlib import Path
from typing import Annotated

import typer

from agentguard.config import RunConfig
from agentguard.reporting import aggregate, markdown, write_run
from agentguard.runner import load_scenarios
from agentguard.runner import run as run_benchmark

app = typer.Typer(no_args_is_help=True)
ScenarioPath = Annotated[Path, typer.Option("--scenarios")]


@app.command("list-scenarios")
def list_scenarios(scenarios: ScenarioPath = Path("scenarios")) -> None:
    """List validated scenario IDs and categories."""
    for scenario in load_scenarios(scenarios):
        typer.echo(f"{scenario.id} {scenario.version} {scenario.category}")


@app.command("validate-scenarios")
def validate_scenarios(scenarios: ScenarioPath = Path("scenarios")) -> None:
    """Validate schemas and uniqueness."""
    typer.echo(f"Validated {len(load_scenarios(scenarios))} scenarios")


@app.command()
def run(
    scenarios: ScenarioPath = Path("scenarios"),
    mode: str = "baseline",
    provider: str = "fake",
    category: str | None = None,
    max_steps: int = 8,
    max_requests: int = 100,
    max_cost: float = 0.0,
    trials: int = 1,
    dry_run: bool = False,
    output: Path = Path("results/offline"),
) -> None:
    """Run synthetic fixtures. Live providers and guarded modes arrive in later milestones."""
    if mode != "baseline" or provider != "fake":
        raise typer.BadParameter("Milestone 1 supports --mode baseline --provider fake only")
    try:
        config = RunConfig(
            max_steps=max_steps, max_requests=max_requests, max_cost=max_cost, trials=trials
        )
        selected = load_scenarios(scenarios, category)
        if dry_run:
            typer.echo(f"Offline plan: {len(selected)} scenarios x {trials} trials; cost $0")
            return
        result = run_benchmark(selected, config)
        write_run(result, output)
        typer.echo(str(output / "run.json"))
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def report(run: Annotated[Path, typer.Option("--run")]) -> None:
    """Render an existing run as Markdown."""
    typer.echo(markdown(json.loads(run.read_text(encoding="utf-8"))))


@app.command()
def compare(
    baseline: Annotated[Path, typer.Option("--baseline")],
    candidate: Annotated[Path, typer.Option("--candidate")],
) -> None:
    """Show separate raw metrics; no significance or model-performance claim."""
    for label, path in [("baseline", baseline), ("candidate", candidate)]:
        typer.echo(json.dumps({label: aggregate(json.loads(path.read_text(encoding="utf-8")))}))
