"""Offline by default; live requests require explicit opt-in and a positive budget."""

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
    model: str | None = None,
    allow_live: bool = False,
    category: str | None = None,
    max_steps: int = 8,
    max_requests: int = 100,
    max_cost: float = 0.0,
    trials: int = 1,
    max_tokens: int = 512,
    temperature: float = 0.0,
    timeout: float = 30.0,
    max_retries: int = 0,
    dry_run: bool = False,
    output: Path = Path("results/offline"),
) -> None:
    """Run baseline agents. --allow-live permits paid Anthropic calls; dry runs never call APIs."""
    if mode != "baseline" or provider not in ("fake", "anthropic"):
        raise typer.BadParameter("Supported: --mode baseline --provider fake|anthropic")
    try:
        config = RunConfig(
            provider=provider,
            model=model or "scripted-fixture-v1",
            allow_live=allow_live or dry_run,
            max_steps=max_steps,
            max_requests=max_requests,
            max_cost=max_cost,
            trials=trials,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout,
            max_retries=max_retries,
        )
        selected = load_scenarios(scenarios, category)
        if dry_run:
            if provider == "anthropic":
                from agentguard.providers.budget import Budget

                reservation = Budget(config).snapshot()["next_attempt_reservation_usd"]
                typer.echo(
                    f"NO API CALLS: {len(selected)} scenarios x {trials} trials; "
                    f"reserve ${reservation:.6f}/attempt; cap ${max_cost}; "
                    f"requests <= {max_requests}"
                )
            else:
                typer.echo(f"Offline plan: {len(selected)} scenarios x {trials} trials; cost $0")
            return
        # Reserve a writable artifact directory before any potentially billable work.
        output.mkdir(parents=True, exist_ok=False)
        result = run_benchmark(selected, config)
        write_run(result, output, directory_prepared=True)
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
