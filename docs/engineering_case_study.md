# Engineering case study: making agent authority observable

AgentGuard Bench asks whether an agent can complete a legitimate task while resisting lower-trust instructions. A refusal-only system cannot meet that goal. The engineering contribution is a small, inspectable execution/evaluation stack that separates model proposals, external enforcement, reviewer judgments and simulated execution.

This case study describes implemented software and offline evidence. No empirical live-model safety results or laboratory affiliations are claimed.

## Architecture decisions

The [runtime](../src/agentguard/agents/__init__.py) owns roles, tool dispatch, step limits and structured traces. A narrow [Provider protocol](../src/agentguard/providers/__init__.py) supports scripted fakes and the official [Anthropic SDK adapter](../src/agentguard/providers/anthropic.py), including tool-use IDs and grouped results. Lightweight custom code avoids an agent framework that would obscure retries, prompts or effects.

[Pydantic contracts](../src/agentguard/schemas/__init__.py) validate scenarios, actions and answers. Six [local tools](../src/agentguard/tools/__init__.py) use deep-copied fixtures; writes append in-memory simulated effects. This makes adversarial cases inspectable without permitting real email or external mutations. The trade-off is limited ecological validity: simulated tools cannot establish real deployment safety or external rollback behavior.

## Trust boundaries and authorization

[Controls](../src/agentguard/guards/__init__.py) are provider-independent. A trusted operator [policy](../src/agentguard/guards/policy.py) binds scenario ID, exact tool arguments and use limits. Documents, tool outputs and reviewer verdicts cannot grant permission. Ambiguous grants and exhausted replays deny execution. The evaluator uses separate scenario ground truth, so a mistaken policy can still be detected as an unauthorized effect.

Baseline keeps mandatory interfaces and parsing. Guarded adds output schemas, data envelopes, protected literals and [evidence checks](../src/agentguard/guards/evidence.py). Evidence originates only from successfully validated runtime reads; claim citations cannot manufacture provenance. Checks downgrade unsupported verification instead of inventing facts. Exact matching is transparent and testable but is not semantic entailment or real-world truth. Known literal protection can miss encodings and paraphrases.

## Independent oversight and failures

The injectable [reviewer contract](../src/agentguard/guards/oversight.py) runs only after deterministic permission. The [real Anthropic reviewer](../src/agentguard/providers/reviewer.py) has a fresh role/context, objective/action-only payload, no tools and a strictly validated verdict. It can veto, never expand authority. Fake allow/deny reviewers test the interface offline. Same-model separate contexts do not guarantee independent errors.

Denied, malformed, unavailable, cancelled or timed-out reviews fail closed. A late approval cannot bypass the deadline. Cooperative async cancellation is an explicit limitation: arbitrary hostile Python code is outside this isolation boundary. Truncated/invalid primary outputs remain incomplete rather than triggering hidden paid repair calls. Raw responses, proposals, blocked actions and executed effects remain distinguishable.

The public demo includes a separate fake-deny diagnostic: three authorized tasks fail because the reviewer refuses them. Keeping that failure visible matters more than presenting universally favorable numbers.

## Budget management

The thread-safe [Decimal ledger](../src/agentguard/providers/budget.py) issues opaque single-use reservations under a reentrant lock. Primary and reviewer reserve from the same mode budget before every SDK attempt. Model identity and usage are validated before settlement. Unknown bills retain reservations; duplicates and foreign tokens cannot refund twice. SDK retries are disabled and adapter retries are bounded, with zero retries in the proposed first live experiment.

The conservative full-context/max-output reservation avoids fragile token heuristics but requires substantial headroom even for tiny prompts. A 512-output-token primary request reserves $0.5032 at the recorded rates. This can stop small-budget runs early, especially after unknown-billing failures. It is an estimated process-local cap, not an invoice/account-wide guarantee. Concurrency, replay, exception and refund behavior have regression tests.

## Evaluation integrity

The [paired scheduler](../src/agentguard/experiments.py) reuses identical scenario/configuration/policy controls, isolates episode state and records shuffled scenario order plus rotating mode order. C consumes its cap on primary and reviewer calls, an explicit resource confound. [Evaluation](../src/agentguard/evaluators/__init__.py) separates proposed unsafe actions from executed ones and excludes benign cases from attack denominators. A malformed replay is checked against effects already executed, avoiding an undercount after authorization consumption.

[Reporting](../src/agentguard/reporting/__init__.py) preserves raw numerators/denominators and category breakdowns. [Cluster bootstrap intervals](../src/agentguard/reporting/statistics.py) retain repeated-trial dependence and paired samples; fake/injected, incomplete, sparse or degenerate evidence receives no misleading interval. Legacy mixed ASR is retained with a warning; the dashboard uses model/runtime endpoints separately.

The [journal](../src/agentguard/tracing.py) appends and flushes before API dispatch, preserving partial evidence. It is not transactional recovery. Scenario authors also define criteria and example policy, so independent label review remains outstanding. Exact claims can reject correct paraphrases; public scripts may contaminate future training data. These are documented threats to validity rather than hidden behind aggregate scores.

## Public demonstration and verification

The [demo builder](../src/agentguard/demo.py) calls the existing runner, paired scheduler, evaluator and reporting functions. Only fake scripts are overlaid on copied scenarios. Frozen fixtures, labels, hypotheses and expected outcomes are unchanged. It accepts no live-result imports. Volatile instrumentation is omitted only in public SIMULATED projections; full experimental traces retain it. LF output plus a SHA-256 manifest enables byte-for-byte reproduction on Windows and Linux.

The [static dashboard](../site/index.html) uses plain HTML/CSS/JavaScript, same-origin assets and inert text rendering for untrusted instructions. It has no API keys, backend, external fonts or analytics. The [Pages workflow](../.github/workflows/pages.yml) gates deployment on tests, secret/dependency/security checks, artifact regeneration and headless browser checks. Only site/ is uploaded. The [demo tests](../tests/integration/test_demo.py) verify frozen fields, action attribution, false refusals, reproducibility and CLI behavior alongside existing regression coverage.

What remains unverified: live service/tool-call compatibility, real model resistance, reviewer quality, actual latency/cost and generalization beyond the authored corpus. The [first live A/B plan](first_live_experiment.md) remains a separately approved qualification with credentials/model-access checks and a $2 estimated cap; it has not been executed.
