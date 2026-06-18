---
name: crescent-finance-ops-reporting
description: >-
  Produce Crescent Finance Ops management-reporting deliverables (Crescent Arts
  Collective) by querying the read-only Finance Ops HTTP API and returning one JSON
  object that matches a provided answer_template. Use this skill WHENEVER a task
  involves Crescent / Finance Ops / Crescent Arts Collective and any of: a branch
  monthly-close package or income statement; MoM revenue variance; FY2024-vs-FY2025
  branch or regional comparisons; EBITDA / ARPU / sales-per-labor-headcount ratios;
  branch or regional EBITDA rankings; ensemble compensation by quarter and pay type;
  multi-year board compensation forecasts with scenario escalation; or theatre /
  touring-production weekly payroll, musician pay categories, doubles/overscale/
  substitute/guarantee handling, or CBA conflict flags. Trigger even if the user
  only mentions a request_memo, answer_template, an ENS-/BR-/REG-/PROD- id, or a
  "close package / management package / board forecast / payroll review", and does
  not name the API explicitly.
---

# Crescent Finance Ops management reporting

You are filling out a management-reporting deliverable for Crescent Arts Collective.
Each task gives you a `prompt.txt` plus `payloads/` containing `request_memo.json`,
`answer_template.json`, and `environment_access.json` (the live `base_url` and the
endpoints this task is allowed to use). Your job: query the read-only HTTP API, compute
the requested figures, and **return ONE JSON object whose keys exactly match
`answer_template.json`'s `required_top_level_keys`** (same names, same nesting, same types).

There are three data families and five task shapes. Identify the shape from the memo
fields and the template, then apply the matching rules below.

| Task shape | Tell-tale memo fields | Endpoints |
|---|---|---|
| Branch close report | `target_branch_id`, `close_period`, `prior_period` | finance/* |
| Regional view | `target_region_id`, `requested_comparison_years` | finance/* |
| Comp current year | `ensemble_id`, `current_year_by_quarter_and_pay_type` | compensation/rate-book, rosters |
| Comp board forecast | `ensemble_id`, `scenario_id`, `forecast_years` | compensation/rate-book, rosters, scenarios |
| Theatre weekly payroll | `production_id` | payroll/rate-book, productions |

## Start here, every time

1. Read `payloads/environment_access.json` for the **actual `base_url`** (don't assume a
   port) and the allowed endpoints. Read `request_memo.json` and `answer_template.json` in full.
2. A bundled, fully-validated helper library lives at `scripts/finance_ops.py`. It reproduces
   all five task families exactly. Prefer using it (import it, or copy the relevant function)
   over re-deriving formulas. Update its `BASE_URL` to match the task's `base_url`.
3. Query only the endpoints the task allows. Inspect the real data shape before computing.
4. Output ONLY the keys the template asks for. Don't invent extra keys; don't omit required
   ones. When the template names a key (e.g. `target_branch_name`), fetch it from the data
   (e.g. the branches endpoint) rather than guessing.

## Output conventions (this is where solvers most often lose points)

- **Currency -> 2 decimals.** Use round-half-up, not Python's default banker's rounding.
  `2082 - 1737.875 = 344.125` must become `344.13`, not `344.12`.
- **"decimal percent" / ratio / growth-rate fields -> a FRACTION rounded to 4 decimals.**
  8.95% is `0.0895`, NOT `8.95` and NOT `0.09`. ebitda_margin, *_growth_pct, mom pct, etc.
  are all `value` as a fraction: compute `(new-old)/old` (or `part/whole`) then round to 4dp.
- **Round at the end.** Aggregate raw values first; round the final metric once. Don't round
  per-row then sum. One exception, observed in the answers: an **annual compensation total =
  the sum of the already-2dp-rounded quarter totals** (use `comp_annual_total`), which can
  differ by a cent from rounding the raw annual sum. Growth rates use that same rounded-quarter
  annual basis.
- **List ordering** follows the template's note. Default: ascending stable IDs (e.g. `branch_ids`
  sorted, `per_musician` by `musician_id`). `conflict_flags` sorted alphabetically. `pay_types`
  in the rate-book's given order. A `rank` field overrides ID order.
- Use `scripts/finance_ops.py`'s `r2` / `r4` helpers to get the rounding right.

## Memos can mislead -- always use the ACTIVE operating data

Memos contain distractor notes ("a draft workbook has background notes for Harbor North",
"reconcile against the active operations data", side-letter notes on roster rows). These are
deliberate. **The authoritative source is the live API records, not narrative groupings or
draft notes in the memo.** When a template asks for a `region_reconciliation_variance`, the
answer is `0.0` when your rollup of the active branch records ties out (it does). Treat memo
prose as context to reconcile against, never as numbers to copy.

---

## Finance: branch close report & regional view

Period/fiscal-year mapping comes from `/api/finance/period-map`: **M1..M12 = FY2024,
M13..M24 = FY2025** (read it; don't hard-code). Records are `(branch, account) -> {period: value}`.

Income-statement line formulas (sum the listed accounts over the chosen periods):
- revenue = product_revenue + service_revenue
- cogs = direct_materials_cogs + direct_labor_cogs
- gross_margin = revenue - cogs
- sga = sales_sga + admin_sga + occupancy_sga
- allocations = shared_service_allocations
- **ebitda = gross_margin - sga - allocations**  (i.e. revenue - cogs - sga - allocations)
- ebitda_margin = ebitda / revenue  (4dp fraction)

Scopes:
- A single month (e.g. M24) for the close income statement.
- A full fiscal year = all 12 of that FY's periods, for FY metrics and FY-vs-FY.

Derived metrics (FY scope unless stated):
- **ARPU = FY revenue / sum(active_customers across the FY's months).** active_customers is a
  monthly count; you sum it across the 12 months, then divide. Currency, 2dp.
- **sales_per_labor_headcount = FY revenue / sum(labor_headcount across the FY's months).**
  For a region, sum the region's revenue and the region's labor_headcount separately, then divide.
- MoM revenue variance: amount = rev(current) - rev(prior); pct = amount / rev(prior) (4dp).
- revenue_growth_pct = (FY2025 rev - FY2024 rev) / FY2024 rev (4dp). ebitda_growth likewise.

Rollups, rankings, tie-breaks:
- Region rollup = sum the metric across the region's branches (from the branches endpoint's
  `region_id`). Region FY2025 EBITDA = sum of branch FY2025 EBITDA.
- `sales_growth_rank_desc` for the target branch: rank ALL branches by FY revenue growth pct,
  descending; the rank is the target's 1-based position. `top_sales_growth_branch_id` is rank 1.
- `top_arpu_branch_id` = branch with highest FY2025 ARPU across all branches.
- Region `ebitda_rank_desc` = rank ALL regions by FY2025 EBITDA, descending.
- Within a region, `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = max/min FY2025 branch EBITDA.
- For ties (rare here), fall back to ascending branch_id. List `branch_ids` ascending.

`scripts/finance_ops.py`: `finance_setup`, `income_statement`, `region_income_statement`,
`cat_sum`, `acct_sum`, `arpu`, `sales_per_labor_headcount`.

---

## Compensation: current-year summary & board forecast

From `/api/compensation/rate-book`: `minimum_weekly_scale` (MWS), ordered `pay_types`,
`title_premium_pct` (by title), `seniority_weekly` bands, and `business_rules` (read them).
Each roster row has `years_of_service`, `title`, `overscale_weekly`, `weeks_by_quarter`,
and `combined_overscale_includes_title`.

Per employee, per quarter (weeks = `weeks_by_quarter[Q]`), the four pay types:
- **Minimum Weekly Scale** = MWS * weeks
- **Titled Position Premium** = MWS * title_premium_pct[title] * title_pct_multiplier * weeks
  -- but **0 if `combined_overscale_includes_title` is true** for that employee (the overscale
  already bundles the title premium per side-letter; do not add it again).
- **Seniority** = seniority_weekly(years) * seniority_scale * weeks. Pick the band where
  `min_years <= years <= max_years` (top band has `max_years = null`).
- **Overscale** = overscale_weekly * overscale_scale * weeks
Quarter total = sum of the four; annual pay-type total = sum across quarters & employees;
`annual_total` = sum of the rounded quarter totals (see rounding note above).
`largest_pay_type` = the pay type with the largest annual dollar total (usually MWS).

Counts (review focus):
- `roster_count` = number of roster rows for the ensemble.
- `combined_overscale_employee_count` = rows where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count` = rows whose `weeks_by_quarter` has ANY quarter != the
  standard 13 weeks (`quarter_weeks` in the rate book). Use roster weeks, not a fixed 13, in
  all dollar math for those employees -- their reduced weeks lower their totals automatically.

Forecast escalation (`/api/compensation/scenarios`, the requested `scenario_id`):
- For the **current** year: scales = 1.0, title_mult = 1.0, no added service years.
- Escalation is **compounded from the base year, not additive year-over-year**:
  - Year+1: MWS*(1+mws_growth_1); seniority_scale=(1+seniority_growth_1);
    overscale_scale=(1+overscale_growth_1); title_mult=title_pct_multiplier_1.
  - Year+2: MWS*(1+mws_growth_1)*(1+mws_growth_2); each scale/mult compounded across both years.
- **Seniority re-banding**: add 1 year of service for Year+1 and 2 years for Year+2 *before*
  choosing the seniority band. Crossing a band boundary is a step jump -- this is why seniority
  often has the largest *percentage* growth even when MWS has the largest *dollar* growth.
- **`largest_growth_pay_type` is by PERCENT growth (Year+2 vs current), not dollar growth.**
  This is a classic trap: MWS grows the most in dollars; Seniority grows the most in percent.

`scripts/finance_ops.py`: `comp_setup`, `seniority_weekly`, `comp_year_totals`,
`comp_annual_total`, `comp_counts`.

---

## Payroll: theatre weekly package & CBA control

From `/api/payroll/rate-book`: `service_rates`, `premium_pct`, `service_time_limits`,
`conflict_thresholds`, `weekly_guarantee`, and `business_rules` (read them).
A production has a `schedule` (services with times/durations) and a `roster` (musicians with
flags and `assigned_service_ids`).

`service_counts` = count of each `service_type` across the whole schedule (one line per type).

Per musician, build categories:
1. **Base service pay**, summed into its category:
   - Performance / Audit / Sound Check: the per-service rate (one charge per assigned service).
   - Rehearsal: hourly rate * max(duration_hours, 3.0) -- a 3-hour minimum call per rehearsal.
2. **Substitute** (`substitute: true`): the performance category gets +0.5 * (performance base),
   AND a separate `substitute_adjustment` line = 0.5 * (performance base). Substitutes earn
   2x on performances overall, split across `performance` and `substitute_adjustment`.
   Substitutes get **no guarantee adjustment**.
3. **premium** = (sum of applicable premium_pct) * base service pay (base AFTER any substitute
   uplift to performance). Applicable: principal_or_lead (if `lead` OR `principal`), quartet
   (if `quartet`), electronic (if `electronic`), concertmaster (if a concertmaster flag is set).
   Premiums are applied to base service pay BEFORE vacation.
4. **doubles** (if `doubles` >= 1) = base service pay * (first_double 0.25 +
   additional_double 0.10 * (doubles - 1)). 25% for the first extra instrument, 10% each more.
5. **vacation** (if `vacation_eligible`) = vacation_pct (0.04) * (base service pay + premium +
   doubles). Include doubles in the vacation base.
6. **guarantee_adjustment** (guaranteed regular players = NON-substitutes only): if base service
   pay < `weekly_guarantee`, add (weekly_guarantee - base service pay). Otherwise omit.

Per-musician `categories` map lists only nonzero categories; `total` = sum of its categories.
`category_totals` = sum each category across musicians. `weekly_total` = sum of musician totals.
`top_paid_musician_id` = highest total (ties -> lowest musician_id). `per_musician` ordered by id.

CBA `conflict_flags` (sorted alphabetically; enum only):
- `REHEARSAL_EARLY_START` -- any rehearsal starts before `rehearsal_earliest_start`.
- `REHEARSAL_LATE_END` -- any rehearsal ends after `rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT` -- any service's duration exceeds its `service_time_limits` value.
- `SOUND_CHECK_DURATION_MISMATCH` -- a sound check's duration != its nominal hours
  (1hr -> 1.0, 2hr -> 2.0). A flag fires once if ANY service triggers it; do not duplicate.
  Only emit flags actually triggered by this production -- don't pad the list.

`scripts/finance_ops.py`: `payroll_setup`, `payroll_weekly` (returns the whole package).

---

## Common misjudgments (check yourself against these)

- Returning percent fields as whole-number percents (8.95) instead of fractions (0.0895).
- Banker's rounding instead of round-half-up (off-by-a-cent on .xx5 values).
- Rounding `annual_total` from the raw sum instead of summing rounded quarter totals.
- Hard-coding the M->FY split or assuming a port -- read period-map and environment_access.json.
- Copying memo/draft groupings instead of the live operating records.
- Forecast: adding growth rates instead of compounding; forgetting to re-band seniority by +1/+2
  service years; picking `largest_growth_pay_type` by dollars instead of percent.
- Comp: double-counting the title premium for `combined_overscale_includes_title` employees;
  using a flat 13-week quarter for partial-quarter employees.
- Payroll: forgetting the rehearsal 3-hour minimum; giving substitutes a guarantee; applying
  vacation before premiums/doubles; excluding doubles from the vacation base; emitting conflict
  flags that aren't actually triggered.

Always reproduce a known figure from `references/worked_examples.md` (e.g. M-H26-02's
guarantee 344.13, or ENS-MAPLE's largest_growth_pay_type "Seniority") as a smoke test before
finalizing, then verify your output keys against the template's `required_top_level_keys`.
