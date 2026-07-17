# Crescent Finance Ops — Skill Reference

## Environment

All API calls use `http://34.46.77.124:8009` as the base URL. HTTP (not HTTPS).
The service exposes three domains: Finance, Compensation, and Payroll.

### Key Endpoints

| Endpoint | Purpose |
|---|---|
| GET `/api/finance/branches` | Branch registry: branch_id, branch_name, region_id |
| GET `/api/finance/period-map` | Maps period labels (M1..M24) to fiscal years and calendar months |
| GET `/api/finance/accounts` | Account definitions with categories and metric types |
| GET `/api/finance/records` | Monthly values per (branch_id, account); keyed by period M1..M24 |
| GET `/api/compensation/rate-book` | Rate-book: MWS, quarter_weeks, seniority_weekly bands, title_premium_pct, business rules |
| GET `/api/compensation/rosters` | Employee-level: ensemble_id, title, years_of_service, overscale_weekly, weeks_by_quarter, combined_overscale_includes_title |
| GET `/api/compensation/scenarios` | Forecast growth parameters per scenario_id, for year_plus_1 and year_plus_2 |
| GET `/api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, weekly guarantee |
| GET `/api/payroll/productions` | Production roster + schedule (services with type, start/end time, duration) |

---

## Domain 1: Finance Ops (Branch / Regional / Close Reporting)

### Data Shape

**Period map**: FY2024 = M1..M12, FY2025 = M13..M24. Every M maps to one fiscal month.
Use the period-map endpoint to build the fiscal-year → period list.
The `period_convention` object maps M1_to_M12 / M13_to_M24 to year strings ("FY2024", "FY2025") and current/prior month to "Mon YYYY" labels derived from the period-map endpoint.

**Account categories** (from `/api/finance/accounts`):
- revenue: `product_revenue` + `service_revenue`
- cogs: `direct_materials_cogs` + `direct_labor_cogs`
- sga: `sales_sga` + `admin_sga` + `occupancy_sga`
- allocations: `shared_service_allocations` (single account)
- operating (count metrics): `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`

### Income Statement / EBITDA

```
revenue       = sum(product_revenue, service_revenue) over selected periods
cogs          = sum(direct_materials_cogs, direct_labor_cogs) over selected periods
gross_margin  = revenue - cogs
sga           = sum(sales_sga, admin_sga, occupancy_sga) over selected periods
allocations   = sum(shared_service_allocations) over selected periods
ebitda        = gross_margin - sga - allocations
```

**Critical rounding rule**: Compute every line from **raw (unrounded)** period sums, then round the final result to 2 decimals. Never round intermediate revenue/cogs/sga before subtracting — that introduces off-by-one-cent errors in gross_margin and ebitda.

### Ratios

- **EBITDA margin** = ebitda / revenue (4 decimals)
- **Revenue growth pct** = (current - prior) / prior (4 decimals); if prior is 0, return 0
- **ARPU** (FY2025) = FY2025 revenue / FY2025 `active_customers` sum (2 decimals, currency)  
  Use the **sum** of `active_customers` across all 12 months of the fiscal year as the denominator.
- **Sales per labor headcount** (FY2025) = FY2025 revenue / FY2025 `labor_headcount` sum (2 decimals, currency)

### MoM Revenue Variance

For a single month:
- `amount` = revenue(current_month) - revenue(prior_month), rounded to 2 decimals
- `pct` = amount / revenue(prior_month), rounded to 4 decimals

### Region Context

- `branch_ids`: all branches in the region, **sorted ascending** by branch_id
- `fy2025_ebitda`: sum of ebitda for all branches in the region across FY2025 periods, rounded to 2 decimals
- `ebitda_rank_desc`: rank of the region among **all regions** by FY2025 EBITDA (1 = highest)

### Branch Rankings

- Compute revenue growth for **every branch** as (FY2025_revenue - FY2024_revenue) / FY2024_revenue
- `sales_growth_rank_desc`: rank of the target branch by revenue growth (1 = highest)
- `top_sales_growth_branch_id`: branch with the highest revenue growth across ALL branches
- `top_arpu_branch_id`: branch with the highest ARPU (FY2025 revenue / FY2025 active_customers sum) across ALL branches

---

## Domain 2: Compensation (Current-Year & Forecast)

### Rate Book Constants

- `minimum_weekly_scale` (MWS): base weekly rate for all musicians
- `quarter_weeks`: default weeks per quarter (typically {"Q1":13, "Q2":13, "Q3":13, "Q4":13})
- `seniority_weekly`: list of bands `[{min_years, max_years, weekly_amount}, ...]`  
  Use `min_years <= years_of_service <= max_years` (inclusive both ends; `null` max means no upper bound).
- `title_premium_pct`: map of title name to decimal percentage (e.g. "Concertmaster": 0.22, "Principal": 0.20, "Section Lead": 0.15).  
  A `None` title or a title not in the map gets 0 title premium.
- `pay_types`: ordered list `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`

### Per-Employee Quarterly Compensation

For each employee in the target ensemble, for each quarter Q:

```
weeks = weeks_by_quarter[Q]          # use actual roster weeks, not a hardcoded 13

base    = mws * weeks
title   = mws * title_premium_pct * weeks   # BUT set to 0 when combined_overscale_includes_title is true
seniority = seniority_weekly_amount * weeks   # band selected from years_of_service
overscale = overscale_weekly * weeks

quarter_total[Q] = round(base + title + seniority + overscale, 2)
```

Accumulate per pay-type across all quarters **without intermediate rounding**, then round each pay-type total to 2 decimals:

```
annual_pay_type_totals["Minimum Weekly Scale"]     = round(sum of all base across all employees & quarters, 2)
annual_pay_type_totals["Titled Position Premium"]  = round(sum of all title across all employees & quarters, 2)
annual_pay_type_totals["Seniority"]                = round(sum of all seniority across all employees & quarters, 2)
annual_pay_type_totals["Overscale"]                = round(sum of all overscale across all employees & quarters, 2)
```

### Quarter Totals & Annual Total

```
quarter_totals[Q] = round(sum of quarter_total[Q] across all employees, 2)
annual_total = round(sum of annual_pay_type_totals values, 2)
```

### Roster Counts

- **roster_count**: number of employees in the ensemble
- **combined_overscale_employee_count**: count of employees where `combined_overscale_includes_title` is `true`
- **partial_quarter_employee_count**: count of employees where `weeks_by_quarter` differs from the default `quarter_weeks` (check any quarter's weeks ≠ expected)
- **largest_pay_type**: the key in `annual_pay_type_totals` with the highest value

### Forecast (Scenarios)

Scenario object (e.g. `case_maple_board`) has `year_plus_1` and `year_plus_2` blocks, each with:
- `mws_growth`: growth rate applied to MWS (compounds: Y2 = Y1 × (1+g2))
- `overscale_growth`: growth rate applied to each employee's `overscale_weekly`
- `seniority_growth`: growth rate applied to the `weekly_amount` in each seniority band
- `title_pct_multiplier`: multiplier applied to each title's premium percentage

**Business rule from rate book**: "For forecast years, add one year of service for Year + 1 and two years of service for Year + 2 before assigning seniority bands."

Forecast computation (Year + 1):
1. MWS_Y1 = MWS_current × (1 + y1.mws_growth)
2. Seniority bands: scale each band's `weekly_amount` × (1 + y1.seniority_growth)
3. Title pcts: scale each by y1.title_pct_multiplier
4. Employee overscale_weekly × (1 + y1.overscale_growth)
5. Employee years_of_service = original + 1
6. Compute per-employee and totals using the same formulas as current year

Forecast computation (Year + 2):
1. MWS_Y2 = MWS_Y1 × (1 + y2.mws_growth)
2. Seniority bands: scale Y1 bands × (1 + y2.seniority_growth)
3. Title pcts: scale each by y2.title_pct_multiplier
4. Employee overscale = original × (1 + y1.overscale_growth) × (1 + y2.overscale_growth)
5. Employee years_of_service = original + 2
6. Compute per-employee and totals

**Growth rates** (round to 4 decimals):
```
year_plus_1_vs_current  = round((Y1_total - current_total) / current_total, 4)
year_plus_2_vs_year_plus_1 = round((Y2_total - Y1_total) / Y1_total, 4)
```
If denominator is 0, return 0.

**largest_growth_pay_type**: compare Year+2 pay-type totals against current pay-type totals. The pay type with the largest **absolute dollar increase** wins.

---

## Domain 3: Payroll (Weekly Production)

### Rate Book

- **service_rates**: flat per-service rates for Performance, Audit, 1hr Sound Check, 2hr Sound Check. Rehearsal: hourly rate.
- **service_time_limits**: max hours for each service type.
- **premium_pct**: percentages for principal_or_lead, quartet, electronic, concertmaster, first_double, additional_double, vacation.
- **conflict_thresholds**: `rehearsal_earliest_start` ("09:00"), `rehearsal_latest_end` ("18:30").
- **weekly_guarantee**: the minimum total base service pay for non-substitute musicians.

### Per-Musician-Pay Computation

For each musician, for each assigned service (looked up from the schedule by service_id):

**1. Base service pay:**
- **Rehearsal**: hourly_rate × max(duration_hours, 3.0)   ← 3-hour minimum call
- **Performance, Audit**: flat `service_rates[service_type]`
- **1hr Sound Check, 2hr Sound Check**: flat `service_rates[service_type]`

**2. Premiums** (per-service percentages applied to the service's base pay):
- If principal=True or lead=True: +`premium_pct.principal_or_lead`
- If quartet=True: +`premium_pct.quartet`
- If electronic=True: +`premium_pct.electronic`
- If musician has a concertmaster role (check roster flags): +`premium_pct.concertmaster`

Sum all applicable premium percentages × service_base_pay for each service.

**3. Doubles premium** (per-service):
- If doubles ≥ 1: +`premium_pct.first_double` × service_base_pay
- If doubles ≥ 2: +`premium_pct.additional_double` × (doubles − 1) × service_base_pay

**4. Vacation** (per-service):
- If vacation_eligible: 0.04 × (service_base_pay + premium_amount + doubles_amount)

**5. Weekly guarantee** (per musician, after summing all services):
- `total_base_service_pay` = sum of all service_base_pay for this musician (raw rates only, no premiums, no doubles)
- If musician is NOT a substitute AND `total_base_service_pay < weekly_guarantee`:
  `guarantee_adjustment = weekly_guarantee - total_base_service_pay`

**6. Substitute adjustment**: Generally 0 unless there is a specific substitute rate rule. Substitute musicians do not qualify for the weekly guarantee.

### Category Totals

Sum across all musicians:

| Category | What it includes |
|---|---|
| `performance` | Base rates of all Performance services |
| `audit` | Base rates of all Audit services |
| `rehearsal` | Base rates of all Rehearsal services (including 3-hour minimum) |
| `sound_check` | Base rates of all Sound Check services |
| `premium` | All principal/lead, quartet, electronic, concertmaster premiums |
| `doubles` | All doubles (first + additional) premiums |
| `vacation` | All vacation pay |
| `guarantee_adjustment` | All weekly guarantee top-ups |
| `substitute_adjustment` | Substitute-specific adjustments (may be 0) |

`weekly_total = round(sum of all category_totals, 2)`

### Service Counts

Map each `service_type` in the schedule to its integer count: `{"Performance": N, "Rehearsal": N, ...}`.

### Conflict Flags

Inspect every service in the schedule. Flags to add:

- **REHEARSAL_EARLY_START**: any Rehearsal with `start_time < conflict_thresholds.rehearsal_earliest_start`
- **REHEARSAL_LATE_END**: any Rehearsal with `end_time > conflict_thresholds.rehearsal_latest_end`
- **SERVICE_OVER_TIME_LIMIT**: any service where `duration_hours > service_time_limits[service_type]`
- **SOUND_CHECK_DURATION_MISMATCH**: any "1hr Sound Check" with `duration_hours > 1.0` OR any "2hr Sound Check" with `duration_hours > 2.0`

Sort the resulting set **alphabetically**.

### Per-Musician Output

Order by `musician_id` ascending. For each musician include:
- `musician_id`, `name`, `total` (currency, 2 decimals)
- `categories`: object mapping **only nonzero** category amounts to rounded currency values

### Top-Paid Musician

The musician with the highest `total` — return their `musician_id`.

---

## General Conventions

### Rounding

| Type | Precision |
|---|---|
| Currency amounts | 2 decimals |
| Percent / ratio | 4 decimals |
| Integers (counts, ranks) | No rounding |

Always round at the **final computation step**, not intermediate values. Computing `round(A-B, 2)` from raw A and B is correct; computing `round(round(A,2)-round(B,2), 2)` introduces cascading errors.

### Ordering

- Lists of branch_ids / employee_ids / musician_ids: **ascending sort** by their string ID
- `conflict_flags`: alphabetical sort
- `per_musician` list: ordered by musician_id
- `pay_types`: use the order from the rate-book's `pay_types` array

### Dates and Time Comparisons

- Time strings are in "HH:MM" 24-hour format — compare as strings (lexicographic comparison works for this format)
- Duration comparisons use the numeric `duration_hours` field

### Common Pitfalls

1. **Don't hardcode periods or fiscal year mappings** — always fetch `/api/finance/period-map` and derive the FY→M mapping dynamically.
2. **Don't use the local URL from payload `environment_access.json`** — the remote `http://34.46.77.124:8009` overrides all local references.
3. **Don't round intermediates** in income-statement chains (revenue→gross_margin→ebitda) — round only the final outputs.
4. **Title premium is MWS-based**, not total-pay-based: `mws × title_pct × weeks`, not `(mws + seniority + overscale) × title_pct`.
5. **`combined_overscale_includes_title`**: when true, title premium is zero, regardless of title. The overscale is presumed to include it.
6. **Forecast seniority bands**: apply the `seniority_growth` rate to the band amounts AND increase `years_of_service` — both effects compound.
7. **Rehearsal minimum call**: applied per-service as `max(duration_hours, 3.0)`, not as a flat 3 hours.
8. **Substitute musicians**: never receive the weekly guarantee adjustment.
9. **Vacation is on (base + premium + doubles)**, not just base, and only when `vacation_eligible` is true.
10. **ARPU denominator**: use `active_customers` summed across all periods, not averaged per-month and not `revenue_units`.
11. **Sales per labor headcount**: sum `labor_headcount` across all periods as the denominator.
12. **Doubles premium**: `first_double` applies for doubles≥1; `additional_double` applies per extra beyond the first. The total doubles premium percentages sum: `first_double_pct + additional_double_pct × max(0, doubles−1)`.
