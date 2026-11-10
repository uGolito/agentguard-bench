# Claude Haiku compatibility correction — 0.4.4

## Confirmed request defect

The previous adapter combined the SDK 2.4 default API version 2026-10-21 with temperature=0 injected through extra_body. Anthropic's [API migration guide](https://platform.claude.com/docs/en/api/migration-2026-10-21#sampling-parameters-are-removed) explicitly documents a 400 for sampling parameters on that version and recommends the older API when a non-default sampling value is required. This establishes a defect in the constructed request. The reported direct-VPS failure means a Codex proxy is not necessary to reproduce the issue. The discarded server message cannot be recovered, so we cannot prove which validation error the particular request ID reported first or exclude further problems.

## Minimal correction and preserved controls

Both primary and reviewer clients now explicitly send anthropic-version: 2023-06-01. The version is reapplied when the SDK client is cloned, including injected clients. The frozen temperature=0 protocol is preserved; silently omitting it on the newer API would change effective sampling to the server default. There is no automatic version negotiation, retry or fallback. Requested API version is recorded in live provider/reviewer metadata, and comparisons reject differing versions.

The [service-tier documentation](https://platform.claude.com/docs/en/api/service-tiers) accepts standard_only, so it is unchanged. The six tool definitions retain their names and object input_schema; local SDK types and [tool documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) support these fields. Message roles, grouped tool results, model ID, max_tokens and system prompt are unchanged. No additional authentication header is introduced. The [migration guide's authentication section](https://platform.claude.com/docs/en/api/migration-2026-10-21#api-keys-are-sent-as-authorization-bearer) confirms the Claude API accepts the SDK's Bearer scheme.

Proxy/TLS handling, authorization, CI/live gates, global request caps, retries and conservative Decimal accounting are unchanged. A failed request still retains unknown billing. Old run ledgers are not loaded into new invocations; cumulative authorization must account for earlier unknown charges explicitly. No scenarios, labels, hypotheses or existing results are changed.

## Strictly filtered useful messages

Diagnostics may now add safe_message for a small set of whole-message validation templates. For example, the input template `temperature: Extra inputs are not permitted` becomes the canonical text `temperature: Request parameter is not permitted.` Only fixed parameter names and canonical constant strings are emitted. Unknown prose, extra suffixes, embedded credentials, long messages and unsupported field names produce no safe_message. This is not blacklist redaction or truncation of arbitrary server content. Original HTTP error bodies remain excluded; existing safe categories/IDs/content types/origin handling and raw-log suppression remain.

This cannot restore messages discarded by version 0.4.3. It provides safe evidence for a future separately authorized failure. No new API request or live experiment was executed for this correction.

## Offline evidence and limits

Regression tests encode the documented version rule with in-memory HTTP transports, assert the old header/temperature combination is rejected by that fixture, and verify the corrected primary/reviewer wire format preserves temperature=0. They also cover constructor headers, cloning, recorded API version, comparison controls, known/unknown error templates and the existing budget/retry/redaction suite. A passing fixture is not proof of remote model success. Live acceptance remains untested.

## VPS image update after validation

Use the exact validated commit from the completion report. These commands fetch source and build/check an image; they do not run a smoke test. Keep the existing 0.4.3 image and private result directory. Do not copy the API key into Git, build arguments or Docker context.

```bash
set -euo pipefail
cd ~/agentguard-lab/repo
git fetch origin
REV=VALIDATED_COMMIT_FROM_COMPLETION_REPORT
git cat-file -e "$REV^{commit}"
git archive --format=tar "$REV" | docker build --pull \
  --label "org.opencontainers.image.revision=$REV" \
  -t agentguard-lab:0.4.4 -

docker run --rm --network none --entrypoint python agentguard-lab:0.4.4 -c \
  'import importlib.metadata as m; from agentguard.providers.anthropic import CLAUDE_API_VERSION; assert m.version("agentguard-bench")=="0.4.4"; assert CLAUDE_API_VERSION=="2023-06-01"; print("0.4.4 / API 2023-06-01 verified offline")'

docker run --rm --network none agentguard-lab:0.4.4 run \
  --provider anthropic --model claude-haiku-4-5-20251001 --mode baseline \
  --scenario-id ce-003 --trials 1 --max-steps 1 --max-requests 1 \
  --max-tokens 64 --temperature 0 --max-cost 0.51 --max-retries 0 \
  --timeout 30 --dry-run

docker image inspect agentguard-lab:0.4.4 \
  --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}'
```

git archive sends tracked source only, excluding the untracked secret files, virtual environment and private results in the VPS checkout. Building does not change its checkout or existing results. The two container checks have networking disabled and receive no key. A dry-run constructs no API client and incurs no model cost. Docker build requires normal package/image downloads; it is not an Anthropic request. These VPS commands have not been executed here. No Jarvis/Hermes service is changed or restarted.

A subsequent live request is a separate decision requiring explicit approval, the new image/revision check and review of cumulative prior unknown costs. The documented payload conflict is corrected; an actual successful Claude response is not yet established.
