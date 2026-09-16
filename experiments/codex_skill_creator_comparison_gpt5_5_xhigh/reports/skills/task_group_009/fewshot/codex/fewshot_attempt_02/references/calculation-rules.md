# Calculation Rules

Use this reference when auditing or extending `scripts/finance_ops_report.py`.

## API Datasets

Finance tasks use:

- `/api/finance/branches`: `branch_id`, `branch_name`, `region_id`, `region_name`.
- `/api/finance/period-map`: period labels such as `M1`, fiscal year, month number, month name.
- `/api/finance/accounts`: account to category mapping. Categories include `revenue`, `cogs`, `sga`, `allocations`, and `operating`.
- `/api/finance/records`: one row per branch/account with period values.

Compensation tasks use:

- `/api/compensation/rate-book`: current year, pay types, minimum weekly scale, title premiums, seniority bands, quarter weeks, and forecast rules.
- `/api/compensation/rosters`: ensemble employee rows with title, years of service, weekly overscale, quarter weeks, and combined-overscale flags.
- `/api/compensation/scenarios`: forecast case assumptions for Year + 1 and Year + 2.

Payroll tasks use:

- `/api/payroll/rate-book`: service rates, premiums, weekly guarantee, duration limits, and conflict thresholds.
- `/api/payroll/productions`: production schedules and musician roster assignments.

## Finance Reports

Calculate financial statement fields from account categories:

- `revenue`: sum all `revenue` accounts.
- `cogs`: sum all `cogs` accounts.
- `gross_margin`: `revenue - cogs`.
- `sga`: sum all `sga` accounts.
- `allocations`: sum all `allocations` accounts.
- `ebitda`: `gross_margin - sga - allocations`.
- `ebitda_margin`: `ebitda / revenue`.
- `arpu`: `revenue / active_customers`.
- `sales_per_labor_headcount`: `revenue / labor_headcount`.

For branch close tasks, use the memo's current and prior periods for monthly variance, the period map for fiscal year grouping, and the target branch's region for regional context. The regional context EBITDA rank is the target region's current-fiscal-year EBITDA rank among all regions. Rank branch facts descending by the requested metric, with stable ID ascending as the tie breaker.

For regional tasks, aggregate all branches with the requested `target_region_id`. The reconciliation variance is the rounded difference between the regional EBITDA total and the sum of branch-level EBITDA totals from the same records.

## Compensation Reports

For each roster row and quarter, use the row's `weeks_by_quarter`; do not assume fixed 13-week quarters.

Current-year pay types:

- `Minimum Weekly Scale`: `minimum_weekly_scale * weeks`.
- `Titled Position Premium`: `minimum_weekly_scale * title_premium_pct[title] * weeks`, unless `combined_overscale_includes_title` is true.
- `Seniority`: seniority weekly amount for the employee's years of service, multiplied by weeks.
- `Overscale`: `overscale_weekly * weeks`.

Count a combined-overscale employee when `combined_overscale_includes_title` is true. Count a partial-quarter employee when any row quarter week differs from the rate book's default for that quarter. Annual compensation totals should reconcile to the sum of rounded quarter totals.

Forecasts compound rate assumptions sequentially. Year + 1 uses the Year + 1 scenario factors. Year + 2 uses `(1 + Year + 1 growth) * (1 + Year + 2 growth)` for minimum scale, overscale, and seniority, and multiplies title premium multipliers the same way. Add one service year for Year + 1 and two service years for Year + 2 before selecting seniority bands. The largest growth pay type is the highest percent growth from current to Year + 2 pay-type total.

## Payroll Reports

Base service pay:

- `Performance`, `Audit`, and sound checks are paid per service from the rate book.
- `Rehearsal` is hourly with a 3-hour minimum call.
- `sound_check` is the reporting category for all sound-check service types.

Premiums are calculated on base service pay before vacation. Apply `principal_or_lead` once when either flag is true, plus `electronic` and `quartet` when those flags are true. Doubles are a separate category: first extra instrument uses `first_double`; each additional extra instrument uses `additional_double`.

Vacation is paid only when `vacation_eligible` is true and equals the vacation percent times base service pay plus premiums plus doubles. The weekly guarantee adjustment applies only to non-substitute players when base service pay is below `weekly_guarantee`.

For substitutes, add a substitute adjustment equal to 50% of assigned performance base pay. Include that adjustment in the performance category for premium-base purposes and also report it in `substitute_adjustment`.

Conflict flags:

- `REHEARSAL_EARLY_START`: a rehearsal begins before the threshold.
- `REHEARSAL_LATE_END`: a rehearsal ends after the threshold.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds its service limit.
- `SOUND_CHECK_DURATION_MISMATCH`: a sound-check duration differs from its named service limit.
