---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops Reporting SOP

This group has THREE task families against one read-only HTTP API. Each task gives you
`prompt.txt`, `payloads/request_memo.json`, and `payloads/answer_template.json`. Your job
is to return ONE JSON object that exactly matches the template's keys/shapes.

## 0. Universal procedure (do this every task)

1. **Read `answer_template.json` first.** Its `required_top_level_keys` and `field_types`
   ARE the contract. Emit exactly those keys, nested exactly as shown, no extras, no omissions.
2. **Read `request_memo.json`** for the target IDs (`target_branch_id`, `target_region_id`,
   `ensemble_id`, `scenario_id`, `production_id`), periods, and focus lists.
3. **IGNORE the `base_url` inside `payloads/environment_access.json`** (it points at a wrong
   localhost). Always use the remote base URL: `<remote-env-url>`.
4. **Memo notes about "draft workbook / background notes / reconcile against active
   operations data" are red herrings/distractors.** There is NO draft data in the API. They
   mean: trust ONLY the live API data and ignore any narrative figures. Reconciliations tie
   to zero (see region task).
5. Fetch with `curl -s`. All endpoints are GET. Compute in a script, then format.

### Rounding & ordering conventions (from the templates)
- **Currency**: round to **2 decimals**. **Percent / ratio / growth**: round to **4 decimals**
  (these are DECIMAL fractions, e.g. 9.66% -> `0.0966`, NOT `9.66`).
- Round each output field **once at the end** from full-precision intermediates. Do NOT chain
  rounding. For aggregate totals computed from many rows, sum the **unrounded** rows and round
  the total once (this can make a total differ by a penny from the sum of the displayed,
  pre-rounded per-row figures — that is expected and correct).
- **Lists** are ordered by ascending stable ID (`branch_id`, `musician_id`, employee_id)
  UNLESS a field name says otherwise (e.g. `*_rank_desc`, `top_*`, "sorted alphabetically").
- `conflict_flags`: sorted alphabetically. `per_musician`: ordered by `musician_id`.
- `pay_types`: emit in the rate book's given order
  `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`.

## 1. API map

Base: `<remote-env-url>`

| Endpoint | Use |
|---|---|
| `/api/manifest` | entity index (branch/ensemble/production IDs & names) |
| `/api/finance/branches` | branch_id -> branch_name, region_id, region_name |
| `/api/finance/period-map` | period `M1..M24` -> fiscal_year, month |
| `/api/finance/accounts` | account -> category (revenue/cogs/sga/allocations/operating) |
| `/api/finance/records?branch_id=&region=&account=` | per-branch monthly values |
| `/api/compensation/rate-book` | scale, seniority bands, title %, business rules |
| `/api/compensation/rosters?ensemble_id=` | employee rows for an ensemble |
| `/api/compensation/scenarios` | forecast growth cases |
| `/api/payroll/rate-book` | service rates, premiums, limits, guarantee |
| `/api/payroll/productions?production_id=` | schedule + musician roster (list of 1) |

Finance records: 12 branches x 14 accounts; each record has
`values` = dict keyed `M1..M24`. `records?branch_id=X` returns that branch's 14 rows.

## 2. Period / fiscal-year convention (finance)

From `/api/finance/period-map`: **M1..M12 = FY2024 (Jan..Dec), M13..M24 = FY2025 (Jan..Dec).**
So `period_convention` = `{"M1_to_M12":"FY2024","M13_to_M24":"FY2025","current_month":<close_period>,
"prior_month":<prior_period>}`. Use the raw M-label (e.g. `"M24"`, `"M23"`) as the period label
string — that is the stable identifier the data uses. M24 is the latest close (Dec FY2025).

## 3. Income statement definitions (finance)

Account categories (`/api/finance/accounts`):
- **revenue** = `product_revenue` + `service_revenue`
- **cogs** = `direct_materials_cogs` + `direct_labor_cogs`
- **sga** = `sales_sga` + `admin_sga` + `occupancy_sga`
- **allocations** = `shared_service_allocations`
- operating COUNT accounts (NOT dollars): `orders`, `revenue_units`, `active_customers`,
  `labor_headcount`, `admin_headcount`, `backlog`.

Line items:
- `gross_margin = revenue - cogs`
- `ebitda = gross_margin - sga - allocations` (= revenue - cogs - sga - allocations)
- `ebitda_margin = ebitda / revenue` (4 dp)

A **monthly** IS sums the single period; an **FY** IS sums all 12 periods of that fiscal year
(FY2024 = M1..M12, FY2025 = M13..M24). EXCLUDE operating-count accounts from all dollar lines.

### Derived ratios
- `mom_revenue_variance.amount = rev(cur) - rev(prior)`; `.pct = amount / rev(prior)` (4 dp).
- `revenue_growth_pct = (rev_fy2025 - rev_fy2024) / rev_fy2024`; same shape for `ebitda_growth_pct`.
- **`arpu`** = FY revenue / **average monthly `active_customers`** = revenue / (sum of 12 monthly
  active_customers / 12). This yields an ANNUAL revenue-per-customer figure. (Do NOT divide by the
  raw 12-month sum.)
- **`sales_per_labor_headcount`** = FY revenue / **average monthly `labor_headcount`**
  (= revenue / (sum of 12 monthly labor_headcount / 12)). Annual revenue per FTE.
  NOTE: average-headcount denominator is the working convention; this is the single biggest
  ambiguity in the finance tasks — if a result looks off by a ~12x factor, reconsider sum vs
  average. Apply the SAME denominator convention at branch and region level.

## 4. Regional rollup & rankings (finance)

- A region's figures = **sum of its member branches** (`/api/finance/branches` gives
  `region_id`; `records?region=REG-X` returns only those branches). REG-WEST = BR-004/005/006,
  REG-NORTH = BR-001/002/003, REG-EAST = BR-007/008/011, REG-SOUTH = BR-009/010/012.
- `branch_ids` = ascending list of the region's branch IDs.
- Region `ebitda_margin` = region_ebitda / region_revenue; region `sales_per_labor_headcount`
  = region_revenue / (region average monthly labor_headcount).
- **`region_reconciliation_variance` = 0.0.** There is no separate region-level record; the
  rollup ties exactly to the active branch data. (This is what "tie back to active operating
  data" means.)
- `*_rank_desc` = 1-based rank, DESCENDING by the metric (1 = largest).
  - `region_context.ebitda_rank_desc`: rank of the target region's FY2025 EBITDA among ALL
    regions (compute every region's FY2025 EBITDA, sort desc, find target's position).
  - `branch_rankings.sales_growth_rank_desc`: rank of the TARGET branch's FY2025-vs-FY2024
    revenue growth % among ALL 12 branches, descending.
  - `top_sales_growth_branch_id`: branch with highest FY revenue growth % across all 12.
  - `top_arpu_branch_id`: branch with highest FY2025 ARPU across all 12 (same ARPU formula).
  - `top_ebitda_branch_id` / `bottom_ebitda_branch_id` (region task): highest / lowest FY2025
    EBITDA among the region's branches only.
- Ties: break by ascending branch_id (stable). Rankings span the relevant universe (all 12
  branches for branch rankings; all regions for region rank; in-region only for region task's
  top/bottom branch).

## 5. CBA compensation (current-year summary AND forecast)

Data: `/api/compensation/rate-book`, `rosters?ensemble_id=`, `scenarios`.

Rate book: `minimum_weekly_scale` (MWS, e.g. 2520.0); `pay_types` (4, ordered);
`seniority_weekly` bands `[{min_years,max_years,weekly_amount}]` (max_years null = open-ended);
`title_premium_pct` (e.g. Concertmaster .22, Principal .20, Section Lead .15, Assistant/Associate
Principal .10); `quarter_weeks` default 13/quarter; `current_year` (e.g. 2026).

Each roster row: `years_of_service`, `title` (or null), `overscale_weekly`,
`combined_overscale_includes_title` (bool), `weeks_by_quarter` {Q1..Q4}, `notes`.

### Per-employee, per-quarter weekly components (multiply each by that quarter's weeks)
For each quarter q with `weeks = weeks_by_quarter[q]`:
- **Minimum Weekly Scale** = `MWS * weeks`
- **Titled Position Premium** = `MWS * title_premium_pct[title] * weeks`
  — but **0 if title is null OR `combined_overscale_includes_title` is true** (when combined,
  the title premium is already inside overscale; do NOT add it separately).
- **Seniority** = `seniority_weekly(years_of_service) * weeks` (band lookup by years).
- **Overscale** = `overscale_weekly * weeks`.

Quarter total = sum of the 4 components over all employees for that quarter.
Pay-type annual total = sum across 4 quarters and all employees.
`annual_total` = sum of all pay-type annual totals (= sum of 4 quarter totals).

Use **actual `weeks_by_quarter`**, not a fixed 13, so partial-quarter employees (a quarter < 13)
are pro-rated automatically.

### Review counts (both comp tasks)
- `roster_count` = number of roster rows for the ensemble.
- `combined_overscale_employee_count` = rows with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = rows where ANY quarter's weeks != 13.
- `largest_pay_type` / `largest_growth_pay_type` = enum from the 4 pay types (see below).

### `largest_pay_type` (current-year task)
Pay type with the largest ANNUAL dollar total. (MWS dominates and is typically the answer.)

### Forecast task (scenarios)
`scenario_id` selects a case in `/api/compensation/scenarios`, each with `year_plus_1` and
`year_plus_2` blocks: `mws_growth`, `overscale_growth`, `seniority_growth`,
`title_pct_multiplier`. Business rules (in the rate book): **for Year+1 add 1 year of service,
for Year+2 add 2 years of service BEFORE assigning seniority bands.**

Compute three annual totals:
- **current**: base rate book, no growth, no added years.
- **year_plus_1**: `MWS*(1+mws_growth_y1)`; title premium pct scaled by `title_pct_multiplier_y1`;
  seniority band looked up at `yos+1` then scaled by `(1+seniority_growth_y1)`; overscale scaled
  by `(1+overscale_growth_y1)`.
- **year_plus_2**: growth COMPOUNDS off Year+1: `MWS*(1+g_y1)*(1+g_y2)`; title mult
  `tm_y1*tm_y2`; seniority at `yos+2` scaled by `(1+sg_y1)*(1+sg_y2)`; overscale scaled by
  `(1+og_y1)*(1+og_y2)`.
- `growth_rates.year_plus_1_vs_current = (y1-cur)/cur`; `year_plus_2_vs_year_plus_1 = (y2-y1)/y1`
  (4 dp).
- `year_plus_2_quarter_totals` / `year_plus_2_pay_type_totals`: the Year+2 breakdown.
- `largest_growth_pay_type`: pay type with the largest **absolute dollar** increase from current
  to Year+2 (MWS typically wins because it is the largest base). Note seniority can have the
  largest PERCENT growth due to band shifts + seniority_growth, but the field tracks absolute
  dollar growth.

Ambiguity to flag: `seniority_growth` is applied as a rate multiplier ON TOP of the band shift
from added years. Both effects compound. (The +years-of-service rule is mandatory; the
seniority_growth multiplier is the literal reading of the scenario field.)

## 6. Theatre weekly payroll

Data: `/api/payroll/rate-book`, `productions?production_id=` (returns a 1-element list; take [0]).
Production has `schedule` (services) and `roster` (musicians).

Rate book: `service_rates` (Performance/Audit per service; Rehearsal per hour; 1hr/2hr Sound
Check per service); `service_time_limits` (hours); `premium_pct`
(principal_or_lead .15, quartet .15, electronic .25, concertmaster .20, first_double .25,
additional_double .10, vacation .04); `weekly_guarantee`; `conflict_thresholds`
(rehearsal_earliest_start "09:00", rehearsal_latest_end "18:30").

Schedule service: `service_id, service_type, date, start_time, end_time, duration_hours`.
Roster musician: `musician_id, name, instrument, assigned_service_ids[], doubles (int),
electronic, lead, principal, quartet, substitute, vacation_eligible`.

### Per-musician pay (sum over the musician's `assigned_service_ids`)
1. **Base service pay** per assigned service:
   - Rehearsal: `Rehearsal_rate * max(duration_hours, 3.0)` (3-hour minimum call, hourly).
   - Performance / Audit / 1hr Sound Check / 2hr Sound Check: the flat per-service rate.
   - Accumulate into category buckets: Performance->`performance`, Audit->`audit`,
     Rehearsal->`rehearsal`, 1hr/2hr Sound Check->`sound_check`.
   - `base_total` = sum of all base service pay for the musician.
2. **Premiums** (`premium` category) = `base_total *` (sum of applicable pct):
   `principal_or_lead` if `principal or lead`; `quartet` if `quartet`; `electronic` if
   `electronic`; `concertmaster` only if a concertmaster flag is present (none in current data,
   so usually not applied). Premiums apply to base service pay, before vacation.
3. **Doubles** (`doubles` category, separate from `premium`): if `doubles >= 1`,
   `base_total * first_double` for the first, plus `base_total * additional_double *
   (doubles - 1)` for each additional. (e.g. 2 doubles = 35% of base_total.)
4. **Vacation** (`vacation`): if `vacation_eligible`,
   `0.04 * (base_total + premiums + doubles)` (4% of base service pay plus premiums).
5. **Guarantee adjustment** (`guarantee_adjustment`): ONLY for guaranteed regular players =
   **non-substitute** musicians (`substitute == false`). If `base_total < weekly_guarantee`,
   add `weekly_guarantee - base_total`. (No explicit `guaranteed` field exists; "regular" = not
   a substitute.) Compare against `base_total` (base service pay), not the premium-inclusive total.
6. **`substitute_adjustment`**: no substitute rate is defined in the rate book, so it is 0 and
   typically omitted (template says "currency when applicable"). Substitutes simply do NOT get
   the weekly guarantee.

Musician `total` = base_total + premiums + doubles + vacation + guarantee_adjustment.
`weekly_total` = sum of all musician totals. `top_paid_musician_id` = musician with max total
(break ties by ascending musician_id).
`per_musician[i].categories` = only the NONZERO category buckets for that musician, rounded 2 dp.
`category_totals` = sum across musicians per category; compute from UNROUNDED values and round
once (so it may differ a penny from summing the displayed per-musician figures — that is fine).

### `service_counts`
Schedule-level count of each `service_type` across the production's UNIQUE services (count the
`schedule` rows by type, e.g. 4 Performance, 2 Rehearsal, 1 Audit, 1 "1hr Sound Check").
(Possible alternative reading is assignment-level counts summed over musicians; prefer the
schedule-level "what happened this week" reading for a weekly payroll package, but sanity-check
against the memo wording.)

### `conflict_flags` (enum, sorted alphabetically; emit only those that trigger)
- `REHEARSAL_EARLY_START`: a Rehearsal `start_time` earlier than `rehearsal_earliest_start` (09:00).
- `REHEARSAL_LATE_END`: a Rehearsal `end_time` later than `rehearsal_latest_end` (18:30).
- `SERVICE_OVER_TIME_LIMIT`: any service whose `duration_hours` exceeds its
  `service_time_limits` entry (Rehearsal 5.0, Performance 3.0, Audit 3.0, 1hr SC 1.0, 2hr SC 2.0).
- `SOUND_CHECK_DURATION_MISMATCH`: a "1hr Sound Check" whose duration != 1.0, or a "2hr Sound
  Check" whose duration != 2.0.
Compare times by converting "HH:MM" to minutes. A flag fires if ANY service triggers it; emit
the deduplicated, alphabetically sorted set.

## 7. Step-by-step SOP for an unseen task in this group

1. Open `answer_template.json`; list required keys and exact field shapes/rounding.
2. Read `request_memo.json` for target IDs/periods/scenario; ignore distractor memo notes.
3. Identify the domain (finance branch close / regional / comp current / comp forecast / payroll)
   by the template's top-level keys.
4. `curl` the relevant endpoints (always the remote base URL).
5. Compute with the formulas above in a script. Keep full precision internally.
6. Round at the very end: currency 2 dp, percent/ratio/growth 4 dp. Order lists by ascending
   stable ID unless a rank/sort field says otherwise.
7. Emit exactly the template keys (no extras), validate JSON, return the single object.

### Self-check before returning
- Finance: `gross_margin == revenue - cogs`; `ebitda == gross_margin - sga - allocations`;
  region figures == sum of member branches; `region_reconciliation_variance == 0.0`; ranks are
  1-based descending.
- Comp: quarter totals sum to annual_total; pay-type totals sum to annual_total; partial-quarter
  count matches rows with a non-13 quarter; title premium suppressed when combined flag true.
- Payroll: sum of per-musician totals == weekly_total; category_totals reconcile to per-musician
  category sums (within rounding); guarantee only on non-substitutes below the guarantee; flags
  deduplicated and alphabetically sorted; per_musician ordered by musician_id.
