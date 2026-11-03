import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.config import RunConfig
from agentguard.guards import Controls
from agentguard.guards.evidence import EvidenceStore
from agentguard.guards.oversight import FakeReviewer, ReviewDecision, ReviewRequest, review_action
from agentguard.guards.policy import Policy
from agentguard.reporting import compare_runs
from agentguard.runner import load_scenarios, run
from agentguard.schemas import Answer, Claim, ToolCall


def test_cli_all_modes_share_identical_scenarios_and_controls(tmp_path):
    runner = CliRunner()
    paths = []
    for mode in ("baseline", "guarded", "guarded_oversight"):
        output = tmp_path / mode
        args = [
            "run",
            "--scenarios",
            "tests/fixtures/milestone3",
            "--mode",
            mode,
            "--provider",
            "fake",
            "--policy",
            "examples/policy.json",
            "--output",
            str(output),
        ]
        if mode == "guarded_oversight":
            args.extend(["--reviewer", "fake-allow"])
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
        paths.append(output / "run.json")
        run_data = json.loads(paths[-1].read_text())
        assert all(r["evaluation"]["task_completed"] for r in run_data["results"])
        assert run_data["config"]["mode"] == mode
        if mode != "baseline":
            events = [e for row in run_data["results"] for e in row["execution"]["trace"]]
            assert any(e["event"] == "evidence_decision" for e in events)
    for candidate in paths[1:]:
        comparison = runner.invoke(
            app, ["compare", "--baseline", str(paths[0]), "--candidate", str(candidate)]
        )
        assert comparison.exit_code == 0, comparison.output
        data = json.loads(comparison.output)
        assert len(data["paired_outcomes"]) == 3
        assert len(data["per_category"]) == 3
        assert "not live model findings" in data["notice"]


@pytest.mark.parametrize(
    "args",
    [
        ["run", "--mode", "guarded_oversight", "--policy", "examples/policy.json"],
        ["run", "--reviewer", "fake-allow"],
        ["run", "--mode", "guarded", "--policy", "missing-policy.json"],
    ],
)
def test_cli_ambiguous_or_missing_configuration_is_actionable(args):
    result = CliRunner().invoke(app, args)
    assert result.exit_code != 0
    assert "Error" in result.output


def test_cli_policy_errors_do_not_echo_protected_values(tmp_path):
    path = tmp_path / "invalid-policy.json"
    path.write_text(
        json.dumps(
            {"version": "1.0.0", "grants": [], "protected_literals": ["PRIVATE-POLICY-CONTENT", ""]}
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["run", "--mode", "guarded", "--policy", str(path)])
    assert result.exit_code != 0
    assert "Schema validation failed" in result.output
    assert "PRIVATE-POLICY-CONTENT" not in result.output


@pytest.mark.parametrize(
    "change", ["policy", "hash", "trials", "duplicates", "transport", "sdk", "package"]
)
def test_compare_rejects_uncontrolled_inputs(change):
    source = run(load_scenarios(Path("tests/fixtures/milestone3")), RunConfig())
    candidate = json.loads(json.dumps(source))
    if change == "policy":
        candidate["policy_sha256"] = "different-policy"
    if change == "hash":
        candidate["results"][0]["scenario_sha256"] = "different-fixture"
    if change == "trials":
        candidate["results"].pop()
    if change == "duplicates":
        candidate["results"].append(candidate["results"][0])
    if change == "transport":
        candidate["provider_metadata"]["client_injected"] = True
    if change == "sdk":
        candidate["provider_metadata"]["sdk_version"] = "different-sdk"
    if change == "package":
        candidate["package_version"] = "different-package"
    with pytest.raises(ValueError):
        compare_runs(source, candidate)


def test_cli_compare_reports_control_mismatch(tmp_path):
    a = run(load_scenarios(Path("tests/fixtures/milestone3")), RunConfig())
    b = json.loads(json.dumps(a))
    b["config"]["max_steps"] += 1
    for name, data in [("a.json", a), ("b.json", b)]:
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
    result = CliRunner().invoke(
        app,
        [
            "compare",
            "--baseline",
            str(tmp_path / "a.json"),
            "--candidate",
            str(tmp_path / "b.json"),
        ],
    )
    assert result.exit_code != 0
    assert "Incompatible comparison" in result.output


def test_protected_arguments_and_false_confirmations_are_rejected():
    controls = Controls(
        Policy(protected_literals=["SYNTHETIC-CANARY-471"]),
        "pi-001",
        "Synthetic task",
        False,
        None,
        1.0,
    )
    allowed, reason, _ = controls.before(
        ToolCall(
            name="update_record",
            arguments={"record_id": "synthetic", "value": "SYNTHETIC-CANARY-471"},
        )
    )
    assert not allowed and reason == "protected_literal"
    with pytest.raises(ValueError):
        controls.after(
            ToolCall(
                name="update_record", arguments={"record_id": "synthetic", "value": "example"}
            ),
            {"status": "simulated", "effect_index": 99},
            1,
        )


@pytest.mark.parametrize(
    "observation",
    [
        [{"source_id": "a", "value": 42, "unit": "items", "timestamp": "2026-01-01"}],
        [{"source_id": "a", "value": 42, "unit": "items", "timestamp": None}],
        [
            {"source_id": "a", "value": 42, "unit": "kg", "timestamp": "2026-01-01"},
            {"source_id": "b", "value": 42, "unit": "lb", "timestamp": "2026-01-01"},
        ],
    ],
)
def test_numeric_support_and_uncertainty(observation):
    store = EvidenceStore()
    store.accept("source", observation)
    answer, _ = store.verify(
        Answer(claims=[Claim(value="42 items", source_ids=["source"], verified=True)])
    )
    confident = len(observation) == 1 and observation[0]["timestamp"] is not None
    assert answer.claims[0].verified == confident
    assert answer.uncertainty != confident


def test_no_literal_support_is_downgraded():
    store = EvidenceStore()
    store.accept("source", {"source_id": "a", "body": "A different fact"})
    answer, decisions = store.verify(
        Answer(claims=[Claim(value="Invented fact", source_ids=["source"], verified=True)])
    )
    assert answer.uncertainty
    assert not answer.claims[0].verified
    assert decisions[0]["reason"] == "no_literal_support"


def test_reviewer_cancellation_and_mutated_decision_fail_closed():
    import asyncio

    class CancelReviewer(FakeReviewer):
        async def review(self, request):
            raise asyncio.CancelledError()

    class MutatedReviewer(FakeReviewer):
        async def review(self, request):
            result = ReviewDecision(allowed=True, reason="synthetic")
            result.allowed = "yes"
            return result

    request = ReviewRequest(
        scenario_id="pi-001", objective="Synthetic", action_json="{}", grant_id="x"
    )
    assert review_action(CancelReviewer(), request, 1.0)["reason"] == "reviewer_cancelled"
    assert review_action(MutatedReviewer(), request, 1.0)["reason"] == "reviewer_error"


def test_nested_event_loop_fails_closed_without_unawaited_coroutine():
    import asyncio

    async def nested():
        request = ReviewRequest(
            scenario_id="pi-001", objective="Synthetic", action_json="{}", grant_id="x"
        )
        return review_action(FakeReviewer(), request, 1.0)

    record = asyncio.run(nested())
    assert not record["allowed"]
    assert record["reason"] == "reviewer_context_error"


def test_late_reviewer_approval_is_rejected_after_cancellation():
    import asyncio

    class LateReviewer(FakeReviewer):
        async def review(self, request):
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                await asyncio.sleep(0.01)
                return ReviewDecision(allowed=True, reason="too late")

    request = ReviewRequest(
        scenario_id="pi-001", objective="Synthetic", action_json="{}", grant_id="x"
    )
    record = review_action(LateReviewer(), request, 0.01)
    assert not record["allowed"]
    assert record["reason"] == "reviewer_timeout"
