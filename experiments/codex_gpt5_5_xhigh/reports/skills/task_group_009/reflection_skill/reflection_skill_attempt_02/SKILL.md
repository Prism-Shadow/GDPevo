---
name: crescent-finance-ops-reporting
description: Produce Crescent Finance Ops reporting JSON for task_group_009-style requests. Use when the task provides prompt.txt plus environment_access.json, request_memo.json, and answer_template.json for Crescent branch close, regional finance, current-year compensation, compensation forecast, or touring-theatre weekly payroll reporting through the public Finance Ops API endpoints.
---

# Crescent Finance Ops Reporting

## Guardrails

Use only the task input payloads and the base URL/endpoints listed in `environment_access.json`. Do not read environment folders, evaluator code/configs, or any test output/notes/eval artifacts. For train reflection, read standards only after producing a blind answer.

Return one JSON object matching `answer_template.json`. Keep numeric values as numbers. Round currency to 2 decimals and percent/ratio fields to 4 decimals at the final output step.

Fetch raw API JSON from the listed endpoints. PowerShell may wrap top-level arrays as `value` during display; the raw API response is an array for many endpoints.

## Finance API

Use:

- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

Use `period-map` to derive fiscal-year period sets and period labels. For `period_convention.current_month` and `prior_month`, output the raw period labels from the memo, such as `M24`, not month names.

Each finance record is one `branch_id` plus one `account`, with `values` keyed by period. Expense accounts are positive source values; subtract them in formulas.

Finance formulas:

- `revenue = product_revenue + service_revenue`
- `cogs = direct_materials_cogs + direct_labor_cogs`
- `gross_margin = revenue - cogs`
- `sga = sales_sga + admin_sga + occupancy_sga`
- `allocations = shared_service_allocations`
- `ebitda = gross_margin - sga - allocations`
- `growth_pct = (current - prior) / prior`
- `ebitda_margin = ebitda / revenue`
- `arpu = revenue / active_customers`, using aggregate active customer counts over the same period set
- `sales_per_labor_headcount = revenue / labor_headcount`, using aggregate labor headcount over the same period set

For branch close packages, calculate the requested current period income statement, prior-period revenue variance, current fiscal-year metrics, and current-vs-prior fiscal-year growth. Rank branch sales growth by fiscal-year revenue growth across all branches, descending, with branch ID ascending as the tie-breaker. Rank the target region against all regions by current fiscal-year EBITDA, descending. `top_arpu_branch_id` uses current fiscal-year `revenue / active_customers`.

For regional packages, sum branch metrics for all branches in the requested region. `branch_ids` must be ascending. `top_ebitda_branch_id` and `bottom_ebitda_branch_id` rank branches inside the target region by current comparison-year EBITDA. `region_reconciliation_variance` is the region EBITDA total minus the sum of branch EBITDA totals from the same records; this should normally round to `0.0`.

## Compensation API

Use:

- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios` when a forecast request names a scenario

Filter rosters by `ensemble_id`. `roster_count` is the number of matching roster rows. `pay_types` must follow `rate-book.pay_types`.

For each employee and quarter:

- Minimum weekly scale: `minimum_weekly_scale * weeks_by_quarter[Q]`.
- Title premium: `minimum_weekly_scale * title_premium_pct[title] * weeks`, only when `title` is present and `combined_overscale_includes_title` is false.
- Seniority: select the inclusive seniority band from `seniority_weekly` using `years_of_service`, then multiply by weeks.
- Overscale: `overscale_weekly * weeks`.

Use roster quarter weeks exactly; do not force every employee to 13 weeks. `partial_quarter_employee_count` is the count of employees with any quarter weeks different from `rate-book.quarter_weeks`. `combined_overscale_employee_count` is the count with `combined_overscale_includes_title = true`.

For current-year summaries, `quarter_totals` sum all pay types by quarter, `annual_pay_type_totals` sum each pay type across quarters, `annual_total` is the sum of pay-type totals, and `largest_pay_type` is the pay type with the largest annual amount.

For forecasts:

- Compute `current` with current rate-book values.
- Compound scenario growth sequentially: Year + 2 rates build on Year + 1 rates.
- Add one service year for Year + 1 and two service years for Year + 2 before selecting seniority bands.
- Apply cumulative seniority growth to the selected seniority weekly amount.
- Apply cumulative overscale growth to `overscale_weekly`.
- Compute title premiums from the year-specific minimum scale and the scenario `title_pct_multiplier`.
- `growth_rates` compare annual totals year-over-year.
- `year_plus_2_*` detail uses Year + 2 rates and service years.
- `largest_growth_pay_type` is the pay type with the largest percentage growth from current to Year + 2, not the largest absolute-dollar growth.

## Payroll API

Use:

- `/api/payroll/rate-book`
- `/api/payroll/productions`

Filter productions by `production_id`. `service_counts` counts schedule rows by the original `service_type` label, such as `Performance` or `1hr Sound Check`; sort labels alphabetically for stable output.

Base service pay:

- `Performance`, `Audit`, and sound-check services are flat per-service rates from `service_rates`.
- `Rehearsal` is hourly at the rehearsal rate with a 3-hour minimum call: `rate * max(duration_hours, 3)`. Do not cap pay at the service time limit.
- Category names are normalized only for pay totals: `performance`, `audit`, `rehearsal`, `sound_check`.

Substitute treatment:

- Regular weekly guarantee does not apply to substitutes.
- For a substitute, apply a six-performance-service floor: `shortfall = max(0, 6 - assigned_performance_count) * Performance rate`.
- Add the shortfall to the substitute's `performance` category and also report the same amount as `substitute_adjustment`.
- Calculate premium and doubles on adjusted base service pay, where adjusted base includes the performance shortfall but excludes the separate `substitute_adjustment` disclosure line.

Premiums and adjustments:

- `principal_or_lead` premium applies once if either `principal` or `lead` is true.
- Add `quartet`, `electronic`, and explicit concertmaster premiums when those flags/roles are present.
- `premium = adjusted_base_service_pay * sum(applicable premium pct)`.
- `doubles = adjusted_base_service_pay * (first_double pct + additional_double pct * (doubles - 1))` when `doubles > 0`.
- `vacation = (adjusted_base_service_pay + premium + doubles) * vacation pct` when `vacation_eligible` is true.
- `guarantee_adjustment = weekly_guarantee - adjusted_base_service_pay` only for non-substitute regular players when adjusted base service pay is below `weekly_guarantee`. Do not include guarantee adjustment in the vacation base.

Per-musician totals are the sum of nonzero categories. Order `per_musician` by `musician_id`. `top_paid_musician_id` is the highest total after all adjustments, with musician ID ascending as tie-breaker.

Conflict flags:

- `REHEARSAL_EARLY_START`: rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: sound-check duration does not equal the exact sound-check service type limit.

Sort `conflict_flags` alphabetically. Omit zero per-musician categories. Include `substitute_adjustment` in category totals when any substitute shortfall exists.

## Output Checks

Build the answer from `answer_template.json`, not from memory. Verify:

- Required top-level keys are present and named exactly as the template states.
- Lists use ascending stable IDs unless a ranking field explicitly sorts by value.
- Rankings are 1-based ordinal positions after sorting by metric descending and stable ID ascending.
- Currency and ratio rounding is final-output rounding; avoid rounding intermediate sums.
- Payroll `weekly_total` equals the sum of category totals and the sum of per-musician totals after rounding tolerance.
