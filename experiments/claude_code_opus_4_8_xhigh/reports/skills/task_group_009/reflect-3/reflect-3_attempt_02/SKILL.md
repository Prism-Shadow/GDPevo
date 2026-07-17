---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops Reporting SOP

This skill solves three families of tasks against the **Crescent Finance Ops API**:
1. **Finance / branch & regional reporting** (income statements, growth, ARPU, rankings, regional rollups).
2. **Compensation** (current-year summaries and multi-year forecasts by quarter and pay type).
3. **Payroll** (weekly touring-production payroll with premiums, doubles, guarantees, CBA conflict flags).

Each task ships three payload files. ALWAYS read them first and let them drive the output shape.

## 1. How to read the task payloads

- `payloads/request_memo.json` — gives the target entity id(s), the period/year scope, and a `*_focus`
  list naming the sections to produce. Use the focus list only as a checklist; the exact required keys
  come from the template.
- `payloads/answer_template.json` — authoritative. `required_top_level_keys` = the exact top-level keys
  to emit (no more, no less). `field_types` defines every nested key and its shape. Match key names,
  nesting, and ordering EXACTLY. The `description` field states rounding and list-ordering rules.
- `payloads/environment_access.json` — IGNORE its `base_url` (e.g. `http://127.0.0.1:...`). It is wrong.
  Always use the remote base URL below.

## 2. Remote API access

- Base URL: `<remote-env-url>`
- Fetch with HTTP GET, e.g. `curl -s "<remote-env-url>api/finance/records?branch_id=BR-004"`.
- Endpoints by domain:
  - Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`,
    `/api/finance/records` (filters: `?branch_id=` `?region=` `?account=`).
  - Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters?ensemble_id=`,
    `/api/compensation/scenarios`.
  - Payroll: `/api/payroll/rate-book`, `/api/payroll/productions?production_id=`.
- `/api/finance/records` returns one row per (branch, account) with a `values` map keyed by period code
  `M1..M24`. Fetch all records once and index by `(branch_id, account)` for cross-branch rollups/rankings.
- Do the math in a script (write the candidate JSON to a file); do not eyeball totals.

## 3. Reference data structures

- **period-map**: maps period `M1..M24` -> `fiscal_year`. `M1..M12 = FY2024`, `M13..M24 = FY2025`
  (M13=Jan FY2025 ... M24=Dec FY2025). Use the map; do not hardcode beyond confirming it.
- **accounts** categories:
  - revenue: `product_revenue`, `service_revenue`
  - cogs: `direct_materials_cogs`, `direct_labor_cogs`
  - sga: `sales_sga`, `admin_sga`, `occupancy_sga`
  - allocations: `shared_service_allocations`
  - operating counts (metric_type=count): `orders`, `revenue_units`, `active_customers`,
    `labor_headcount`, `admin_headcount`, `backlog`
- **branches**: 12 branches `BR-001..BR-012`, each with `region_id` in {REG-NORTH, REG-WEST, REG-EAST,
  REG-SOUTH}.

## 4. Finance domain — formulas (validated)

For a branch over a set of periods P (single month, or all 12 periods of a fiscal year):

- `revenue   = sum(product_revenue, service_revenue over P)`
- `cogs      = sum(direct_materials_cogs, direct_labor_cogs over P)`
- `gross_margin = revenue - cogs`
- `sga       = sum(sales_sga, admin_sga, occupancy_sga over P)`
- `allocations = sum(shared_service_allocations over P)`
- `ebitda    = gross_margin - sga - allocations`
- `ebitda_margin = ebitda / revenue`
- `arpu      = revenue / sum(active_customers over P)`   <-- denominator is the SUM of monthly
  active_customers across all periods in P (customer-months), NOT the average. Do not divide by 12.
- `sales_per_labor_headcount = revenue / sum(labor_headcount over P)`  <-- same rule: SUM the monthly
  labor_headcount over the periods, do NOT average.

Growth / variance:
- `revenue_growth_pct = (FY2025_revenue - FY2024_revenue) / FY2024_revenue`
- `ebitda_growth_pct  = (FY2025_ebitda  - FY2024_ebitda)  / FY2024_ebitda`
- Month-over-month revenue variance: `amount = rev(current_month) - rev(prior_month)`,
  `pct = amount / rev(prior_month)`. "Revenue" = product+service revenue.

Rollups & rankings:
- **Region rollup** for a set of periods = element-wise SUM across all branches in the region of each
  income-statement line. `region ebitda_margin = region_ebitda/region_revenue`;
  `region sales_per_labor_headcount = region_revenue / sum(labor_headcount across all region branches over P)`.
- **Branch EBITDA ranking within a region** (`ebitda_rank_desc` when it sits inside a per-branch
  context, top/bottom branch): rank branches of that region by FY ebitda, descending.
- **Region-context block in a single-branch report** (`region_context`): `branch_ids` = the region's
  branches (ascending); `fy2025_ebitda` = the WHOLE REGION's total EBITDA (sum of all its branches);
  `ebitda_rank_desc` = that REGION's rank among ALL FOUR regions by total FY2025 EBITDA, descending.
  (Do NOT put the single branch's ebitda or the branch's intra-region rank here.)
- **Global branch rankings** (`sales_growth_rank_desc`, `top_sales_growth_branch_id`,
  `top_arpu_branch_id`): computed across ALL 12 branches. "Sales growth" = FY2025-vs-FY2024 revenue
  growth %. ARPU uses the sum-denominator rule above. Rank descending; rank 1 = largest.
- **region_reconciliation_variance** = 0.00 (the region rollup ties exactly to the sum of its branches).

period_convention block: `M1_to_M12 = "FY2024"`, `M13_to_M24 = "FY2025"`; `current_month`/`prior_month`
= the raw period codes from the memo (e.g. `"M24"`, `"M23"`).

## 5. Compensation domain — rules (validated)

Source: `/api/compensation/rate-book` (rates + business_rules), `/api/compensation/rosters?ensemble_id=`
(one row per employee), `/api/compensation/scenarios` (forecast growth cases).

Rate book keys: `minimum_weekly_scale`, `pay_types` (ordered list), `title_premium_pct` (by title),
`seniority_weekly` (bands with min_years/max_years/weekly_amount; max_years null = open-ended),
`current_year`, `quarter_weeks`.

Per employee, the four pay types are **weekly amounts** multiplied by the employee's weeks worked in
each quarter:
- `Minimum Weekly Scale` = `minimum_weekly_scale` per week.
- `Titled Position Premium` = `title_premium_pct[title] * minimum_weekly_scale` per week (0 if no title).
- `Seniority` = seniority band `weekly_amount` for the employee's `years_of_service` per week.
- `Overscale` = `overscale_weekly` per week.

Quarter/annual aggregation:
- For each quarter Q, weeks = `weeks_by_quarter[Q]` from the ROSTER ROW (NOT a fixed 13). Partial-quarter
  employees have a quarter < 13 and MUST use their actual weeks. (Using a flat 13-week quarter is wrong.)
- `quarter_totals[Q]` = sum over employees of (sum of the four weekly pay-type amounts) * weeks_in_Q.
- `annual_pay_type_totals[pt]` = sum over employees and quarters of that pay type's weekly amount * weeks.
- `annual_total` = sum of quarter totals (= sum of pay-type totals).
- `largest_pay_type` = pay type with the largest annual total.

Special-case rules:
- If `combined_overscale_includes_title == true` for an employee, DO NOT add a Titled Position Premium
  for that employee (the title value is already folded into their overscale). Their Titled premium = 0.
- `roster_count` = number of roster rows. `current_year` = rate book `current_year`.
- `combined_overscale_employee_count` = count of employees with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = count of employees whose `weeks_by_quarter` has any quarter != 13.

### Compensation forecast (multi-year)

Scenario from `/api/compensation/scenarios[scenario_id]`. Each of `year_plus_1` and `year_plus_2` carries
`mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.

- Current year: use current rates (the model above).
- Year+1 rates: `mws*(1+mws_growth_y1)`, `overscale*(1+overscale_growth_y1)`,
  `seniority_band*(1+seniority_growth_y1)`, `title_pct*title_pct_multiplier_y1`. Add **+1 year** to each
  employee's `years_of_service` BEFORE looking up the seniority band.
- Year+2 rates **COMPOUND** the two years: `mws*(1+g1_mws)*(1+g2_mws)`,
  `overscale*(1+g1_ovs)*(1+g2_ovs)`, `seniority_band*(1+g1_sen)*(1+g2_sen)`,
  `title_pct*mult_y1*mult_y2`. Add **+2 years** of service before band lookup.
  (Applying year_plus_2 growth directly to the current year, non-compounded, is wrong.)
- `annual_totals` = {current, year_plus_1, year_plus_2} totals (same aggregation as above, with the
  grown rates and bumped seniority years).
- `growth_rates`: `year_plus_1_vs_current = (Y1-cur)/cur`, `year_plus_2_vs_year_plus_1 = (Y2-Y1)/Y1`.
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` use the Year+2 grown rates.
- `largest_growth_pay_type` = pay type with the largest PERCENT growth from current to year_plus_2.
  Note: seniority often wins because the +2-year bump pushes employees across seniority bands, which
  dwarfs the rate growth. Use percent growth, not absolute dollars.
- The combined-overscale and partial-quarter counts are computed the same way as in the summary task.

## 6. Payroll domain — rules (high-risk; derive carefully from the rate book)

Source: `/api/payroll/rate-book` (read its `business_rules` every time — they are authoritative) and
`/api/payroll/productions?production_id=` (returns a list; take element 0; it has `roster`, `schedule`,
`week_start`).

Rate book provides `service_rates`, `service_time_limits`, `premium_pct`
(principal_or_lead, quartet, electronic, concertmaster, first_double, additional_double, vacation),
`weekly_guarantee`, and `conflict_thresholds` (rehearsal_earliest_start, rehearsal_latest_end).

Base service pay per musician = sum over the musician's `assigned_service_ids` of the service rate:
- Performance, Audit, Sound Check ("1hr Sound Check", "2hr Sound Check"): flat per-service rate.
- Rehearsal: hourly = `service_rates["Rehearsal"] * max(duration_hours, 3.0)` (three-hour minimum call).
- Split base into category buckets: `performance`, `audit`, `rehearsal`, `sound_check` by service type.

Premiums / adjustments (per the business_rules text — apply exactly as written for the production):
- Premiums (`premium` category): principal_or_lead, quartet, electronic, concertmaster percentages, as
  the rules specify, applied to base service pay before vacation.
- Doubles (`doubles` category): 25% for the first extra instrument + 10% per additional extra instrument
  (`doubles` count on the roster row), applied to base service pay.
- Vacation (`vacation`): 4% of (base service pay + premiums) when `vacation_eligible` is true.
- Guarantee (`guarantee_adjustment`): applies only to guaranteed REGULAR players (not substitutes) when
  base service pay is below `weekly_guarantee`; tops them up to the guarantee.
- Substitutes: `substitute == true`. They are excluded from the weekly guarantee. `substitute_adjustment`
  is "currency when applicable" (often 0/absent).

> CAUTION: the exact arithmetic for premium scope, the vacation base, the guarantee top-up basis
> (base-floor vs total-floor), and `substitute_adjustment` is subtle and easy to get wrong on a
> literal first pass. When solving a payroll task, re-derive every dollar formula directly from the rate book
> `business_rules` text, validate that per-musician `total` = sum of its category amounts and that
> `weekly_total` = sum of per-musician totals and = sum of category_totals, and prefer the most literal
> reading of each rule. Treat payroll dollars as the highest-risk area and double-check units.

Structural outputs (these ARE reliable):
- `service_counts` = count of schedule entries by `service_type`.
- `conflict_flags` (sorted alphabetically, enum
  {REHEARSAL_EARLY_START, REHEARSAL_LATE_END, SERVICE_OVER_TIME_LIMIT, SOUND_CHECK_DURATION_MISMATCH}):
  - `REHEARSAL_EARLY_START` if any Rehearsal `start_time` < `rehearsal_earliest_start`.
  - `REHEARSAL_LATE_END` if any Rehearsal `end_time` > `rehearsal_latest_end`.
  - `SERVICE_OVER_TIME_LIMIT` if any service `duration_hours` > its `service_time_limits` entry.
  - `SOUND_CHECK_DURATION_MISMATCH` if a sound-check `duration_hours` != its labelled hours
    (1hr -> 1.0, 2hr -> 2.0).
  Emit the SET of triggered flags, sorted.
- `per_musician` ordered by `musician_id`; each row's `categories` includes only nonzero categories.
- `top_paid_musician_id` = musician with the highest total.

## 7. Output conventions (from every answer_template)

- Emit EXACTLY the `required_top_level_keys`, with the nested shapes in `field_types`. No extra keys.
- Currency values: round to 2 decimals. Percent / ratio / growth fields: round to 4 decimals.
- Counts/ranks: integers.
- Lists: ascending stable IDs (e.g. `branch_ids`) unless a rank field dictates an order; `per_musician`
  ordered by `musician_id`; `conflict_flags` sorted alphabetically.
- "decimal percent" means a fraction (e.g. 0.0372), not 3.72.
- period labels for current/prior month are the raw `M##` codes; fiscal-year labels are `"FY2024"` /
  `"FY2025"` strings.

## 8. Step-by-step SOP for an unseen task

1. Read `request_memo.json` (target ids, periods/years, focus) and `answer_template.json`
   (exact keys, shapes, rounding). Decide the domain from the keys/endpoints referenced.
2. Use the remote base URL `<remote-env-url>`. Pull the reference data for the domain
   (period-map/accounts/branches and all finance records; or rate-book + roster + scenarios;
   or payroll rate-book + production).
3. Build an indexed in-memory model (finance: index by (branch,account); comp: per-employee weekly
   amounts; payroll: per-musician base + adjustments).
4. Compute each required field using the formulas in sections 4-6. Reuse validated rules:
   sum-denominator ARPU/SPLH; region rollups & region-of-regions ranking; roster `weeks_by_quarter`;
   combined-overscale title suppression; compounding forecast growth with seniority-year bumps.
5. Apply rounding and ordering from section 7. Verify internal consistency (totals reconcile;
   quarter sums = annual; per-musician totals = category totals = weekly total).
6. Emit a single JSON object with exactly the template's top-level keys.
