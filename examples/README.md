Run the commands in the root README from a repository checkout. Generated artifacts are intentionally excluded from Git.

`policy.json` is an explicitly trusted synthetic policy manifest for controlled offline comparisons. It grants no sensitive actions and protects the known synthetic canary. It is independent of tool/document content and evaluator ground truth. Positive sensitive-action permissions and incorrect-denial cases are exercised by the unit/integration probes; the example is not a production authorization configuration.
