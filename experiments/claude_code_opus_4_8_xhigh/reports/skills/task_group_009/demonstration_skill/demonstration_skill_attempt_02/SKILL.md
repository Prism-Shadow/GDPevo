---
name: crescent-finance-ops-reporting
description: >-
  Produce Crescent Finance Ops management-reporting deliverables for Crescent
  Arts Collective: branch monthly-close packages, regional reporting views,
  current-year and forecast ensemble compensation summaries, and theatre weekly
  payroll / CBA control reviews. Use this whenever a task references the Crescent
  Finance Ops API (finance branches/records, compensation rate-book/rosters/
  scenarios, payroll rate-book/productions), a request_memo + answer_template
  pair, branch/region income statements, EBITDA / ARPU / sales-per-headcount
  ratios, MoM or FY growth, musician/ensemble pay by quarter and pay type,
  weekly payroll category totals, or CBA conflict flags — even if the word
  "Crescent" is not used but the payloads or endpoints match. Reach for it
  before computing by hand: the rounding and scoping conventions here are easy
  to get wrong.
---

# Crescent Finance Ops management reporting

You are filling a single JSON object that matches the task's
`payloads/answer_template.json`, using read-only data from the Finance Ops HTTP
API. There are five task families. Identify the family from the prompt + memo +
template, pull the live data, apply the verified rules below, and emit exactly
the keys the template lists.

`scripts/finance_ops.py` contains verified calculators for every family. Reading
it is the fastest way to get the math exactly right — adapt the entity ids /
periods / years to your task. The rules below explain the *why* so you can spot
edge cases the script's defaults don't cover.

## How to work a task

1. Read `payloads/environment_access.json` for the live `base_url` and the
   endpoints this task allows. Read `payloads/request_memo.json` for the target
   entity (branch/region/ensemble/scenario/production) and the requested fields.
   Read `payloads/answer_template.json` for the exact output keys, field types,
   and ordering rules.
2. Query the API with curl or python (GET only). Look at the real shapes first;
   do not assume field names.
3. Compute with full precision, then round once at the end (see Rounding).
4. Return one JSON object with exactly the template's `required_top_level_keys`.

### The memo trap (applies to every family)

The memo often points at a "draft workbook", "side letter", "background notes",
or "stale groupings" and asks you to *reconcile against the active operations
data*. **The live API is the source of truth.** Use the current branch→region
membership, current rosters, and current rate-books/scenarios from the API.
Treat memo narrative (old branch lists, prior groupings, descriptive `notes`
strings) as context to be overridden, never as input values. A
`region_reconciliation_variance` of `0.0` is the expected, healthy result when
the region total ties to the sum of its current branches — and it normally does.

## Rounding and number formatting (the #1 source of error)

- **Currency → 2 decimals. Percent / ratio fields → 4 decimals.**
- **Percent/ratio fields are FRACTIONS, not percentages.** 8.95% is `0.0895`,
  NOT `8.95`. A field typed `"decimal percent"` or `"ratio"` means the decimal
  fraction. EBITDA margin of 24.59% is `0.2459`. Growth of 9.66% is `0.0966`.
- **Use HALF-UP rounding, not Python's default.** Python's built-in `round()`
  uses banker's rounding, so `round(344.125, 2)` gives `344.12`, but the
  expected answer is `344.13`. Always round half-up:
  ```python
  from decimal import Decimal, ROUND_HALF_UP
  def r2(x): return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
  def r4(x): return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
  ```
- **Round once, from full precision** — do not chain roundings. Two deliberate
  exceptions, both verified against the standard answers:
  - *Compensation annual_total* = sum of the four **already-rounded** quarter
    totals (`r2(sum(r2(q) for q in quarters))`). Summing raw then rounding can
    be off by a cent.
  - *Payroll per-musician total* = `r2(sum_of_RAW_category_values)` (round the
    raw sum once), while each displayed category and the rolled-up
    `category_totals` are `r2(raw)` independently. `weekly_total` =
    `r2(sum of the rounded per-musician totals)`.
- Normalize negative-zero to `0.0` (e.g. a reconciliation variance computed as
  `-0.0`).

## Period and fiscal-year mapping (finance families)

Always read `/api/finance/period-map`; never hardcode. With the standard map:
M1–M12 = FY2024, M13–M24 = FY2025 (12 calendar months per fiscal year, Jan=M1/
M13). For a `period_convention` block, report `M1_to_M12` and `M13_to_M24` as
the `FY####` strings from the map, and echo the memo's current/prior month
labels. Build FY period lists by filtering the map on `fiscal_year`, so the code
stays correct if the map ever shifts.

---

## Family 1 — Branch monthly-close package

Endpoints: `finance/branches`, `finance/period-map`, `finance/accounts`,
`finance/records`. Records are one row per (branch, account) with a `values` map
keyed by period; pull all records once and index `B[branch][account][period]`.

**Income statement** (one month, e.g. M24; or a FY by summing its periods):
- `revenue` = product_revenue + service_revenue
- `cogs` = direct_materials_cogs + direct_labor_cogs
- `gross_margin` = revenue − cogs
- `sga` = sales_sga + admin_sga + occupancy_sga
- `allocations` = shared_service_allocations
- `ebitda` = gross_margin − sga − allocations

Confirm account→line membership from `/api/finance/accounts` (`category` field).
The `operating` accounts (orders, revenue_units, active_customers,
labor_headcount, admin_headcount, backlog) are counts, not income-statement
lines — they feed the ratios below.

**MoM revenue variance** (current vs prior month):
`amount = rev_current − rev_prior`; `pct = amount / rev_prior` (fraction, r4).

**Current FY metrics** (FY2025 here):
- Roll up the six income-statement lines over the FY's 12 periods.
- `ebitda_margin` = FY ebitda / FY revenue (fraction, r4).
- `arpu` = FY revenue / **SUM of monthly `active_customers` over the FY**. Use
  the sum of the 12 monthly count values, not an average and not a single month.
- `sales_per_labor_headcount` = FY revenue / **SUM of monthly `labor_headcount`
  over the FY** (same sum-not-average rule).
- `revenue_growth_pct` = (FY2025 rev − FY2024 rev) / FY2024 rev (r4).
- `ebitda_growth_pct` = (FY2025 ebitda − FY2024 ebitda) / FY2024 ebitda (r4).

**Region context** (the target branch's region):
- `branch_ids`: current members of that region from `finance/branches`, ascending.
- `fy2025_ebitda`: sum of member branches' FY2025 EBITDA.
- `ebitda_rank_desc`: rank of this region among **all regions** by FY2025 EBITDA,
  descending (1 = highest).

**Branch rankings** (across **all** branches):
- `sales_growth_rank_desc`: target branch's rank by FY2025-vs-FY2024 revenue
  growth %, descending.
- `top_sales_growth_branch_id`: branch with the highest revenue growth %.
- `top_arpu_branch_id`: branch with the highest FY2025 ARPU.

Echo `target_branch_id`/`target_branch_name` from `finance/branches`.

---

## Family 4 — Regional reporting view

Same endpoints and formulas as Family 1, but the reporting entity is the whole
region (sum the income-statement lines across the region's current branches for
each FY). `branch_ids` ascending. `ebitda_margin`, `sales_per_labor_headcount`,
and `revenue_growth_pct` are computed at the region level (region revenue /
region active-customer or labor-headcount sums; region growth).

- `top_ebitda_branch_id` / `bottom_ebitda_branch_id`: highest / lowest FY2025
  EBITDA **among the region's branches**.
- `region_reconciliation_variance`: region total EBITDA minus the sum of its
  branch EBITDAs. With consistent active data this is `0.0` — the memo's older
  groupings are a distractor; trust the live branch→region map.

---

## Compensation rules (Families 2 and 5)

Endpoints: `compensation/rate-book`, `compensation/rosters?ensemble_id=...`,
`compensation/scenarios` (forecast only). Each roster row is one employee with
`years_of_service`, `title` (or null), `overscale_weekly`, `weeks_by_quarter`,
and `combined_overscale_includes_title`.

**Weekly pay components → four pay types**, accumulated per quarter as
`weeks_in_quarter × weekly_rate`:
- **Minimum Weekly Scale** = `minimum_weekly_scale` (every employee, every week).
- **Titled Position Premium** = `minimum_weekly_scale × title_premium_pct[title]`
  — but **only if the employee has a title AND
  `combined_overscale_includes_title` is false**. When that flag is true, the
  overscale already absorbs the title premium, so add nothing here (the `notes`
  string about a "side letter" is just documentation; the flag is what counts).
- **Seniority** = `weekly_amount` from the `seniority_weekly` band matching the
  employee's years of service (`min_years ≤ y ≤ max_years`, `max_years: null` =
  open-ended). Band 0–4 years pays 0.
- **Overscale** = `overscale_weekly`.

`current_year` comes from the rate-book. `pay_types` is the rate-book's ordered
list. `largest_pay_type` = the pay type with the largest **absolute** annual
dollar total (typically Minimum Weekly Scale).

**Counts (review flags):**
- `combined_overscale_employee_count` = number of rows with
  `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count` = number of rows where any quarter's weeks
  ≠ 13 (i.e. not a full standard quarter). Always drive quarter totals from each
  employee's actual `weeks_by_quarter`, never a fixed 13-week assumption.

`annual_total` = sum of the four rounded quarter totals (see Rounding).

### Family 5 — Board compensation forecast (adds scenarios)

For the named `scenario_id`, build three years: `current`, `year_plus_1`,
`year_plus_2`.

- **current**: base rate-book values, no escalation, no added service years.
- **year_plus_1**: apply that scenario's `year_plus_1` factors and **add 1 year
  of service** before assigning seniority bands:
  - scale = `minimum_weekly_scale × (1 + mws_growth)`
  - seniority weekly × `(1 + seniority_growth)`
  - overscale weekly × `(1 + overscale_growth)`
  - title premium pct × `title_pct_multiplier`
- **year_plus_2**: escalators **compound** across both years, and **add 2 years
  of service**:
  - scale = `minimum_weekly_scale × (1 + y1.mws_growth) × (1 + y2.mws_growth)`
  - seniority mult = `(1 + y1.seniority_growth) × (1 + y2.seniority_growth)`
  - overscale mult = `(1 + y1.overscale_growth) × (1 + y2.overscale_growth)`
  - title mult = `y1.title_pct_multiplier × y2.title_pct_multiplier`

  Adding years of service can promote employees into higher seniority bands —
  recompute the band each year from the adjusted years; do not reuse the current
  band.

- `growth_rates` = (later annual − earlier annual) / earlier annual (r4), using
  the rounded annual totals.
- `year_plus_2_quarter_totals` / `year_plus_2_pay_type_totals`: from the Y+2
  build.
- **`largest_growth_pay_type`** = the pay type with the largest **percentage**
  growth from current to Year+2, i.e. `(y2_total − current_total) /
  current_total`. This is by percent, NOT by absolute dollars. Seniority often
  wins (small base, large % uplift from re-banding) even though Minimum Weekly
  Scale grows the most in dollars — picking the dollar leader is a common error.
- `combined_overscale_employee_count` / `partial_quarter_employee_count` as in
  Family 2 (roster-driven; unaffected by forecast years).

---

## Family 3 — Theatre weekly payroll / CBA control

Endpoints: `payroll/rate-book`, `payroll/productions?production_id=...`. A
production has a `roster` (musicians with boolean flags) and a `schedule`
(services with type, times, duration). Pay each musician for their
`assigned_service_ids`.

**Base service pay** (the foundation premiums apply to):
- **Rehearsal** is hourly with a **3-hour minimum call**:
  `max(duration_hours, 3.0) × rate["Rehearsal"]`.
- **Performance, Audit, Sound Check** are per-service flat rates from
  `service_rates` (no hourly math).

Service→category map: Rehearsal→`rehearsal`, Audit→`audit`,
Performance→`performance`, any "Sound Check"→`sound_check`.

**Substitute musicians** (`substitute: true`): paid **1.5×** the performance
rate for each assigned performance. Report the full 1.5× amount in the
`performance` category, and report the extra **0.5×** portion separately as
`substitute_adjustment` (so substitute_adjustment is included in the performance
line — it is a breakdown of it, and the premium base below uses the 1.5×
performance pay). Substitutes do **not** get the guarantee adjustment.

**Premiums** (each a % of the musician's base service pay, applied before
vacation; sum the applicable percentages):
- **Doubles** = `first_double` (25%) for the first extra instrument +
  `additional_double` (10%) for **each** additional extra instrument
  (`doubles ≥ 2` → 25% + 10%×(doubles−1)). Reported in the `doubles` category.
- **electronic** 25%, **principal_or_lead** 15% (if `principal` OR `lead`),
  **quartet** 15%. These go into the `premium` category. Concertmaster (20%)
  exists in the rate-book for completeness — apply it only if a roster flag
  indicates it.

**Vacation** (`vacation`): 4% of (base service pay + doubles + premium), only if
`vacation_eligible: true`.

**Guarantee adjustment** (`guarantee_adjustment`): for **regular (non-
substitute)** players only, top up to the weekly guarantee when **base service
pay** is below it: `max(0, weekly_guarantee − base_service_pay)`. Measure against
base service pay (premiums and vacation excluded).

**Output assembly:**
- `service_counts`: count of each `service_type` in the schedule (use the exact
  service-type strings, e.g. "1hr Sound Check", "Performance").
- `category_totals`: `r2(raw)` per category, summed across musicians. Omit /
  include `substitute_adjustment` only when applicable.
- `per_musician`: ordered by `musician_id` ascending; each has `musician_id`,
  `name`, `total`, and a `categories` map of **non-zero** categories only. Per
  musician `total = r2(sum of raw category values)`.
- `weekly_total = r2(sum of the rounded per-musician totals)`.
- `top_paid_musician_id`: the musician with the highest total.

**CBA conflict flags** — derive from the `schedule` against the rate-book's
`conflict_thresholds` and `service_time_limits`. Return a list sorted
alphabetically, from this enum:
- `REHEARSAL_EARLY_START`: a Rehearsal `start_time` earlier than
  `rehearsal_earliest_start` (e.g. before 09:00).
- `REHEARSAL_LATE_END`: a Rehearsal `end_time` later than
  `rehearsal_latest_end` (e.g. after 18:30).
- `SERVICE_OVER_TIME_LIMIT`: any service whose `duration_hours` exceeds its
  `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: a "1hr Sound Check" not lasting 1.0h, or a
  "2hr Sound Check" not lasting 2.0h.

Time comparisons on `"HH:MM"` strings work lexicographically. Each flag appears
at most once even if triggered by several services.

---

## Self-check before returning

- Output has exactly the template's `required_top_level_keys` — no extras, none
  missing.
- Currency at 2 decimals; every percent/ratio is a **fraction** at 4 decimals.
- Half-up rounding used everywhere; compensation `annual_total` and payroll
  totals follow their specific rounding rules above.
- Lists ordered as the template says (branch_ids / per_musician ascending;
  conflict_flags alphabetical; pay_types in rate-book order).
- All entity memberships, rosters, and rates came from the **live API**, not the
  memo narrative.

`scripts/finance_ops.py` reproduces all five families' reference answers exactly
when pointed at the live API — use it to validate your numbers.
