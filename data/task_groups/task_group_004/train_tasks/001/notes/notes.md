# Notes
## Data Lineage

This task is built from the ApexCloud Retention Operations environment in `task_group_004/env`. The answer uses the public API data surfaces represented by accounts, account metrics, support tickets, NPS responses, billing snapshots, and A/R aging. The assessment date is 2026-06-30 and the operating period is 2026-04-01 through 2026-06-30.

## Task Definition

The solver must review eight North America account IDs and return the top five accounts by renewal risk, including score, level, primary action, ARR, latest valid NPS, clean ticket count, overdue balance, reason codes, portfolio summary, and model checks.

## Scenario Fit

The scenario fits a VP Customer Success workflow before a retention standup. It requires combining customer health, finance, support, and renewal context into a short action queue.

## Material Map

`prompt.txt` gives the business request and output contract. `answer_template.json` shows the JSON shape and controlled enums. `answer.json` is the deterministic gold answer. `eval.sh` scores exact business outcomes and accepts an optional prediction path.

## Solution And Evaluation Basis

Current ARR is taken from Q2 posted billing snapshots on 2026-06-30. Clean tickets exclude spam, duplicates, and cancelled records. Latest NPS ignores retracted responses and uses the last valid response in the Q2 period. Overdue balance is the 61-90 plus 90-plus A/R buckets at 2026-06-30. Risk ranking uses the shared retention-risk business rules, then sorts by score, current ARR, and account ID.

## Transfer Design

This train task teaches billing ARR precedence, clean-ticket filtering, retracted-NPS handling, overdue collections priority, tenure risk direction, and controlled action enums. These conventions transfer to later strategic save-plan and executive watchlist tasks while leaving account-specific exploration necessary.
