import copy

import pytest

from agentguard.reporting.statistics import intervals


def analytic_fixture():
    # Mathematical test inputs only; never a published model evaluation.
    return {
        "provider_metadata": {"live": True, "client_injected": False},
        "results": [
            {
                "scenario_id": f"fixture-{i}",
                "trial": trial,
                "evaluation": {
                    "model_attack_success": i == 0,
                    "runtime_attack_success": i == 0,
                    "task_completed": i != 0,
                    "false_refusal": i == 0,
                },
            }
            for i in range(4)
            for trial in range(3)
        ],
    }


def test_cluster_intervals_are_reproducible_and_bounded():
    run = analytic_fixture()
    a = intervals(run, resamples=500, seed=42)
    b = intervals(run, resamples=500, seed=42)
    assert a == b and a["available"]
    for endpoint in a["endpoints"].values():
        low, high = endpoint["interval"]
        assert 0 <= low <= high <= 1
        assert endpoint["eligible_scenarios"] == 4


def test_paired_bootstrap_resamples_identical_clusters():
    a, b = analytic_fixture(), analytic_fixture()
    for row in b["results"]:
        row["evaluation"]["task_completed"] = True
    result = intervals(a, b, resamples=500)
    assert result["endpoints"]["task_completion"]["interval"][0] >= 0
    assert result["endpoints"]["model_attack_success"]["interval"] is None  # Degenerate difference.


def test_fake_injected_partial_and_tiny_corpora_do_not_receive_misleading_bounds():
    run = analytic_fixture()
    run["provider_metadata"]["client_injected"] = True
    assert not intervals(run)["available"]
    run["provider_metadata"]["client_injected"] = False
    run["experiment_complete"] = False
    assert not intervals(run)["available"]
    run.pop("experiment_complete")
    run["results"] = run["results"][:3]
    assert intervals(run)["endpoints"]["task_completion"]["interval"] is None


def test_mismatched_eligibility_and_trials_are_rejected():
    a, b = analytic_fixture(), analytic_fixture()
    b["results"][0]["evaluation"]["model_attack_success"] = None
    with pytest.raises(ValueError, match="eligibility"):
        intervals(a, b)
    b = copy.deepcopy(a)
    b["results"] = b["results"][:3]
    with pytest.raises(ValueError, match="clusters"):
        intervals(a, b)
    with pytest.raises(ValueError, match="100"):
        intervals(a, resamples=10)
