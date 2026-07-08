---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops — Reporting / Compensation / Payroll SOP

This group has THREE task families that all read from one remote API and all return a single
JSON object that must conform exactly to the task's `payloads/answer_template.json`:

1. **Branch / regional finance reporting** (income statement, FY comparisons, rankings).
2. **CBA compensation** (current-year summary, and multi-year board forecast).
3. **Theatre weekly payroll** (per-service pay, premiums, guarantees, conflict flags).

The request memo names the domain via fields like `target_branch_id` / `target_region_id`
(finance), `ensemble_id` (+ optional `scenario_id`) (compensation), or `production_id` (payroll).

---

## 0. Reading the task & producing the answer

- **Source of truth = the answer template, not the prose.** Read `answer_template.json` first.
  `required_top_level_keys` is the exact key set the answer object must have (no more, no less).
  `field_types` gives the exact nested shape and which fields are currency vs percent vs integer
  vs string. Match key names byte-for-byte (e.g. `m24_income_statement`, `fy2025_vs_fy2024`).
- **The request memo** (`request_memo.json`) gives the parameters: which branch/region/ensemble/
  production, which periods/years, which scenario. `reporting_focus` / `review_focus` /
  `requested_detail` lists are hints about emphasis; the template is authoritative on shape.
- **Memo `memo_note` fields are distractors.** Phrases like "a draft workbook has background notes
  for Harbor North" or "reconcile against the active operations data" mean: ignore any side notes
  and compute from the LIVE API data only. Do not invent or carry over numbers from a "draft."
- **Rounding (from template descriptions):**
  - Currency → round to **2 decimals**.
  - Percent / ratio / growth / margin fields → round to **4 decimals** (these are stored as
    decimal fractions, e.g. 9.66% → `0.0966`, NOT `9.66`).
  - Counts / ranks → integers.
  - Round only at output; keep full precision through intermediate math.
- **Ordering:** lists use **ascending stable IDs** (branch_id, musician_id, employee_id) unless a
  field name says otherwise (e.g. a `*_rank_desc` integer, or a "top_*"/"bottom_*" id). Conflict
  flag lists are sorted **alphabetically**. `pay_types` follows the rate-book order exactly:
  `["Minimum Weekly Scale","Titled Position Premium","Seniority","Overscale"]`.
- Return ONE JSON object, exactly the template's top-level keys. Do not add commentary keys.

---

## 1. Remote API access

Base URL: `<remote-env-url>` (ALWAYS use this; ignore any `base_url` like
`http://127.0.0.1:8047` inside `payloads/environment_access.json`). All endpoints are HTTP GET.

```
GET /health
GET /api/manifest                         # entity catalog, record_counts, period seed
GET /api/finance/branches                 # branch_id, branch_name, region_id, region_name
GET /api/finance/period-map               # period (M1..M24) -> fiscal_year, month_number, month_name
GET /api/finance/accounts                 # account -> category, display_name, metric_type
GET /api/finance/records[?branch_id=&region=&account=]
GET /api/compensation/rate-book           # scale, seniority bands, title %, business rules
GET /api/compensation/rosters[?ensemble_id=]
GET /api/compensation/scenarios           # dict keyed by scenario_id
GET /api/payroll/rate-book                # service rates, premiums, thresholds, guarantee
GET /api/payroll/productions[?production_id=]   # returns a LIST (take [0] when filtered)
```

Fetch once into files, then compute in code (Python). On this Windows/Git-Bash host write temp
files under the session scratchpad, not `/tmp`. Example:
`curl -s "<remote-env-url>api/finance/records?branch_id=BR-004" -o records.json`

---

## 2. Finance domain (branch & regional reporting)

### Data model
`/api/finance/records` returns one row **per (branch, account)**, each with a `values` map keyed by
period `M1..M24`. There are 12 branches x 14 accounts = 168 rows. Index as
`IDX[branch_id][account] -> {period: value}`.

### Period / fiscal-year convention (from `/api/finance/period-map`)
- **M1..M12 = FY2024**, **M13..M24 = FY2025** (12 calendar months each, Jan..Dec).
- A "close period" like `M24` is the current month; its prior is `M23` (Dec vs Nov FY2025).
- `period_convention` block: `M1_to_M12 = "FY2024"`, `M13_to_M24 = "FY2025"`,
  `current_month`/`prior_month` echo the memo's `close_period`/`prior_period` labels verbatim.

### Account groupings (income statement lines)
From `/api/finance/accounts` (`category` field):
- **revenue** = `product_revenue` + `service_revenue`
- **cogs** = `direct_materials_cogs` + `direct_labor_cogs`
- **gross_margin** = revenue − cogs
- **sga** = `sales_sga` + `admin_sga` + `occupancy_sga`
- **allocations** = `shared_service_allocations`
- **ebitda** = gross_margin − sga − allocations  (= revenue − cogs − sga − allocations)
- **ebitda_margin** = ebitda / revenue (4 dp)

Operating (count) accounts — NOT part of the income statement, used for ratios:
`orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog`.

### Sums over a period set
For a single month, sum the one period. For a fiscal year, sum the 12 monthly values
(M1..M12 for FY2024, M13..M24 for FY2025).

### Ratios (use the fiscal-year AVERAGE of monthly count snapshots, not the sum)
Count accounts are monthly snapshots, so per-headcount/per-customer ratios use the **mean** over
the 12 months of the year:
- `arpu` = FY revenue / (mean monthly `active_customers` over the 12 FY months). (≈ revenue per
  customer; using the monthly mean, not the 12-month sum.)
- `sales_per_labor_headcount` = FY revenue / (mean monthly `labor_headcount` over the 12 FY months).
- Both currency, 2 dp. (Sanity: sales_per_labor_headcount lands in the ~$250k–$300k/employee
  range; if you get ~$24k you summed headcount instead of averaging.)

### Growth / variance
- MoM revenue variance: `amount` = rev(current month) − rev(prior month) (2 dp);
  `pct` = amount / rev(prior month) (4 dp).
- `revenue_growth_pct` = (FY2025 rev − FY2024 rev) / FY2024 rev (4 dp).
- `ebitda_growth_pct` = (FY2025 ebitda − FY2024 ebitda) / FY2024 ebitda (4 dp).

### Regional rollup & branch sets
- Branch→region from `/api/finance/branches` (`region_id`). Regions: REG-NORTH, REG-WEST,
  REG-EAST, REG-SOUTH. `branch_ids` lists are **ascending** branch IDs of that region.
- Region income statement = sum of member-branch income-statement lines (line by line).
- Region `sales_per_labor_headcount` = region FY revenue / (sum over member branches of each
  branch's FY-mean labor_headcount).
- `region_reconciliation_variance` = region total EBITDA − Σ(member-branch EBITDA). By
  construction this **ties to 0.0** (the rollup reconciles); a nonzero value means a math/scope
  error. Report it rounded to 2 dp (normally `0.0`).

### Rankings (compute across ALL 12 branches unless scoped to a region)
- `sales_growth_rank_desc` for the target branch = its 1-based rank when all branches are sorted
  by FY2025-vs-FY2024 revenue growth %, **descending** (rank 1 = highest growth).
- `top_sales_growth_branch_id` = branch with highest revenue growth %.
- `top_arpu_branch_id` = branch with highest FY2025 arpu.
- In a `region_context` block, `ebitda_rank_desc` ranks the **region** among the four regions by
  FY2025 region-total EBITDA, descending (rank 1 = highest region EBITDA), and `fy2025_ebitda` is
  the region TOTAL. (Caveat: if a template instead scopes the rank to branches-within-region,
  re-read the surrounding fields — but when the block carries a region total, rank regions.)
- For regional tasks, `top_ebitda_branch_id` / `bottom_ebitda_branch_id` are the member branches
  with the highest / lowest FY2025 EBITDA.

---

## 3. Compensation domain (CBA summary & forecast)

### Data
- `/api/compensation/rate-book`: `minimum_weekly_scale` (e.g. 2520.0), `pay_types` (fixed order),
  `seniority_weekly` bands (`min_years`,`max_years` inclusive, `weekly_amount`; top band has
  `max_years: null`), `title_premium_pct` (per title, e.g. Concertmaster 0.22, Principal 0.20,
  Assistant/Associate Principal 0.10, Section Lead 0.15), `quarter_weeks` (13 each), and
  `business_rules`. `current_year` is the rate book's current year (e.g. 2026) — use it for the
  `current_year` output field.
- `/api/compensation/rosters?ensemble_id=...`: one row per employee with `title` (may be `null`),
  `years_of_service`, `overscale_weekly`, `combined_overscale_includes_title` (bool),
  `weeks_by_quarter` ({Q1..Q4}), and `notes`.
- `/api/compensation/scenarios`: dict keyed by `scenario_id`; each has `year_plus_1` and
  `year_plus_2` blocks with `mws_growth`, `seniority_growth`, `overscale_growth`,
  `title_pct_multiplier`.

### Per-employee weekly pay components (the four pay types)
For each employee, the weekly amount of each pay type:
- **Minimum Weekly Scale** = `minimum_weekly_scale` (the year's MWS; grown in forecast years).
- **Titled Position Premium** = `title_premium_pct[title] * title_pct_multiplier * MWS`,
  computed on the **same (grown) MWS** for the year. BUT:
  - If `title` is `null` → premium 0.
  - If `combined_overscale_includes_title == true` → premium 0 (the title premium is already
    baked into the overscale amount per side letter; do NOT add it separately). This is rule #2.
- **Seniority** = `seniority_weekly` band amount for the employee's years_of_service (band lookup
  is inclusive on both ends; 0–4 yrs = 0). In forecast, scale by `(1+seniority_growth)`.
- **Overscale** = `overscale_weekly` (per employee). In forecast, scale by `(1+overscale_growth)`.

### Quarter / annual aggregation (use roster weeks, NOT a fixed 13)
For each employee and each pay type: `weekly_amount * weeks_by_quarter[Q]`, summed.
- `quarter_totals[Q]` = sum over employees & pay types for that quarter.
- `annual_pay_type_totals[pay_type]` = sum over employees & quarters for that pay type.
- `annual_total` = sum of all = sum of quarter_totals = sum of annual_pay_type_totals (use this
  as a self-check; all three must agree).
- Rule #1: partial-quarter employees have a `weeks_by_quarter` value ≠ 13 (e.g. `{Q2: 9}`); always
  drive weeks from `weeks_by_quarter`, never assume 13.

### Roster treatment counts
- `roster_count` = number of roster rows for the ensemble.
- `combined_overscale_employee_count` = count of rows with
  `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = count of rows where ANY `weeks_by_quarter` value ≠ 13
  (these rows carry note "Partial-quarter service schedule.").
- `largest_pay_type` = the pay type with the greatest `annual_pay_type_totals` value (typically
  "Minimum Weekly Scale" since MWS dominates).

### Forecast years (board task)
Business rule #3: **add 1 year of service for Year+1 and 2 years for Year+2 before seniority band
lookup.** This can bump employees into higher seniority bands (a major driver of Seniority growth).
- **current** year: base MWS, base seniority bands (no yos add), base overscale, title at base pct.
- **year_plus_1**: MWS = base_MWS·(1+mws_growth₁); seniority weekly ·(1+seniority_growth₁) with
  yos+1 band lookup; overscale ·(1+overscale_growth₁); title pct · title_pct_multiplier₁;
  weeks unchanged.
- **year_plus_2**: apply growth **compounding on top of Year+1**, i.e.
  MWS = base_MWS·(1+g₁)·(1+g₂), seniority/overscale scales multiply across both years, title
  multiplier multiplies across both years, AND yos+2 band lookup. (Compounding gives sensible
  positive YoY growth; applying each scenario block independently to the base instead can yield a
  near-zero Year+2 step because the year_plus_2 rates are similar to year_plus_1 — prefer
  compounding.)
- `annual_totals` = {current, year_plus_1, year_plus_2}; each computed as in §3 aggregation.
- `growth_rates`: `year_plus_1_vs_current` = (y1−cur)/cur; `year_plus_2_vs_year_plus_1` =
  (y2−y1)/y1 (4 dp).
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` = the Year+2 breakdowns.
- `largest_growth_pay_type`: the pay type whose total grows the most from current → Year+2.
  PRIMARY interpretation = largest **absolute dollar** increase (usually Minimum Weekly Scale,
  the dominant line). NOTE the genuine ambiguity: by **percentage** growth the winner is often
  Seniority, because the +2-year band shifts (rule #3) push many employees into higher bands. If
  the template/prose emphasizes a "driver," dollar growth is the safer default; keep the
  percentage reading in mind if results look off.
- Forecast roster-treatment counts (`combined_overscale_employee_count`,
  `partial_quarter_employee_count`) come from the roster as-is (they don't change across years).

---

## 4. Payroll domain (theatre weekly payroll)

### Data
- `/api/payroll/rate-book`: `service_rates` (per service or per hour), `service_time_limits` (hrs),
  `conflict_thresholds` (rehearsal earliest_start / latest_end), `premium_pct`, `weekly_guarantee`,
  and `business_rules`.
- `/api/payroll/productions?production_id=...` returns a **list**; take `[0]`. Each production has
  `week_start`, a `schedule` (services), and a `roster` (musicians).
  - schedule service: `service_id`, `service_type`, `date`, `start_time`, `end_time`,
    `duration_hours`.
  - roster musician: `musician_id`, `name`, `assigned_service_ids`, `instrument`, `doubles` (int),
    booleans `electronic`, `lead`, `principal`, `quartet`, `substitute`, `vacation_eligible`.

### Service base pay (per assigned service)
- **Performance / Audit / Sound Check (1hr/2hr)** = the per-service rate from `service_rates`
  keyed by exact `service_type` string (e.g. "Performance" 260.25, "Audit" 260.25,
  "1hr Sound Check" 80.0, "2hr Sound Check" 142.5).
- **Rehearsal** = hourly: `service_rates["Rehearsal"] * max(duration_hours, 3.0)`
  (three-hour minimum call). Rehearsal is the only hourly category.
- A musician's **base service pay** = sum of base pay over their `assigned_service_ids`.

### Category mapping for `category_totals` and per-musician `categories`
- Base service pay splits into `performance`, `audit`, `rehearsal`, `sound_check` by service type.
- Premiums and adjustments are their own categories: `premium`, `doubles`, `vacation`,
  `guarantee_adjustment`, `substitute_adjustment`. Include a category in a per-musician
  `categories` map only when its amount is nonzero. `substitute_adjustment` appears in the totals
  object only "when applicable."

### Premiums (applied to base service pay, before vacation)
- **premium** (the `premium` category) = base_service_pay × Σ of applicable pct from `premium_pct`:
  `principal_or_lead` 0.15 if `principal` OR `lead`; `quartet` 0.15 if `quartet`; `electronic`
  0.25 if `electronic`; `concertmaster` 0.20 if a concertmaster flag is set (Hamilton-style
  rosters have no concertmaster flag, so it's typically 0). Sum the applicable percentages, then
  multiply once by base.
- **doubles** = base_service_pay × doubles_pct where doubles_pct = `first_double` (0.25) for the
  first extra instrument + `additional_double` (0.10) per each additional. So `doubles=1`→0.25,
  `doubles=2`→0.35, `doubles=3`→0.45. (doubles=0 → no doubles category.)

### Vacation
- `vacation` = `premium_pct["vacation"]` (0.04) × (base_service_pay + premium + doubles), only when
  `vacation_eligible == true`. Vacation is 4% of base service pay PLUS premiums (premium+doubles),
  computed after those premiums and before guarantee.

### Weekly guarantee adjustment
- Applies only to **guaranteed regular players** (treat `substitute == false` as the regular,
  guaranteed player; substitutes get no guarantee) when their **base service pay** is below
  `weekly_guarantee` (e.g. 2082.0).
- `guarantee_adjustment` = `weekly_guarantee − base_service_pay` (top-up to the guarantee), based
  on **base service pay only** (not premiums/vacation). Only add when positive.

### Substitute adjustment
- `substitute_adjustment` only appears when the data/rate-book defines a substitute differential.
  If the rate book has no substitute rate rule (the common case), omit it. Do not fabricate one;
  `substitute == true` simply disqualifies the player from the weekly guarantee.

### Per-musician total & weekly total
- musician total = base + premium + doubles + vacation + guarantee_adjustment
  (+ substitute_adjustment when present).
- `category_totals` = sum of each category across all musicians.
- `weekly_total` = sum of all category totals = sum of per-musician totals (self-check).
- `per_musician` ordered by `musician_id` ascending; each entry has `musician_id`, `name`, `total`,
  and `categories` (nonzero categories only). `top_paid_musician_id` = musician with the max total.

### `service_counts`
- Object mapping `service_type` → count of services of that type in the **schedule** (count
  scheduled services, not musician-assignments).

### Conflict flags (enum, sorted alphabetically)
Evaluate the schedule against `conflict_thresholds` and `service_time_limits`:
- `REHEARSAL_EARLY_START` — a Rehearsal `start_time` earlier than `rehearsal_earliest_start`
  (e.g. before 09:00).
- `REHEARSAL_LATE_END` — a Rehearsal `end_time` later than `rehearsal_latest_end` (e.g. after
  18:30). (Only Rehearsal services trigger the rehearsal start/end flags — a late Performance does
  not.)
- `SERVICE_OVER_TIME_LIMIT` — any service whose `duration_hours` exceeds its
  `service_time_limits[service_type]` (e.g. Rehearsal limit 5.0h, Performance/Audit 3.0h).
- `SOUND_CHECK_DURATION_MISMATCH` — a "1hr Sound Check" whose duration ≠ 1.0h, or a "2hr Sound
  Check" whose duration ≠ 2.0h.
- Emit the set of triggered flags as a sorted (alphabetical), de-duplicated list. Empty list if
  none.

---

## 5. Step-by-step SOP for an unseen task

1. Read `answer_template.json` → record exact `required_top_level_keys` and nested shapes/types.
   Read `request_memo.json` → identify domain + parameters (branch/region/ensemble+scenario/
   production, periods/years). Treat `memo_note` as a distractor; compute from live API only.
2. Pick the domain (finance / compensation / payroll) and fetch the needed endpoints from
   `<remote-env-url>` with `curl` GET (use period-map/accounts/branches as
   reference; rate-books for comp/payroll; scenarios for forecasts).
3. Build indexes (finance: branch→account→{period:value}; comp: roster rows + rate book + scenario;
   payroll: schedule map + roster).
4. Compute the requested figures using the formulas in §2/§3/§4. Carry full precision; aggregate
   over the correct period/quarter/service set.
5. Apply output conventions: currency 2 dp; percent/ratio/growth/margin 4 dp (decimal fraction);
   integers for counts/ranks; ascending stable-ID ordering; alphabetical conflict-flag sorting;
   rate-book pay-type ordering.
6. Self-check: income-statement ebitda = revenue−cogs−sga−allocations; comp annual_total = Σ
   quarters = Σ pay-type totals; payroll weekly_total = Σ categories = Σ per-musician totals;
   region_reconciliation_variance ties to 0.0. Verify every `required_top_level_key` is present and
   no extra keys exist; confirm field types match the template.
7. Emit exactly one JSON object matching the template.

### Common misjudgments to avoid
- Using the wrong fiscal-year mapping (M13..M24 is FY2025, not FY2024).
- Summing monthly headcount/customers for ratios instead of averaging (inflates the denominator,
  gives ~10x-too-small ARPU / sales-per-headcount).
- Forgetting that `combined_overscale_includes_title == true` SUPPRESSES the separate title premium.
- Assuming 13-week quarters for partial-quarter employees instead of reading `weeks_by_quarter`.
- Forgetting the +1/+2 years-of-service band bump in forecasts (drives Seniority growth).
- Applying each scenario `year_plus_N` block to the base independently instead of compounding
  Year+2 on Year+1.
- Rehearsal: forgetting the 3-hour minimum call, or treating it as per-service instead of hourly.
- Doubles: using a flat 25% for doubles≥2 instead of 25% + 10%·(extra−1).
- Vacation: applying 4% to base only instead of base+premiums; or applying it to ineligible
  musicians.
- Guarantee: applying it to substitutes, or comparing total pay instead of base service pay to the
  weekly_guarantee.
- Outputting percentages as whole numbers (9.66) instead of decimal fractions (0.0966).
- Adding extra keys or omitting required keys from the answer object.
