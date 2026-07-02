# SKILL.md — Crescent Finance Ops Reporting (task_group_009)

Reusable skill for solving Crescent Arts Collective Finance Ops reporting tasks. Covers five task families: branch close, compensation current-year, weekly payroll, regional dashboard, compensation forecast. All conventions below were verified against the live remote environment and the train-only judge.

## 0. Environment & data access

- Live remote base URL: `<remote-env-url>` (NEVER use 127.0.0.1).
- Fetch with `curl -sS <BASE>/<endpoint>`. All responses are JSON.
- Endpoints:
  - `GET /api/finance/branches` — branch_id, branch_name, region_id, region_name.
  - `GET /api/finance/period-map` — maps period label M1..M24 → fiscal_year, month_name, month_number.
  - `GET /api/finance/accounts` — account → category (revenue/cogs/sga/allocations/operating) + metric_type (currency/count).
  - `GET /api/finance/records` — list of {account, branch_id, branch_name, region_id, values:{M1..M24}}. Filter `?branch_id=`, `?region=`, `?account=`. Each record is one (branch, account) with all 24 monthly values.
  - `GET /api/compensation/rate-book` — pay types, MWS, seniority bands, title premium %, quarter weeks, business rules.
  - `GET /api/compensation/rosters` — list of employees. Filter `?ensemble_id=`. Fields: employee_id, ensemble_id, title, years_of_service, overscale_weekly, weeks_by_quarter{Q1..Q4}, combined_overscale_includes_title, notes.
  - `GET /api/compensation/scenarios` — named scenarios with year_plus_1/year_plus_2 drivers (mws_growth, overscale_growth, seniority_growth, title_pct_multiplier).
  - `GET /api/payroll/rate-book` — service_rates, service_time_limits, premium_pct, weekly_guarantee, conflict_thresholds, business rules.
  - `GET /api/payroll/productions` — list of productions. Filter `?production_id=`. Each has roster[] and schedule[].

## 1. Shared conventions (apply to every family)

### Rounding & formatting
- Currency fields: round to **2 decimals**.
- Percent / ratio / margin fields ("decimal percent"): round to **4 decimals**, expressed as a decimal (e.g. 6.92% → `0.0692`, NOT `6.92`).
- Lists of IDs: **ascending stable IDs** (e.g. `["BR-004","BR-005","BR-006"]`).
- Rank fields suffixed `_rank_desc`: rank in **descending** order where **1 = best/highest**.
- Integer counts: plain integers.
- Return exactly the keys in the answer_template; include conditional sub-keys only as the template indicates.

### Period → fiscal-year convention (CONFIRMED)
- **M1..M12 = FY2024**, **M13..M24 = FY2025**. (FY = calendar year; M13 = Jan of next fiscal year.)
- M24 = Dec FY2025, M23 = Nov FY2025. Close period is a single month (e.g. M24); prior period is the previous month (M23).
- `period_convention` object: `M1_to_M12:"FY2024"`, `M13_to_M24:"FY2025"`, `current_month`/`prior_month` = the period labels (e.g. `"M24"`,`"M23"`).

### Branches & regions (CONFIRMED)
12 branches across 4 regions (3 branches each):
- REG-NORTH: BR-001 Aurora North, BR-002 Granite Bay, BR-003 Lakeview
- REG-WEST: BR-004 Harbor North, BR-005 Pine Hill, BR-006 Mesa Ridge
- REG-EAST: BR-007 Riverbend, BR-008 Old Port, BR-011 Summit Yard
- REG-SOUTH: BR-009 Beacon South, BR-010 Coral Point, BR-012 Valley Forge
- **Always derive region membership from `/api/finance/branches` (the active ops data),** not from any stale memo note. Do NOT exclude a branch from its region based on a memo.

### Finance accounts & income-statement construction (CONFIRMED)
Account categories (from `/api/finance/accounts`):
- revenue = `product_revenue` + `service_revenue`
- cogs = `direct_materials_cogs` + `direct_labor_cogs`
- gross_margin = revenue − cogs
- sga = `sales_sga` + `admin_sga` + `occupancy_sga`
- allocations = `shared_service_allocations`
- ebitda = gross_margin − sga − allocations
- **operating counts** (`orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`) are **COUNTS, not currency expenses** — never add them into the income statement.

For a period or fiscal year, sum the monthly `values` for the relevant M-periods:
- Single month (income statement): use that one M-period.
- Fiscal year: FY2024 = sum M1..M12; FY2025 = sum M13..M24.
- Region/branch-set aggregate: sum across all branches in the set.

### Key ratios (CONFIRMED — use SUM of monthly operating counts, NOT average)
- `ebitda_margin` = ebitda / revenue (decimal 4dp).
- `arpu` = FY revenue / **FY SUM(active_customers)** (currency 2dp). Use the sum of the 12 monthly count values, not the monthly average.
- `sales_per_labor_headcount` = FY revenue / **FY SUM(labor_headcount)** (currency 2dp). Sum, not average. (Confirmed at both branch and region level.)
- MoM variance: amount = current_rev − prior_rev; pct = (current_rev − prior_rev) / prior_rev (4dp).
- revenue_growth_pct / ebitda_growth_pct = (new − old) / old (4dp).

### Rank conventions (CONFIRMED)
- `*_rank_desc` = 1 is best (descending sort by the metric).
- **region_context.ebitda_rank_desc** = the **region's** rank among **ALL regions** by FY ebitda (1 = highest region). NOT the branch's rank within its region.
- region_context.fy2025_ebitda = the **region's aggregate** FY ebitda (sum of the region's branches).
- branch-level rank fields (e.g. sales_growth_rank_desc) = the **target branch's** rank among **all 12 branches**.
- top_*_branch_id = the branch achieving the max of that metric.

## 2. SOP — Branch close (monthly close package)

Inputs: target_branch_id, close_period (e.g. M24), prior_period (e.g. M23). Output keys: target_branch_id, target_branch_name, period_convention, m24_income_statement, mom_revenue_variance, fy2025_vs_fy2024, region_context, branch_rankings.

1. Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`.
2. Index records by (branch_id, account). Identify the target branch name & region.
3. **m24_income_statement** (single close-period month): for the target branch, sum each account category for the one M-period; build revenue/cogs/gross_margin/sga/allocations/ebitda per §1.
4. **mom_revenue_variance**: revenue(close_period) − revenue(prior_period); pct = amount / revenue(prior_period). (decimal 4dp)
5. **fy2025_vs_fy2024**: build full IS for FY2025 (M13..M24) and FY2024 (M1..M12). For FY2025 also compute ebitda_margin, arpu (rev/FY sum active_customers), sales_per_labor_headcount (rev/FY sum labor_headcount). revenue_growth_pct & ebitda_growth_pct = (FY25−FY24)/FY24.
6. **region_context**: region_id; branch_ids = sorted region members; fy2025_ebitda = SUM of FY2025 ebitda across region branches; **ebitda_rank_desc = region's rank among all 4 regions by FY2025 ebitda (desc, 1=best)**.
7. **branch_rankings** (across ALL 12 branches): sales_growth_rank_desc = target branch's rank by FY25-vs-FY24 revenue growth (desc); top_sales_growth_branch_id = highest growth branch; top_arpu_branch_id = highest arpu branch (sum-based arpu, same ranking as average since all branch arpus scale by 1/12).
8. Round: currency 2dp, decimals 4dp.

Watch-outs: region rank is the REGION's rank vs other regions, not the branch's rank within region. arpu/per-headcount use SUM of monthly counts.

## 3. SOP — Compensation current-year summary

Inputs: ensemble_id. Output keys: ensemble_id, current_year, roster_count, pay_types, quarter_totals, annual_pay_type_totals, annual_total, largest_pay_type, combined_overscale_employee_count, partial_quarter_employee_count.

Rate book (`/api/compensation/rate-book`): current_year=2026, minimum_weekly_scale=2520.0, quarter_weeks all 13.
- pay_types (ordered): `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`.
- seniority_weekly bands (by years_of_service): 0-4 → 0.0; 5-9 → 48.0; 10-14 → 82.0; 15-19 → 126.0; 20-24 → 170.0; 25+ → 215.0.
- title_premium_pct: Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15. (No title → 0.)

Per employee, per quarter Q (weeks = weeks_by_quarter[Q]):
- MWS_Q = 2520.0 × weeks
- Titled Position Premium_Q = 2520.0 × title_premium_pct[title] × weeks — **SKIP (0) if combined_overscale_includes_title is true** (the title premium is already bundled in that employee's overscale).
- Seniority_Q = seniority_weekly[band(years_of_service)] × weeks
- Overscale_Q = overscale_weekly × weeks
- quarter_total[Q] += sum of the four.

Aggregate:
- annual_pay_type_totals = sum across employees & quarters of each pay type.
- quarter_totals{Q1..Q4} = sum across employees for that quarter.
- annual_total = sum of all pay types (== sum of quarter_totals).
- largest_pay_type = pay type with the **max annual total** (by amount).
- roster_count = employees in the ensemble.
- combined_overscale_employee_count = count where combined_overscale_includes_title == true.
- partial_quarter_employee_count = count where **any** quarter weeks != 13.

Critical rules:
- **Use each employee's roster weeks_by_quarter, not a fixed 13**, when partial-quarter employees are present (e.g. Q2=9, Q3=10). This lowers the relevant quarter total.
- combined_overscale employees get NO separate titled-position-premium line (their overscale_weekly already includes it); still count them in combined_overscale_employee_count.
- current_year = the rate-book `current_year` (2026).

## 4. SOP — Weekly payroll review

Inputs: production_id. Output keys: production_id, service_counts, category_totals, weekly_total, conflict_flags, per_musician, top_paid_musician_id.

Rate book (`/api/payroll/rate-book`):
- service_rates (per service, flat): Performance 260.25, Audit 260.25, 1hr Sound Check 80.0, 2hr Sound Check 142.5. **Rehearsal 58.75 is HOURLY with a 3-hour minimum call** → rehearsal pay = 58.75 × max(duration_hours, 3.0).
- service_time_limits: 1hr Sound Check 1.0, 2hr Sound Check 2.0, Audit 3.0, Performance 3.0, Rehearsal 5.0 (used for conflict flags, not to cap pay).
- premium_pct: electronic 0.25, principal_or_lead 0.15, quartet 0.15, concertmaster 0.20, first_double 0.25, additional_double 0.10, vacation 0.04.
- weekly_guarantee 2082.0; conflict_thresholds: rehearsal_earliest_start "09:00", rehearsal_latest_end "18:30".

Pay categories (in template order): performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment, substitute_adjustment.

Per musician, per assigned service:
- Base service pay: flat rate per service type; rehearsal = 58.75 × max(duration, 3.0). Categorize into performance/audit/rehearsal/sound_check (1hr & 2hr sound checks both → sound_check).
- **premium** (role premiums, applied to base service pay, additive): electronic 0.25 if electronic; principal_or_lead 0.15 if principal OR lead; quartet 0.15 if quartet; concertmaster 0.20 if concertmaster. Sum applicable % × base. (Role premiums are ADDITIVE on base, per the rule "premiums applied to base service pay".)
- **doubles** (separate category, on base): first_double 0.25 for the first extra instrument + additional_double 0.10 × (doubles−1) for each additional. For doubles=1 → 0.25×base; doubles=2 → 0.35×base; doubles=3 → 0.45×base.
- **vacation** = 0.04 × (base + premium + doubles) when vacation_eligible is true (doubles counts as a premium — included in the vacation base). Else 0.
- **guarantee_adjustment**: regular (non-substitute) players whose pay would fall below the weekly guarantee. **Most likely interpretation (deduced, not judge-confirmed): tops up TOTAL weekly pay to weekly_guarantee** → guarantee_adjustment = max(0, 2082.0 − (base + premium + doubles + vacation)), for non-substitute players. This brings the lowest earner to exactly 2082.0. Substitutes get no guarantee. (A base-only top-up, 2082−base, was tried and did NOT score; the total-top-up interpretation is the best remaining hypothesis. If the judge rejects this, alternative is guarantee = max(0, 2082 − (base+premium+doubles)) before vacation.)
- **substitute_adjustment**: include only when a specific substitute adjustment applies; otherwise omit/0. Substitutes still receive their role premiums (electronic, doubles) — they are only excluded from guarantee & vacation (vacation via vacation_eligible flag). "Electronic substitute treatment" is a called-out special area: do NOT strip premiums from substitutes unless a rule says so.
- per_musician total = sum of that musician's categories. per_musician[] sorted by musician_id; each entry's `categories` = ONLY nonzero category names → rounded amount.

Aggregates:
- category_totals = sum across musicians of each category (include a category key only when nonzero, except follow template for substitute_adjustment "when applicable").
- weekly_total = sum of all category_totals.
- service_counts = {service_type → count of services of that type in the schedule} (e.g. {"Rehearsal":2,"1hr Sound Check":1,"Performance":4,"Audit":1}). Include only service types that occur.
- top_paid_musician_id = musician with the highest per-musician total.

**Conflict flags** (production-level, sorted alphabetically; enum: REHEARSAL_EARLY_START, REHEARSAL_LATE_END, SERVICE_OVER_TIME_LIMIT, SOUND_CHECK_DURATION_MISMATCH):
- REHEARSAL_EARLY_START if any rehearsal start_time < "09:00".
- REHEARSAL_LATE_END if any rehearsal end_time > "18:30".
- SERVICE_OVER_TIME_LIMIT if any service duration_hours > service_time_limits[service_type].
- SOUND_CHECK_DURATION_MISMATCH if a sound-check service's duration ≠ expected (1.0 for "1hr Sound Check", 2.0 for "2hr Sound Check").

Watch-outs (from reflect loop): category_totals and per_musician appear to be scored as composite (all-or-nothing) units — one wrong sub-field fails the whole group, so every component must be correct. The unresolved item in this family is the exact guarantee/substitute-adjustment basis; the total-top-up guarantee is the strongest hypothesis. Premiums are additive on base (multiplicative was tested and did not change the score). Vacation includes doubles in its base.

## 5. SOP — Regional management dashboard

Inputs: target_region_id, comparison years [2024,2025]. Output keys: region_id, branch_ids, fy2024, fy2025, revenue_growth_pct, top_ebitda_branch_id, bottom_ebitda_branch_id, region_reconciliation_variance.

1. Fetch branches + records. region branches = branches where region_id == target, sorted ascending.
2. **fy2024 / fy2025**: across the region's branches, sum revenue, sga, allocations, ebitda for M1..M12 (FY2024) and M13..M24 (FY2025). (IS construction per §1; report only revenue, sga, allocations, ebitda as the template requests.)
3. fy2025 also: ebitda_margin = fy2025_ebitda / fy2025_revenue (4dp); sales_per_labor_headcount = fy2025_revenue / **FY2025 SUM(labor_headcount) across region branches** (2dp, sum convention).
4. revenue_growth_pct = (fy2025_revenue − fy2024_revenue) / fy2024_revenue (4dp).
5. top_ebitda_branch_id / bottom_ebitda_branch_id = region branch with max / min FY2025 ebitda.
6. **region_reconciliation_variance = 0.0** (the region aggregate ties out exactly to the sum of branch monthly data; confirmed correct).

## 6. SOP — Compensation forecast (board)

Inputs: ensemble_id, scenario_id, forecast_years [current, year_plus_1, year_plus_2]. Output keys: ensemble_id, scenario_id, annual_totals, growth_rates, year_plus_2_quarter_totals, year_plus_2_pay_type_totals, largest_growth_pay_type, combined_overscale_employee_count, partial_quarter_employee_count.

Scenario (`/api/compensation/scenarios[scenario_id]`) gives per-year drivers: mws_growth, overscale_growth, seniority_growth, title_pct_multiplier (for year_plus_1 and year_plus_2). Growth is **cumulative** (compounds across forecast years).

For each employee and each forecast year (year=0 current, 1 = year_plus_1, 2 = year_plus_2):
- Cumulative growth factor for a driver: year0 → 1.0; year1 → (1+g_y1); year2 → (1+g_y1)×(1+g_y2).
- **MWS_weekly(year)** = 2520.0 × cumulative(mws_growth).
- **Overscale_weekly(year)** = overscale_weekly × cumulative(overscale_growth).
- **Seniority_weekly(year)** = seniority_band(years_of_service + year) × cumulative(seniority_growth). **Advance years_of_service by +1 for year_plus_1 and +2 for year_plus_2 before assigning the band** (this can cause band crossings and large seniority jumps — that is intended).
- **Title premium_weekly(year)** = title_premium_pct[title] × cumulative(title_pct_multiplier) × **MWS_weekly(year)** × ... — SKIP if combined_overscale_includes_title. **The title premium grows WITH the MWS base** (confirmed: using a constant/current MWS base scored far worse). cumulative(title_pct_multiplier): year0→1.0; year1→mult_y1; year2→mult_y1×mult_y2.
- Per quarter Q: component × weeks_by_quarter[Q] (use roster quarter weeks, incl. partial-quarter employees).

Aggregates:
- annual_totals.{current,year_plus_1,year_plus_2} = total comp across all employees for that year.
- growth_rates: year_plus_1_vs_current = (y1−current)/current; year_plus_2_vs_year_plus_1 = (y2−y1)/y1 (4dp).
- year_plus_2_quarter_totals{Q1..Q4} = sum across employees of year_plus_2 total pay for that quarter.
- year_plus_2_pay_type_totals = {MWS, Titled Position Premium, Seniority, Overscale} summed across employees/quarters at year_plus_2.
- **largest_growth_pay_type** = pay type with the highest **growth RATE** from current → year_plus_2 (NOT absolute dollars). Because of seniority band crossings, this is typically **Seniority** (a high % growth); MWS/Title grow ~6-7%, Overscale ~2-3%. The enum value must be consistent with your own submitted pay_type_totals growth rates.
- combined_overscale_employee_count / partial_quarter_employee_count: same as current-year (roster-based counts, unchanged by forecast).

Watch-outs (from reflect loop): title premium MUST use the grown MWS base (constant-base scored 0.33 vs 0.80). largest_growth is by growth RATE (absolute/dollars scored lower and was inconsistent with the data). Growth is cumulative (compounding). Best-observed score on this family was 0.80; a residual ~0.20 gap remained unresolved — re-check seniority cumulative-growth application and partial-quarter handling in forecast years if a forecast task misses.

## 7. Common pitfalls (cross-family)

- **Operating counts are not currency** — never sum active_customers/labor_headcount/orders into revenue or expenses.
- **arpu & sales_per_labor_headcount use SUM of monthly counts, not the monthly average.** (Average was tested and scored worse.)
- **region_context.ebitda_rank_desc is the REGION's rank among all regions**, not the branch's rank within its region (mixing these is a classic error).
- **Do not exclude a branch from its region based on a stale memo** — use the active `/api/finance/branches` data.
- **rank_desc = 1 is best** (descending). A rank of 1 means highest.
- **Rehearsal pay is hourly** (58.75 × hours, 3hr minimum), while Performance/Audit/Sound-Check are flat per-service. Don't multiply rehearsal by a flat per-service rate.
- **combined_overscale_includes_title → no separate title premium** for that employee; their overscale_weekly already includes it.
- **Forecast: advance years_of_service** before picking the seniority band — band crossings drive most of the seniority (and total) growth.
- **Forecast: title premium grows with MWS** (use the year's grown MWS as the base, not the current MWS).
- **Forecast: largest_growth_pay_type is by growth RATE**, and Seniority usually wins because of band crossings.
- **Payroll category_totals and per_musician are composite-scored** — every sub-field must be right for the group to score; isolate each component carefully.
- **decimal percent** means the decimal form (0.0138), not the percentage number (1.38).
