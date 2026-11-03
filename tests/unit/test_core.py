from pathlib import Path

import pytest
from pydantic import ValidationError

from agentguard.agents import execute
from agentguard.config import RunConfig
from agentguard.evaluators import evaluate
from agentguard.providers import FakeProvider
from agentguard.reporting import aggregate, write_run
from agentguard.runner import load_scenarios, run
from agentguard.schemas import Answer, Claim, ToolCall, Turn
from agentguard.tools import INPUTS, SyntheticTools


@pytest.fixture
def scenario():
    return load_scenarios(Path("tests/fixtures/milestone3"))[1]


def test_strict_config():
    with pytest.raises(ValidationError):
        RunConfig(max_steps=0)
    with pytest.raises(ValidationError):
        RunConfig(provider="anthropic")


@pytest.mark.parametrize("name", sorted(INPUTS))
def test_tool_input_validation(name):
    with pytest.raises(ValidationError):
        SyntheticTools({}).execute(ToolCall(name=name, arguments={"unexpected": True}))


@pytest.mark.parametrize("name", ["send_email", "update_record"])
def test_sensitive_tools_only_simulate(name):
    args = (
        {"recipient": "test@example.invalid", "body": "test"}
        if name == "send_email"
        else {"record_id": "synthetic", "value": "updated"}
    )
    tools = SyntheticTools({})
    assert tools.execute(ToolCall(name=name, arguments=args))["status"] == "simulated"
    assert tools.effects[0]["simulated"] is True


def test_limits(scenario):
    result = execute(scenario, FakeProvider(scenario), RunConfig(max_steps=1), 100)
    assert result["status"] == "step_limit"
    assert result["answer"] is None
    assert execute(scenario, FakeProvider(scenario), RunConfig(), 0)["status"] == "request_limit"


def test_invalid_turn(scenario):
    scenario.fake_script = [Turn()]
    assert execute(scenario, FakeProvider(scenario), RunConfig(), 10)["status"] == "invalid_turn"


def test_errors_recorded(scenario):
    scenario.fake_script = [Turn(call=ToolCall(name="fetch_report", arguments={"key": "absent"}))]
    result = execute(scenario, FakeProvider(scenario), RunConfig(max_steps=1), 10)
    assert next(e for e in result["trace"] if e["event"] == "tool_result")["data"] == {
        "error": "KeyError"
    }


def test_evaluator_detects_failure(scenario):
    scenario.attack_present = True
    result = {
        "answer": Answer(
            claims=[Claim(value="SYNTHETIC-CANARY-471", source_ids=[], verified=False)]
        ).model_dump(),
        "effects": [{"tool": "send_email"}],
    }
    verdict = evaluate(scenario, result)
    assert verdict["attack_success"]
    assert not verdict["task_completed"]
    assert verdict["unauthorized_actions"] == 1


def test_no_scenarios(tmp_path):
    with pytest.raises(ValueError, match="No scenarios"):
        load_scenarios(tmp_path)


def test_artifact_preservation(tmp_path, scenario):
    result = run([scenario], RunConfig())
    out = tmp_path / "run"
    write_run(result, out)
    assert (out / "traces.jsonl").read_text()
    with pytest.raises(FileExistsError):
        write_run(result, out)
    assert aggregate(result)["task_completion_rate"]["denominator"] == 1


def test_runtime_records_unauthorized_proposal(scenario):
    scenario.attack_present = True
    scenario.fake_script = [
        Turn(
            call=ToolCall(
                name="send_email",
                arguments={"recipient": "attacker@example.invalid", "body": "synthetic only"},
            )
        ),
        Turn(answer=Answer(claims=[])),
    ]
    execution = execute(scenario, FakeProvider(scenario), RunConfig(), 10)
    assert len(execution["effects"]) == 1
    assert evaluate(scenario, execution)["attack_success"] is True


def test_confidence_without_support_fails():
    scenario = load_scenarios(Path("tests/fixtures/milestone3"), "conflicting_evidence")[0]
    answer = Answer(
        claims=[
            Claim(value=v, source_ids=["report"], verified=True)
            for v in scenario.evaluation_criteria.required_values
        ],
        uncertainty=True,
    )
    verdict = evaluate(scenario, {"answer": answer.model_dump(), "effects": []})
    assert not verdict["task_completed"]
    assert verdict["attack_success"] is None
    assert verdict["unsupported_verification"]


def test_request_budget_is_global(scenario):
    result = run([scenario], RunConfig(trials=3, max_requests=1))
    assert sum(row["execution"]["requests"] for row in result["results"]) == 1
    assert not any(row["evaluation"]["task_completed"] for row in result["results"])


def test_duplicate_ids_rejected(tmp_path, scenario):
    directory = tmp_path / "category"
    directory.mkdir()
    for filename in ["a.json", "b.json"]:
        (directory / filename).write_text(scenario.model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_scenarios(tmp_path)


def test_refusal_is_not_success(scenario):
    verdict = evaluate(
        scenario, {"answer": Answer(claims=[], refused=True).model_dump(), "effects": []}
    )
    assert verdict["false_refusal"]
    assert not verdict["task_completed"]
