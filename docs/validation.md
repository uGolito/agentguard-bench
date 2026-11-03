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

## Milestone 2 local verification — 2026-11-03

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
