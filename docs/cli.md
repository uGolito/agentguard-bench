# CLI reference — Milestone 3

Run commands from a checkout containing `scenarios/`. `agentguard --help` and `agentguard run --help` show the installed interface.

- `list-scenarios [--scenarios PATH]`: list typed scenario definitions.
- `validate-scenarios [--scenarios PATH]`: validate schemas and unique IDs.
- `run`: execute episodes and preserve incomplete/error outcomes.
- `report --run PATH`: render a saved JSON run, identifying fake and injected-client execution.
- `compare --baseline PATH --candidate PATH`: reject mismatched controls and report paired/per-category metrics and resource differences; no significance claim.

## Run options

- `--provider fake|anthropic`: defaults to fake; no implicit model requests.
- `--mode baseline|guarded|guarded_oversight`: default baseline. `guarded-oversight` is accepted as an alias for `guarded_oversight`.
- `--policy PATH`: explicit trusted policy JSON, required for guarded modes. Supply the same file in baseline for a controlled comparison, even though baseline does not enforce it. The example file denies sensitive actions and protects the synthetic canary.
- `--reviewer fake-allow|fake-deny`: required in oversight mode and rejected in other modes. These are explicitly deterministic fakes. A custom reviewer can be injected into the Python runner; no paid reviewer adapter is provided.
- `--reviewer-timeout`: cooperative review deadline in seconds, default 2 (greater than zero, at most 30). Review denial, failure, cancellation or timeout blocks execution.
- `--model`: fake defaults to `scripted-fixture-v1`; Anthropic requires the explicit priced snapshot `claude-haiku-4-5-20251001`.
- `--allow-live`: explicit permission for this invocation to send paid model requests. Required for Anthropic execution, never inferred from a key's presence.
- `--max-cost`: USD estimate cap, default zero. Anthropic requires a positive cap, including previews. A cap below the next-attempt reservation permits no requests.
- `--max-requests`: shared across scenarios/trials and retries, default 100.
- `--max-steps`: provider turns per episode, default 8 (1–100). Retries consume requests but not additional turns.
- `--max-tokens`: output limit per request, default 512 (64–4096).
- `--temperature`: default 0 (0–1), included in request and configuration snapshots. Zero does not imply model determinism.
- `--timeout`: SDK connect/read/write/pool timeout in seconds, default 30 (greater than zero, at most 120). This is not an end-to-end wall-clock deadline.
- `--max-retries`: additional attempts per provider turn, default 0 (0–3). SDK retries are always disabled. Each retry must pass the global budget check.
- `--trials`: repeats per scenario, default 1 (1–100).
- `--category`: exact scenario category; unmatched categories fail before execution.
- `--scenarios`: fixture directory, default `scenarios`.
- `--output`: new artifact directory, default `results/offline`. An existing directory is rejected before provider construction. The directory is reserved before any paid work; setup failures may leave an empty directory.
- `--dry-run`: validate and show a plan; never constructs an API client, reads credentials, or calls a token-counting endpoint. Anthropic previews do not require `--allow-live`.

## Credential-free preview

```bash
agentguard run --provider anthropic --model claude-haiku-4-5-20251001 --max-requests 6 --max-cost 1 --max-tokens 512 --max-retries 0 --dry-run
```

Actual Anthropic execution requires removing `--dry-run`, adding `--allow-live`, a separate approval to spend, and `ANTHROPIC_API_KEY` in the process environment. No live execution was performed during Milestones 1–3. `CI` blocks default live client creation. Alternate API base URLs, environment proxies and redirects are disabled for the default client. Injected clients exist for integration tests and retain caller responsibility for endpoint/transport configuration.

The CLI returns an error for invalid configuration or setup. A completed infrastructure run can still contain failed episodes; inspect `results[*].execution.status`, blocked actions and review records, not only the command's exit code. Statuses include `completed`, `answer_blocked`, `step_limit`, `request_limit`, `cost_limit`, `timeout`, `provider_error`, `provider_exception`, `invalid_response`, `invalid_usage`, `unsupported_billing`, `output_limit`, `model_mismatch`, `reservation_exceeded`, `retry_after_limit`, and `accounting_halted`. A blocked action is returned as a tool error and does not itself terminate the episode; the provider may still complete its legitimate task.

Model final text must be exactly the `Answer` JSON object (claims with value/source IDs/verified, uncertainty and refusal), without Markdown. Format failures are retained, never silently repaired using another paid call. Tool-use stop reasons execute typed calls; truncated responses execute none. Multiple calls are executed sequentially and returned in one correctly correlated result message.

## Controlled offline comparison

```bash
agentguard run --mode baseline --policy examples/policy.json --output results/a
agentguard run --mode guarded --policy examples/policy.json --output results/b
agentguard run --mode guarded_oversight --policy examples/policy.json --reviewer fake-allow --output results/c
agentguard compare --baseline results/a/run.json --candidate results/b/run.json
agentguard compare --baseline results/b/run.json --candidate results/c/run.json
```

These are infrastructure replays, not LLM evaluations. The initial three scenarios contain no authorized sensitive operations and therefore do not invoke review. Authorized-action, incorrect-denial and reviewer-failure cases are in the offline test probes.
