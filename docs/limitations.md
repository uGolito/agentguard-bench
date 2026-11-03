# Limitations and threats to validity

- No live LLM benchmark results have been published yet. Scripted behavior is not model evidence.
- Three easy original cases provide no representativeness or statistical power. Twenty-seven scenarios remain unimplemented.
- Exact structured claims can be gamed; paraphrases are not recognized. No independent semantic evaluator exists.
- Baseline has no external authorization, output schema or evidence safeguards. Sensitive effects are simulated, including deliberately unauthorized proposals used in tests.
- Trusted authorization currently covers tool names, not argument scope. Provenance labels are recorded, not verified. Evidence semantics need dedicated evaluation in later milestones.
- No independent oversight, token accounting, live cost enforcement, retries or timeout management. No provider SDK or MCP transport yet.
- Scripts contain expected answers and ignore tool output; comparisons between fake configurations would be scientifically meaningless.
- Latency measures local infrastructure only; repeated fake trials are not independent samples of agent behavior.
- Dependency pinning aids reproduction but hardware, OS and timestamp differences remain. Docker availability and CI execution must be reported honestly in validation records.
- No claims of model safety, legal compliance, statistical significance or laboratory affiliation follow from this repository.
