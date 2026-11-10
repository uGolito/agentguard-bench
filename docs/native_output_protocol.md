# Native Anthropic final-answer protocol — offline qualified

No live requests were executed to qualify this patch. No empirical model results
are published. The SDK serializes the tested combination, but only a separately
authorized live request can confirm service acceptance for this account.

## Compatibility evidence

- Official [structured-output guide](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
  documents output_config.format, JSON Schema, and coexistence with tool calling.
  Its [compatibility section](https://platform.claude.com/docs/en/build-with-claude/structured-outputs?lead_type=emfin#compatibility)
  includes Haiku 4.5. JSON grammar applies to final text, not tool results.
- Version compatibility is supported by Anthropic's own SDK source, not inferred
  solely from today's API reference (which defaults to API 2026-10-21).
  SDK [v0.79.0 client](https://github.com/anthropics/anthropic-sdk-python/blob/v0.79.0/src/anthropic/_client.py)
  defaults to 2023-06-01, while its
  [Messages types](https://github.com/anthropics/anthropic-sdk-python/blob/v0.79.0/src/anthropic/types/message_create_params.py)
  already expose output_config. This supports availability before the new API.
- Installed, locked SDK **2.4.0** exposes output_config in Messages.create,
  OutputConfigParam.format and JSONOutputFormatParam.schema/type. Real SDK
  MockTransport tests verify the exact wire payload with API **2023-06-01**,
  model **claude-haiku-4-5-20251001**, temperature **0**, six existing tools,
  tool_use/tool_result continuation and final JSON. A mock is not a server.

No API-version change, beta header, SDK upgrade or strict tool-input feature is
required by this implementation. Existing TLS, proxy, retry and budget controls
remain in force. A server rejection stops; there is no fallback to another protocol.

## Protocols and controls

- prompt-json-v1: historical prompt-only JSON contract, default; unchanged payload.
- anthropic-json-schema-v1: opt-in native JSON format for every primary request,
  using anthropic.transform_schema(Answer). The SDK removes unsupported default
  keywords; original strict local Answer validation still applies. No schema-specific
  model values, source IDs, claim count, verified or uncertainty answers are fixed.

The schema can accept three wrong claims, verified=true and uncertainty=false;
these remain evaluator failures. It constrains structure, not scenario semantics.
We retain messages.create instead of messages.parse so usage is settled before
local validation. Refusals, token limits, errors and malformed mocked replies retain
explicit handling. No repair requests or extra requests are introduced.

The same option propagates through run and paired-run to A/B/C. It controls the
primary answer only; the independent reviewer retains its existing ReviewDecision
contract. Native mode is rejected for the fake provider to avoid misrepresenting
scripted infrastructure as native decoding.

Run configuration and provider metadata record output_protocol. Comparisons
reject different or inconsistent markers. Missing historical markers mean
prompt-json-v1; other compatibility checks remain enforced. Published fake demo
artifacts retain their existing projection and do not claim native qualification.

## Preview without API calls

```bash
agentguard run --provider anthropic --model claude-haiku-4-5-20251001 --scenario-id ce-003 --output-protocol anthropic-json-schema-v1 --max-tokens 512 --max-steps 4 --max-requests 4 --max-cost 1 --max-retries 0 --dry-run
```

The same --output-protocol option is available on paired-run. Do not combine new
native runs with historical prompt-only runs. Freeze the protocol before collecting
comparative results. This patch does not authorize paid execution.

## Limitations

Native decoding does not establish truth, correct provenance, calibrated confidence
or task completion. Refusal and truncation may still fail completion. Grammar
compilation and additional system tokens may change latency and input usage, so
historical smoke costs are not a measured forecast. Budget reservation still covers
full context and output with conservative rates. Account availability and actual
server acceptance remain unverified without a separately approved live test.
