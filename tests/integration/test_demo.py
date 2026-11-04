import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.demo import build_demo, probes
from agentguard.runner import load_scenarios


@pytest.fixture(scope="module")
def public_demo(tmp_path_factory):
    output = tmp_path_factory.mktemp("public-demo") / "data"
    return build_demo(Path.cwd(), output), output


def test_demo_distinguishes_simulated_proposals_execution_and_refusal(public_demo):
    data, output = public_demo
    assert data["simulation"] and not data["live_results"] and data["provider"] == "fake"
    assert len(data["corpus"]) == 30
    for profile in data["profiles"].values():
        assert len(profile["schedule"]) == 90
        assert all(m["episodes"] == 30 for m in profile["modes"].values())
        assert all(m["confidence_interval"] is None for m in profile["modes"].values())
    arms = data["profiles"]["adversarial"]["modes"]
    assert arms["baseline"]["executed_unauthorized_actions"] == 16
    for mode in ("guarded", "guarded_oversight"):
        assert arms[mode]["executed_unauthorized_actions"] == 0
        assert arms[mode]["proposed_unsafe_actions"] == 16
        assert arms[mode]["blocked_actions"] == 16
        assert arms[mode]["metrics"]["model_attack_success_rate"]["numerator"] > 0
        assert arms[mode]["metrics"]["task_completion_rate"]["numerator"] < 30
    reference = data["profiles"]["reference"]["modes"]
    assert all(m["metrics"]["task_completion_rate"]["numerator"] == 30 for m in reference.values())
    assert reference["guarded_oversight"]["review_calls"] == 3
    diagnostic = data["false_refusal_diagnostic"]["summary"]
    assert diagnostic["metrics"]["false_refusal_rate"]["numerator"] == 3
    rows = [json.loads(line) for line in (output / "traces.jsonl").read_text().splitlines()]
    assert len(rows) == 183 and all(row["label"] == "SIMULATED" for row in rows)
    assert any(e["event"] == "reviewer_decision" for r in rows for e in r["execution"]["trace"])
    assert all(m["estimated_api_cost_usd"] == 0 for m in arms.values())


def test_demo_is_byte_reproducible_and_has_verifiable_hashes(public_demo, tmp_path):
    _, first = public_demo
    second = tmp_path / "repeat"
    build_demo(Path.cwd(), second)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes(), path.name
    manifest = json.loads((first / "manifest.json").read_text())
    for name, expected in manifest["files_sha256"].items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == expected
    # Existing demonstration data cannot be silently overwritten.
    with pytest.raises(FileExistsError):
        build_demo(Path.cwd(), second)


def test_script_overlay_preserves_all_frozen_fields():
    original = load_scenarios(Path("scenarios"))
    before = [s.model_dump_json() for s in original]
    modified = probes(original)
    for a, b in zip(original, modified, strict=True):
        assert a.model_dump(exclude={"fake_script"}) == b.model_dump(exclude={"fake_script"})
    assert [s.model_dump_json() for s in original] == before


def test_checked_in_public_artifacts_match_current_engine(public_demo):
    _, generated = public_demo
    for path in generated.iterdir():
        assert path.read_bytes() == (Path("site/data") / path.name).read_bytes(), path.name


def test_demo_cli_and_errors_are_offline(tmp_path):
    target = tmp_path / "demo"
    result = CliRunner().invoke(app, ["demo", "--output", str(target)])
    assert result.exit_code == 0 and "SIMULATED" in result.output
    assert CliRunner().invoke(app, ["demo", "--output", str(target)]).exit_code != 0
