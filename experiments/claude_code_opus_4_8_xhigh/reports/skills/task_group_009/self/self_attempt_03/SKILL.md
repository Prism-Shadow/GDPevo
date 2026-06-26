---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops — Reporting SOP

You produce one `answer.json` per task in three domains: (A) branch/regional **finance** reporting, (B) **compensation** current-year summaries and multi-year forecasts, (C) theatre weekly **payroll** control. Each task ships `prompt.txt` plus `payloads/{environment_access.json, request_memo.json, answer_template.json}`. Everything you need beyond the memo comes from the remote API.

## 0. Universal workflow (do this every time)

1. Read `prompt.txt` for the domain and the human framing.
2. Read `request_memo.json` for the **entity id(s)** (`target_branch_id`, `target_region_id`, `ensemble_id`, `scenario_id`, `production_id`), period fields, and the `*_focus` list (focus lists tell you which computations matter; they do not change the output schema).
3. Read `answer_template.json`. The `required_top_level_keys` list is the **exact** set of top-level keys your object must have (no more, no less). `field_types` gives the nested shape, the enum domains, and the rounding hints. Build your output to match these keys verbatim, in that order.
4. Ignore any `base_url` inside payloads (e.g. `http://127.0.0.1:...`). **Always** use the remote base URL below.
5. Compute with full float precision; round **only at the end**, per the rounding rules in the template.

### Remote API
Base URL: `<remote-env-url>` — all GET, no auth.

| Domain | Endpoints |
|---|---|
| Finance (A) | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` (filters `?branch_id=` `?region=` `?account=`) |
| Compensation (B) | `/api/compensation/rate-book`, `/api/compensation/rosters` (filter `?ensemble_id=`), `/api/compensation/scenarios` |
| Payroll (C) | `/api/payroll/rate-book`, `/api/payroll/productions` (filter `?production_id=`) |

`/api/manifest` lists entity ids (12 branches BR-001..012; ensembles ENS-CEDAR/MAPLE/OAK/REDWOOD; productions PROD-*). Fetch the **whole** records set (`/api/finance/records` unfiltered = 168 rows = 12 branches × 14 accounts) when you need region rollups or cross-branch rankings; filter by `branch_id` only for single-branch work.

### Rounding & ordering (from the templates — apply uniformly)
- Currency → **2 decimals**.
- Percent / ratio / growth / margin fields → **4 decimals**, expressed as a **decimal fraction** (e.g. 9.66% → `0.0966`, not `9.66`). Margins like ebitda_margin and ARPU-style ratios follow the same rule (ratios 4dp; ARPU and sales/headcount are currency → 2dp).
- Lists of ids → **ascending stable id order** unless a `rank` field says otherwise. `per_musician` → order by `musician_id`. `conflict_flags` → sorted alphabetically. Pay-type lists → the rate-book `pay_types` order.
- Round with banker-safe care: keep raw floats through the whole calc, then `round(x, 2)` / `round(x, 4)` once.

---

## A. Finance reporting (Tasks like 001 branch close, 004 regional view)

### A.1 Data model
`/api/finance/records` rows: `{branch_id, branch_name, region_id, account, values}` where `values` maps period label `M1`..`M24` to a number. 14 accounts per branch:
- revenue: `product_revenue`, `service_revenue`
- cogs: `direct_materials_cogs`, `direct_labor_cogs`
- sga: `sales_sga`, `admin_sga`, `occupancy_sga`
- allocations: `shared_service_allocations`
- operating **counts**: `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`

### A.2 Period / fiscal-year convention (from `/api/finance/period-map`)
- **M1–M12 → FY2024** (Jan..Dec 2024). **M13–M24 → FY2025** (Jan..Dec 2025).
- So `period_convention` for a close at M24 is: `M1_to_M12="FY2024"`, `M13_to_M24="FY2025"`, `current_month`=memo `close_period`, `prior_month`=memo `prior_period`.
- A single "close period" (e.g. M24) is **one month**; a fiscal-year view sums the 12 months of that FY.

### A.3 Income-statement line definitions (sum the listed accounts over the chosen period set)
```
revenue       = product_revenue + service_revenue
cogs          = direct_materials_cogs + direct_labor_cogs
gross_margin  = revenue - cogs
sga           = sales_sga + admin_sga + occupancy_sga
allocations   = shared_service_allocations
ebitda        = gross_margin - sga - allocations           (i.e. revenue - cogs - sga - allocations)
ebitda_margin = ebitda / revenue                            (ratio, 4dp)
```
For a **month** statement use periods=`["M24"]`; for an **FY** statement use the 12 periods of that FY. For a **region** statement, sum the per-branch statements across the region's branches (region rollup = simple additive sum; `region_reconciliation_variance` between the region total and the sum of its branches is therefore **0.00** — use it as a self-check).

### A.4 Derived metrics
- **MoM revenue variance**: `amount = rev(current_month) - rev(prior_month)`, `pct = amount / rev(prior_month)` (4dp).
- **revenue_growth_pct / ebitda_growth_pct (FY-over-FY)**: `(FY2025 - FY2024) / FY2024` (4dp).
- **ARPU**: `FY revenue / average monthly active_customers`, where average = `sum(active_customers over the 12 FY months) / 12`. Currency, 2dp. (active_customers is a monthly **stock**, so average it — do NOT divide by the 12-month sum.)
- **sales_per_labor_headcount**: `FY revenue / average monthly labor_headcount` (= `sum(labor_headcount)/12`). Currency, 2dp. Same stock-averaging logic as ARPU.
  - ⚠ This is the single biggest interpretation risk in finance tasks. The operating accounts are per-month counts. The defensible KPI is **revenue per head per year** = revenue ÷ (sum of monthly counts / 12). If a result looks ~12× too small, you mistakenly divided by the 12-month sum instead of the average.

### A.5 Rankings & regional context
- **Region branch set**: branches whose `region_id` equals the target region, ascending by `branch_id`. Regions: REG-NORTH {BR-001,002,003}, REG-WEST {BR-004,005,006}, REG-EAST {BR-007,008,011}, REG-SOUTH {BR-009,010,012}.
- **EBITDA rank (region context)**: rank the **target region** among all 4 regions by FY2025 EBITDA, **descending** (1 = highest). `ebitda_rank_desc` is an integer.
- **Branch EBITDA ranking (regional task)**: within the region, `top_ebitda_branch_id` = branch with highest FY2025 EBITDA, `bottom_ebitda_branch_id` = lowest.
- **Branch sales-growth rank** (`branch_rankings.sales_growth_rank_desc`): rank the target branch among **all 12 branches** by FY2025-vs-FY2024 revenue growth %, descending (1 = fastest growth). `top_sales_growth_branch_id` = highest-growth branch overall; `top_arpu_branch_id` = highest-ARPU branch overall (using the A.4 ARPU definition).
- Resolve `branch_name` / `region_name` from `/api/finance/branches`.

### A.6 "Active operations data" caveat (memo_note)
Memo notes warn that draft workbooks may carry stale/background figures (e.g. "background notes for Harbor North"). **Ignore narrative figures in the memo**; the API `records` are the source of truth. Reconcile to the API, never to prose.

---

## B. Compensation (Tasks like 002 current-year summary, 005 multi-year forecast)

### B.1 Rate book (`/api/compensation/rate-book`)
- `current_year` (e.g. 2026), `minimum_weekly_scale` (MWS, e.g. 2520.0), `pay_types` order = `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`.
- `quarter_weeks` Q1..Q4 = 13 each (a "fixed" 13-week quarter) — **but** business rule #1 says: when a roster row lists partial weeks, use the roster's `weeks_by_quarter`, not the fixed 13.
- `seniority_weekly` bands: 0–4→0, 5–9→48, 10–14→82, 15–19→126, 20–24→170, 25+→215 (per week).
- `title_premium_pct`: Concertmaster 0.22, Principal 0.20, Section Lead 0.15, Assistant Principal 0.10, Associate Principal 0.10.
- Business rules: (1) use roster quarter weeks when partials listed; (2) if `combined_overscale_includes_title` is true, do **not** add a titled premium separately for that employee (the overscale already embeds it); (3) for forecasts, add +1 year of service for Year+1 and +2 for Year+2 **before** assigning seniority bands.

### B.2 Roster (`/api/compensation/rosters?ensemble_id=...`)
Each row: `{employee_id, title (or null), years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter:{Q1..Q4}, notes}`. `roster_count` = number of rows.

### B.3 Per-employee weekly rates, then × weeks per quarter
For each employee and each quarter q with weeks `w = weeks_by_quarter[q]`:
```
Minimum Weekly Scale[q]     = MWS * w
Titled Position Premium[q]  = (title ? title_premium_pct[title] * MWS : 0) * w
                              → 0 if title is null OR combined_overscale_includes_title is true
Seniority[q]                = seniority_weekly(years_of_service) * w
Overscale[q]                = overscale_weekly * w
```
- **quarter_totals[q]** = sum over employees of all four pay types for that quarter.
- **annual_pay_type_totals[pt]** = sum over employees and quarters.
- **annual_total** = sum of all pay-type totals = sum of all quarter totals (must reconcile — self-check).
- **largest_pay_type** = pay type with the max annual total (almost always "Minimum Weekly Scale").

### B.4 Roster treatment counts (reviewed before sending)
- `combined_overscale_employee_count` = count of rows with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = count of rows where any quarter's weeks ≠ 13.

### B.5 Forecast scenarios (`/api/compensation/scenarios`, key = memo `scenario_id`)
Each scenario has `year_plus_1` and `year_plus_2` blocks with `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`. Forecast years are **compounded from the current base**:
```
current   : MWS, overscale, seniority(yos),   title_pct                       (no growth)
year_plus_1: MWS*(1+mws_g1), overscale*(1+ov_g1), seniority(yos+1)*(1+sen_g1),
             title_pct * title_mult1
year_plus_2: MWS*(1+mws_g1)*(1+mws_g2), overscale*(1+ov_g1)*(1+ov_g2),
             seniority(yos+2)*(1+sen_g1)*(1+sen_g2), title_pct * title_mult1 * title_mult2
```
- Seniority for a forecast year: **first** bump years_of_service (+1 / +2), re-look-up the band, **then** apply the seniority growth factor.
- Title premium = `title_premium_pct[title] * MWS_of_that_year * cumulative_title_multiplier`. Because the premium is a % of MWS, when `title_pct_multiplier == 1.0` the title line grows at exactly the MWS rate.
- Keep weeks_by_quarter as given (partials persist across forecast years).
- `annual_totals` = {current, year_plus_1, year_plus_2}; `growth_rates` = {year_plus_1_vs_current, year_plus_2_vs_year_plus_1} as 4dp decimal fractions.
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` are the Year+2 breakdowns.
- `combined_overscale_employee_count` / `partial_quarter_employee_count` same as B.4.

### B.6 `largest_growth_pay_type` (ambiguous — decide explicitly)
The pay type with the largest growth from **current → Year+2**. There are two readings; they can differ:
- **By percentage growth** (recommended default): Seniority often wins because year-of-service bumps push employees into higher bands (a large % jump on a small base).
- **By absolute dollar delta**: Minimum Weekly Scale usually wins (largest base).
Pick **percentage growth** unless the prompt explicitly says "largest dollar/absolute increase." State which you used if borderline. The value must be one of the four enum pay-type strings.

---

## C. Theatre weekly payroll (Tasks like 003)

### C.1 Rate book (`/api/payroll/rate-book`)
- `service_rates`: Performance 260.25, Audit 260.25 (per service); `1hr Sound Check` 80.0, `2hr Sound Check` 142.5 (per service); Rehearsal 58.75 (per **hour**).
- Rehearsal: hourly with a **3-hour minimum call** → `hours = max(duration_hours, 3.0)`, pay = 58.75 × hours.
- `premium_pct`: concertmaster 0.20, principal_or_lead 0.15, quartet 0.15, electronic 0.25, first_double 0.25, additional_double 0.10, vacation 0.04.
- `service_time_limits`: Performance 3.0, Audit 3.0, `1hr Sound Check` 1.0, `2hr Sound Check` 2.0, Rehearsal 5.0.
- `conflict_thresholds`: rehearsal_earliest_start "09:00", rehearsal_latest_end "18:30".
- `weekly_guarantee`: 2082.0.
- Business rules: rates/premiums from rate book; rehearsal hourly w/ 3h min; Performance/Audit/Sound-check per service; **premiums applied to base service pay before vacation**; doubles = 25% first extra instrument + 10% each additional; vacation = 4% of (base + premiums) when `vacation_eligible`; **weekly guarantee adjustment only for guaranteed regular players when base service pay < weekly_guarantee**.

### C.2 Production (`/api/payroll/productions?production_id=...`) → list with one element
`{production_id, title, week_start, roster[], schedule[]}`. Schedule rows: `{service_id, service_type, date, start_time, end_time, duration_hours}`. Roster rows: `{musician_id, name, instrument, assigned_service_ids[], doubles (int), electronic, principal, lead, quartet, substitute, vacation_eligible}`. There is **no** per-musician `guaranteed`/`regular`/`concertmaster` field.

### C.3 Per-musician pay (sum over their `assigned_service_ids`)
1. **Base service pay** by service type, accumulated into output categories:
   - Performance → `performance` (260.25 each)
   - Audit → `audit` (260.25 each)
   - 1hr/2hr Sound Check → `sound_check` (80 / 142.5)
   - Rehearsal → `rehearsal` (58.75 × max(duration,3))
   - `base = sum of all the above`.
2. **Premiums** (on `base`), split across two output categories:
   - `premium` = base × (principal_or_lead if principal **or** lead) + base × (quartet if quartet) + base × (electronic if electronic). Sum the applicable pct's. **concertmaster** premium exists in the rate book but **no roster flag triggers it** in this data — do not apply it unless a concertmaster flag appears.
   - `doubles` = base × doubles_pct, where doubles_pct(n) = 0 if n≤0, 0.25 if n==1, else 0.25 + 0.10×(n−1).
3. **Vacation** (`vacation` category): if `vacation_eligible`, 0.04 × (base + premium + doubles). Else 0.
4. **Guarantee adjustment** (`guarantee_adjustment`): only if `substitute == false` (substitutes are NOT guaranteed regulars) AND `base < weekly_guarantee (2082)` → add `(2082 − base)`. "Base service pay" here = base service rates only (before premiums).
5. **Substitute adjustment** (`substitute_adjustment`): the data/rate book define **no** substitute pay formula. The `substitute` flag's only effect is to **exclude** that musician from the guarantee. So `substitute_adjustment` is **0 / omitted** unless a future rate book adds an explicit substitute rule. The template marks it "when applicable" — include it only when nonzero.
6. **musician total** = sum of all their category amounts.

### C.4 Aggregation & output shape
- `service_counts`: object mapping each `service_type` string to the count of services of that type in the schedule.
- `category_totals`: sum each category across all musicians. Categories: performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment, substitute_adjustment (include substitute_adjustment only when nonzero).
- `weekly_total`: sum of all category totals (= sum of all musician totals — self-check).
- `per_musician`: list ordered by `musician_id`, each `{musician_id, name, total, categories}` where `categories` includes **only nonzero** category names → currency.
- `top_paid_musician_id`: musician with the highest `total`.

### C.5 Conflict flags (`conflict_flags`, sorted alphabetically; enum below)
Scan the **schedule** (per service) and raise a flag (deduplicated) when:
- `REHEARSAL_EARLY_START`: a Rehearsal `start_time` < 09:00.
- `REHEARSAL_LATE_END`: a Rehearsal `end_time` > 18:30.
- `SERVICE_OVER_TIME_LIMIT`: any service whose `duration_hours` **strictly exceeds** its `service_time_limits` value (e.g. a 5.5h Rehearsal vs limit 5.0; a 2.5h Audit vs limit 3.0 does **not** flag). Use strict `>` — a duration exactly at the limit is fine.
- `SOUND_CHECK_DURATION_MISMATCH`: a Sound Check whose `duration_hours` ≠ its nominal hours (1hr→1.0, 2hr→2.0).
Compare times by converting "HH:MM" to minutes.

---

## D. Common misjudgments (checklist before you submit)
- Used the remote base URL, not the localhost `base_url` in payloads.
- FY mapping: M1–M12 = FY2024, M13–M24 = FY2025 (do not assume calendar-year column names).
- EBITDA = revenue − cogs − sga − allocations (allocations are subtracted, not part of cogs).
- ARPU & sales-per-headcount divide by the **average** monthly count (sum/12), not the 12-month sum.
- Percent fields are decimal fractions at 4dp (0.0966), not whole-number percents (9.66).
- Comp: skip the title premium for `combined_overscale_includes_title` employees; use roster `weeks_by_quarter` for partials; bump years_of_service before band lookup in forecasts.
- Comp forecast growths **compound** across years; seniority growth applies on top of the band bump.
- Payroll: rehearsal has a 3h minimum; doubles is its own category separate from `premium`; vacation is on base+premiums; guarantee only for non-substitutes below 2082; no substitute_adjustment formula exists (flag-only); `SERVICE_OVER_TIME_LIMIT` is strict `>`.
- Output keys exactly match `required_top_level_keys` (order included); per_musician sorted by id; conflict_flags sorted; pay-type lists in rate-book order; ids ascending.
- Reconcile self-checks: sum(quarter_totals)=annual_total; sum(category_totals)=weekly_total=sum(musician totals); region EBITDA = sum of branch EBITDAs (variance 0.00).
- Ignore narrative numbers in `memo_note`; the API is the source of truth.

## E. Step-by-step SOP for an unseen task
1. Identify domain from prompt + which endpoints `environment_access.json` lists.
2. Pull entity ids and period/scenario fields from `request_memo.json`.
3. Read `answer_template.json` → list the exact output keys and each field's shape/rounding/enum.
4. Fetch the needed endpoints (rate-book/scenarios/period-map first; then the entity records/roster/production; fetch all finance records when rankings/rollups are required).
5. Compute with the formulas above at full precision.
6. Round (currency 2dp, ratio/percent 4dp), order lists (ascending ids / by-id / alphabetical / rank), and assemble the object with keys in template order.
7. Run the reconciliation self-checks; fix any mismatch before returning.
8. Return exactly one JSON object — nothing else.
