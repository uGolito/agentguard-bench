# Decision log

## 2026-11-03: Milestone 1 boundary (accepted by mission scope)

Implement three scenarios and offline baseline only. Defer paid providers, guarded/oversight configurations, full corpus and research release. Keep scenario assets outside the wheel and document checkout-based execution; snapshots make individual runs self-contained. Use mandatory typed input interfaces in every future configuration and reserve output-policy safeguards for comparative experiments. Do not publish fake outcomes as model findings.

The repository is independent of FamilyProps. No FamilyProps sources, personal datasets or employer materials are used.

## 2026-11-03: Milestone 2 integration (accepted by explicit user mission)

Extend the existing provider/runtime split with the official Anthropic SDK and keep every tool synthetic. Add shared run-wide request/spending accounting, reserve before retries, retain reservations for unknown billing, and refuse unpriced model aliases. Support the exact Haiku 4.5 snapshot initially; defer other pricing profiles rather than guess rates. Live use requires per-invocation opt-in and a positive budget, and default client creation is blocked in CI. No credentials are needed to implement or test this milestone and no paid calls are authorized.

Advance the package to 0.2.0, run schema to 1.1.0 and baseline prompt to v2. Preserve the three source scenario files. Add parallel tool-use IDs, explicit JSON answers, fixture-key discovery hints and disclosure checking over raw assistant emissions, including malformed final output. These protocol/evaluator changes must be identified when comparing future runs. Safeguards and oversight remain Milestone 3 work; the benchmark is still unvalidated against a live service. No GitHub Release is authorized.

## 2026-11-03: Milestone 3 controls (accepted by explicit user mission)

Advance the package to 0.3.0 and run schema to 1.2.0. Keep prompt baseline-v2, provider architecture, six tools and original three scenario files. Add exact argument/use-scoped trusted policies independently of evaluator ground truth. Guarded CLI runs require an explicit policy manifest; library calls without one deny sensitive operations. Validate common typed local read outputs and simulated confirmations, preserve untrusted role boundaries, and downgrade unsupported/conflicting evidence without inventing new facts. Protected literals are explicitly bounded checks, not general DLP.

Provide independent injectable async oversight with deterministic fake reviewers and fail-closed denial, errors, cancellation, malformed decisions and cooperative timeouts. Reviewer implementations are trusted code, not a sandbox. Do not add a paid LLM reviewer adapter without integrating shared billing limits; current C runs test the interface and cannot support H4 findings. Record this as an explicit remaining integration task.

Keep raw model proposals visible alongside delivered answers and executed effects. Compare only controlled scenario/policy/configuration snapshots, and retain per-case/per-category metrics and reviewer availability/false-refusal costs. New test-only probes exercise authorized sensitive tasks and deliberately mistaken policy; do not silently expand the versioned research corpus or present those probes as live experiments.

The reservation audit found unsynchronized cap checks, amount-only settlement replay and refund before returned model-identity validation. Fix these with a lock, unique budget-owned single-settlement tokens, per-token provider totals and unknown-bill retention. No paid API calls, credit purchases, new repository or Release are authorized for this milestone.

## M4A — corpus, independent reviewer and controlled evaluation (2026-11-03)

- Expand to 30 original versioned cases, preserving original three assets; retain original corpus fixtures explicitly for regression tests. Add positive authorized actions and benign controls.
- Use official async Anthropic SDK for independent reviewer-v1 context with objective/action only and shared per-mode ledger; fail closed and retain unknown bills. No paid evaluations performed.
- Freeze prompt baseline-v3 and run schema 1.3.0 for expanded closed status/value/provenance criteria. Do not silently pool earlier evaluator versions.
- Separate model proposals from executed outcomes and retain labeled legacy mixed ASR. Add paired counterbalanced repeated schedules, order seeds (not unsupported model sampling seeds), per-category counts and conditional cluster bootstrap intervals; suppress misleading intervals for mocks/partial/sparse/degenerate data.
- Journal requests before dispatch with append/flush; no transactional recovery or resume promise. Qualification can stop globally on technical/reviewer failure and retain partial outcomes without comparisons.
- Package version 0.4.0. Independent label/policy review and approved live qualification remain outstanding; no release or empirical model findings are published.

## M4B — public offline demonstration (2026-11-04)

- Reuse existing runner, paired scheduling, safeguards, reporting and 30 frozen scenarios. Overlay only copied fake scripts for adversarial probes; never change hypotheses, labels, fixtures or expected outcomes.
- Publish 180 explicitly SIMULATED comparison episodes plus three separate fake-deny false-refusal probes. Retain incomplete outcomes and separate model/runtime attack-success attribution.
- Export deterministic public projections with volatile instrumentation omitted, canonical LF and SHA-256 file digests. Full experimental artifacts retain identifiers, timestamps and timing. Never import live traces into the public builder.
- Plain static HTML/CSS/JavaScript avoids backend services, credentials, paid infrastructure and frontend dependencies. Render attack strings as inert text; no external scripts/fonts/analytics.
- Test regeneration and browser interactions before Pages deployment; only site/ enters the deployment artifact. Browser tooling is an optional development dependency pinned in workflow, not an agent/runtime requirement.
- Package 0.4.1; no paid evaluations, billing changes or release. Same frozen live protocol still requires credentials, account/model verification and separate approval.

## M4C — explicit Codex Cloud transport (2026-11-05)

- Preserve direct default trust_env=False. Add AGENTGUARD_HTTP_MODE=codex-cloud for both official SDK HTTP clients, requiring an explicit HTTPS_PROXY and honoring runtime CA trust with TLS/hostname verification enabled.
- Set proxy explicitly so NO_PROXY cannot create a direct path; reject missing/invalid proxy setup without fallback. Keep fixed API endpoint, redirects off, CI/live gates, accounting and bounded retries unchanged.
- Preserve SDK Bearer placeholder authentication for sidecar injection. Sanitize transport construction errors; record only mode in live metadata and reject uncontrolled mode differences in comparisons.
- Package 0.4.2; no dependency changes, scenario/label/hypothesis changes or experimental result changes. Existing public SIMULATED assets remain byte-identical. Actual cloud binding/account readiness and paid smoke execution remain unverified and separately gated.

## HTTP 400 diagnostic investigation (2026-11-06)

- Preserve API version, model, temperature, service tier, Messages/tool schema and single Bearer authentication. Local SDK types/wire serialization are evidence of SDK behavior, not remote acceptance. No confirmed request-compatibility defect supports speculative changes.
- Add shared bounded diagnostics for primary/reviewer errors: allowlisted category, syntactically validated/redacted request ID, normalized content type, response shape, HTTP status and unknown origin. No raw HTTP error body/header or exception message persists.
- Suppress confirmed raw dependency header logging; keep application logs. Restrict existing malformed HTTP-200 model tracing to assistant envelopes, excluding non-model error bodies.
- Package 0.4.3; unchanged proxy/TLS, request/retry/budget controls, frozen assets, dependency lock and published SIMULATED results. HTTP 400 remote cause remains unresolved; no Anthropic request or new experimental run is performed for this patch.

## 0.4.4 — documented sampling/API incompatibility correction (2026-11-10)

- Supersedes the 0.4.3 unresolved sampling/version hypothesis: official migration guidance states that API 2026-10-21 rejects sampling parameters, even defaults. Pin 2023-06-01 in primary/reviewer constructors and clones to preserve the frozen temperature=0 protocol; do not silently adopt temperature 1 by omission.
- Record API version separately from SDK version and reject version-mismatched comparisons. Keep model, service_tier, tools, authentication, proxy/TLS, request/retry and budget controls unchanged.
- Allow safe_message only through whole known-template recognition and fixed canonical output. Unknown/freeform text and secrets remain excluded. Do not recover or fabricate the discarded original error message.
- Package 0.4.4, no dependency/scenario/label/hypothesis/result changes. Unit mocks encode the documented rule; actual server success remains unverified. Provide tracked-source-only Docker rebuild and network-disabled checks, without executing a new smoke test or touching Jarvis/Hermes.


## 0.4.5 — explicit native JSON protocol and final-answer diagnostics

- Retain historical prompt-json-v1 by default; native anthropic-json-schema-v1
  requires explicit selection on run or paired-run and the Anthropic provider.
- Apply the same primary-agent output protocol to A/B/C; keep independent review
  unchanged. Record protocol metadata and reject mismatched comparisons.
- Keep strict Answer validation and frozen semantic criteria. Format errors remain
  incomplete; native schema validity does not imply semantic correctness.
- Compatibility is documented and tested through SDK 2.4.0 mocked wire requests
  with API 2023-06-01. Live server acceptance remains unverified for this protocol.
- No paid calls, new benchmark findings, scenario changes or VPS changes.


## 0.4.6 — independent reviewer native JSON output

- Request the generic Verdict schema with native output_config.format on every
  Anthropic review, independently of the primary response protocol. Record
  anthropic-review-json-schema-v1 in reviewer metadata.
- Retain the existing prompt, isolated context, trusted policy, strict Verdict
  parser, local reason limits, fail-closed behavior and shared budget controls.
- No Markdown recovery, retries beyond configured limits or automatic campaign
  restart. Preserve interrupted private 0.4.5 artifacts and reject mixed-version
  comparisons. Actual live reviewer acceptance is not established by offline tests.
