---
name: crescent-finance-ops-reporting
description: >-
  Produce Crescent Arts "Finance Ops" management reporting packages from the read-only HTTP API:
  branch monthly-close packages, regional rollup dashboards, current-year and multi-year compensation
  summaries/forecasts, and weekly touring-production payroll reviews. Use this skill whenever a task
  references the Finance Ops base URL / a payloads/ bundle (request_memo.json, answer_template.json,
  environment_access.json), or asks for income-statement / EBITDA / ARPU / per-headcount metrics,
  branch or region rankings, ensemble compensation by quarter and pay type, seniority/overscale/titled
  forecasts, or musician payroll with doubles/premiums/guarantee/substitute/CBA-conflict logic. It
  captures the exact formulas, field-scope rules, rounding conventions, and the specific pitfalls that
  cause wrong answers. Reach for it even when the prompt only says "close package", "regional view",
  "comp summary", "board forecast", or "payroll review" without naming the API.
---

# Crescent Finance Ops Reporting

You build one JSON object per task that conforms to a provided `answer_template.json`. The data lives
behind a read-only HTTP API. Everything you output is derived from LIVE API data — never from memory,
never from the `memo_note` (which is a distractor, see below).

This skill exists because the work is deceptively simple-looking but has many traps that silently produce
wrong numbers: the SAME field name uses different denominators in different report types, "growth" means
percent in one place and dollars in another, rounding mode matters to the cent, and roster/schedule
booleans each unlock a pay rule that is easy to skip. Read the relevant section in full before computing.

## Golden workflow (every task)

1. Read the three payload files: `request_memo.json` (what/which entity), `answer_template.json`
   (required keys, field types, formatting rules), `environment_access.json` (base URL + allowed endpoints).
2. Identify the report TYPE from the template's top-level keys and the prompt. The type determines which
   formulas and which denominator conventions apply (see "Report types" below). Do not assume one global rule.
3. Pull EVERY input from the API (see "Environment / API"). Confirm the entity exists and note its scope
   (a single branch? a region's branch set? an ensemble roster? a production schedule + roster?).
4. Compute using the formulas for that report type. Apply each per-row business rule driven by the data's
   own flags/booleans — do not skip an "optional" template field if its trigger is present in the data.
5. Format per the conventions section (rounding mode, 2dp vs 4dp, fraction-not-percent, ordering).
6. Emit exactly the template's required keys, with the specified types. Output one JSON object, nothing else.

## Environment / API

Base URL comes from `environment_access.json` (e.g. `http://127.0.0.1:8028`). Read-only GET. Query with
curl or python (`urllib`). The API never exposes answers, rubrics, or the template. Endpoints (each task's
`environment_access.json` lists the subset it allows):

- `/api/manifest` — endpoint list, file list, and `public_entities` (branches, ensembles, productions). Good
  for a quick entity sanity check.
- Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`,
  `/api/finance/records` (filters: `?branch_id=` `?region=` `?account=`).
- Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters?ensemble_id=`,
  `/api/compensation/scenarios`.
- Payroll: `/api/payroll/rate-book`, `/api/payroll/productions?production_id=`.

Pull whole datasets and compute locally; the data is small (e.g. finance `records` = 12 branches x 14
accounts = 168 rows). Always prefer programmatic computation (a short python script) over mental math —
the rounding and aggregation rules below are unforgiving.

### Finance data model
- `records`: one row per (branch_id, account); each row has `values` keyed `M1..M24` plus its own
  authoritative `region_id` and `branch_name`. Use the record's `region_id` for rollups.
- `period-map`: `M1..M12` = FY2024, `M13..M24` = FY2025. For monthly close, the current month is the latest
  period (`M24` = Dec FY2025) and the prior month is `M23`. Confirm against `period-map` rather than assuming.
- `accounts` carry a `category` (revenue, cogs, sga, allocations, operating) and `metric_type`
  (currency vs count). The `operating` counts include `active_customers`, `labor_headcount`,
  `admin_headcount`, `orders`, `revenue_units`, `backlog`.

### The memo_note is a distractor
Memos say things like "reconcile against the active operations data" or "tie back to the active operating
data used for the management package." This is a reminder to compute from the LIVE API records — NOT an
instruction to apply a draft/workbook overlay. There is no hidden stale dataset; the records endpoint IS the
active operating data. A reconciliation-variance field is therefore 0.0 when all sources agree (they do).

## Formatting & rounding conventions (high-error area)

These trip up answers constantly. Apply them exactly.

- **Currency**: 2 decimals.
- **"decimal percent" / ratio / growth fields**: a FRACTION rounded to 4 decimals. 8.95% -> `0.0895`,
  NOT `8.95` and NOT `0.09`. EBITDA margin of 24.59% -> `0.2459`. This applies to every margin, growth_pct,
  and rate field.
- **Rounding mode = ROUND_HALF_UP** (half away from zero), NOT Python's default banker's rounding.
  `344.125 -> 344.13`, `111.895 -> 111.90`. In python:
  `float(Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP))`.
- **Aggregate raw, then round once.** For category/weekly/region totals, sum the unrounded component values
  and round the total a single time. Do NOT sum already-rounded per-row values (that introduces cent drift).
- **Ordering**: lists use ascending stable IDs unless a field name says otherwise (a `*_rank_*` or
  `top_*`/`bottom_*` field implies a ranking order, not ID order). Payroll `per_musician` is ordered by
  musician_id; `conflict_flags` sorted alphabetically and de-duplicated. Compensation `pay_types` follow the
  rate-book's `pay_types` order.
- Object keys: emit exactly the keys the template names; include an "optional/when applicable" field whenever
  its trigger condition is present in the data.

## Read the field NOUN: scope and "growth vs level"

Two recurring mistakes come from not reading what a field actually describes:

1. **Scope by container.** A field nested under `region_context` describes the REGION (a rollup and the
   region's rank among regions), while a sibling under `branch_rankings` describes the BRANCH vs ALL
   branches. Same word ("ebitda", "rank") means different things by container. Before filling a field, ask:
   "is this about the target entity, its region rollup, or a population ranking?"
2. **"largest"/"top" vs "largest growth".** `largest_pay_type` = the pay type with the largest absolute
   total DOLLARS. `largest_growth_pay_type` = the pay type with the largest PERCENT growth (relative change),
   which can be a different pay type than the one adding the most dollars. Match the metric to the noun:
   level -> absolute; growth -> relative/percent.

---

## Report type: Branch monthly-close package

Template keys like `m24_income_statement`, `mom_revenue_variance`, `fy2025_vs_fy2024`, `region_context`,
`branch_rankings`. Endpoints: finance/*.

### Income statement (one period or a full FY = sum of its 12 periods)
- revenue = product_revenue + service_revenue
- cogs = direct_materials_cogs + direct_labor_cogs
- gross_margin = revenue - cogs
- sga = sales_sga + admin_sga + occupancy_sga
- allocations = shared_service_allocations
- ebitda = gross_margin - sga - allocations  (equivalently revenue - cogs - sga - allocations)

### Variance & growth
- mom_revenue_variance.amount = revenue[current] - revenue[prior]; .pct = amount / revenue[prior] (4dp fraction).
- revenue_growth_pct = (FY2025_rev - FY2024_rev) / FY2024_rev (4dp). ebitda_growth_pct analogously.
- ebitda_margin = FY ebitda / FY revenue (4dp).

### Per-unit ANNUAL metrics — BRANCH scope uses SUM of monthly counts (unit-months)
This is a top error source. For a BRANCH close package:
- arpu = FY revenue / SUM over the 12 FY months of `active_customers` (= customer-months; e.g. 3486).
  NOT the average monthly customers, NOT the year-end count.
- sales_per_labor_headcount = FY revenue / SUM over the 12 FY months of `labor_headcount`
  (= headcount-months; e.g. 142). NOT the average, NOT year-end.
(Note: the REGION report uses a DIFFERENT denominator for the same-named field — see the regional section.
This inconsistency is real; pick the convention by report type.)

### region_context (describes the REGION)
- region_id, branch_ids (the region's branch set, ascending).
- fy2025_ebitda = REGION TOTAL = sum of FY2025 EBITDA across ALL branches in that region (a rollup, NOT the
  target branch's own EBITDA).
- ebitda_rank_desc = the REGION's rank among ALL regions, descending by region-total FY2025 EBITDA.

### branch_rankings (describe the BRANCH vs ALL branches)
- sales_growth_rank_desc = the target branch's rank among ALL branches by FY revenue growth, descending.
- top_sales_growth_branch_id, top_arpu_branch_id = the branch (across all branches) that leads each metric.
  top_arpu uses the same branch-ARPU definition (rev / sum of customer-months) consistently.

---

## Report type: Regional management view (rollup dashboard)

Template keys like `region_id`, `branch_ids`, `fy2024`, `fy2025`, `revenue_growth_pct`,
`top_ebitda_branch_id`, `bottom_ebitda_branch_id`, `region_reconciliation_variance`. Endpoints: finance/*.

- Region figures = SUM across the region's branches of each FY line item (revenue, sga, allocations, ebitda).
- ebitda_margin = region ebitda / region revenue (4dp). revenue_growth_pct = (FY2025 - FY2024)/FY2024 (4dp).
- **sales_per_labor_headcount (REGION scope) = region FY revenue / AVERAGE monthly headcount**, where average
  = (sum of all branches' headcount across all 12 months) / 12. Equivalently sum-of-branch-monthly-averages.
  This is the OPPOSITE denominator from the branch-close report (which divides by the SUM of headcount-months).
  Do not carry the branch convention over to the region view, or vice versa.
- top_ebitda_branch_id / bottom_ebitda_branch_id = ranked among the REGION's branches by FY2025 EBITDA.
- region_reconciliation_variance = tie-out between the region rollup and the sum of its branch records;
  0.0 when sources agree (they do — the memo_note is a distractor). branch_ids ascending.

---

## Report type: Compensation summary (current year, by quarter & pay type)

Template keys like `current_year`, `roster_count`, `pay_types`, `quarter_totals`, `annual_pay_type_totals`,
`annual_total`, `largest_pay_type`, `combined_overscale_employee_count`, `partial_quarter_employee_count`.
Endpoints: compensation/rate-book, compensation/rosters.

Rate-book gives: `minimum_weekly_scale` (MWS), `pay_types` order, `title_premium_pct` by title,
`seniority_weekly` bands (by years_of_service ranges), default `quarter_weeks` (13 each).

### Per-employee, per-quarter amounts (then sum across employees and quarters)
For each roster row, for each quarter, multiply the weekly amount by that quarter's weeks:
- Minimum Weekly Scale = MWS * weeks
- Titled Position Premium = title_premium_pct[title] * MWS * weeks
  -> 0 if the employee has NO title, OR if `combined_overscale_includes_title` is true (premium is folded
     into overscale per side letter — the employee still has a title, but you do NOT add it separately).
- Seniority = (seniority band weekly amount for years_of_service) * weeks
- Overscale = overscale_weekly * weeks

### Weeks: use the roster row's `weeks_by_quarter`
Each roster row carries `weeks_by_quarter` (e.g. `{Q1:13, Q2:9, Q3:13, Q4:13}`). USE IT — do not assume a
flat 13. The default `quarter_weeks` from the rate-book applies only when a row lacks `weeks_by_quarter`.
Partial quarters lower that quarter's total for that employee.

### Counts and "largest"
- roster_count = number of roster rows for the ensemble.
- partial_quarter_employee_count = rows whose `weeks_by_quarter` has ANY value != 13.
- combined_overscale_employee_count = rows with `combined_overscale_includes_title` == true.
  (The roster `notes` text corroborates these flags but the BOOLEAN is authoritative.)
- largest_pay_type = pay type with the largest ANNUAL TOTAL DOLLARS (read the enum literally; MWS usually
  wins — do not exclude the base scale). Contrast `largest_growth_pay_type` in the forecast report.
- pay_types list = the rate-book `pay_types` in that exact order.

---

## Report type: Compensation forecast (current, Year+1, Year+2)

Template keys like `annual_totals` (current/year_plus_1/year_plus_2), `growth_rates`,
`year_plus_2_quarter_totals`, `year_plus_2_pay_type_totals`, `largest_growth_pay_type`, the two counts.
Endpoints: compensation/rate-book, rosters, scenarios.

Start from the current-year compensation model above, then apply the named scenario from
`/api/compensation/scenarios` (selected by `scenario_id`). Each scenario has per-year growth dicts:
`mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.

### Forecast mechanics
- **Compound year over year.** Year+1 factor = (1 + g1); Year+2 factor = (1 + g1) * (1 + g2), per pay type.
  `title_pct_multiplier` is cumulative too: tm2 = tm1 * (Year+2 title_pct_multiplier). (When multipliers are
  1.0, the titled premium still grows because it is computed on the grown MWS.)
- **Seniority re-banding, then growth.** Add +1 year of service for Year+1 and +2 for Year+2 BEFORE picking
  the seniority band (a rate-book business rule). Crossing a threshold can jump the weekly amount sharply
  (e.g. 0 -> 48). Apply the seniority_growth multiplier to the band amount after re-banding.
- Per-pay-type Year+2 amount = (current weekly amount, with re-banded seniority) * cumulative factor * weeks.
- growth_rates = (total[next] - total[prev]) / total[prev], 4dp fraction (year_plus_1_vs_current and
  year_plus_2_vs_year_plus_1).
- combined_overscale and partial_quarter counts: same definitions as the summary report.

### largest_growth_pay_type = largest PERCENT growth (not dollars)
Measure (Year+2 total - current total) / current total per pay type and take the max. Seniority often wins
on percent (band re-assignment drives a large relative change) even though MWS adds the most absolute
dollars. Do not pick by absolute growth here.

---

## Report type: Weekly touring-production payroll review

Template keys like `service_counts`, `category_totals`, `weekly_total`, `conflict_flags`, `per_musician`,
`top_paid_musician_id`. Endpoints: payroll/rate-book, payroll/productions.

Rate-book gives: `service_rates`, `service_time_limits`, `premium_pct` (principal_or_lead, quartet,
electronic, concertmaster, first_double, additional_double, vacation), `weekly_guarantee`,
`conflict_thresholds`, and `business_rules`. The production gives a `schedule` (services with type, times,
duration_hours) and a `roster` (musicians with assigned_service_ids and booleans).

### Per-musician computation (apply EVERY relevant flag)
1. **Base service pay** = sum of the rates for the musician's assigned services.
   - Performance / Audit / Sound Check: flat per-service rate.
   - Rehearsal: hourly rate * max(duration_hours, 3.0) (three-hour minimum call).
2. **Substitute** (roster `substitute` == true): Performance services are paid at 1.5x. The `performance`
   category shows the full 1.5x amount, AND a separate `substitute_adjustment` category = 0.5x * the plain
   performance pay (the differential). Both contribute to the total. Substitutes receive NO weekly guarantee.
   (Only performance was uplifted in observed data; verify against the rate-book's substitute rule.)
3. **Premiums** are applied to the (post-substitute-uplift) base service pay, BEFORE vacation, and summed
   into ONE `premium` category: principal_or_lead (if `principal` OR `lead`), quartet, electronic,
   concertmaster — each a pct of base.
4. **Doubles** -> `doubles` category = base * (first_double for the first extra instrument + additional_double
   for each further one). `doubles: N` means N extra instruments.
5. **Vacation** (if `vacation_eligible`) -> `vacation` = vacation_pct * (base + premiums + doubles).
6. **Guarantee adjustment** -> `guarantee_adjustment` = max(0, weekly_guarantee - base) for NON-substitute
   regular players only; compared against base service pay (pre-premium).
7. musician total = sum of that musician's category amounts. Round each output ROUND_HALF_UP to 2dp.

### Totals, counts, ranking
- service_counts = integer counts of each service TYPE in the schedule (keys = rate-book service-type names).
- category_totals & weekly_total = sum the RAW per-musician category amounts, then round once.
- top_paid_musician_id = musician with the highest total (the substitute uplift can make a substitute the
  top earner — don't assume a regular player wins).
- per_musician ordered by musician_id; each musician's `categories` lists only nonzero categories.

### Conflict flags (enum, sorted alphabetically, de-duplicated)
- REHEARSAL_EARLY_START: any Rehearsal start_time earlier than `rehearsal_earliest_start`.
- REHEARSAL_LATE_END: any Rehearsal end_time later than `rehearsal_latest_end`.
- SERVICE_OVER_TIME_LIMIT: any service whose duration_hours exceeds its `service_time_limits` entry.
- SOUND_CHECK_DURATION_MISMATCH: a "1hr/2hr Sound Check" whose actual duration != its nominal hours.
- Pay the ACTUAL hours even when a service violates a limit (pay-actual, flag-the-violation). Don't cap pay.
- conflict_flags is a SET of flag types (one entry per type even if several services trigger it).

---

## Pre-submit checklist (catches the historical errors)

- Currency 2dp; every margin/growth/ratio is a 4dp FRACTION (0.0895 not 8.95).
- Rounding mode is ROUND_HALF_UP; totals aggregated raw then rounded once.
- Per-unit annual metric denominator matches the report type: BRANCH = sum of unit-months;
  REGION = average monthly count.
- region_context / regional fields describe the REGION (rollup + region-among-regions rank), not the branch.
- "largest" = absolute dollars; "largest growth" = percent.
- Compensation: weeks from `weeks_by_quarter`; titled premium dropped when combined_overscale flag is true;
  forecast compounds and re-bands seniority (yos +1 / +2) before applying growth.
- Payroll: applied substitute 1.5x + substitute_adjustment, premiums on uplifted base, doubles, vacation on
  base+premiums+doubles, guarantee only for non-substitute; included every "when applicable" category present.
- Output is exactly the template's required keys, correct types, one JSON object only. The memo_note added
  nothing to the numbers.
