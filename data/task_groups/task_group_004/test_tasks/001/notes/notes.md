# Strategic Renewal Save Plan Notes

## English

### Data Lineage
The task uses the ApexCloud Retention Operations API backed by the task_group_004 environment data. Account profile data comes from `accounts.json`; billing ARR comes from posted billing snapshots; support quality comes from `support_tickets.json`; NPS comes from `nps_responses.json`; usage comes from `account_metrics.json`; and overdue receivables come from `ar_aging.json`.

### Task Definition
The solver must review 10 named strategic/enterprise renewal-cycle accounts as of 2026-09-30, rank them by the shared retention-risk policy, and return the top 6 save-plan accounts with operational metrics, actions, and portfolio totals.

### Scenario Fit
This fits a CRO save-plan workflow because it combines renewal timing, collections exposure, support health, customer sentiment, usage trajectory, and ARR size into a single intervention queue.

### Material Map
- `input/prompt.txt`: solver-facing business request and output constraints.
- `input/payloads/answer_template.json`: JSON response shape.
- `output/answer.json`: canonical expected result.
- `eval/eval.sh`: exact-match business-result evaluator with optional prediction path.

### Solution And Evaluation Basis
The canonical answer uses 2026-09-30 posted billing ARR, Q3 2026 clean support tickets, Q3 valid NPS responses, Q3 account usage, and A/R aging as of 2026-09-30. The six selected accounts are ordered by risk score descending, then current ARR descending, then account_id ascending. The evaluator gives weighted credit for ordered accounts, scores and levels, actions, ARR and ARR-at-risk, support and NPS metrics, overdue amounts, summary action counts, and quality checks.

### Transfer Design
The task transfers patterns from the retention scoring and action-priority training tasks: use posted billing as the ARR source of truth, filter invalid support/NPS records, apply the shared risk/action policy, and summarize the portfolio without exposing the full formula in the prompt.
