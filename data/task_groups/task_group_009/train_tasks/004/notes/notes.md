# Notes for train_004

## English

This train task is a regional branch-reporting task derived from source example `E001`. It targets `REG-WEST` and requires the solver to use the shared Finance Ops API rather than stale offline branch lists.

The task definition is to build a compact regional management view with FY2024 and FY2025 rollups, growth, FY2025 EBITDA margin, sales per labor headcount, top and bottom branch EBITDA performers, and reconciliation variance. The visible materials are the prompt, environment access, request memo, and answer template.

Material map: `/api/finance/branches` identifies the branches in `REG-WEST`; `/api/finance/period-map` maps M-periods to fiscal years; `/api/finance/accounts` classifies records; `/api/finance/records` provides the monthly branch-account data.

The standard answer includes 7 scoring points with raw weights 2, 2, 3, 2, 2, 2, and 1. Evaluation checks the branch set, FY rollups, dashboard ratios, ranking facts, and zero reconciliation variance.

Transfer design: this is a formal train task that reinforces branch hierarchy source precedence, account category rollups, period mapping, and descending EBITDA ranking. These conventions anchor `test_001` and `test_004`.
