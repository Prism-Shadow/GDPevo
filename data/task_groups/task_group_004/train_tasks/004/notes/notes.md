# Churn Model Validation And Outreach Ranking Notes

## Data lineage

The task uses the ApexCloud Retention Operations churn exports exposed by the shared environment: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv`. The row counts are taken from the public export files, and the model-validation answer is computed from the training and validation exports using the deterministic reference churn procedure.

## Task definition

The visible request asks Analytics Ops to validate the churn export, report model validation metrics, and rank a fixed subset of candidate accounts by predicted churn probability. The deliverable is a JSON object matching the provided answer template, with percentages rounded to 1 decimal and probabilities rounded to 3 decimals.

## Scenario fit

This is a practical retention-operations scenario: the team needs confidence that the exported churn data is usable and needs a short outreach queue for customer-success action. The task combines dataset validation, coefficient sanity checking, candidate ranking, and operational action assignment.

## Material map

- `input/prompt.txt`: solver-facing business request and candidate subset.
- `input/payloads/answer_template.json`: required JSON shape.
- `output/answer.json`: deterministic reference answer.
- `eval/eval.sh`: exact-match business-result evaluator with an optional prediction path.
- Environment exports: source CSVs served by the local API.

## Solution and evaluation basis

The reference result uses 180 training rows, 60 validation rows, and 19 model features. The validation accuracy is 93.3%, placing it in the `90_plus` band, and the tenure coefficient direction is negative. The ranked top five are `acct_tandemworks`, `acct_northstar_finance`, `acct_northstar_retail`, `acct_globex_north`, and `acct_valence`. Evaluation awards eight weighted business-result checks for counts, accuracy, coefficient direction, ordering, probabilities, actions with reason codes, cohort checks, and neutral model-policy codes.

## Transfer design

This train task teaches solvers how to handle churn exports, verify feature counts, check whether tenure behaves in the expected business direction, rank a selected candidate cohort, and preserve probability precision. Those behaviors transfer to test tasks that use the same export family with different candidate subsets or longer training settings.

## Update record

Updated 2026-06-01 to add neutral `model_policy_codes` fields for model protocol, probability scale, deployment rule, and outreach mapping transfer.
