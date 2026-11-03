import json
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.config import RunConfig
from agentguard.evaluators import evaluate
from agentguard.experiments import run_paired
from agentguard.guards.oversight import FakeReviewer
from agentguard.guards.policy import Policy
from agentguard.providers import FakeProvider
from agentguard.reporting import aggregate, compare_runs
from agentguard.runner import load_scenarios, run
from agentguard.tools import SyntheticTools
from agentguard.tracing import EventLog, Journal


@pytest.fixture
def corpus():
    return load_scenarios(Path("scenarios"))


@pytest.fixture
def policy():
    return Policy.model_validate_json(Path("examples/policy.json").read_text())


def test_thirty_original_versioned_cases_and_positive_controls(corpus):
    counts = Counter(s.category for s in corpus)
    assert len(corpus) == 30 and set(counts.values()) == {10}
    assert len({s.id for s in corpus}) == 30
    assert len({json.dumps(s.fixtures, sort_keys=True) for s in corpus}) == 30
    assert sum(bool(s.authorized_calls) for s in corpus) == 3
    assert any(not s.attack_present for s in corpus if s.category == "prompt_injection")
    for scenario in corpus:
        assert scenario.version == "1.0.0"
        assert scenario.legitimate_objective and scenario.threat_model
        assert scenario.failure_condition and scenario.expected_authorized_behavior
        assert scenario.evaluation_criteria.required_values


@pytest.mark.parametrize("mode", ["baseline", "guarded", "guarded_oversight"])
def test_all_thirty_safe_fixture_scripts_complete_repeatedly(corpus, policy, mode):
    before = [s.model_dump_json() for s in corpus]
    result = run(
        corpus,
        RunConfig(mode=mode, trials=2, max_requests=300, order_seed=47),
        policy=policy,
        reviewer=FakeReviewer() if mode == "guarded_oversight" else None,
    )
    assert len(result["results"]) == 60
    assert all(r["evaluation"]["task_completed"] for r in result["results"])
    assert aggregate(result)["task_completion_rate"]["denominator"] == 60
    assert [s.model_dump_json() for s in corpus] == before
    if mode == "guarded_oversight":
        assert sum(len(r["execution"]["reviews"]) for r in result["results"]) == 6


def test_paired_schedule_and_trials_reproduce_without_sharing_state(corpus, policy):
    subset = [s for s in corpus if s.id in ("pi-004", "pi-010", "tm-010", "ce-010")]
    config = RunConfig(trials=3, max_requests=100, order_seed=17)
    a = run_paired(subset, config, policy, oversight=True)
    b = run_paired(subset, config, policy, oversight=True)
    assert a["complete"] and len(a["schedule"]) == 36
    assert [(x["trial"], x["scenario_id"], x["mode"]) for x in a["schedule"]] == [
        (x["trial"], x["scenario_id"], x["mode"]) for x in b["schedule"]
    ]
    assert a["experiment_id"] != b["experiment_id"]
    for mode in a["runs"]:
        rows = a["runs"][mode]["results"]
        assert len(rows) == 12
        assert all(r["evaluation"]["task_completed"] for r in rows)
        assert len({r["episode_run_id"] for r in rows}) == 12
        assert len(a["runs"][mode]["scenario_snapshots"]) == 4
    comparison = compare_runs(a["runs"]["baseline"], a["runs"]["guarded_oversight"])
    assert len(comparison["paired_outcomes"]) == 12
    assert not comparison["confidence_intervals"]["available"]


def test_fake_request_limits_are_per_mode_across_paired_episodes(corpus, policy):
    experiment = run_paired(corpus[:3], RunConfig(max_requests=1, trials=2), policy)
    for result in experiment["runs"].values():
        assert sum(r["execution"]["requests"] for r in result["results"]) == 1
        assert len(result["results"]) == 6  # Keep all failed/incomplete outcomes.


def test_fixture_mutation_cannot_leak_to_later_scenarios():
    fixtures = {"report": {"source_id": "x", "body": "Original"}}
    tool = SyntheticTools(fixtures)
    from agentguard.schemas import ToolCall

    returned = tool.execute(ToolCall(name="fetch_report", arguments={"key": "report"}))
    returned["body"] = "Mutated only in episode"
    assert fixtures["report"]["body"] == "Original"
    assert SyntheticTools(fixtures).fixtures["report"]["body"] == "Original"


def test_model_proposal_and_runtime_effect_are_different_endpoints(corpus, policy):
    from agentguard.schemas import ToolCall, Turn

    scenario = next(s for s in corpus if s.id == "pi-008").model_copy(deep=True)
    action = ToolCall(name="update_record", arguments={"record_id": "quartz", "value": "0"})
    scenario.fake_script.insert(1, Turn(call=action))
    result = run([scenario], RunConfig(mode="guarded"), policy=policy)
    verdict = result["results"][0]["evaluation"]
    assert verdict["proposed_unsafe_actions"] == 1
    assert verdict["unauthorized_actions"] == 0
    assert verdict["model_attack_success"] is True
    assert verdict["runtime_attack_success"] is False
    assert verdict["task_completed"] is True


def test_wrong_benign_evidence_is_not_an_attack_and_extra_claims_fail(corpus):
    scenario = next(s for s in corpus if s.id == "ce-009")
    answer = scenario.fake_script[-1].answer.model_dump()
    answer["claims"].append({"value": "99 items", "source_ids": ["report"], "verified": False})
    verdict = evaluate(scenario, {"answer": answer, "proposed_answer": answer, "effects": []})
    assert not verdict["task_completed"] and verdict["delivered_wrong_claims"]
    assert verdict["model_attack_success"] is None
    assert verdict["runtime_attack_success"] is None


def test_provenance_mismatch_fails_independent_rubric(corpus):
    scenario = next(s for s in corpus if s.id == "pi-010")
    answer = scenario.fake_script[-1].answer.model_dump()
    answer["claims"][0]["source_ids"] = ["invented-reference"]
    effects = [{"tool": c.name, "arguments": c.arguments} for c in scenario.authorized_calls]
    verdict = evaluate(scenario, {"answer": answer, "effects": effects})
    assert not verdict["task_completed"] and verdict["delivered_wrong_sources"]


def test_journal_flushes_request_before_provider_continues(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal = Journal(path)
    events = EventLog(journal)
    events.append({"event": "api_request", "data": {"reservation_id": "synthetic"}})
    assert json.loads(path.read_text())["event"] == "api_request"
    events.extend(events[:])  # The same event ID must not be journaled twice.
    journal.close()
    assert len(path.read_text().splitlines()) == 1


def test_paired_cli_outputs_and_preview_are_offline(tmp_path):
    runner = CliRunner()
    args = [
        "paired-run",
        "--policy",
        "examples/policy.json",
        "--scenario-id",
        "pi-010",
        "--scenario-id",
        "ce-010",
        "--with-oversight",
        "--trials",
        "2",
    ]
    preview = runner.invoke(app, [*args, "--dry-run", "--output", str(tmp_path / "preview")])
    assert preview.exit_code == 0, preview.output
    assert not (tmp_path / "preview").exists()
    result = runner.invoke(app, [*args, "--output", str(tmp_path / "actual")])
    assert result.exit_code == 0, result.output
    output = tmp_path / "actual"
    data = json.loads((output / "experiment.json").read_text())
    assert data["complete"] and data["planned_episodes"] == 12
    assert (output / "baseline-vs-guarded_oversight.json").exists()
    assert (output / "guarded" / "analysis.json").exists()
    assert (output / "journal.jsonl").read_text()


def test_stop_on_error_retains_partial_design_without_comparison(tmp_path, monkeypatch):
    from agentguard.providers import ProviderError

    def broken(self, messages):
        raise ProviderError("provider_exception")

    monkeypatch.setattr(FakeProvider, "next_turn", broken)
    output = tmp_path / "stopped"
    result = CliRunner().invoke(
        app,
        [
            "paired-run",
            "--policy",
            "examples/policy.json",
            "--stop-on-error",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 2
    data = json.loads((output / "experiment.json").read_text())
    assert not data["complete"] and data["stop_reason"]["status"] == "provider_exception"
    assert len(data["schedule"]) == 1
    assert not list(output.glob("baseline-vs-*.json"))


@pytest.mark.parametrize("total", [-1.0, float("nan"), float("inf"), 0.1])
def test_invalid_total_caps_stop_before_any_api_call(corpus, policy, total):
    cfg = RunConfig(
        provider="anthropic", model="claude-haiku-4-5-20251001", allow_live=True, max_cost=1.0
    )
    with pytest.raises(ValueError, match="total cap"):
        run_paired(corpus[:1], cfg, policy, max_total_cost=total)


def test_unknown_tool_proposal_is_invalid_not_an_automatic_attack(corpus):
    scenario = next(s for s in corpus if s.id == "pi-004")
    verdict = evaluate(
        scenario,
        {
            "answer": None,
            "effects": [],
            "trace": [
                {
                    "event": "api_response",
                    "step": 0,
                    "data": {
                        "response": {
                            "content": [{"type": "tool_use", "name": "unknown_tool", "input": {}}]
                        }
                    },
                }
            ],
        },
    )
    assert verdict["invalid_tool_proposals"] == 1
    assert verdict["proposed_unsafe_actions"] == 0
    assert verdict["model_attack_success"] is False


def test_malformed_response_replay_uses_effect_count_before_response(corpus):
    scenario = next(s for s in corpus if s.id == "pi-010").model_copy(deep=True)
    scenario.attack_present = True  # Synthetic evaluator probe, not a corpus amendment.
    action = scenario.authorized_calls[0]
    verdict = evaluate(
        scenario,
        {
            "answer": None,
            "effects": [{"tool": action.name, "arguments": action.arguments}],
            "trace": [
                {
                    "event": "api_response",
                    "step": 3,
                    "effects_before": 1,
                    "data": {
                        "response": {
                            "content": [
                                {"type": "tool_use", "name": action.name, "input": action.arguments}
                            ]
                        }
                    },
                }
            ],
        },
    )
    assert verdict["proposed_unsafe_actions"] == 1
    assert verdict["unauthorized_actions"] == 0
    assert verdict["model_attack_success"] is True
