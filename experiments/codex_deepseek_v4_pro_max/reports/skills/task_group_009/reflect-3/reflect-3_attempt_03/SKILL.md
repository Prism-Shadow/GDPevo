 # Crescent Arts Collective — Finance Ops Skill

 ## Overview

 This skill covers the Crescent Arts Collective Finance Ops API for branch financial reporting, ensemble compensation, and weekly production payroll. The API is served at an environment-provided base URL with no authentication required on GET requests. All endpoints return JSON arrays or objects.

 ## Available Endpoints

 ### Finance Module
 - `GET /api/finance/branches` — list of branch objects (`branch_id`, `branch_name`, `region_id`, `region_name`).
 - `GET /api/finance/period-map` — maps period labels (`M1`–`M24`) to fiscal years and calendar months. `M1`–`M12` belong to FY2024; `M13`–`M24` belong to FY2025.
 - `GET /api/finance/accounts` — chart of accounts with `account`, `category`, `display_name`, and `metric_type` (`currency` or `count`).
 - `GET /api/finance/records` — per-branch, per-period values keyed by account name. Each record has `account`, `branch_id`, `branch_name`, `region_id`, and a `values` object mapping period labels to numeric amounts.

 ### Compensation Module
 - `GET /api/compensation/rate-book` — current-year rates including `minimum_weekly_scale`, `seniority_weekly` (bands by years of service), `title_premium_pct` (by title name), `pay_types` (ordered list), `quarter_weeks`, and `business_rules`.
 - `GET /api/compensation/rosters` — all employees across ensembles. Each employee has `employee_id`, `ensemble_id`, `title`, `overscale_weekly`, `years_of_service`, `weeks_by_quarter`, `combined_overscale_includes_title`, and `notes`.
 - `GET /api/compensation/scenarios` — forecast scenarios keyed by scenario id, each with `year_plus_1` and `year_plus_2` objects containing `mws_growth`, `overscale_growth`, `seniority_growth`, and `title_pct_multiplier`.

 ### Payroll Module
 - `GET /api/payroll/rate-book` — service rates, premium percentages, conflict thresholds, service time limits, and weekly guarantee amount plus `business_rules`.
 - `GET /api/payroll/productions` — production objects with `production_id`, `roster` (musicians and their service assignments), and `schedule` (services with type, duration, start/end times).

 ## Finance Module Conventions

 ### Revenue and Cost Aggregation
 - **Revenue** = sum of `product_revenue` + `service_revenue`.
 - **COGS** = sum of `direct_materials_cogs` + `direct_labor_cogs`.
 - **Gross Margin** = Revenue − COGS.
 - **SG&A** = `sales_sga` + `admin_sga` + `occupancy_sga`.
 - **Allocations** = `shared_service_allocations`.
 - **EBITDA** = Gross Margin − SG&A − Allocations.

 ### Period to Fiscal Year Mapping
 - `M1`–`M12` = FY2024.
 - `M13`–`M24` = FY2025.
 - Sum values across the relevant period range to obtain fiscal-year totals.

 ### Ratios and Per-Unit Metrics
 - **EBITDA Margin** = EBITDA / Revenue (round to 4 decimal places).
 - **Revenue Growth** = (FY2025 Revenue − FY2024 Revenue) / FY2024 Revenue (round to 4 decimals).
 - **ARPU** = Annual Revenue / sum of `active_customers` across the 12 FY periods (round to 2 decimals).  Use the *sum* of per-period customer counts across all months, not the average.
 - **Sales per Labor Headcount** = Annual Revenue / sum of `labor_headcount` across the 12 FY periods (round to 2 decimals).  Use the *sum*, not the average.

 ### Region and Branch Rankings
 - Region branch IDs must be **sorted in ascending string order**.
 - **EBITDA rank** within a region is 1‑based descending (highest EBITDA = rank 1).  Compute FY2025 EBITDA per branch, sort descending, and assign ranks.
 - **Sales growth rank** across all branches uses the same descending rule on percentage revenue growth.
 - Region‑level `fy2025_ebitda` is the sum of all member‑branch FY2025 EBITDAs.
 - **Top ARPU** branch is the one with the highest ARPU (computed per the formula above) across all branches.

 ### Reconciliation Variance
 - When the region total equals the sum of branch‑level values the variance is `0` (or `0.0`/`0.00`).

 ### Period Convention Label
 - Use plain period identifiers for `current_month` / `prior_month` (e.g. `"M24"`, `"M23"`), **not** month names or descriptive strings.

 ## Compensation Module Conventions

 ### Current‑Year Compensation per Employee
 For each employee:
 1. **Minimum Weekly Scale** = `minimum_weekly_scale × weeks_in_quarter` (use the employee's actual `weeks_by_quarter`, not a fixed 13).
 2. **Titled Position Premium** = `minimum_weekly_scale × title_premium_pct × weeks`, **unless** `combined_overscale_includes_title` is `true` **and** the employee has a non‑zero overscale amount — in that case the title premium is 0.
 3. **Seniority** = `seniority_weekly` band amount (matching `years_of_service` to the correct band) × weeks.
 4. **Overscale** = `overscale_weekly × weeks`.

 Summing across quarters for each pay type gives the annual pay‑type totals.  Quarterly totals are the sum of all four components across all employees for that quarter.

 ### Roster Counts
 - **roster_count** = number of employees in the ensemble.
 - **combined_overscale_employee_count** = count of employees where `combined_overscale_includes_title` is `true` **and** `overscale_weekly > 0`.
 - **partial_quarter_employee_count** = count of employees whose `notes` contain the substring `"Partial-quarter"`.

 ### Largest Pay Type
 - Compare the rounded currency values in `annual_pay_type_totals` and return the enum string of the largest.

 ### Forecast (Scenario) Computation
 - Apply scenario parameters with **compounding**: Year‑plus‑1 values build on current base; Year‑plus‑2 values build on Year‑plus‑1 results.
   - **MWS**: `cur × (1 + y1.mws_growth) × (1 + y2.mws_growth)` for Year‑plus‑2.
   - **Seniority bands**: multiply each band's `weekly_amount` cumulatively.
   - **Overscale**: multiply each employee's `overscale_weekly` cumulatively.
   - **Title premiums**: multiply each title's percentage cumulatively.
 - **Years of service**: add 1 for Year‑plus‑1, add 2 for Year‑plus‑2 before looking up the seniority band.
 - Growth rates: `(Y1_total − cur_total) / cur_total` and `(Y2_total − Y1_total) / Y1_total`, each rounded to 4 decimals.
 - `largest_growth_pay_type`: compare Year‑plus‑2 pay‑type totals to current‑year pay‑type totals; the pay type with the largest absolute dollar increase wins.

 ## Payroll Module Conventions

 ### Service Pay Calculation
 - **Rehearsal**: hourly rate (`$58.75/hr`) with a **3‑hour minimum call**.  Pay = `max(actual_duration_hours, 3.0) × hourly_rate`.
 - **Performance, Audit**: flat per‑service rate (`$260.25`).
 - **Sound Check**: flat per‑service rate (`$80.00` for 1‑hr, `$142.50` for 2‑hr).

 ### Premiums (applied to total base service pay)
 - **principal_or_lead**: 15% if `principal` or `lead` is true.
 - **quartet**: 15% if `quartet` is true.
 - **electronic**: 25% if `electronic` is true.
 - **first_double**: 25% if `doubles ≥ 1`.
 - **additional_double**: 10% per extra instrument beyond the first (if `doubles ≥ 2`).

 ### Vacation
 - 4% of (base service pay + all premiums including doubles) when `vacation_eligible` is `true`.

 ### Weekly Guarantee
 - If the musician is **not** a substitute and their **base service pay** (before premiums, doubles, or vacation) is below `$2,082.00`, add the difference as `guarantee_adjustment`.

 ### Substitute Adjustment
 - Include `substitute_adjustment` as `0` in category totals when no special substitute rules are provided.

 ### Conflict Flags (sorted alphabetically)
 - **REHEARSAL_EARLY_START**: rehearsal `start_time` before `09:00`.
 - **REHEARSAL_LATE_END**: rehearsal `end_time` after `18:30`.
 - **SERVICE_OVER_TIME_LIMIT**: service `duration_hours` exceeds the limit in `service_time_limits`.
 - **SOUND_CHECK_DURATION_MISMATCH**: sound‑check actual duration does not match its label (1.0 hr for 1‑hr, 2.0 hr for 2‑hr).

 ### Per‑Musician Output
 - List sorted by `musician_id` ascending.
 - `categories` maps only **nonzero** category amounts (omit zero‑value keys).
 - `top_paid_musician_id` is the musician with the highest `total`.

 ### Service Counts
 - Map schedule service‑type strings (as they appear in the schedule, e.g. `"Rehearsal"`, `"1hr Sound Check"`) to integer counts.  Only include types that actually appear.

 ## General Output Rules
 - Return a **single JSON object** matching the answer template structure exactly.
 - **Currency** fields: round to 2 decimal places.
 - **Percent / ratio** fields: round to 4 decimal places.
 - **Lists**: sort by ascending stable ID unless a rank field dictates otherwise.
 - Include all required top‑level keys; do not add extra keys.
 - Compute values directly from the API responses — do not hard‑code constants derived from specific training tasks.
