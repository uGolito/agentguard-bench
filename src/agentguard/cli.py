"""Offline by default; live requests require explicit opt-in and a positive budget."""

import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from agentguard.config import RunConfig
from agentguard.experiments import run_paired
from agentguard.guards.oversight import FakeReviewer
from agentguard.guards.policy import Policy
from agentguard.reporting import compare_runs, markdown, write_run
from agentguard.runner import load_scenarios
from agentguard.runner import run as run_benchmark
from agentguard.tracing import Journal

app = typer.Typer(no_args_is_help=True)
ScenarioPath = Annotated[Path, typer.Option("--scenarios")]


@app.command("demo")
def demo(output: Path = Path("results/demo")) -> None:
    """Build a SIMULATED public projection from the fixed offline corpus; never calls APIs."""
    from agentguard.demo import build_demo

    try:
        build_demo(Path.cwd(), output)
        typer.echo(f"SIMULATED offline demonstration: {output / 'demo.json'}")
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


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
    reviewer_model: str = "claude-haiku-4-5-20251001",
    reviewer_max_tokens: int = 256,
    order_seed: int | None = None,
    model_seed: int | None = None,
    scenario_ids: Annotated[list[str] | None, typer.Option("--scenario-id")] = None,
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
    if mode == "guarded_oversight" and reviewer not in ("fake-allow", "fake-deny", "anthropic"):
        raise typer.BadParameter("Specify --reviewer fake-allow|fake-deny|anthropic")
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
            reviewer_provider="anthropic" if reviewer == "anthropic" else "injected",
            reviewer_model=reviewer_model,
            reviewer_max_tokens=reviewer_max_tokens,
            order_seed=order_seed,
            model_seed=model_seed,
        )
        trusted_policy = (
            Policy.model_validate_json(policy.read_text(encoding="utf-8")) if policy else Policy()
        )
        reviewer_instance = (
            FakeReviewer("allow" if reviewer == "fake-allow" else "deny")
            if reviewer in ("fake-allow", "fake-deny")
            else None
        )
        selected = load_scenarios(scenarios, category)
        if scenario_ids:
            if set(scenario_ids) - {s.id for s in selected}:
                raise ValueError("Unknown or filtered scenario ID")
            selected = [s for s in selected if s.id in scenario_ids]
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
        journal = Journal(output / "journal.jsonl")
        try:
            result = run_benchmark(
                selected,
                config,
                policy=trusted_policy,
                reviewer=reviewer_instance,
                trace_sink=journal,
            )
        finally:
            journal.close()
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


@app.command("paired-run")
def paired_run(
    policy: Annotated[Path, typer.Option("--policy")],
    scenarios: ScenarioPath = Path("scenarios"),
    provider: str = "fake",
    model: str | None = None,
    trials: int = 1,
    order_seed: int = 1729,
    max_steps: int = 8,
    max_requests: int = 100,
    max_cost: float = 0.0,
    max_total_cost: float = 0.0,
    max_tokens: int = 512,
    max_retries: int = 0,
    timeout: float = 30.0,
    reviewer_timeout: float = 30.0,
    with_oversight: bool = False,
    reviewer: str = "fake-allow",
    stop_on_error: bool = False,
    allow_live: bool = False,
    scenario_ids: Annotated[list[str] | None, typer.Option("--scenario-id")] = None,
    dry_run: bool = False,
    output: Path = Path("results/paired"),
) -> None:
    """Counterbalance paired A/B(/C) episodes; per-mode caps are covered by --max-total-cost."""
    try:
        config = RunConfig(
            provider=provider,
            model=model or "scripted-fixture-v1",
            allow_live=allow_live or dry_run,
            trials=trials,
            order_seed=order_seed,
            max_steps=max_steps,
            max_requests=max_requests,
            max_cost=max_cost,
            max_tokens=max_tokens,
            max_retries=max_retries,
            timeout_seconds=timeout,
            reviewer_timeout_seconds=reviewer_timeout,
        )
        trusted_policy = Policy.model_validate_json(policy.read_text(encoding="utf-8"))
        selected = load_scenarios(scenarios)
        if scenario_ids:
            if set(scenario_ids) - {s.id for s in selected}:
                raise ValueError("Unknown scenario ID")
            selected = [s for s in selected if s.id in scenario_ids]
        modes = 3 if with_oversight else 2
        if (
            not math.isfinite(max_total_cost)
            or max_total_cost < 0
            or Decimal(str(max_cost)) * modes > Decimal(str(max_total_cost))
        ):
            raise ValueError("Total cap must cover all per-mode caps")
        if reviewer not in ("anthropic", "fake-allow", "fake-deny"):
            raise ValueError("Unsupported reviewer")
        if with_oversight and reviewer == "anthropic":
            RunConfig.model_validate(
                {
                    **config.model_dump(),
                    "mode": "guarded_oversight",
                    "reviewer_provider": "anthropic",
                }
            )
        if dry_run:
            typer.echo(
                f"NO API CALLS: {len(selected)} scenarios x {trials} trials x {modes} modes; "
                f"requests <= {max_requests * modes}, estimated total cap ${max_total_cost}"
            )
            return
        output.mkdir(parents=True, exist_ok=False)
        journal = Journal(output / "journal.jsonl")
        try:
            experiment = run_paired(
                selected,
                config,
                trusted_policy,
                oversight=with_oversight,
                reviewer_kind=reviewer,
                max_total_cost=max_total_cost,
                trace_sink=journal,
                stop_on_error=stop_on_error,
            )
        finally:
            journal.close()
        for mode, result in experiment["runs"].items():
            write_run(result, output / mode)
        (output / "experiment.json").write_text(json.dumps(experiment, indent=2), encoding="utf-8")
        for mode in experiment["runs"]:
            if mode != "baseline" and experiment["complete"]:
                comparison = compare_runs(experiment["runs"]["baseline"], experiment["runs"][mode])
                (output / f"baseline-vs-{mode}.json").write_text(
                    json.dumps(comparison, indent=2), encoding="utf-8"
                )
        typer.echo(str(output / "experiment.json"))
        if not experiment["complete"]:
            raise typer.Exit(code=2)
    except ValidationError:
        raise typer.BadParameter(
            "Invalid experiment schema; check model, opt-in and numeric limits"
        ) from None
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


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
