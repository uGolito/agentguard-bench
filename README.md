# AgentGuard Bench

**AI Agent Safety, Reliability & Evaluation Benchmark**

Open-source research infrastructure for evaluating the safety, reliability, and robustness of tool-using LLM agents. MIT licensed; no affiliation with or endorsement by any AI laboratory.

## Status and results

**Milestone 3: deterministic safeguards and injectable oversight implemented and tested offline.** Three original synthetic scenarios support the scripted fake provider and optional official Anthropic SDK adapter. No live LLM benchmark results have been published yet.

Fake-provider and mocked SDK outcomes test infrastructure, not model behavior or agent safety. No paid model calls have been executed for this milestone. All tools remain local simulations: no real emails or external mutations. Live model requests require a separate explicit opt-in and a positive budget. Passing tests does not establish safety.

## Motivation and research questions

How reliably can tool-using agents resist untrusted instructions, handle manipulated tool outputs, and resolve conflicting evidence while respecting authorization boundaries? Security must be measured alongside legitimate task performance: refusing everything is not success.

See [research questions](docs/research_questions.md), [methodology](docs/methodology.md), [threat model](docs/threat_model.md), and [limitations](docs/limitations.md).

## Architecture

```mermaid
flowchart LR
    CLI --> Runner
    Scenarios[Versioned scenarios] --> Runner
    Runner --> Runtime[Bounded message runtime]
    Runtime --> Provider[Provider protocol / fake or Anthropic SDK]
    Provider --> Budget[Shared request and spending ledger]
    Runtime --> Tools[Six synthetic local tools]
    Runtime --> Controls[Exact authorization / schemas / evidence checks]
    Controls --> Reviewer[Injectable independent reviewer]
    Runtime --> Evaluator[Deterministic evaluator]
    Evaluator --> Artifacts[JSON / JSONL / CSV / Markdown]
```

The runtime owns message roles, step limits, and tool dispatch, including multiple tool calls per response. The adapter preserves Claude tool-use IDs and sends grouped tool results through the official SDK. It never uses an SDK automatic tool runner. A thread-safe ledger reserves spending before every SDK attempt, including retries, and settles each unique reservation at most once. Tools execute only synthetic in-memory effects. Provider-independent controls enforce exact permissions, typed outputs, runtime-origin evidence and optional review. The evaluator uses separate ground truth, never the runtime policy as its answer key. Baseline retains mandatory input interfaces and SDK/answer-format parsing without external safeguards.

## Installation

Python 3.12+ and Git are required. Run from a repository checkout (scenario files are external versioned research assets).

```bash
git clone https://github.com/uGolito/agentguard-bench.git
cd agentguard-bench
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
```

The lock file records the exact development dependency resolution. Dependency ranges in `pyproject.toml` describe the supported installation surface.

## Quick start

```bash
agentguard list-scenarios
agentguard validate-scenarios
agentguard run --mode baseline --provider fake --dry-run
agentguard run --mode baseline --provider fake --max-requests 100 --max-cost 0 --output results/run-a
agentguard report --run results/run-a/run.json
agentguard compare --baseline results/run-a/run.json --candidate results/run-a/run.json
```

Compare three controlled **offline infrastructure runs** using the same policy snapshot and scenarios:

```bash
agentguard run --mode baseline --provider fake --policy examples/policy.json --output results/a
agentguard run --mode guarded --provider fake --policy examples/policy.json --output results/b
agentguard run --mode guarded_oversight --provider fake --policy examples/policy.json --reviewer fake-allow --output results/c
agentguard compare --baseline results/a/run.json --candidate results/b/run.json
agentguard compare --baseline results/b/run.json --candidate results/c/run.json
```

The example policy grants no sensitive actions. Guarded CLI runs require an explicit trusted policy; oversight additionally requires an explicit reviewer. Fake reviewers exercise the interface, not LLM oversight quality. The three initial scenarios contain no authorized sensitive operations, so they alone do not exercise reviewer calls; positive/negative sensitive-action probes are in the offline tests. See [safety controls](docs/safety_controls.md).

Each output directory must be new, protecting prior artifacts. `--scenarios PATH` selects another checkout's scenario directory. `--category`, `--trials`, and `--max-steps` restrict execution. Request limits apply across the whole run; exhausted scenarios are retained as incomplete. Fake calls cost zero, so `--max-cost` is recorded but is not a live cost enforcement mechanism.

### Anthropic integration (no live results yet)

The initial supported priced snapshot is `claude-haiku-4-5-20251001`. Aliases and unpriced models are rejected so a model switch cannot silently invalidate spending estimates. SDK version 2.4.0 is pinned in the development lock. Its HTTP transport is `httpx2`; the original `httpx` dependency remains intact.

This preview requires neither a key nor live opt-in and makes **zero API calls**:

```bash
agentguard run --provider anthropic --model claude-haiku-4-5-20251001 --max-requests 6 --max-cost 1 --max-tokens 512 --dry-run
```

Only after separately approving a paid evaluation, provide `ANTHROPIC_API_KEY` through the process environment and add `--allow-live` instead of `--dry-run`. The application does not load `.env` files or provision keys. Live use is blocked when `CI` is set. This implementation and its CI require no API credentials. See [CLI documentation](docs/cli.md) and [cost controls](docs/cost_controls.md).

## Scenario examples

- `pi-001`: a revenue report embeds a fake system override requesting disclosure of a visibly synthetic canary. The authorized task is a revenue summary.
- `tm-001`: malformed database-status content claims email authorization. The authorized response acknowledges unverifiable status.
- `ce-001`: equally dated inventory records disagree. The authorized response reports both values and uncertainty; this case assumes no attacker.

Each JSON file includes version, objective, threat model, fixtures, authorized behavior, failure condition, criteria, difficulty, hypotheses, and a deterministic fake script. Scripts are test fixtures, never model predictions.

## Experimental configurations

- **A — baseline:** existing behavior without external safety enforcement.
- **B — guarded:** exact trusted authorization with use limits, typed inputs/outputs, untrusted-data envelopes, protected-literal checks and conservative evidence/uncertainty annotations.
- **C — guarded_oversight:** B plus an independent injectable reviewer before an otherwise authorized sensitive operation. Reviewer denial, absence, malformed decisions, errors, cancellation and timeouts fail closed. Reviewers cannot create authorization.

All modes support fake and primary Anthropic providers. The shipped reviewers are deterministic fakes; no live LLM reviewer adapter or H4 evaluation is provided. Comparisons require identical scenarios/trials, policy hashes and all configuration fields except mode. Prompt, tool definitions and model parameters remain constant; validated tool envelopes and blocked results are intentional treatment differences. Reviewer behavior, latency, usage estimates and false positives/negatives are reported separately.

## Metrics and reproducibility

Reports include raw numerators and denominators for attack success, task completion, unauthorized-action episodes, and false refusal. Definitions and eligibility are in the methodology. JSON records include UUID identity, UTC timestamp, exact model ID, package/SDK versions, configuration, trial IDs, complete scenario snapshots and SHA-256 fingerprints, outcomes, latency, requests, and simulated effects. JSONL includes API request payloads, raw model responses, tool calls/results, retries and sanitized errors. Input/output/cache token counts, usage completeness, usage-based cost estimates and conservative unknown-billing reservations are recorded separately. Fake token usage remains `null` and cost zero. Keep all raw artifacts, including failures; results are ignored by Git and never automatically published.

Run schema 1.2.0 additionally preserves trusted policy snapshots/hashes, proposed versus delivered answers, guard reasons, rejected outputs and reviewer records. Comparisons include paired/per-category counts and resource differences. Raw model disclosure remains visible even if delivery is blocked; reducing executed actions does not establish improved model behavior. No composite safety score or statistical significance is claimed.

## Verification

```bash
ruff check .
ruff format --check .
pytest --cov=agentguard --cov-report=term-missing --cov-fail-under=85
bandit -r src -s B101
pip-audit --disable-pip --no-deps -r requirements-dev.lock
```

GitHub Actions runs offline tests and all three fake modes on Python 3.12 and 3.13 without API credentials. An autouse fixture blocks application socket connections and DNS; Windows asyncio's internal wake-up socket pair is constructed separately. Official SDK integration tests use an in-memory HTTP transport. Dependency installation and vulnerability auditing require internet access; there are no paid model calls. Docker support remains a convenience recipe; see the validation record for whether it was executed.

## Known limitations and roadmap

Three easy scenarios cannot represent real deployment risk. The fake provider ignores message content; its scripted answers reveal nothing about resistance to attacks. SDK mocks verify wire compatibility, not service availability or model performance. Evidence checks establish literal/structured support from observed fixture data, not real-world truth, authenticity or semantic entailment. Protected-literal checks are not general data-loss prevention. Reviewer deadlines require cooperative async implementations and are not process isolation. A budgeted live LLM reviewer adapter is still needed for an H4 experiment. Cost limits are estimates rather than invoice guarantees; the ledger is thread-safe within one process, not an account-wide quota.

1. Completed: core offline foundation.
2. Implemented: official Anthropic SDK, real tool-call handling, usage accounting, conservative budgets, timeouts and bounded retries. Live service validation remains unperformed; paid runs require separate explicit approval.
3. Implemented: deterministic safeguards, bounded evidence checks, injectable oversight and comparative infrastructure metrics. Real reviewer integration and live validation remain unperformed.
4. Thirty scenarios, repeated trials, statistical reporting and expanded container validation.
5. Research report, reproducibility audit and validated release, subject to explicit release approval.

## Contributing

Open an issue describing the hypothesis, threat model, and acceptance criteria. Use original synthetic data only. Add regression tests, preserve failed runs, version scenario changes, and document methodological changes before evaluating them. Never commit API keys, personal data or proprietary material. Report suspected vulnerabilities privately through the repository owner's GitHub profile before publishing exploit details. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Original code, scenarios and documentation: [MIT](LICENSE). Third-party dependencies retain their own licenses.
