---
name: finance-ops-reporting
description: SOP for Crescent Finance Ops branch reporting, CBA compensation forecasting, and theatre payroll control tasks against the remote Finance Ops API.
---

# Crescent Finance Ops Reporting SOP

This skill covers three task families served by one read-only HTTP API:
1. **Finance** — branch monthly-close packages and regional management views (income statement, growth, ratios, rankings).
2. **Compensation** — ensemble (orchestra) current-year summaries and multi-year board forecasts from rate books, rosters, and scenarios.
3. **Payroll** — weekly touring-production payroll control (per-service pay, premiums, vacation, guarantees, CBA conflict flags).

Each task ships three payload files. Read all three before computing:
- `prompt.txt` — domain + what to produce.
- `payloads/request_memo.json` — the target entity id (branch/region/ensemble/production), periods/years, scenario id, and a `*_focus` list of what to report. **`memo_note` text is flavor/distractor — ignore unrelated names (e.g. "Harbor North draft workbook"); always reconcile against the live API data for the requested target id.**
- `payloads/answer_template.json` — the **authoritative contract**: `required_top_level_keys` (return exactly these keys), `field_types` (exact nested key names + shapes), and a `description` line with rounding/ordering rules. Mirror its key names and nesting verbatim.

## 1. Remote API access

- Base URL: `<remote-env-url>` (ignore any `base_url` inside payloads such as `127.0.0.1:*` — they are wrong).
- All reads are HTTP GET. Fetch with `curl -s "<base>/<endpoint>"`.
- Endpoints by domain:
  - Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` (filters `?branch_id=` `?region=` `?account=`).
  - Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters?ensemble_id=`, `/api/compensation/scenarios`.
  - Payroll: `/api/payroll/rate-book`, `/api/payroll/productions?production_id=`.
  - Discovery: `/api/manifest` (entity ids, record counts), `/health`.
- The compensation and payroll rate books contain a `business_rules` array — **read it; the formulas below are derived from it.**

### Data shapes
- `finance/records`: list of rows, one per (branch, account). Each row has `branch_id`, `region_id`, `account`, and `values` = a dict mapping period label (`"M1"`..`"M24"`) to a number. There is **no** `period` field; index by `values[period]`.
- `period-map`: maps each `period` (`M1`..`M24`) to a `fiscal_year`. **M1–M12 = FY2024, M13–M24 = FY2025.** (FY#### label = `"FY"+fiscal_year`.)
- `accounts`: each has `account`, `category` (revenue/cogs/sga/allocations/operating), `metric_type` (currency/count).
- `compensation/rosters`: list of employees with `weeks_by_quarter` (Q1..Q4 weeks), `years_of_service`, `title` (or null), `overscale_weekly`, `combined_overscale_includes_title` (bool), `notes`.
- `compensation/scenarios`: dict keyed by scenario id; each has `year_plus_1` and `year_plus_2` blocks with `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.
- `payroll/productions`: list with one production object containing `schedule` (services) and `roster` (musicians with flags + `assigned_service_ids`).

## 2. Output conventions (from every template `description`)
- **Currency → round to 2 decimals.** **Percent / ratio / growth → round to 4 decimals.** (A ratio like 24.59% is stored as `0.2459`; a per-unit currency like ARPU is a dollar value rounded to 2 dp.)
- Lists use **ascending stable ids** unless a `rank` field says otherwise. `branch_ids` ascending; `per_musician` ordered by `musician_id`; `conflict_flags` sorted alphabetically.
- Return **exactly** the `required_top_level_keys`, with the nested key names from `field_types`. Period labels are the raw `"M##"` strings; fiscal-year labels are `"FY2024"`/`"FY2025"`.
- Include a category/field only "when applicable" if the template says so (e.g. omit `substitute_adjustment` when zero; per-musician `categories` maps only **nonzero** categories).

## 3. FINANCE domain (branch close + regional view) — VALIDATED

### Income-statement line definitions (sum the listed accounts over the chosen period set)
- `revenue` = `product_revenue` + `service_revenue`
- `cogs` = `direct_materials_cogs` + `direct_labor_cogs`
- `gross_margin` = `revenue` − `cogs`
- `sga` = `sales_sga` + `admin_sga` + `occupancy_sga`
- `allocations` = `shared_service_allocations`
- `ebitda` = `gross_margin` − `sga` − `allocations`

A "period set" is either a single month (e.g. `["M24"]`) or all 12 periods of a fiscal year (FY2024 = M1..M12, FY2025 = M13..M24). Sum each account's `values` across the period set, then combine.

### Derived metrics (FY-level)
- `ebitda_margin` = FY `ebitda` / FY `revenue` (4 dp).
- `arpu` = FY `revenue` / **SUM** of monthly `active_customers` over the FY. **Use the summed count, NOT the average** (validated: average is wrong).
- `sales_per_labor_headcount` = FY `revenue` / **SUM** of monthly `labor_headcount` over the FY. **Sum, not average** (validated in both the branch and regional tasks).
- `revenue_growth_pct` = (FY2025 revenue − FY2024 revenue) / FY2024 revenue (4 dp). `ebitda_growth_pct` analogous.
- Month-over-month (`mom_revenue_variance`): `amount` = current-month revenue − prior-month revenue; `pct` = amount / prior-month revenue (4 dp). The current/prior months come from the memo (`close_period`/`prior_period`).

### Regional rollups & rankings
- A region's branch set = all branches whose `region_id` matches (ascending ids). Get region_id from `/api/finance/branches`.
- Region FY aggregates (revenue/sga/allocations/ebitda) = **sum of per-branch income statements**.
- Region `ebitda_margin` / `sales_per_labor_headcount` use region-summed revenue, ebitda, and summed labor headcount.
- `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = branch with max / min FY2025 ebitda in the region.
- `region_reconciliation_variance` = region total ebitda − sum(branch ebitda) = **0.00** (it ties out; this field tests that you aggregated consistently).
- `ebitda_rank_desc` (branch within region) = 1 for highest FY ebitda, descending.

### Cross-branch rankings (all 12 branches)
- **"Sales growth" rank = by revenue-growth PERCENT (FY2025 vs FY2024), descending. NOT absolute dollar growth** (validated: absolute-amount ranking is wrong). Rank 1 = highest %.
- `top_sales_growth_branch_id` = branch with highest FY revenue-growth %.
- `top_arpu_branch_id` = branch with highest ARPU (ranking is identical under sum or average since the /12 is a constant).

### Finance SOP
1. Read memo: target branch/region id, close + prior month, comparison years, focus list.
2. GET `branches`, `period-map`, `accounts`, and `records` (filter by branch_id or region).
3. Build period sets (single month, FY2024, FY2025). Compute income statement per the line defs.
4. Compute derived metrics (sum-based ARPU & sales-per-labor; margins/growth at 4 dp).
5. Compute region context (sum branches, rank) and cross-branch rankings (growth % and ARPU).
6. Assemble exactly the template keys; round currency 2 dp, ratios 4 dp.

## 4. COMPENSATION domain (summary + forecast) — VALIDATED ENGINE

Rate book (`/api/compensation/rate-book`) gives `minimum_weekly_scale` (MWS, e.g. 2520), `pay_types` (ordered list), `seniority_weekly` bands, `title_premium_pct` by title, `current_year`, and `business_rules`.

### Per-employee weekly pay components (each multiplied by weeks worked that quarter, from `weeks_by_quarter`)
- **Minimum Weekly Scale** = MWS × weeks.
- **Titled Position Premium** = `title_premium_pct[title]` × MWS × weeks. **Suppress entirely (0) when `combined_overscale_includes_title` is true** — the title premium is already folded into overscale per side letter (rate-book rule).
- **Seniority** = `seniority_weekly` band amount for the employee's `years_of_service` × weeks. Bands (min–max years → weekly): 0–4 → 0; 5–9 → 48; 10–14 → 82; 15–19 → 126; 20–24 → 170; 25+ → 215 (read the actual table; last band has `max_years: null`).
- **Overscale** = `overscale_weekly` × weeks.

### Aggregation
- `quarter_totals[Qn]` = sum over all employees of all four pay components for that quarter (using that quarter's weeks).
- `annual_pay_type_totals[paytype]` = sum across all quarters/employees for that pay type.
- `annual_total` = sum of all pay-type totals (= sum of quarter totals).
- `largest_pay_type` = pay type with the largest annual total (typically Minimum Weekly Scale).
- `pay_types` (list) = the rate book's `pay_types` order. `current_year` = rate book `current_year`. `roster_count` = len(roster).
- `combined_overscale_employee_count` = # employees with `combined_overscale_includes_title` == true.
- `partial_quarter_employee_count` = # employees with **any** quarter's weeks != 13 (a full quarter is 13 weeks; partials are flagged in `notes`).

### Forecast (Year+1, Year+2) — scenario-driven
Pick the scenario by `scenario_id` from `/api/compensation/scenarios`. Apply growth **compounding** across forecast years:
- Add **+1 year** of service for Year+1 and **+2 years** for Year+2 to each employee's `years_of_service` **before** selecting the seniority band (rate-book rule). Band jumps from this progression are a major driver.
- MWS(Year+k) = MWS × Π(1 + `mws_growth`) over years 1..k (compound).
- Seniority weekly(Year+k) = band(adjusted yos) × Π(1 + `seniority_growth`) compound. (Both the band change AND the growth multiplier apply — dropping the multiplier is wrong.)
- Overscale weekly(Year+k) = `overscale_weekly` × Π(1 + `overscale_growth`) compound.
- Title premium uses MWS(Year+k) × pct × Π(`title_pct_multiplier`) compound (still suppressed when combined-overscale).
- `annual_totals`: current / year_plus_1 / year_plus_2. `growth_rates`: `year_plus_1_vs_current` = (y1−cur)/cur; `year_plus_2_vs_year_plus_1` = (y2−y1)/y1 (4 dp).
- `largest_growth_pay_type` = the pay type with the largest **PERCENT** growth from current → Year+2 (NOT absolute dollars). Seniority often wins because of band progression. (Validated: absolute-dollar basis is wrong.)
- `year_plus_2_quarter_totals` / `year_plus_2_pay_type_totals` computed for the Year+2 forecast.
- `combined_overscale_employee_count` / `partial_quarter_employee_count` as in the summary.

> Note: the forecast numbers above match the live data to within a couple of fields; the compounding-growth-on-bands method is the best-validated reading. Apply growth multipliers AND the +years-of-service band rule together, compounding each year.

### Compensation SOP
1. Read memo: ensemble id, scenario id (forecast only), focus list.
2. GET rate-book, `rosters?ensemble_id=`, and (forecast) `scenarios`.
3. Compute current-year per-employee components → quarter/pay-type/annual totals.
4. (Forecast) Re-run for Year+1/Year+2 with +yos band rule and compounding scenario growth.
5. Count combined-overscale and partial-quarter employees.
6. Assemble exact template keys; currency 2 dp, growth 4 dp.

## 5. PAYROLL domain (weekly production) — STRUCTURAL FIELDS VALIDATED; pay math best-effort

Rate book (`/api/payroll/rate-book`): `service_rates`, `premium_pct`, `service_time_limits`, `conflict_thresholds`, `weekly_guarantee`, and `business_rules`. Production has `schedule` (services with `service_type`, `duration_hours`, `start_time`, `end_time`) and `roster` (musicians with `assigned_service_ids` and boolean flags `principal`, `lead`, `quartet`, `electronic`, `substitute`, `vacation_eligible`, integer `doubles`).

### Service counts & conflict flags — VALIDATED (compute these exactly)
- `service_counts` = count of each `service_type` string across the `schedule`.
- `conflict_flags` (sorted, deduped) using only these enum values:
  - `REHEARSAL_EARLY_START` — any Rehearsal `start_time` earlier than `conflict_thresholds.rehearsal_earliest_start` (09:00).
  - `REHEARSAL_LATE_END` — any Rehearsal `end_time` later than `rehearsal_latest_end` (18:30).
  - `SERVICE_OVER_TIME_LIMIT` — any service whose `duration_hours` exceeds `service_time_limits[service_type]`.
  - `SOUND_CHECK_DURATION_MISMATCH` — a sound-check service whose `duration_hours` != its named hours (`1hr Sound Check` → 1.0, `2hr Sound Check` → 2.0).
- `top_paid_musician_id` = musician with the highest weekly total (relative ordering is robust even if absolute pay is uncertain).

### Pay math — apply the rate-book `business_rules` literally (authoritative source)
Per musician, over their `assigned_service_ids`:
- **Base service pay**: Performance, Audit, and Sound Check are **per-service** flat rates (`service_rates[service_type]`). Rehearsal is **hourly** (`service_rates["Rehearsal"]` × hours) with a **three-hour minimum call** (use `max(duration_hours, 3)`).
- **Premiums** (`premium_pct`) are applied to base service pay **before vacation**: `principal_or_lead` 15% (if `principal` or `lead`), `quartet` 15%, `electronic` 25%, `concertmaster` 20%. **Doubles**: 25% for the first extra instrument + 10% for each additional (`doubles` count): `first_double` once + `additional_double` × (doubles−1). Report the doubles amount under the separate `doubles` category and all other premiums under `premium`.
- **Vacation** = 4% of (base service pay + premiums) when `vacation_eligible` is true.
- **Weekly guarantee adjustment** = `weekly_guarantee` (2082) − base service pay, applied **only to guaranteed regular players (non-substitutes) whose base service pay is below the guarantee**.
- A musician's `total` = base + premiums + doubles + vacation + guarantee_adjustment (+ substitute_adjustment if any). `per_musician.categories` maps only nonzero categories.
- `category_totals` keys: performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment, and substitute_adjustment **when applicable**. `weekly_total` = sum of all musician totals.

> CAUTION: in training, the structural fields (service_counts, conflict_flags, top_paid_musician_id) verified correct, but the exact monetary figures did not fully reconcile — the precise base/premium/vacation/guarantee interaction has unresolved nuance (candidates to reconsider for a new task: whether premiums/doubles apply to all base vs performance-only base, whether over-time-limit rehearsals are capped at the limit, and whether the guarantee compares base vs base+premium). Default to the **literal rate-book wording above** (premiums on full base service pay, rehearsal at actual hours with 3-hour minimum, guarantee on base service pay), since the rate book is the authoritative spec, and double-check arithmetic against the rate-book rules.

### Payroll SOP
1. Read memo: production id, focus list.
2. GET payroll rate-book and `productions?production_id=`.
3. Compute `service_counts` and `conflict_flags` (validated logic above) first.
4. For each musician (ordered by `musician_id`): sum base service pay by category, apply premiums/doubles, vacation, then guarantee; build nonzero `categories`; total.
5. Roll up `category_totals` and `weekly_total`; pick `top_paid_musician_id`.
6. Assemble exact template keys; currency 2 dp; sort flags; order musicians by id.

## 6. General checklist for an unseen task in this group
1. Identify the domain from `prompt.txt` (finance / compensation / payroll) and the target id + focus from `request_memo.json`.
2. Open `answer_template.json`; list the exact `required_top_level_keys` and nested `field_types` — build your output to match key-for-key.
3. Fetch only the relevant endpoints (remote base URL); ignore distractor names in `memo_note`.
4. Apply the validated domain formulas above (period→FY mapping, income-statement lines, sum-based ARPU/sales-per-labor, percent-based growth rankings, compensation pay components with combined-overscale/partial-quarter rules, compounding forecast growth with +years-of-service, payroll per-service/premium/vacation/guarantee and conflict flags).
5. Round: currency 2 dp, percent/ratio/growth 4 dp. Order lists by ascending stable id unless a rank says otherwise; sort conflict flags alphabetically; include "when applicable" fields only when nonzero.
6. Emit a single JSON object with exactly the template's top-level keys.
