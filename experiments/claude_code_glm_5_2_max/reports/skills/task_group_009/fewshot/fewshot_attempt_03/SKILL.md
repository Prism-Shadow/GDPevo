# Crescent Finance Ops — Solver Skill

Transferable workflow for the Crescent Arts Collective Finance Ops task group. covers four task families that share one remote API: (1) branch close reporting, (2) compensation current-year summary, (3) compensation board forecast, (4) weekly payroll, plus the regional/company dashboard variant of (1). Every numeric convention below was confirmed by reproducing the staged train gold answers against the live remote data.

## 0. Environment

- **Live remote base URL: `<remote-env-url>`**. Always use this. The staged `payloads/environment_access.json` base_url is already set to this host; ignore any `127.0.0.1` placeholder in notes. Do NOT call any `/api/judge` endpoint.
- All endpoints return JSON. Fetch with `curl -s "<url>" | python3 -m json.tool`.
- Public endpoints:
  - `GET /api/manifest` — entity roster (branches, ensembles, productions), record counts, seed.
  - `GET /api/finance/branches` — authoritative branch→region map + region_name.
  - `GET /api/finance/period-map` — M-period → fiscal_year/month map.
  - `GET /api/finance/accounts` — account → category + metric_type.
  - `GET /api/finance/records` — financial time series; supports `?branch_id=`, `?region=`, `?account=`.
  - `GET /api/compensation/rate-book` — comp engine parameters (current_year, MWS, pay types, seniority bands, title %, quarter weeks, business rules).
  - `GET /api/compensation/rosters?ensemble_id=` — per-employee roster rows.
  - `GET /api/compensation/scenarios` — per-scenario year_plus_1 / year_plus_2 growth drivers.
  - `GET /api/payroll/rate-book` — service rates, premium %, time limits, guarantee, conflict thresholds.
  - `GET /api/payroll/productions?production_id=` — production roster + schedule.
- Working habit: fetch each reference file once into `/tmp`, then compute with python. Keep full float precision through the whole calculation; round only the reported fields at the end.

## 1. Shared conventions

### 1.1 Period map (M-period → fiscal year)
The period map maps each `M1..M24` to a fiscal year:
- **`M1`–`M12` → FY2024** (Jan–Dec 2024)
- **`M13`–`M24` → FY2025** (Jan–Dec 2025)

General rule: M1–M12 = the earlier fiscal year, M13–M24 = the next fiscal year. For any fiscal-year rollup, sum the 12 M-periods that the period-map assigns to that fiscal_year. **Never assume a calendar-year split — always read `/api/finance/period-map`.**

For a close-period `M{n}`: `prior_period = M{n-1}`. The "current fiscal year" = the fiscal_year of the close period; the "prior fiscal year" = that year − 1. The `period_convention` object reports `M1_to_M12` and `M13_to_M24` as `FY####` strings, plus `current_month` / `prior_month` as the raw period labels.

### 1.2 Account categories (from `/api/finance/accounts`)
Each account has a `category` and a `metric_type`. The income statement uses only currency-category accounts; operating accounts are counts used for ratios.

| category | accounts | metric_type | role |
|---|---|---|---|
| `revenue` | `product_revenue`, `service_revenue` | currency | IS revenue line |
| `cogs` | `direct_materials_cogs`, `direct_labor_cogs` | currency | IS cogs line |
| `sga` | `sales_sga`, `admin_sga`, `occupancy_sga` | currency | IS sga line |
| `allocations` | `shared_service_allocations` | currency | IS allocations line |
| `operating` | `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog` | **count** | ratios only |

**Operating counts are NOT currency and never enter revenue/cogs/sga/allocations/ebitda.** They are consumed only by ARPU and sales-per-labor-headcount.

### 1.3 Income statement construction (per branch, per period set)
For a given branch and a set of M-periods (a single month, or the 12 months of a fiscal year), sum each account's values over those periods, then roll up by category:
- `revenue` = Σ revenue-category accounts
- `cogs` = Σ cogs-category accounts
- `gross_margin` = revenue − cogs
- `sga` = Σ sga-category accounts
- `allocations` = Σ allocations-category accounts
- `ebitda` = gross_margin − sga − allocations  (= revenue − cogs − sga − allocations)

Records carry `region_id` and `branch_name` redundantly; filter on `branch_id`.

### 1.4 Ratios
- `arpu` (per branch/region, FY) = FY revenue ÷ Σ `active_customers` over the FY periods.
- `sales_per_labor_headcount` (per branch/region, FY) = FY revenue ÷ Σ `labor_headcount` over the FY periods. For a region this is region revenue ÷ **sum** of branch labor_headcount (not an average of branch ratios).
- `ebitda_margin` = ebitda ÷ revenue (same period set).
- `revenue_growth_pct` = (fy_cur revenue − fy_prev revenue) ÷ fy_prev revenue.
- `ebitda_growth_pct` = (fy_cur ebitda − fy_prev ebitda) ÷ fy_prev ebitda.
- For MoM: `amount` = current_month revenue − prior_month revenue; `pct` = amount ÷ prior_month revenue.

### 1.5 Rounding
- **Currency fields: 2 decimals, round half up.** Percent/ratio/decimal-percent fields: **4 decimals, round half up.** Use `decimal.Decimal(x).quantize(Decimal('0.01'), ROUND_HALF_UP)` (or `'0.0001'` for ratios). Plain Python `round()` can give banker's-rounding surprises (e.g. 3253.125 must become 3253.13, not 3253.12).
- Compute every intermediate at full precision; round each reported field independently at the end. Per-musician/category/total fields are each rounded from the unrounded computation (do not sum already-rounded category values to get a total — recompute from unrounded).
- Count fields are plain integers.

### 1.6 Ranking & list ordering
- "rank desc" / "rank_desc" = descending rank where **1 = best (highest)**. `sales_growth_rank_desc`, `ebitda_rank_desc`, etc. all mean 1 = top.
- Lists of branch_ids are **ascending stable IDs** (e.g. `["BR-004","BR-005","BR-006"]`).
- `top_*` = the branch with the maximum value; `bottom_*` = the minimum.
- Range for rank comparisons is `ALL` branches (rankings in `branch_rankings` are across all 12 branches, not within region) unless the field is explicitly scoped (e.g. `region_context.ebitda_rank_desc` ranks the **region** among all regions — see SOP 1).
- If an exact tie occurs in a ranking, break by ascending branch_id; this is a sensible default (ties are unlikely with the real data).

### 1.7 Source-of-truth caveat (stale memos)
Request memos and "draft workbook" notes may contain background prose (e.g. a stale region assignment, a wrong period label, a hint that a branch left a region). **The active operations data is authoritative.** Region membership comes from `/api/finance/branches` `region_id`. Period→FY comes from `/api/finance/period-map`. Do not exclude a branch from its region, reassign it, or alter the period convention based on memo prose — reconcile against the live endpoints.

### 1.8 Regions (from `/api/finance/branches`)
12 branches across 4 regions (seed 9009):
- REG-NORTH: BR-001 Aurora North, BR-002 Granite Bay, BR-003 Lakeview
- REG-WEST: BR-004 Harbor North, BR-005 Pine Hill, BR-006 Mesa Ridge
- REG-EAST: BR-007 Riverbend, BR-008 Old Port, BR-011 Summit Yard
- REG-SOUTH: BR-009 Beacon South, BR-010 Coral Point, BR-012 Valley Forge

BR-011 is in REG-EAST (a stale memo may claim otherwise — ignore it). Always derive this list from `/api/finance/branches` for the test seed; do not hardcode.

---

## 2. SOP — Branch close reporting (family 1)

Inputs: `target_branch_id`, `close_period` (e.g. M24), `prior_period` (e.g. M23).

1. Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records?branch_id=<target>` (or all records and filter). Identify target branch name and region from `branches`.
2. Build `period_convention`: `M1_to_M12` = `FY2024`, `M13_to_M24` = `FY2025`; `current_month` = close_period; `prior_month` = prior_period.
3. **m24_income_statement** (or `<close_period>_income_statement`): single-month IS for the close period (§1.3 with that one period).
4. **mom_revenue_variance**: `amount` = close-period revenue − prior-period revenue; `pct` = amount ÷ prior-period revenue (4dp).
5. **fy2025_vs_fy2024**: compute the full IS (§1.3) for both FY2025 (M13–M24) and FY2024 (M1–M12). In `fy2025` include `ebitda_margin`, `arpu`, `sales_per_labor_headcount` (§1.4). Top-level `revenue_growth_pct` and `ebitda_growth_pct` compare FY2025 vs FY2024. (If the close period sits in a different fiscal year, use current_fiscal_year vs prior_fiscal_year per the period map; the template key names follow the fiscal years in scope.)
6. **region_context**: list the target branch's region branches (ascending). `fy2025_ebitda` = sum of FY2025 ebitda across all branches in that region. `ebitda_rank_desc` = the rank of the **target branch's region** among all 4 regions by FY2025 ebitda (desc, 1 = highest). (This is a region-level rank, not the branch's rank within the region — confirmed: BR-004/REG-WEST reports rank 3 because REG-WEST is the 3rd-highest region by FY2025 ebitda.)
7. **branch_rankings** (across ALL 12 branches):
   - `sales_growth_rank_desc` = rank of the TARGET branch by FY2025 revenue growth pct (desc, 1 = best).
   - `top_sales_growth_branch_id` = branch with the max FY2025 revenue growth pct.
   - `top_arpu_branch_id` = branch with the max FY2025 ARPU (FY2025 revenue ÷ FY2025 active_customers).
8. Round per §1.5. Output keys exactly as in the answer template.

### Pitfalls (family 1)
- `region_context.ebitda_rank_desc` is the **region's** rank among regions, not the branch's rank within its region.
- `branch_rankings` is global (all 12 branches), not regional.
- ARPU and sales_per_labor_headcount use FY2025 (current FY) operating counts summed over the 12 periods — not the single close-month count.
- Do not let a memo's "draft workbook" notes change region membership or the M→FY convention.

---

## 3. SOP — Regional / company dashboard (family 4)

Inputs: `target_region_id`, comparison years (e.g. [2024, 2025]).

1. Fetch branches + records. Derive the region's branch set from `/api/finance/branches` (ascending branch_ids).
2. **fy2024** and **fy2025** blocks: for each fiscal year, sum `revenue`, `sga`, `allocations`, `ebitda` across **all branches in the region** (§1.3 per branch, then add). The fy-block the memo calls "current" also includes `ebitda_margin` (= region ebitda ÷ region revenue) and `sales_per_labor_headcount` (= region revenue ÷ Σ branch `labor_headcount` for that FY).
3. `revenue_growth_pct` = (fy2025 revenue − fy2024 revenue) ÷ fy2024 revenue (4dp).
4. `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch in the region with max / min FY2025 ebitda.
5. `region_reconciliation_variance` = region FY2025 ebitda − Σ(branch FY2025 ebitda). This is a sanity check and is **0.0** (the region total is built by summing the branches).
6. Round per §1.5.

**Company dashboard variant**: if a task asks for a company-wide view (all branches / all regions), apply the same field logic but across all 12 branches (or equivalently sum all 4 regions). `branch_ids` becomes all branch_ids ascending; reconciliation variance stays 0.0; top/bottom and rankings scope to the company. The same IS/ratio/ranking conventions (§1) apply unchanged.

### Pitfalls (family 4)
- `sales_per_labor_headcount` at region level = region revenue ÷ **sum** of branch labor_headcount (not the mean of per-branch ratios).
- `region_reconciliation_variance` is structurally 0.0; a non-zero value means you double-counted or missed a branch.
- Derive the region's branch set from the branches endpoint, not from a memo.

---

## 4. Compensation engine — shared (families 2 & 3a)

### 4.1 Rate book (`/api/compensation/rate-book`) — confirmed values
- `current_year`: **2026**
- `minimum_weekly_scale` (MWS): **2520.00** per week
- `pay_types` (use this order): `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `quarter_weeks`: Q1=Q2=Q3=Q4 = **13** (default; per-employee `weeks_by_quarter` overrides — see §4.4)
- `title_premium_pct`: Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15
- `seniority_weekly` bands (by years_of_service):
  - 0–4 yrs → 0.00
  - 5–9 → 48.00
  - 10–14 → 82.00
  - 15–19 → 126.00
  - 20–24 → 170.00
  - 25+ (max_years null) → 215.00
- Business rules (authoritative):
  1. Use roster `weeks_by_quarter`, not the fixed 13-week quarter, when partial-quarter employees are listed.
  2. If `combined_overscale_includes_title` is true, **do not add a Titled Position Premium separately** for that employee — their `overscale_weekly` already bundles the title premium.
  3. For forecast years, add one year of service for Year+1 and two years for Year+2 before assigning the seniority band.

### 4.2 Per-employee weekly pay (one quarter)
For one employee in one quarter with `w` weeks that quarter:
- **Minimum Weekly Scale** = `MWS × w` = 2520 × w
- **Titled Position Premium** = `title_premium_pct[title] × MWS × w` (a % of the MWS base) — **skip** when `combined_overscale_includes_title` is true, or when `title` is null/None (untitled employees pay 0).
- **Seniority** = `seniority_weekly_band(years_of_service) × w`
- **Overscale** = `overscale_weekly × w`
- Sum these four across all employees and all four quarters → pay-type totals and quarter totals.

### 4.3 Roster treatment counts
- `combined_overscale_employee_count` = number of roster rows with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = number of roster rows where **any** quarter in `weeks_by_quarter` is less than the rate-book `quarter_weeks` for that quarter (i.e. < 13 here).
- `roster_count` = number of roster rows.

### 4.4 Quarter weeks
Always use the employee's own `weeks_by_quarter[Qn]` as `w`. Do not substitute the rate-book 13. Partial-quarter employees simply contribute fewer weeks (their pay is proportionally lower).

---

## 5. SOP — Compensation current-year summary (family 2)

Inputs: `ensemble_id`.

1. Fetch `/api/compensation/rate-book` and `/api/compensation/rosters?ensemble_id=<id>`.
2. For each employee × quarter, compute the four pay-type amounts (§4.2) using the employee's `weeks_by_quarter`. Skip Titled Position Premium when `combined_overscale_includes_title` is true or title is null.
3. **quarter_totals** (`Q1`..`Q4`): sum all pay across all employees for each quarter.
4. **annual_pay_type_totals**: sum each pay type across all employees × all quarters.
5. **annual_total** = sum of the four annual pay-type totals (= sum of quarter_totals).
6. **largest_pay_type** = the pay type with the maximum annual total (enum: one of the four pay_types).
7. **combined_overscale_employee_count**, **partial_quarter_employee_count**, **roster_count** per §4.3.
8. **pay_types** = the ordered list from the rate book.
9. **current_year** = rate-book `current_year` (2026). **ensemble_id** = input.
10. Round all currency to 2dp. Output keys exactly as in the template.

### Pitfalls (family 2)
- For `combined_overscale_includes_title` employees: still pay MWS, Seniority, and Overscale — only the Titled Position Premium is dropped.
- `largest_pay_type` is by **annual total amount** (here always Minimum Weekly Scale), NOT by growth rate.
- Use roster weeks, not 13. The partial-quarter count and the pay both depend on the true weeks.

---

## 6. SOP — Compensation board forecast (family 3)

Inputs: `ensemble_id`, `scenario_id` (e.g. `case_maple_board`), forecast years = current / year_plus_1 / year_plus_2.

### 6.1 Scenario drivers (`/api/compensation/scenarios`)
Each scenario has `year_plus_1` and `year_plus_2` blocks, each with:
- `mws_growth`, `overscale_growth`, `seniority_growth` (per-pay-type growth rates)
- `title_pct_multiplier` (multiplier on the title premium percentage)

### 6.2 Forecast computation
Growth is **cumulative and compound** from the current year. For each pay type, the year-N value = current-year value × Π(1 + growth_k for k=1..N). Years of service advance (+1 for Y+1, +2 for Y+2) for the seniority **band** lookup before applying the seniority growth rate.

- **current**: base computation (§4.2, with the employee's actual `years_of_service`). Title premium uses the base `title_premium_pct`. MWS=2520.
- **year_plus_1**: for each employee/quarter,
  - MWS = 2520 × (1 + y1.mws_growth) × w
  - Title premium = `title_premium_pct[title] × (y1.title_pct_multiplier) × 2520 × (1 + y1.mws_growth) × w`  (skip if combined_overscale or untitled)
  - Seniority = `seniority_band(years_of_service + 1) × (1 + y1.seniority_growth) × w`
  - Overscale = `overscale_weekly × (1 + y1.overscale_growth) × w`
- **year_plus_2**: cumulative multipliers from current = `(1+y1.g)×(1+y2.g) − 1` for each growth rate; `title_pct_multiplier` = `y1.title_pct_multiplier × y2.title_pct_multiplier`; years_of_service + 2 for the seniority band. I.e.
  - MWS = 2520 × (1+y1.mws)×(1+y2.mws) × w
  - Title premium = `title_premium_pct[title] × (y1.tmult × y2.tmult) × 2520 × (1+y1.mws)×(1+y2.mws) × w`
  - Seniority = `seniority_band(years_of_service + 2) × (1+y1.sen)×(1+y2.sen) × w`
  - Overscale = `overscale_weekly × (1+y1.os)×(1+y2.os) × w`

Note `title_premium_pct` itself stays at the rate-book value; only the `title_pct_multiplier` factors compound it. Confirmed scenario `case_maple_board` reproduces: current 4232653.60, Y+1 4390313.80, Y+2 4545741.02; Y+2 quarter totals Q1 1129891.58, Q2/Q3/Q4 1138616.48; Y+2 pay-type totals MWS 3914775.18, TPP 320833.74, Seniority 190829.80, Overscale 119302.29.

### 6.3 Outputs
- **annual_totals**: `current`, `year_plus_1`, `year_plus_2` (each = sum of all pay across all employees × all quarters for that forecast year).
- **growth_rates**: `year_plus_1_vs_current` = year_plus_1_total ÷ current_total − 1; `year_plus_2_vs_year_plus_1` = year_plus_2_total ÷ year_plus_1_total − 1 (4dp). Compute from unrounded totals.
- **year_plus_2_quarter_totals**: Q1..Q4 sums in the year_plus_2 frame.
- **year_plus_2_pay_type_totals**: the four pay-type sums in the year_plus_2 frame.
- **largest_growth_pay_type**: the pay type with the largest **percentage growth from current to year_plus_2** (current→Y+2). This is a growth-RATE comparison, not absolute dollars — Seniority typically wins because band reassignment compounds with the seniority growth rate. (Largest absolute-dollar growth is usually MWS; that is NOT this field.)
- **combined_overscale_employee_count**, **partial_quarter_employee_count**: same as current-year (roster attributes, unaffected by the forecast).
- **scenario_id**, **ensemble_id**: echo inputs.
- Round currency 2dp, growth rates 4dp.

### Pitfalls (family 3)
- Growth compounds cumulatively from current: Y+2 = current × (1+y1)×(1+y2), not current × (1+y2) alone.
- Reassign the seniority band using years_of_service + N for year+N before applying the (compounded) seniority growth rate. Crossing a band boundary (e.g. 9→10 yrs) jumps the weekly amount AND the growth rate still applies on top.
- `title_pct_multiplier` compounds multiplicatively (y1×y2) and multiplies the **percentage**, while the title premium **amount** also rides the grown MWS base.
- `largest_growth_pay_type` = largest percentage growth current→Y+2 (not Y+1→Y+2, not absolute).
- `combined_overscale_includes_title` rule still applies in forecast years (skip separate title premium; grow overscale by overscale_growth).
- The four scenario ids available are `case_cedar_negotiation`, `case_maple_board`, `case_oak_sensitivity`, `case_redwood_baseline`. Fetch the one named in the memo; do not assume.

---

## 7. SOP — Weekly payroll (family 5)

Inputs: `production_id`.

### 7.1 Rate book (`/api/payroll/rate-book`) — confirmed values
- `service_rates`: 1hr Sound Check 80.00, 2hr Sound Check 142.50, Audit 260.25, Performance 260.25, Rehearsal 58.75
- `service_time_limits`: 1hr Sound Check 1.0, 2hr Sound Check 2.0, Audit 3.0, Performance 3.0, Rehearsal 5.0 (hours)
- `premium_pct`: additional_double 0.10, concertmaster 0.20, electronic 0.25, first_double 0.25, principal_or_lead 0.15, quartet 0.15, vacation 0.04
- `weekly_guarantee`: 2082.00
- `conflict_thresholds`: rehearsal_earliest_start `09:00`, rehearsal_latest_end `18:30`
- Business rules:
  1. Rehearsal pay is **hourly with a 3-hour minimum call** (pay = `max(3.0, duration_hours) × 58.75`).
  2. Performance, Audit, and Sound-Check rates are **per service** (flat, ignore duration for pay; duration still feeds conflict checks).
  3. Premiums apply to the musician's **base service pay before vacation**.
  4. Doubles premium: 25% for the first extra instrument, 10% for each additional extra instrument → `% = 0.25 + 0.10×(doubles−1)` for `doubles ≥ 1`, else 0.
  5. Vacation = 4% of (base service pay + premium + doubles) when `vacation_eligible` is true.
  6. Weekly guarantee adjustment applies **only to regular (non-substitute) players** when base service pay is below `weekly_guarantee`.

### 7.2 Roster flags → premiums
Payroll roster fields: `assigned_service_ids, doubles, electronic, instrument, lead, musician_id, name, principal, quartet, substitute, vacation_eligible`. Premiums triggered by flags:
- `electronic` true → electronic 25%
- `principal` true OR `lead` true → principal_or_lead 15% (apply once even if both true)
- `quartet` true → quartet 15%
- (concertmaster 20% exists in the book but has no roster flag in observed productions — apply only if a roster field explicitly marks it.)
These premium percentages **sum** (additive, not multiplicative) and apply to base service pay. Doubles is a separate additive percentage (formula above), reported in its own `doubles` category — it is NOT part of `premium`.

### 7.3 Per-musician computation
For each musician, build their **base service pay** from the services in `assigned_service_ids`:
- Performance: count × 260.25
- Audit: count × 260.25
- Sound check: count × (1hr rate 80 or 2hr rate 142.50) by service_type
- Rehearsal: Σ `max(3.0, duration_hours) × 58.75` over their rehearsal services

For **substitute musicians** (`substitute: true`): performance services are paid at **1.5× the rate** in the `performance` category (i.e., performance = 1.5 × count × 260.25), and an additional **`substitute_adjustment` = 0.5 × count × 260.25** is added as its own category. (Net: substitutes earn 2× on performances — the 1.5× in `performance` plus a separate 0.5× `substitute_adjustment`. The 0.5× loading applies to **performance services only**; audit, rehearsal, and sound-check are at standard rates.) The base used for premium/doubles/vacation is the **grossed-up** service pay (performance at 1.5× + other service pay). Substitutes get **no** weekly guarantee.

Then:
- `premium` = (Σ applicable premium %) × base
- `doubles` = (0.25 + 0.10×(doubles−1) if doubles≥1 else 0) × base
- `vacation` = 0.04 × (base + premium + doubles) if `vacation_eligible` else 0  (guarantee is NOT included in the vacation base)
- `guarantee_adjustment` = max(0, 2082.00 − base) for **regular** musicians whose base < 2082; 0 for substitutes and for regulars with base ≥ 2082. (Base here = service pay at standard 1× for regulars; guarantee does NOT receive premium or vacation.)
- per-musician `total` = base + premium + doubles + vacation + guarantee_adjustment (+ substitute_adjustment for subs)
- per-musician `categories`: include only the nonzero categories (performance, audit, rehearsal, sound_check as base components; premium, doubles, vacation, guarantee_adjustment, substitute_adjustment as applicable).

### 7.4 Outputs
- **service_counts**: object mapping each service_type present in the schedule → integer count of services of that type (across the whole schedule, not per musician). Keys are the schedule's `service_type` strings (e.g. `"1hr Sound Check"`, `"Audit"`, `"Performance"`, `"Rehearsal"`).
- **category_totals**: sum across musicians of each category (`performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, and `substitute_adjustment` when any substitute is present). Compute from unrounded per-musician values, then round.
- **weekly_total**: sum of all category_totals (= sum of per-musician totals), rounded from unrounded.
- **per_musician**: ordered by `musician_id` ascending. Each entry: `musician_id`, `name`, `total`, `categories` (nonzero category→currency).
- **top_paid_musician_id**: musician_id with the max total (ties → ascending musician_id).
- **conflict_flags**: sorted alphabetically, drawn from this enum (omit any that don't fire):
  - `REHEARSAL_EARLY_START` — any rehearsal with `start_time < 09:00`
  - `REHEARSAL_LATE_END` — any rehearsal with `end_time > 18:30`
  - `SERVICE_OVER_TIME_LIMIT` — any service with `duration_hours > service_time_limits[service_type]` (strictly greater; equal is OK)
  - `SOUND_CHECK_DURATION_MISMATCH` — any `1hr Sound Check` with `duration_hours ≠ 1.0`, or any `2hr Sound Check` with `duration_hours ≠ 2.0`
- **production_id**: echo input.

Confirmed against `PROD-HAMILTON-26`: weekly_total 14357.36; service_counts {1hr Sound Check:1, Audit:1, Performance:4, Rehearsal:2}; conflict_flags ["REHEARSAL_EARLY_START","SERVICE_OVER_TIME_LIMIT"] (S01 rehearsal starts 08:45 < 09:00; S07 rehearsal 5.5h > 5.0h limit; S02 1hr sound check duration 1.0 = OK so no mismatch flag).

### Pitfalls (family 5)
- Rehearsal pay is **hourly with a 3-hr minimum**, based on `duration_hours` — not a flat per-service rate. Other service types are flat per-service.
- Substitute handling is the trickiest part: `performance` category = 1.5× the performance base, AND `substitute_adjustment` = 0.5× the performance base is added separately (both count in the total). Premium/doubles/vacation use the 1.5×-grossed base. Substitutes get no guarantee.
- `SERVICE_OVER_TIME_LIMIT` uses `duration_hours` strictly greater than the limit (5.0h rehearsal is OK; 5.5h is not).
- `SOUND_CHECK_DURATION_MISMATCH` compares the sound-check's actual `duration_hours` to its nominal (1.0 for "1hr Sound Check", 2.0 for "2hr Sound Check").
- Vacation base = base + premium + doubles (NOT including guarantee). Guarantee is added after vacation and earns no premium/vacation.
- `principal_or_lead` 15% applies once if principal OR lead is true (do not double-count if both).
- Doubles `0` → no doubles premium; doubles `1` → 25%; doubles `2` → 35%; doubles `3` → 45%.
- conflict_flags must be sorted alphabetically; per_musician must be ordered by musician_id.

---

## 8. Cross-family reminders

- Always read the request memo's `request_id` prefix to identify the family: `BR_CLOSE_*` → family 1; `REGIONAL_VIEW_*` → family 4; `COMP_CURRENT_*` → family 2; `COMP_FORECAST_*` → family 3; `PAYROLL_REVIEW_*` → family 5. The answer template's `required_top_level_keys` is the contract — produce exactly those keys, nothing extra.
- Fetch the live remote data; do not rely on memo-embedded numbers. Recompute everything.
- Round currency 2dp half-up, ratios/percent 4dp half-up, from unrounded intermediates.
- Operating accounts (orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog) are counts — never sum them into currency line items.
- Region/branch membership and the M→FY map come from the live endpoints, not memos.
- Rank "desc" = 1 is best; lists of IDs are ascending; conflict flags are alphabetical; per_musician is by musician_id ascending.
