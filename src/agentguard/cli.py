"""Offline by default; live requests require explicit opt-in and a positive budget."""

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from agentguard.config import RunConfig
from agentguard.guards.oversight import FakeReviewer
from agentguard.guards.policy import Policy
from agentguard.reporting import compare_runs, markdown, write_run
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
    policy: Path | None = None,
    reviewer: str | None = None,
    reviewer_timeout: float = 2.0,
    dry_run: bool = False,
    output: Path = Path("results/offline"),
) -> None:
    """Run controlled modes. Live model requests require --allow-live; previews never call APIs."""
    mode = mode.replace("-", "_")
    if mode not in ("baseline", "guarded", "guarded_oversight") or provider not in (
        "fake",
        "anthropic",
    ):
        raise typer.BadParameter("Supported modes: baseline, guarded, guarded_oversight")
    if mode != "baseline" and policy is None:
        raise typer.BadParameter("Guarded modes require an explicit trusted --policy JSON file")
    if mode == "guarded_oversight" and reviewer not in ("fake-allow", "fake-deny"):
        raise typer.BadParameter(
            "Specify --reviewer fake-allow|fake-deny; no live reviewer is implemented"
        )
    if mode != "guarded_oversight" and reviewer is not None:
        raise typer.BadParameter("--reviewer requires --mode guarded_oversight")
    try:
        config = RunConfig(
            mode=mode,
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
            reviewer_timeout_seconds=reviewer_timeout,
        )
        trusted_policy = (
            Policy.model_validate_json(policy.read_text(encoding="utf-8")) if policy else Policy()
        )
        reviewer_instance = (
            FakeReviewer("allow" if reviewer == "fake-allow" else "deny") if reviewer else None
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
        result = run_benchmark(selected, config, policy=trusted_policy, reviewer=reviewer_instance)
        write_run(result, output, directory_prepared=True)
        typer.echo(str(output / "run.json"))
    except ValidationError as exc:
        locations = [
            ".".join(map(str, error["loc"])) or "root"
            for error in exc.errors(include_input=False, include_context=False)
        ]
        raise typer.BadParameter("Schema validation failed at: " + ", ".join(locations)) from None
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
    """Validate experimental controls and show paired counts; no significance claim."""
    try:
        typer.echo(
            json.dumps(
                compare_runs(
                    json.loads(baseline.read_text(encoding="utf-8")),
                    json.loads(candidate.read_text(encoding="utf-8")),
                ),
                indent=2,
            )
        )
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
