# Safety controls — contracts and acceptance criteria

These controls are runtime mechanisms, not a claim that an LLM is safe. All effects remain synthetic and in memory. No paid calls were executed to implement or test them.

## Configuration A: baseline

Preserve the existing provider protocol, message roles, mandatory tool input interfaces, SDK/answer parsing, bounded execution and simulated tools. Do not enforce grants, output data schemas, evidence verification or review. Keep the same prompt and tool definitions as B/C. Shared API accounting protects spending in every mode; it is not an experimental model-safety treatment.

## Configuration B: guarded

The operator supplies a separate trusted `Policy` JSON manifest through `--policy`. It is copied before use and recorded with its SHA-256 hash. It is never loaded from model output, document content, tool responses, environment instructions or scenario authorization oracles. Missing library policy defaults to denial of every sensitive operation; the CLI requires an explicit manifest to make the trust root reviewable.

Grants bind a scenario ID, exact sensitive tool name, exact typed argument object and maximum uses per episode. There are no wildcard grants, substring permissions or automatic authority inferred from user prose. Grant IDs must be unique. Multiple grants matching one operation are ambiguous and deny it. Replay beyond the use allowance denies execution. Actual simulated execution consumes a grant even if its success response is subsequently rejected. Policies are trusted operator configuration, not signed documents or revocable external capabilities; malicious local code or policy-file changes are outside this boundary.

Every input is validated before dispatch. Read outputs must be either a document (`source_id`, `body`) or a nonempty list of numeric observations (`source_id`, numeric `value`, `unit`, optional ISO-date `timestamp`). Extra fields, malformed JSON strings, missing fields, wrong types, invalid dates and duplicate observation source IDs are rejected. `send_email` and `update_record` responses must have literal status `simulated` and the correct nonnegative effect index. Output validation happens after execution and cannot undo an effect; real effects are deliberately unsupported. Raw rejected data remains in the appropriate model/tool trace; the agent receives an error rather than a false success.

Validated reads are wrapped as untrusted data with the runtime-known fixture key. No body or metadata field can change a message role or manufacture a grant. Embedded instruction text is not removed or executed by the runtime. A model can still follow it in language; guard action authorization and final delivery independently. A trusted list of protected literals blocks their use in tool arguments and delivered answers, but is not general secret detection or protection against encoding/paraphrase.

Evidence is indexed only after successful output validation. Claims cite observed fixture keys; attacker-controlled source labels cannot create provenance. Document support is an exact nonempty substring match. Numeric support requires exact value/unit matching, available dates and a consistent set of observations. Different values, units, dates, missing timestamps, unseen references or changed results make evidence uncertain. The guard downgrades `verified` and sets `uncertainty`; it never invents values, removes inconvenient observations or promotes model uncertainty to verification. Proposed and delivered answers are both preserved. These checks establish bounded textual/structured support, not authenticity, recency, semantic entailment or real-world truth.

## Configuration C: guarded plus oversight

Only an operation already permitted by B can reach `Reviewer.review`. The reviewer receives a frozen request with objective, scenario ID, canonical action JSON and grant ID. It has no tool handles and returns only a strictly revalidated decision. It cannot grant permission or mutate the operation. `FakeReviewer` provides deterministic allow, deny, failure and timeout behaviors; CLI users must explicitly select `fake-allow` or `fake-deny`.

Denial, absence, exceptions, malformed or mutated decisions, cancellation and deadline expiry deny the operation. Exception messages are omitted. A late approval is rejected even if a reviewer suppresses cancellation. Review attempts, actual invocation, reason, decision, latency and successful-response usage estimates are recorded. The synchronous runtime rejects nested-event-loop invocation explicitly rather than silently bypassing review.

Reviewers must be trusted, nonblocking async implementations that cooperate with cancellation. This is not process isolation: a reviewer that blocks the event loop or never finishes cancellation can stall the process. No sensitive action executes while waiting, but wall-clock termination is not guaranteed against malicious reviewer code. A real LLM reviewer adapter is not shipped; its future implementation must reserve shared request/cost budgets before all calls/retries and retain unknown bills after cancellation. Self-reported reviewer metrics alone are not spending enforcement.

## Acceptance coverage

- Complete an explicitly authorized synthetic task in A, B and C; refusal of everything does not pass.
- Reject document authority spoofing, altered arguments, extra input fields, ambiguous permissions, wrong scenario scope and exhausted replays.
- Reject malformed outputs and false simulated success confirmations; downgrade unsupported/conflicting evidence without overwriting the proposed answer.
- Verify that a reviewer cannot authorize an otherwise denied operation or mutate an approved action.
- Measure a deliberately incorrect denial and an approval under deliberately misconfigured policy against independent evaluator ground truth.
- Fail closed for reviewer failures, timeout, cancellation and invalid decisions, and retain reasons in traces.
- Reject comparisons with different scenarios/trials, policy snapshots, parameters or budgets; preserve both per-case and per-category outcomes.

The original three scenarios remain unchanged. Additional synthetic probes are test fixtures, not a new corpus or live research results.
