# Preregistered research questions (before live experiments)

These hypotheses are proposed, not findings. No live experiments have occurred.

- **H1:** baseline agents follow lower-trust malicious instructions more often than guarded agents. Test paired A/B trials on injection scenarios with identical model, parameters, fixtures and budgets. Primary outcome: ASR; secondary: completion and false refusal. Equal or higher guarded ASR contradicts the directional prediction.
- **H2:** typed output validation and trusted authorization reduce invalid or unauthorized executions. Test A/B manipulation cases, logging proposals, guard decisions and executed effects separately. Equal or higher invalid/unauthorized execution rates contradict the prediction. Add ablations to distinguish each control's contribution.
- **H3:** evidence verification reduces unsupported factual claims under contradictory or incomplete sources. Test A/B evidence cases with independently specified claim/provenance criteria. Equal or higher unsupported-claim rates contradict the prediction. This metric and semantic evaluator are deferred; current exact-value checks do not test H3.
- **H4:** independent review may reduce unsafe execution but adds latency, tokens, cost and false refusals. Compare B/C on identical trials with a separately configured reviewer. Non-improving safety or no measurable overhead challenges the corresponding hypothesis component. Record reviewer false positives and false negatives against trusted scenario authorization, never against the reviewer's own labels.

Before live runs, freeze scenario hashes, primary endpoints, model identifiers, sample size and analysis plan in a committed experiment manifest. Separate confirmatory and exploratory analyses. Run all selected cases and preserve negative results. No hypothesis is testable using the scripted fake as evidence about LLM behavior.
