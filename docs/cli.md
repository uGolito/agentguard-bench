# CLI reference

Run from the checkout root. All output directories must be new. Use agentguard --help, run --help and paired-run --help for exact defaults.

## Offline commands

```bash
agentguard list-scenarios
agentguard validate-scenarios
agentguard run --mode baseline --provider fake --output results/a
agentguard run --mode guarded --provider fake --policy examples/policy.json --output results/b
agentguard run --mode guarded_oversight --provider fake --policy examples/policy.json --reviewer fake-allow --output results/c
agentguard paired-run --policy examples/policy.json --with-oversight --reviewer fake-allow --trials 2 --order-seed 1729 --max-requests 300 --output results/paired
agentguard compare --baseline results/a/run.json --candidate results/b/run.json
agentguard report --run results/b/run.json
```

Default corpus: 30 cases. --scenarios PATH selects another corpus; run supports --category prompt_injection|tool_manipulation|conflicting_evidence. Repeat --scenario-id ID for a subset. Unknown/filtered IDs fail. --trials repeats each case; --order-seed controls scheduling only. Anthropic --model-seed is rejected as unsupported; fake repetitions are deterministic.

Guarded modes require --policy; oversight requires --reviewer fake-allow|fake-deny|anthropic. Real review requires primary anthropic, supported priced model, positive cap and explicit live opt-in. Individual run exposes --reviewer-model, --reviewer-max-tokens and --reviewer-timeout. Paired-run uses recorded reviewer model/output defaults.

## Paired design and limits

Baseline/guarded are mandatory; --with-oversight adds C. Mode order rotates within scenario/trial; scenarios are shuffled from the order seed. Every episode has isolated context/data. Each mode has identical --max-requests and --max-cost across all episodes, shared by its primary/reviewer. --max-total-cost must cover the sum of per-mode caps, including previews. Fake cost defaults to zero.

--max-steps applies per episode. --max-tokens, --timeout, --max-retries and --reviewer-timeout bound work. Every SDK attempt counts; SDK automatic retries are disabled. --stop-on-error stops qualification on technical/reviewer failures, saves partial artifacts and exits 2. Partial designs cannot produce paired conclusions. Ordinary refusals/blocked answers remain outcomes.

## Live gate and artifacts

--dry-run constructs no clients, needs no credentials and makes zero requests. Live execution requires --allow-live, a positive cap, exact priced model and ANTHROPIC_API_KEY in the environment. CI blocks live clients. Never run paid commands without separate approval. See first_live_experiment.md for the complete proposed plan and cost_controls.md for estimates.

run.json preserves configurations/episodes, traces.jsonl finalized events, journal.jsonl flushed events during execution, metrics.csv/analysis.json/report.md summaries. Paired roots add experiment.json and complete-design comparisons. Injection metadata distinguishes fake/mocked clients; it is not cryptographic provenance. Results are ignored by Git and never automatically published. Journals do not promise automatic recovery. Inspect partial data before proposing any retry.

## Public SIMULATED demonstration

`agentguard demo --output results/demo` builds the fixed 30-case corpus using fake providers only. It includes reference/adversarial script profiles across A/B/C plus a separate three-case false-refusal diagnostic. It has no provider, live-import or credential option. Output directories must be new. Run `python scripts/verify_demo.py results/demo site/data` to verify byte-for-byte reproduction and file hashes. See demo.md for static preview and artifact interpretation.
