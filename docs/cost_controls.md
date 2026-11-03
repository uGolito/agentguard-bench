# Spending controls and first-evaluation estimate

No live model requests or paid evaluations have been executed for this milestone. The following is planning arithmetic, not measured usage or benchmark findings.

## Pinned pricing

The only supported live model is `claude-haiku-4-5-20251001`. The [official model page](https://platform.claude.com/docs/en/models/haiku-4-5/overview), checked 2026-11-03, lists a 200,000-token context, standard input at $1/million tokens and output at $5/million. Cache reads are $0.10/million; cache-write estimation conservatively uses the $2/million one-hour rate, including for shorter writes. Pricing is snapshotted in each run and may become stale. Aliases and unpriced model IDs are rejected. Standard service is explicitly requested; server tools, fast/priority tiers and unexpected geography/billing categories are not supported.

## Reservation algorithm

Before every SDK request attempt, including retries, a shared thread-safe ledger checks the request cap and reserves:

`1.25 Ã— (200000 Ã— $2 + max_output_tokens Ã— $5) / 1000000`

This reserves the model's entire context at the highest supported input/cache-write rate, maximum output, plus a 25% margin. It avoids unproven byte/token heuristics and makes no token-counting API calls. At 512 output tokens the reservation is **$0.5032 per attempt**. Even a tiny request requires that much headroom. This intentionally favors stopping early over using the entire nominal budget.

After a response with validated model identity and usage, replace its unique reservation with a usage-based estimate exactly once. Standard uncached input and output use the rates above; cache tokens are tracked separately. All money comparisons use `Decimal`, not binary float. Missing/invalid usage or unsupported billing halts further calls and retains the reservation. Model-ID mismatch retains the reservation without applying the requested model's rate. Reported usage exceeding a reservation is recorded and halts execution; an already incurred bill cannot be undone.

Connection failures, timeouts and HTTP errors keep the full reservation because billing may be unknown. Retrying can duplicate billed inference, so retries are off by default and each additional attempt reserves again. Only connection/timeout errors and HTTP 408, 409, 429 and 5xx are retryable. There are at most three additional attempts, exponential delays capped at ten seconds, and no SDK automatic retries. A numeric `Retry-After` up to ten seconds is honored; longer, invalid or HTTP-date values stop automatic retrying.

## Accounting fields

- `tokens`: observed input, output, cache-write and cache-read token totals, or null for fake runs.
- `token_usage_complete`: false after any attempt without validated usage; null for fake runs. Observed zero tokens must not be mistaken for proof of zero consumption.
- `estimated_cost_usd`: cost estimated from validated usage only, excluding unknown bills.
- `conservative_charge_usd`: usage estimates plus retained reservations for unknown attempts.
- `unknown_billing_attempts`: attempt count without validated usage.
- `next_attempt_reservation_usd`: preflight headroom required for another request.

The ledger is run-local and thread-safe, not a cross-process or account-wide quota. The runner and each provider remain sequential; separate providers may share one ledger. It does not query balances, purchase credits or enforce invoices. Taxes, stale rates, billing changes, account-level activity and overbilling remain outside this estimate cap. Use provider-side spending controls as an additional boundary in any approved live experiment.

## Milestone 3 reservation audit

The audit identified missing synchronization, replayable amount-only settlement and a refund before validating returned model identity. The implementation now uses atomic reserve/settle/retain operations under a reentrant lock and opaque budget-owned single-use tokens that remain Decimal-compatible. Concurrent cap checks cannot reserve the same headroom. Duplicate settlement, fabricated amounts, foreign-budget tokens and settlement after unknown-billing finalization are rejected without changing funds. Snapshot reads are synchronized and expose pending attempts.

Provider accounting now uses per-token charges, avoiding incorrect global balance deltas when separate providers settle concurrently. Every retry reserves independently. SDK errors retain unknown charges; unexpected exceptions halt further calls and retain the token. Cancellation/interrupts retain before propagating. Known valid usage still settles when answer parsing fails, because malformed model content does not imply unknown billing. A model mismatch never refunds using the requested model's price. Concurrent tests cover overspend races, request caps and duplicate refunds; mocked SDK tests cover retries, exceptions, mismatch and per-provider totals.

## Milestone 4A shared reviewer accounting

The real Anthropic reviewer and primary provider use the same budget per mode. Every reviewer attempt reserves with its own output limit (256 by default, $0.5016 reservation); primary 512-token attempts reserve $0.5032. Concurrent callers cannot reuse headroom or settle a token twice. Injected shared ledgers must match the recorded cap/request/primary reservation configuration. Retry, timeout, exception and cancellation paths retain unknown bills; known usage settles even when the review verdict is invalid. Per-review accounting derives from attempt snapshots and records failed attempts, not only successful decisions.

Paired experiments keep a separate identical cap for each mode across all episodes. The declared total cap must cover their sum; C shares its mode cap between agent and reviewer. This can stop C earlier than A/B and is an explicit experimental limitation. Budgets are sequential per runtime and thread-safe across separate callers, not cross-process/account-wide quotas. Fake reviewers cost zero; arbitrary custom reviewer instrumentation does not enforce spending.

## First live plan — proposed only

See first_live_experiment.md for a six-case, two-trial A/B plan with optional C. Planning assumptions yield about 56 primary requests A/B and 88 primary/reviewer requests A/B/C. At 2,000 input/512 output per primary call and 500 input/256 output per review, estimates are approximately $0.26 and $0.40 before taxes. Actual usage is unmeasured. Conservative estimated caps are $1 per mode: $2 A/B or $3 A/B/C, 40 attempts per mode, zero retries. Unknown-bill reservations can stop early. These are not invoice guarantees, approval or experimental findings. Recheck current rates before any separately authorized live evaluation.
