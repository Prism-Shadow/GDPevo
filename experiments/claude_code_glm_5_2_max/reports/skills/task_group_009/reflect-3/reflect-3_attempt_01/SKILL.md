# Crescent Finance Ops — Solver Skill

Self-contained playbook for solving Finance Ops reporting tasks against the live remote
environment. All numbers (rate books, period map, account categories, premium rules) are the
real values from the environment. Rules are stated generically so they transfer to new target
ids (branch / ensemble / region / production).

## 0. Environment & endpoints
- Live base URL: `<remote-env-url>` (never `127.0.0.1`). All responses are JSON.
- `GET /api/finance/branches` — branch_id, branch_name, region_id, region_name.
- `GET /api/finance/period-map` — period code → fiscal_year + month.
- `GET /api/finance/accounts` — account → category + metric_type.
- `GET /api/finance/records` — per (branch_id, account) a `values` map of period→amount. Filterable: `?branch_id=`, `?region=`, `?account=`.
- `GET /api/compensation/rate-book` — MWS, pay types, seniority bands, title premium %, quarter weeks, business rules.
- `GET /api/compensation/rosters` — per employee: ensemble_id, title, years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter. Filterable: `?ensemble_id=`.
- `GET /api/compensation/scenarios` — per scenario: per-year mws_growth, overscale_growth, seniority_growth, title_pct_multiplier.
- `GET /api/payroll/rate-book` — service rates, time limits, premium %, weekly guarantee, conflict thresholds.
- `GET /api/payroll/productions` — per production: roster (musician flags + assigned_service_ids), schedule (services). Filterable: `?production_id=`.

## 1. Shared conventions (CONFIRMED)
- **Period / fiscal year:** M1–M12 = FY2024, M13–M24 = FY2025. The period code (e.g. `M24`) is the canonical period label. `current_year` for compensation = 2026. Close period is given as an M-code in the request memo (e.g. `M24`); prior period is the prior M-code (e.g. `M23`).
- **Account categories:** revenue = `product_revenue`, `service_revenue`. cogs = `direct_materials_cogs`, `direct_labor_cogs`. sga = `sales_sga`, `admin_sga`, `occupancy_sga`. allocations = `shared_service_allocations`. operating (count, NOT currency) = `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`.
- **Income statement construction:** revenue = Σ(revenue accounts); cogs = Σ(cogs accounts); gross_margin = revenue − cogs; sga = Σ(sga accounts); allocations = Σ(allocations accounts); **ebitda = gross_margin − sga − allocations** (= revenue − cogs − sga − allocations).
- **Operating counts are NOT currency expenses** — never add them into revenue/cogs/sga/ebitda. They are only used as ratio denominators.
- **Rounding:** currency → 2 decimals; percent & ratio fields → 4 decimals, expressed in **decimal form** (e.g. 1.38% = `0.0138`, ebitda margin 24.59% = `0.2459`).
- **Ranks are descending (1 = best/highest).** `..._rank_desc` = 1 is the top.
- **Lists:** branch_ids ascending stable; conflict_flags sorted alphabetically; per_musician ordered by musician_id; pay_types in rate-book order.
- **Region membership comes from `/api/finance/branches`, NOT from stale memo notes.** A memo may mention a different branch name as a distractor — always use the live branch file.
  - REG-NORTH = BR-001, BR-002, BR-003; REG-WEST = BR-004, BR-005, BR-006; REG-EAST = BR-007, BR-008, BR-011; REG-SOUTH = BR-009, BR-010, BR-012.
- **Ratio denominators use the SUM of the monthly count across the period (naive uniform rollup), NOT the average and NOT the period-end snapshot.**
  - **ARPU** = fiscal-year revenue / **SUM** of monthly `active_customers` across the 12 periods.
  - **sales_per_labor_headcount** = fiscal-year revenue / **SUM** of monthly `labor_headcount` across the 12 periods.
  - For a region, denominator = SUM of the count across all branches in the region × the 12 periods (i.e. sum every monthly value for every branch).
- **"sales growth" = revenue growth.** `top_sales_growth_branch_id` = the branch with the highest fiscal-year revenue growth (FY2025 vs FY2024). "sales" and "revenue" are synonyms here; `sales_growth_rank_desc` is the rank of the target branch by that same revenue-growth metric.
- **region_reconciliation_variance = 0.00** — the region figure is the sum of its branch figures, so they tie out exactly.

## 2. SOP — Branch close (per-branch monthly management package)
Inputs: target_branch_id, close_period (M-code), prior_period (M-code). Build one JSON object.
1. Fetch branches, period-map, accounts, records.
2. `period_convention`: `M1_to_M12` = "FY2024"; `M13_to_M24` = "FY2025"; `current_month` = close_period code (e.g. "M24"); `prior_month` = prior_period code (e.g. "M23"). **Use the M-code string, not "Dec FY2025".**
3. **m24_income_statement** (single close-period month): for the close M-code, sum that period's value across each account in the category, build revenue/cogs/gross_margin/sga/allocations/ebitda.
4. **mom_revenue_variance**: amount = close_revenue − prior_revenue; pct = amount / prior_revenue.
5. **fy2025_vs_fy2024**: sum M13–M24 for FY2025, M1–M12 for FY2024, for each IS line. Add `ebitda_margin` = fy2025 ebitda / fy2025 revenue; `arpu` = fy2025 revenue / SUM(fy2025 active_customers); `sales_per_labor_headcount` = fy2025 revenue / SUM(fy2025 labor_headcount). `revenue_growth_pct` = (fy25−fy24)/fy24 revenue; `ebitda_growth_pct` = (fy25−fy24)/fy24 ebitda.
6. **region_context**: region_id from branches file; branch_ids = that region's branches ascending; `fy2025_ebitda` = sum of fy2025 ebitda across the region's branches; `ebitda_rank_desc` = the region's rank among all 4 regions by fy2025 ebitda (1 = highest).
7. **branch_rankings**: compute every branch's fy2025-vs-fy2024 revenue growth; `sales_growth_rank_desc` = the target branch's rank (1=highest); `top_sales_growth_branch_id` = branch with the highest revenue growth; `top_arpu_branch_id` = branch with the highest fy2025 ARPU (revenue / SUM active_customers).

## 3. SOP — Compensation current-year summary (per ensemble)
Inputs: ensemble_id. Build one JSON object. (This engine scored 1.0 — follow exactly.)
1. Fetch compensation rate-book and rosters; filter rosters by ensemble_id.
2. Rate-book constants: MWS = 2520.0/week; pay_types order = ["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]; quarter_weeks default Q1–Q4 = 13 each (but use each employee's `weeks_by_quarter`).
3. Per-employee weekly rates:
   - Minimum Weekly Scale = 2520.0.
   - Titled Position Premium weekly = 2520.0 × title_premium_pct, where Concertmaster=0.22, Principal=0.20, Section Lead=0.15, Associate Principal=0.10, Assistant Principal=0.10. **Skip this pay type entirely when `combined_overscale_includes_title` is true** (the overscale figure already bundles the title premium). No title → 0.
   - Seniority weekly = band for `years_of_service`: 0–4→0.0, 5–9→48.0, 10–14→82.0, 15–19→126.0, 20–24→170.0, 25+→215.0.
   - Overscale weekly = `overscale_weekly` (0 if absent).
4. For each quarter, pay for a type = its weekly rate × that quarter's weeks (from `weeks_by_quarter`, so partial-quarter employees use their actual weeks). Sum across employees.
5. `quarter_totals` Q1–Q4 = total pay (all 4 types) in that quarter across the ensemble.
6. `annual_pay_type_totals` = sum across employees & quarters per pay type. `annual_total` = sum of all four.
7. `largest_pay_type` = the pay type with the largest annual total (almost always Minimum Weekly Scale).
8. `combined_overscale_employee_count` = number of employees with `combined_overscale_includes_title` == true.
9. `partial_quarter_employee_count` = number of employees with any quarter weeks ≠ 13.
10. `current_year` = rate-book `current_year` (2026). `roster_count` = number of employees.

## 4. SOP — Weekly payroll review (per production)
Inputs: production_id. Build one JSON object. Fetch payroll rate-book + productions.
- service_rates (per service, except rehearsal): Performance 260.25, Audit 260.25, "2hr Sound Check" 142.5, "1hr Sound Check" 80.0. **Rehearsal = 58.75/hour with a three-hour minimum call** (pay = 58.75 × max(duration_hours, 3.0)).
- service_time_limits: "1hr Sound Check" 1.0, "2hr Sound Check" 2.0, Audit 3.0, Performance 3.0, Rehearsal 5.0 (hours).
- premium_pct: electronic 0.25, concertmaster 0.20, principal_or_lead 0.15, quartet 0.15, first_double 0.25, additional_double 0.10, vacation 0.04.
- weekly_guarantee = 2082.0. conflict thresholds: rehearsal_earliest_start 09:00, rehearsal_latest_end 18:30.
- Per musician: base service pay = Σ assigned services' pay. `premium` = (sum of applicable role premiums: electronic + principal_or_lead + quartet + concertmaster, additive) × base. `doubles` = (25% if doubles≥1) + (10% × (doubles−1) if doubles≥2), × base. `vacation` = 0.04 × (base + premium + doubles) when vacation_eligible. `guarantee_adjustment`: for non-substitute players whose base service pay < weekly_guarantee. `substitute_adjustment`: applies for substitute musicians (electronic-substitute treatment). `top_paid_musician_id` = musician with the highest total.
- category_totals keys (lowercase): performance, audit, rehearsal, sound_check (both 1hr & 2hr sound checks combined), premium, doubles, vacation, guarantee_adjustment, substitute_adjustment (only when applicable).
- service_counts = map of service_type → count, using the schedule's exact service_type strings.
- conflict_flags (sorted): REHEARSAL_EARLY_START (rehearsal start < 09:00); REHEARSAL_LATE_END (rehearsal end > 18:30); SERVICE_OVER_TIME_LIMIT (any service duration_hours > its service_time_limit); SOUND_CHECK_DURATION_MISMATCH ("1hr Sound Check" duration ≠ 1.0, or "2hr Sound Check" duration ≠ 2.0).
- per_musician entries: {musician_id, name, total, categories:{nonzero category→amount}}; ordered by musician_id; weekly_total = Σ category_totals.

**Known payroll pitfalls (this family was the hardest to lock down):** the rehearsal "three-hour minimum call" interpretation, the exact guarantee base (base service pay vs. make-whole on total), the premium stacking (additive on base service pay is the natural reading of "premiums applied to base service pay before vacation"), and the electronic-substitute / substitute_adjustment treatment all need care. Re-derive each from the rate-book `business_rules` list and test against the production's roster flags. The structural fields that are unambiguous: production_id, service_counts (by service_type), and the four conflict-flag enums above.

## 5. SOP — Regional dashboard (per region)
Inputs: target_region_id, years [2024, 2025]. Build one JSON object. (Scored 1.0.)
1. `region_id` = target. `branch_ids` = ascending list of that region's branches (from branches file).
2. `fy2024` / `fy2025`: revenue, sga, allocations, ebitda each = SUM across the region's branches of that line (M1–M12 for 2024, M13–M24 for 2025).
3. `fy2025.ebitda_margin` = fy2025 ebitda / fy2025 revenue. `fy2025.sales_per_labor_headcount` = fy2025 region revenue / SUM of monthly labor_headcount across all region branches (M13–M24).
4. `revenue_growth_pct` = (fy2025 − fy2024) region revenue / fy2024 region revenue.
5. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch in the region with the max / min fy2025 ebitda.
6. `region_reconciliation_variance` = 0.00 (region = sum of branches).

## 6. SOP — Compensation forecast (per ensemble + scenario)
Inputs: ensemble_id, scenario_id, forecast years [current, year_plus_1, year_plus_2]. Build one JSON object.
1. Fetch rate-book, rosters (filter ensemble), scenarios (pick scenario_id).
2. **Cumulative per-pay-type growth**, compounding year over year. For year δ (1 or 2), build factors:
   - mws_f = ∏(1 + mws_growth) over years 1..δ.
   - sen_f = ∏(1 + seniority_growth) over years 1..δ.
   - over_f = ∏(1 + overscale_growth) over years 1..δ.
   - title_mult = ∏ title_pct_multiplier over years 1..δ.
3. Per-employee weekly rates for year δ:
   - MWS weekly = 2520 × mws_f.
   - Titled Position Premium weekly = **(grown MWS = 2520 × mws_f) × title_premium_pct × title_mult**. (Title premium rides on the grown MWS; confirmed that base-MWS is wrong.) Skip when combined_overscale_includes_title.
   - Seniority weekly = band(years_of_service + δ) × sen_f — i.e. **advance service by δ years for the band lookup, AND grow the band amount by sen_f**.
   - Overscale weekly = overscale_weekly × over_f.
4. Pay per quarter = weekly rate × weeks_by_quarter; sum across employees & quarters.
5. `annual_totals`: current (δ=0, base rates), year_plus_1 (δ=1), year_plus_2 (δ=2).
6. `growth_rates`: year_plus_1_vs_current = (y1−current)/current; year_plus_2_vs_year_plus_1 = (y2−y1)/y1.
7. `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` from the δ=2 computation.
8. `largest_growth_pay_type` = pay type with the largest **percentage** growth from current to year_plus_2 (for board scenarios with seniority band advancement this is normally **Seniority**, because advancing service years pushes employees into higher bands — MWS/title grow only at the mws rate, overscale at the overscale rate). Use the rate with the largest (y2−y0)/y0.
9. `combined_overscale_employee_count` and `partial_quarter_employee_count` as in the current-year SOP (roster flags are unchanged by the forecast).

## 7. Common misjudgments to avoid
- Don't use monthly **average** or period-**end** counts for ARPU / sales-per-labor — use the **SUM** of the monthly values.
- Don't label periods "Dec FY2025"; use the M-code ("M24").
- Don't trust a memo's branch/region hint over the live branches file.
- Don't treat operating counts (orders, revenue_units, active_customers, labor_headcount) as currency in the income statement.
- Don't forget to skip the Titled Position Premium for `combined_overscale_includes_title` employees.
- Don't use fixed 13-week quarters for employees with `weeks_by_quarter` differing from 13.
- Don't advance seniority bands in the current-year summary (advancement is forecast-only: +1 for year_plus_1, +2 for year_plus_2).
- Rank descending = 1 is best, for ebitda rank and sales-growth rank.
- Region totals = sum of branch totals; reconciliation variance is 0.00.
