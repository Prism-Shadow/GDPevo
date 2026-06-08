# Executive Retention Watchlist Notes

## Data lineage

The task uses the ApexCloud Retention Operations environment for Q3 2026. Account identity and segment values come from `accounts.json`; current ARR comes from the latest posted billing snapshot on or before 2026-09-30; receivables come from `ar_aging.json` matched by exact legal customer name; support health comes from clean Q3 support tickets; NPS comes from valid Q3 survey responses; usage comes from monthly account metrics; open expansion pipeline comes from open opportunities with Q3 close dates.

## Task definition

The solver must create a CEO staff watchlist for ten named accounts and return the top seven by the shared retention risk score. Each row combines rank, risk score, risk level, primary action, current ARR, overdue balance, open expansion pipeline, net revenue exposure, next-touch due date, and reason-code set. The summary totals ARR at risk, overdue receivables, expansion offset, net exposure, and action counts.

## Scenario fit

The scenario fits an executive retention review because it elevates accounts where customer health, receivables, renewal timing, usage, and pipeline offsets interact. It is intentionally leadership-oriented and focuses on ordered action rather than raw operational diagnostics.

## Material map

`input/prompt.txt` contains the visible business request and dates. `input/payloads/answer_template.json` defines the required JSON shape. `output/answer.json` is the deterministic gold answer. `eval/eval.sh` accepts an optional prediction path and otherwise evaluates the included gold answer.

## Solution and evaluation basis

Ranking uses score descending, then current ARR descending, then account id ascending. Current ARR uses 2026-09-30 posted billing snapshots. Overdue balance is `61_90 + 90_plus` from exact legal-name A/R rows as of 2026-09-30. Open expansion excludes Closed Won and Closed Lost opportunities and uses close dates from 2026-07-01 through 2026-09-30. Net revenue exposure is current ARR plus overdue balance minus open expansion pipeline. The evaluator checks ordered business results, risk fields, finance values, reason-code sets, due dates, action map, summary totals, and action counts.

## Transfer design

This test transfers patterns from the training tasks: retention score ranking, overdue priority, billing ARR precedence, exact legal-name receivables matching, open-pipeline offsets, controlled enum labels, and executive due-date mapping.

## Construction record

Constructed for `task_group_004/test_tasks/005` only. No environment source files were copied into payloads. The evaluator uses ten weighted exact-match business-result checks and gives full credit to the included gold answer.

Updated 2026-06-01 to add neutral retention board `policy_codes` aligned with train_001/train_005 and consolidate scoring to 10 business-result points.

