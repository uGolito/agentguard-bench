# Changelog

## 0.4.6

- Request native JSON-schema output for the independent Anthropic reviewer using
  the generic allowed/reason Verdict schema; record its versioned output protocol.
- Keep the strict parser, local reason length/type/extra-field validation and
  fail-closed handling. No Markdown stripping, repair calls or fallback.
- Preserve reviewer independence, authorization policy, budget reservations,
  request/retry limits, timeouts and primary output protocols.
- Add offline wire and regression tests for fenced allow verdicts and malformed
  decisions. Preserve private interrupted campaign data; no automatic resumption.
- No paid calls or scenario/criterion changes; live acceptance remains unverified.

## 0.4.5

- Add explicit opt-in anthropic-json-schema-v1 final-answer output via the
  official SDK output_config.format; retain prompt-json-v1 as the default.
- Preserve API 2023-06-01, temperature, existing tools, budget reservations,
  request limits and bounded retries. No automatic protocol fallback or repairs.
- Record output protocols and reject incompatible comparative runs.
- Separate JSON syntax/schema diagnostics from conditional semantic task failures;
  unavailable historical diagnostics remain unavailable rather than zero failures.
- Add offline SDK wire tests across all three modes, tool continuations, invalid
  and semantically wrong responses, refusals, truncation, limits and accounting.
- Document compatibility evidence and the unverified live-acceptance limitation.
- No scenario, hypothesis, criterion or published benchmark-result changes.
  No paid model evaluation was executed for this version.

Earlier engineering history is recorded in [docs/decisions.md](docs/decisions.md).
