# First controlled live experiment — readiness and proposed boundary

Status: proposed, not approved or executed. No live LLM benchmark results have been published yet.

## Engineering readiness

The primary Anthropic adapter, deterministic A/B controls, run snapshots, usage accounting, trace capture, spending reservations and offline regression suite support preparing a small A/B service-qualification experiment. This is readiness to test an integration, not evidence of model safety or permission to spend. Service/account availability remains unverified. Keep all tools synthetic.

C is operational with injectable reviewers and shipped deterministic fakes. It is not ready for an independent-LLM H4 study: a real reviewer adapter must first implement shared request/spending reservations, usage accounting and cancellation behavior. Do not label a primary-Claude run with a fake reviewer as independent LLM oversight.

## Proposed qualification design

- Freeze the repository commit, package/run-schema versions, the same three scenario hashes, policy hash and hypotheses before invocation. Preserve the exact plan alongside raw artifacts.
- Use the exact supported model snapshot, identical system prompt, tool definitions, temperature, token limits, trials, step and request caps in A and B. Use the same explicit policy manifest, enforced only in B.
- Start with one trial per scenario and a small per-run budget and request cap (for example $1 estimate cap and six attempts per mode, no retries, 512 output tokens). These are proposed caps, not authorization or invoice guarantees. Each attempt requires the documented $0.5032 reservation headroom. Separate run caps do not create an account-wide total cap.
- Verify the dated pricing snapshot and obtain explicit approval of the total intended spending and credential use before any request. No key is needed for implementation, offline tests or dry runs.
- Run all selected cases, retain errors/format failures/blocked operations, and inspect response/tool wire compatibility before interpreting any completion or security outcome.
- Report raw model emissions, delivered answers, effects, policy decisions and reviewer identity separately. Label the small study as service qualification; do not claim hypothesis validation, significance or representative robustness.

## Remaining research readiness work

The three easy cases do not test oversight or represent a full benchmark. Add preregistered authorized-action and reviewer-challenge scenarios, a budgeted real reviewer, repeated live trials, semantic evaluator validation, statistical design and a reproducibility audit before making comparative research claims. Docker remains locally unverified. No GitHub Release is proposed here.
