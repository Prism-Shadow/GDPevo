---
name: task-group-009-fewshot-attempt-01
description: SOP for Crescent Finance Ops API reporting tasks. Use when a task provides environment_access.json, request_memo.json, and answer_template.json for branch or regional finance reporting, ensemble compensation summaries or forecasts, or touring production weekly payroll reviews.
---

# Crescent Finance Ops SOP

Use this skill to produce one JSON object from the active Finance Ops API. Treat the request memo and answer template as the contract. Do not copy training answers as constants or infer answers from branch/ensemble/production IDs alone.

## First Pass

1. Read only the task input payloads: `prompt.txt`, `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`.
2. Use `base_url` from `environment_access.json`; call only endpoints listed in `available_endpoints`.
3. Fetch the full endpoint data, then filter client-side by IDs from `request_memo.json`.
4. Build exactly the keys required by `answer_template.json`; keep key names and nested shapes unchanged.
5. Keep calculations unrounded until the final JSON fields. Return JSON numbers, not strings.

For HTTP clients, the API returns raw JSON objects or arrays. Some shells wrap arrays during display; normalize to the raw array before calculating.

## Rounding And Ordering

- Round currency and counts-derived currency ratios to 2 decimals.
- Round percent, growth, margin, and ratio fields to 4 decimals.
- Use decimal percentages, not display percentages: `0.0966`, not `9.66`.
- Round final per-field values only. Per-person category values and per-person totals may differ by a cent if category fields are rounded independently.
- Sort stable ID lists ascending unless a template says a rank is descending.
- Sort `per_musician` by `musician_id`.
- Sort `conflict_flags` alphabetically.
- For rank ties, prefer stable ascending IDs unless the request/template states another tie-break.

## Finance API

Endpoints:

- `/api/finance/branches`: branch metadata with `branch_id`, `branch_name`, `region_id`, `region_name`.
- `/api/finance/period-map`: maps `period` labels such as `M24` to `fiscal_year`, `month_number`, and `month_name`.
- `/api/finance/accounts`: account metadata with categories such as `revenue`, `cogs`, `sga`, `allocations`, and `operating`.
- `/api/finance/records`: one row per `branch_id` and `account`, with monthly values in `values.M#`.

Finance formulas:

- `revenue = product_revenue + service_revenue`.
- `cogs = direct_materials_cogs + direct_labor_cogs`.
- `gross_margin = revenue - cogs`.
- `sga = sales_sga + admin_sga + occupancy_sga`.
- `allocations = shared_service_allocations`.
- `ebitda = gross_margin - sga - allocations`.
- `ebitda_margin = ebitda / revenue`.
- `arpu = revenue / active_customers`, using summed monthly `active_customers` over the requested period set.
- `sales_per_labor_headcount = revenue / labor_headcount`, using summed monthly `labor_headcount`.
- Growth percent: `(current - prior) / prior`.

Branch close workflow:

1. Resolve `target_branch_id`, `close_period`, and `prior_period` from the memo.
2. Use the period map to identify current/prior months and fiscal-year period sets.
3. Build the current-month income statement from the target branch.
4. Compute month-over-month revenue variance from current vs prior period.
5. Compute current fiscal-year branch metrics and prior fiscal-year comparison metrics.
6. For region context, find the target branch region, list region branches ascending, sum region FY EBITDA, and rank the region by FY EBITDA among all regions descending.
7. For branch rankings, compute each branch's fiscal-year revenue growth and ARPU; rank descending and report top branch IDs plus the target branch rank when requested.

Regional workflow:

1. Filter branches by `target_region_id`.
2. Aggregate all requested year metrics over every branch in the region.
3. Compute `ebitda_margin` and `sales_per_labor_headcount` only for years requested by the template.
4. Rank region branches by FY EBITDA for `top_ebitda_branch_id` and `bottom_ebitda_branch_id`.
5. Reconcile regional EBITDA to the sum of branch-level EBITDA; report `region_reconciliation_variance` rounded to 2 decimals.

## Compensation API

Endpoints:

- `/api/compensation/rate-book`: current year, minimum weekly scale, pay type order, quarter weeks, seniority bands, title premium percentages, and business rules.
- `/api/compensation/rosters`: one row per employee with `ensemble_id`, `weeks_by_quarter`, `years_of_service`, `title`, `overscale_weekly`, and `combined_overscale_includes_title`.
- `/api/compensation/scenarios`: forecast growth assumptions by scenario and future year.

Current-year compensation workflow:

1. Filter roster rows by `ensemble_id`.
2. Preserve `pay_types` order from the rate book.
3. For each employee and quarter, use that employee's `weeks_by_quarter`; do not assume every quarter is 13 weeks.
4. Minimum scale: `minimum_weekly_scale * weeks`.
5. Title premium: `minimum_weekly_scale * title_premium_pct[title] * weeks`.
6. If `combined_overscale_includes_title` is true, do not add a separate title premium for that employee.
7. Seniority: choose the rate-book seniority band using `years_of_service`, then multiply by weeks.
8. Overscale: `overscale_weekly * weeks`.
9. Sum quarter totals, pay-type totals, annual total, roster count, and largest pay type by annual amount.
10. `combined_overscale_employee_count` counts roster rows with `combined_overscale_includes_title: true`.
11. `partial_quarter_employee_count` counts employees whose `weeks_by_quarter` differs from the rate-book `quarter_weeks` in any quarter.

Forecast workflow:

1. Compute `current` exactly as the current-year workflow.
2. For `year_plus_1`, add 1 year of service before selecting seniority bands. Apply scenario year-plus-1 growth to minimum weekly scale, overscale, and seniority weekly amounts.
3. For `year_plus_2`, add 2 years of service before selecting seniority bands. Apply growth cumulatively: multiply year-plus-1 and year-plus-2 factors for minimum weekly scale, overscale, and seniority.
4. Title premium is based on the grown minimum weekly scale and the title premium percentage multiplied by the scenario `title_pct_multiplier`. For year plus 2, compound the title multipliers.
5. Growth rates compare annual totals: `(year_plus_1 - current) / current` and `(year_plus_2 - year_plus_1) / year_plus_1`.
6. `largest_growth_pay_type` is the pay type with the largest relative growth from current to year plus 2, not simply the largest dollar total.

## Payroll API

Endpoints:

- `/api/payroll/rate-book`: service rates, premium percentages, service time limits, weekly guarantee, conflict thresholds, and payroll business rules.
- `/api/payroll/productions`: productions with `schedule` services and rostered musicians.

Weekly payroll workflow:

1. Filter productions by `production_id`.
2. Count scheduled services by `service_type` for `service_counts`; this is schedule count, not musician assignment count.
3. For each musician, use only services in `assigned_service_ids`.
4. Base service categories:
   - `performance`: service rate for each assigned `Performance`.
   - `audit`: service rate for each assigned `Audit`.
   - `sound_check`: service rate for assigned `1hr Sound Check` or `2hr Sound Check`.
   - `rehearsal`: `Rehearsal` hourly rate times `max(duration_hours, 3)`.
5. Apply the observed substitute convention when `substitute` is true and the template includes `substitute_adjustment`: add two `Performance` service-rate units as `substitute_adjustment`, include the same amount in the musician's `performance` base, and do not apply the weekly guarantee to that substitute.
6. Premiums are additive percentages on base service pay before vacation:
   - `principal` or `lead`: `principal_or_lead`.
   - `quartet`: `quartet`.
   - `electronic`: `electronic`.
   - concertmaster/title signal, if present in the roster: `concertmaster`.
7. Doubles are a separate `doubles` category: first extra instrument at `first_double`, each additional extra at `additional_double`, applied to base service pay.
8. Weekly guarantee applies only to guaranteed regular players, not substitutes: if base service pay is below `weekly_guarantee`, add `weekly_guarantee - base_service_pay` as `guarantee_adjustment`.
9. Vacation applies only when `vacation_eligible` is true. Calculate it as `vacation_pct * (base service pay + premium + doubles)`, excluding guarantee adjustments.
10. Per-musician `categories` should include nonzero rounded categories only. Compute each musician `total` from unrounded components, then round.
11. `category_totals` sums each category across musicians from unrounded components, then rounds. `weekly_total` is the unrounded sum of musician totals, rounded once.
12. `top_paid_musician_id` is the musician with the highest unrounded total.

Conflict flags:

- `REHEARSAL_EARLY_START`: any rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: any rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: a named sound-check service duration does not match its listed time limit.

## Final Validation

Before returning the answer:

- Confirm every required top-level key from `answer_template.json` is present and no lookup-table training constants slipped in.
- Confirm all IDs come from the active API records and memo filters.
- Confirm rank directions, list ordering, and conflict flag sorting match the template.
- Confirm subtotals were computed from unrounded numbers and rounded only for output fields.
