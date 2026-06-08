# High-Touch Retention Operations Board Notes

## Data lineage

The task uses the ApexCloud Retention Operations environment for Q2 2026. Account identity and segment values come from `accounts.json`; current ARR comes from the latest posted billing snapshot on or before 2026-06-30; receivables come from `ar_aging.json` matched by exact legal customer name; support health comes from clean Q2 support tickets; NPS comes from valid Q2 survey responses; usage comes from monthly account metrics; expansion pipeline comes from open opportunities with Q2 close dates.

## Task definition

The solver must create an action board for eight named high-touch accounts as of 2026-06-30. The board combines retention risk level, primary action, billing ARR, Q2 open expansion pipeline, overdue receivables, next-touch due date, and reason-code sets. It also returns segment counts and portfolio-level exposure totals.

## Scenario fit

The scenario fits CS leadership operating-review work: it requires reconciling financial exposure, service deterioration, renewal timing, NPS movement, usage weakness, and expansion offsets before deciding where leadership attention should go.

## Material map

`input/prompt.txt` gives the visible business request. `input/payloads/answer_template.json` provides the required JSON shape. `output/answer.json` is the deterministic gold answer. `eval/eval.sh` compares a submitted prediction, or the gold answer by default, against exact business-result checks.

## Solution and evaluation basis

Ranking follows the shared retention risk score order. Current ARR uses billing snapshot values as of 2026-06-30. Overdue balance is `61_90 + 90_plus` from A/R aging. Q2 open expansion pipeline excludes Closed Won and Closed Lost opportunities and uses close dates from 2026-04-01 through 2026-06-30. `arr_at_risk` sums current ARR for medium, high, and critical accounts; `net_revenue_exposure` subtracts all Q2 open expansion pipeline from that at-risk ARR total.

## Transfer design

This task transfers the same conventions needed by executive watchlist tasks: retention risk ranking, action priority, billing ARR precedence, A/R legal-name matching, open-pipeline offsets, and action due-date mapping.

## Construction record

Constructed for `task_group_004/train_tasks/005` only. No environment source files were copied into payloads. The evaluator uses nine weighted business-result checks and gives full credit to the included gold answer.

Updated 2026-06-01 to add neutral retention board `policy_codes`, including board sorting, exposure formula, and calendar policy codes for train-to-test transfer.

