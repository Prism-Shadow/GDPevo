# Crescent Finance Ops — Solver Skill (task_group_009)

A reusable SOP for the five task families in this group: **branch close**, **compensation current-year**, **weekly payroll**, **regional dashboard**, **compensation forecast**. All rules below were confirmed by fetching the live remote environment and computing the train tasks end-to-end. Worked numbers from the train tasks are included ONLY as illustrations of each rule (they are not to be copied verbatim for test tasks — recompute against the live data for any new target id).

---

## 0. Environment & shared conventions

### Base URL (LIVE remote — always use this)
`<remote-env-url>`
The staged `payloads/environment_access.json` already carries this remote `base_url`. NEVER use `127.0.0.1` / a local dev server — it is not running. Fetch with `curl -s $BASE/<endpoint>`; all responses are JSON.

### Endpoint catalog
| Endpoint | Returns | Used by |
|---|---|---|
| `GET /health` | `{status:ok}` sanity check | all |
| `GET /api/manifest` | entity lists + record_counts + seed | discovery |
| `GET /api/finance/branches` | 12 branches w/ canonical `branch_id`→`region_id`→`region_name` | finance families |
| `GET /api/finance/period-map` | 24 monthly periods M1..M24 → fiscal_year/month_name/month_number | finance families |
| `GET /api/finance/accounts` | 14 accounts w/ `category` + `metric_type` | finance families |
| `GET /api/finance/records` | 168 rows = 14 accounts × 12 branches; each row = `{account, branch_id, branch_name, region_id, values:{M1..M24}}` | finance families |
| `GET /api/compensation/rate-book` | MWS, pay_types, quarter_weeks, seniority_weekly, title_premium_pct, business_rules, `current_year`=2026 | comp families |
| `GET /api/compensation/rosters` | 109 employees across 4 ensembles; per-employee `title, years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter` | comp families |
| `GET /api/compensation/scenarios` | 4 scenarios; each has `year_plus_1`/`year_plus_2` drivers | forecast |
| `GET /api/payroll/rate-book` | service_rates, service_time_limits, premium_pct, weekly_guarantee, conflict_thresholds, business_rules | payroll |
| `GET /api/payroll/productions` | 17 productions; each = `{production_id, title, week_start, roster[], schedule[]}` | payroll |

Useful query filters: `?branch_id=BR-009`, `?region=REG-SOUTH`, `?account=product_revenue`, `?ensemble_id=ENS-REDWOOD`, `?production_id=PROD-HAMILTON-26`. (It is usually simpler to fetch the whole collection once and index it in Python.)

### Rounding rules (follow the `field_types` label in each answer_template)
- **currency** → 2 decimals.
- **decimal percent / ratio** → 4 decimals, expressed as a decimal fraction (e.g. `0.0138`, NOT `1.38`).
- **integer** counts → exact integer.
- Lists: ascending stable IDs unless a rank field says otherwise; `conflict_flags` sorted alphabetically; `per_musician` ordered by `musician_id`.
- ARPU and sales_per_labor_headcount are labeled `currency` in the templates → round to **2 decimals** (even though they are computed as ratios). `ebitda_margin`, `revenue_growth_pct`, `ebitda_growth_pct`, MoM `pct`, forecast `growth_rates` are `decimal percent` → **4 decimals**.

### Period → fiscal-year convention (CONFIRMED from period-map)
- `M1..M12` → **FY2024** (Jan..Dec 2024).
- `M13..M24` → **FY2025** (Jan..Dec 2025).
- `M23` = Nov 2025, `M24` = Dec 2025. A fiscal year = 12 consecutive M-periods.
- For `period_convention`: `M1_to_M12` = `"FY2024"`, `M13_to_M24` = `"FY2025"`. `current_month`/`prior_month` are period-label strings — use the M-code of the close/prior period (e.g. `"M24"`, `"M23"`); a `"Dec 2025"`/`"Nov 2025"` style is an acceptable alternative if the template expects a human label.

### Account categories (CONFIRMED from /api/finance/accounts)
- **revenue**: `product_revenue`, `service_revenue`
- **cogs**: `direct_materials_cogs`, `direct_labor_cogs`
- **sga**: `sales_sga`, `admin_sga`, `occupancy_sga`
- **allocations**: `shared_service_allocations`
- **operating** (metric_type = `count`, NOT currency — never sum these into revenue/ebitda): `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`

### Income-statement construction (CONFIRMED)
- `revenue` = Σ revenue accounts
- `cogs` = Σ cogs accounts
- `gross_margin` = revenue − cogs
- `sga` = Σ sga accounts
- `allocations` = Σ allocations accounts
- `ebitda` = revenue − cogs − sga − allocations (= gross_margin − sga − allocations). EBITDA always subtracts COGS, **even in regional views where the cogs/gross_margin fields are not displayed**.
- `ebitda_margin` = ebitda / revenue
- `arpu` = revenue / (Σ `active_customers` over the same periods)
- `sales_per_labor_headcount` = revenue / (Σ `labor_headcount` over the same periods)
  - operating counts are stored as period values just like currency accounts; sum them across the same periods used for revenue.

### Region membership (CONFIRMED from /api/finance/branches — canonical source of truth)
- REG-NORTH: BR-001, BR-002, BR-003
- REG-WEST: BR-004, BR-005, BR-006
- REG-EAST: BR-007, BR-008, BR-011
- REG-SOUTH: BR-009, BR-010, BR-012
- **Always derive region membership from `/api/finance/branches`.** Ignore any stale/draft "background notes" or claimed region in a request memo. Do NOT exclude a branch from its region because a memo says otherwise. The active operations data is authoritative.
- `branch_ids` lists are ascending-sorted.
- `ebitda_rank_desc` / `*_rank_desc` = descending rank (1 = best/highest). For region ebitda rank, rank the target branch among its region's branches by FY2025 ebitda descending.

### Dataset facts (seed 9009)
- 12 branches, 4 regions, 168 finance records (14 accounts × 12 branches; each row carries all 24 M-periods).
- 4 ensembles: ENS-CEDAR (31), ENS-MAPLE (28), ENS-OAK (24), ENS-REDWOOD (26) — 109 roster rows total.
- 17 productions. Payroll roster flags available: `lead, principal, quartet, electronic, doubles, substitute, vacation_eligible` (NO `concertmaster` or `guaranteed` flag on productions — the concertmaster premium is defined in the rate book but no production roster sets it, so it is $0 in payroll).

---

## 1. Family: Branch close (train_001 — `BR_CLOSE`)

### Inputs
`request_memo`: `target_branch_id`, `close_period` (e.g. M24), `prior_period` (e.g. M23). Reporting focus: income statement, revenue variance, current-FY metrics, regional context, branch rankings.

### Step-by-step SOP
1. Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`. Index records by `(branch_id, account)` → `values[M]`.
2. **`target_branch_id` / `target_branch_name`**: from branches list. `period_convention`: M1-M12→FY2024, M13-M24→FY2025; `current_month`=close_period code, `prior_month`=prior_period code.
3. **`m24_income_statement`** (single-period IS for close_period): sum each account category over `[close_period]` only.
   - Worked (BR-004, M24): revenue `293306.29`, cogs `108946.99`, gross_margin `184359.30`, sga `100245.35`, allocations `9280.16`, ebitda `74833.79`.
4. **`mom_revenue_variance`**: `amount` = revenue(close_period) − revenue(prior_period); `pct` = amount / revenue(prior_period), 4dp.
   - Worked (BR-004): M23 revenue `289310.14`, amount `3996.15`, pct `0.0138`.
5. **`fy2025_vs_fy2024`**: 
   - FY2024 = sum of M1..M12; FY2025 = sum of M13..M24 (for every category).
   - `fy2025` block: revenue, cogs, gross_margin, sga, allocations, ebitda, `ebitda_margin` (=fy2025 ebitda/fy2025 revenue, 4dp), `arpu` (=fy2025 revenue / Σ active_customers M13..M24, currency 2dp), `sales_per_labor_headcount` (=fy2025 revenue / Σ labor_headcount M13..M24, currency 2dp).
   - Worked (BR-004): FY2024 revenue `3177038.53` ebitda `749925.74`; FY2025 revenue `3483871.60` ebitda `856610.10` ebitda_margin `0.2459` arpu `999.39` (active_customers=3486) sales_per_labor_hc `24534.31` (labor_hc=142).
   - `revenue_growth_pct` = (fy2025_rev − fy2024_rev)/fy2024_rev, 4dp → `0.0966`.
   - `ebitda_growth_pct` = (fy2025_ebitda − fy2024_ebitda)/fy2024_ebitda, 4dp → `0.1423`.
6. **`region_context`**: target branch's region from canonical map. `branch_ids` = ascending list of that region's branches. `fy2025_ebitda` = Σ FY2025 ebitda across region branches. `ebitda_rank_desc` = rank of target branch's FY2025 ebitda within the region, descending (1=best).
   - Worked (BR-004, REG-WEST): branch_ids `[BR-004,BR-005,BR-006]`, fy2025_ebitda `2515012.15`, ebitda_rank_desc `2` (BR-005=1, BR-004=2, BR-006=3).
7. **`branch_rankings`**: compute across ALL 12 branches.
   - `sales_growth_rank_desc` = descending rank of target branch's **annual revenue growth** (FY2025 vs FY2024). `top_sales_growth_branch_id` = branch with max annual revenue growth. `top_arpu_branch_id` = branch with max FY2025 ARPU.
   - Worked (annual): BR-004 rank `2`, top_sales_growth `BR-002`, top_arpu `BR-012`.
   - **Decision point — period for "sales growth":** primary interpretation is annual (FY25 vs FY24), consistent with `top_arpu` using FY2025. If a test task's wording emphasizes the monthly close/MoM, the alternative is MoM (M24 vs M23) revenue growth — under that reading BR-004 ranks 11 and top is still BR-002. Prefer annual unless the task explicitly says "month-over-month".
8. Round: currency 2dp, percents/ratios 4dp. Output keys exactly per template.

---

## 2. Family: Compensation current-year (train_002 — `COMP_CURRENT`)

### Inputs
`request_memo`: `ensemble_id`, `summary_type` = `current_year_by_quarter_and_pay_type`.

### Rate book constants (CONFIRMED, current_year = 2026)
- `minimum_weekly_scale` (MWS) = **2520.0** /week.
- `pay_types` (use this order): `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`.
- `quarter_weeks` default = 13 each — but **use each employee's own `weeks_by_quarter`** (partial-quarter rule).
- `seniority_weekly` bands (by `years_of_service`):
  - 0–4 yrs → 0.00
  - 5–9 → 48.00
  - 10–14 → 82.00
  - 15–19 → 126.00
  - 20–24 → 170.00
  - 25+ (max null) → 215.00
- `title_premium_pct`: Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15, no title (null) → 0.

### Per-employee per-quarter pay computation
For employee `e`, quarter `Q` with `w = e.weeks_by_quarter[Q]`:
- **Minimum Weekly Scale** = MWS × w
- **Titled Position Premium** = `title_premium_pct[title] × MWS × w` … **UNLESS** `e.combined_overscale_includes_title == true`, in which case Titled Position Premium = 0 (the overscale already bundles the title premium per side letter).
- **Seniority** = `band_amount(e.years_of_service) × w`
- **Overscale** = `e.overscale_weekly × w`

### Aggregations & output fields
- `roster_count` = number of employees in the ensemble.
- `pay_types` = the ordered list above.
- `quarter_totals[Q]` = Σ over employees of (MWS + Title + Seniority + Overscale) for that quarter.
- `annual_pay_type_totals[pt]` = Σ over employees & quarters of that pay type.
- `annual_total` = Σ of all pay-type totals.
- `largest_pay_type` = pay type with the largest annual total (enum).
- `combined_overscale_employee_count` = count of employees with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = count of employees with any `weeks_by_quarter[Q] != 13`.

### Worked example (ENS-REDWOOD)
- roster_count `26`; combined_overscale `0`; partial_quarter `3` (employees with Q2=9, Q3=10, Q2=9).
- quarter_totals: Q1 `977636.40`, Q2 `953292.40`, Q3 `969086.40`, Q4 `977636.40`. (Q2/Q3 lower because of partial-quarter employees — each employee's own weeks drive the totals, not a flat 13.)
- annual_pay_type_totals: Minimum Weekly Scale `3379320.00`, Titled Position Premium `297561.60`, Seniority `142790.00`, Overscale `57980.00`; annual_total `3877651.60`; largest = `Minimum Weekly Scale`.
- Sanity: MWS total / 2520 = total employee-weeks (REDWOOD = 1341 = 26×52 − 11 partial-week shortfall).

---

## 3. Family: Weekly payroll (train_003 — `PAYROLL_REVIEW`)

### Inputs
`request_memo`: `production_id`. Fetch `/api/payroll/productions?production_id=...` (or the whole collection and index).

### Rate book constants (CONFIRMED)
- `service_rates` (per service, flat — except Rehearsal): Performance `260.25`, Audit `260.25`, 1hr Sound Check `80.00`, 2hr Sound Check `142.50`, Rehearsal `58.75` **per hour with a 3-hour minimum call**.
- `service_time_limits` (hours, threshold for the over-time flag): Performance 3.0, Audit 3.0, Rehearsal 5.0, 1hr Sound Check 1.0, 2hr Sound Check 2.0.
- `premium_pct`: concertmaster 0.20, principal_or_lead 0.15, quartet 0.15, electronic 0.25, first_double 0.25, additional_double 0.10, vacation 0.04.
- `weekly_guarantee` = `2082.0`.
- `conflict_thresholds`: rehearsal_earliest_start `09:00`, rehearsal_latest_end `18:30`.

### Service pay
- Performance / Audit / 1hr Sound Check / 2hr Sound Check: flat `service_rates[type]` per assigned service (one payment per assigned service_id, regardless of duration; duration only feeds the flags).
- Rehearsal: `max(duration_hours, 3.0) × 58.75` — pay for the actual call length, floored at 3 hours. If duration exceeds the 5.0h time limit, still pay the actual duration (the breach only raises a flag; the time limit is NOT a pay cap).

### Per-musician pay model (stacking order — CONFIRMED)
1. **base service pay** = Σ assigned-service pay, split by category:
   - `performance`, `audit`, `rehearsal`, `sound_check` (sound_check = 1hr + 2hr Sound Check combined).
2. **premium** category = Σ applicable role premiums × base (additive):
   - `principal_or_lead` 15% if `principal==true` OR `lead==true` (single 15%, not doubled if both).
   - `quartet` 15% if `quartet==true`.
   - `concertmaster` 20% if a concertmaster flag were set (none in current productions → 0).
   - Electronic (electronic flag) handling: see substitute_adjustment below for electronic substitutes; a non-substitute electronic musician's 25% electronic premium goes in the `premium` category.
3. **doubles** category = `[0.25 + 0.10 × (doubles − 1)] × base` if `doubles ≥ 1`, else 0. (doubles=1 → 25%; doubles=2 → 35%; doubles=3 → 45%.)
4. **vacation** category = `0.04 × (base + premium + doubles)` if `vacation_eligible==true`, else 0. (All substitutes observed have `vacation_eligible==false`, so substitutes get no vacation.)
5. **guarantee_adjustment** = `max(0, 2082.0 − base service pay)` for **non-substitute** musicians when their base service pay (service earnings only, BEFORE premiums/doubles) is below the weekly guarantee. Substitutes get NO guarantee. (Literal rule: "base service pay is below weekly_guarantee".)
6. **substitute_adjustment** (when applicable): the **electronic-substitute treatment**. For a musician who is `electronic==true AND substitute==true`, the 25% electronic premium is reported here as `substitute_adjustment` (it is NOT placed in the `premium` category). Non-electronic substitutes have `substitute_adjustment = 0`; the field is included only when a substitute (and especially an electronic substitute) is present. Substitutes otherwise still receive principal/lead/quartet premiums in the `premium` category and doubles in `doubles`.
   - **Decision point / uncertainty:** this is the least-certain field. The "electronic substitute treatment" hints that the electronic premium for elec+sub musicians is split out. Alternative readings: (a) substitute_adjustment is always 0/omitted; (b) it is the forfeited guarantee (negative). The electronic-premium-split reading is adopted because it is the only one that yields a nonzero, rate-book-derived value consistent with the "electronic substitute treatment" hint. Re-examine against the specific test production's roster.

### musician total
`total` = base + premium + doubles + vacation + guarantee_adjustment + substitute_adjustment. `categories` = object of **nonzero** category → 2dp amount.

### category_totals
Sum each category across all musicians. Include `substitute_adjustment` only when nonzero (applicable). Omit zero-valued categories (the template marks some "when applicable").

### service_counts
Object mapping each service type present in the schedule to its integer count (e.g. Performance 4, Audit 1, Rehearsal 2, 1hr Sound Check 1). Omit zero-count types.

### conflict_flags (sorted alphabetically; enum)
- `REHEARSAL_EARLY_START` — any rehearsal with `start_time < "09:00"`.
- `REHEARSAL_LATE_END` — any rehearsal with `end_time > "18:30"`.
- `SERVICE_OVER_TIME_LIMIT` — any service with `duration_hours > service_time_limits[type]` (strictly greater; equal-to-limit does NOT flag).
- `SOUND_CHECK_DURATION_MISMATCH` — a sound-check service whose `service_type` nominal hours (1.0 for "1hr Sound Check", 2.0 for "2hr Sound Check") differ from `duration_hours`.
- Sort the resulting flag list alphabetically.

### top_paid_musician_id
Musician with the highest `total`. Ties → lowest `musician_id` (ascending).

### Output ordering
`per_musician` ordered by `musician_id` ascending. `conflict_flags` sorted alphabetically. Currency 2dp.

### Worked example (PROD-HAMILTON-26)
- service_counts: `{"Rehearsal":2, "1hr Sound Check":1, "Performance":4, "Audit":1}`.
- category_totals: performance `5205.00`, audit `520.50`, rehearsal `2467.50`, sound_check `160.00`, premium `1318.44`, doubles `1405.10`, vacation `378.00`, guarantee_adjustment `1276.25`, substitute_adjustment `325.31`.
- weekly_total `13056.11`.
- conflict_flags: `["REHEARSAL_EARLY_START","SERVICE_OVER_TIME_LIMIT"]` (S01 rehearsal starts 08:45 < 09:00; S07 rehearsal 5.5h > 5.0h limit. No late end, no sound-check mismatch — S02 1hr Sound Check duration 1.0 matches.)
- per_musician (totals): M-H26-01 Avery `1951.88` (sub+elec; performance 1041.00, audit 260.25, doubles 325.31, substitute_adjustment 325.31), M-H26-02 Mira `2693.73`, M-H26-03 Jon `3010.41`, M-H26-04 Nadia `2406.94`, M-H26-05 Theo `2993.14`.
- top_paid_musician_id `M-H26-03` (Jon Reyes, 3010.41).
- Note on HAMILTON: every regular musician's base service pay < 2082, so all four regulars receive a guarantee_adjustment; the substitute (Avery) receives none.

---

## 4. Family: Regional dashboard (train_004 — `REGIONAL_VIEW`)

### Inputs
`request_memo`: `target_region_id`, `requested_comparison_years` = [2024, 2025].

### Step-by-step SOP
1. Derive the region's branch list from `/api/finance/branches` (canonical) — ascending sorted.
2. For each year, sum across the region's branches and across that year's 12 periods (FY2024 = M1..M12; FY2025 = M13..M24):
   - `revenue` = Σ revenue accounts; `sga` = Σ sga accounts; `allocations` = Σ allocations accounts; `ebitda` = revenue − cogs − sga − allocations (cogs summed the same way even though it is not a displayed field).
   - Worked (REG-WEST): FY2024 revenue `10453506.76`, sga `3763931.94`, allocations `354160.21`, ebitda `2310369.33`. FY2025 revenue `11139674.79`, sga `3935915.21`, allocations `376735.89`, ebitda `2515012.15` (= Σ of the three branches' FY2025 ebitda, matching branch-close region_context).
3. FY2025-only extra fields:
   - `ebitda_margin` = fy2025 ebitda / fy2025 revenue, 4dp → `0.2258`.
   - `sales_per_labor_headcount` = fy2025 revenue / Σ(labor_headcount over region, M13..M24), currency 2dp → `24809.97` (region labor_hc = 449).
4. `revenue_growth_pct` = (fy2025 revenue − fy2024 revenue) / fy2024 revenue, 4dp → `0.0656`.
5. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch in the region with max/min FY2025 ebitda. Worked: top `BR-005`, bottom `BR-006`.
6. `region_reconciliation_variance` (currency). **Decision point — meaning is not fully pinned by the template.** Adopted primary reading: the year-over-year ebitda dollar variance for the region = fy2025_ebitda − fy2024_ebitda → `204642.82`. Plausible alternatives to consider if a test task's wording points otherwise: (a) revenue YoY dollar variance `686168.03`; (b) the COGS "plug" that reconciles (revenue − sga − allocations) down to ebitda `4312011.54`; (c) branch-sum vs region-total, which is 0 here (data is internally consistent — no stale region tags). Prefer the ebitda-YoY reading; re-evaluate from the task's `management_focus` if it singles out revenue or "tie-out".
7. Output keys: `region_id`, `branch_ids`, `fy2024`, `fy2025`, `revenue_growth_pct`, `top_ebitda_branch_id`, `bottom_ebitda_branch_id`, `region_reconciliation_variance`.

---

## 5. Family: Compensation forecast (train_005 — `COMP_FORECAST`)

### Inputs
`request_memo`: `ensemble_id`, `scenario_id`, `forecast_years` = [current, year_plus_1, year_plus_2].

### Scenario driver structure (CONFIRMED)
Each scenario (e.g. `case_maple_board`, `case_redwood_baseline`, `case_cedar_negotiation`, `case_oak_sensitivity`) has `year_plus_1` and `year_plus_2`, each with:
- `mws_growth` — fractional growth applied to MWS.
- `overscale_growth` — fractional growth applied to each employee's `overscale_weekly`.
- `seniority_growth` — fractional growth applied to the seniority band weekly amount.
- `title_pct_multiplier` — multiplier applied to the title premium percentage.

### Core rules (CONFIRMED)
- **Cumulative / compound growth across forecast years.** year_plus_1 applies its drivers to current; year_plus_2 applies its drivers ON TOP of year_plus_1.
  - `MWS_y1 = MWS × (1 + y1.mws_growth)`; `MWS_y2 = MWS_y1 × (1 + y2.mws_growth)`.
  - `overscale_mult_y1 = (1 + y1.overscale_growth)`; `overscale_mult_y2 = overscale_mult_y1 × (1 + y2.overscale_growth)`.
  - `seniority_mult_y1 = (1 + y1.seniority_growth)`; `seniority_mult_y2 = seniority_mult_y1 × (1 + y2.seniority_growth)`.
  - `title_mult_y2 = y1.title_pct_multiplier × y2.title_pct_multiplier` (multiplicative; for scenarios where one year is e.g. 0.98, the reduction compounds).
- **Advance years of service** before assigning seniority bands: year_plus_1 uses `years_of_service + 1`; year_plus_2 uses `years_of_service + 2`. (This can move an employee up a band → large seniority growth — the dominant growth driver.)
- **combined_overscale_includes_title persists**: such employees still get NO separate Titled Position Premium in any forecast year; their (grown) overscale_weekly already bundles it.
- **Partial quarters persist**: use the same `weeks_by_quarter` for all forecast years (do NOT normalize partial quarters to 13).
- Title premium in a forecast year = `title_pct × effective_title_mult × MWS_thatYear × weeks` (the premium grows with MWS).
- Seniority in a forecast year = `band_amount(years + advance) × seniority_mult_thatYear × weeks`.
- Overscale in a forecast year = `overscale_weekly × overscale_mult_thatYear × weeks`.

### Output fields
- `annual_totals`: `current` (current-year total), `year_plus_1`, `year_plus_2` — each = Σ all pay across all employees & quarters for that year.
- `growth_rates`: `year_plus_1_vs_current` = (y1 − current)/current; `year_plus_2_vs_year_plus_1` = (y2 − y1)/y1. Both 4dp.
- `year_plus_2_quarter_totals`: Q1..Q4 for year_plus_2.
- `year_plus_2_pay_type_totals`: the four pay types for year_plus_2.
- `largest_growth_pay_type`: pay type with the largest **growth rate** from current → year_plus_2 (enum). (Alternative: largest absolute dollar growth — would usually be Minimum Weekly Scale. Prefer rate-based; "growth" mirrors the rate-based `growth_rates` field.)
- `combined_overscale_employee_count` & `partial_quarter_employee_count`: same definitions as the current-year family (roster attributes, unchanged by forecasting).

### Worked example (ENS-MAPLE, scenario `case_maple_board`)
Drivers: y1 {mws 0.035, overscale 0.012, seniority 0.018, title_mult 1.0}; y2 {mws 0.033, overscale 0.014, seniority 0.020, title_mult 1.0}.
- annual_totals: current `4232653.60`, year_plus_1 `4390313.79`, year_plus_2 `4545741.02`.
- growth_rates: year_plus_1_vs_current `0.0372`, year_plus_2_vs_year_plus_1 `0.0354`.
- year_plus_2_quarter_totals: Q1 `1129891.58`, Q2 `1138616.48`, Q3 `1138616.48`, Q4 `1138616.48` (Q1 lower because ENS-MAPLE-005 has Q1=10 weeks — partial quarter persists).
- year_plus_2_pay_type_totals: Minimum Weekly Scale `3914775.18`, Titled Position Premium `320833.74`, Seniority `190829.80`, Overscale `119302.29`.
- largest_growth_pay_type `Seniority` (rate ≈ 0.2331 current→year_plus_2, driven by both the seniority_growth multiplier and band advancement from +2 years; MWS ≈ 0.0692, Title ≈ 0.0692, Overscale ≈ 0.0262).
- combined_overscale_employee_count `4`; partial_quarter_employee_count `1`.
- Sanity: this ensemble has 4 `combined_overscale_includes_title=true` employees, so 4 employees contribute 0 to "Titled Position Premium" (their overscale covers it).

---

## 6. Common misjudgments & exclusion rules (DO / DON'T)

- **DON'T** sum `operating` accounts (orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog) into revenue/cogs/sga/ebitda. They are `metric_type: count`. Use active_customers / labor_headcount only as DENOMINATORS for ARPU and sales-per-labor-headcount.
- **DON'T** compute regional ebitda as `revenue − sga − allocations` (forgetting COGS). EBITDA always subtracts COGS even when the cogs field is hidden in the regional view.
- **DO** use each employee's own `weeks_by_quarter`, not the flat `quarter_weeks: 13`, for compensation totals — partial-quarter employees materially lower the affected quarter.
- **DO** suppress the Titled Position Premium when `combined_overscale_includes_title == true` (both current-year and forecast).
- **DO** advance years of service (+1, +2) in the forecast before picking the seniority band — this is the single biggest driver of seniority growth.
- **DO** apply scenario drivers cumulatively (compound) across year_plus_1 → year_plus_2.
- **DON'T** cap rehearsal pay at the 5.0h time limit. Pay the actual call (floored at 3h); the >5.0h breach only raises a `SERVICE_OVER_TIME_LIMIT` flag.
- **DON'T** give substitutes the weekly guarantee (only "guaranteed regular players" = non-substitutes get it). All observed substitutes also have `vacation_eligible=false`.
- **DO** use `>=`-style strictly-greater for the over-time flag: equal-to-limit does NOT flag; only `duration_hours > limit` does.
- **DO** rank descending (rank 1 = highest/best) for all `*_rank_desc` fields.
- **DO** derive region membership from `/api/finance/branches` and ignore stale memo notes claiming a different region for a branch.
- **DO** round currency to 2dp and decimal-percent/ratio to 4dp, per each field's `field_types` label.
- **DO** sort `conflict_flags` alphabetically and `per_musician` by `musician_id`.

---

## 7. Quick numeric reference (confirmed from live env)

**Compensation rate book** — MWS 2520.0; seniority weekly [0→0, 5→48, 10→82, 15→126, 20→170, 25→215]; title pct {Concertmaster 0.22, Principal 0.20, Section Lead 0.15, Assistant/Associate Principal 0.10}; current_year 2026; quarter_weeks 13/13/13/13 (overridden by roster).

**Payroll rate book** — Performance/Audit 260.25; Rehearsal 58.75/hr (3hr min); 1hr Sound Check 80.00; 2hr Sound Check 142.50. Limits 3/3/5/1/2 hrs. Premiums: concertmaster 20%, principal_or_lead 15%, quartet 15%, electronic 25%, first_double 25%, additional_double 10%, vacation 4%. weekly_guarantee 2082.0. Rehearsal window 09:00–18:30.

**Finance** — 12 branches, 4 regions (North: BR-001/002/003; West: BR-004/005/006; East: BR-007/008/011; South: BR-009/010/012). M1–M12 = FY2024, M13–M24 = FY2025. IS = revenue − cogs(sga,alloc) → ebitda. ARPU ÷ active_customers; sales/labor ÷ labor_headcount.

**Scenarios** — `case_cedar_negotiation`, `case_maple_board`, `case_oak_sensitivity`, `case_redwood_baseline`. Each has year_plus_1/year_plus_2 with `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.

---

## 8. Open decision points (re-evaluate per test task wording)
1. **`sales_growth_rank_desc` period** — annual (FY25 vs FY24) preferred; MoM (M24 vs M23) is the alternative. Worked annual: BR-004 rank 2, top BR-002. Worked MoM: BR-004 rank 11, top BR-002.
2. **`region_reconciliation_variance`** — ebitda YoY (204642.82) preferred; alternatives revenue-YoY (686168.03) or COGS plug (4312011.54).
3. **`largest_growth_pay_type`** — growth-rate based (Seniority) preferred; absolute-dollar alternative (Minimum Weekly Scale).
4. **`substitute_adjustment`** — electronic-premium-split for elec+sub musicians preferred; the field is the least-certain in the payroll model.
5. **`current_month`/`prior_month` label format** — M-code (`M24`) preferred; `Dec 2025` style acceptable.
6. **ARPU / sales_per_labor_headcount precision** — 2dp (per `currency` label) preferred; 4dp is the alternative if the evaluator treats them as ratios.
