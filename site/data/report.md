# SIMULATED AgentGuard demonstration

SIMULATED â€” deterministic fake-provider infrastructure demonstration; no live findings.

## SIMULATED reference

### SIMULATED guarded
- attack_success_rate: 0/16
- task_completion_rate: 30/30
- unauthorized_action_rate: 0/30
- false_refusal_rate: 0/30
- model_disclosure_rate: 0/30
- delivered_disclosure_rate: 0/30
- reviewer_false_positive_rate: 0/0
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 0/16
- runtime_attack_success_rate: 0/16
- unsafe_proposal_episode_rate: 0/30
- delivered_wrong_claim_rate: 0/30
- Blocked actions: 0

### SIMULATED guarded_oversight
- attack_success_rate: 0/16
- task_completion_rate: 30/30
- unauthorized_action_rate: 0/30
- false_refusal_rate: 0/30
- model_disclosure_rate: 0/30
- delivered_disclosure_rate: 0/30
- reviewer_false_positive_rate: 0/3
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 0/16
- runtime_attack_success_rate: 0/16
- unsafe_proposal_episode_rate: 0/30
- delivered_wrong_claim_rate: 0/30
- Blocked actions: 0

### SIMULATED baseline
- attack_success_rate: 0/16
- task_completion_rate: 30/30
- unauthorized_action_rate: 0/30
- false_refusal_rate: 0/30
- model_disclosure_rate: 0/30
- delivered_disclosure_rate: 0/30
- reviewer_false_positive_rate: 0/0
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 0/16
- runtime_attack_success_rate: 0/16
- unsafe_proposal_episode_rate: 0/30
- delivered_wrong_claim_rate: 0/30
- Blocked actions: 0

## SIMULATED adversarial

### SIMULATED guarded
- attack_success_rate: 1/16
- task_completion_rate: 28/30
- unauthorized_action_rate: 0/30
- false_refusal_rate: 1/30
- model_disclosure_rate: 1/30
- delivered_disclosure_rate: 0/30
- reviewer_false_positive_rate: 0/0
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 16/16
- runtime_attack_success_rate: 0/16
- unsafe_proposal_episode_rate: 16/30
- delivered_wrong_claim_rate: 0/30
- Blocked actions: 16

### SIMULATED guarded_oversight
- attack_success_rate: 1/16
- task_completion_rate: 28/30
- unauthorized_action_rate: 0/30
- false_refusal_rate: 1/30
- model_disclosure_rate: 1/30
- delivered_disclosure_rate: 0/30
- reviewer_false_positive_rate: 0/3
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 16/16
- runtime_attack_success_rate: 0/16
- unsafe_proposal_episode_rate: 16/30
- delivered_wrong_claim_rate: 0/30
- Blocked actions: 16

### SIMULATED baseline
- attack_success_rate: 16/16
- task_completion_rate: 20/30
- unauthorized_action_rate: 16/30
- false_refusal_rate: 0/30
- model_disclosure_rate: 1/30
- delivered_disclosure_rate: 1/30
- reviewer_false_positive_rate: 0/0
- reviewer_false_negative_rate: 0/0
- model_attack_success_rate: 16/16
- runtime_attack_success_rate: 16/16
- unsafe_proposal_episode_rate: 16/30
- delivered_wrong_claim_rate: 1/30
- Blocked actions: 0

## Interpretation

Scripts define behavior and ignore tool content. These differences demonstrate runtime enforcement, not model robustness. No informative confidence interval, model latency or API tokens apply. API cost is exactly $0. No live Claude benchmark results are included.
