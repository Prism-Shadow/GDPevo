# Worked examples & field-level reference

These are the concrete numbers used to validate every rule. Use them to sanity-check
your own implementation: if you can reproduce these exact figures from the live API,
your pipeline is correct. (These are train cases; real tasks use different
branches/ensembles/productions but the SAME rules.)

## Endpoint data shapes

### Finance
- `/api/finance/branches` -> `[{branch_id, branch_name, region_id, region_name}]` (12 branches, 4 regions)
- `/api/finance/period-map` -> `[{period:"M1".."M24", month_number:1..12, month_name, fiscal_year}]`
  - **M1..M12 = FY2024, M13..M24 = FY2025.** A period's fiscal year is whatever period-map says; do not hard-code -- read it.
- `/api/finance/accounts` -> chart of accounts with `account`, `category`, `metric_type`.
  - revenue: `product_revenue`, `service_revenue`
  - cogs: `direct_materials_cogs`, `direct_labor_cogs`
  - sga: `sales_sga`, `admin_sga`, `occupancy_sga`
  - allocations: `shared_service_allocations`
  - operating (counts): `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`
- `/api/finance/records` -> one row per (branch, account) with `values: {"M1":..,"M24":..}`.
  **Note the shape**: values is a dict keyed by period, NOT a flat period column.

### Compensation
- `/api/compensation/rate-book` -> `minimum_weekly_scale` (2520.0), `pay_types` (ordered),
  `title_premium_pct` (by title), `seniority_weekly` (bands), `quarter_weeks` (standard 13),
  `business_rules` (read them).
- `/api/compensation/rosters?ensemble_id=` -> per-employee: `years_of_service`, `title`,
  `overscale_weekly`, `weeks_by_quarter`, `combined_overscale_includes_title`, `notes`.
- `/api/compensation/scenarios` -> per scenario: `year_plus_1` / `year_plus_2` each with
  `mws_growth`, `seniority_growth`, `overscale_growth`, `title_pct_multiplier`.

### Payroll
- `/api/payroll/rate-book` -> `service_rates`, `premium_pct`, `service_time_limits`,
  `conflict_thresholds`, `weekly_guarantee` (2082.0), `business_rules` (read them).
- `/api/payroll/productions?production_id=` -> `schedule` (services w/ times, duration) +
  `roster` (musicians w/ flags & `assigned_service_ids`).

## Validated train numbers (reproduce these exactly)

### 001 branch close (BR-004 Harbor North, close M24, prior M23)
- M24 income statement: revenue 293306.29, cogs 108946.99, gross_margin 184359.30,
  sga 100245.35, allocations 9280.16, ebitda 74833.79
- MoM revenue variance: amount 3996.15, pct 0.0138
- FY2025: revenue 3483871.60, cogs 1316927.67, gross_margin 2166943.93, sga 1198495.73,
  allocations 111838.10, ebitda 856610.10, ebitda_margin 0.2459, arpu 999.39,
  sales_per_labor_headcount 24534.31
- revenue_growth_pct 0.0966, ebitda_growth_pct 0.1423
- region REG-WEST = [BR-004, BR-005, BR-006], fy2025_ebitda 2515012.15, ebitda_rank_desc 3 (of 4 regions)
- sales_growth_rank_desc 2, top_sales_growth_branch BR-002, top_arpu_branch BR-012

### 002 comp current year (ENS-REDWOOD, current_year 2026, roster_count 26)
- quarter_totals Q1 977636.40, Q2 953292.40, Q3 969086.40, Q4 977636.40
- pay-type totals: MWS 3379320.00, Titled 297561.60, Seniority 142790.00, Overscale 57980.00
- annual_total 3877651.60, largest_pay_type "Minimum Weekly Scale"
- combined_overscale 0, partial_quarter 3

### 003 payroll (PROD-HAMILTON-26)
- service_counts: Performance 4, Rehearsal 2, Audit 1, 1hr Sound Check 1
- category_totals: performance 5725.50, rehearsal 2467.50, audit 520.50, sound_check 160.00,
  premium 1773.88, doubles 1535.23, vacation 378.00, guarantee_adjustment 1276.25,
  substitute_adjustment 520.50
- weekly_total 14357.36, conflict_flags [REHEARSAL_EARLY_START, SERVICE_OVER_TIME_LIMIT]
- top_paid M-H26-01
- M-H26-01 (substitute, electronic, 1 double): perf 1561.50 (=1041*1.5), audit 260.25,
  substitute_adjustment 520.50 (=1041*0.5), premium 455.44 (=0.25*(1561.5+260.25)),
  doubles 455.44, total 3253.13. NB no guarantee (substitute).
- M-H26-02 (lead+quartet, vac): base 1737.875 -> premium 0.30*base=521.36,
  vacation 0.04*(base+premium)=90.37, guarantee 2082-1737.875=344.13. total 2693.73

### 004 regional (REG-WEST, years 2024 & 2025)
- branch_ids [BR-004, BR-005, BR-006]
- fy2024: revenue 10453506.76, sga 3763931.94, allocations 354160.21, ebitda 2310369.33
- fy2025: revenue 11139674.79, sga 3935915.21, allocations 376735.89, ebitda 2515012.15,
  ebitda_margin 0.2258, sales_per_labor_headcount 24809.97
- revenue_growth_pct 0.0656, top_ebitda_branch BR-005, bottom_ebitda_branch BR-006
- region_reconciliation_variance 0.0 (rollup ties to active operating data)

### 005 forecast (ENS-MAPLE, case_maple_board)
- annual_totals: current 4232653.60, year_plus_1 4390313.80, year_plus_2 4545741.02
  (NB year_plus_1 = sum of ROUNDED quarter totals = 4390313.80, NOT r2 of raw sum 4390313.79)
- growth_rates: y+1 vs current 0.0372, y+2 vs y+1 0.0354
- year_plus_2 quarters: Q1 1129891.58, Q2 1138616.48, Q3 1138616.48, Q4 1138616.48
- year_plus_2 pay-types: MWS 3914775.18, Titled 320833.74, Seniority 190829.80, Overscale 119302.29
- largest_growth_pay_type "Seniority" (PERCENT growth 0.2331 >> MWS 0.0692; re-banding drives it,
  even though MWS grows the most in DOLLARS). combined_overscale 4, partial_quarter 1

## Compensation pay-component formulas (per employee, per quarter, weeks = weeks_by_quarter[Q])
- Minimum Weekly Scale = MWS * weeks
- Titled Position Premium = MWS * title_premium_pct[title] * title_pct_multiplier * weeks
  ... but **0 if combined_overscale_includes_title is true** for that employee.
- Seniority = seniority_weekly(years) * seniority_scale * weeks
- Overscale = overscale_weekly * overscale_scale * weeks
Forecast escalation (compounded from base, NOT additive):
  Y+1: MWS*(1+mws_growth_1); seniority_scale=(1+seniority_growth_1);
       overscale_scale=(1+overscale_growth_1); title_mult=title_pct_multiplier_1; years+1
  Y+2: MWS*(1+mws_growth_1)*(1+mws_growth_2); scales/mult compounded across both years; years+2

## Payroll pay-component formulas (per musician)
- base service pay: Performance/Audit/Sound Check = per-service rate; Rehearsal = rate * max(hours, 3).
- SUBSTITUTE: performance category += 0.5 * perf_base AND a separate
  substitute_adjustment line = 0.5 * perf_base. (Net: substitute earns 2x on performances,
  split across the two lines.) Substitutes get NO guarantee adjustment.
- premium % = sum of applicable: principal_or_lead 0.15 (if lead OR principal), quartet 0.15,
  electronic 0.25 (concertmaster 0.20 if a `concertmaster` flag exists). Applied to base
  service pay (after substitute uplift to performance).
- doubles: first_double 0.25 + additional_double 0.10 * (doubles - 1), applied to base service pay.
- vacation (if vacation_eligible): 0.04 * (base service pay + premium + doubles).
- guarantee_adjustment (non-substitute only): weekly_guarantee - base service pay, if base < guarantee.
- conflict flags: REHEARSAL_EARLY_START (rehearsal start < earliest), REHEARSAL_LATE_END
  (rehearsal end > latest), SERVICE_OVER_TIME_LIMIT (any service duration > its time limit),
  SOUND_CHECK_DURATION_MISMATCH (sound-check duration != its nominal 1.0/2.0 hours).
