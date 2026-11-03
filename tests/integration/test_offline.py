import json
from pathlib import Path

from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.config import RunConfig
from agentguard.runner import load_scenarios, run


def test_all_scenarios_repeated():
    scenarios = load_scenarios(Path("tests/fixtures/milestone3"))
    first = run(scenarios, RunConfig(trials=2))
    second = run(scenarios, RunConfig(trials=2))
    assert first["run_id"] != second["run_id"]
    assert len(first["results"]) == 6
    assert all(r["evaluation"]["task_completed"] for r in first["results"])
    assert [r["evaluation"] for r in first["results"]] == [
        r["evaluation"] for r in second["results"]
    ]


def test_cli(tmp_path):
    runner = CliRunner()
    assert runner.invoke(app, ["validate-scenarios"]).exit_code == 0
    assert runner.invoke(app, ["list-scenarios"]).exit_code == 0
    output = tmp_path / "new"
    assert runner.invoke(app, ["run", "--dry-run", "--output", str(output)]).exit_code == 0
    assert not output.exists()
    result = runner.invoke(app, ["run", "--output", str(output)])
    assert result.exit_code == 0, result.output
    path = output / "run.json"
    assert json.loads(path.read_text())["provider_metadata"]["live"] is False
    assert runner.invoke(app, ["report", "--run", str(path)]).exit_code == 0
    assert (
        runner.invoke(app, ["compare", "--baseline", str(path), "--candidate", str(path)]).exit_code
        == 0
    )
    assert runner.invoke(app, ["run", "--provider", "anthropic"]).exit_code != 0
    assert runner.invoke(app, ["run", "--mode", "guarded"]).exit_code != 0
    assert runner.invoke(app, ["run", "--category", "unknown"]).exit_code != 0
