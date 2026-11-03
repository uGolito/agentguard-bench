# First live qualification — proposed, not executed

This is interface qualification, not a powered hypothesis test. Separate explicit approval is required before paid execution. No live results have been published.

## Frozen candidate design

Freeze the published M4A commit, dependency lock, scenario/policy hashes and endpoints. Review the policy independently. Use claude-haiku-4-5-20251001, temperature 0, primary output 512, reviewer output 256, four agent steps, two trials and order seed 1729. Never tune labels after observing results.

Select pi-004 (canary attack), pi-010 (authorized email), tm-002 (benign malformed data), tm-007 (unauthorized update instruction), ce-003 (missing timestamp), ce-010 (agreeing evidence and authorized email). These cover all categories and positive controls, but cannot support broad safety conclusions.

A/B: 24 episodes. Assuming two primary turns per ordinary case and three per authorized-action case, expect 56 primary requests. Optional C adds 28 primary and four review requests: about 88 total. Actual trajectories may differ. Each mode is capped at 40 attempts including reviews/retries, $1 estimated spending, zero retries, and 30-second transport/reviewer timeouts. Overall attempt ceilings: 80 A/B, 120 A/B/C.

Planning arithmetic at 2,000 input/512 output tokens per primary request and 500 input/256 output per review: about $0.26 A/B, $0.40 A/B/C before taxes. These are unmeasured assumptions. Conservative estimator caps: **$2 A/B**, **$3 A/B/C**. Each primary attempt needs $0.5032 headroom; each review $0.5016. Unknown bills can stop the experiment early. Recheck official prices before approval; see cost_controls.md.

## Exact commands

This preview needs no key and makes zero calls:

```bash
agentguard paired-run --provider anthropic --model claude-haiku-4-5-20251001 --policy examples/policy.json --scenario-id pi-004 --scenario-id pi-010 --scenario-id tm-002 --scenario-id tm-007 --scenario-id ce-003 --scenario-id ce-010 --trials 2 --order-seed 1729 --max-steps 4 --max-requests 40 --max-cost 1 --max-total-cost 2 --max-tokens 512 --max-retries 0 --timeout 30 --reviewer-timeout 30 --stop-on-error --dry-run
```

Only after separate paid approval, supply ANTHROPIC_API_KEY through the environment using a secret manager. Never paste it into commands/logs. The application does not load .env files. For the approved A/B experiment, replace --dry-run with --allow-live --output results/live-qualification-ab.

For an approved A/B/C design, also add --with-oversight --reviewer anthropic, replace --max-total-cost 2 with --max-total-cost 3 and use results/live-qualification-abc. These are new complete runs with reset budgets: approving both separate runs would authorize $5 total estimated caps. Prefer one design. Fake review cannot qualify H4.

## Outputs, stopping and verification

Expect root journal.jsonl, experiment.json and complete-design baseline-vs-guarded.json (plus C comparison). Each mode has run.json, traces.jsonl, metrics.csv, report.md and analysis.json. No model outcome is prescribed.

--stop-on-error stops on technical/accounting/format errors or reviewer failure, saves partial outcomes and exits 2 without paired conclusions. Budget/request limits also stop qualification. Normal denials, blocked answers and step-limit outcomes remain scored observations. Manually stop for suspected key disclosure, missing journal records or unexpected effects. Do not automatically retry unknown bills or treat a partial run as complete.

Verify the scenario/trial/mode schedule, model identity, usage completeness, all tool effects/reviews, settled reservations and primary/reviewer charges. Compare completed arms with agentguard compare; inspect provider billing separately. Preserve failures and raw data privately and sanitize before publication. Journals flush before dispatch but do not provide transactional recovery.

## Rollback

Preserve failed data, document the issue, fix code in a new commit and obtain approval for any additional paid work. Revert code normally without rewriting public history. Revoke compromised keys. Tools have only synthetic effects; incurred API charges cannot be undone. No experiment is executed by this plan.
