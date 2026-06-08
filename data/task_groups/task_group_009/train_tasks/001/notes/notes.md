# Notes for train_001

## English

This task is derived from `SCN_009_finance_operational_modeling_management_reporting`, especially source example `E001`. It asks for a branch close package for `BR-004` using the shared Crescent Finance Ops environment. Solver-visible inputs are `prompt.txt`, `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`.

The task fits the scenario because it converts raw monthly branch records into a repeatable management-reporting view. The solver must use the Finance Ops period map, account categories, branch hierarchy, and financial records. The local memo names the target and close periods but does not replace the environment source of truth.

Material map: `/api/finance/period-map` defines the M-period fiscal-year mapping; `/api/finance/accounts` defines account categories; `/api/finance/branches` defines the region membership; `/api/finance/records` contains the branch-account wide monthly data.

The standard answer calculates revenue, COGS, gross margin, SG&A, allocations, and EBITDA from the account records; compares M24 to M23 for revenue variance; rolls FY2025 and FY2024 periods; computes EBITDA margin, ARPU, and sales per labor headcount; and ranks branches and regions from the shared data. The seven scoring points have raw weights 1, 3, 2, 3, 2, 2, and 2. Exact matching is done through `eval/config.json`.

Transfer value: blind solving and answer comparison should teach the period convention, source precedence, account rollup logic, and ranking directions needed later in branch test tasks. Common pitfalls are using the wrong fiscal year for M-periods, treating operating counts like expenses, excluding a branch from the region, or ranking growth in ascending order.

Construction record: created by Codex on 2026-06-02; generated from fixed-seed environment data and task-specific branch close brief.

