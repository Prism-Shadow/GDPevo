---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops Reporting SOP

This skill covers three task families served by one remote API:
1. **Finance** — branch monthly-close income statements and regional management views.
2. **Compensation** — ensemble current-year pay summaries and multi-year board forecasts.
3. **Payroll** — weekly touring-production payroll control.

Always work backward from the task's `payloads/answer_template.json`: the
`required_top_level_keys`, the `field_types` tree, and the rounding/ordering
sentence in `description` are the contract. Return ONE JSON object with exactly
those top-level keys, exact sub-keys, and exact field shapes. Read
`payloads/request_memo.json` for the specific target IDs and periods.

## 1. Remote API access

- Base URL: `<remote-env-url>` (ALWAYS use this; ignore any
  `base_url` like `http://127.0.0.1:...` inside `payloads/environment_access.json`).
- All calls are HTTP GET. Useful endpoints:
  - `/api/manifest` — entity index (branch list, ensembles, productions, counts).
  - **Finance:** `/api/finance/branches`, `/api/finance/period-map`,
    `/api/finance/accounts`, `/api/finance/records` (filters `?branch_id=` `?region=` `?account=`).
  - **Compensation:** `/api/compensation/rate-book`,
    `/api/compensation/rosters?ensemble_id=`, `/api/compensation/scenarios`.
  - **Payroll:** `/api/payroll/rate-book`, `/api/payroll/productions?production_id=`.
- Endpoints that return a list of rows often need local aggregation. `/api/finance/records`
  returns one row per (branch, account) with a `values` map keyed by period `M1..M24`.
- The rate-book endpoints embed a `business_rules` array and the literal rate
  tables — read them every time; do not hard-code numbers, read them from the API.

## 2. Output conventions (apply unless the template overrides)

- Currency → round to **2 decimals**. Percent / ratio / growth → round to **4 decimals**.
- A "decimal percent" is a fraction, e.g. 9.66% is `0.0966`, NOT `9.66`.
- Lists use **ascending stable IDs** unless a rank field dictates order.
  `branch_ids` ascending; `per_musician` ordered by `musician_id`; `conflict_flags`
  sorted alphabetically.
- Emit every required key even when a value is 0. For "object mapping nonzero ...",
  omit zero entries; for fixed-key objects, include all keys.

## 3. Period <-> fiscal-year mapping (finance)

From `/api/finance/period-map`: periods `M1..M12` = **FY2024** (Jan..Dec),
`M13..M24` = **FY2025** (Jan..Dec). So `M24` = Dec FY2025, `M23` = Nov FY2025.
`period_convention.M1_to_M12 = "FY2024"`, `M13_to_M24 = "FY2025"`. The "current
month" / "prior month" labels are the raw period codes from the memo (e.g. `M24`, `M23`).

## 4. Finance: income statement and metrics

Map accounts (from `/api/finance/accounts`) to income-statement lines:

- `revenue`     = product_revenue + service_revenue
- `cogs`        = direct_materials_cogs + direct_labor_cogs
- `gross_margin`= revenue - cogs
- `sga`         = sales_sga + admin_sga + occupancy_sga
- `allocations` = shared_service_allocations
- `ebitda`      = gross_margin - sga - allocations
- `ebitda_margin` = ebitda / revenue

For any period scope, sum each account's `values` over the relevant period codes
(one month, or all 12 months of a fiscal year).

**Operating ratios — denominator is the SUM over the fiscal year, NOT an average:**
- `arpu` = FY revenue / **sum**(active_customers over the FY's 12 months).
- `sales_per_labor_headcount` = FY revenue / **sum**(labor_headcount over the FY's 12 months).
  (Using the average monthly headcount/customers is WRONG — verified.)

**Variances / growth:**
- MoM revenue variance: `amount` = rev(current month) - rev(prior month);
  `pct` = amount / rev(prior month).
- FY growth: `revenue_growth_pct` = (FY2025 rev - FY2024 rev) / FY2024 rev;
  `ebitda_growth_pct` analogous.

**Regional rollups:** a region's totals = SUM of its member branches' account values
(get members from `/api/finance/branches` by `region_id`, or `?region=` filter — both
agree and tie exactly). `region_reconciliation_variance` = region rollup minus the sum of
per-branch rollups = **0.0** (the data is internally consistent; there is no hidden adjustment).

**Rankings:**
- `ebitda_rank_desc` for a region = rank of that region among all regions by FY EBITDA, descending (1 = highest).
- `sales_growth_rank_desc` for a branch = rank among all 12 branches by FY revenue growth %, descending.
- `top_sales_growth_branch_id` / `top_arpu_branch_id` = the branch maximizing that metric across all branches
  (ARPU uses the same FY-revenue / FY-sum-of-active_customers definition).
- `top_ebitda_branch_id` / `bottom_ebitda_branch_id` within a region = max / min branch FY2025 EBITDA.

**Memo "reconcile against active operations data" note:** it is a sanity hint, not an
instruction to apply an adjustment. Always compute from the live `/api/finance/records`
data; the rollups already reconcile (variance 0).

## 5. Compensation: current-year summary

Source: `/api/compensation/rate-book` (rates + rules) and
`/api/compensation/rosters?ensemble_id=...` (one row per employee).
`current_year` and `minimum_weekly_scale` (MWS, e.g. 2520.0) come from the rate book.
Pay types, in rate-book order: `Minimum Weekly Scale`, `Titled Position Premium`,
`Seniority`, `Overscale`.

**Per-employee WEEKLY components:**
- Minimum Weekly Scale = MWS.
- Titled Position Premium = MWS x `title_premium_pct[title]` (e.g. Concertmaster 0.22,
  Principal 0.20, Section Lead 0.15, Assistant/Associate Principal 0.10). Untitled = 0.
  **If `combined_overscale_includes_title` is true for the employee, set this to 0**
  (the title premium is already folded into the overscale figure).
- Seniority = `seniority_weekly` band amount selected by `years_of_service`
  (bands: 0-4=0, 5-9=48, 10-14=82, 15-19=126, 20-24=170, 25+=215; read live values).
- Overscale = the employee's `overscale_weekly`.

**Per-quarter pay** = weekly component x `weeks_by_quarter[Q]` for that employee.
Use the roster's actual `weeks_by_quarter` (partial-quarter employees have a quarter < 13);
do NOT assume a fixed 13-week quarter.

**Aggregations:**
- `quarter_totals[Q]` = sum over employees of (all four components x weeks in Q).
- `annual_pay_type_totals[pay_type]` = sum over employees & quarters for that component.
- `annual_total` = sum of quarter totals.
- `largest_pay_type` = the pay type with the largest annual total.
- `roster_count` = number of roster rows.
- `combined_overscale_employee_count` = count of employees with
  `combined_overscale_includes_title == true` (verified: this exact flag, not "has overscale").
- `partial_quarter_employee_count` = count of employees with any `weeks_by_quarter[Q] != 13`.

## 6. Compensation: multi-year board forecast

Adds `/api/compensation/scenarios` (keyed by `scenario_id`; each has `year_plus_1`
and `year_plus_2` blocks with `mws_growth`, `overscale_growth`, `seniority_growth`,
`title_pct_multiplier`).

For each forecast year build per-employee weekly components as in section 5, with:
- **Seniority re-banding:** add 1 year of service for Year+1 and 2 years for Year+2
  BEFORE selecting the seniority band (an employee may cross into a higher band).
- **Growth multipliers COMPOUND across years** (verified far better than band-only):
  - MWS(Y+1) = MWS x (1+mws_growth_y1); MWS(Y+2) = MWS x (1+mws_growth_y1) x (1+mws_growth_y2).
  - Overscale(Y+n) compounds the same way with `overscale_growth`.
  - Seniority(Y+n) = band-amount(years+n) x (compounded (1+seniority_growth) factors).
    i.e. the COLA multiplier is applied ON TOP of the re-banded amount.
  - Title premium pct(Y+n) = base title_pct x compounded `title_pct_multiplier` factors,
    then x the grown MWS. Still 0 if `combined_overscale_includes_title`.
- Combined-overscale employees: grow the whole `overscale_weekly` by `overscale_growth`
  and keep the title premium at 0.

**Outputs:**
- `annual_totals` = {current, year_plus_1, year_plus_2} full-roster annual totals
  (current year uses MWS / overscale / bands as-is, no growth).
- `growth_rates`: `year_plus_1_vs_current` = (Y+1 total - current)/current;
  `year_plus_2_vs_year_plus_1` = (Y+2 total - Y+1 total)/Y+1 total.
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` computed for Year+2.
- `largest_growth_pay_type` = pay type with the largest growth from current to Year+2
  (Seniority typically dominates because of band crossings + COLA).
- `combined_overscale_employee_count` and `partial_quarter_employee_count` as in section 5.

## 7. Payroll: weekly production control

Source: `/api/payroll/rate-book` and `/api/payroll/productions?production_id=...`
(a production has `roster`, `schedule`, `week_start`). The rate book holds
`service_rates`, `service_time_limits`, `premium_pct`, `weekly_guarantee`,
`conflict_thresholds`, and a `business_rules` array — follow it literally.

**Service categories** (for `service_counts` and `category_totals`):
Performance->performance, Audit->audit, Rehearsal->rehearsal,
"1hr/2hr Sound Check"->sound_check. `service_counts` maps the **raw service_type string**
to its count of scheduled instances.

**Base service pay** per assigned service:
- Performance, Audit, Sound Check are **per-service flat rates** from `service_rates`.
- Rehearsal is **hourly** at the Rehearsal rate x hours, with a **3-hour minimum call**
  (pay = rate x max(duration_hours, 3)).

**Premiums** (from `premium_pct`, applied to base service pay, before vacation):
role premiums — principal_or_lead (use once if principal OR lead), quartet, electronic,
concertmaster; plus **doubles** = first extra instrument 25% + 10% per additional extra
(doubles count `d` -> 0.25 + 0.10*(d-1) when d>=1). Keep `doubles` in its own category;
`premium` holds the role premiums.

**Vacation** = 4% of (base service pay + premiums) when `vacation_eligible` is true.

**Weekly guarantee** = top-up to `weekly_guarantee` for guaranteed **regular** players
(`substitute == false`) when their base service pay is below the guarantee
(`guarantee_adjustment` = weekly_guarantee - base). Substitutes get no guarantee;
`substitute_adjustment` appears only when applicable to a substitute.

**Per-musician / totals:** sum each musician's category amounts into `categories`
(omit zero categories), `total` = sum of their categories; `per_musician` ordered by
`musician_id`; `top_paid_musician_id` = highest total; `category_totals` and
`weekly_total` are the roster-wide sums.

**Conflict flags** (enum, sorted alphabetically) — verified detection rules:
- `REHEARSAL_EARLY_START` — a Rehearsal `start_time` earlier than
  `conflict_thresholds.rehearsal_earliest_start` (e.g. 09:00).
- `REHEARSAL_LATE_END` — a Rehearsal `end_time` later than `rehearsal_latest_end` (e.g. 18:30).
- `SERVICE_OVER_TIME_LIMIT` — any service whose `duration_hours` exceeds its
  `service_time_limits` entry (e.g. a 5.5h rehearsal vs a 5.0h limit).
- `SOUND_CHECK_DURATION_MISMATCH` — a sound-check whose duration differs from its
  nominal length (1hr/2hr).
Emit the de-duplicated, alphabetically sorted set; do not emit flags that did not trigger.

> Payroll money composition (exact premium stacking, vacation/guarantee interaction,
> and substitute handling) is the most intricate part of this family. Re-derive the
> numbers strictly from the rate-book `business_rules` and rate tables for the specific
> production, and double-check each category against those rules; the conflict-flag,
> service-count, base-rate, and ordering rules above are confirmed.

## 8. Step-by-step SOP for an unseen task in this group

1. Read `prompt.txt`, `request_memo.json` (target IDs, periods, scenario, focus list),
   and `answer_template.json` (exact keys, field shapes, rounding/ordering rules).
2. Identify the domain from the requested keys: income-statement/region -> finance;
   quarter/pay-type/forecast -> compensation; service/category/per_musician -> payroll.
3. GET the relevant reference data + the target entity from the remote base URL.
4. Compute with the formulas above. For finance use FY-SUM denominators for ARPU and
   sales-per-headcount. For compensation read MWS/bands/title pcts from the rate book and
   use roster `weeks_by_quarter`. For forecasts re-band seniority by +1/+2 years and
   compound the scenario growth multipliers. For payroll follow the rate-book business
   rules line by line.
5. Round (currency 2dp, percent/ratio/growth 4dp), order lists (ascending IDs / alpha
   flags / rank fields), and assemble exactly the required top-level keys.
6. Return a single JSON object — no extra keys, no commentary.
