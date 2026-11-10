"""No sockets: proxy routing, TLS trust and SDK wire compatibility with dummy secrets."""

import asyncio
import json
import logging
import ssl
from pathlib import Path

import anthropic
import certifi
import httpcore2
import httpx2
import pytest
from typer.testing import CliRunner

from agentguard.cli import app
from agentguard.config import RunConfig
from agentguard.providers.anthropic import create_client
from agentguard.providers.budget import MODEL, Budget
from agentguard.providers.http import async_http_client, http_mode, sync_http_client
from agentguard.providers.reviewer import create_review_client
from agentguard.runner import run


@pytest.fixture(autouse=True)
def transport_environment(monkeypatch):
    for name in (
        "AGENTGUARD_HTTP_MODE",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "https_proxy",
        "http_proxy",
        "all_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def config(**changes):
    return RunConfig(
        **{
            "provider": "anthropic",
            "model": MODEL,
            "allow_live": True,
            "max_cost": 1,
            "max_requests": 1,
            "max_retries": 0,
            **changes,
        }
    )


def cloud(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_HTTP_MODE", "codex-cloud")
    monkeypatch.setenv("HTTPS_PROXY", "http://sidecar.example.invalid:8080")
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("ALL_PROXY", "http://unrelated.example.invalid:8888")


@pytest.mark.parametrize("async_client", [False, True])
def test_cloud_routes_through_explicit_proxy_even_with_no_proxy(monkeypatch, async_client):
    cloud(monkeypatch)
    client = async_http_client(7) if async_client else sync_http_client(7)
    try:
        transport = client._transport_for_url(httpx2.URL("https://api.anthropic.com/v1/messages"))
        pool = transport._pool
        assert isinstance(pool, httpcore2.AsyncHTTPProxy if async_client else httpcore2.HTTPProxy)
        assert pool._proxy_url.host == b"sidecar.example.invalid"
        assert not client.follow_redirects and client.timeout.connect == 7
        assert pool._ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert pool._ssl_context.check_hostname
    finally:
        asyncio.run(client.aclose()) if async_client else client.close()


@pytest.mark.parametrize("async_client", [False, True])
def test_default_does_not_trust_proxy_or_ca_environment(monkeypatch, async_client):
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted.example.invalid:8080")
    monkeypatch.setenv("SSL_CERT_FILE", "invalid-do-not-use")
    client = async_http_client(7) if async_client else sync_http_client(7)
    try:
        assert http_mode() == "direct"
        transport = client._transport_for_url(httpx2.URL("https://api.anthropic.com"))
        assert not isinstance(transport._pool, (httpcore2.HTTPProxy, httpcore2.AsyncHTTPProxy))
        assert transport._pool._ssl_context.verify_mode == ssl.CERT_REQUIRED
    finally:
        asyncio.run(client.aclose()) if async_client else client.close()


@pytest.mark.parametrize("name", ["SSL_CERT_FILE", "SSL_CERT_DIR"])
@pytest.mark.parametrize("async_client", [False, True])
def test_cloud_preserves_custom_ca_configuration(monkeypatch, tmp_path, name, async_client):
    cloud(monkeypatch)
    path = certifi.where() if name == "SSL_CERT_FILE" else str(tmp_path)
    original = ssl.create_default_context
    calls = []

    def observed(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setenv(name, path)
    monkeypatch.setattr(ssl, "create_default_context", observed)
    client = async_http_client(7) if async_client else sync_http_client(7)
    try:
        field = "cafile" if name == "SSL_CERT_FILE" else "capath"
        assert any(call.get(field) == path for call in calls)
        context = client._transport._pool._ssl_context
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    finally:
        asyncio.run(client.aclose()) if async_client else client.close()


@pytest.mark.parametrize(
    "value",
    [
        None,
        "socks5://proxy.invalid",
        "http://",
        "http://x:bad",
        "http://proxy.invalid/private?token=dummy",
    ],
)
def test_invalid_cloud_proxy_never_falls_back_or_echoes_value(monkeypatch, value):
    cloud(monkeypatch)
    if value is None:
        monkeypatch.delenv("HTTPS_PROXY")
    else:
        monkeypatch.setenv("HTTPS_PROXY", value)
    for build in (sync_http_client, async_http_client):
        with pytest.raises(ValueError) as error:
            build(7)
        assert value is None or value not in str(error.value)


@pytest.mark.parametrize("async_client", [False, True])
def test_invalid_custom_ca_is_sanitized_and_no_tls_bypass(monkeypatch, tmp_path, async_client):
    cloud(monkeypatch)
    path = str(tmp_path / "dummy-private-ca-path.pem")
    monkeypatch.setenv("SSL_CERT_FILE", path)
    with pytest.raises(ValueError, match="HTTP transport setup failed") as error:
        (async_http_client if async_client else sync_http_client)(7)
    assert path not in str(error.value)


def test_unknown_mode_is_explicit_error(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_HTTP_MODE", "dummy-private-value")
    with pytest.raises(ValueError, match="must be direct or codex-cloud") as error:
        sync_http_client(7)
    assert "dummy-private-value" not in str(error.value)


@pytest.mark.parametrize("async_client", [False, True])
def test_constructor_errors_cannot_leak_proxy_credentials(monkeypatch, async_client):
    cloud(monkeypatch)

    def broken(**kwargs):
        raise httpx2.InvalidURL("dummy-proxy-secret-in-upstream-exception")

    monkeypatch.setattr(httpx2, "AsyncClient" if async_client else "Client", broken)
    with pytest.raises(ValueError, match="HTTP transport setup failed") as error:
        (async_http_client if async_client else sync_http_client)(7)
    assert "dummy-proxy-secret" not in str(error.value)
    assert error.value.__suppress_context__


def test_both_sdk_factories_use_cloud_transport_and_preserve_placeholder(monkeypatch):
    cloud(monkeypatch)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-http-secret-placeholder")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://untrusted.example.invalid")
    primary = create_client(config())
    reviewer = create_review_client(config(mode="guarded_oversight", reviewer_provider="anthropic"))
    try:
        for client in (primary, reviewer):
            assert str(client.base_url) == "https://api.anthropic.com"
            assert client.max_retries == 0
            assert client.auth_headers == {"Authorization": "Bearer dummy-http-secret-placeholder"}
            pool = client._client._transport_for_url(httpx2.URL(str(client.base_url)))._pool
            assert isinstance(pool, (httpcore2.HTTPProxy, httpcore2.AsyncHTTPProxy))
    finally:
        primary.close()
        asyncio.run(reviewer.close())


def test_placeholder_wire_header_budget_and_no_log_or_trace_leak(monkeypatch, caplog, capsys):
    cloud(monkeypatch)
    dummy = "dummy-proxy-placeholder-not-a-credential"
    monkeypatch.setenv("ANTHROPIC_API_KEY", dummy)
    seen = []

    def handle(request):
        assert request.headers["Authorization"] == "Bearer " + dummy
        seen.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_offline",
                "type": "message",
                "role": "assistant",
                "model": MODEL,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "content": [
                    {"type": "text", "text": '{"claims":[],"uncertainty":true,"refused":false}'}
                ],
                "usage": {"input_tokens": 100, "output_tokens": 20},
            },
        )

    client = anthropic.Anthropic(
        api_key=dummy,
        max_retries=3,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle), trust_env=False),
    )
    from agentguard.runner import load_scenarios

    caplog.set_level(logging.DEBUG)
    ledger = Budget(config())
    try:
        result = run(load_scenarios(Path("scenarios"))[:1], config(), client=client, budget=ledger)
    finally:
        client.close()
    assert len(seen) == 1 and ledger.requests == 1 and not ledger.unknown_attempts
    assert result["budget"]["estimated_cost_usd"] == pytest.approx(0.0002)
    assert result["provider_metadata"]["http_mode"] == "injected"
    assert dummy not in json.dumps(result) + caplog.text + capsys.readouterr().out


def test_cloud_dry_run_does_not_construct_clients_or_require_proxy(monkeypatch):
    monkeypatch.setenv("AGENTGUARD_HTTP_MODE", "codex-cloud")
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--provider",
            "anthropic",
            "--model",
            MODEL,
            "--max-cost",
            "1",
            "--max-requests",
            "1",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0 and "NO API CALLS" in result.output


def test_ci_gate_remains_before_transport_creation(monkeypatch):
    cloud(monkeypatch)
    monkeypatch.setenv("CI", "true")
    for build, cfg in (
        (create_client, config()),
        (create_review_client, config(mode="guarded_oversight", reviewer_provider="anthropic")),
    ):
        with pytest.raises(ValueError, match="disabled in CI"):
            build(cfg)


@pytest.mark.parametrize("key", ["http_mode", "api_version"])
def test_comparison_rejects_hidden_transport_difference(key):
    from agentguard.reporting import compare_runs
    from agentguard.runner import load_scenarios

    original = run(load_scenarios(Path("tests/fixtures/milestone3")), RunConfig())
    candidate = json.loads(json.dumps(original))
    left, right = {
        "http_mode": ("direct", "codex-cloud"),
        "api_version": ("2023-06-01", "2026-10-21"),
    }[key]
    original["provider_metadata"][key] = left
    candidate["provider_metadata"][key] = right
    with pytest.raises(ValueError, match=f"{key} differs"):
        compare_runs(original, candidate)
