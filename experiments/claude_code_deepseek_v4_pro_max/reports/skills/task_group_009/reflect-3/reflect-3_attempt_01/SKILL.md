# Crescent Finance Ops — Reusable Skill Guide

## Environment

All API calls use the environment base URL from `environment_access.md` (which overrides any localhost references in payload files). Use HTTP, not HTTPS.

Key public endpoints:

| Endpoint | Use |
|---|---|
| `GET /api/finance/branches` | Branch metadata (id, name, region_id) |
| `GET /api/finance/period-map` | Fiscal period definitions (M1–M24, month names, fiscal years) |
| `GET /api/finance/accounts` | Chart of accounts (account name, category) |
| `GET /api/finance/records` | Monthly values per account per branch; shape: `{account, branch_id, values: {M1..M24}}` |
| `GET /api/compensation/rate-book` | Pay rates, seniority bands, title premium pcts, business rules |
| `GET /api/compensation/rosters` | Per-employee roster entries with title, overscale, weeks_by_quarter, years_of_service |
| `GET /api/compensation/scenarios` | Forecast growth rates per scenario |
| `GET /api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, weekly guarantee |
| `GET /api/payroll/productions` | Production schedule and musician roster per production |

---

## Finance (Branch / Regional Reporting)

### Account Categories

Map raw account names into reporting lines by summing all accounts in the category:

| Reporting Line | Accounts to Sum |
|---|---|
| **Revenue** | `product_revenue` + `service_revenue` |
| **COGS** | `direct_materials_cogs` + `direct_labor_cogs` |
| **Gross Margin** | Revenue − COGS |
| **SG&A** | `sales_sga` + `admin_sga` + `occupancy_sga` |
| **Allocations** | `shared_service_allocations` |
| **EBITDA** | Revenue − COGS − SG&A − Allocations |

### Fiscal Periods

The period map spans two fiscal years:
- **M1–M12** → first fiscal year (e.g. FY2024)
- **M13–M24** → second fiscal year (e.g. FY2025)

Always read the period-map endpoint to determine which FY each block maps to — do not hardcode year numbers.

### Period Convention Label

Format period labels as `"{period} ({month_name} {fiscal_year})"` using the period-map data. Example: `"M24 (Dec 2025)"`.

### ARPU

`ARPU = FY Revenue / sum of "active_customers" over the fiscal year periods`

### Sales per Labor Headcount

`Sales_per_labor_headcount = FY Revenue / sum of "labor_headcount" over the fiscal year periods`

### EBITDA Margin

`EBITDA_margin = EBITDA / Revenue` (for the relevant fiscal year)

With revenue = 0, EBITDA margin = 0.

### Growth Rates

```
revenue_growth_pct = (FY2025_revenue − FY2024_revenue) / FY2024_revenue
ebitda_growth_pct  = (FY2025_ebitda  − FY2024_ebitda)  / FY2024_ebitda
```

Guard against division by zero: return 0 when prior-year value is 0.

### Region Context

1. Identify the region for the target branch from the branches endpoint.
2. Collect all `branch_id` values belonging to that region, sorted ascending.
3. `fy2025_ebitda` is the **sum** of FY2025 EBITDA across all branches in the region.
4. `ebitda_rank_desc` is the **1-based descending** rank of the target branch's FY2025 EBITDA within the region (1 = highest EBITDA).

### Branch Rankings (All-Branch)

- **sales_growth_rank_desc**: 1-based descending rank of the target branch's revenue growth (FY2025 vs FY2024) among all branches.
- **top_sales_growth_branch_id**: The branch with the highest revenue growth.
- **top_arpu_branch_id**: The branch with the highest ARPU (FY2025 Revenue / FY2025 active_customers sum).

### MoM Revenue Variance

For a close period vs prior period:
```
amount = revenue(close_period) − revenue(prior_period)
pct    = amount / revenue(prior_period)
```

### Regional Reconciliation Variance

Compute as `0` when branch-level aggregates fully account for the region total (no top-down/bottom-up discrepancy).

---

## Compensation (Current-Year Summary)

### Rate Book Structure

- `minimum_weekly_scale` — base weekly pay for every employee
- `title_premium_pct` — mapping of title name to fraction of MWS (e.g. `"Concertmaster": 0.22`)
- `seniority_weekly` — list of bands: `{min_years, max_years, weekly_amount}`
  - `max_years: null` on the last band means "no upper bound"
  - Band selection is **inclusive** on both ends: `min_years ≤ years_of_service ≤ max_years`
- `quarter_weeks` — standard weeks per quarter (13 per quarter)
- `current_year` — the current calendar/fiscal year integer

### Pay Types (ordered as in the rate book)

1. Minimum Weekly Scale
2. Titled Position Premium
3. Seniority
4. Overscale

### Per-Employee Quarterly Calculation

For each employee and each quarter Q:

```
weeks = employee.weeks_by_quarter[Q]   # use actual roster weeks, not a fixed 13

mws   = minimum_weekly_scale × weeks
```

**Titled Position Premium**: If `combined_overscale_includes_title` is **true**, title premium = 0 (it is already bundled into overscale). Otherwise:
```
title_premium = mws × title_premium_pct[employee.title]
```
If `employee.title` is `null`, the title premium fraction is 0.

**Seniority**: Find the seniority band for `employee.years_of_service`, then:
```
seniority = band.weekly_amount × weeks
```

**Overscale**:
```
overscale = employee.overscale_weekly × weeks
```

**Quarter total** = mws + title_premium + seniority + overscale

### Roster-Wide Aggregation

- **quarter_totals**: sum of all employees' quarter totals for each of Q1–Q4.
- **annual_pay_type_totals**: sum of each pay type across all four quarters and all employees.
- **annual_total**: sum of all four annual pay-type totals.
- **largest_pay_type**: the pay type string with the highest `annual_pay_type_totals` value.
- **roster_count**: total number of employee entries for the ensemble.

### Combined Overscale Employee Count

Count of employees with `overscale_weekly > 0`. (The field name "combined overscale" reflects the payroll concept of overscale compensation that may bundle additional elements.)

### Partial Quarter Employee Count

Count of employees where **any** quarter has `weeks_by_quarter[Q] ≠ 13`. Use the actual roster weeks, not a fixed 13-week assumption.

---

## Payroll (Weekly Review)

### Rate Book

- **Service rates**: `Rehearsal` = hourly rate; `Performance`, `Audit` = per-service; `1hr Sound Check`, `2hr Sound Check` = per-service
- **Rehearsal minimum call**: 3 hours — pay for `max(actual_duration_hours, 3.0)` hours
- **Weekly guarantee**: applies only to non-substitute ("regular") players when base service pay < weekly_guarantee
- **Vacation**: 4% of (base service pay + **all** premiums) when `vacation_eligible` is true
- **Substitutes**: do not receive weekly guarantee adjustments; no special deduction unless a substitute-specific rate is documented

### Premium Categories — Critical Separation

Premiums are **two distinct categories** in the output:

| Category | Premiums Included |
|---|---|
| **premium** | `concertmaster` (20%), `principal_or_lead` (15%), `electronic` (25%), `quartet` (15%) |
| **doubles** | `first_double` (25%), `additional_double` (10% each beyond the first) |

**Do not include doubles premiums in the "premium" category.** Each category is reported separately in both the top-level `category_totals` and each musician's `categories` dict. The vacation calculation, however, uses the **sum** of both categories (all premiums).

### Premium Application

Premiums are computed **per service** as a fraction of that service's base pay, then summed across services:

```
for each assigned service:
    svc_pay = service_rate (with rehearsal minimum-call adjustment)
    premium += svc_pay × applicable_non_doubles_fractions
    doubles += svc_pay × applicable_doubles_fractions
```

- `principal_or_lead` fires when the musician is either a principal OR a lead (not both — it's a single flag at 15%)
- `first_double` fires when `doubles ≥ 1` (applies once per service)
- `additional_double` fires for each double beyond the first, i.e. `doubles - 1` times per service

### Per-Musician Categories (nonzero only)

Report only categories with nonzero amounts in the `per_musician[].categories` dict. Key names: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`.

### Top-Level Category Totals

Include all categories in `category_totals` even when zero, **except** `substitute_adjustment` which is only present when nonzero.

### Conflict Flags

Evaluate against the entire schedule (not per musician):

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any rehearsal `start_time` < `rehearsal_earliest_start` (`"09:00"`) |
| `REHEARSAL_LATE_END` | Any rehearsal `end_time` > `rehearsal_latest_end` (`"18:30"`) |
| `SERVICE_OVER_TIME_LIMIT` | Any service `duration_hours` > `service_time_limits[service_type]` |
| `SOUND_CHECK_DURATION_MISMATCH` | `"1hr Sound Check"` with duration ≠ 1.0, or `"2hr Sound Check"` with duration ≠ 2.0 |

Sort conflict flags alphabetically.

### Ordering

`per_musician` must be sorted ascending by `musician_id`. Service counts use the raw service type strings from the schedule as keys.

---

## Compensation Forecast

### Growth Rate Semantics

Scenario entries have two tiers of growth rates — `year_plus_1` and `year_plus_2`. Rates represent **sequential compounding** from the preceding year:

```
Year+1 effective rate = 1 + year_plus_1.growth
Year+2 effective rate = (1 + year_plus_1.growth) × (1 + year_plus_2.growth)
```

Apply the effective rate to the current-year base value for each pay type:

| Pay Type | Growth Applied To |
|---|---|
| Minimum Weekly Scale | `minimum_weekly_scale` |
| Seniority | Band weekly amount (determined by adjusted years of service) |
| Overscale | `employee.overscale_weekly` |
| Titled Position Premium | MWS × title_pct × cumulative `title_pct_multiplier` |

### Years of Service Adjustment

For each forecast year, **add** years of service before determining the seniority band:

| Year | Years of Service |
|---|---|
| Current | `employee.years_of_service` |
| Year + 1 | `years_of_service + 1` |
| Year + 2 | `years_of_service + 2` |

### Output Growth Rates

```
year_plus_1_vs_current   = (year_plus_1_total − current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total − year_plus_1_total) / year_plus_1_total
```

Guard against division by zero: if the denominator is 0, return 0.

### Largest Growth Pay Type

The pay type with the largest **absolute dollar** increase from current to year + 2: `max(y2_pt_total − current_pt_total)`.

### Combined Overscale and Partial Quarter Counts

Use the **current** roster (not forecast-adjusted) to compute `combined_overscale_employee_count` and `partial_quarter_employee_count`, following the same definitions as in the current-year compensation summary.

---

## Rounding Conventions

| Value Type | Decimals | Rule |
|---|---|---|
| Currency (revenue, COGS, SGA, EBITDA, ARPU, per-musician totals, payroll amounts, compensation totals, etc.) | 2 | Round half up |
| Percent / ratio (growth pct, EBITDA margin, MoM variance pct) | 4 | Round half up |

Use `ROUND_HALF_UP` (financial rounding) — not banker's rounding. Python's built-in `round()` uses banker's rounding and will produce incorrect results for `.xx5` boundary values.

---

## Ordering Conventions

- **Branch IDs in lists**: ascending (e.g. `["BR-004", "BR-005", "BR-006"]`)
- **Per-musician lists**: ascending by `musician_id`
- **Pay types**: use the order from the rate book: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- **Conflict flags**: alphabetically sorted
- **Rank fields**: descending (1 = best/highest)

---

## Common Pitfalls

1. **Doubles vs Premium separation in payroll**: Treat doubles premiums as a separate category from other premiums (concertmaster, lead, electronic, quartet). Use the sum of both only for the vacation base. Double-counting doubles in both categories inflates per-musician totals and category totals.

2. **Rehearsal minimum call**: Always apply `max(duration_hours, 3.0)` when computing rehearsal pay. The raw `duration_hours` from the schedule may be above or below 3.

3. **Growth rate compounding in forecasts**: Year+2 growth rates compound on top of Year+1 rates. Do not apply Year+2 rates directly to the current-year base — the result would show a decline if Year+2's standalone rate is lower than Year+1's.

4. **Years-of-service offset for seniority bands in forecasts**: Adding service years can push an employee into a higher seniority band, which multiplies the effect beyond just the seniority growth rate. Always determine the band using the offset years before applying the growth factor.

5. **`combined_overscale_includes_title`**: When true, skip titled position premium entirely for that employee — the title component is already reflected in their overscale amount. This field is per-employee in the roster.

6. **Rounding**: Use `ROUND_HALF_UP` (Decimal quantize), not Python's default banker's rounding. Values ending in `.xx5` will otherwise round incorrectly for financial reporting.

7. **Division by zero guards**: Always guard growth rate, margin, and ARPU calculations against zero denominators. Return `0` rather than raising an error.

8. **`substitute_adjustment`**: Only include in `category_totals` when the amount is nonzero. Unlike other category totals which are always present, this field is conditional.

9. **Active customers and labor headcount for ARPU/sales-per-headcount**: These are stored as `count`-type accounts in the finance records, summed over all periods in the fiscal year, not averaged.

10. **Period label construction**: Use the period-map endpoint's month_name and fiscal_year fields. Don't derive month names from period numbers — the mapping is defined by the API data.

11. **Weeks per quarter**: Always use the roster's `weeks_by_quarter` for each employee. Do not substitute a fixed 13-week quarter. Partial-quarter employees have non-13 values that directly affect their compensation.

12. **Service time limits**: Compare `duration_hours` (a float) against `service_time_limits[service_type]` (also a float). Don't convert to integer.
