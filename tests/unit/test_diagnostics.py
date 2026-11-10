import logging

import anthropic
import httpx2
import pytest

from agentguard.providers.diagnostics import (
    error_diagnostics,
    safe_error_message,
    suppress_raw_http_logs,
)

GOOD = "req_0123456789AbCdEfabcdef"


def error(body=None, headers=None, auth="Bearer dummy-placeholder"):
    request = httpx2.Request(
        "POST", "https://api.anthropic.com/v1/messages", headers={"Authorization": auth}
    )
    response = httpx2.Response(400, request=request, headers=headers or {})
    return anthropic.BadRequestError(
        "Never persist this exception message", response=response, body=body
    )


@pytest.mark.parametrize(
    "identity",
    [
        "",
        "req_short",
        "req_" + "x" * 81,
        "req_12345678_secret",
        "secret-placeholder",
        "req_12345678,req_abcdefgh",
    ],
)
def test_unvalidated_request_ids_are_dropped(identity):
    assert error_diagnostics(error(headers={"request-id": identity}))["request_id"] is None


def test_request_id_body_fallback_conflicts_and_credential_echo():
    body = {
        "type": "error",
        "error": {"type": "invalid_request_error", "message": "private"},
        "request_id": GOOD,
    }
    assert error_diagnostics(error(body))["request_id"] == GOOD
    assert (
        error_diagnostics(error(body, {"request-id": "req_different12345678"}))["request_id"]
        is None
    )
    assert error_diagnostics(error(body, auth="Bearer " + GOOD))["request_id"] is None


@pytest.mark.parametrize(
    "content_type,expected",
    [
        ("application/json; token=PRIVATE", "application/json"),
        ("application/problem+json", "application/problem+json"),
        ("text/plain", "text/plain"),
        ("application/private-credential", "other"),
        ("x" * 257, "other"),
        (None, None),
    ],
)
def test_only_normalized_allowlisted_content_types_are_retained(content_type, expected):
    headers = {"content-type": content_type} if content_type else {}
    diagnostic = error_diagnostics(error(headers=headers))
    assert diagnostic["response_content_type"] == expected
    assert diagnostic["origin"] == "unknown"


def test_timeout_does_not_invent_http_evidence():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    result = error_diagnostics(anthropic.APITimeoutError(request))
    assert result["http_status"] is None and result["request_id"] is None
    assert result["response_shape"] == "no_response" and result["origin"] == "unknown"


def test_raw_dependency_logs_suppressed_but_application_logs_remain(caplog):
    suppress_raw_http_logs()
    suppress_raw_http_logs()
    caplog.set_level(logging.DEBUG)
    for name in ("anthropic._base_client", "httpx2", "httpcore2.http11", "httpcore2.proxy"):
        logging.getLogger(name).error("PRIVATE_RAW_HTTP_HEADER")
    logging.getLogger("agentguard").info("Safe application event")
    assert "PRIVATE_RAW_HTTP_HEADER" not in caplog.text
    assert "Safe application event" in caplog.text


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "temperature: Extra inputs are not permitted",
            "temperature: Request parameter is not permitted.",
        ),
        ("TOP_P: extra fields not permitted.", "top_p: Request parameter is not permitted."),
        ("messages: Field required", "messages: Required request field is missing."),
        ("temperature: Extra inputs are not permitted; secret=PRIVATE", None),
        ("temperature: Extra inputs are not permitted\nPRIVATE", None),
        ("api_key: Extra inputs are not permitted", None),
        ("model: PRIVATE", None),
        ("PRIVATE " * 100, None),
        (None, None),
    ],
)
def test_error_message_is_whole_template_recognition_not_free_text_redaction(message, expected):
    assert safe_error_message(message) == expected


def test_known_error_message_is_canonical_and_others_are_not_persisted():
    body = {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "temperature: Extra inputs are not permitted",
        },
    }
    assert error_diagnostics(error(body))["safe_message"] == (
        "temperature: Request parameter is not permitted."
    )
    body["error"]["message"] += " PRIVATE"
    assert "safe_message" not in error_diagnostics(error(body))
