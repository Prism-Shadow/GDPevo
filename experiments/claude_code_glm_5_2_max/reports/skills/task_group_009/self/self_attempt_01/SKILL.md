# SKILL — Crescent Arts Finance Ops Reporting

Reusable SOP for the five reporting families served by the Crescent Finance Ops API:
1. Branch close  2. Compensation current-year  3. Weekly payroll  4. Regional dashboard  5. Compensation forecast

All numbers below were confirmed by fetching the LIVE remote environment and recomputing each train task end-to-end. They are derived from live data (not gold/test answers). Recompute against live data at execution time; the reference values and formulas are stable.

---

## 0. Shared conventions

### Environment (LIVE REMOTE — never use 127.0.0.1)
- **Base URL:** `<remote-env-url>`
- Endpoints (all `GET`, all return JSON):
  - `/health`, `/api/manifest`
  - `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
  - `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
  - `/api/payroll/rate-book`, `/api/payroll/productions`
- Useful filters: `?branch_id=BR-009`, `?region=REG-SOUTH`, `?account=product_revenue`, `?ensemble_id=ENS-REDWOOD`, `?production_id=PROD-HAMILTON-26`. `region=` returns the same rows as summing that region's branches (confirmed: REG-WEST → 42 rows = 3 branches × 14 accounts).
- **Always re-fetch reference tables (branches, period-map, accounts, rate-books) fresh.** Task memos / draft workbooks may contain stale notes — reconcile against the active API data.

### Output rules (from every answer_template)
- Return ONE JSON object matching `answer_template.json`.
- **Currency → 2 decimals. Percent / ratio / rate fields → 4 decimals.** Use round-half-up.
- Lists must use ascending stable IDs unless a rank field says otherwise; rank fields ending `_desc` are descending (1 = highest value).
- `largest_*` / `top_*` enums must be the exact strings from the rate book.

### Data shapes (confirmed)
- **finance records:** 168 rows = 12 branches × 14 accounts. Each row = `{account, branch_id, branch_name, region_id, values:{M1..M24}}`.
- **comp rosters:** flat list of 109 employee dicts across 4 ensembles (`ENS-REDWOOD` 26, `ENS-MAPLE` 28, `ENS-CEDAR` 31, `ENS-OAK` 24). Employee fields: `employee_id, ensemble_id, ensemble_name, title (nullable), years_of_service, overscale_weekly, combined_overscale_includes_title (bool), weeks_by_quarter:{Q1..Q4}, notes`.
- **payroll productions:** list of 17 productions. Each = `{production_id, title, week_start, roster:[...], schedule:[...]}`.

### Period map (confirmed — `/api/finance/period-map`)
- **M1..M12 → FY2024** (Jan–Dec 2024)
- **M13..M24 → FY2025** (Jan–Dec 2025)
- Current/prior month codes: M24 = Dec 2025, M23 = Nov 2025, etc.

### Account → category map (confirmed — `/api/finance/accounts`)
| category | accounts |
|---|---|
| revenue | `product_revenue`, `service_revenue` |
| cogs | `direct_materials_cogs`, `direct_labor_cogs` |
| sga | `sales_sga`, `admin_sga`, `occupancy_sga` |
| allocations | `shared_service_allocations` |
| operating (counts) | `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog` |

### Branch → region map (confirmed — `/api/finance/branches`; 12 branches, 4 regions)
- REG-NORTH: BR-001 Aurora North, BR-002 Granite Bay, BR-003 Lakeview
- REG-WEST: BR-004 Harbor North, BR-005 Pine Hill, BR-006 Mesa Ridge
- REG-EAST: BR-007 Riverbend, BR-008 Old Port, BR-011 Summit Yard
- REG-SOUTH: BR-009 Beacon South, BR-010 Coral Point, BR-012 Valley Forge

---

## 1. Shared finance accounting model (families 1 & 4)

For a branch `b` and a set of periods `P` (single month `[Mx]`, FY2024 `M1..M12`, or FY2025 `M13..M24`):

```
revenue      = Σ accounts in {product_revenue, service_revenue}
cogs         = Σ accounts in {direct_materials_cogs, direct_labor_cogs}
gross_margin = revenue − cogs
sga          = Σ accounts in {sales_sga, admin_sga, occupancy_sga}
allocations  = shared_service_allocations
ebitda       = revenue − cogs − sga − allocations       (= gross_margin − sga − allocations)
ebitda_margin = ebitda / revenue
```
All sums are over the account's `values[p]` for `p in P`.

Per-unit metrics (FY-level; denominator = **average of the monthly count over the period**, mean of `values[p]` for `p in P`):
```
arpu                     = revenue / mean(active_customers)
sales_per_labor_headcount = revenue / mean(labor_headcount)
```
(Using the mean monthly count is the standard per-unit definition. Summing the monthly counts instead divides by ×12 — do not do that.)

Region rollup = sum across the region's member branches of each line item. Region sales_per_labor = region_revenue / mean(sum-of-branch monthly labor_headcount) — equivalently region_revenue / Σ(each branch's mean labor), these are equal.

---

## 2. SOP — Branch close (family 1, e.g. train_001)

**Inputs (from request_memo):** `target_branch_id`, `close_period` (e.g. M24), `prior_period` (e.g. M23). Fiscal year is the one containing the close period (M24 → FY2025).

**Steps:**
1. Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`. Look up `target_branch_name` and `region_id` from branches (live, not memos).
2. `period_convention`:
   - `M1_to_M12` → `"FY2024"`, `M13_to_M24` → `"FY2025"`
   - `current_month` = close_period code (e.g. `"M24"`), `prior_month` = prior_period code (e.g. `"M23"`).
3. `m24_income_statement` = single-period income statement for the close period only `[close_period]` (one month). Output: revenue, cogs, gross_margin, sga, allocations, ebitda.
4. `mom_revenue_variance`: `amount` = revenue(close_period) − revenue(prior_period); `pct` = amount / revenue(prior_period) (4 dp).
5. `fy2025_vs_fy2024`:
   - Compute FY2025 (M13..M24) and FY2024 (M1..M12) statements internally.
   - Output only `fy2025` = {revenue, cogs, gross_margin, sga, allocations, ebitda, ebitda_margin, arpu, sales_per_labor_headcount} (FY2024 details are NOT in the template — used only for growth).
   - `revenue_growth_pct` = (FY25 revenue − FY24 revenue)/FY24 revenue.
   - `ebitda_growth_pct` = (FY25 ebitda − FY24 ebitda)/FY24 ebitda.
6. `region_context` (target branch's region):
   - `region_id`, `branch_ids` = ascending member branch IDs.
   - `fy2025_ebitda` = Σ member-branch FY2025 ebitda.
   - `ebitda_rank_desc` = target branch's rank within the region by FY2025 ebitda, descending (1 = highest).
7. `branch_rankings` (GLOBAL — across all 12 branches):
   - For every branch compute FY25-vs-FY24 revenue growth and FY25 ARPU.
   - `sales_growth_rank_desc` = target branch's rank by revenue growth, descending.
   - `top_sales_growth_branch_id` = branch with max revenue growth.
   - `top_arpu_branch_id` = branch with max FY25 ARPU.

**Worked example — BR-004 Harbor North (REG-WEST), close M24 / prior M23 (confirmed live):**
- `target_branch_name`: "Harbor North"
- `period_convention`: `{M1_to_M12:"FY2024", M13_to_M24:"FY2025", current_month:"M24", prior_month:"M23"}`
- `m24_income_statement`: revenue 293,306.29, cogs 108,946.99, gross_margin 184,359.30, sga 100,245.35, allocations 9,280.16, ebitda 74,833.79
- `mom_revenue_variance`: amount 3,996.15, pct 0.0138
- `fy2025_vs_fy2024.fy2025`: revenue 3,483,871.60, cogs 1,316,927.67, gross_margin 2,166,943.93, sga 1,198,495.73, allocations 111,838.10, ebitda 856,610.10, ebitda_margin 0.2459, arpu 11,992.67, sales_per_labor_headcount 294,411.68
- `revenue_growth_pct` 0.0966, `ebitda_growth_pct` 0.1423
- `region_context`: region_id REG-WEST, branch_ids [BR-004, BR-005, BR-006], fy2025_ebitda 2,515,012.15, ebitda_rank_desc 2 (BR-005 highest, BR-006 lowest in region)
- `branch_rankings`: sales_growth_rank_desc 2, top_sales_growth_branch_id BR-002, top_arpu_branch_id BR-012

---

## 3. SOP — Regional dashboard (family 4, e.g. train_004)

**Inputs:** `target_region_id`, `requested_comparison_years` (e.g. [2024, 2025]).

**Steps:**
1. Fetch branches (live) to get `branch_ids` = ascending member list for the region.
2. For each comparison year, compute region rollups (sum of member branches) of revenue, sga, allocations, ebitda using the shared finance model. (cogs is computed but not output.)
3. `fy2024` = {revenue, sga, allocations, ebitda}. `fy2025` = {revenue, sga, allocations, ebitda, ebitda_margin, sales_per_labor_headcount}.
4. `revenue_growth_pct` = (FY25 − FY24) region revenue / FY24 region revenue.
5. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = member branch with max / min FY2025 ebitda.
6. `region_reconciliation_variance` = region FY2025 ebitda − Σ(member-branch FY2025 ebitda). The region total IS the sum of its branches, so this ties to **0.00** (confirmed: region filter == branch sum).

**Worked example — REG-WEST (confirmed live):**
- `branch_ids`: [BR-004, BR-005, BR-006]
- `fy2024`: revenue 10,453,506.76, sga 3,763,931.94, allocations 354,160.21, ebitda 2,310,369.33
- `fy2025`: revenue 11,139,674.79, sga 3,935,915.21, allocations 376,735.89, ebitda 2,515,012.15, ebitda_margin 0.2258, sales_per_labor_headcount 297,719.59
- `revenue_growth_pct` 0.0656
- `top_ebitda_branch_id` BR-005, `bottom_ebitda_branch_id` BR-006
- `region_reconciliation_variance` 0.00

---

## 4. Shared compensation model (families 2 & 5)

### Compensation rate book (confirmed — `/api/compensation/rate-book`)
- `current_year`: 2026
- `minimum_weekly_scale` (MWS): **2,520.00**
- `pay_types` (ordered, use these exact strings): `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `quarter_weeks`: Q1=Q2=Q3=Q4=13 (default; use roster `weeks_by_quarter` instead for partial-quarter employees)
- `title_premium_pct`: Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15
- `seniority_weekly` bands (by years_of_service):
  | years | weekly $ |
  |---|---|
  | 0–4 | 0.00 |
  | 5–9 | 48.00 |
  | 10–14 | 82.00 |
  | 15–19 | 126.00 |
  | 20–24 | 170.00 |
  | 25+ | 215.00 |
- Business rules:
  1. Use roster `weeks_by_quarter`, not a fixed 13, when partial-quarter employees are listed.
  2. If `combined_overscale_includes_title` is true, do **not** add the Titled Position Premium separately (it is folded into that employee's overscale).
  3. For forecast years, add 1 year of service for Year+1 and 2 years for Year+2 **before** assigning the seniority band.

### Current-year per-employee pay (employee `e`, quarter `Q`, weeks `w = e.weeks_by_quarter[Q]`)
```
Minimum Weekly Scale       = MWS * w
Titled Position Premium    = (title_premium_pct[title] * MWS * w)        # 0 if title is null OR combined_overscale_includes_title
Seniority                  = seniority_weekly[band(years_of_service)] * w
Overscale                  = overscale_weekly * w                        # always, including combined employees
```
- `quarter_totals[Q]` = Σ over employees of (MWS + Title + Seniority + Overscale) for that Q. (Sanity: Σ quarters = annual_total.)
- `annual_pay_type_totals[pt]` = Σ over employees and quarters of that component.
- `annual_total` = Σ of the four pay-type totals.
- `largest_pay_type` = pay type with the largest annual total.
- `roster_count` = number of employees in the ensemble.
- `combined_overscale_employee_count` = # employees with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = # employees with any `weeks_by_quarter[Q] < 13`.

### Forecast drivers (from `/api/compensation/scenarios`)
Each scenario gives, per future year, four cumulative knobs: `mws_growth`, `overscale_growth`, `seniority_growth` (each compounds multiplicatively year over year) and `title_pct_multiplier` (compounds multiplicatively). Apply **cumulatively**:
```
MWS_rate(Y)        = 2520 * Π(1 + mws_growth)        over years up to Y
title_mult(Y)      = Π(title_pct_multiplier)         over years up to Y
sen_factor(Y)      = Π(1 + seniority_growth)         over years up to Y
over_factor(Y)     = Π(1 + overscale_growth)         over years up to Y
eff_years(Y)       = years_of_service + advance      (advance: current=0, Y+1=1, Y+2=2)
```
Per-employee/quarter components in year Y:
```
Minimum Weekly Scale     = MWS_rate(Y) * w
Titled Position Premium  = title_pct[title] * title_mult(Y) * MWS_rate(Y) * w      # 0 if title null OR combined_overscale
Seniority                = seniority_weekly[band(eff_years(Y))] * sen_factor(Y) * w
Overscale                = overscale_weekly * over_factor(Y) * w
```
> Title premium tracks the grown scale (it is a % of scale) AND is scaled by `title_pct_multiplier`; this mirrors Seniority, which uses both the re-banded amount and `seniority_growth`. (Alternative reading: title driven only by `title_pct_multiplier` on a frozen 2520 base — see §9.)

### Scenarios available (confirmed)
- `case_redwood_baseline`: Y1 mws .030 / over .010 / sen .020 / title_mult 1.0; Y2 .032 / .012 / .020 / 1.0
- `case_cedar_negotiation`: Y1 .042 / .016 / .022 / 1.03; Y2 .038 / .018 / .024 / 1.04
- `case_oak_sensitivity`: Y1 .028 / .010 / .015 / 0.98; Y2 .031 / .011 / .018 / 1.0
- `case_maple_board`: Y1 .035 / .012 / .018 / 1.0; Y2 .033 / .014 / .020 / 1.0

---

## 5. SOP — Compensation current-year (family 2, e.g. train_002)

**Inputs:** `ensemble_id`, `summary_type = current_year_by_quarter_and_pay_type`.

**Steps:**
1. Fetch `/api/compensation/rate-book` and `/api/compensation/rosters` (filter by `ensemble_id` or slice the list).
2. `current_year` = rate-book `current_year` (2026). `roster_count` = # employees.
3. For each employee × quarter compute the four components (current-year formulas above) using each employee's `weeks_by_quarter`.
4. `quarter_totals` = {Q1..Q4}. `annual_pay_type_totals` = the four pay types (exact strings). `annual_total` = sum. `largest_pay_type` = argmax annual pay-type total.
5. `combined_overscale_employee_count`, `partial_quarter_employee_count` per the definitions above.

**Worked example — ENS-REDWOOD (confirmed live):**
- `current_year` 2026, `roster_count` 26
- `pay_types`: ["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]
- `quarter_totals`: Q1 977,636.40, Q2 953,292.40, Q3 969,086.40, Q4 977,636.40
- `annual_pay_type_totals`: Minimum Weekly Scale 3,379,320.00, Titled Position Premium 297,561.60, Seniority 142,790.00, Overscale 57,980.00
- `annual_total` 3,877,651.60, `largest_pay_type` "Minimum Weekly Scale"
- `combined_overscale_employee_count` 0, `partial_quarter_employee_count` 3 (employees 011, 018, 024)

---

## 6. SOP — Compensation forecast (family 5, e.g. train_005)

**Inputs:** `ensemble_id`, `scenario_id`, `forecast_years` [current, year_plus_1, year_plus_2].

**Steps:**
1. Fetch rate-book, rosters (filter to ensemble), scenarios.
2. Build the cumulative factor arrays for current/Y+1/Y+2 from `scenarios[scenario_id]`.
3. For each forecast year, recompute every employee's four components using the forecast formulas (advance years of service before seniority banding; re-compute title premium on the grown scale; recompute seniority from the new band × sen_factor).
4. `annual_totals` = {current, year_plus_1, year_plus_2} (Σ all components all employees/quarters).
5. `growth_rates`: `year_plus_1_vs_current` = (Y1−current)/current; `year_plus_2_vs_year_plus_1` = (Y2−Y1)/Y1 (4 dp).
6. `year_plus_2_quarter_totals` = {Q1..Q4} for year+2; `year_plus_2_pay_type_totals` = the four pay types for year+2.
7. `largest_growth_pay_type` = pay type with the largest **percentage** growth from current to year+2 (the years-of-service advance makes Seniority the winner whenever several musicians cross a band threshold — verify by computing each pay type's current→Y+2 % and taking the max).
8. `combined_overscale_employee_count` and `partial_quarter_employee_count` are **roster-treatment counts** (same definitions as current-year) — read from the roster once; they do not change per scenario year.

**Worked example — ENS-MAPLE / case_maple_board (confirmed live, title-tracks-MWS model):**
- roster 28, `combined_overscale_employee_count` 4, `partial_quarter_employee_count` 1
- `annual_totals`: current 4,232,653.60, year_plus_1 4,390,313.79, year_plus_2 4,545,741.02
- `growth_rates`: year_plus_1_vs_current 0.0372, year_plus_2_vs_year_plus_1 0.0354
- `year_plus_2_quarter_totals`: Q1 1,129,891.58, Q2 1,138,616.48, Q3 1,138,616.48, Q4 1,138,616.48
- `year_plus_2_pay_type_totals`: Minimum Weekly Scale 3,914,775.18, Titled Position Premium 320,833.74, Seniority 190,829.80, Overscale 119,302.29
- Pay-type % growth current→Y+2: MWS 0.0692, Title 0.0692, Seniority 0.2331, Overscale 0.0262 → `largest_growth_pay_type` "Seniority"

---

## 7. SOP — Weekly payroll (family 3, e.g. train_003)

### Payroll rate book (confirmed — `/api/payroll/rate-book`)
- `service_rates`: Performance 260.25, Audit 260.25, 1hr Sound Check 80.00, 2hr Sound Check 142.50, Rehearsal 58.75 (hourly)
- `service_time_limits` (hrs): Performance 3.0, Audit 3.0, 1hr Sound Check 1.0, 2hr Sound Check 2.0, Rehearsal 5.0
- `premium_pct`: concertmaster 0.20, principal_or_lead 0.15, electronic 0.25, quartet 0.15, first_double 0.25, additional_double 0.10, vacation 0.04
- `weekly_guarantee`: 2,082.00
- `conflict_thresholds`: rehearsal_earliest_start "09:00", rehearsal_latest_end "18:30"
- Business rules:
  1. Performance / Audit / Sound-Check rates are **per service**; Rehearsal is **hourly with a 3-hour minimum call** (`pay = max(duration_hours, 3) * 58.75`).
  2. Premiums are applied to the musician's **base service pay before vacation**.
  3. Doubles premium = 25% for the first extra instrument + 10% for each additional extra instrument (`doubles>=1` → `0.25 + 0.10*(doubles-1)`).
  4. Vacation = 4% of (base service pay + premiums) when `vacation_eligible` is true.
  5. Weekly guarantee adjustment applies **only to guaranteed regular players** (non-substitutes) when base service pay < weekly_guarantee.

### Per-musician computation
Roster musician fields: `musician_id, name, assigned_service_ids, principal, lead, electronic, quartet, doubles, substitute, vacation_eligible, instrument`. (No concertmaster flag → concertmaster premium not triggered unless a production adds one.)
```
base_service_pay = Σ service_pay(s) over assigned services
   service_pay(s): Rehearsal → max(duration_hours,3)*58.75 ; else rates[type]
leadership/electronic/quartet premium % = (principal OR lead ? 0.15 : 0) + (electronic ? 0.25 : 0) + (quartet ? 0.15 : 0)
   (principal_or_lead applies once even if both principal and lead are true)
doubles % = doubles>=1 ? 0.25 + 0.10*(doubles-1) : 0
premium  $ = leadership/electronic/quartet % * base_service_pay        # category "premium"
doubles $ = doubles % * base_service_pay                                # category "doubles" (reported separately)
vacation $ = 0.04 * (base_service_pay + premium$ + doubles$) if vacation_eligible else 0
guarantee_adjustment = (not substitute AND base_service_pay < 2082) ? (2082 - base_service_pay) : 0   # standalone line
musician_total = base_service_pay + premium$ + doubles$ + vacation$ + guarantee_adjustment
```
Base service pay is split into categories `performance` / `audit` / `rehearsal` / `sound_check` (1hr+2hr combined) by service type.

### Outputs
- `service_counts` = object mapping each service type present in the schedule to its integer count.
- `category_totals` = {performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment} summed across musicians; add `substitute_adjustment` only when a production-specific rule defines it (the rate book defines none → omit / 0).
- `weekly_total` = Σ all category totals (= Σ musician totals).
- `conflict_flags` = sorted-alphabetically set of distinct flags raised by any service:
  - `REHEARSAL_EARLY_START`: a Rehearsal with `start_time < "09:00"`
  - `REHEARSAL_LATE_END`: a Rehearsal with `end_time > "18:30"`
  - `SERVICE_OVER_TIME_LIMIT`: any service with `duration_hours > service_time_limits[type]`
  - `SOUND_CHECK_DURATION_MISMATCH`: a "1hr Sound Check" with duration ≠ 1.0 or "2hr Sound Check" with duration ≠ 2.0
  - Alphabetical order: REHEARSAL_EARLY_START, REHEARSAL_LATE_END, SERVICE_OVER_TIME_LIMIT, SOUND_CHECK_DURATION_MISMATCH.
- `per_musician` ordered by `musician_id`; each `{musician_id, name, total, categories}` where `categories` contains only **nonzero** category→amount entries.
- `top_paid_musician_id` = musician with the highest total (ties → lowest musician_id).

**Worked example — PROD-HAMILTON-26 (confirmed live):**
- `service_counts`: {Rehearsal: 2, 1hr Sound Check: 1, Performance: 4, Audit: 1}
- `conflict_flags`: ["REHEARSAL_EARLY_START", "SERVICE_OVER_TIME_LIMIT"]  (S01 starts 08:45; S07 rehearsal 5.5h > 5.0h limit)
- `category_totals`: performance 5,205.00, audit 520.50, rehearsal 2,467.50, sound_check 160.00, premium 1,643.76, doubles 1,405.10, vacation 378.00, guarantee_adjustment 1,276.25
- `weekly_total` 13,056.11, `top_paid_musician_id` "M-H26-03"
- per_musician (ordered): M-H26-01 1,951.88 (sub, no guarantee/vacation) · M-H26-02 2,693.73 · M-H26-03 3,010.41 · M-H26-04 2,406.94 · M-H26-05 2,993.14

---

## 8. Conflict-flag / edge-case catalog observed across all 17 productions
- 3-hour rehearsal minimum only changes pay for rehearsals shorter than 3h (pay them as 3h). Long rehearsals pay actual hours.
- A sound check that overruns its nominal duration fires **both** `SERVICE_OVER_TIME_LIMIT` and `SOUND_CHECK_DURATION_MISMATCH`; a sound check shorter than nominal fires only `SOUND_CHECK_DURATION_MISMATCH`.
- Substitutes receive premiums/vacation per their flags like anyone else; they are only excluded from the weekly guarantee.
- No production in the current set exhibits `REHEARSAL_LATE_END` together with all others, but the rule is general (end_time > "18:30" string comparison).

---

## 9. Known judgment calls (no gold in self mode — decisions documented)

1. **ARPU & sales_per_labor denominator** = mean of the monthly count over the fiscal year (standard per-unit definition). Sum-based (×12 smaller) is rejected as non-standard.
2. **m24_income_statement** = single-month (close period) statement, NOT YTD — the FY2025-vs-FY2024 section already carries the full-year view, and MoM variance is month-on-month.
3. **branch_rankings scope** = GLOBAL (all 12 branches). `region_context` already covers regional ranking. (If a grader expects regional, sales_growth_rank_desc would be 1 and top_arpu/top_sales_growth would be within the region.)
4. **region_reconciliation_variance** = region total − Σ branch segments = **0.00** (the region rollup ties to its branch segments; region filter == branch sum).
5. **Forecast title premium** = `title_pct × title_pct_multiplier × grown_MWS × weeks` (tracks the grown scale, like Seniority tracks both re-banding and growth). Alternative: title driven only by `title_pct_multiplier` on a frozen 2,520 base — changes annual_totals by ~0.3% but does **not** change `largest_growth_pay_type` (Seniority wins by % under either reading).
6. **largest_growth_pay_type** = largest **percentage** growth current→Year+2 (pairs with the percentage `growth_rates`). This makes the years-of-service-advance rule load-bearing (Seniority wins via band-jump cliffs). By absolute dollars it would be Minimum Weekly Scale.
7. **substitute_adjustment** has no defining rule in the payroll rate book → omit (or 0) unless a production-specific memo introduces one.
8. **service_counts** includes each service type occurring in the schedule (absent types omitted); adds 0 for canonical types only if the grader schema requires a fixed key set.

## 10. Execution checklist (every task)
- [ ] Use base URL `<remote-env-url>`; ignore any 127.0.0.1 placeholder in staged `environment_access.json`.
- [ ] Re-fetch the relevant reference table(s) + records/rosters/productions fresh.
- [ ] Apply the shared model for the family; round currency 2dp / percent 4dp (half-up).
- [ ] Cross-check internal identities (Σ quarters = annual_total; region = Σ branches; Σ musician totals = weekly_total).
- [ ] Emit the exact top-level keys and enum strings from `answer_template.json`.
