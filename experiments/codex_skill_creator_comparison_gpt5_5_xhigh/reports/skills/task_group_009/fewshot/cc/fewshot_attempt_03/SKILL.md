---
name: crescent-finance-ops
description: Solve Crescent Arts Collective Finance Ops JSON reports for branch close, regional management, compensation, payroll, and forecast tasks. Use when a prompt mentions the Crescent Finance Ops API, `payloads/environment_access.json`, `payloads/request_memo.json`, or asks for strict JSON built from `/api/finance`, `/api/compensation`, or `/api/payroll`.
---

# Crescent Finance Ops

Use the bundled solver first:

`python scripts/solve_crescent_ops.py <task-input-dir>`

The script reads the request memo, answer template, and environment access payload, fetches only the needed API endpoints, and prints the final JSON to stdout. If the payload base URL is a placeholder, it falls back to `environment_access.md` or the task environment URL.

## Workflow

1. Locate the task input directory that contains `payloads/`.
2. Run the solver script.
3. If you must reason manually, follow the same report-specific formulas below and keep the output schema exactly aligned to the template.

## Report Rules

- Branch close: aggregate finance records by account category and period. Compute gross margin as revenue minus COGS, then EBITDA as gross margin minus SG&A and allocations. Use the close period for the month-over-month variance and the fiscal year containing that period for the year-over-year block, region context, and branch rankings.
- Regional finance: aggregate only the branches in the target region. Use ascending branch IDs, compute EBITDA margin as EBITDA divided by revenue, compute sales per labor headcount from summed labor headcount, and rank regions by current-year EBITDA.
- Current compensation: use roster quarter weeks, not a fixed 13-week quarter. Multiply weekly pay components by each roster row's weeks by quarter. Treat combined overscale as title-inclusive, count partial-quarter employees when any quarter differs from the standard quarter map, and keep pay-type totals in rate-book order.
- Compensation forecast: apply scenario growth cumulatively from current to Year + 1 and then Year + 2, add years of service before assigning seniority bands, and choose the largest-growth pay type by relative Year + 2 growth.
- Payroll review: pay rehearsal at hourly rate with a three-hour minimum, pay other services per service, apply role and doubles premiums to service pay, add vacation on eligible workers, add guarantee adjustments only for regular players below the weekly guarantee, and flag rehearsal timing or sound-check duration conflicts from the schedule.

## Output Discipline

- Preserve the template's key names and nesting.
- Round currency to 2 decimals and ratios or percentages to 4 decimals.
- Sort branch IDs, per-musician rows, and conflict flags as required by the template.
- Prefer the script output over hand-built JSON.

