# Churn Model Deployment Shortlist Notes

## English

### Data lineage

This task uses the ApexCloud Retention Operations churn exports from the shared environment: `churn_train.csv`, `churn_validation.csv`, and `churn_candidates.csv`. The account segment check for the shortlisted cohort is grounded in `accounts.json`; the shortlist itself is produced from the churn candidate export.

### Task definition

The solver is asked to validate the churn model export and return a deployment-oriented report plus the top six accounts from a fixed candidate subset. The visible prompt names the API endpoints and candidate IDs but does not disclose the construction-only model settings, encodings, or training procedure.

### Scenario fit

The scenario fits Analytics Ops and enterprise renewal workflows: the validation result gives model readiness context, while the ordered shortlist gives the renewal team a compact account queue with probability, risk, action, and reason labels.

### Material map

- `input/prompt.txt`: solver-visible business request and candidate list.
- `input/payloads/answer_template.json`: required JSON shape and enum examples.
- `output/answer.json`: deterministic reference answer.
- `eval/eval.sh`: exact-match evaluator for the nine weighted business-result checks.

### Solution and evaluation basis

The deterministic test-task churn procedure uses all 19 exported feature columns, 180 training rows, and 60 validation rows. Validation accuracy is 93.3%, the accuracy band is `90_plus`, and the fitted tenure coefficient is negative. The top six candidates by predicted churn probability are `acct_bayside_bio`, `acct_helios`, `acct_valence`, `acct_westport`, `acct_apexia`, and `acct_southridge`. Probabilities are rounded to three decimals, percentages to one decimal, and cohort checks are based on the same top-six shortlist.

### Transfer design

This task transfers the churn-export handling from the train anchor while changing the candidate subset, required list length, top-level schema, and deployment-readiness fields. It also adds risk levels and enterprise-or-strategic cohort counting so solvers must combine the model output with customer account context.

### Construction record

Created the five required task files under `test_tasks/004/` only. The evaluator defaults to the task's own answer and accepts an optional prediction JSON path as its first argument.

