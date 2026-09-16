---
name: crescent-finance-ops
description: Solve Crescent Finance Ops reporting tasks across branch close packages, regional management views, compensation summaries, compensation forecasts, and weekly payroll reviews. Use the task environment API to fetch live data, apply domain-specific computation rules, and return structured JSON answers matching the supplied answer template.
---

# Crescent Finance Ops Solver

Solve structured financial reporting tasks for Crescent Arts Collective by
reading the task prompt, the three payload files (`environment_access.json`,
`request_memo.json`, `answer_template.json`), and the live Finance Ops API at
the base URL given in `environment_access.json`. Return a single JSON object
that satisfies every required key, field type, rounding rule, and ordering
constraint declared in the answer template.

## Environment

The task provides three payload files inside the task input directory:

- **`environment_access.json`** -- contains `base_url` and the list of
  `available_endpoints` for this task. All API calls use `GET` with no
  authentication.
- **`request_memo.json`** -- the task parameters: target entity IDs, periods,
  years, or focus areas.
- **`answer_template.json`** -- the required JSON shape with
  `required_top_level_keys`, `field_types`, and formatting rules.

Read all three before calling the API. Use **only** the endpoints listed in
`available_endpoints` for that task; do not call endpoints outside the list.

## Rounding, Precision, and Ordering

- Currency values: round to **2 decimal places** with standard half-up rounding.
- Percent and ratio fields: round to **4 decimal places** (e.g. 0.0966, not
  9.66%).
- Growth rates and margins are decimal fractions, not percentages.
- Lists of IDs must be in **ascending** stable string order unless a rank field
  in the template explicitly states otherwise.
- `per_musician` arrays must be ordered by `musician_id` ascending.
- `conflict_flags` arrays must be sorted alphabetically.
- When computing intermediate values (e.g. gross margin = revenue − cogs), use
  the unrounded operand values before rounding the result.
- All financial arithmetic should use double-precision floating point or an
  equivalent decimal type; do not truncate at intermediate steps.

## Finance Operations Domain

Used for branch close packages and regional management views.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/finance/branches` | All branches with `branch_id`, `branch_name`, `region_id`, `region_name` |
| `GET /api/finance/period-map` | 24-month period map: M1–M12 = FY2024, M13–M24 = FY2025 |
| `GET /api/finance/accounts` | Chart of accounts: `account`, `category`, `display_name`, `metric_type` |
| `GET /api/finance/records` | Per-branch record rows; each has `account`, `branch_id`, and `values` (dict of period → amount). Accepts query params `?branch_id=...&period=...` |

### Account Rollups

Combine individual accounts into the standard line items used throughout:

- **revenue** = `product_revenue` + `service_revenue`
- **cogs** = `direct_materials_cogs` + `direct_labor_cogs`
- **gross_margin** = revenue − cogs
- **sga** = `sales_sga` + `admin_sga` + `occupancy_sga`
- **allocations** = `shared_service_allocations`
- **ebitda** = gross_margin − sga − allocations

Operating accounts (`orders`, `revenue_units`, `active_customers`,
`labor_headcount`, `admin_headcount`, `backlog`) have `metric_type: "count"`.
When a template asks for `arpu` or `sales_per_labor_headcount`, sum the
relevant operating account values over the target periods, then divide the
period revenue total by that sum.

### Period Convention

The period map is fixed across all runs: M1–M12 map to FY2024, M13–M24 map to
FY2025. When the task references "current close period" and "prior period" (or
similarly "current month" / "prior month"), these are period labels like M24
and M23 from the request memo. The `period_convention` object always maps
`M1_to_M12` to `"FY2024"`, `M13_to_M24` to `"FY2025"`, and carries the
`current_month` / `prior_month` labels directly from the request.

### Income Statement for a Single Period

For a target period P (e.g. M24), extract each account's `values[P]` for the
target branch, then roll up to revenue / cogs / gross_margin / sga /
allocations / ebitda using the formulas above.

### Month-over-Month Revenue Variance

- **amount** = revenue(period P) − revenue(period P−1)
- **pct** = amount / revenue(period P−1)

### Fiscal Year Comparisons

For a fiscal year, sum each account's values across the 12 periods of that
year (M1–M12 for FY2024, M13–M24 for FY2025), then roll up to line items.

- **revenue_growth_pct** = (FY2025_revenue − FY2024_revenue) / FY2024_revenue
- **ebitda_growth_pct** = (FY2025_ebitda − FY2024_ebitda) / FY2024_ebitda
- **ebitda_margin** (FY2025) = FY2025_ebitda / FY2025_revenue
- **arpu** (FY2025) = FY2025_revenue / sum of `active_customers` across M13–M24
- **sales_per_labor_headcount** (FY2025) = FY2025_revenue / sum of `labor_headcount` across M13–M24

### Region Context

The target branch belongs to a region. Look up `region_id` from the branches
endpoint. Collect all `branch_ids` that share that `region_id`, sorted
ascending. Compute FY2025 ebitda for every branch in the region, sum them for
`fy2025_ebitda`. Rank the target branch by FY2025 ebitda within the region
(descending: highest ebitda = rank 1).

### Branch Rankings (Enterprise-Wide)

Fetch records for **all** branches (omit the branch filter or iterate all 12).
Compute each branch's FY2025 revenue and FY2024 revenue to derive
`revenue_growth_pct`. Compute each branch's FY2025 ARPU.

- **sales_growth_rank_desc** = descending rank of the target branch's revenue
  growth among all branches (highest growth = 1). Ties: the branch with the
  lexicographically smaller `branch_id` gets the better (lower) rank.
- **top_sales_growth_branch_id** = `branch_id` with the highest revenue growth
  (ties broken by ascending `branch_id`).
- **top_arpu_branch_id** = `branch_id` with the highest FY2025 ARPU (ties
  broken by ascending `branch_id`).

### Regional Management View

For a target region, collect all branches in that region. Sum FY2024 and
FY2025 line items across those branches (revenue, sga, allocations, ebitda).
Compute FY2025 ebitda_margin and sales_per_labor_headcount at the region level.

- **revenue_growth_pct** = (FY2025_region_revenue − FY2024_region_revenue) / FY2024_region_revenue
- **top_ebitda_branch_id** / **bottom_ebitda_branch_id** = branch with the
  highest / lowest FY2025 ebitda within the region (ties broken by ascending
  `branch_id`).
- **region_reconciliation_variance** = 0.0 (the branch-level data is internally
  consistent; the sum of branch line items equals the region totals).

## Compensation Domain

Used for current-year summaries and board forecast scenarios.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/compensation/rate-book` | Rate book with `current_year`, `minimum_weekly_scale`, `pay_types`, `quarter_weeks`, `seniority_weekly` bands, `title_premium_pct`, and `business_rules` |
| `GET /api/compensation/rosters` | Roster rows for a given `?ensemble_id=...`. Each row: `employee_id`, `title`, `years_of_service`, `overscale_weekly`, `combined_overscale_includes_title`, `weeks_by_quarter` |
| `GET /api/compensation/scenarios` | Forecast scenarios keyed by scenario id. Each scenario has `year_plus_1` and `year_plus_2` with `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier` |

### Business Rules (from the Rate Book)

1. **Quarter weeks**: Use each employee's `weeks_by_quarter` from the roster,
   not the fixed 13-week default. The rate-book `quarter_weeks` is a fallback
   only when the roster omits `weeks_by_quarter`.
2. **Combined overscale**: When `combined_overscale_includes_title` is `true`,
   do **not** add a separate titled position premium for that employee.
3. **Forecast seniority**: For Year + 1, add 1 year to each employee's
   `years_of_service` before selecting the seniority band. For Year + 2, add
   2 years. The `seniority_weekly` bands are inclusive on both ends (e.g.
   `min_years: 5, max_years: 9` covers 5 through 9 years of service).

### Per-Employee Quarterly Pay Calculation

For each employee, for each quarter Q:

```
weeks = roster.weeks_by_quarter[Q]

mws_pay = minimum_weekly_scale × weeks

title_pct = title_premium_pct[roster.title]   (0 if no title)
title_pay = mws_pay × title_pct    (skip if combined_overscale_includes_title)

seniority_amt = lookup_seniority_weekly(roster.years_of_service)  (0 if 0-4)
seniority_pay = seniority_amt × weeks

overscale_pay = roster.overscale_weekly × weeks

quarter_pay = mws_pay + title_pay + seniority_pay + overscale_pay
```

### Roster Treatment Counts

- **roster_count** = total number of employees in the roster.
- **combined_overscale_employee_count** = count of employees where
  `combined_overscale_includes_title` is `true`.
- **partial_quarter_employee_count** = count of employees whose total weeks
  across all four quarters (Q1+Q2+Q3+Q4) is **less than 52**.

### Quarterly and Annual Aggregation

- **quarter_totals[Q]** = sum of `quarter_pay` for all employees in quarter Q.
- **annual_pay_type_totals**: sum each pay type component (MWS, title,
  seniority, overscale) across all employees and all quarters.
- **annual_total** = sum of all four `quarter_totals` (must equal sum of all
  `annual_pay_type_totals`).
- **largest_pay_type** = the pay type string with the highest
  `annual_pay_type_totals` value (ties broken by the order in the rate-book
  `pay_types` list).
- **pay_types** = the ordered list from the rate book (not from the roster).

### Forecast Scenarios

Start from the **current-year** calculation using the roster as-is.

For **Year + 1**, adjust each component:

- `mws` = `minimum_weekly_scale` × (1 + `mws_growth`)
- `overscale` = `overscale_weekly` × (1 + `overscale_growth`)
- `seniority_weekly` = lookup with `years_of_service + 1`, then multiply the
  looked-up amount by (1 + `seniority_growth`)
- `title_premium_pct` = original × `title_pct_multiplier`

For **Year + 2**, apply Year + 2 growths with `years_of_service + 2`.

Growth rates between years:

- **year_plus_1_vs_current** = (`annual_total_year_plus_1` − `annual_total_current`) / `annual_total_current`
- **year_plus_2_vs_year_plus_1** = (`annual_total_year_plus_2` − `annual_total_year_plus_1`) / `annual_total_year_plus_1`

The **largest_growth_pay_type** is the pay type with the greatest absolute
dollar increase from `current` to `year_plus_2` in `annual_pay_type_totals`
(ties broken by the rate-book `pay_types` order).

## Payroll Domain

Used for weekly production payroll reviews.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/payroll/rate-book` | Payroll rate book with `service_rates`, `premium_pct`, `weekly_guarantee`, `conflict_thresholds`, `service_time_limits`, and `business_rules` |
| `GET /api/payroll/productions` | Production data for a given `?production_id=...`. Contains `roster` (musicians with flags and assigned service IDs) and `schedule` (services with type, date, times, duration) |

### Business Rules (from the Rate Book)

1. **Rehearsal** is hourly at `service_rates["Rehearsal"]` with a **3-hour
   minimum call**. Compute rehearsal base pay as `max(duration_hours, 3.0) ×
   rehearsal_rate`.
2. **Performance, Audit, and Sound Check** are **per-service** flat rates from
   `service_rates`.
3. **Premiums** are percentages applied to the musician's **base service pay**
   (the sum of all service-rate or rehearsal-rate earnings before premiums).
   Premiums stack additively -- sum all applicable percentages, then multiply
   by base pay. Applicable premiums:
   - `principal_or_lead` (0.15) -- if `principal` or `lead` is true
   - `concertmaster` (0.20) -- if the musician is a concertmaster (title-based)
   - `quartet` (0.15) -- if `quartet` is true
   - `electronic` (0.25) -- if `electronic` is true
   - `first_double` (0.25) -- if `doubles` ≥ 1
   - `additional_double` (0.10) -- for each extra instrument beyond the first:
     `(doubles − 1) × 0.10` when `doubles` > 1
4. **Vacation** is 4% of (`base_pay` + `total_premiums`) when
   `vacation_eligible` is `true`. Apply vacation **after** premiums.
5. **Weekly guarantee adjustment** applies only to **non-substitute** players
   (`substitute: false`). If `base_pay + premiums + vacation <
   weekly_guarantee`, add a `guarantee_adjustment` equal to the shortfall.
6. **Substitute adjustment**: substitutes (`substitute: true`) receive a
   substitute adjustment. Compute the substitute's base pay from their
   assigned services at the per-service rates, then the `substitute_adjustment`
   = `weekly_guarantee` − (that base pay). This adjustment is separate from
   premiums and vacation (substitutes are not vacation-eligible and do not
   receive a guarantee adjustment).

### Per-Musician Calculation

For each musician, iterate over their `assigned_service_ids`. For each service
ID, find the matching entry in the `schedule` array, determine the service
type, and apply the rate rule (rehearsal hourly with 3-hour minimum, or
per-service flat rate). Sum to get `base_pay`.

Compute premiums on `base_pay` using the stacked premium formula.

Compute vacation on `base_pay + premiums` if `vacation_eligible`.

For non-substitutes: if `base_pay + premiums + vacation < weekly_guarantee`,
add `guarantee_adjustment = weekly_guarantee − (base_pay + premiums +
vacation)`.

For substitutes: `substitute_adjustment = weekly_guarantee − base_pay`
(premiums and vacation still computed separately; the guarantee adjustment
rule does not apply to substitutes).

The musician's total = `base_pay + premiums + vacation + guarantee_adjustment
+ substitute_adjustment` (only the applicable adjustments are non-zero).

### Category Totals

Map each component to the category totals object:

- **performance**: sum of base pay for all Performance-type services across
  all musicians.
- **audit**: sum of base pay for all Audit-type services.
- **rehearsal**: sum of base pay for all Rehearsal-type services.
- **sound_check**: sum of base pay for all Sound Check services.
- **doubles**: sum of the doubles premium portion (first_double +
  additional_double) across all musicians.
- **premium**: sum of all non-doubles premiums (principal_or_lead,
  concertmaster, quartet, electronic) across all musicians.
- **vacation**: sum of vacation pay across all musicians.
- **guarantee_adjustment**: sum of guarantee adjustments (non-substitutes
  only).
- **substitute_adjustment**: sum of substitute adjustments (substitutes only).

### Per-Musician Categories

For each musician, include only categories where the amount is **non-zero**.
Category names are the same as in `category_totals` (lowercase). Order does
not matter within the per-musician `categories` object.

### Service Counts

Count each service type in the `schedule` array: group by `service_type` and
count occurrences. Use the exact `service_type` strings from the schedule
(e.g. `"1hr Sound Check"`, `"Performance"`, `"Rehearsal"`, `"Audit"`).

### Top Paid Musician

Find the musician with the highest `total`. Ties are broken by ascending
`musician_id`.

### Conflict Flags (from the Schedule)

Check every service in the schedule against the rate-book thresholds. Collect
any violations as an alphabetically sorted list of flag enum values:

- **REHEARSAL_EARLY_START**: any rehearsal with `start_time` <
  `conflict_thresholds.rehearsal_earliest_start` (string comparison, e.g.
  `"08:45" < "09:00"`).
- **REHEARSAL_LATE_END**: any rehearsal with `end_time` >
  `conflict_thresholds.rehearsal_latest_end`.
- **SERVICE_OVER_TIME_LIMIT**: any service where `duration_hours` >
  `service_time_limits[service_type]`.
- **SOUND_CHECK_DURATION_MISMATCH**: any sound check whose `duration_hours`
  does not match its nominal duration (1.0 for `"1hr Sound Check"`, 2.0 for
  `"2hr Sound Check"`).

Only include flags that are actually triggered. An empty list is allowed.

## Task Approach Checklist

1. Read the three payload files to understand what is being asked and what
   shape the answer must take.
2. Identify the domain: finance (branches/periods/records), compensation
   (rate-book/rosters/scenarios), or payroll (rate-book/productions).
3. Call the relevant API endpoints to fetch live data. Filter by the entities
   in the request memo (branch_id, ensemble_id, production_id, scenario_id).
4. Apply the domain-specific formulas and business rules described above.
5. Round currency to 2 decimals, percents/ratios to 4 decimals, sort lists
   as specified in the answer template.
6. Return exactly one JSON object with every `required_top_level_key` present.
   Do not include extra keys beyond what the template declares.
