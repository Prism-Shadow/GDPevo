---
name: crescent-finance-ops
description: Solve Crescent Arts Collective finance, compensation, and payroll reporting tasks by calling the Crescent Finance Ops API and applying documented computation rules from three business domains.
---

# Crescent Finance Ops Solver

When a task references Crescent Arts Collective and the "Finance Ops environment," work through the following workflow to produce a single JSON answer from the active API data.

## Workflow

1. **Read the task context.** Open `payloads/environment_access.json` to get the `base_url` and list of `available_endpoints`. Open `payloads/request_memo.json` for the target entity IDs, reporting periods, scenario names, and any `memo_note` hints. Open `payloads/answer_template.json` for the required top-level keys, field types, rounding rules, and ordering conventions. The template's `description` field often contains critical rounding and ordering instructions.

2. **Fetch the data.** Call every endpoint listed in `environment_access.json`. The API is at the `base_url`, no authentication required. All endpoints return JSON arrays or objects. Call them in parallel when possible.

   Optional discovery: `GET /api/manifest` returns a summary of all entities (branches, ensembles, productions) and record counts. This is never required but can confirm data completeness.

3. **Compute the answer.** Apply the domain-specific rules below. Every currency value must be rounded to 2 decimal places. Every percentage or ratio must be rounded to 4 decimal places. Follow the template's field ordering and list-sorting instructions exactly.

4. **Return a single JSON object** whose top-level keys and structure match `answer_template.json`.

## Finance Domain

Used for branch close packages (Train 1) and regional management views (Train 4). Endpoints: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`.

### Data Schemas

**Branches** (`GET /api/finance/branches`): Array of `{branch_id, branch_name, region_id, region_name}`.

**Period Map** (`GET /api/finance/period-map`): Array of `{fiscal_year, month_name, month_number, period}`. The convention is M1-M12 = FY2024, M13-M24 = FY2025. Each subsequent block of 12 periods extends the fiscal year by 1.

**Accounts** (`GET /api/finance/accounts`): Array of `{account, category, display_name, metric_type}`. Categories are `revenue`, `cogs`, `sga`, `allocations`, and `operating`. Use the `category` field to aggregate, not the display name.

**Records** (`GET /api/finance/records`): Array of `{account, branch_id, branch_name, region_id, values}` where `values` is a period-to-number map.

### Income Statement Computation

For a single branch and period (or period range):

```
revenue   = product_revenue + service_revenue
cogs      = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga       = sales_sga + admin_sga + occupancy_sga
allocations = shared_service_allocations
ebitda    = gross_margin - sga - allocations
```

For a date range (e.g. full fiscal year), sum each account across the relevant periods first, then apply the formulas above.

### Ratios and Derived Metrics

```
ebitda_margin          = ebitda / revenue
arpu                   = revenue / active_customers
sales_per_labor_headcount = revenue / labor_headcount
```

Use the `operating` accounts from the records endpoint. Sum `active_customers` and `labor_headcount` across the same period range used for the income statement.

### Growth Rates

```
revenue_growth_pct = (current_revenue - prior_revenue) / prior_revenue
ebitda_growth_pct  = (current_ebitda - prior_ebitda) / prior_ebitda
```

For month-over-month variance, use the current and prior period revenues directly.

### Regional Aggregation

To compute a region total, filter all branch records to branches whose `region_id` matches the target region, then sum each account across those branches and the desired periods.

**Region reconciliation variance**: Sum branch-level EBITDA for the region from the branch detail, then subtract the region total computed from aggregated records. The result should be zero when the data is consistent.

### Branch Rankings

- **Sales growth rank (descending)**: For every branch, compute FY2025 vs FY2024 revenue growth, then rank descending (1 = highest growth).
- **Top sales growth branch**: The branch with maximum revenue growth.
- **Top ARPU branch**: The branch with maximum FY2025 ARPU.
- **Top/bottom EBITDA branch within a region**: Rank only branches in the target region by FY2025 EBITDA descending. The top is rank 1; the bottom is the last rank.

### Period Convention Object

When the template requires `period_convention`, derive it from the period map:
- `M1_to_M12`: "FY2024"
- `M13_to_M24`: "FY2025"
- `current_month`: the period label from the request memo (e.g. "M24")
- `prior_month`: the prior period label from the request memo (e.g. "M23")

## Compensation Domain

Used for current-year summaries (Train 2) and board forecasts (Train 5). Endpoints: `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` (forecasts only).

### Data Schemas

**Rate Book** (`GET /api/compensation/rate-book`): Object with `current_year`, `minimum_weekly_scale`, `quarter_weeks` (Q1-Q4 each 13), `seniority_weekly` (array of `{min_years, max_years, weekly_amount}` bands), `title_premium_pct` (map from title to decimal), `pay_types` (ordered list), and `business_rules`.

**Rosters** (`GET /api/compensation/rosters`): Array of roster entries. Each has `employee_id`, `ensemble_id`, `ensemble_name`, `title` (string or null), `overscale_weekly`, `years_of_service`, `weeks_by_quarter` (Q1-Q4 week counts), `combined_overscale_includes_title` (boolean), and `notes`.

**Scenarios** (`GET /api/compensation/scenarios`): Object keyed by scenario ID. Each scenario has `year_plus_1` and `year_plus_2` objects with `mws_growth`, `overscale_growth`, `seniority_growth`, and `title_pct_multiplier`.

### Per-Employee Quarterly Pay Calculation (Current Year)

For each employee in the target ensemble, for each quarter Q:

1. **Base (Minimum Weekly Scale)**: `mws * weeks_in_quarter`
2. **Title Premium**: If `title` is non-null and `combined_overscale_includes_title` is **false**, add `mws * title_premium_pct[title] * weeks_in_quarter`. If `combined_overscale_includes_title` is **true**, skip this step (the overscale already covers it).
3. **Seniority**: Find the seniority band where `min_years <= years_of_service` and (`max_years` is null or `years_of_service <= max_years`). Add `band.weekly_amount * weeks_in_quarter`.
4. **Overscale**: Add `overscale_weekly * weeks_in_quarter`.

Quarter total = sum of all four components for all employees in the ensemble.

### Current-Year Aggregation

- `roster_count`: Count of employees in the target ensemble.
- `pay_types`: The ordered list from the rate book.
- `quarter_totals`: Sum per-employee quarterly totals for the ensemble.
- `annual_pay_type_totals`: Aggregate by pay type across all employees and quarters.
- `annual_total`: Sum of all four pay type totals.
- `largest_pay_type`: The pay type with the highest `annual_pay_type_totals` value.
- `combined_overscale_employee_count`: Count of employees where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count`: Count of employees whose `notes` contains "Partial-quarter".

### Forecast Calculation (Trains with Scenarios)

For a forecast, compute three annual totals: **current**, **Year + 1**, and **Year + 2**.

**Current year**: Same as current-year aggregation above.

**Year + 1**: For each employee, add 1 to `years_of_service` before looking up the seniority band. Apply the scenario's `year_plus_1` multipliers:

- New MWS rate = `minimum_weekly_scale * (1 + mws_growth)`
- New overscale = `overscale_weekly * (1 + overscale_growth)`
- New seniority weekly = `band.weekly_amount * (1 + seniority_growth)`
- Title premium = `new_mws * title_premium_pct[title] * title_pct_multiplier * weeks`

Compute each quarter and aggregate.

**Year + 2**: Same as Year + 1, but add 2 to `years_of_service` and use `year_plus_2` multipliers.

**Growth rates**:
```
year_plus_1_vs_current = (year_plus_1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```

**Largest growth pay type**: For each pay type, compute `(year_plus_2_total - current_total) / current_total`. The pay type with the largest ratio is `largest_growth_pay_type`. If the growth is negative, use absolute magnitude for comparison but report the pay type with the most positive (or least negative) growth.

**Roster treatment counts** apply to the current year roster: `combined_overscale_employee_count` and `partial_quarter_employee_count` use the same rules as the current-year summary.

**Forecast-specific keys**: Include `scenario_id`, `year_plus_2_quarter_totals`, and `year_plus_2_pay_type_totals` only when the answer template requires them.

### Business Rules from Rate Book

- Use roster quarter weeks, not a fixed 13-week quarter, when partial-quarter employees are listed. The `weeks_by_quarter` field on each roster entry already reflects the correct week counts.
- If `combined_overscale_includes_title` is true, do not add a titled position premium separately.
- For forecast years, add one year of service for Year + 1 and two years for Year + 2 before assigning seniority bands.

## Payroll Domain

Used for weekly payroll reviews (Train 3). Endpoints: `/api/payroll/rate-book`, `/api/payroll/productions`.

### Data Schemas

**Rate Book** (`GET /api/payroll/rate-book`): Object with `service_rates` (service type to dollar amount), `premium_pct` (premium name to decimal), `weekly_guarantee`, `conflict_thresholds` (`rehearsal_earliest_start`, `rehearsal_latest_end`), `service_time_limits` (service type to max hours), and `business_rules`.

**Productions** (`GET /api/payroll/productions`): Array of production objects. Each has `production_id`, `title`, `week_start`, `roster` (array of musicians), and `schedule` (array of services).

Musician object: `{musician_id, name, instrument, assigned_service_ids, doubles, electronic, lead, principal, quartet, substitute, vacation_eligible}`.

Schedule entry: `{service_id, date, start_time, end_time, duration_hours, service_type}`.

### Per-Musician Pay Calculation

For each musician in the target production's roster:

1. **Base service pay**: For each assigned service, look up its `service_type` in the schedule to get `duration_hours`.
   - **Rehearsal**: `service_rates["Rehearsal"] * max(3, duration_hours)` (hourly rate, 3-hour minimum call)
   - **All other service types**: `service_rates[service_type]` (flat per-service rate)

   Sum base pay by service type category for reporting, but compute premiums on total base.

2. **Premiums**: Apply each applicable premium percentage to **total base pay**. Premiums are cumulative (add the percentages then multiply). Applicable premiums:
   - `principal_or_lead` (15%): if `principal` is true OR `lead` is true (not both; the flag applies once)
   - `quartet` (15%): if `quartet` is true
   - `electronic` (25%): if `electronic` is true
   - `first_double` (25%): if `doubles >= 1`
   - `additional_double` (10%): for each double beyond the first, i.e. if `doubles >= 2`, add `(doubles - 1) * 10%`

   Total premium = `total_base_pay * sum(applicable_premium_pcts)`.

   Note: Report doubles pay as a separate `doubles` category. Report all other premiums combined under `premium`.

3. **Doubles pay** (for the `doubles` category in per-musician breakdown): `total_base_pay * (first_double_pct + (doubles - 1) * additional_double_pct)` when `doubles >= 1`. This is the same calculation as the doubles portion of premiums; report separately in the per-musician categories breakdown.

4. **Vacation**: If `vacation_eligible` is true: `0.04 * (total_base_pay + total_premium + doubles_pay)`. Report under the `vacation` category.

5. **Weekly guarantee adjustment**: Applies to non-substitute musicians when base service pay (before premiums, doubles, vacation) is below `weekly_guarantee`. Amount = `weekly_guarantee - total_base_pay`. If `total_base_pay >= weekly_guarantee`, no adjustment. Report under `guarantee_adjustment`.

6. **Substitute adjustment**: For `substitute` musicians, compute the substitute adjustment separately. Substitute musicians do not receive vacation or guarantee adjustments.

### Per-Musician Categories

The `categories` object in per_musician output must only include nonzero amounts. Group base pay by service type, and add separate keys for `premium`, `doubles`, `vacation`, `guarantee_adjustment`, and `substitute_adjustment` as applicable.

### Aggregations

- `service_counts`: Count each `service_type` across the production's schedule.
- `category_totals`: Sum each category across all musicians. Include all nine possible categories from the template, using 0 for any that have no activity. The standard set: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`.
- `weekly_total`: Sum of all per-musician totals.
- `top_paid_musician_id`: The `musician_id` with the highest per-musician total.
- `per_musician`: Array ordered by `musician_id` ascending.

### Conflict Flag Detection

Check the production's schedule against the rate book thresholds:

- `REHEARSAL_EARLY_START`: Any rehearsal service where `start_time < conflict_thresholds.rehearsal_earliest_start` (string comparison on "HH:MM").
- `REHEARSAL_LATE_END`: Any rehearsal where `end_time > conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: Any service where `duration_hours > service_time_limits[service_type]` (strictly greater, not equal).
- `SOUND_CHECK_DURATION_MISMATCH`: Any sound check where the `service_type` label does not match the actual duration. Use the `service_time_limits` entry to determine the expected duration for the labeled type: a "1hr Sound Check" should have `duration_hours` close to `service_time_limits["1hr Sound Check"]` (within ~0.25 hours), and similarly for "2hr Sound Check".

Sort `conflict_flags` alphabetically. Return an empty array if none fire.

## Rounding and Formatting Conventions

- **Currency values**: Round to 2 decimal places. Use `round(value, 2)`.
- **Percentages and ratios** (`pct`, `margin`, growth rates): Round to 4 decimal places. Use `round(value, 4)`.
- **Lists**: Unless a rank field dictates otherwise, sort string IDs in ascending order.
- **per_musician**: Order by `musician_id` ascending.
- **conflict_flags**: Sort alphabetically.
- **branch_ids in region_context**: Sort ascending.

## Task Type Recognition

Read `request_memo.json` to determine which domain applies:

- `target_branch_id` and `close_period` -> Branch close package (Finance domain)
- `target_region_id` and `requested_comparison_years` -> Regional management view (Finance domain)
- `ensemble_id` and `summary_type` without `scenario_id` -> Current-year compensation (Compensation domain)
- `ensemble_id` and `scenario_id` and `forecast_years` -> Compensation forecast (Compensation domain)
- `production_id` -> Weekly payroll review (Payroll domain)

Use only the endpoints listed in `environment_access.json`. Do not call endpoints outside the listed set.

## Answer Template Conformance

The `answer_template.json` defines both the schema and validation requirements. The `description` field often contains critical instructions. The `required_top_level_keys` array defines every key the output must include. The `field_types` object specifies types and substructures.

Always return exactly the keys listed in `required_top_level_keys`. Do not add extra keys. Do not omit keys.

If a category or field has no activity, include it with a zero value (0 for integers, 0.0 for currency) rather than omitting it, unless the template explicitly says to exclude empty entries.
