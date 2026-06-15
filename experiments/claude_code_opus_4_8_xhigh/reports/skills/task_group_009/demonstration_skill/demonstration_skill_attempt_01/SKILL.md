---
name: crescent-finance-ops-reporting
description: >-
  Use this skill for any Crescent Finance Ops / Crescent Arts Collective
  management-reporting task that returns a single JSON object built from the
  read-only Finance Ops HTTP API. It covers branch monthly-close packages,
  regional rollups, current-year and forecast compensation summaries, and
  weekly theatre payroll / CBA control. Trigger it whenever the prompt mentions
  a request_memo + answer_template + environment_access payload, a Finance Ops
  base_url, income statement / EBITDA / ARPU / sales-per-labor-headcount,
  branch or region rankings, compensation by quarter and pay type, seniority
  or overscale, or weekly payroll with services, doubles, premiums, guarantees
  and conflict flags. Even when the task only says "prepare the close package"
  or "review this payroll week", use this skill — the numeric conventions and
  business rules here are where solvers most often go wrong.
---

# Crescent Finance Ops — Management Reporting

You produce **one JSON object** per task, matching the keys and types in that
task's `payloads/answer_template.json`, computed from the read-only Finance Ops
API. The data is deterministic; if you apply the rules below exactly, your
numbers will match to the penny.

## How to work a task

1. Read `payloads/environment_access.json` for the `base_url` and the
   `available_endpoints` that this task allows. Use only those endpoints.
2. Read `payloads/request_memo.json` for IDs and scope (target branch/region/
   ensemble/production, periods, scenario, focus list).
3. Read `payloads/answer_template.json`. It is the contract: the
   `required_top_level_keys`, the `field_types`, the rounding rules in
   `description`, and any ordering rules. Build exactly those keys — no more.
4. Query the API (curl or python). Compute. Emit JSON.

A ready-made, validated implementation of every rule below lives in
`scripts/finance_ops_helpers.py` (it reproduces all known standard answers
exactly). Import or copy from it rather than re-deriving the math:

```python
import sys; sys.path.insert(0, "scripts")
from finance_ops_helpers import *
BASE = "http://127.0.0.1:8028"   # always read the real value from the payload
```

## Output conventions (this is the #1 source of error)

- **Currency → 2 decimals.** Use `money(x)` (rounds with a tiny epsilon so
  `x.xx5` rounds up rather than floor-flipping on float error).
- **"decimal percent" / ratio fields → a FRACTION rounded to 4 decimals.**
  8.95% is `0.0895`, NOT `8.95`. Never multiply by 100. This applies to every
  field the template calls `decimal percent`: EBITDA margin, MoM pct, revenue/
  EBITDA growth, forecast growth rates. Use `ratio(x)`.
- **Counts/headcounts/ranks → integers.**
- **Annual totals → sum the four ROUNDED quarter totals**, not the raw annual
  sum then rounded. Quarter-first rounding is what the standard answers use and
  it can differ by a cent (`annual_total_from_quarters`).
- **List ordering — follow the template's own words.** Default is ascending
  stable IDs. Branch/region `branch_ids` ascending. `per_musician` ordered by
  `musician_id`. `conflict_flags` sorted alphabetically. `pay_types` in the
  rate-book order. Rank fields override default ordering.
- **Emit only nonzero category amounts** where the template says so (e.g.
  per-musician `categories`, and `substitute_adjustment` "when applicable").
- Round only at output time; keep full precision through intermediate sums.

## Use live operating data, not stale memo groupings

Memos often plant a distractor ("a draft workbook has notes for Harbor North",
"reconcile against the active operations data"). Always take branch names,
region membership, period→FY mapping, rate books, rosters and schedules from
the **API**, never from the memo's prose. The memo gives you IDs and scope; the
API gives you facts.

---

## Family A — Branch close package (finance)

Endpoints: `/api/finance/branches`, `/period-map`, `/accounts`, `/records`.
Records carry `values` as a `{period: amount}` map (no per-row `period` field);
index them with `index_records(records)`.

**Period / fiscal-year mapping.** Derive it from `/period-map`, which ships
`period → fiscal_year`. As currently seeded: M1..M12 = FY2024, M13..M24 =
FY2025 (period Mn for n>12 is month n-12 of the next FY). Use
`fy_periods(period_map, year)` so it still works if the map changes. "Current
close period" and "prior period" come from the memo (`close_period`,
`prior_period`).

**Income statement** (single month or a full FY — same formula over the chosen
periods), via `income_statement(idx, branch, periods)`:

```
revenue      = product_revenue + service_revenue
cogs         = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga          = sales_sga + admin_sga + occupancy_sga
allocations  = shared_service_allocations
ebitda       = gross_margin - sga - allocations
```

**MoM revenue variance:** amount = rev(current) − rev(prior);
pct = amount / rev(prior) as a 4dp fraction.

**FY metrics & growth** (`fy_metrics`):
- `ebitda_margin` = ebitda / revenue (4dp fraction).
- `arpu` = FY revenue / **SUM of monthly `active_customers`** over the FY.
- `sales_per_labor_headcount` = FY revenue / **SUM of monthly `labor_headcount`**
  over the FY. The denominators are summed monthly counts, NOT a point-in-time
  or averaged headcount — this is a common mistake.
- `revenue_growth_pct` = (FY25 rev − FY24 rev) / FY24 rev; `ebitda_growth_pct`
  likewise (4dp fractions).

**Regional context & rankings.**
- Region membership from `/branches` (`region_branches`); list `branch_ids`
  ascending.
- A region's metric = arithmetic **sum of its member branches** (no separate
  region record). `region_context.fy2025_ebitda` is the FY25 EBITDA sum.
- `ebitda_rank_desc` ranks the region among **all regions** by FY25 EBITDA,
  descending, rank 1 = highest.
- `branch_rankings` are computed **across all 12 branches**, not within the
  region: `sales_growth_rank_desc` = the target branch's rank by FY25-vs-FY24
  revenue growth (desc); `top_sales_growth_branch_id` = branch with highest such
  growth; `top_arpu_branch_id` = branch with highest FY25 ARPU.
- Ranking helper: `rank_desc(value_by_id)` → `[(id, rank)]`. Default sort is
  stable; if a tie ever appears, break it by ascending branch_id.

## Family B — Regional view (finance)

Same endpoints and formulas as Family A, aggregated to the region.
- `branch_ids` ascending (`region_branches`).
- `fy2024` / `fy2025` lines = sum of member-branch income statements
  (`region_rollup`).
- `fy2025.ebitda_margin` = region EBITDA / region revenue (4dp).
- `fy2025.sales_per_labor_headcount` = region FY25 revenue / **sum of member
  branches' FY25 labor_headcount sums** (sum revenue ÷ sum headcount, not an
  average of per-branch ratios).
- `revenue_growth_pct` = region (FY25−FY24)/FY24 (4dp).
- `top_ebitda_branch_id` / `bottom_ebitda_branch_id` = highest / lowest FY25
  EBITDA branch within the region.
- `region_reconciliation_variance` = region total − sum of branch totals = `0.0`
  by construction (there is no independent region record to disagree with).

---

## Family C — Compensation: current year by quarter & pay type

Endpoints: `/api/compensation/rate-book`, `/rosters?ensemble_id=...`.

Rate book gives `minimum_weekly_scale`, ordered `pay_types`,
`title_premium_pct` (by title), and `seniority_weekly` bands (inclusive
`[min_years, max_years]`, open band has `max_years: null`). Each roster row has
`weeks_by_quarter`, `years_of_service`, `title`, `overscale_weekly`, and
`combined_overscale_includes_title`.

Per employee, per quarter (`comp_breakdown(rate_book, roster)`), summing weeks
from the roster's **actual `weeks_by_quarter`** (not a fixed 13):

```
Minimum Weekly Scale = scale * weeks
Titled Position Prem = scale * title_premium_pct[title] * weeks
                       -> SKIP entirely if combined_overscale_includes_title
Seniority            = seniority_band(years_of_service) * weeks
Overscale            = overscale_weekly * weeks
```

- `quarter_totals` Q1..Q4 = per-quarter sums (currency).
- `annual_pay_type_totals` = each pay type summed across the year (each rounded
  independently).
- `annual_total` = **sum of the four rounded quarter totals**.
- `largest_pay_type` = the pay type with the largest annual dollar total.
- `pay_types` = the rate-book order, verbatim.
- `roster_count` = number of roster rows for the ensemble.
- `combined_overscale_employee_count` = rows with
  `combined_overscale_includes_title == true` (these get NO separate title
  premium; their overscale already bundles it).
- `partial_quarter_employee_count` = rows whose any quarter weeks ≠ 13.

## Family D — Compensation: board forecast

Endpoints: rate-book, rosters, and `/api/compensation/scenarios`.

Pick the single scenario named by `scenario_id`. Compute three years:
`current` (offset 0), `year_plus_1` (1), `year_plus_2` (2) with
`comp_breakdown(rate_book, roster, year_offset=off, scenario=scen)`.

Escalation rules (rate-book `business_rules`):
- Scenario growth rates **compound multiplicatively** year over year. For
  Year+N: `scale = minimum_weekly_scale * Π(1+mws_growth)`,
  overscale ×`Π(1+overscale_growth)`, seniority weekly ×`Π(1+seniority_growth)`,
  title premium ×`Π(title_pct_multiplier)`.
- **Add N years of service before assigning the seniority band** for Year+N.
  This band jump is the dominant forecast driver.

Outputs:
- `annual_totals.{current,year_plus_1,year_plus_2}` — each = sum of that year's
  four rounded quarter totals.
- `growth_rates` = year-over-year annual growth as 4dp fractions
  (`year_plus_1_vs_current`, `year_plus_2_vs_year_plus_1`).
- `year_plus_2_quarter_totals`, `year_plus_2_pay_type_totals` from the Year+2
  breakdown.
- `largest_growth_pay_type` = the pay type with the largest growth from
  **current to Year+2 measured by PERCENT change**, not by absolute dollars.
  (Minimum Weekly Scale usually grows most in dollars, but Seniority typically
  grows most in percent because of band jumps — answer the percent winner.)
- `combined_overscale_employee_count`, `partial_quarter_employee_count` — same
  definitions as Family C (computed once on the roster; not year-dependent).

---

## Family E — Weekly theatre payroll & CBA control

Endpoints: `/api/payroll/rate-book`, `/api/payroll/productions?production_id=...`
(productions endpoint returns a list; take element 0). A production has a
`schedule` (services with `service_id`, `service_type`, `start_time`,
`end_time`, `duration_hours`) and a `roster` of musicians with
`assigned_service_ids` and flags.

Use `musician_pay(rate_book, schedule_by_id, m)` for the per-musician
`{category: amount}` and `conflict_flags(rate_book, schedule)` for flags.

**Base service pay.** Rehearsal is hourly with a **3-hour minimum call**
(`rate * max(duration_hours, 3)`). Performance, Audit, Sound Check are flat
per-service rates. Category buckets: Performance→`performance`, Audit→`audit`,
Rehearsal→`rehearsal`, "…Sound Check"→`sound_check`.

**Order of operations (validated to the penny):**
1. Sum base service pay into its category bucket.
2. **Substitute uplift = 50% of performance base pay.** Add it INTO
   `performance` **and** report the same amount again as `substitute_adjustment`
   — it intentionally contributes twice to the weekly total. The uplifted base
   is what premiums are computed on. Substitutes get **no** guarantee
   adjustment.
3. **Role premiums STACK** (sum the applicable percentages, apply once to base
   service pay → `premium`): principal OR lead → `principal_or_lead`;
   `quartet` → `quartet`; `electronic` → `electronic`; concertmaster →
   `concertmaster` (apply if such a flag is present).
4. **Doubles premium** → `doubles`: first extra instrument 25% (`first_double`),
   each additional +10% (`additional_double`), i.e.
   `first_double + additional_double*(doubles-1)`, on base service pay.
5. **Vacation** (`vacation`) = 4% of (base service + role premium + doubles
   premium) when `vacation_eligible`.
6. **Guarantee adjustment** (`guarantee_adjustment`) = only non-substitute
   guaranteed regular players, only when **base service pay alone** (excluding
   premiums) is below `weekly_guarantee`; amount = `weekly_guarantee −
   base_service_pay`.

**Aggregates:**
- `service_counts` = count of schedule entries per `service_type` (e.g.
  `{"Performance": 4, "Rehearsal": 2, ...}`).
- `category_totals` = sum each category across all musicians.
- `weekly_total` = sum of all category totals (= sum of per-musician totals).
- `per_musician` ordered by `musician_id`; each row carries only nonzero
  `categories`.
- `top_paid_musician_id` = musician with the highest total (tie-break by
  ascending musician_id).

**CBA conflict flags** (enum: `REHEARSAL_EARLY_START`, `REHEARSAL_LATE_END`,
`SERVICE_OVER_TIME_LIMIT`, `SOUND_CHECK_DURATION_MISMATCH`), emitted once if any
service triggers them, sorted alphabetically:
- `REHEARSAL_EARLY_START`: a Rehearsal `start_time` < `rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: a Rehearsal `end_time` > `rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service `duration_hours` > its
  `service_time_limits[type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: a sound check whose `duration_hours` ≠ its
  nominal length (1hr→1.0, 2hr→2.0).
Times are zero-padded `HH:MM`, so lexicographic string comparison is correct.

---

## Common misjudgments — quick checklist

- Wrote a percent as `8.95` instead of the fraction `0.0895`.
- Rounded the raw annual sum instead of summing the four rounded quarters.
- Used a fixed 13-week quarter instead of the roster's `weeks_by_quarter`.
- Added a title premium to a `combined_overscale_includes_title` employee.
- Used average/point-in-time headcount or customers for ARPU / sales-per-labor
  instead of the **summed** monthly counts.
- Ranked branches within the region when the template wants all-branch ranks
  (or vice versa).
- Picked `largest_growth_pay_type` by dollars instead of percent.
- Forgot to increment years of service before the seniority band in forecasts,
  or applied scenario growth additively instead of compounding.
- Dropped the substitute uplift, or counted it only once (it lands in both
  `performance` and `substitute_adjustment`).
- Gave a substitute a guarantee adjustment, or compared guarantee against base
  pay including premiums.
- Trusted a memo's branch grouping/notes instead of the live API.
- Emitted extra top-level keys or zero-valued category entries the template
  didn't ask for.

Before returning, re-read the template's `required_top_level_keys`,
`field_types`, and ordering/rounding notes and confirm your object matches them
exactly.
