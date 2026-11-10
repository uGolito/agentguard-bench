# HTTP 400 investigation — version 0.4.3 history

This patch investigates an operator-reported single-request smoke failure. No Anthropic requests, authentication probes or paid calls were made during this investigation. The original response body is unavailable; it cannot be recovered from the previous sanitized trace. No live benchmark results are published here.

**Update 2026-11-10:** official API migration documentation confirms that the outgoing temperature parameter conflicts with API 2026-10-21. Version 0.4.4 pins the older API to preserve sampling. The observations below describe the earlier 0.4.3 investigation; its unresolved version hypothesis is superseded by the [compatibility correction](claude_compatibility_fix.md). The original server message remains unavailable and live success is still untested.

## Initial facts versus hypotheses (0.4.3)

The locked installed SDK is Anthropic 2.4.0. These facts are established from its local source/types and in-memory wire tests, not remote server acceptance:

- `_constants.ANTHROPIC_API_VERSION` is 2026-10-21; `_client.Anthropic.default_headers` emits that anthropic-version header. The adapter does not override it. No evidence supports a speculative downgrade.
- `_client.Anthropic._api_key_auth` emits a single Authorization: Bearer header. The adapter passes the configured API-key placeholder unchanged. Explicit api_key avoids credential autodiscovery. Wire tests confirm no duplicate Authorization, x-api-key or application-added Proxy-Authorization headers.
- `types/model.py` explicitly includes claude-haiku-4-5-20251001 and the adapter/pricing table pins that exact snapshot. Account/model availability remains separate from a local SDK literal.
- `types/message_create_params.py` permits service_tier=standard_only. It remains unchanged.
- The SDK no longer has a typed temperature argument. Its official extra_body mechanism merges temperature=0 into the outgoing JSON exactly once. This is an untyped escape hatch: the SDK's ability to serialize it does not prove that the selected model/API version accepts it. It is a hypothesis to investigate, not a confirmed incompatibility. Temperature was not removed or altered.
- The Messages call is POST /v1/messages with model, max_tokens, system, messages, service_tier and tools. ToolParam requires name/input_schema; description/type are optional. The six schemas are objects with explicit properties/required fields. Initial messages use role/content; tool results preserve tool_use_id and group results in a user message. Existing multi-step wire tests remain. These structural checks cannot certify server-side validation.

The cloud runtime documentation describes sidecar proxy credential injection with possible application placeholders. Current saved-configuration metadata exposes the environment identity/status/repository, but not the actual HTTP-secret header substitution rule. The operator confirms routing/TLS and the exact allowed domain api.anthropic.com. Neither that domain nor a ready binding establishes that the outgoing Bearer placeholder was replaced correctly. Local source confirms the SDK's header format; effective secret-injection compatibility remains unverified without the runtime's non-secret binding specification or an authorized service response. No alternate authentication header was added and no configuration was changed.

Remaining hypotheses include a credential-substitution mismatch, intermediary request rejection, or remote rejection of a request field/API-version/model combination. A 400 status alone does not distinguish them. The exception class BadRequestError is selected by the SDK from status 400 and does not prove Anthropic produced the response.

## Confirmed diagnostic defects corrected

The adapter previously discarded all useful HTTP-error evidence. It now records a nested diagnostics object on api_error/reviewer_api_error with only:

- HTTP status, validated as an integer HTTP status or null.
- Error category from the pinned SDK's fixed allowlist, or unknown. The error message is never retained.
- Request ID matching a bounded req_ + alphanumeric grammar, or null. Conflicting body/header IDs and IDs echoing sent credential placeholders are dropped. Syntax validation is not proof of origin.
- Content type normalized to application/json, application/problem+json, text/html, text/plain, other or null. Parameters and arbitrary header text are discarded.
- Response shape: documented error-envelope shape, other JSON, unstructured or no response.
- Origin: unknown. A JSON/HTML shape or request ID does not authenticate a producer through a proxy; no stronger attribution is made without independent attestation.

The same policy covers sync primary and async reviewer failures. No raw HTTP error body, arbitrary header, exception message, workspace identifier or credential is added to execution traces. Existing raw *model-output* tracing remains for malformed HTTP-200 assistant envelopes; non-model error envelopes returned as HTTP 200 are no longer misclassified and retained as raw model output.

Local SDK source also confirms DEBUG logs include entire response headers. The adapter therefore suppresses the pinned raw transport loggers (anthropic._base_client, httpx2 and the httpcore2 connection/http11/http2/proxy/socks loggers) process-wide. Application logs are unaffected; structured adapter events are the supported diagnostic channel. This is intentional suppression of dependency wire logging, not mutation of credentials or HTTP behavior. Caller-installed tracing/hooks and new loggers introduced by future dependency upgrades remain outside this boundary and require separate review. Do not enable custom raw wire capture around credentials.

## Controls preserved and verification

Endpoint, API version, model, temperature, service tier, message/tool definitions and authentication are unchanged. Cloud proxy/CA selection, verified TLS, redirects off, explicit live opt-in and CI prohibition remain. HTTP 400 is still permanent and never retried, even when max_retries is nonzero. Its reservation is retained as unknown billing; a 400 is not assumed free. Global request caps and single-settlement accounting remain unchanged.

Offline tests use only dummy credentials and in-memory transports, with application sockets/DNS blocked. They cover Anthropic-shaped JSON, proxy-shaped JSON/HTML, malicious category/content-type/request-ID fields, credential echoes, conflicting IDs, log/trace redaction, one attempt/no retry, retained reservations and fail-closed reviewer behavior. Wire tests pin the current SDK facts above. Existing frozen scenarios/hypotheses, dependency lock and public SIMULATED assets are unchanged. Only unit/integration validation is run; no new experimental evaluation is initiated.

## Initial recommendation (0.4.3; see the correction above)

The remote HTTP 400 is **not proven fixed**. The patch fixes the diagnostic blind spot and confirmed raw-header logging exposure. Before any separately authorized second request, review the cloud binding's destination/header substitution semantics without viewing the secret, use this exact patched commit and inspect the previous run's retained-charge ledger. A new invocation resets its local ledger; it does not automatically subtract prior unknown charges from a cumulative $2 authorization.

Do not retry automatically. If the non-secret runtime binding contract can be verified and a human explicitly approves one diagnostic request, retain the new safe category/request ID/content type for the next decision. Otherwise remain NO-GO. No second request is authorized or executed by this patch.
