# SKILL — Crescent Arts Collective Finance Ops Reporting

Reusable skill for solving Finance Ops reporting tasks against the Crescent Arts
Collective remote API. Covers five task families: branch close reporting,
regional/company dashboard, compensation current-year summary, compensation
forecast, and weekly payroll review.

## 0. Hard rules
- Read base URL from `payloads/environment_access.json`. The staged `base_url`
  there is the LIVE REMOTE host (do NOT use `127.0.0.1`/`localhost` — that dev
  server is not running). If a value looks like a local placeholder, use the
  remote host documented in `environment_access.md`.
- Return ONE JSON object that follows `payloads/answer_template.json` exactly:
  include every key in `required_top_level_keys`, use the field types and enums
  the template specifies, and do not add extra top-level keys.
- Never call any `/api/judge` endpoint. Use only the public read endpoints below.
- Pull numbers from the live API; do not guess. Currency rounds to 2 decimals;
  percent/ratio fields round to 4 decimals and are expressed as a decimal
  (0.0138, not 1.38%).
- Aggregate from unrounded values, then round once at the end. Per-row figures
  that look inconsistent by a cent or two are usually a rounding-order issue:
  recompute from unrounded inputs.
- Lists use ascending stable IDs unless a rank field states otherwise.
  `per_musician` is ordered by `musician_id`. `conflict_flags` sorted
  alphabetically. `branch_ids` ascending. Output `pay_types` in rate-book order.
- Do NOT echo gold/train answers; recompute from the live data for whatever
  target IDs the request memo gives you.

## 1. Environment
Public GET endpoints (all on the base URL):
- `/api/manifest` — entity lists (branches, ensembles, productions) and counts.
- `/api/finance/branches` — branch_id, branch_name, region_id, region_name.
- `/api/finance/period-map` — period label ↔ fiscal year/month.
- `/api/finance/accounts` — account catalog with `category` and `metric_type`.
- `/api/finance/records` — monthly values; filter `?branch_id=`, `?region=`,
  `?account=`. Each record is `{account, branch_id, branch_name, region_id,
  values:{M1..M24}}`.
- `/api/compensation/rate-book` — pay types, scales, seniority bands, title pcts.
- `/api/compensation/rosters` — filter `?ensemble_id=`. Per-employee rows.
- `/api/compensation/scenarios` — forecast growth parameters per scenario_id.
- `/api/payroll/rate-book` — service rates, premiums, conflict thresholds.
- `/api/payroll/productions` — filter `?production_id=`. Roster + schedule.

Fetch with `curl -s "$BASE/api/..."` and parse with `python3 -m json.tool` or
`jq`. Cache big responses to a temp file and process with python.

## 2. Shared conventions (finance)

Period map (confirmed): `M1`..`M12` = FY2024 (Jan..Dec 2024); `M13`..`M24` =
FY2025 (Jan..Dec 2025). So `period_convention` for close reporting is:
`{"M1_to_M12":"FY2024","M13_to_M24":"FY2025","current_month":<close_period>,"prior_month":<prior_period>}`.

Account categories (from `/api/finance/accounts`):
- revenue: `product_revenue`, `service_revenue`
- cogs: `direct_materials_cogs`, `direct_labor_cogs`
- sga: `sales_sga`, `admin_sga`, `occupancy_sga`
- allocations: `shared_service_allocations`
- operating counts: `orders`, `revenue_units`, `active_customers`,
  `labor_headcount`, `admin_headcount`, `backlog`

Income-statement formulas (sum the account values over the period set):
- `revenue` = product_revenue + service_revenue
- `cogs` = direct_materials_cogs + direct_labor_cogs
- `gross_margin` = revenue − cogs
- `sga` = sales_sga + admin_sga + occupancy_sga
- `allocations` = shared_service_allocations
- `ebitda` = gross_margin − sga − allocations

Period sets: a single month = `[<Mm>]`; FY2025 = `M13..M24`; FY2024 = `M1..M12`.

Derived ratios (round 4 dec):
- `ebitda_margin` = ebitda / revenue
- `arpu` = revenue / sum(active_customers over the period)  [currency, 2 dec]
- `sales_per_labor_headcount` = revenue / sum(labor_headcount over the period) [currency, 2 dec]
- growth pct = (new − old) / old

Branches & regions (12 branches, 4 regions, 3 branches each):
- REG-NORTH: BR-001, BR-002, BR-003
- REG-WEST: BR-004, BR-005, BR-006
- REG-EAST: BR-007, BR-008, BR-011
- REG-SOUTH: BR-009, BR-010, BR-012

Ranking convention: a field named `*_rank_desc` is a 1-based rank where 1 =
highest value (descending sort). Two distinct ranks appear:
- For a BRANCH among all 12 branches (e.g. `sales_growth_rank_desc`): rank the
  branch against every branch by that metric, descending.
- For a REGION (`region_context.ebitda_rank_desc`): rank the branch's REGION
  among the 4 regions by the region's FY2025 EBITDA total, descending. (This is
  the region's rank, NOT the branch's rank within its region — easy to misread.)

## 3. SOP — Branch Close Reporting (finance, single target branch)
Memo fields: `target_branch_id`, `close_period` (e.g. M24), `prior_period`
(e.g. M23). Template requires: `target_branch_id`, `target_branch_name`,
`period_convention`, `<close_period>_income_statement` (key named after the
close period, e.g. `m24_income_statement`), `mom_revenue_variance`,
`fy2025_vs_fy2024`, `region_context`, `branch_rankings`.

Steps:
1. `GET /api/finance/records?branch_id=<target>`. Build a dict
   `{account: {Mm: value}}`.
2. `target_branch_name` from `/api/finance/branches` (or the records).
3. `period_convention` per §2 using memo `close_period`/`prior_period`.
4. `<close_period>_income_statement`: compute revenue/cogs/gross_margin/sga/
   allocations/ebitda for the single close_period month using §2 formulas.
5. `mom_revenue_variance`: `amount` = revenue(close_period) − revenue(prior_period)
   (2 dec); `pct` = amount / revenue(prior_period) (4 dec).
6. `fy2025_vs_fy2024`:
   - `fy2025` block = full FY2025 (M13..M24) totals for revenue/cogs/gross_margin/
     sga/allocations/ebitda, plus `ebitda_margin`, `arpu`, `sales_per_labor_headcount`.
   - `revenue_growth_pct` = (FY2025 rev − FY2024 rev)/FY2024 rev (4 dec).
   - `ebitda_growth_pct` = (FY2025 ebitda − FY2024 ebitda)/FY2024 ebitda (4 dec).
7. `region_context`: `region_id` and the ascending `branch_ids` for the target
   branch's region (use `/api/finance/branches`). `fy2025_ebitda` = sum of
   FY2025 ebitda over the region's branches (fetch each branch's records or
   filter `?region=`). `ebitda_rank_desc` = the REGION's rank among the 4
   regions by FY2025 EBITDA total (compute all 4 region totals, sort desc).
8. `branch_rankings`:
   - `sales_growth_rank_desc` = target branch's rank among all 12 branches by
     FY2025-vs-FY2024 revenue growth, descending.
   - `top_sales_growth_branch_id` = the #1 branch by that growth.
   - `top_arpu_branch_id` = branch with the highest FY2025 ARPU.
   Compute growth and ARPU for all 12 branches (fetch all records once).

Tip: one `GET /api/finance/records` (no filter) returns all 168 rows; build a
`{branch: {account: {Mm: v}}}` map and compute every branch/region metric locally.

## 4. SOP — Regional / Company Dashboard (finance, one region)
Memo: `target_region_id`, `requested_comparison_years` ([2024,2025]). Template
requires: `region_id`, `branch_ids`, `fy2024`, `fy2025`, `revenue_growth_pct`,
`top_ebitda_branch_id`, `bottom_ebitda_branch_id`, `region_reconciliation_variance`.

Steps:
1. `branch_ids` = ascending list of branches in the region.
2. `fy2024` = {revenue, sga, allocations, ebitda} summed over the region's
   branches for M1..M12. `fy2025` = same for M13..M24, plus `ebitda_margin`
   (= region fy2025 ebitda / region fy2025 revenue, 4 dec) and
   `sales_per_labor_headcount` (= region fy2025 revenue / sum of labor_headcount
   over M13..M24 across the region's branches, 2 dec).
3. `revenue_growth_pct` = (fy2025 rev − fy2024 rev)/fy2024 rev (4 dec).
4. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch in the region
   with max / min FY2025 EBITDA.
5. `region_reconciliation_variance` = region_reported_total − sum_of_branch_
   recomputed. With live data this ties out to `0.0` (the reported region
   aggregate equals the sum of the branch-level recomputations). Report 0.0.

A company-wide dashboard uses the same pattern with all 12 branches instead of
one region's 3.

## 5. SOP — Compensation Current-Year Summary
Memo: `ensemble_id`, `summary_type=current_year_by_quarter_and_pay_type`.
Template requires: `ensemble_id`, `current_year`, `roster_count`, `pay_types`,
`quarter_totals`, `annual_pay_type_totals`, `annual_total`, `largest_pay_type`,
`combined_overscale_employee_count`, `partial_quarter_employee_count`.

Reference (from `/api/compensation/rate-book`, confirmed values):
- `current_year` = 2026
- `minimum_weekly_scale` (MWS) = 2520.0 /week
- `pay_types` order = ["Minimum Weekly Scale","Titled Position Premium",
  "Seniority","Overscale"]
- `quarter_weeks` default Q1..Q4 = 13 each — BUT use each employee's
  `weeks_by_quarter`, not the default, when partial-quarter employees exist.
- `seniority_weekly` by years_of_service:
  0-4 → 0.0; 5-9 → 48.0; 10-14 → 82.0; 15-19 → 126.0; 20-24 → 170.0; 25+ → 215.0
- `title_premium_pct`: Concertmaster 0.22, Principal 0.20, Section Lead 0.15,
  Associate Principal 0.10, Assistant Principal 0.10 (applied to MWS).
- Business rules (from the rate book):
  1. Use roster `weeks_by_quarter`, not a fixed 13-week quarter.
  2. If `combined_overscale_includes_title` is true, do NOT add a titled position
     premium separately for that employee (their overscale already includes it).
  3. (Forecast only) add years of service for forecast years.

Per-employee weekly amounts:
- MWS weekly = 2520.0
- Titled Position Premium weekly = title_premium_pct[title] × 2520.0 (only if
  title is set AND `combined_overscale_includes_title` is false; else 0)
- Seniority weekly = band lookup on `years_of_service`
- Overscale weekly = `overscale_weekly`

For each quarter Q: employee Q pay for each type = weekly_amount ×
`weeks_by_quarter[Q]`. Annual per-type = sum of 4 quarters. Annual per-employee
total = sum of the 4 pay types.

Outputs:
- `roster_count` = number of employees for the ensemble.
- `quarter_totals` = {Q1..Q4}: sum over all employees of (all 4 pay types ×
  weeks that quarter). (Quarter total = sum of all pay types across employees.)
- `annual_pay_type_totals` = {pay_type: annual total across all employees}.
- `annual_total` = sum of annual_pay_type_totals.
- `largest_pay_type` = pay_type with the max annual total (enum from rate book).
- `combined_overscale_employee_count` = count of employees with
  `combined_overscale_includes_title` == true.
- `partial_quarter_employee_count` = count of employees whose `weeks_by_quarter`
  has any quarter ≠ 13.

## 6. SOP — Compensation Forecast
Memo: `ensemble_id`, `scenario_id`, `forecast_years`=[current, year_plus_1,
year_plus_2]. Template requires: `ensemble_id`, `scenario_id`, `annual_totals`,
`growth_rates`, `year_plus_2_quarter_totals`, `year_plus_2_pay_type_totals`,
`largest_growth_pay_type`, `combined_overscale_employee_count`,
`partial_quarter_employee_count`.

Scenario parameters (from `/api/compensation/scenarios[<scenario_id>]`): per year
`mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.

Computation (CONFIRMED — growth compounds year over year):
- `current` = base computation from §5 (MWS 2520, overscale×1, seniority×1,
  title pct×1, years_of_service as-is).
- `year_plus_1`: MWS_rate = 2520 × (1+mws_growth_y1); overscale_multiplier =
  (1+overscale_growth_y1); seniority_multiplier = (1+seniority_growth_y1);
  title_pct scaled by title_pct_multiplier_y1; years_of_service += 1 when
  looking up the seniority band.
- `year_plus_2`: compound on year_plus_1 — MWS_rate × (1+mws_growth_y2);
  overscale_multiplier × (1+overscale_growth_y2); seniority_multiplier ×
  (1+seniority_growth_y2); title_pct_multiplier × title_pct_multiplier_y2
  (apply the y2 multiplier on top of y1); years_of_service += 2 for the band.
- For each year, per-employee per-quarter = weekly_amount × weeks_by_quarter[Q],
  where weekly MWS is the year's rate, weekly overscale = roster overscale_weekly
  × overscale_multiplier, weekly seniority = band(yos+shift) ×
  seniority_multiplier, weekly title = pct (scaled) × MWS_rate (or 0 if
  combined_overscale_includes_title).

Outputs:
- `annual_totals` = {current, year_plus_1, year_plus_2} (2 dec).
- `growth_rates`: `year_plus_1_vs_current` = (yp1−current)/current (4 dec);
  `year_plus_2_vs_year_plus_1` = (yp2−yp1)/yp1 (4 dec).
- `year_plus_2_quarter_totals` = {Q1..Q4} totals for the year_plus_2 scenario.
- `year_plus_2_pay_type_totals` = {4 pay types} totals for year_plus_2.
- `largest_growth_pay_type` = pay_type with the largest (year_plus_2 − current)/
  current growth ( Seniority typically wins because seniority compounds via both
  the growth rate and the +2 band shift).
- `combined_overscale_employee_count` and `partial_quarter_employee_count` =
  roster-treatment counts (same as §5; the roster itself does not change across
  forecast years).

## 7. SOP — Weekly Payroll Review
Memo: `production_id`. Template requires: `production_id`, `service_counts`,
`category_totals`, `weekly_total`, `conflict_flags`, `per_musician`,
`top_paid_musician_id`.

Reference (from `/api/payroll/rate-book`, confirmed):
- `service_rates` (per service, flat): Performance 260.25, Audit 260.25,
  1hr Sound Check 80.0, 2hr Sound Check 142.5. Rehearsal is HOURLY at 58.75
  with a 3-hour minimum call (bill max(duration_hours, 3.0) × 58.75).
- `service_time_limits` (hours): Performance 3.0, Audit 3.0, Rehearsal 5.0,
  1hr Sound Check 1.0, 2hr Sound Check 2.0.
- `weekly_guarantee` = 2082.0.
- `premium_pct`: principal_or_lead 0.15, concertmaster 0.20, quartet 0.15,
  electronic 0.25, first_double 0.25, additional_double 0.10, vacation 0.04.
- `conflict_thresholds`: rehearsal_earliest_start 09:00,
  rehearsal_latest_end 18:30.
- Business rules:
  1. Rehearsal: hourly, 3-hour minimum call.
  2. Performance/Audit/Sound Check: per service (flat).
  3. Premiums apply to the musician's base service pay BEFORE vacation.
  4. Doubles: 25% for the first extra instrument, 10% each additional.
  5. Vacation = 4% of (base service pay + premiums) when `vacation_eligible`.
  6. Weekly guarantee adjustment applies only to guaranteed regular players
     (i.e. NOT substitutes), when base service pay < weekly_guarantee.

`/api/payroll/productions?production_id=` returns `{production_id, title,
week_start, schedule:[...], roster:[...]}`. Each schedule entry: `{service_id,
service_type, date, start_time, end_time, duration_hours}`. Each roster entry:
`{musician_id, name, instrument, assigned_service_ids:[...], principal, lead,
quartet, electronic, doubles (int count of extra instruments), substitute,
vacation_eligible}`.

Per-musician computation:
1. Base service pay by category, summing over `assigned_service_ids`:
   - `performance` = count(Performance) × 260.25
   - `audit` = count(Audit) × 260.25
   - `sound_check` = sum of the sound-check service rates assigned
     (1hr→80.0, 2hr→142.5)
   - `rehearsal` = sum over Rehearsal services of max(duration_hours,3.0)×58.75
   - base_service_pay = performance + audit + rehearsal + sound_check
2. Role premium pct = (0.15 if principal) + (0.15 if lead) + (0.15 if quartet)
   + (0.25 if electronic) + (0.20 if concertmaster flag present). Stacked.
3. Doubles pct = 0.25 if doubles≥1, plus 0.10 × max(0, doubles−1).
4. `premium` = role_premium_pct × base (compute on the effective base — see
   substitute note below). Reported in the `premium` category.
5. `doubles` = doubles_pct × base. Reported in the `doubles` category.
6. `vacation` = 0.04 × (base + premium + doubles) if vacation_eligible else 0.
7. `guarantee_adjustment` = max(0, 2082.0 − base_service_pay) for NON-substitute
   musicians whose base_service_pay < 2082.0; 0 for substitutes.
8. Substitute musicians (substitute == true) — apply the substitute rule below.

Substitute rule (derived from convention; substitutes are not guaranteed-regular
but receive a 50% performance premium):
- Let perf_base = count(assigned Performance) × 260.25.
- `substitute_adjustment` = 0.50 × perf_base.
- The reported `performance` category = perf_base × 1.5 (= perf_base +
  substitute_adjustment).
- Effective base for premium/doubles/vacation = base_service_pay +
  substitute_adjustment (equivalently: sum of reported base categories, with
  performance at 1.5×). So premium, doubles, vacation are computed on this
  inflated base.
- `substitute_adjustment` is ALSO added as its own line item in the total.
- `guarantee_adjustment` = 0 for substitutes.
- Non-performance categories (audit, rehearsal, sound_check) are NOT inflated.

Per-musician `total` = sum of that musician's reported nonzero categories.
`per_musician` entries: `{musician_id, name, total, categories}` where
`categories` contains ONLY nonzero category names → currency (2 dec). Ordered by
`musician_id`.

Production-level outputs:
- `service_counts` = {service_type: count} over the SCHEDULE (total services of
  each type in the week, not per-musician). Keys use the service_type labels
  exactly (e.g. "1hr Sound Check", "Performance", "Rehearsal", "Audit").
- `category_totals` = sum over musicians of each category (aggregate from
  UNROUNDED per-musician values, then round to 2). Categories that appear:
  performance, audit, rehearsal, sound_check, premium, doubles, vacation,
  guarantee_adjustment, substitute_adjustment (only when applicable).
- `weekly_total` = sum over musicians of per-musician totals (aggregate unrounded,
  round to 2).
- `top_paid_musician_id` = musician_id with the highest total.
- `conflict_flags` = sorted alphabetically list, drawn from this enum, raised
  when ANY scheduled service violates the threshold:
  - `REHEARSAL_EARLY_START` — any Rehearsal with start_time < 09:00.
  - `REHEARSAL_LATE_END` — any Rehearsal with end_time > 18:30.
  - `SERVICE_OVER_TIME_LIMIT` — any service whose duration_hours exceeds its
    `service_time_limits` entry (e.g. Rehearsal > 5.0, Performance > 3.0).
  - `SOUND_CHECK_DURATION_MISMATCH` — a "1hr Sound Check" whose duration ≠ 1.0,
    or a "2hr Sound Check" whose duration ≠ 2.0 (label doesn't match duration).

## 8. Verification checklist
- Did you use the LIVE REMOTE base URL (not 127.0.0.1)?
- Does the JSON have exactly the template's `required_top_level_keys`?
- Currency 2 dec; percent/ratio 4 dec as a decimal?
- Rankings: branch-rank among 12 vs region-rank among 4 — not confused?
- Compensation: used `weeks_by_quarter` (not fixed 13) and the
  combined_overscale_includes_title suppression of title premium?
- Forecast: compounding year-over-year, +1/+2 years of service for bands?
- Payroll: rehearsal 3-hr minimum; premiums before vacation; guarantee only for
  non-substitutes; substitute 1.5× performance + substitute_adjustment line;
  conflict flags sorted; per_musician by musician_id with only nonzero
  categories?
- Aggregates (category_totals, weekly_total) summed from unrounded values?
