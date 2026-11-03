# Decision log

## 2026-11-03: Milestone 1 boundary (accepted by mission scope)

Implement three scenarios and offline baseline only. Defer paid providers, guarded/oversight configurations, full corpus and research release. Keep scenario assets outside the wheel and document checkout-based execution; snapshots make individual runs self-contained. Use mandatory typed input interfaces in every future configuration and reserve output-policy safeguards for comparative experiments. Do not publish fake outcomes as model findings.

The repository is independent of FamilyProps. No FamilyProps sources, personal datasets or employer materials are used.

## 2026-11-03: Milestone 2 integration (accepted by explicit user mission)

Extend the existing provider/runtime split with the official Anthropic SDK and keep every tool synthetic. Add shared run-wide request/spending accounting, reserve before retries, retain reservations for unknown billing, and refuse unpriced model aliases. Support the exact Haiku 4.5 snapshot initially; defer other pricing profiles rather than guess rates. Live use requires per-invocation opt-in and a positive budget, and default client creation is blocked in CI. No credentials are needed to implement or test this milestone and no paid calls are authorized.

Advance the package to 0.2.0, run schema to 1.1.0 and baseline prompt to v2. Preserve the three source scenario files. Add parallel tool-use IDs, explicit JSON answers, fixture-key discovery hints and disclosure checking over raw assistant emissions, including malformed final output. These protocol/evaluator changes must be identified when comparing future runs. Safeguards and oversight remain Milestone 3 work; the benchmark is still unvalidated against a live service. No GitHub Release is authorized.
