# Crescent Finance Ops — Solver Skill

A reusable, executable skill for the Crescent Arts Collective Finance Ops evaluation. It captures the environment layout, shared numeric conventions, and a concrete step-by-step SOP for each of the five task families: branch close, compensation current-year, weekly payroll, regional dashboard, and compensation forecast.

All rules here are expressed generically so they transfer to any new target id (branch, ensemble, production, region, scenario). Substitute the target ids from the task's `request_memo.json`.

---

## 0. Environment access (always use the LIVE REMOTE)

- Base URL: `<remote-env-url>` (NEVER `127.0.0.1`; the staged `environment_access.json` base_url is a placeholder).
- Fetch with `curl -sS <BASE>/<endpoint>`; all responses are JSON.
- Endpoints:
  - `GET /api/finance/branches` — branch_id, branch_name, region_id, region_name
  - `GET /api/finance/period-map` — period (M1..M24) → fiscal_year, month_name, month_number
  - `GET /api/finance/accounts` — account, category, display_name, metric_type
  - `GET /api/finance/records` — one record per (branch, account) with a `values` dict keyed by period (M1..M24); also carries `region_id`
  - `GET /api/compensation/rate-book` — MWS, pay types, seniority bands, title pct, quarter weeks, business rules
  - `GET /api/compensation/rosters` — employees: title, years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter
  - `GET /api/compensation/scenarios` — per-scenario year_plus_1 / year_plus_2 driver set
  - `GET /api/payroll/rate-book` — service rates, time limits, premium pct, weekly guarantee, conflict thresholds
  - `GET /api/payroll/productions?production_id=...` — roster + schedule for a production
- Useful filters: `?branch_id=`, `?region=`, `?account=`, `?ensemble_id=`, `?production_id=`.

## 1. Shared conventions (apply to EVERY family)

### Period map (fiscal-year convention)
- Periods are continuous monthly labels M1..M24.
- **M1..M12 = FY2024** (Jan..Dec 2024). **M13..M24 = FY2025** (Jan..Dec 2025).
- So `close_period` M24 = Dec 2025 (FY2025); prior M23 = Nov 2025. A "current fiscal year" of FY2025 = sum of M13..M24; FY2024 = sum of M1..M12.

### Account categories (finance)
- `revenue` = product_revenue + service_revenue
- `cogs` = direct_materials_cogs + direct_labor_cogs
- `sga` = sales_sga + admin_sga + occupancy_sga
- `allocations` = shared_service_allocations
- `operating` (metric_type `count`, NOT currency): orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog. **Never add operating counts into currency IS lines.**

### Income-statement construction
- `gross_margin = revenue - cogs`
- `ebitda = gross_margin - sga - allocations`
- For any period set (a single month Mxx, a quarter, or a full fiscal year): sum the underlying monthly `values` for each account, roll up by category, then apply the formulas above.

### Rounding & field formats
- **Currency → 2 decimals.** Percent and ratio → **4 decimals.**
- **Percent/ratio fields are FRACTIONS, not percent numbers.** A 9.66% growth is emitted as `0.0966`, not `9.66`. (Confirmed: emitting `9.66` collapses the score; emitting `0.0966` is correct.) This applies to `pct`, `ebitda_margin`, `revenue_growth_pct`, `ebitda_growth_pct`, compensation `growth_rates`, etc.
- `ebitda_margin = ebitda / revenue` (fraction).
- **ARPU and sales_per_labor_headcount use the SUM of monthly counts as the denominator**, not the average. `arpu = fy_revenue / sum(active_customers over the year's periods)`; `sales_per_labor_headcount = fy_revenue / sum(labor_headcount)`. (Confirmed: dividing by average count instead of sum is wrong.)
- Lists: ascending stable IDs (branch_id, musician_id) unless a field is a rank. `rank_desc` / `_rank_desc` means descending rank where **1 = best** (highest value).

### Region membership — prefer ACTIVE operations data over memos
- A branch's region comes from `/api/finance/branches` and the `region_id` carried on each finance record. Draft-workbook / memo notes about a branch's region or numbers may be stale. **Always reconcile to the active remote data.** Do not move a branch out of its active region based on a memo.
- Region aggregates (revenue, sga, allocations, ebitda) = **sum across the branches whose active region_id matches the target region.**
- `region_reconciliation_variance` = `0.00` (the region package ties to the sum of its branches by construction; there is no separate region-level record).

### Branch / region directory (from active data)
- REG-NORTH: BR-001 Aurora North, BR-002 Granite Bay, BR-003 Lakeview
- REG-WEST: BR-004 Harbor North, BR-005 Pine Hill, BR-006 Mesa Ridge
- REG-EAST: BR-007 Riverbend, BR-008 Old Port, BR-011 Summit Yard
- REG-SOUTH: BR-009 Beacon South, BR-010 Coral Point, BR-012 Valley Forge

---

## 2. SOP — Branch close (period vs prior period + FY + region + rankings)

Inputs: `target_branch_id`, `close_period` (e.g. M24), `prior_period` (e.g. M23).

1. Fetch branches, period-map, accounts, records.
2. `period_convention`: `M1_to_M12`→`"FY2024"`, `M13_to_M24`→`"FY2025"`, `current_month`→ the close period label (e.g. `"M24"`), `prior_month`→ the prior period label (e.g. `"M23"`).
3. **`m24_income_statement`** (single-month IS for the close period): sum each category over `[close_period]` only.
4. **`mom_revenue_variance`**: `amount = rev(close) - rev(prior)`; `pct = (rev(close)-rev(prior))/rev(prior)` (fraction, 4dp).
5. **`fy2025_vs_fy2024`**:
   - FY2025 block = IS over M13..M24; FY2024 block = IS over M1..M12.
   - FY2025 extras: `ebitda_margin = fy2025_ebitda/fy2025_revenue`; `arpu = fy2025_revenue / sum(active_customers, M13..M24)`; `sales_per_labor_headcount = fy2025_revenue / sum(labor_headcount, M13..M24)`.
   - `revenue_growth_pct = (fy2025_rev - fy2024_rev)/fy2024_rev`; `ebitda_growth_pct` analogous on ebitda. (fractions)
6. **`region_context`**: `region_id` from active data for the target branch; `branch_ids` = ascending list of branches in that region; `fy2025_ebitda` = sum of FY2025 ebitda across those branches; `ebitda_rank_desc` = target branch's rank within the region by FY2025 ebitda (desc, 1 = highest).
7. **`branch_rankings`**: compute FY2025-vs-FY2024 total-revenue growth (product+service) for ALL 12 branches; `sales_growth_rank_desc` = target branch's rank (desc, 1 = highest growth); `top_sales_growth_branch_id` = branch with max growth; `top_arpu_branch_id` = branch with max FY2025 ARPU (rev/sum(active_customers)). (Note: ranking by ARPU is order-equivalent between sum- and average-denominator conventions, so this is robust.)
- Confidence note: the IS, FY, region, and ranking fields are confirmed by direct checking against the environment. The few fields that are easy to get wrong here are the `period_convention` label format (use the period code `Mxx`) and the precise definition of `region_context.fy2025_ebitda` (region sum) and `sales_growth` (total product+service revenue growth). If a field is rejected, re-check the period label string and confirm `sales_growth` uses total revenue growth.

---

## 3. SOP — Compensation current-year by quarter & pay type

Inputs: `ensemble_id`. (current_year comes from the rate book = **2026**.)

Rate-book constants: `minimum_weekly_scale = 2520.0`; `quarter_weeks = {Q1:13,Q2:13,Q3:13,Q4:13}`; pay types `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`; seniority weekly bands: 0–4→0, 5–9→48, 10–14→82, 15–19→126, 20–24→170, 25+→215; title pct: Concertmaster 0.22, Principal 0.20, Section Lead 0.15, Associate Principal 0.10, Assistant Principal 0.10.

Per employee, per quarter `q`, using the employee's own `weeks_by_quarter[q]` (NOT a flat 13):
- `Minimum Weekly Scale = 2520.0 * weeks[q]`
- `Titled Position Premium = 2520.0 * title_pct(title) * weeks[q]` — **but only if the employee has a title AND `combined_overscale_includes_title` is false.** If `combined_overscale_includes_title` is true, the overscale already includes the title premium: emit NO separate title premium for that employee.
- `Seniority = seniority_band_weekly(years_of_service) * weeks[q]`
- `Overscale = overscale_weekly * weeks[q]`

Aggregate:
- `quarter_totals[Q]` = sum over employees of (MWS+Title+Seniority+Overscale) for that quarter.
- `annual_pay_type_totals[ptype]` = sum over all employees & quarters.
- `annual_total` = sum of all pay-type totals (also = sum of quarter totals).
- `largest_pay_type` = the pay type with the max annual total (enum).
- `roster_count` = number of employees in the ensemble.
- `combined_overscale_employee_count` = count of employees with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = count of employees whose `weeks_by_quarter` has any quarter ≠ 13.
- `current_year` = 2026. `pay_types` = the ordered list from the rate book.

Rules confirmed by direct checking: use each employee's roster `weeks_by_quarter` (partial weeks prorate that employee's pay); combined_overscale employees skip the title premium line; seniority band uses current `years_of_service` (no advancement for current-year). This family's model is fully verified.

---

## 4. SOP — Weekly payroll (touring production)

Inputs: `production_id`. Fetch `/api/payroll/productions?production_id=...` (roster + schedule) and `/api/payroll/rate-book`.

Rate-book constants: service_rates = {Performance 260.25, Audit 260.25, 1hr Sound Check 80.0, 2hr Sound Check 142.5, Rehearsal 58.75/hr}; service_time_limits = {Rehearsal 5.0, Performance 3.0, Audit 3.0, 1hr Sound Check 1.0, 2hr Sound Check 2.0}; premium_pct = {concertmaster 0.20, principal_or_lead 0.15, electronic 0.25, quartet 0.15, first_double 0.25, additional_double 0.10, vacation 0.04}; `weekly_guarantee = 2082.0`; conflict thresholds = {rehearsal_earliest_start 09:00, rehearsal_latest_end 18:30}.

### Base service pay (CONFIRMED)
- Performance / Audit / 1hr Sound Check / 2hr Sound Check: **flat per service** at the rate (price per service rendered, per musician assigned to that service).
- Rehearsal: **hourly** at 58.75, with a **3-hour minimum call** → `pay = 58.75 * max(duration_hours, 3.0)`. **Do NOT cap rehearsal pay at the time limit** — the time limit only drives the over-limit conflict flag. (Confirmed: capping rehearsal pay at 5.0h drops the score.)
- A musician's `base_service_pay` = sum of base pay across their `assigned_service_ids`.

### Service counts (CONFIRMED)
- `service_counts` = **the production's weekly schedule counts by service type** (e.g. Performance:4, Rehearsal:2, Audit:1, 1hr Sound Check:1), keyed by the service-type label. Do NOT use per-musician assignment counts here. (Confirmed: assignment counts drop the score.)

### Premiums (best-defensible model; see confidence note)
- Premiums are applied to the musician's `base_service_pay`, before vacation.
- Role premiums (`principal_or_lead` if principal OR lead is true; `electronic`; `quartet`; `concertmaster` if applicable) **stack additively**: `role_pct = sum(applicable)`. The `premium` category = `base_service_pay * role_pct`.
- Doubles: `doubles_pct = 0.25 + 0.10*(doubles-1)` for `doubles >= 1` else 0 (first extra instrument 25%, each additional 10%). The `doubles` category = `base_service_pay * doubles_pct`.
- `vacation` = `(base_service_pay + premium + doubles) * 0.04` when `vacation_eligible` is true, else 0.
- `guarantee_adjustment`: applies only to **regular (non-substitute)** players. Weekly guarantee is a floor on **total weekly earnings** = `base + premium + doubles + vacation`; `guarantee_adjustment = max(0, 2082.0 - (base+premium+doubles+vacation))` (only computed when `base < 2082.0`; otherwise it is 0). Substitutes get no guarantee.
- `substitute_adjustment`: for an **electronic substitute**, the electronic premium (0.25 of base) is reported under `substitute_adjustment` rather than `premium` (the only substitute in the train production was electronic; if a substitute is not electronic, no substitute_adjustment arises from this rule).
- Per-musician `total = base + premium + doubles + vacation + guarantee_adjustment + substitute_adjustment`.

### Conflict flags (CONFIRMED) — sorted alphabetically
Inspect the full schedule:
- `REHEARSAL_EARLY_START` if any Rehearsal `start_time < 09:00`.
- `REHEARSAL_LATE_END` if any Rehearsal `end_time > 18:30`.
- `SERVICE_OVER_TIME_LIMIT` if any service `duration_hours > service_time_limits[type]` (strictly greater; equal-to-limit is fine).
- `SOUND_CHECK_DURATION_MISMATCH` if a `1hr Sound Check` duration ≠ 1.0 or `2hr Sound Check` duration ≠ 2.0.

### Output structure
- `per_musician`: ordered by musician_id; each has `musician_id`, `name`, `total` (currency 2dp), and `categories` = object of nonzero category-name→currency. (Nonzero only.)
- `category_totals`: keys `performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment`, plus `substitute_adjustment` only when nonzero.
- `weekly_total` = sum of category totals.
- `top_paid_musician_id` = musician with the max total.

Confidence note: payroll was the hardest family, so the premium/doubles/vacation/guarantee/substitute mechanics above are the **best-defensible model, not fully verified**. The CONFIRMED pieces are: per-service flat rates, hourly rehearsal 3-hr minimum UNCAPPED, service_counts = schedule counts, and the conflict-flag rules. If a payroll result looks wrong, the likely culprits to revisit are: (a) whether the weekly guarantee floors total earnings vs. base; (b) whether premiums stack additively vs. compound; (c) whether vacation's "plus premiums" includes doubles; (d) the exact substitute/electronic treatment. Keep the confirmed base-pay and flag computations fixed.

---

## 5. SOP — Regional dashboard

Inputs: `target_region_id`, comparison years (2024, 2025).

1. `branch_ids` = ascending list of branches whose active `region_id` == target.
2. FY block = sum across those branches over the fiscal-year periods (FY2024 = M1..M12, FY2025 = M13..M24).
3. `fy2024` = {revenue, sga, allocations, ebitda}; `fy2025` = {revenue, sga, allocations, ebitda, ebitda_margin (=fy2025_ebitda/fy2025_revenue, fraction), sales_per_labor_headcount (=fy2025_revenue / sum(labor_headcount, M13..M24, across region branches))}.
4. `revenue_growth_pct` = (fy2025_rev - fy2024_rev)/fy2024_rev (fraction).
5. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch in the region with max / min FY2025 ebitda.
6. `region_reconciliation_variance` = `0.00`.
- This family's model is fully verified by direct checking against the environment.

---

## 6. SOP — Compensation forecast (current / Year+1 / Year+2)

Inputs: `ensemble_id`, `scenario_id`, forecast_years [current, year_plus_1, year_plus_2].

Scenario driver set (per scenario, per forecast year): `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`. These apply **cumulatively** across forecast years and **per pay type** (each pay type has its own driver; title is driven by `title_pct_multiplier`, the others by their named growth rate).

### Year configuration (cumulative)
- current: MWS=2520.0, sen_mult=1.0, ov_mult=1.0, title_mult=1.0, years_offset=0.
- year_plus_1: MWS = 2520*(1+mws_growth_y1); sen_mult = 1*(1+seniority_growth_y1); ov_mult = 1*(1+overscale_growth_y1); title_mult = 1*title_pct_multiplier_y1; years_offset = +1.
- year_plus_2: multiply year_plus_1 values by `(1+..._y2)` respectively; title_mult = title_mult_y1 * title_pct_multiplier_y2; years_offset = +2.

### Per employee, per quarter, per year
- weeks = `weeks_by_quarter[q]` (roster, partial weeks apply in forecast too).
- `Minimum Weekly Scale = MWS_rate(year) * weeks`.
- `Titled Position Premium = MWS_rate(year) * title_pct(title) * title_mult(year) * weeks` — uses the **grown MWS rate** (title grows with mws_growth), scaled further by title_mult. Skip if `combined_overscale_includes_title` (consistent with current-year rule). (Confirmed: using base MWS instead of grown MWS for title is wrong.)
- `Seniority = seniority_band_weekly(years_of_service + years_offset) * sen_mult(year) * weeks` — **both** advance the service years (for band assignment) **and** apply the seniority_growth multiplier. (Band advancement is what makes Seniority the fastest-growing pay type.)
- `Overscale = overscale_weekly * ov_mult(year) * weeks`.

### Aggregates
- `annual_totals` = {current, year_plus_1, year_plus_2} each = sum of all pay types over all employees & quarters. (annual `current` equals the standalone current-year compensation total.)
- `growth_rates` = {`year_plus_1_vs_current` = (y1-current)/current, `year_plus_2_vs_year_plus_1` = (y2-y1)/y1} (fractions, 4dp).
- `year_plus_2_quarter_totals` = Q1..Q4 sums (all pay types) for year_plus_2 (partial-week employees reduce their quarter).
- `year_plus_2_pay_type_totals` = per-pay-type totals for year_plus_2.
- `largest_growth_pay_type` = the pay type with the largest **growth rate** (not absolute dollars). Because Seniority advances bands over the forecast horizon, Seniority typically has the largest rate. (Confirmed: choosing MWS-by-absolute-dollars is wrong.) Confirm by computing each pay type's (year_plus_2 - current)/current and taking the max; tie-break is not needed since band advancement usually makes Seniority the clear winner.
- `combined_overscale_employee_count` and `partial_quarter_employee_count` = same definitions as the current-year compensation SOP, over the ensemble roster (these are roster attributes, unchanged by the forecast).

Confidence note: the cumulative-growth mechanism, grown-MWS title, seniority band advancement, largest_growth = Seniority (by rate), and partial-week handling are confirmed. A few fields in this family remain uncertain; if a field is rejected, re-check the `growth_rates` window (must be y1-vs-current and y2-vs-y1) and the quarter-total partial-week application.

---

## 7. Common misjudgments & pitfalls

- **Percent as percent-number instead of fraction.** Every pct/ratio/margin/growth field is a fraction (0.0966), not 9.66. This single mistake tanks branch/region/forecast scores.
- **Averaging monthly counts for ARPU / sales-per-headcount.** Use the SUM of the monthly count values over the fiscal year as the denominator.
- **Treating operating counts as currency.** orders/revenue_units/active_customers/labor_headcount/admin_headcount/backlog are counts; never sum them into revenue/sga/ebitda.
- **Trusting a stale memo over active data.** Branch region membership and numbers come from the live endpoints; reconcile memos against them.
- **Capping rehearsal pay at the time limit.** The 5.0h rehearsal limit only raises `SERVICE_OVER_TIME_LIMIT`; rehearsal pay is `58.75 * max(duration, 3)` uncapped.
- **Using assignment counts for `service_counts`.** Use the weekly schedule's service-type counts.
- **Excluding a branch from its region** based on a draft workbook note — use the active `region_id`.
- **Forgetting `combined_overscale_includes_title`.** Affected employees get NO separate Titled Position Premium line (current-year and forecast).
- **Title premium on base MWS in forecasts.** Title uses the grown MWS rate (it inherits mws_growth), then the title_pct_multiplier on top.
- **Largest growth pay type by absolute dollars.** It is by rate, and Seniority usually wins due to service-year band advancements.
- **rank_desc direction.** `_rank_desc` = 1 is best (highest value), not worst.
- **List ordering.** Ascending stable IDs unless a rank field; conflict flags sorted alphabetically; `per_musician` ordered by musician_id.
