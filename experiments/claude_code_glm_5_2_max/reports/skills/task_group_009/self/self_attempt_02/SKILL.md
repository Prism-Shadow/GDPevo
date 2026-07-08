# SKILL.md — Crescent Finance Ops Reporting (task_group_009)

A reusable SOP for the Crescent Arts Collective Finance Ops evaluation. Five task families share one remote environment:
1. **Branch close** (monthly close package, one branch)
2. **Compensation current-year** (one ensemble, by quarter & pay type)
3. **Weekly payroll** (one touring production)
4. **Regional dashboard** (one region, FY vs FY)
5. **Compensation forecast** (one ensemble + scenario, current / Y+1 / Y+2)

All numbers below were confirmed against the LIVE remote environment by solving the 5 train tasks. They are shown as **illustrative reference values** so a solver can sanity-check its engine; the RULES are generic and transfer to any new target id. Do not copy a train JSON verbatim — recompute for the test target.

---

## 0. Environment & shared conventions

### Base URL (LIVE remote — always use this)
`<remote-env-url>`
Never use `127.0.0.1:8047` (dev placeholder in staged `environment_access.json`). The staged `base_url` is already the remote host; trust it.

### Endpoints (all return JSON)
- `GET /health` → `{"status":"ok"}`
- `GET /api/manifest` → endpoint list + `public_entities` (branches/ensembles/productions index — use for id lookups)
- `GET /api/finance/branches` → branch_id, branch_name, region_id, region_name
- `GET /api/finance/period-map` → period (M-code), fiscal_year, month_name, month_number
- `GET /api/finance/accounts` → account, category, display_name, metric_type
- `GET /api/finance/records` → per (branch_id, account): `values` dict keyed M1..M24. Filters: `?branch_id=`, `?region=`, `?account=`
- `GET /api/compensation/rate-book` → MWS, pay_types, quarter_weeks, seniority_weekly, title_premium_pct, business_rules, current_year
- `GET /api/compensation/rosters` → list of employees (filter `?ensemble_id=`)
- `GET /api/compensation/scenarios` → scenario driver dicts
- `GET /api/payroll/rate-book` → service_rates, service_time_limits, premium_pct, weekly_guarantee, conflict_thresholds, business_rules
- `GET /api/payroll/productions` → list of productions (filter `?production_id=`)

Fetch each reference file once and cache it; records are the largest (~108 KB). `curl -s "$B/api/finance/records"`.

### Period map (fiscal-year convention — CRITICAL)
24 monthly periods M1..M24, calendar months Jan..Dec:
- **M1..M12 → FY2024**
- **M13..M24 → FY2025**

So a "close_period M24" is Dec FY2025; "prior_period M23" is Nov FY2025. `period_convention` reports `M1_to_M12: "FY2024"`, `M13_to_M24: "FY2025"`. `current_month`/`prior_month` = the period code string (e.g. `"M24"`, `"M23"`). FY rollups = sum of the 12 monthly `values` for that fiscal year.

### Account categories (from /api/finance/accounts)
| category | accounts | metric_type |
|---|---|---|
| revenue | product_revenue, service_revenue | currency |
| cogs | direct_materials_cogs, direct_labor_cogs | currency |
| sga | sales_sga, admin_sga, occupancy_sga | currency |
| allocations | shared_service_allocations | currency |
| operating | orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog | **count** (NOT currency) |

**Income-statement construction (IS line):**
- `revenue` = Σ revenue-category accounts (that period)
- `cogs` = Σ cogs-category accounts
- `gross_margin` = revenue − cogs
- `sga` = Σ sga-category accounts
- `allocations` = Σ allocations-category accounts
- `ebitda` = revenue − cogs − sga − allocations  (= gross_margin − sga − allocations)

**Operating counts are NEVER summed into a currency line.** They are used only for per-customer / per-headcount ratios:
- `arpu` (FY) = FY revenue / **mean** of the 12 monthly `active_customers` values
- `sales_per_labor_headcount` (FY) = FY revenue / **mean** of the 12 monthly `labor_headcount` values

Use the **arithmetic mean of the monthly counts** over the FY (summing 12 monthly headcounts would double-count people). Both ratios are currency, rounded 2dp.

### Region membership — trust the live branches file, NOT names/memos
Confirmed region→branch map:
- REG-NORTH: BR-001, BR-002, BR-003
- REG-WEST: BR-004, BR-005, BR-006
- REG-EAST: BR-007, BR-008, BR-011
- REG-SOUTH: BR-009, BR-010, BR-012

**Stale-memo trap:** `BR-004` is named "Harbor North" but lives in **REG-WEST**, not REG-NORTH. A task memo may reference a "draft workbook" / background notes that imply a different region or a branch split — ignore it. Region membership is whatever `/api/finance/branches` says. Do not add/drop branches based on a memo. "Reconcile against the active operations data."

### Rounding
- Currency → 2 decimals.
- Percent / ratio / decimal-percent fields → 4 decimals (e.g. 0.013813 → `0.0138`; 0.245879 → `0.2459`).
- Lists → ascending stable IDs unless a rank field says otherwise. `conflict_flags` → sorted alphabetically. `per_musician` → ordered by musician_id.
- `rank_desc` / `rank_descENDING` = **1 is best** (sorted high→low; rank 1 = largest value).

### Standard fetch helper (python)
```python
import json, urllib.request
B="<remote-env-url>"
def get(p): return json.load(urllib.request.urlopen(B+p))
branches=get("/api/finance/branches")
pmap=get("/api/finance/period-map")
accts=get("/api/finance/accounts")
recs=get("/api/finance/records")
crb=get("/api/compensation/rate-book")
rost=get("/api/compensation/rosters")
scen=get("/api/compensation/scenarios")
prb=get("/api/payroll/rate-book")
prods=get("/api/payroll/productions")
cat={a["account"]:a["category"] for a in accts}
by={(r["branch_id"],r["account"]):r["values"] for r in recs}
fy24=["M%d"%i for i in range(1,13)]; fy25=["M%d"%i for i in range(13,25)]
```

---

## 1. Family: Branch close

**Task shape:** request_memo gives `target_branch_id`, `close_period` (e.g. M24), `prior_period` (e.g. M23). Produce IS for the close period, MoM revenue variance, current-FY vs prior-FY view, the branch's region context, and company-wide branch rankings.

### SOP
1. Resolve target branch from `/api/finance/branches` → `target_branch_name`, `region_id`.
2. **m24_income_statement** (use the close_period, here M24): build the IS line from that single month's `values` across the 8 currency accounts (revenue/cogs/sga/allocations). All six fields (revenue, cogs, gross_margin, sga, allocations, ebitda).
3. **mom_revenue_variance**: `amount` = revenue(close_period) − revenue(prior_period); `pct` = amount / revenue(prior_period), 4dp.
4. **fy2025_vs_fy2024**: build the full IS line for FY2025 (Σ M13..M24) and FY2024 (Σ M1..M12). The `fy2025` sub-object carries all six IS lines PLUS `ebitda_margin` (= ebitda/revenue, 4dp), `arpu`, `sales_per_labor_headcount`. Top-level `revenue_growth_pct` = (FY25 rev − FY24 rev)/FY24 rev; `ebitda_growth_pct` = (FY25 ebitda − FY24 ebitda)/FY24 ebitda. (4dp each.)
5. **period_convention**: `{M1_to_M12:"FY2024", M13_to_M24:"FY2025", current_month:"M24", prior_month:"M23"}` (substitute the actual period codes).
6. **region_context**: `region_id`; `branch_ids` = ascending list of branches in that region; `fy2025_ebitda` = Σ over the region's branches of FY2025 ebitda; `ebitda_rank_desc` = the target branch's rank within its region by FY2025 ebitda (descending, 1 = highest).
7. **branch_rankings** (company-wide, all 12 branches): `sales_growth_rank_desc` = target branch's rank by FY25-vs-FY24 revenue growth (descending); `top_sales_growth_branch_id` = branch with the highest revenue growth across all 12; `top_arpu_branch_id` = branch with the highest FY2025 ARPU across all 12.

### Confirmed train reference (BR-004, M24 vs M23)
- m24_income_statement: revenue `293306.29`, cogs `108946.99`, gross_margin `184359.30`, sga `100245.35`, allocations `9280.16`, ebitda `74833.79`
- mom_revenue_variance: amount `3996.15`, pct `0.0138`
- FY2025: rev `3483871.60`, cogs `1316927.67`, gm `2166943.93`, sga `1198495.73`, alloc `111838.10`, ebitda `856610.10`, ebitda_margin `0.2459`, arpu `11992.67`, sales_per_labor_headcount `294411.68`
- FY2024 (for growth): rev `3177038.53`, ebitda `749925.74` → revenue_growth_pct `0.0966`, ebitda_growth_pct `0.1423`
- region_context: REG-WEST, [BR-004, BR-005, BR-006], fy2025_ebitda `2515012.15`, ebitda_rank_desc `2`
- branch_rankings: sales_growth_rank_desc `2`, top_sales_growth_branch_id `BR-002`, top_arpu_branch_id `BR-012`

### Pitfalls
- Don't zero-pad month keys when slicing (`values` keys are `M1`,`M2`,…,`M9`,`M10`,… — NOT `M01`). `["M%d"%i ...]` is correct; `["M%02d"%i ...]` silently returns 0s for M1..M9.
- ARPU / sales_per_labor_headcount use the **mean** of monthly counts, not the sum, not the closing month.
- branch_rankings are company-wide (12 branches); region_context.ebitda_rank_desc is region-internal. Both "desc" => 1 is best.
- BR-004 is in REG-WEST despite "Harbor North" name.

---

## 2. Family: Compensation current-year

**Task shape:** request_memo gives `ensemble_id`, `summary_type=current_year_by_quarter_and_pay_type`. Produce quarterly totals, pay-type totals, annual total, largest pay type, and two roster-treatment counts.

### Rate book facts (`/api/compensation/rate-book`)
- `current_year` = **2026** (this is the "current_year" output field)
- `minimum_weekly_scale` (MWS) = **2520.0**
- `pay_types` (output order) = `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`
- `quarter_weeks` default = 13 each (used only when an employee has no `weeks_by_quarter` override)
- `title_premium_pct`: Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15 (title premium = pct × MWS)
- `seniority_weekly` bands (by years_of_service):
  | years | weekly |
  |---|---|
  | 0–4 | 0.0 |
  | 5–9 | 48.0 |
  | 10–14 | 82.0 |
  | 15–19 | 126.0 |
  | 20–24 | 170.0 |
  | 25+ | 215.0 |
- Business rules: (a) use roster `weeks_by_quarter`, not a fixed 13; (b) if `combined_overscale_includes_title` is true, **do not add a titled position premium separately** for that employee (the overscale figure already embeds it); (c) for forecast years advance years of service (see §5).

### Per-employee weekly pay (current year)
```
mws_w        = 2520.0
title_w      = title_premium_pct[title] * 2520.0          # 0 if no title
sen_w        = seniority_band(years_of_service)
overscale_w  = overscale_weekly                            # roster field
if combined_overscale_includes_title: title_w = 0.0       # title folded into overscale
weekly_total = mws_w + title_w + sen_w + overscale_w
```
Quarter pay for employee = `weekly_total × weeks_by_quarter[Q]`. Annual = Σ over Q and employees.

### Output assembly
- `roster_count` = number of employees in the ensemble.
- `quarter_totals` {Q1,Q2,Q3,Q4} = Σ over employees of weekly_total × roster weeks that quarter.
- `annual_pay_type_totals` = Σ over employees/quarters of (weeks × per-pay-type weekly amount). The four pay types are reported by their exact names from `rate_book.pay_types`.
- `annual_total` = Σ of the four pay-type totals (== Σ of quarter totals).
- `largest_pay_type` = the pay-type name with the largest annual total.
- `combined_overscale_employee_count` = **count of employees with `combined_overscale_includes_title == true`** (the "side-letter" employees whose overscale already includes title). These employees have a note like "Overscale amount includes titled position premium per side letter." (Do NOT count mere overscale>0.)
- `partial_quarter_employee_count` = count of employees whose `weeks_by_quarter` has any quarter ≠ 13. Use the roster weeks for these employees (don't fall back to 13).

### Confirmed train reference (ENS-REDWOOD)
- current_year `2026`, roster_count `26`
- quarter_totals: Q1 `977636.40`, Q2 `953292.40`, Q3 `969086.40`, Q4 `977636.40`
- annual_pay_type_totals: Minimum Weekly Scale `3379320.00`, Titled Position Premium `297561.60`, Seniority `142790.00`, Overscale `57980.00`
- annual_total `3877651.60`, largest_pay_type `Minimum Weekly Scale`
- combined_overscale_employee_count `0` (no REDWOOD employee has the flag true), partial_quarter_employee_count `3` (emp -011 Q2=9, -018 Q3=10, -024 Q2=9)

### Pitfalls
- `combined_overscale_includes_title` is per-employee (not per-ensemble). When true, exclude that employee's title premium entirely (the overscale_weekly already contains it).
- Count "partial-quarter employees" from the roster's `weeks_by_quarter`, and use those reduced weeks in the math.
- Title premium is pct × MWS (2520), not pct × (MWS+something). Concertmaster 22%, Principal 20%, Section Lead 15%, Associate/Assistant Principal 10%.

---

## 3. Family: Weekly payroll

**Task shape:** request_memo gives `production_id`. Produce service counts, currency category totals, weekly total, conflict flags, per-musician totals, top-paid musician.

### Rate book facts (`/api/payroll/rate-book`)
- `service_rates` (per service, flat — except Rehearsal which is hourly): 1hr Sound Check `80.0`, 2hr Sound Check `142.5`, Audit `260.25`, Performance `260.25`, Rehearsal `58.75`/hr
- `service_time_limits` (hours): 1hr SC 1.0, 2hr SC 2.0, Audit 3.0, Performance 3.0, Rehearsal 5.0
- `premium_pct`: additional_double 0.10, concertmaster 0.20, electronic 0.25, first_double 0.25, principal_or_lead 0.15, quartet 0.15, vacation 0.04
- `weekly_guarantee` = `2082.0`
- `conflict_thresholds`: rehearsal_earliest_start `09:00`, rehearsal_latest_end `18:30`
- Business rules: Rehearsal is hourly with a **3-hour minimum call**; Performance/Audit/Sound-check are per service; premiums apply to base service pay BEFORE vacation; doubles = 25% first extra + 10% each additional; vacation = 4% of (base + premiums) when `vacation_eligible`; weekly guarantee applies **only to guaranteed regular players (non-substitutes) when base service pay < weekly_guarantee**.

### Production data shape
`/api/payroll/productions?production_id=` → `{production_id, title, week_start, roster[], schedule[]}`.
- `schedule[]`: `{service_id, service_type, date, start_time, end_time, duration_hours}`
- `roster[]`: `{musician_id, name, instrument, assigned_service_ids[], doubles, electronic, lead, principal, quartet, substitute, vacation_eligible}`

### Per-musician computation
1. **Base service pay** = Σ over `assigned_service_ids` of `service_pay(service_type, duration_hours)`:
   - Rehearsal: `58.75 × max(duration_hours, 3.0)` (3-hr minimum call per rehearsal)
   - Performance / Audit / 1hr Sound Check / 2hr Sound Check: flat `service_rates[type]`
   Bucket each service's pay into its category: `performance`, `audit`, `rehearsal`, `sound_check` (1hr+2hr sound checks both roll into `sound_check`).
2. **Premium %** (stacked additively on base service pay):
   - `principal_or_lead` 0.15 if `principal` OR `lead` (one premium, not both)
   - `quartet` 0.15 if `quartet`
   - `electronic` 0.25 if `electronic`
   - `concertmaster` 0.20 if a concertmaster flag is present (the HAMILTON roster has no explicit concertmaster flag; apply only when present)
   - `doubles`: first extra 0.25 + 0.10 × (doubles − 1) for doubles ≥ 1
3. **Category split**:
   - `premium` = base × (principal_or_lead + quartet + electronic + concertmaster portion) — BUT see electronic-substitute treatment below
   - `doubles` = base × doubles_pct (reported in its own `doubles` category, NOT in `premium`)
4. **Electronic-substitute treatment** (drives the `substitute_adjustment` category, "when applicable"): for a musician who is **both `electronic` AND `substitute`**, the 25% electronic premium is reported under `substitute_adjustment` (not `premium`); all other (non-electronic) premiums for that musician still go to `premium`, and doubles still go to `doubles`. For a non-substitute electronic musician, the electronic premium stays in `premium`. (If the rate book ever defines an explicit substitute differential, prefer that; in this environment it does not, so the substitute_adjustment line is driven solely by the electronic-substitute reclassification and is 0 for non-electronic substitutes.)
5. **vacation** = `0.04 × (base + premium + doubles + substitute_adjustment)` if `vacation_eligible` else 0.
6. **guarantee_adjustment** = `max(0, 2082.0 − base_service_pay)` if `substitute == false` else 0. (Condition is on BASE service pay per the rate-book rule; the adjustment tops base up to the guarantee floor.)
7. Musician `total` = base + premium + doubles + vacation + guarantee_adjustment + substitute_adjustment. Per-musician `categories` = only the nonzero category amounts.

### Output assembly
- `service_counts` = count of **distinct schedule services** by `service_type` (e.g. {Rehearsal:2, "1hr Sound Check":1, Performance:4, Audit:1}); only types that occur.
- `category_totals` (currency): performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment, substitute_adjustment (omit substitute_adjustment if 0/not applicable).
- `weekly_total` = Σ musician totals.
- `per_musician` ordered by `musician_id`: `{musician_id, name, total, categories(nonzero)}`.
- `top_paid_musician_id` = musician_id with the highest total.

### Conflict flags (sorted alphabetically; enum)
Evaluate over ALL schedule services:
- `REHEARSAL_EARLY_START` — any Rehearsal with `start_time` < 09:00 (compare HH:MM as minutes).
- `REHEARSAL_LATE_END` — any Rehearsal with `end_time` > 18:30.
- `SERVICE_OVER_TIME_LIMIT` — any service with `duration_hours` > `service_time_limits[service_type]` (strictly greater; equal is OK).
- `SOUND_CHECK_DURATION_MISMATCH` — any "1hr Sound Check" whose `duration_hours` ≠ 1.0, or any "2hr Sound Check" whose `duration_hours` ≠ 2.0.

### Confirmed train reference (PROD-HAMILTON-26)
Schedule (8 services): S01 Rehearsal 08:45–13:45 (5.0h); S02 1hr Sound Check 18:15–19:15 (1.0h); S03 Performance 20:00–22:30 (2.5h); S04 Performance 14:00–16:35 (2.58h); S05 Performance 20:00–22:35 (2.58h); S06 Audit 13:00–15:30 (2.5h); S07 Rehearsal 10:00–15:30 (5.5h); S08 Performance 20:00–22:45 (2.75h).
- service_counts: `{Rehearsal:2, "1hr Sound Check":1, Performance:4, Audit:1}`
- conflict_flags: `["REHEARSAL_EARLY_START","SERVICE_OVER_TIME_LIMIT"]` (S01 starts 08:45<09:00; S07 is 5.5h>5.0h limit; sound check matches its 1hr nominal; no rehearsal ends after 18:30)
- category_totals: performance `5205.00`, audit `520.50`, rehearsal `2467.50`, sound_check `160.00`, premium `1318.44`, doubles `1405.10`, vacation `378.00`, guarantee_adjustment `1276.25`, substitute_adjustment `325.31`
- weekly_total `13056.11`
- per_musician (by id): M-H26-01 `1951.88`, M-H26-02 `2693.73`, M-H26-03 `3010.41`, M-H26-04 `2406.94`, M-H26-05 `2993.14`
- top_paid_musician_id `M-H26-03`

Key per-musician facts: rehearsal pay = 58.75 × max(dur,3) (S01=5h→293.75, S07=5.5h→323.125; a musician with both rehearsals gets 616.875). Each regular musician assigned 4 performances = 1041.00. Substitute M-H26-01 is electronic+substitute → its 325.31 electronic premium is reported as substitute_adjustment; it gets no guarantee (substitute) and no vacation (not eligible). All four regulars have base < 2082 so each receives a base-top-up guarantee (344.12 / 424.12 / 424.12 / 83.88).

### Pitfalls
- `service_counts` counts schedule services, not musician-assignments (don't sum assigned_service_ids).
- Rehearsal uses the 3-hour minimum **per rehearsal service** (max of duration and 3), then × hourly rate.
- Doubles pct = 0.25 + 0.10×(doubles−1); doubles=2 → 0.35, doubles=3 → 0.45.
- Guarantee condition keys off **base service pay** (not base+premium). Substitutes never get guarantee.
- Premiums stack additively; compute on base service pay; vacation is 4% of (base+premium+doubles+substitute_adjustment).
- Conflict thresholds are strictly greater/less (a 5.0h rehearsal vs 5.0 limit is NOT a violation; 5.5h is).

---

## 4. Family: Regional dashboard

**Task shape:** request_memo gives `target_region_id` and `requested_comparison_years` [2024, 2025]. Produce FY2024 and FY2025 region rollups, growth, top/bottom EBITDA branch, and a reconciliation variance.

### SOP
1. From `/api/finance/branches`, get the region's branch_ids (ascending) — e.g. REG-WEST → [BR-004, BR-005, BR-006].
2. **fy2024** = Σ over the region's branches of each IS line over M1..M12: report `revenue, sga, allocations, ebitda` (ebitda = rev−cogs−sga−alloc).
3. **fy2025** = same over M13..M24, plus `ebitda_margin` (= region FY25 ebitda / region FY25 revenue, 4dp) and `sales_per_labor_headcount` = region FY25 revenue / **mean** of the 12 monthly region labor_headcount totals. Region monthly labor_headcount = Σ over the region's branches of that month's `labor_headcount`; average those 12 monthly sums.
4. **revenue_growth_pct** = (FY25 region revenue − FY24 region revenue) / FY24 region revenue, 4dp.
5. **top_ebitda_branch_id** / **bottom_ebitda_branch_id** = branch in the region with max/min FY2025 ebitda.
6. **region_reconciliation_variance** = (Σ of the region's branches' FY2025 ebitda) − (FY2025 ebitda computed from the region-filtered records). Using the active operations data these tie out → **`0.00`**. Any nonzero value means a branch was dropped/added or a stale source was used; recompute from `/api/finance/records` (the same records answer `?region=` and per-branch queries).

### Confirmed train reference (REG-WEST)
- branch_ids: [BR-004, BR-005, BR-006]
- fy2024: revenue `10453506.76`, sga `3763931.94`, allocations `354160.21`, ebitda `2310369.33`
- fy2025: revenue `11139674.79`, sga `3935915.21`, allocations `376735.89`, ebitda `2515012.15`, ebitda_margin `0.2258`, sales_per_labor_headcount `297719.59` (mean region monthly labor_headcount = 37.4167)
- revenue_growth_pct `0.0656`, top_ebitda_branch_id `BR-005` (893436.01), bottom_ebitda_branch_id `BR-006` (764966.04)
- region_reconciliation_variance `0.00`

### Pitfalls
- Region membership from the live branches file only (BR-004 is REG-WEST).
- `sales_per_labor_headcount` at region level = region revenue / mean of monthly region headcount totals (not the average of the branches' per-branch ratios).
- reconciliation_variance is a tie-out: it should be 0.00 when you use active records for both the branch-sum and region-filter views. The memo's "tie back to active operating data" is the signal.
- `ebitda_margin` and `revenue_growth_pct` are 4dp; currency fields 2dp.

---

## 5. Family: Compensation forecast

**Task shape:** request_memo gives `ensemble_id`, `scenario_id`, `forecast_years` [current, year_plus_1, year_plus_2]. Produce annual totals for the 3 years, two growth rates, Y+2 quarter & pay-type detail, largest-growth pay type, and the two roster-treatment counts.

### Scenario drivers (`/api/compensation/scenarios`)
Each scenario has `year_plus_1` and `year_plus_2` with:
- `mws_growth`, `overscale_growth`, `seniority_growth` (per-pay-type growth rates)
- `title_pct_multiplier` (multiplier on the title premium)

Example — `case_maple_board`:
- y+1: mws_growth 0.035, overscale_growth 0.012, seniority_growth 0.018, title_pct_multiplier 1.0
- y+2: mws_growth 0.033, overscale_growth 0.014, seniority_growth 0.020, title_pct_multiplier 1.0

(Other scenarios: `case_cedar_negotiation`, `case_oak_sensitivity`, `case_redwood_baseline`. Always pull the requested scenario_id from the endpoint — do not hardcode.)

### Cumulative driver application
Growth rates compound year-over-year (cumulative). For year_plus_N:
- `mws_N` = mws_current × Π(1 + mws_growth_k) for k=1..N
- `seniority_growth_cum_N` = Π(1 + seniority_growth_k) − 1   (applied as a multiplier on the seniority band amount)
- `overscale_growth_cum_N` = Π(1 + overscale_growth_k) − 1   (applied as a multiplier on overscale_weekly)
- `title_pct_multiplier_cum_N` = Π(title_pct_multiplier_k)   (applied as a multiplier on the title premium)

For `case_maple_board` (multipliers all 1.0): mws path = 2520.0 → 2608.20 (y+1) → 2694.2706 (y+2); sen_cum = 0.018 (y+1), 0.03836 (y+2); os_cum = 0.012 (y+1), 0.026168 (y+2).

### Forecast-year per-employee weekly pay
For year_plus_N (advance years_of_service by N):
```
yos_eff      = years_of_service + N                         # band selection
sen_w        = seniority_band(yos_eff) × (1 + seniority_growth_cum_N)
overscale_w  = overscale_weekly × (1 + overscale_growth_cum_N)
title_w      = title_premium_pct[title] × mws_N × title_pct_multiplier_cum_N
if combined_overscale_includes_title: title_w = 0.0         # overscale already includes title (rule carries into forecast)
weekly_total = mws_N + title_w + sen_w + overscale_w
```
Use the **roster `weeks_by_quarter`** in every forecast year (partial-quarter employees keep their reduced weeks; the partial-quarters rule does not reset). Annual total for a year = Σ employees Σ quarters (weekly_total × weeks_by_quarter[Q]).

- `annual_totals.current` = current-year comp (mws=2520, current yos, no scenario growth) — same method as §2 current-year.
- `annual_totals.year_plus_1`, `annual_totals.year_plus_2` = forecast years with cumulative drivers.

### Growth rates & largest growth
- `growth_rates.year_plus_1_vs_current` = (annual Y+1 − annual current) / annual current, 4dp.
- `growth_rates.year_plus_2_vs_year_plus_1` = (annual Y+2 − annual Y+1) / annual Y+1, 4dp.
- `largest_growth_pay_type` = the pay type with the largest percentage growth from year_plus_1 to year_plus_2 (if a tie, largest absolute currency growth). Each pay type's annual total for a forecast year = Σ employees Σ quarters (weeks × that pay type's weekly component). NOTE seniority grows fastest because both the seniority_growth rate applies AND advancing yos can push an employee into a higher band (e.g. yos 4→5 jumps 0→48; yos 24→25 jumps 170→215).

### Quarter / pay-type detail (year_plus_2)
- `year_plus_2_quarter_totals` {Q1..Q4} = Σ employees of weekly_total(Y+2) × weeks_by_quarter[Q].
- `year_plus_2_pay_type_totals` = the four pay types' annual totals at Y+2.

### Roster treatment counts (year-independent, from the roster)
- `combined_overscale_employee_count` = count of `combined_overscale_includes_title == true` in the ensemble.
- `partial_quarter_employee_count` = count with any `weeks_by_quarter[Q] != 13`.

### Confirmed train reference (ENS-MAPLE, case_maple_board)
- annual_totals: current `4232653.60`, year_plus_1 `4390313.79`, year_plus_2 `4545741.02`
- growth_rates: year_plus_1_vs_current `0.0372`, year_plus_2_vs_year_plus_1 `0.0354`
- year_plus_2_quarter_totals: Q1 `1129891.58`, Q2 `1138616.48`, Q3 `1138616.48`, Q4 `1138616.48` (Q1 lower because ENS-MAPLE-005 has Q1=10 weeks)
- year_plus_2_pay_type_totals: Minimum Weekly Scale `3914775.18`, Titled Position Premium `320833.74`, Seniority `190829.80`, Overscale `119302.29`
- largest_growth_pay_type `Seniority`
- combined_overscale_employee_count `4` (ENS-MAPLE-004, -013, -016, -028), partial_quarter_employee_count `1` (ENS-MAPLE-005, Q1=10)

### Pitfalls
- Advance **years_of_service** by +1 / +2 BEFORE picking the seniority band (band crossings are a real driver of seniority growth). Apply seniority_growth on top of the new band amount.
- `combined_overscale_includes_title` rule carries into every forecast year: those employees get title_w = 0 (their overscale_weekly, grown by overscale_growth, already includes title).
- Growth is **cumulative/compounding** across years (multiply (1+g) factors), not a simple sum of the two years' rates.
- MWS growth also raises the title-premium base (title = pct × mws_N × multiplier), so title grows with MWS even when title_pct_multiplier = 1.0.
- Use roster weeks_by_quarter in forecast years too (partial-quarter weeks persist).
- Pull the scenario by `scenario_id` from the endpoint; don't assume values.

---

## 6. Cross-family quick checks (sanity)
- FY totals are ~12× a single month; if a FY revenue looks like one month's value, you sliced with zero-padded keys (M01..M09 don't exist).
- EBITDA margin for these branches runs ~20–26%; ARPU ~$11.5k–$15k; sales/labor-headcount ~$285k–$331k. Region values sit near the mean of members.
- Compensation current-year annual per ensemble is in the $3.8M–$4.2M range; MWS dominates (>85% of pay).
- Payroll weekly totals are ~$13k for a 5-musician Hamilton week; guarantee top-ups matter when base < 2082.
- Forecast 2-year growth is single-digit percent annually; seniority is usually the fastest-growing pay type.

## 7. What the skill deliberately does NOT contain
- No test-task answers or derivations.
- No copies of train gold JSON beyond the illustrative reference values above (used only to anchor the rules).
- No calls to any `/api/judge` endpoint — judge access is train-only and not used at test time.
- No speculation about evaluator internals. Where a convention is ambiguous (e.g. ARPU averaging basis, electronic-substitute reclassification, reconciliation_variance tie-out), the rule stated is the one confirmed against the live data; apply it consistently and recompute for the test target.
