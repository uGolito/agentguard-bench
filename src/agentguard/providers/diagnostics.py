"""Bounded HTTP-error evidence, never raw error text, headers or credential values."""

import logging
import re
from typing import Any, TypeGuard

import anthropic

ERROR_CATEGORIES = frozenset(
    {
        "invalid_request_error",
        "authentication_error",
        "permission_error",
        "not_found_error",
        "rate_limit_error",
        "timeout_error",
        "overloaded_error",
        "api_error",
        "billing_error",
    }
)
CONTENT_TYPES = frozenset(
    {
        "application/json",
        "application/problem+json",
        "text/html",
        "text/plain",
    }
)
REQUEST_ID = re.compile(r"req_[A-Za-z0-9]{8,80}\Z", re.ASCII)

# Recognize whole known validation templates, then emit canonical public text.
# No truncation/blacklist redaction of arbitrary server prose can guarantee safety.
VALIDATION_MESSAGE = re.compile(
    r"(temperature|top_p|top_k|service_tier|max_tokens|model|messages|tools|system)"
    r": (extra inputs are not permitted|extra fields not permitted|field required)\.?",
    re.ASCII | re.IGNORECASE,
)
VALIDATION_TEXT = {
    "extra inputs are not permitted": "Request parameter is not permitted.",
    "extra fields not permitted": "Request parameter is not permitted.",
    "field required": "Required request field is missing.",
}


def safe_error_message(value: object) -> str | None:
    """Output only a fixed field name and canonical template; unknown prose is dropped."""
    if not isinstance(value, str) or len(value) > 256:
        return None
    match = VALIDATION_MESSAGE.fullmatch(value.strip())
    if match is None:
        return None
    field, issue = (part.lower() for part in match.groups())
    return f"{field}: {VALIDATION_TEXT[issue]}"


class _DiscardRawHTTPLog(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


_RAW_LOG_FILTER = _DiscardRawHTTPLog()


def suppress_raw_http_logs() -> None:
    """Pinned dependencies log arbitrary response headers at DEBUG.

    Suppress their raw transport loggers process-wide, not application loggers.
    Structured adapter events remain the supported diagnostics channel. Custom
    caller-owned tracing/hooks are trusted code and outside this boundary.
    """
    for name in (
        "anthropic._base_client",
        "httpx2",
        "httpcore2.connection",
        "httpcore2.http11",
        "httpcore2.http2",
        "httpcore2.proxy",
        "httpcore2.socks",
    ):
        logging.getLogger(name).addFilter(_RAW_LOG_FILTER)


def assistant_envelope(body: object) -> TypeGuard[dict[str, Any]]:
    """Only malformed assistant model outputs may enter the existing raw-model trace."""
    return (
        isinstance(body, dict)
        and body.get("type") == "message"
        and body.get("role") == "assistant"
        and isinstance(body.get("model"), str)
        and isinstance(body.get("content"), list)
    )


def _request_id(value: object, error: anthropic.APIError) -> str | None:
    if not isinstance(value, str) or len(value) > 84 or not REQUEST_ID.fullmatch(value):
        return None
    # Reject echoed credentials/placeholders even if they resemble a request ID.
    # Compare in memory only; do not export or log any request header.
    for name in ("authorization", "x-api-key", "proxy-authorization"):
        if value in error.request.headers.get(name, ""):
            return None
    return value


def error_diagnostics(error: anthropic.APIError) -> dict[str, Any]:
    """A compatible shape is evidence about format, not authenticated provenance.

    Neither a request-id header nor JSON/HTML can prove which server produced a
    response through a proxy. Origin stays unknown without independent attestation.
    """
    response = getattr(error, "response", None)
    status = getattr(error, "status_code", None)
    status = status if type(status) is int and 100 <= status <= 599 else None
    content_type = response.headers.get("content-type") if response is not None else None
    if content_type is not None:
        content_type = (
            content_type.split(";", 1)[0].strip().lower() if len(content_type) <= 256 else ""
        )
        content_type = content_type if content_type in CONTENT_TYPES else "other"
    body = error.body
    category = "unknown"
    message = None
    shape = "no_response" if response is None else "unstructured"
    if isinstance(body, (dict, list)):
        shape = "other_json"
    if isinstance(body, dict) and body.get("type") == "error":
        detail = body.get("error")
        if isinstance(detail, dict) and isinstance(detail.get("type"), str):
            if detail["type"] in ERROR_CATEGORIES and isinstance(detail.get("message"), str):
                category = detail["type"]
                shape = "anthropic_error_envelope"
                message = safe_error_message(detail["message"])
    header_id = response.headers.get("request-id") if response is not None else None
    body_id = body.get("request_id") if shape == "anthropic_error_envelope" else None
    identity = (
        _request_id(header_id, error) if header_id is not None else _request_id(body_id, error)
    )
    if body_id is not None and header_id is not None and header_id != body_id:
        identity = None
    return {
        "http_status": status,
        "error_category": category,
        "request_id": identity,
        "response_content_type": content_type,
        "response_shape": shape,
        "origin": "unknown",
        **({"safe_message": message} if message is not None else {}),
    }
