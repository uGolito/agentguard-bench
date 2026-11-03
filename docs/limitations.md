# Limitations and threats to validity

- No live LLM benchmark results have been published yet. Scripted behavior and mocked SDK transport tests are not model evidence. No paid evaluation or account/model availability test was performed.
- Three easy original cases provide no representativeness or statistical power. Twenty-seven scenarios remain unimplemented.
- Exact structured claims can be gamed; paraphrases are not recognized. No independent semantic evaluator exists.
- Baseline has no external authorization, output schema or evidence safeguards. Sensitive effects are simulated, including deliberately unauthorized proposals used in tests.
- Trusted authorization currently covers tool names, not argument scope. Provenance labels are recorded, not verified. Evidence semantics need dedicated evaluation in later milestones.
- No independent oversight or MCP transport yet. The official Anthropic adapter now records usage and implements conservative estimates, caps, bounded retries and socket timeouts. These controls are not an account-wide or invoice-level spending guarantee. They do not coordinate between processes or query account balances.
- Only the priced snapshot `claude-haiku-4-5-20251001` is currently supported. Its availability and pricing may change. Pricing is snapshotted and should be checked before any approved experiment. Cache writes use a conservative one-hour rate; unknown costs keep a full reservation.
- No streaming, extended thinking, server tools, priority/fast tiers or strict overall wall-clock deadline. Retry delays are bounded, but SDK timeouts are socket-operation timeouts. A timed-out request may still be billed. Failed requests retain unknown-bill reservations and may stop small-budget runs early.
- Final answers require exact benchmark JSON. Format failures and truncations remain incomplete; prose refusals without structured fields may not count as false refusals. Literal disclosure checks count a canary even when quoted to warn about an attack. Neither behavior is a semantic safety judgment.
- Successful raw model content and request payloads are retained, including malicious synthetic strings; API keys and HTTP headers are excluded, and HTTP error bodies are omitted. Runs remain in memory until artifacts are written, so abrupt termination lacks crash recovery.
- SDK 2.4 compatibility uses its strict-response-validation option and `extra_body` for the legacy model's temperature parameter. Lock-file upgrades require the wire-level tests. Injected clients are a test seam; endpoint/transport trust remains the caller's responsibility.
- Scripts contain expected answers and ignore tool output; comparisons between fake configurations would be scientifically meaningless.
- Latency measures local infrastructure only; repeated fake trials are not independent samples of agent behavior.
- Dependency pinning aids reproduction but hardware, OS and timestamp differences remain. Docker availability and CI execution must be reported honestly in validation records.
- No claims of model safety, legal compliance, statistical significance or laboratory affiliation follow from this repository.
