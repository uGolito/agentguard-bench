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
