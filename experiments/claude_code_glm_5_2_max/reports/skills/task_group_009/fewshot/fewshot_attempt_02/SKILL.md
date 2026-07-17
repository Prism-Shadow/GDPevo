# Crescent Finance Ops — Solver Skill

Transferable playbook for the Crescent Arts Collective "Finance Ops" task group. There are four task
families in this group, all driven by the same live remote API:

1. **Branch close reporting** (one branch, current vs prior month + FY view + regional/ranking facts)
2. **Regional / company dashboard** (one region, FY2024 vs FY2025 + operating ratios + branch EBITDA rank)
3. **Compensation current-year summary** (one ensemble, by quarter and pay type)
4. **Compensation forecast** (one ensemble + scenario, current / Year+1 / Year+2)
5. **Weekly payroll review** (one production, category totals + per-musician + conflict flags)

Everything below was confirmed by reproducing the staged train gold answers against the live data. Rules
are stated generically so they transfer to new target ids (different branch / region / ensemble /
production / scenario).

---

## 0. Environment access (LIVE REMOTE — always use this host)

- Base URL: `<remote-env-url>`  (the staged `payloads/environment_access.json` `base_url`
  `http://127.0.0.1:8047` is a dead local dev placeholder — never use it.)
- All responses are JSON. Use `curl` or python `urllib`/`requests`.
- Endpoints (all `GET`, all on the base URL):
  - `/health`, `/api/manifest`
  - `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
  - `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
  - `/api/payroll/rate-book`, `/api/payroll/productions`
- Useful filters:
  - `/api/finance/records?branch_id=BR-009`
  - `/api/finance/records?region=REG-SOUTH`
  - `/api/finance/records?account=product_revenue`
  - `/api/compensation/rosters?ensemble_id=ENS-REDWOOD`
  - `/api/payroll/productions?production_id=PROD-HAMILTON-26`
- Never call any `/api/judge` endpoint. The judge is train-only and off-limits at solve time.

Fetch the **rate books and the period-map/accounts catalogs first**, once, and reuse them — they are the
source of truth for every numeric convention below.

---

## 1. Shared conventions (apply to every family)

### 1.1 Output shape
- Return ONE JSON object containing exactly the data keys listed under `required_top_level_keys` in the
  task's `answer_template.json`. Do NOT echo the template metadata fields
  (`description`, `required_top_level_keys`, `field_types`) into the answer.
- Currency values: round to 2 decimals. Percent / ratio / margin fields: round to 4 decimals.
- Integers (counts, ranks): plain ints.
- Lists: ascending stable IDs unless a rank field states otherwise.
- `per_musician` ordered by `musician_id`; `conflict_flags` sorted alphabetically; `branch_ids` ascending.

### 1.2 Rounding — ROUND_HALF_UP, no intermediate rounding
This is the single biggest source of off-by-0.01 errors. The convention, confirmed against gold:
- Compute every component in **full floating precision**.
- Round only at the end:
  - each displayed value = `round(full_precision_value, 2 or 4)` using **ROUND_HALF_UP** (not banker's
    rounding; Python's built-in `round` is banker's — use `decimal.Decimal(...).quantize(Decimal("0.01"),
    ROUND_HALF_UP)`).
  - a per-entity `total` = `round(sum of that entity's full-precision components, 2)` — NOT the sum of
    already-rounded components.
  - a top-level aggregate (e.g. `category_totals`, `quarter_totals`) =
    `round(sum over entities of full-precision component, 2)` — again, sum the unrounded values then round
    once.
- Equivalently: never chain rounded numbers into another rounded number.

### 1.3 Period map (finance)
24 monthly periods `M1..M24`, two fiscal years:
- `M1..M12` → **FY2024**
- `M13..M24` → **FY2025**

So fiscal year membership is period-range based: a fiscal-year total = sum of the 12 monthly `values` for
that branch×account over the FY's period range. The `period-map` endpoint gives the exact
`period → fiscal_year` map; use it, don't hardcode beyond the M1–M12 / M13–M24 split.

`period_convention` object in the branch-close answer uses exactly these keys:
`M1_to_M12` = `"FY2024"`, `M13_to_M24` = `"FY2025"`, `current_month` = the close period label (e.g.
`"M24"`), `prior_month` = the prior period label (e.g. `"M23"`).

### 1.4 Accounts & categories (finance)
Each `account` belongs to exactly one `category` and has a `metric_type`:

| category    | accounts                                                                 | metric_type |
|-------------|--------------------------------------------------------------------------|-------------|
| `revenue`   | `product_revenue`, `service_revenue`                                     | currency    |
| `cogs`      | `direct_materials_cogs`, `direct_labor_cogs`                             | currency    |
| `sga`       | `sales_sga`, `admin_sga`, `occupancy_sga`                                | currency    |
| `allocations` | `shared_service_allocations`                                           | currency    |
| `operating` | `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog` | count |

Critical: the `operating` accounts are **counts, not currency**. Never sum them into revenue/sga/etc.
They are used only as denominators for ratios (active_customers → ARPU, labor_headcount → sales per
labor headcount).

### 1.5 Income statement construction (per branch, per period or per FY)
For any single period or any FY range, roll accounts up to category totals, then:

```
revenue       = sum(account where category == "revenue")
cogs          = sum(account where category == "cogs")
gross_margin  = revenue - cogs
sga           = sum(account where category == "sga")
allocations   = sum(account where category == "allocations")
ebitda        = gross_margin - sga - allocations
```

A fiscal-year figure = the same rollup but summing each account's monthly `values` over the FY's 12
periods before subtracting.

### 1.6 Ratios (FY basis)
- `ebitda_margin` = `fy_ebitda / fy_revenue`  (4dp)
- `arpu` = `fy_revenue / fy_sum(active_customers)`  (currency 2dp) — note: divisor is the **sum of the
  12 monthly `active_customers` values** for that branch/FY, not an average.
- `sales_per_labor_headcount` = `fy_revenue / fy_sum(labor_headcount)`  (currency 2dp) — same convention:
  sum the 12 monthly labor_headcount values.

### 1.7 Growth / variance
- MoM revenue variance `amount` = `current_period_revenue - prior_period_revenue`; `pct` =
  `amount / prior_period_revenue` (4dp).
- FY growth pct = `(fy_new - fy_old) / fy_old` (4dp). `revenue_growth_pct`, `ebitda_growth_pct` etc. all
  follow this.

### 1.8 Branches & regions (membership from `/api/finance/branches`)
12 branches, 4 regions (region membership comes from the live `branches` endpoint — never from stale
memo notes; a draft workbook/memo may name a wrong region and must be reconciled to the live data):

- REG-NORTH: BR-001, BR-002, BR-003
- REG-WEST:  BR-004, BR-005, BR-006
- REG-EAST:  BR-007, BR-008, BR-011
- REG-SOUTH: BR-009, BR-010, BR-012

### 1.9 Ranking convention — "rank_desc" = 1 is best (highest)
`rank_desc` fields mean descending rank: rank 1 = the **highest** value, rank 2 = second highest, etc.
Compute by sorting descending by the metric and taking 1-based position.

---

## 2. SOP — Branch close reporting (train_001 family)

Inputs from `request_memo.json`: `target_branch_id`, `close_period` (e.g. `M24`), `prior_period`
(e.g. `M23`). Watch for a `memo_note` referencing a draft workbook with stale facts — ignore it and use
live data.

Steps:
1. `GET /api/finance/branches` → resolve `target_branch_name` and its `region_id`. Build the region's
   `branch_ids` list (ascending) from live data.
2. `GET /api/finance/period-map` (or use §1.3) → map `close_period`/`prior_period` to fiscal years;
   fill `period_convention`.
3. `GET /api/finance/records?branch_id=<target>` → for the close period, build `m<close>_income_statement`
   (revenue, cogs, gross_margin, sga, allocations, ebitda) per §1.5.
4. `mom_revenue_variance`: revenue(close) − revenue(prior); `pct` = amount / revenue(prior).
5. `fy2025_vs_fy2024`: build the FY2025 IS (sum M13–M24) and FY2024 IS (sum M1–M12). The `fy2025`
   sub-object also includes `ebitda_margin`, `arpu`, `sales_per_labor_headcount` (§1.6, using the
   FY2025 sums of active_customers and labor_headcount). Also return `revenue_growth_pct` and
   `ebitda_growth_pct` (fy2025 vs fy2024).
   - The template names these keys literally (`fy2025`, `revenue_growth_pct`, …) even if the task's
     fiscal years differ — match the template's key names exactly.
6. `region_context`:
   - `region_id` = target branch's region (live).
   - `branch_ids` = ascending list of that region's branch ids.
   - `fy2025_ebitda` = **sum of FY2025 EBITDA across all branches in the region** (region total).
   - `ebitda_rank_desc` = that **region's** FY2025 EBITDA rank among all four regions, descending
     (1 = highest region). Common pitfall: this is NOT the target branch's rank within its region.
7. `branch_rankings` (company-wide, across all 12 branches):
   - `sales_growth_rank_desc` = target branch's rank for FY2025-vs-FY2024 **revenue** growth, descending.
   - `top_sales_growth_branch_id` = branch with the highest FY2025 revenue growth.
   - `top_arpu_branch_id` = branch with the highest FY2025 ARPU.
8. Round per §1.2.

### Pitfalls (branch close)
- Do not exclude the target branch from its region based on a stale memo/draft workbook.
- `region_context.fy2025_ebitda` is the **region total**, not the branch's EBITDA.
- `ebitda_rank_desc` ranks **regions**, not branches-within-region.
- ARPU / sales-per-labor-headcount divisors are the **FY sum** of monthly counts.

---

## 3. SOP — Regional / company dashboard (train_004 family)

Inputs: `target_region_id`, `requested_comparison_years` (e.g. `[2024, 2025]`).

Steps:
1. `GET /api/finance/branches` → `branch_ids` = ascending list of the region's branches.
2. For each FY in the comparison, sum each IS line across all member branches:
   - `fy2024` / `fy2025` objects contain `revenue`, `sga`, `allocations`, `ebitda` (no cogs/gross_margin
     on the regional view — match the template).
   - The `fy2025` (latest year) object ALSO carries `ebitda_margin` and `sales_per_labor_headcount`
     (region FY2025 ebitda / region FY2025 revenue; region FY2025 revenue / region FY2025
     labor_headcount sum). The `fy2024` object does NOT include these extra fields.
3. `revenue_growth_pct` = (fy2025 revenue − fy2024 revenue) / fy2024 revenue.
4. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = member branch with max / min **FY2025 EBITDA**
   (descending: top = highest, bottom = lowest).
5. `region_reconciliation_variance` = `region_fy2025_ebitda − sum(member branches' fy2025_ebitda)` → by
   construction this is `0.0` (region total equals sum of branch totals). Report `0.0`. (If it were
   non-zero you'd have a data/aggregation bug — recompute.)
6. Round per §1.2.

A "company dashboard" variant uses the same skeleton but the scope is all 12 branches (the "region" is
the whole company) — analogous fields, all-branch totals and whole-company operating ratios.

### Pitfalls (regional)
- `region_reconciliation_variance` is a reconciliation check — expect exactly `0.0`; a non-zero value
  means you double-counted or missed a branch.
- Only the latest FY object gets `ebitda_margin` + `sales_per_labor_headcount`.
- `top_ebitda_branch_id` uses FY2025 EBITDA, not revenue.

---

## 4. The compensation engine (shared by §5 and §6)

`GET /api/compensation/rate-book` returns the canonical config:

- `current_year`: **2026**
- `minimum_weekly_scale` (MWS): **2520.0** per week
- `pay_types` (use this exact order everywhere): `["Minimum Weekly Scale", "Titled Position Premium",
  "Seniority", "Overscale"]`
- `quarter_weeks` default: `{Q1:13, Q2:13, Q3:13, Q4:13}` — but **use each employee's
  `weeks_by_quarter`**, not the default, when partial-quarter employees are listed.
- `seniority_weekly` bands (weekly amount added per week; band chosen by years-of-service):

  | min_years | max_years | weekly_amount |
  |-----------|-----------|---------------|
  | 0  | 4    | 0.0   |
  | 5  | 9    | 48.0  |
  | 10 | 14   | 82.0  |
  | 15 | 19   | 126.0 |
  | 20 | 24   | 170.0 |
  | 25 | null | 215.0 |

- `title_premium_pct` (applied to MWS base; keyed by the roster `title` string):
  - `Assistant Principal`: 0.10
  - `Associate Principal`: 0.10
  - `Concertmaster`: 0.22
  - `Principal`: 0.20
  - `Section Lead`: 0.15

- Business rules (verbatim meaning, must implement):
  1. **Use `weeks_by_quarter` per employee**, not a fixed 13-week quarter, when partial-quarter
     employees are listed. (A "partial-quarter employee" = any employee whose `weeks_by_quarter` has a
     quarter `!= 13`.)
  2. **`combined_overscale_includes_title`**: if `true` for an employee, do NOT add a separate Titled
     Position Premium for that employee (their title premium is already bundled into overscale). Their
     Titled Position Premium pay-type amount is 0.
  3. **Forecast service advancement**: for Year+1 add 1 year of service, for Year+2 add 2 years, before
     selecting the seniority band. (Current year uses the roster's `years_of_service` as-is.)

### 4.1 Per-employee, per-quarter, per-pay-type formula
Let `mws_eff` = MWS scaled by the cumulative MWS growth factor (1.0 for current year), `sen_eff` =
seniority-band weekly amount (from advanced yos) scaled by the cumulative seniority growth factor,
`ov_eff` = `overscale_weekly` scaled by the cumulative overscale growth factor, `title_mult` = cumulative
title-pct multiplier (1.0 for current year), `tp` = `title_premium_pct[title]` (0 if title not in map or
employee is combined-overscale).

For each quarter `q` with weeks `w_q`:
- `Minimum Weekly Scale`   += `mws_eff * w_q`
- `Titled Position Premium`+= `0` if `combined_overscale_includes_title` else `mws_eff * tp * title_mult * w_q`
- `Seniority`              += `sen_eff * w_q`
- `Overscale`              += `ov_eff * w_q`

Sum across employees → `quarter_totals[q]` and `annual_pay_type_totals[type]`. `annual_total` =
sum of all quarter_totals (= sum of all pay-type totals). Quarter totals sum == pay-type totals sum.

### 4.2 Counts
- `roster_count` = number of employees on the ensemble roster (`GET
  /api/compensation/rosters?ensemble_id=...`).
- `combined_overscale_employee_count` = count of employees with `combined_overscale_includes_title ==
  true`.
- `partial_quarter_employee_count` = count of employees with any `weeks_by_quarter[q] != 13`.

### 4.3 Forecast drivers (cumulative compounding — critical)
`GET /api/compensation/scenarios` returns per-scenario `year_plus_1` and `year_plus_2` blocks, each with
`mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`. These are **year-over-year
growth rates that compound cumulatively**:

- current year: all factors = 1.0, advance = 0.
- Year+1: apply `year_plus_1` block: `mws_f = (1+mws_growth_y1)`, `ov_f = (1+overscale_growth_y1)`,
  `sen_f = (1+seniority_growth_y1)`, `title_mult_f = title_pct_multiplier_y1`; advance = 1.
- Year+2: apply Year+1 then Year+2 on top (compounded):
  `mws_f = (1+mws_growth_y1)*(1+mws_growth_y2)`, similarly for `ov_f` and `sen_f`;
  `title_mult_f = title_pct_multiplier_y1 * title_pct_multiplier_y2`; advance = 2.

Do NOT reset factors each year — compound them. (Resetting gives wildly wrong Year+2 totals.)
`seniority_growth`/`mws_growth`/`overscale_growth` are applied as `(1+rate)` multipliers to the
weekly amounts; `title_pct_multiplier` multiplies the title percent directly.

### 4.4 "largest" pay type
- Current-year summary: `largest_pay_type` = the pay type with the largest `annual_pay_type_total`.
- Forecast: `largest_growth_pay_type` = the pay type with the largest growth rate from **current-year
  total to Year+2 total** = `max over types of (y2_total - current_total)/current_total`.

---

## 5. SOP — Compensation current-year summary (train_002 family)

Inputs: `ensemble_id`, `summary_type` (current-year by quarter and pay type).

Steps:
1. `GET /api/compensation/rate-book` and `GET /api/compensation/rosters?ensemble_id=<id>`.
2. `current_year` = rate-book `current_year` (2026). `roster_count` = len(roster).
3. `pay_types` = the rate-book `pay_types` list, in order.
4. For each employee, for each quarter, compute the four pay-type amounts per §4.1 (current year → all
   factors 1.0, advance 0, use roster `years_of_service` and `weeks_by_quarter`).
5. Aggregate:
   - `quarter_totals` = {Q1,Q2,Q3,Q4} sum across employees.
   - `annual_pay_type_totals` = per pay-type sum across all employees & quarters.
   - `annual_total` = sum of quarter_totals (= sum of pay-type totals).
   - `largest_pay_type` = argmax of `annual_pay_type_totals`.
   - `combined_overscale_employee_count`, `partial_quarter_employee_count` per §4.2.
6. Round per §1.2 (currency 2dp).

### Pitfalls (comp current)
- Respect `combined_overscale_includes_title` (skip title premium for those employees).
- Use each employee's `weeks_by_quarter`, NOT a flat 13.

---

## 6. SOP — Compensation forecast (train_005 family)

Inputs: `ensemble_id`, `scenario_id`, `forecast_years` (current / year_plus_1 / year_plus_2).

Steps:
1. `GET /api/compensation/rate-book`, `GET /api/compensation/rosters?ensemble_id=<id>`,
   `GET /api/compensation/scenarios` → pick `scenarios[scenario_id]`.
2. Compute three years using §4.1 + §4.3:
   - current: factors all 1.0, advance 0.
   - year_plus_1: compounded Year+1 factors, advance 1.
   - year_plus_2: compounded Year+1×Year+2 factors, advance 2.
3. `annual_totals` = {current, year_plus_1, year_plus_2} (each = sum of that year's quarter totals).
4. `growth_rates`:
   - `year_plus_1_vs_current` = (y1 − current)/current.
   - `year_plus_2_vs_year_plus_1` = (y2 − y1)/y1.
5. `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` from the Year+2 computation.
6. `largest_growth_pay_type` per §4.4.
7. `combined_overscale_employee_count`, `partial_quarter_employee_count` from the **roster**
   (same for all years; roster attributes don't change).
8. Round currency 2dp, growth rates 4dp.

### Pitfalls (forecast)
- Compound growth factors cumulatively across years — do not apply Year+2 rates to the current base.
- Advance years-of-service by +1 / +2 before picking the seniority band (this can move an employee up a
  band, changing seniority weekly amount materially — that's why Seniority typically shows the largest
  growth).
- `title_pct_multiplier` is a multiplier on the title **percent**, not an additive growth rate; it
  compounds multiplicatively across years.
- `annual_totals.year_plus_2` must equal `sum(year_plus_2_quarter_totals)` and
   `sum(year_plus_2_pay_type_totals)`.

---

## 7. The weekly payroll engine (train_003 family)

`GET /api/payroll/rate-book`:

- `service_rates` (per-service flat, except Rehearsal which is hourly):
  - `1hr Sound Check`: 80.0
  - `2hr Sound Check`: 142.5
  - `Audit`: 260.25
  - `Performance`: 260.25
  - `Rehearsal`: 58.75 per hour
- `service_time_limits` (hours, for conflict detection):
  - `1hr Sound Check`: 1.0, `2hr Sound Check`: 2.0, `Audit`: 3.0, `Performance`: 3.0, `Rehearsal`: 5.0
- `conflict_thresholds`: `rehearsal_earliest_start` = `09:00`, `rehearsal_latest_end` = `18:30`.
- `premium_pct`:
  - `additional_double`: 0.10
  - `concertmaster`: 0.20
  - `electronic`: 0.25
  - `first_double`: 0.25
  - `principal_or_lead`: 0.15
  - `quartet`: 0.15
  - `vacation`: 0.04
- `weekly_guarantee`: 2082.0

Business rules (verbatim meaning, must implement):
- Rehearsal pay is **hourly with a three-hour minimum call** → `max(duration_hours, 3.0) * 58.75`.
- Performance / Audit / Sound-check rates are **per service** (flat, regardless of duration).
- Premiums apply to the musician's **base service pay** before vacation.
- Doubles premium: `0.25` for the first extra instrument, `0.10` for each additional extra instrument.
- Vacation = `4%` of (base service pay + premiums + doubles) when `vacation_eligible` is true.
- Weekly guarantee adjustment applies **only to guaranteed regular players** (i.e. `substitute == false`)
  when base service pay is below `weekly_guarantee`.

Roster musician fields (from `/api/payroll/productions?production_id=...` → `roster[]`):
`musician_id`, `name`, `instrument`, `assigned_service_ids`, `doubles` (int count of extra instruments),
`electronic` (bool), `lead` (bool), `principal` (bool), `quartet` (bool), `substitute` (bool),
`vacation_eligible` (bool). No `concertmaster`/`title` field exists in the payroll roster data; map
`principal` OR `lead` → `principal_or_lead` (0.15, added once even if both true).

### 7.1 Service base pay (per musician)
- `performance_base` = (# assigned Performance services) × 260.25
- `audit_base`       = (# assigned Audit services) × 260.25
- `sound_check_base` = (# assigned 1hr Sound Check)×80.0 + (# assigned 2hr Sound Check)×142.5
- `rehearsal_base`   = Σ over assigned Rehearsal services of `max(duration_hours, 3.0) × 58.75`
- `base_service_pay` = sum of the four.

### 7.2 Premiums (per musician), all applied to `base_service_pay`
- Role/electronic premium % = `principal_or_lead`(0.15 if principal or lead) + `quartet`(0.15 if quartet)
  + `electronic`(0.25 if electronic). (Concertmaster 0.20 would apply if a roster ever designates it; no
  field triggers it in the current data, so do not add it.)
  → `premium` component = `base_service_pay × role_electronic_pct`.
- Doubles premium % = `0.25` if `doubles >= 1`, plus `0.10` for each additional (i.e.
  `0.25 + 0.10×(doubles−1)` for `doubles >= 1`; 0 for doubles=0).
  → `doubles` component = `base_service_pay × doubles_pct`.
- **Stacking is additive**: the rates sum, then multiply base. They do NOT compound on each other.

### 7.3 Vacation
`vacation` = `0.04 × (base_service_pay + premium_component_full_precision + doubles_component_full_precision)`
if `vacation_eligible` else `0.0`. Compute from full-precision premium/doubles (not rounded).

### 7.4 Substitute treatment (electronic-substitute rule)
For musicians with `substitute == true`:
- **No weekly guarantee** (substitutes forfeit the guarantee).
- **Substitute premium = 100% of `base_service_pay`** (i.e. double pay on services).
- That premium is allocated across categories as follows (confirmed against the train production):
  - The portion attributable to **performance base**: half is added to the `performance` category and
    half is reported as `substitute_adjustment`.
    → `performance` category becomes `performance_base × 1.5`; `substitute_adjustment` =
    `0.5 × performance_base`.
  - The portion attributable to **non-performance base** (audit + rehearsal + sound_check): half is added
    to `premium` and half to `doubles` (on top of the role/electronic and doubles premiums from §7.2).
    → `premium` += `0.5 × non_performance_base`; `doubles` += `0.5 × non_performance_base`.
- Vacation for substitutes (if `vacation_eligible`) is computed on the **pre-substitution**
  `base + premium_component + doubles_component` (role/electronic + doubles, before the substitute
  re-allocation), per §7.3. (No train case exercises a vacation-eligible substitute — apply this rule
  and flag if uncertain.)

Worked shape (matches train gold exactly): a substitute whose `performance_base = P`, `non_performance_base = N`,
role+electronic premium rate `r`, doubles rate `d` (r,d as decimals), base `B = P+N`:
- `performance` = `P × 1.5`
- (each non-performance category `audit`/`rehearsal`/`sound_check`) = its own base (unchanged)
- `premium`        = `B × r + 0.5 × N`
- `doubles`        = `B × d + 0.5 × N`
- `substitute_adjustment` = `0.5 × P`
- `vacation` (if eligible) = `0.04 × (B + B×r + B×d)`
- `guarantee_adjustment` = 0
- per-musician total = round(sum of all full-precision components, 2)

### 7.5 Weekly guarantee (non-substitutes only)
`guarantee_adjustment` = `max(0.0, weekly_guarantee − base_service_pay)` when `substitute == false`, else
`0.0`. (`weekly_guarantee` = 2082.0.) No guarantee if `base_service_pay >= 2082.0`.

### 7.6 Per-musician assembly & rounding
- `categories` = map of **nonzero** category → `round(component, 2)` (ROUND_HALF_UP), for categories:
  `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`,
  `guarantee_adjustment`, `substitute_adjustment`. Omit zero categories entirely.
- `total` = `round(sum of all full-precision components, 2)` — NOT the sum of the rounded categories.
- Order `per_musician` by `musician_id`.

### 7.7 Production-level aggregates
- `service_counts` = object mapping each **service_type string** present in the schedule to its count
  (e.g. `{"Performance": 4, "Rehearsal": 2, "Audit": 1, "1hr Sound Check": 1}`). Count distinct services
  in the schedule, not per-musician assignments.
- `category_totals` = for each category, `round(Σ over musicians of full-precision component, 2)`.
- `weekly_total` = `round(Σ over all musicians & categories of full-precision component, 2)` = round(Σ
  of category_totals' unrounded sums, 2).
- `top_paid_musician_id` = `musician_id` with the highest `total` (break ties by musician_id order).

### 7.8 Conflict flags (deduped, sorted alphabetically)
Iterate every service in `schedule`:
- `REHEARSAL_EARLY_START` if any `Rehearsal` has `start_time < "09:00"` (string compare `HH:MM` works).
- `REHEARSAL_LATE_END`    if any `Rehearsal` has `end_time > "18:30"`.
- `SERVICE_OVER_TIME_LIMIT` if any service has `duration_hours > service_time_limits[service_type]`
  (strictly greater; equal-to-limit is OK).
- `SOUND_CHECK_DURATION_MISMATCH` if a `1hr Sound Check` service has `duration_hours != 1.0` OR a
  `2hr Sound Check` service has `duration_hours != 2.0`.

Deduplicate into a set, return as a sorted list. The four enums are exactly:
`REHEARSAL_EARLY_START`, `REHEARSAL_LATE_END`, `SERVICE_OVER_TIME_LIMIT`, `SOUND_CHECK_DURATION_MISMATCH`.

### Pitfalls (payroll)
- Rehearsal: 3-hour minimum call (use `max(duration, 3)`), hourly rate 58.75 — most other services are
  flat per-service. Confusing rehearsal hours with service counts is a common error.
- Doubles premium is `0.25 + 0.10×(doubles−1)`, NOT `0.25×doubles`.
- `principal` and `lead` both → the single `principal_or_lead` 0.15 (do not double-count if both true).
- Vacation is 4% of base **plus premiums plus doubles** (full precision), not 4% of base alone.
- Guarantee is for **regular (non-substitute) players only**, and only when base < 2082.
- Substitute premium ≈ double pay; the re-allocation into performance/premium/doubles/substitute_adjustment
  matters for `categories` and `category_totals` to match — see §7.4.
- Round half-up, sum unrounded then round — per-category rounding then summing gives 0.01–0.03 errors.
- `top_paid_musician_id` is the highest `total`, not the most services.

---

## 8. Quick-reference numbers (confirmed from live rate books)

Compensation (`/api/compensation/rate-book`): current_year 2026 · MWS 2520.0/wk · quarter_weeks 13/13/13/13
(default) · seniority weekly bands 0/48/82/126/170/215 at 0–4/5–9/10–14/15–19/20–24/25+ yrs · title pct
Asst/Assoc Principal 0.10, Section Lead 0.15, Principal 0.20, Concertmaster 0.22.

Payroll (`/api/payroll/rate-book`): rates Performance 260.25, Audit 260.25, 1hr Sound Check 80.0,
2hr Sound Check 142.5, Rehearsal 58.75/hr (3hr min) · time limits Perf/Audit 3.0, 1hr SC 1.0, 2hr SC 2.0,
Rehearsal 5.0 · rehearsal window 09:00–18:30 · premiums first_double 0.25, additional_double 0.10,
electronic 0.25, principal_or_lead 0.15, quartet 0.15, concertmaster 0.20, vacation 0.04 ·
weekly_guarantee 2082.0.

Finance (`/api/finance/*`): 24 periods M1–M24 (`M1–M12`=FY2024, `M13–M24`=FY2025) · 12 branches / 4
regions · accounts roll up into category IS per §1.4–1.5 · operating accounts are counts (denominators
only) · ARPU = FY revenue / FY sum(active_customers) · sales-per-labor = FY revenue / FY
sum(labor_headcount).

## 9. General solve hygiene
- Always pull rate-books + period-map + accounts + branches first; never trust memo/workbook text over
  live data.
- Resolve all target ids (`branch_id`, `region_id`, `ensemble_id`, `production_id`, `scenario_id`) from
  the live endpoints, not from the prompt narrative.
- Compute in full precision, round once at the end with ROUND_HALF_UP, sum unrounded values before
  rounding aggregates.
- Match the answer-template key names and nesting exactly; omit zero-valued optional sub-fields only
  where the template allows (e.g. payroll `categories` omits zero categories; `substitute_adjustment`
  only present when a substitute exists).
- Sanity-check internal identities: `annual_total == sum(quarter_totals) == sum(pay_type_totals)`;
  `weekly_total == round(sum(category_totals unrounded))`; `region_reconciliation_variance == 0.0`;
  `sum(per_musician unrounded totals) == weekly_total`.
