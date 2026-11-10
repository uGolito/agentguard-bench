# Codex Cloud proxy compatibility — Milestone 4C

This is an offline-tested transport integration, not a live service validation. No Anthropic requests were made to prepare it. Scenario fixtures, frozen labels, hypotheses and public SIMULATED results are unchanged.

## Runtime contract

Codex Cloud routes outbound HTTP through a sidecar. The runtime supplies HTTP_PROXY/HTTPS_PROXY, CA trust and configured HTTP secret bindings. The application can receive a placeholder instead of the real API key; the proxy injects the configured secret on the permitted outbound request. A placeholder is not evidence that authentication is broken. Never read secret files, print values, replace injected credentials, unset the proxy or disable TLS verification.

The saved environment being listed as ready/runnable is not proof of active credential readiness. In the actual cloud task, inspect the runtime's environment_status and non-secret /etc/codex/network-policy.json. Require current observations, ready secret/runtime-variable states and enforced destination policy for api.anthropic.com. If those tools/observations are unavailable, report readiness as unverified. The Windows checkout used for offline development is not the published cloud executor. Do not bypass denied egress or create an alternate route.

## Explicit opt-in

Configure this non-secret variable in the approved cloud environment:

```text
AGENTGUARD_HTTP_MODE=codex-cloud
```

Keep the runtime-provided HTTPS_PROXY, SSL_CERT_FILE/SSL_CERT_DIR and ANTHROPIC_API_KEY variable/placeholder. The latter is required by the SDK factory before constructing a client; bind the HTTP secret through the environment's supported setup, not a repository file. The locked Anthropic SDK 2.4.0 emits **Authorization: Bearer ...** for api_key. The secret-injection binding must match that destination/header behavior; do not assume the legacy x-api-key header. No actual credential values or binding contents are needed for application logging.

Modes:

- **direct (default):** retains trust_env=False. Ambient proxy and CA environment overrides are ignored; verified platform/default TLS trust remains. This preserves existing local behavior and is not a fallback from cloud mode.
- **codex-cloud (explicit):** requires an absolute HTTP(S) HTTPS_PROXY URL. Both sync primary and async reviewer clients use that proxy explicitly and trust_env=True. Explicit proxy selection prevents NO_PROXY=* or unrelated ALL_PROXY settings from silently creating a direct route. There is no fallback when proxy setup fails. SSL_CERT_FILE and SSL_CERT_DIR retain their HTTPX2 precedence; SSL_CERT_FILE wins when both are configured. Use the runtime-provided trust configuration. REQUESTS_CA_BUNDLE is not consumed by HTTPX2.

TLS certificate and hostname verification remain enabled; redirects remain disabled. The API endpoint stays fixed at https://api.anthropic.com regardless of ANTHROPIC_BASE_URL. No custom proxy code reads, substitutes or logs authentication values. Mode selection does not enable live calls: existing explicit opt-in, positive budget, CI prohibition, timeout, request and retry controls still apply.

Security trade-off: opting in trusts the selected proxy and environment CA configuration to mediate TLS and inject credentials. Only enable it in a reviewed trusted runtime; do not copy proxy settings from retrieved documents or model output. Invalid mode/proxy/CA construction errors are sanitized without values or chained exception details. Only the mode name is added to live metadata, not proxy addresses, CA paths or headers. Injected test clients are labeled injected. Controlled comparisons require matching primary transport-mode metadata.

## Offline verification

```bash
pytest tests/integration/test_cloud_http.py -q
```

Tests block application sockets/DNS. They inspect sync/async routing with NO_PROXY=*, successful custom CA loading, verified TLS flags, default isolation, invalid configuration, fixed endpoint, zero SDK retries and exact dummy-placeholder Authorization headers. Mock SDK responses test usage settlement and absence of dummy secrets in logs/traces. Existing budget/concurrency/retry tests remain unchanged. These checks do not establish that a real cloud secret binding, proxy, account or remote model works.

With the cloud mode variable configured, this preview sends no requests and constructs no clients:

```bash
agentguard run --provider anthropic --model claude-haiku-4-5-20251001 --mode baseline --scenario-id ce-003 --trials 1 --max-steps 1 --max-requests 1 --max-tokens 64 --temperature 0 --max-cost 0.51 --max-retries 0 --timeout 30 --dry-run
```

A dry-run validates the plan, not the actual proxy/CA or authentication. Do not infer runtime readiness from preview success alone.

## First authentication smoke test — not executed

After reviewing current cloud readiness and obtaining separate explicit paid authorization, use the same command with --allow-live in place of --dry-run and --output results/live-auth-smoke-001 (a new private output directory). Set AGENTGUARD_HTTP_MODE=codex-cloud in that runtime first. One request is permitted, zero retries, 30-second transport timeout, no oversight. A tool-use response can end at the step limit: successful service authentication is distinct from benchmark completion. A 64-token answer may truncate; inspect sanitized status/HTTP response and usage, not only task completion.

At the recorded model rates, 2,000 input plus 64 output tokens would cost approximately $0.00232; actual usage is unknown. The full-context conservative reservation is $0.5004, so the local estimated cap is $0.51. These are estimates, not invoice guarantees. This separate smoke invocation does not automatically debit the later $2 A/B run cap; explicitly account for its actual/unknown cost in any cumulative authorization. No request may be initiated merely because this patch or its CI passed.

The frozen 24-episode A/B protocol remains $1 per mode / $2 total, 40 requests per mode, zero retries and four steps. Both modes must use the same reviewed transport. A fresh code/environment snapshot must be frozen before live execution without changing labels or hypotheses.

## HTTP error diagnostics and unresolved 400

See http_400_investigation.md for local SDK evidence and hypotheses concerning the operator-reported first smoke failure. Ready binding metadata and an allowed domain do not prove effective Bearer placeholder substitution. The adapter now retains only safe structured HTTP-error fields; arbitrary error bodies, headers and exception strings remain excluded. Raw dependency wire logging is suppressed, while application logs and structured events remain available. Origin is unknown without independent provenance. Valid request parameters/authentication are unchanged. Do not interpret this patch as a confirmed remote fix or permission for a second request; review prior retained billing and obtain separate explicit authorization.

## Sampling/API version correction in 0.4.4

The primary and reviewer now explicitly use API 2023-06-01 to preserve temperature=0 under the published migration contract. The SDK version remains pinned at 2.4.0, and the Bearer/proxy/TLS configuration is unchanged. Requested API version is recorded separately from SDK version. See claude_compatibility_fix.md for evidence, limitations and offline-only image update commands. Do not reuse 0.4.3's assumption that sending temperature through extra_body is valid under API 2026-10-21.
