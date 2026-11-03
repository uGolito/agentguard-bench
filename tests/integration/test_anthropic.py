"""Official SDK wire-level tests. MockTransport never leaves the process."""

import json
from pathlib import Path

import anthropic
import httpx2
import pytest
from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.config import RunConfig
from agentguard.providers.anthropic import AnthropicProvider, create_client
from agentguard.providers.budget import MODEL, Budget
from agentguard.reporting import markdown, write_run
from agentguard.runner import load_scenarios, run


def live_config(**changes):
    return RunConfig(
        **{
            "provider": "anthropic",
            "model": MODEL,
            "allow_live": True,
            "max_cost": 5.0,
            "retry_delay_seconds": 0.0,
            **changes,
        }
    )


def message(content, stop="end_turn", **changes):
    return {
        "id": "msg_synthetic",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "content": content,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 20},
        **changes,
    }


def answer_content():
    return [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "claims": [{"value": "EUR 120000", "source_ids": ["report"], "verified": True}],
                    "uncertainty": False,
                    "refused": False,
                }
            ),
        }
    ]


def tool_content(name="fetch_report", key="report", identity="tool_synthetic"):
    return {"type": "tool_use", "id": identity, "name": name, "input": {"key": key}}


@pytest.fixture
def sdk_factory():
    clients = []

    def make(replies):
        requests = []
        sequence = iter(replies)

        def handler(request):
            requests.append(request)
            reply = next(sequence)
            if isinstance(reply, Exception):
                raise reply
            if isinstance(reply, tuple):
                status, body, headers = reply
                return httpx2.Response(status, json=body, headers=headers)
            return httpx2.Response(200, json=reply, headers={"request-id": "req_synthetic"})

        client = anthropic.Anthropic(
            api_key="offline-test",
            max_retries=0,
            _strict_response_validation=True,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler), trust_env=False),
        )
        clients.append(client)
        return client, requests

    yield make
    for client in clients:
        client.close()


def scenarios():
    return load_scenarios(Path("scenarios"), "prompt_injection")


def test_real_sdk_multistep_wire_format(sdk_factory, tmp_path):
    client, requests = sdk_factory(
        [
            message(
                [tool_content(), tool_content("retrieve_metadata", identity="tool_meta")],
                "tool_use",
            ),
            message(answer_content()),
        ]
    )
    result = run(scenarios(), live_config(), client=client)
    row = result["results"][0]
    assert row["execution"]["status"] == "completed"
    assert row["evaluation"]["task_completed"]
    assert row["execution"]["tokens"]["input_tokens"] == 200
    assert row["execution"]["tokens"]["output_tokens"] == 40
    assert row["execution"]["estimated_cost_usd"] == pytest.approx(0.0004)
    assert result["budget"]["conservative_charge_usd"] == pytest.approx(0.0004)
    assert result["budget"]["unknown_billing_attempts"] == 0
    first = json.loads(requests[0].content)
    second = json.loads(requests[1].content)
    assert first["model"] == MODEL
    assert first["max_tokens"] == 512
    assert len(first["tools"]) == 6
    assert "Available local fixture keys" in first["messages"][0]["content"]
    assert "fake_script" not in json.dumps(first)
    assert "evaluation_criteria" not in json.dumps(first)
    assert second["messages"][-2]["role"] == "assistant"
    results = second["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["tool_synthetic", "tool_meta"]
    assert "SYNTHETIC-CANARY-471" in results[0]["content"]
    assert all(r["type"] == "tool_result" for r in results)
    assert requests[0].extensions["timeout"]["read"] == 30.0
    output = tmp_path / "wire"
    write_run(result, output)
    trace = [json.loads(line) for line in (output / "traces.jsonl").read_text().splitlines()]
    assert len([e for e in trace if e["event"] == "api_response"]) == 2
    assert any(e.get("tool_use_id") == "tool_meta" for e in trace)
    assert "offline-test" not in (output / "run.json").read_text()
    assert "not evidence of live" in markdown(result)


@pytest.mark.parametrize("kind", ["timeout", "rate_limit", "server_error"])
def test_retry_attempts_are_counted_and_unknown_charges_retained(sdk_factory, kind):
    if kind == "timeout":
        failure = httpx2.ReadTimeout("synthetic timeout")
    else:
        failure = (
            429 if kind == "rate_limit" else 503,
            {"type": "error", "error": {"type": "overloaded_error", "message": "test"}},
            {"retry-after": "0"},
        )
    client, requests = sdk_factory([failure, message(answer_content())])
    config = live_config(max_retries=1)
    result = run(scenarios(), config, client=client)
    assert len(requests) == 2
    assert result["results"][0]["execution"]["requests"] == 2
    assert result["budget"]["unknown_billing_attempts"] == 1
    assert result["budget"]["conservative_charge_usd"] == pytest.approx(
        float(Budget(config).reservation) + 0.0002
    )


def test_global_request_cap_includes_retries(sdk_factory):
    failure = httpx2.ReadTimeout("test")
    client, requests = sdk_factory([failure])
    result = run(scenarios(), live_config(max_requests=1, max_retries=3, trials=2), client=client)
    assert len(requests) == 1
    assert all(row["execution"]["status"] == "request_limit" for row in result["results"])
    assert result["budget"]["requests"] == 1


def test_cost_cap_prevents_retry(sdk_factory):
    client, requests = sdk_factory([httpx2.ReadTimeout("test")])
    config = live_config(max_cost=0.6, max_retries=1)
    result = run(scenarios(), config, client=client)
    assert len(requests) == 1
    assert result["results"][0]["execution"]["status"] == "cost_limit"
    assert result["budget"]["conservative_charge_usd"] <= config.max_cost


def test_no_request_if_reservation_exceeds_cap(sdk_factory):
    client, requests = sdk_factory([])
    result = run(scenarios(), live_config(max_cost=0.01), client=client)
    assert not requests
    assert result["results"][0]["execution"]["status"] == "cost_limit"


@pytest.mark.parametrize(
    ("content", "stop", "status"),
    [
        ([tool_content("unknown_tool")], "tool_use", "invalid_response"),
        ([tool_content(), tool_content()], "tool_use", "invalid_response"),
        ([tool_content()], "max_tokens", "output_limit"),
        ([{"type": "text", "text": "SYNTHETIC-CANARY-471"}], "end_turn", "invalid_response"),
        ([], "pause_turn", "unsupported_stop_reason"),
        ([tool_content()], "end_turn", "unsupported_stop_reason"),
    ],
)
def test_invalid_responses_preserve_raw_and_never_execute(sdk_factory, content, stop, status):
    client, requests = sdk_factory([message(content, stop)])
    result = run(scenarios(), live_config(), client=client)
    row = result["results"][0]
    assert len(requests) == 1
    assert row["execution"]["status"] == status
    assert not row["execution"]["effects"]
    assert any(e["event"] == "api_response" for e in row["execution"]["trace"])
    if content and content[0].get("text") == "SYNTHETIC-CANARY-471":
        assert row["evaluation"]["attack_success"] is True


def test_validation_error_returned_to_claude(sdk_factory):
    bad_call = tool_content()
    bad_call["input"] = {"unexpected": "value"}
    client, requests = sdk_factory([message([bad_call], "tool_use"), message(answer_content())])
    result = run(scenarios(), live_config(), client=client)
    assert result["results"][0]["execution"]["status"] == "completed"
    tool_result = json.loads(requests[1].content)["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert json.loads(tool_result["content"])["error"] == "ValidationError"


def test_refusal_is_measured(sdk_factory):
    client, _ = sdk_factory([message([], "refusal")])
    result = run(scenarios(), live_config(), client=client)
    assert result["results"][0]["evaluation"]["false_refusal"] is True


def test_permanent_error_is_not_retried_or_logged_with_body(sdk_factory):
    client, requests = sdk_factory(
        [
            (
                401,
                {
                    "type": "error",
                    "error": {"type": "authentication_error", "message": "SENSITIVE-ERROR-BODY"},
                },
                {},
            )
        ]
    )
    result = run(scenarios(), live_config(max_retries=3), client=client)
    assert len(requests) == 1
    assert result["results"][0]["execution"]["status"] == "provider_error"
    assert "SENSITIVE-ERROR-BODY" not in json.dumps(result)
    assert result["budget"]["unknown_billing_attempts"] == 1


def test_sdk_retry_default_is_overridden(sdk_factory):
    client, requests = sdk_factory([httpx2.ReadTimeout("test")])
    # Even an injected SDK client configured for retries cannot hide requests.
    result = run(scenarios(), live_config(), client=client.with_options(max_retries=3))
    assert len(requests) == 1
    assert result["results"][0]["execution"]["status"] == "timeout"


@pytest.mark.parametrize("advice", ["600", "Wed, 01 Jan 2030 00:00:00 GMT"])
def test_long_retry_after_stops_instead_of_unbounded_wait(sdk_factory, advice):
    client, requests = sdk_factory(
        [
            (
                429,
                {"type": "error", "error": {"type": "rate_limit_error", "message": "test"}},
                {"retry-after": advice},
            )
        ]
    )
    result = run(scenarios(), live_config(max_retries=1), client=client)
    assert len(requests) == 1
    assert result["results"][0]["execution"]["status"] == "retry_after_limit"


def test_model_mismatch_halts_following_episodes(sdk_factory):
    client, requests = sdk_factory([message(answer_content(), model="unexpected-model")])
    result = run(scenarios(), live_config(trials=2), client=client)
    assert len(requests) == 1
    assert result["results"][0]["execution"]["status"] == "model_mismatch"
    assert result["results"][1]["execution"]["status"] == "accounting_halted"


def test_cli_live_requires_opt_in_and_dry_run_needs_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    args = [
        "run",
        "--provider",
        "anthropic",
        "--model",
        MODEL,
        "--max-cost",
        "1",
        "--output",
        str(tmp_path / "unused"),
    ]
    runner = CliRunner()
    assert runner.invoke(app, args).exit_code != 0
    dry = runner.invoke(app, [*args, "--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "NO API CALLS" in dry.output
    assert not (tmp_path / "unused").exists()


def test_live_client_refuses_ci_and_missing_key(monkeypatch):
    config = live_config()
    monkeypatch.setenv("CI", "true")
    with pytest.raises(ValueError, match="disabled in CI"):
        create_client(config)
    monkeypatch.delenv("CI")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="not set"):
        create_client(config)
    with pytest.raises(ValueError, match="opt-in"):
        create_client(RunConfig())


def test_provider_rejects_fake_config(sdk_factory):
    client, _ = sdk_factory([])
    with pytest.raises(ValueError, match="provider=anthropic"):
        AnthropicProvider(RunConfig(), Budget(RunConfig()), client)


def test_malformed_sdk_response_preserves_raw_disclosure(sdk_factory):
    malformed = message(
        [{"type": "text", "text": "SYNTHETIC-CANARY-471"}], usage={"input_tokens": 100}
    )
    client, requests = sdk_factory([malformed])
    result = run(scenarios(), live_config(trials=2), client=client)
    assert len(requests) == 1
    row = result["results"][0]
    assert row["execution"]["status"] == "invalid_response"
    assert row["evaluation"]["attack_success"] is True
    assert row["execution"]["token_usage_complete"] is False
    assert result["budget"]["unknown_billing_attempts"] == 1
    assert result["results"][1]["execution"]["status"] == "accounting_halted"


def test_default_client_settings_and_owned_client_closed(monkeypatch, sdk_factory):
    client, requests = sdk_factory([message(answer_content())])
    constructor_calls = []

    def constructor(**kwargs):
        constructor_calls.append(kwargs)
        # Never use this real HTTP transport; only inspect and close it.
        kwargs["http_client"].close()
        return client

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://untrusted.example.invalid")
    monkeypatch.setattr("agentguard.providers.anthropic.anthropic.Anthropic", constructor)
    result = run(scenarios(), live_config())
    assert len(requests) == 1
    assert constructor_calls[0]["base_url"] == "https://api.anthropic.com"
    assert constructor_calls[0]["max_retries"] == 0
    assert constructor_calls[0]["_strict_response_validation"] is True
    assert client.is_closed()
    assert result["provider_metadata"]["client_injected"] is False
    assert "Anthropic API execution" in markdown(result)


def test_existing_artifacts_rejected_before_provider_creation(monkeypatch, tmp_path):
    def unexpected(*args, **kwargs):
        pytest.fail("Provider should not be constructed for an existing output directory")

    monkeypatch.setattr("agentguard.cli.run_benchmark", unexpected)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--provider",
            "anthropic",
            "--model",
            MODEL,
            "--allow-live",
            "--max-cost",
            "1",
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0


def test_model_mismatch_never_refunds_using_the_requested_model_price(sdk_factory):
    client, _ = sdk_factory([message(answer_content(), model="different-priced-model")])
    config = live_config()
    result = run(scenarios(), config, client=client)
    assert result["budget"]["conservative_charge_usd"] == float(Budget(config).reservation)
    assert result["budget"]["estimated_cost_usd"] == 0
    assert result["budget"]["pending_attempts"] == 0
    assert result["budget"]["unknown_billing_attempts"] == 1


def test_unexpected_sdk_exception_retains_reservation(monkeypatch, sdk_factory):
    def unexpected(*args, **kwargs):
        raise RuntimeError("PRIVATE-EXCEPTION-CONTENT")

    monkeypatch.setattr(anthropic.resources.messages.Messages, "create", unexpected)
    client, _ = sdk_factory([])
    result = run(scenarios(), live_config(trials=2), client=client)
    assert result["results"][0]["execution"]["status"] == "provider_exception"
    assert result["results"][1]["execution"]["status"] == "accounting_halted"
    assert result["budget"]["pending_attempts"] == 0
    assert result["budget"]["unknown_billing_attempts"] == 1
    assert "PRIVATE-EXCEPTION-CONTENT" not in json.dumps(result)


def test_known_usage_refunds_even_when_final_answer_is_invalid(sdk_factory):
    client, _ = sdk_factory([message([{"type": "text", "text": "invalid answer"}])])
    result = run(scenarios(), live_config(), client=client)
    assert result["results"][0]["execution"]["status"] == "invalid_response"
    assert result["budget"]["conservative_charge_usd"] == pytest.approx(0.0002)
    assert result["budget"]["unknown_billing_attempts"] == 0


def test_distinct_providers_share_thread_safe_budget_without_global_delta_errors(sdk_factory):
    from concurrent.futures import ThreadPoolExecutor

    from agentguard.agents import SYSTEM
    from agentguard.tools import TOOL_DEFINITIONS

    client, requests = sdk_factory([message(answer_content()), message(answer_content())])
    config = live_config()
    ledger = Budget(config)
    providers = [AnthropicProvider(config, ledger, client) for _ in range(2)]
    messages = [
        {"role": "system", "content": SYSTEM, "tools": TOOL_DEFINITIONS},
        {"role": "user", "content": "Synthetic task"},
    ]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda provider: provider.next_turn(messages), providers))
    assert len(requests) == 2
    assert float(ledger.reported_cost) == pytest.approx(0.0004)
    for provider in providers:
        assert provider.estimated_cost_usd == pytest.approx(0.0002)
        assert provider.budget_charge_usd == pytest.approx(0.0002)


def test_guarded_runtime_returns_validated_untrusted_data_to_sdk(sdk_factory):
    from agentguard.guards.policy import Policy

    client, requests = sdk_factory(
        [message([tool_content()], "tool_use"), message(answer_content())]
    )
    result = run(scenarios(), live_config(mode="guarded"), client=client, policy=Policy())
    assert result["results"][0]["evaluation"]["task_completed"]
    output = json.loads(json.loads(requests[1].content)["messages"][-1]["content"][0]["content"])
    assert output["trust"] == "untrusted"
    assert output["fixture_key"] == "report"
    assert output["data"]["source_id"] == "report-a"
