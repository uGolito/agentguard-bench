# Milestone 1 validation record

Local verification on 2026-11-03, Windows, Python 3.13.14:

- Editable project installation and `pip check`: successful.
- `pytest --cov=agentguard --cov-report=term-missing --cov-fail-under=85`: 22 tests passed; 100% line coverage of the core package. Coverage is not a safety claim.
- Ruff lint and formatting: passed after fixing a comparison CLI option mismatch discovered by integration testing.
- Three scenario schema validation and offline CLI execution: passed. Fake results were not committed as model findings.
- Bandit on `src`, excluding assert-use check B101: no issues. Assertions only express internal programmer invariants, not authorization.
- `pip-audit --disable-pip --no-deps -r requirements-dev.lock`: no known vulnerabilities at verification time.
- Basic tracked-file credential/private-path scan: passed. This regex check is limited and does not establish absence of every possible secret. Staged files were also reviewed for scope; no FamilyProps sources or unrelated local material are included.
- Docker is unavailable locally; the container recipe was not built or executed.

GitHub Actions checks the published commit on Python 3.12 and 3.13; consult the repository Actions page for authoritative remote execution status. No live model evaluation or GitHub Release was performed.

## Milestone 2 local verification â€” 2026-11-03

Windows, Python 3.13.14, official Anthropic SDK 2.4.0, package 0.2.0:

- Editable installation and `pip check`: successful.
- 68 tests passed, including all 22 existing tests unchanged, 26 official-SDK integration cases using an in-memory HTTP transport and 20 budget/configuration cases. Test sockets/DNS are blocked by an autouse fixture.
- Core package line coverage: 98.81%. This is infrastructure coverage, not evidence of model safety.
- Ruff lint and formatting checks: passed.
- Bandit on `src` excluding B101: no issues. Dependency audit of the updated lock: no known vulnerabilities at verification time.
- Credential-free fake execution, scenario validation and Anthropic dry-run smoke checks: successful. No real API client or model request is created by a dry run.
- New tests exposed SDK 2 compatibility details: temperature needs `extra_body` for the selected legacy model, and strict response validation must be reapplied when cloning SDK options. Both paths now have wire-level regression coverage.
- Regression cases verify truncated/malformed output, raw disclosure detection, grouped tool-result IDs, missing usage, unknown billing, global retry/request caps, retained timeout reservations, model mismatch, bounded Retry-After handling, CI blocking and pre-existing output-directory rejection.
- Credentials and HTTP error bodies are excluded from result artifacts. Only synthetic inputs and dummy test credentials are used in tests. No live evaluation results are committed.
- Docker remains unavailable locally, so the recipe remains unverified.

Remote CI status is reported separately against the exact published commit; this local record does not claim a future run has passed. No paid Claude calls, credit purchase, new repository or GitHub Release occurred during Milestone 2.

## Milestone 3 local verification â€” 2026-11-03

Windows, Python 3.13.14, package 0.3.0, unchanged Anthropic SDK/dependency lock:

- 135 tests passed with no warnings; core package line coverage 98.55%. Guard and budget modules have 100% line coverage. This does not prove safety or semantic correctness.
- All 68 Milestone 2 tests remain passing. AST comparison against commit `10ef4e6a9aa502a0c10e5cc61004853954a4b2d2` confirmed all 48 original top-level test/helper definitions are unchanged. The offline fixture was extended only to construct Windows asyncio's internal wake-up socket pair without enabling application network access.
- Added 67 cases covering exact authorization, altered arguments, authority spoofing, ambiguous grants, replay, positive legitimate task execution, output rejection, evidence provenance/conflicts, protected literals, false refusals, reviewer judgments/errors/cancellation/timeouts, comparison controls, concurrent/refund accounting and CLI error redaction.
- Ruff lint and formatting passed. Bandit (`src`, B101 excluded) reported no issues; the dependency audit reported no known vulnerabilities. `pip check` and editable installation succeeded.
- All three original scenario files remain unchanged. Schema validation, all three fake CLI modes, both controlled comparisons and an Anthropic guarded dry run succeeded. Raw fake artifacts remain ignored under `results/` and are not published as benchmark findings.
- Concurrent tests verify budget/request caps and exactly one refund under settlement replay. SDK tests verify mismatch retention before refund, sanitized unexpected exceptions, retry accounting and per-provider totals under a shared ledger.
- Policy, run schema and evaluator amendments are recorded in the decision log and methodology. A real paid reviewer adapter, semantic evaluator validation and live service qualification remain explicit gaps.
- Docker remains unavailable and unverified. No live model calls, credit purchases, new repository or GitHub Release were performed.

CI status for the exact pushed commit is reported separately; consult GitHub Actions for authoritative remote results.

## Milestone 4A local verification — 2026-11-03

Windows, Python 3.13.14, package 0.4.0, unchanged locked SDK/dependencies:

- 177 offline tests passed (all original 135 regression cases plus 42 new cases); package line coverage 97.26%. Original corpus fixtures are selected explicitly by old three-case regression tests; new tests exercise all 30 default assets. See integrity_audit.md for the migration and limitations.
- Editable installation, Ruff lint/format, pip check, Bandit and dependency-advisory auditing were executed. Bandit's three noncryptographic random-generator findings are narrowly annotated B311 with reproducible-scheduling/statistical reasons; no global B311 suppression was added. Vulnerability audit found no known vulnerabilities; unhashed dependency pins remain a supply-chain limitation.
- CLI validation found 30 scenarios, ten per category (16 attack-present, 14 benign). A full two-trial fake A/B/C paired run completed 180 episodes and controlled comparisons. These are infrastructure checks, not real LLM findings; raw fake artifacts remain ignored under results/.
- The six-case, two-trial real-reviewer qualification dry-run confirmed 36 planned A/B/C episodes, at most 120 requests and a $3 total estimated cap with zero API calls.
- Mocked official sync/async SDK transports exercise reviewer isolation, structured decisions, invalid responses, retry/timeout/cancellation, shared spending/request caps, failed-verdict usage and model identity checks. Additional tests reject mismatched ledgers and correctly classify a malformed replay after authorization consumption.
- Original pi-001, tm-001 and ce-001 source assets remain unchanged. Secret/confidential-data review covers tracked source/docs/scenarios; only synthetic canaries and dummy test credentials are present. No real evaluation data are published.
- Docker execution remains unverified. No paid calls, credit purchases, new repository or GitHub Release occurred.

Remote Python 3.12/3.13 CI is verified after pushing; the completion report links the exact commit/run. Local results alone do not assert remote CI success.

## Milestone 4B local verification — 2026-11-04

Windows, Python 3.13.14, package 0.4.1:

- 182 tests passed, retaining all 177 prior cases; package coverage 97.31%. Five new integration cases cover simulation attribution, frozen-field preservation, false-refusal diagnostics, exact regeneration, checked-in asset consistency and CLI errors.
- Rebuilt all five public SIMULATED artifacts byte-for-byte, verified SHA-256 digests and canonical LF output. The corpus remains 30 unchanged original scenarios; hypotheses and the frozen first-live protocol are unchanged. Public projections contain 180 comparison episodes plus three separate false-refusal probes.
- Chromium verification exercised both profiles, all category filters, 36 trace/configuration combinations, mobile overflow and an inert HTML/XSS regression probe, with no page/console errors or unexpected external requests. Desktop, mobile, overview and trace screenshots are original captures of the static page. No full accessibility audit is claimed.
- Ruff lint/format, JavaScript syntax, Bandit, dependency-advisory audit and pip check passed. Basic tracked-file credential scanning includes image bytes without printing matches. Only original synthetic fixture data and clearly named canaries appear in public projections; no live runs or private preflight artifacts are imported.
- Optional Playwright tooling is pinned in the Pages workflow and documented separately from runtime dependencies. Deployment uploads only site/ after offline tests/security checks, artifact verification and browser checks. Remote CI/deployment status is verified after push and linked in the completion report.
- No paid model calls, credit purchases, billing changes, changes to other repositories or GitHub Release occurred. Live Claude/reviewer behavior, actual latency/cost and broader empirical safety remain unverified. Docker remains unverified.

## Milestone 4C local verification — 2026-11-05

Windows, Python 3.13.14, package 0.4.2, unchanged locked dependencies:

- 205 offline tests passed (all prior 182 plus 23 cloud transport cases); package coverage 97.45%, new HTTP transport helper 100% line coverage. Socket/DNS blocking remains active.
- Tests cover explicit proxy routing for sync/async clients despite NO_PROXY=*, default isolation, SSL_CERT_FILE/SSL_CERT_DIR trust loading and verified TLS flags, invalid proxy/CA configuration, sanitized constructor exceptions, fixed API endpoint, dummy-placeholder Bearer headers, no log/trace leakage, CI gates and comparison rejection for differing transport modes. Existing retry, request, budget, concurrency and refund tests pass.
- Ruff lint/format, Bandit, pip check, dependency-advisory audit and tracked-file secret scan passed. No dependencies were added; editable installation succeeded.
- Rebuilt all five public SIMULATED assets and verified byte identity/SHA-256 against site/data. Scenario JSON, frozen labels/hypotheses, the first-live protocol and experimental results are unchanged.
- Cloud-mode dry-run of the one-request smoke plan made zero requests and confirmed a $0.5004 reservation within a $0.51 estimated cap. Dry-run does not establish proxy/CA/secret/account readiness.
- The local executor is Windows, not the published cloud worker. Current cloud environment_status observations and real proxy/header-injection/account compatibility remain unverified; require ready secret/runtime bindings and enforced destination policy before a separately authorized live smoke test.
- No Anthropic API requests, paid calls, credit purchases, billing changes or GitHub Release occurred. Remote Python 3.12/3.13 CI and Pages checks are verified after pushing and linked in the completion report.

## HTTP 400 diagnostics local verification — 2026-11-06

Windows, Python 3.13.14, package 0.4.3; unchanged locked Anthropic SDK 2.4.0/dependencies:

- 230 tests passed (all prior 205 plus 25 diagnostics/compatibility cases), package line coverage 97.60%, diagnostics helper 100%. Tests block application sockets/DNS and use dummy credentials/in-memory responses only.
- Primary and reviewer HTTP 400 tests cover documented Anthropic error envelopes and proxy-shaped JSON/HTML, strict allowlisted fields, invalid categories/content types/request IDs, credential echo redaction, unknown origin, no retries, retained reservations and fail-closed review. Non-assistant HTTP-200 error envelopes no longer enter raw model traces. Application logging remains active while pinned raw dependency HTTP loggers are suppressed.
- SDK source/type/wire tests verify version 2026-10-21, supported model literal, service_tier=standard_only, temperature=0 merged via extra_body, tool/message shapes and exactly one Bearer header. They do not establish remote acceptance or effective proxy credential substitution. The original 400 cause remains unresolved.
- Ruff lint/format, Bandit, pip check, tracked-file credential scan and dependency-advisory audit passed. Editable installation succeeded. No dependencies were added or upgraded.
- Frozen scenario files, hypotheses, first-live protocol, published SIMULATED results and dependency lock are unchanged against base 3d654118aac6fd2fe26a74005b411948a1dce9b0. Existing integration tests verify checked-in public artifact consistency; no standalone benchmark evaluation or Anthropic request was initiated.
- Saved cloud metadata provides no header-substitution specification. Actual binding compatibility and origin of the operator-reported 400 remain unverified; do not infer them from a ready binding or allowed domain. No secret values, raw live traces or experimental findings were published.
- No Anthropic calls, authentication probes, paid requests, retries of the earlier smoke, billing changes or GitHub Release occurred. Remote CI for the exact pushed commit is reported separately. A second diagnostic request still requires separate approval and cumulative accounting review.
