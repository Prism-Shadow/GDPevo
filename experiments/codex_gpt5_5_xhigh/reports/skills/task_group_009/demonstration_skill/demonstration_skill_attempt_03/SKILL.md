---
name: task-group-009-finance-ops
description: Transferable SOP for Crescent Arts Collective Finance Ops API tasks in task_group_009 requiring branch close reporting, regional finance reporting, current-year ensemble compensation summaries, compensation forecasts, or touring theatre payroll/CBA review. Use when Codex must read input payloads, query the localhost Finance Ops API, calculate rounded JSON outputs, rank branches or regions, apply roster/scenario compensation rules, or compute payroll premiums, guarantees, vacation, substitute adjustments, and conflict flags.
---

# Task Group 009 Finance Ops SOP

Use this skill to solve new Finance Ops reporting tasks from their active input payloads. Do not use train answers as a lookup table. Always derive results from the request memo, answer template, and the public endpoints listed in the task input.

## Access Protocol

1. Read only the task input artifacts: `prompt.txt`, `payloads/request_memo.json`, `payloads/environment_access.json`, and `payloads/answer_template.json`.
2. Get `base_url` and `available_endpoints` from `environment_access.json`.
3. Query only listed public endpoints under that base URL. Typical endpoints are:
   - Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
   - Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
   - Payroll: `/api/payroll/rate-book`, `/api/payroll/productions`
4. Use `request_memo.json` to identify the target branch, region, ensemble, production, scenario, periods, and requested view.
5. Use `answer_template.json` as the output contract. Return one JSON object only, with exactly the requested keys and numeric JSON values.
6. Do not read test outputs, notes, eval files, evaluator code, or environment internals.

PowerShell note: `Invoke-RestMethod` often returns JSON arrays directly. Do not assume a `.value` wrapper exists just because `ConvertTo-Json` displayed one.

## Rounding And Ordering

Use raw precision for all intermediate math. Round only values emitted in the final JSON.

```python
from decimal import Decimal, ROUND_HALF_UP

def round_money(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def round_ratio(x):
    return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
```

- Currency fields: round to 2 decimals.
- Percent and ratio fields: round to 4 decimals as decimal ratios, for example `0.0656`.
- Aggregate totals from raw unrounded components, then round. Do not sum already rounded display rows.
- Sort stable ID lists ascending unless the template states a ranking order.
- For rankings, sort by metric descending, then stable ID ascending, and use the 1-based position after sorting.
- For ties in "largest" fields, use the rate-book pay type order or stable ID order unless the prompt says otherwise.

## Finance Reporting

### Data Model

- `branches`: branch metadata with `branch_id`, `branch_name`, `region_id`, and `region_name`.
- `period-map`: maps period labels such as `M1` to fiscal years and month numbers.
- `accounts`: maps each account to a category such as `revenue`, `cogs`, `sga`, `allocations`, or `operating`.
- `records`: one row per branch/account with a `values` object keyed by period label.

Build fiscal-year period sets from `period-map`, not from calendar assumptions. If the request gives a close period, the current fiscal year is the fiscal year of that period; compare it with the prior fiscal year unless the memo specifies comparison years.

### Account Rollups

For a branch, region, month, or fiscal-year period set:

- `revenue = sum(accounts where category == "revenue")`
- `cogs = sum(accounts where category == "cogs")`
- `gross_margin = revenue - cogs`
- `sga = sum(accounts where category == "sga")`
- `allocations = sum(accounts where category == "allocations")`
- `ebitda = gross_margin - sga - allocations`
- `ebitda_margin = ebitda / revenue`
- `revenue_growth_pct = (current_revenue - prior_revenue) / prior_revenue`
- `ebitda_growth_pct = (current_ebitda - prior_ebitda) / prior_ebitda`
- `arpu = revenue / sum(active_customers over the same periods)`
- `sales_per_labor_headcount = revenue / sum(labor_headcount over the same periods)`

Use the operating denominators as period sums. Do not use average active customers, average headcount, orders, or revenue units for these two ratios.

### Branch Close View

For a target branch close package:

1. Resolve the target branch from `/api/finance/branches`.
2. Resolve current and prior periods from the memo.
3. Build `period_convention` from `period-map`, for example fiscal-year ranges and the current/prior period labels.
4. Build the current-month income statement for the close period.
5. Build month-over-month revenue variance as current period revenue minus prior period revenue, plus percent over prior period revenue.
6. Build current fiscal-year metrics and current-vs-prior fiscal-year growth.
7. Build regional context for the target branch's region:
   - `branch_ids`: all branches in the region, sorted ascending.
   - `fy####_ebitda`: sum the region's branch EBITDA for the current fiscal year.
   - `ebitda_rank_desc`: rank the region among all regions by current fiscal-year EBITDA descending.
8. Build branch rankings across all branches:
   - `sales_growth_rank_desc`: rank the target branch by current-vs-prior fiscal-year revenue growth.
   - `top_sales_growth_branch_id`: branch with the highest current-vs-prior fiscal-year revenue growth.
   - `top_arpu_branch_id`: branch with the highest current fiscal-year ARPU.

### Regional View

For a regional management report:

1. Resolve `target_region_id` and collect included branches sorted by `branch_id`.
2. For each requested comparison year, sum branch metrics across the region.
3. Emit the requested fiscal-year blocks, usually `fy2024` and `fy2025`.
4. Compute current-year `ebitda_margin` and `sales_per_labor_headcount` from region totals.
5. Compute `revenue_growth_pct` between the requested years.
6. Find `top_ebitda_branch_id` and `bottom_ebitda_branch_id` within the target region using current-year branch EBITDA.
7. Compute `region_reconciliation_variance = region_ebitda_from_region_total - sum(branch_ebitda_for_included_branches)`. When both sides come from the same records, this should round to `0.0`.

Pitfall: in the branch close view, `region_context.ebitda_rank_desc` is the region's rank among all regions, not the target branch's rank within its region. In the regional view, top and bottom branch IDs are within the selected region.

## Compensation Summaries

### Rate Book And Roster Fields

Use `/api/compensation/rate-book` for:

- `current_year`
- `minimum_weekly_scale`
- `pay_types` order
- `quarter_weeks`
- `title_premium_pct`
- `seniority_weekly` bands
- business rules

Use `/api/compensation/rosters` for employees with:

- `ensemble_id`, `employee_id`, `title`
- `years_of_service`
- `overscale_weekly`
- `combined_overscale_includes_title`
- `weeks_by_quarter`
- `notes`

Select only the requested `ensemble_id`.

### Current-Year Compensation

For each employee and quarter:

```text
weeks = employee.weeks_by_quarter[quarter]
mws = minimum_weekly_scale * weeks
title = minimum_weekly_scale * title_premium_pct[title] * weeks
seniority = seniority_weekly_for(years_of_service) * weeks
overscale = overscale_weekly * weeks
```

If `title` is null, title premium is zero. If `combined_overscale_includes_title` is true, do not add a separate title premium for that employee, but still include the `overscale_weekly` amount in `Overscale`.

Build:

- `roster_count`: count selected roster rows.
- `pay_types`: exact order from the rate book.
- `quarter_totals`: sum all pay types by quarter.
- `annual_pay_type_totals`: sum all quarters by pay type.
- `annual_total`: sum annual pay type totals.
- `largest_pay_type`: pay type with the largest annual total.
- `combined_overscale_employee_count`: count employees where `combined_overscale_includes_title` is true. Do not count employees merely because `overscale_weekly > 0`.
- `partial_quarter_employee_count`: count employees where any `weeks_by_quarter[Q]` differs from `rate_book.quarter_weeks[Q]`.

### Compensation Forecasts

Use `/api/compensation/scenarios` only when the request includes a `scenario_id`.

Compute three annual layers when requested:

- `current`: current rate book and current years of service.
- `year_plus_1`: apply Year + 1 scenario growth; add 1 service year before seniority band lookup.
- `year_plus_2`: compound Year + 1 and Year + 2 scenario growth; add 2 service years before seniority band lookup.

For Year + 2, multiply growth factors cumulatively:

```text
mws_multiplier_y2 = (1 + y1.mws_growth) * (1 + y2.mws_growth)
seniority_multiplier_y2 = (1 + y1.seniority_growth) * (1 + y2.seniority_growth)
overscale_multiplier_y2 = (1 + y1.overscale_growth) * (1 + y2.overscale_growth)
title_pct_multiplier_y2 = y1.title_pct_multiplier * y2.title_pct_multiplier
```

Forecast pay formulas:

```text
scale_rate = minimum_weekly_scale * mws_multiplier
mws = scale_rate * weeks
title = scale_rate * title_premium_pct[title] * title_pct_multiplier * weeks
seniority = seniority_weekly_for(years_of_service + service_year_add) * seniority_multiplier * weeks
overscale = overscale_weekly * overscale_multiplier * weeks
```

Apply the same combined-overscale rule as current-year compensation.

Build:

- `annual_totals.current`, `annual_totals.year_plus_1`, `annual_totals.year_plus_2`.
- `growth_rates.year_plus_1_vs_current = (year_plus_1_total - current_total) / current_total`.
- `growth_rates.year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total`.
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` from Year + 2 calculations.
- `largest_growth_pay_type`: pay type with the largest percent increase from current annual pay-type total to Year + 2 annual pay-type total. This is a percentage-growth driver classification, not the largest absolute dollar increase.
- Roster treatment counts using the selected current roster.

Pitfalls:

- Use roster quarter weeks, not a fixed 13 weeks.
- Recalculate seniority bands after adding forecast service years.
- Compound scenario growth for Year + 2.
- Skip separate title premium when `combined_overscale_includes_title` is true.

## Theatre Payroll Review

### Rate Book And Production Fields

Use `/api/payroll/rate-book` for:

- `service_rates`
- `premium_pct`
- `weekly_guarantee`
- `service_time_limits`
- `conflict_thresholds`
- business rules

Use `/api/payroll/productions` to select the requested `production_id`. A production has `schedule` services and a `roster` with each musician's assigned service IDs and flags.

### Service Counts

Count services from the production `schedule`, not from roster assignments. Emit service type keys sorted alphabetically unless the template says otherwise.

### Per-Musician Pay

For each musician:

1. Build base service categories from assigned services:
   - `Rehearsal`: `service_rates["Rehearsal"] * max(duration_hours, 3.0)`.
   - `Performance`: flat `service_rates["Performance"]`.
   - `Audit`: flat `service_rates["Audit"]`.
   - Any sound check: flat service rate for that exact sound-check service type, category `sound_check`.
2. If `substitute` is true:
   - Add `2 * service_rates["Performance"]` to the `performance` category.
   - Include that same amount in `base_service_pay` for premium and doubles calculations.
   - Add `2 * service_rates["Performance"]` as a separate `substitute_adjustment` category.
   - Do not apply the weekly guarantee.
3. Compute role premium on `base_service_pay` using the sum of applicable role percentages:
   - `principal_or_lead` once when either `principal` or `lead` is true.
   - `quartet` when true.
   - `electronic` when true.
   - `concertmaster` only if a roster field exposes that flag.
4. Compute doubles on `base_service_pay`:
   - First extra instrument: `first_double`.
   - Each additional extra instrument: `additional_double`.
   - Formula: `base_service_pay * (first_double + max(0, doubles - 1) * additional_double)`.
5. Compute guarantee adjustment for non-substitute regular players:
   - `max(0, weekly_guarantee - base_service_pay)`.
   - Exclude premiums, doubles, vacation, and adjustment categories from this comparison.
6. Compute vacation only when `vacation_eligible` is true:
   - `vacation_pct * (base_service_pay + premium + doubles)`.
   - Exclude guarantee adjustment and the separate substitute adjustment line.
7. Omit zero categories from each musician's `categories` object.

Aggregate payroll category totals from raw per-musician category values, then round. Do not aggregate from rounded musician display values.

### Payroll Output Fields

- `category_totals`: sum raw category amounts by category, sorted by category name when order is not specified.
- `weekly_total`: sum all raw category totals.
- `per_musician`: order by `musician_id`; include `musician_id`, `name`, rounded `total`, and rounded nonzero `categories`.
- `top_paid_musician_id`: highest raw musician total, tie by `musician_id` ascending.

### Conflict Flags

Build a set of flags from the production schedule, then sort alphabetically:

- `REHEARSAL_EARLY_START`: any rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: any rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service has `duration_hours > service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: any sound-check service has `duration_hours != service_time_limits[service_type]`.

Sound-check mismatch and over-time are independent. A long sound check can trigger both if its duration exceeds the limit.

## Final Validation Checklist

Before finalizing:

1. Confirm every required key from `answer_template.json` is present and no extra top-level keys are added.
2. Confirm all currency, percent, and ratio fields use the template's required rounding.
3. Confirm lists and per-person rows use required stable ordering.
4. Confirm rankings are computed across the correct population: all branches, all regions, or selected region branches as requested.
5. Confirm compensation counts distinguish partial-quarter service from combined overscale side-letter treatment.
6. Confirm payroll totals aggregate raw values, not rounded display rows.
7. Return only the final JSON object unless the user explicitly asks for explanation.
