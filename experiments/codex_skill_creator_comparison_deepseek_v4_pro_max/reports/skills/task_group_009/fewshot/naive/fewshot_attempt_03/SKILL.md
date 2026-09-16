---
name: crescent-finance-ops
description: Solve Crescent Arts Collective finance, compensation, and payroll reporting tasks against the Crescent Finance Ops REST API. Covers branch close packages, regional views, ensemble compensation summaries and forecasts, and weekly payroll reviews with conflict detection.
---

# Crescent Finance Ops Solver

You are supporting reporting and analysis for Crescent Arts Collective. Every
task arrives with a `payloads/environment_access.json` that provides the
environment base URL, a `payloads/request_memo.json` describing the specific
request, and a `payloads/answer_template.json` specifying the output schema.
Read the base URL from the environment access payload, never hardcode it.

The environment serves a REST API. Always start by calling `GET /api/manifest`
to confirm the available endpoints and entity inventory. The manifest returns
`public_entities` with branch, ensemble, and production lists keyed by ID.

---

## API Reference

All endpoints return JSON arrays of objects unless noted otherwise.

### Shared Conventions

- `base_url` comes from `payloads/environment_access.json`.
- Currency values must be rounded to 2 decimals.
- Percent and ratio values must be rounded to 4 decimals.
- Lists of IDs must be ascending (lexicographic) unless a rank field explicitly
  states descending order.
- Period labels `M1` through `M12` map to FY2024; `M13` through `M24` map to
  FY2025. Verify this against `/api/finance/period-map` on every task.

### Finance Endpoints

`GET /api/finance/branches`
: Array of `{ branch_id, branch_name, region_id, region_name }`. One object per
  branch (12 total).

`GET /api/finance/period-map`
: Array of `{ fiscal_year, month_name, month_number, period }`. Maps `M1`–`M24`
  to fiscal years. Confirm the FY2024/FY2025 split on every call.

`GET /api/finance/accounts`
: Array of `{ account, category, display_name, metric_type }`. Categories:
  `revenue`, `cogs`, `sga`, `allocations`, `operating`. The `operating`
  category includes counts (`active_customers`, `labor_headcount`,
  `admin_headcount`, `orders`, `revenue_units`, `backlog`) that are not
  currency-valued.

`GET /api/finance/records`
: Array of `{ account, branch_id, branch_name, region_id, values }`. `values`
  is a dict keyed by period label (`M1`–`M24`) with numeric values. There is
  one record object per (`branch_id`, `account`) pair.

**Finance account composition rules:**

| Output field | Source accounts (summed per period) |
|---|---|
| `revenue` | `product_revenue` + `service_revenue` |
| `cogs` | `direct_materials_cogs` + `direct_labor_cogs` |
| `gross_margin` | `revenue` − `cogs` |
| `sga` | `sales_sga` + `admin_sga` + `occupancy_sga` |
| `allocations` | `shared_service_allocations` |
| `ebitda` | `revenue` − `cogs` − `sga` − `allocations` |

For any fiscal-year aggregation, sum each account’s values over the relevant
period range, then apply the composition rules to the aggregated account
totals. The `/api/manifest` `branches` array is authoritative for branch
metadata; use `/api/finance/branches` as a live cross-check.

### Compensation Endpoints

`GET /api/compensation/rate-book`
: Single object (not an array):

```json
{
  "business_rules": ["..."],
  "current_year": 2026,
  "minimum_weekly_scale": 2520.0,
  "pay_types": ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"],
  "quarter_weeks": { "Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13 },
  "seniority_weekly": [
    { "min_years": 0,  "max_years": 4,  "weekly_amount": 0.0 },
    { "min_years": 5,  "max_years": 9,  "weekly_amount": 48.0 },
    { "min_years": 10, "max_years": 14, "weekly_amount": 82.0 },
    { "min_years": 15, "max_years": 19, "weekly_amount": 126.0 },
    { "min_years": 20, "max_years": 24, "weekly_amount": 170.0 },
    { "min_years": 25, "max_years": null, "weekly_amount": 215.0 }
  ],
  "title_premium_pct": {
    "Concertmaster": 0.22,
    "Principal": 0.20,
    "Section Lead": 0.15,
    "Associate Principal": 0.10,
    "Assistant Principal": 0.10
  }
}
```

`GET /api/compensation/rosters`
: Array of employee objects. Each has:
  `employee_id`, `ensemble_id`, `ensemble_name`, `title` (string or null),
  `years_of_service` (int), `overscale_weekly` (float),
  `combined_overscale_includes_title` (bool), `notes` (string),
  `weeks_by_quarter` (dict of `Q1`–`Q4` → int, normally 13 but may be less
  for partial-quarter employees).

`GET /api/compensation/scenarios`
: Single object mapping scenario IDs to growth parameters:

```json
{
  "case_maple_board": {
    "year_plus_1": {
      "mws_growth": 0.035, "overscale_growth": 0.012,
      "seniority_growth": 0.018, "title_pct_multiplier": 1.0
    },
    "year_plus_2": {
      "mws_growth": 0.033, "overscale_growth": 0.014,
      "seniority_growth": 0.02, "title_pct_multiplier": 1.0
    }
  }
}
```

### Payroll Endpoints

`GET /api/payroll/rate-book`
: Single object:

```json
{
  "business_rules": ["..."],
  "conflict_thresholds": {
    "rehearsal_earliest_start": "09:00",
    "rehearsal_latest_end": "18:30"
  },
  "premium_pct": {
    "electronic": 0.25,
    "principal_or_lead": 0.15,
    "concertmaster": 0.20,
    "quartet": 0.15,
    "first_double": 0.25,
    "additional_double": 0.10,
    "vacation": 0.04
  },
  "service_rates": {
    "Performance": 260.25,
    "Audit": 260.25,
    "Rehearsal": 58.75,
    "1hr Sound Check": 80.0,
    "2hr Sound Check": 142.5
  },
  "service_time_limits": {
    "Performance": 3.0,
    "Audit": 3.0,
    "Rehearsal": 5.0,
    "1hr Sound Check": 1.0,
    "2hr Sound Check": 2.0
  },
  "weekly_guarantee": 2082.0
}
```

`GET /api/payroll/productions`
: Array of production objects. Each has `production_id`, `roster` (array of
  musician objects), and `schedule` (array of service objects).

Musician object:
  `musician_id`, `name`, `instrument`, `assigned_service_ids` (array of
  strings), `doubles` (int, extra instruments count), `electronic` (bool),
  `lead` (bool), `principal` (bool), `quartet` (bool), `substitute` (bool),
  `vacation_eligible` (bool).

Schedule service object:
  `service_id`, `date`, `service_type` (one of `Performance`, `Audit`,
  `Rehearsal`, `1hr Sound Check`, `2hr Sound Check`), `start_time` (HH:MM),
  `end_time` (HH:MM), `duration_hours` (float).

---

## Task Domain: Branch Close Reporting

When the task asks for a branch close package (pulls from finance endpoints):

**Period convention.**
Read the period map. `M1`–`M12` → `FY2024`, `M13`–`M24` → `FY2025`.
The `period_convention` output object maps these keys literally:
`"M1_to_M12"`, `"M13_to_M24"`, `"current_month"` (the close period label, e.g.
`"M24"`), `"prior_month"` (the prior period label, e.g. `"M23"`).

**Single-period income statement.**
For the close period (e.g. `M24`), look up each account’s value for that
period on the target branch. Sum the constituent accounts per the composition
table, then compute `gross_margin` and `ebitda`. Round all six line items to 2
decimals.

**Month-over-month revenue variance.**
`amount` = `revenue[close_period]` − `revenue[prior_period]`.
`pct` = `amount` / `revenue[prior_period]`. Round amount to 2 decimals, pct to
4 decimals. If prior-period revenue is zero, omit or handle as undefined.

**Fiscal-year comparison.**
For each account, sum its values over `M1`–`M12` (FY2024) and `M13`–`M24`
(FY2025). Apply the composition rules to the aggregated sums. Output
`fy2025_vs_fy2024` with:

- `fy2025` block: `revenue`, `cogs`, `gross_margin`, `sga`, `allocations`,
  `ebitda` (all currency), plus computed ratios:
  - `ebitda_margin` = `fy2025.ebitda` / `fy2025.revenue` (4 decimals)
  - `arpu` = `fy2025.revenue` / sum of `active_customers` across `M13`–`M24`
    for the target branch (currency, 2 decimals)
  - `sales_per_labor_headcount` = `fy2025.revenue` / sum of `labor_headcount`
    across `M13`–`M24` for the target branch (currency, 2 decimals)
- `revenue_growth_pct` = (`fy2025.revenue` − `fy2024.revenue`) /
  `fy2024.revenue` (4 decimals)
- `ebitda_growth_pct` = (`fy2025.ebitda` − `fy2024.ebitda`) /
  `fy2024.ebitda` (4 decimals)

**Region context.**
Use the branches endpoint to find the target branch’s `region_id`. Collect all
branch IDs in that region (ascending). For each regional branch, compute its
`fy2025.ebitda`. Sum these for `fy2025_ebitda` (the regional total). Rank the
target branch’s `fy2025.ebitda` within the region **descending**
(largest = 1). The `ebitda_rank_desc` is an integer. Output `region_id` as a
string, `branch_ids` as the ascending list, `fy2025_ebitda` (currency, 2
decimals), and `ebitda_rank_desc`.

**Branch rankings (all branches, all regions).**
Compute for every branch:

1. Sales growth = (`fy2025.revenue` − `fy2024.revenue`) / `fy2024.revenue`.
2. ARPU = `fy2025.revenue` / sum of `active_customers` over `M13`–`M24`.

Rank branches by sales growth descending. The target branch’s
`sales_growth_rank_desc` is its 1-based rank (1 = highest growth).
`top_sales_growth_branch_id` is the branch ID with rank 1.
`top_arpu_branch_id` is the branch ID with the highest ARPU (break ties by
ascending branch ID).

---

## Task Domain: Regional Reporting

When the task asks for a regional view (pulls from finance endpoints):

Compute FY2024 and FY2025 aggregates across **all branches** in the target
region. Sum each account across those branches over the appropriate period
range, then apply the composition rules.

- `branch_ids`: ascending list of branch IDs in the region.
- `fy2024` block: `revenue`, `sga`, `allocations`, `ebitda`.
- `fy2025` block: `revenue`, `sga`, `allocations`, `ebitda`, plus
  `ebitda_margin` and `sales_per_labor_headcount` computed from the regional
  aggregates (same formulas as branch-level, applied at region level).
- `revenue_growth_pct`: regional (`fy2025.revenue` − `fy2024.revenue`) /
  `fy2024.revenue`.
- `top_ebitda_branch_id`: branch in the region with the highest
  `fy2025.ebitda` (break ties by ascending branch ID).
- `bottom_ebitda_branch_id`: branch in the region with the lowest
  `fy2025.ebitda` (break ties by ascending branch ID).
- `region_reconciliation_variance`: (`fy2025.revenue` − `fy2025.cogs` −
  `fy2025.sga` − `fy2025.allocations`) − `fy2025.ebitda`. This must equal
  0.0 when the composition rules are applied correctly; report it as a
  currency value rounded to 2 decimals.

---

## Task Domain: Compensation Summary (Current Year)

When the task asks for a current-year ensemble compensation summary (pulls
from compensation endpoints):

**Roster scope.** Filter `/api/compensation/rosters` to the requested
`ensemble_id`. `roster_count` is the total number of employee objects for that
ensemble.

**Pay computation.** For each employee and each quarter (`Q1`–`Q4`):

1. `weeks` = `weeks_by_quarter[quarter]` from the roster.
2. `base` = `minimum_weekly_scale` × `weeks`.
3. `title_premium`: if the employee has a non-null `title` **and**
   `combined_overscale_includes_title` is **false**, then
   `title_premium` = `base` × `title_premium_pct[title]`. Otherwise 0.
   If `combined_overscale_includes_title` is true, the overscale amount
   already covers the title premium — add nothing separately.
4. `seniority`: look up the employee’s `years_of_service` in the
   `seniority_weekly` band where `min_years` ≤ YOS ≤ `max_years` (use
   `max_years: null` as unbounded). `seniority` = `weekly_amount` × `weeks`.
5. `overscale` = `overscale_weekly` × `weeks`.
6. Employee quarter total = `base` + `title_premium` + `seniority` + `overscale`.

**Aggregation.**

- `quarter_totals[Q]` = sum of employee quarter totals for that quarter.
- `annual_pay_type_totals` = sum across all employees and all quarters of:
  - `"Minimum Weekly Scale"` ← all `base` amounts
  - `"Titled Position Premium"` ← all `title_premium` amounts
  - `"Seniority"` ← all `seniority` amounts
  - `"Overscale"` ← all `overscale` amounts
- `annual_total` = sum of all four pay-type totals (equals sum of quarter totals).
- `pay_types`: the ordered list `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`.
- `current_year`: from the rate book.

**Treatment counts.**

- `combined_overscale_employee_count`: number of employees where
  `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count`: number of employees where any quarter’s
  `weeks_by_quarter` value is less than the rate-book `quarter_weeks` value (13).

**Largest pay type.** Compare the four `annual_pay_type_totals` values. The
enum string for the largest is one of `"Minimum Weekly Scale"`, `"Titled
Position Premium"`, `"Seniority"`, `"Overscale"`. Break ties by the order
given in `pay_types`.

---

## Task Domain: Compensation Forecast

When the task asks for a forecast (pulls from compensation endpoints plus
`/api/compensation/scenarios`):

Start with the current-year computation as described above, but do it
**across all roster employees** for the target `ensemble_id` using current
rate-book values and current `years_of_service`.

**Forecast years.** Read the scenario object from
`/api/compensation/scenarios` using the `scenario_id` from the request memo.
Each forecast year (Year + 1, Year + 2) applies growth factors to the
**current-year** baseline. Follow the rate-book business rule: before
assigning a seniority band, add 1 year of service for Year + 1 and 2 years
for Year + 2. All other employee attributes (weeks, titles, overscale amounts,
flags) carry forward unchanged except where growth factors apply.

For Year + N:
1. `mws` = `minimum_weekly_scale` × (1 + `year_plus_N.mws_growth`).
   Apply cumulatively: Y+1 MWS = current × (1 + g1); Y+2 MWS = Y+1 MWS × (1 + g2).
2. `title_premium_pct` for each title = original rate-book percentage ×
   `year_plus_N.title_pct_multiplier`. Only applied when
   `combined_overscale_includes_title` is false (unchanged rule).
3. `seniority`: recompute the band using (`years_of_service` + N). Multiply
   the band’s `weekly_amount` by (1 + `year_plus_N.seniority_growth`).
4. `overscale_weekly` = current overscale × (1 + `year_plus_N.overscale_growth`).

After computing pay for the baseline year and each forecast year, produce:

- `annual_totals`: `{ "current": ..., "year_plus_1": ..., "year_plus_2": ... }`
  (currency, 2 decimals).
- `growth_rates`: `year_plus_1_vs_current` = (Y+1 − current) / current;
  `year_plus_2_vs_year_plus_1` = (Y+2 − Y+1) / Y+1. Both 4 decimals.
- `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals`: computed
  from the Year + 2 scenario. Quarter totals are currency (2 decimals); pay
  type totals use the standard four keys.
- `largest_growth_pay_type`: compare each pay type’s growth from
  **current** to **Year + 2** (`Y+2_pay_type` − `current_pay_type`). The enum
  string for the largest absolute growth. Break ties by the `pay_types` order.
- `combined_overscale_employee_count` and `partial_quarter_employee_count`:
  same definitions as the current-year summary, computed on the roster
  (these do not change across forecast years since roster composition is
  static).

---

## Task Domain: Payroll Review

When the task asks for a weekly payroll review (pulls from payroll endpoints):

**Service counts.** Iterate the production’s `schedule`. Count occurrences
of each `service_type`. Map service types to the exact string keys used in
`service_counts`:
`Performance`, `Audit`, `Rehearsal`, `1hr Sound Check`, `2hr Sound Check`.
Only include types that appear at least once.

**Per-musician computation.** For each musician in the production’s `roster`:
iterate over their `assigned_service_ids`. For each service ID, look up the
schedule entry.

**Base service pay.** The base amount depends on service type:

- `Performance`, `Audit`, `1hr Sound Check`, `2hr Sound Check`: flat
  `service_rates[service_type]` per service.
- `Rehearsal`: hourly rate `service_rates["Rehearsal"]` multiplied by
  `max(duration_hours, 3.0)` (three-hour minimum call).

**Premiums.** Premium percentages are applied to the **base service pay** of
each individual service. A musician may qualify for multiple premiums on the
same service; compute each independently and sum them:

| Condition | Premium |
|---|---|
| `electronic` is true | `premium_pct.electronic` × base |
| `principal` is true or `lead` is true | `premium_pct.principal_or_lead` × base (do not double-count if both are true) |
| `quartet` is true | `premium_pct.quartet` × base |

Note: `premium_pct.concertmaster` (20%) is **not applied** during payroll —
the concertmaster premium only applies in compensation. The payroll
`principal_or_lead` premium covers lead and principal designations.

**Doubles.** When `doubles` > 0:
- First extra instrument: `premium_pct.first_double` × base.
- Each additional extra instrument (`doubles` − 1, if any):
  `premium_pct.additional_double` × base per instrument.
- Total doubles premium = base × `first_double` + base × (`doubles` − 1) × `additional_double`
  (when `doubles` ≥ 2; when `doubles` = 1, only the first_double term).

**Vacation.** If `vacation_eligible` is true, add `premium_pct.vacation` ×
(base service pay + sum of all premiums and doubles). Vacation applies to
the total of base, premium, and doubles for the service. Vacation is computed
per-service, not lump-sum.

**Guarantee adjustment.** For musicians where `substitute` is **false**, sum
their base service pay (before premiums, doubles, and vacation) across all
assigned services. If this total is less than `weekly_guarantee`:
`guarantee_adjustment` = `weekly_guarantee` − total base service pay. Round
to 2 decimals. Substitute musicians never receive a guarantee adjustment.

**Substitute adjustment.** For musicians where `substitute` is **true**, add a
`substitute_adjustment` equal to `weekly_guarantee / 4` (rounded to 2
decimals). This amount also earns the musician’s applicable premiums and
doubles: apply the same premium and doubles percentages to the
substitute_adjustment amount and include those amounts in the `premium` and
`doubles` category totals for that musician.

**Category bucketing (per-musician).** Each component of a musician’s pay is
mapped to a category key:

| Component | Category key |
|---|---|
| Base pay for Performance services | `performance` |
| Base pay for Audit services | `audit` |
| Base pay for Rehearsal services | `rehearsal` |
| Base pay for 1hr/2hr Sound Check services | `sound_check` |
| Sum of all premium amounts (electronic, principal_or_lead, quartet) | `premium` |
| Sum of all doubles amounts | `doubles` |
| Sum of all vacation amounts | `vacation` |
| Guarantee adjustment (non-substitutes only) | `guarantee_adjustment` |
| Substitute adjustment (substitutes only) | `substitute_adjustment` |

The `per_musician[].categories` object includes only nonzero categories.
`per_musician[].total` is the sum of all categories for that musician. Order
`per_musician` by `musician_id` ascending.

**Category totals (production-level).** Sum each category across all
musicians.

**Weekly total.** Sum of all per-musician totals, or equivalently the sum of
all category totals.

**Top-paid musician.** The musician with the highest `total`. Break ties by
ascending `musician_id`.

**Conflict flags.** Inspect the production `schedule`:

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any Rehearsal service with `start_time` < `rehearsal_earliest_start` ("09:00"). Compare times lexicographically as HH:MM strings. |
| `REHEARSAL_LATE_END` | Any Rehearsal service with `end_time` > `rehearsal_latest_end` ("18:30"). |
| `SERVICE_OVER_TIME_LIMIT` | Any service where `duration_hours` > `service_time_limits[service_type]`. |
| `SOUND_CHECK_DURATION_MISMATCH` | Any Sound Check service whose actual `duration_hours` does not match the expected duration in the service type name: `1hr Sound Check` expects 1.0 hours, `2hr Sound Check` expects 2.0 hours. Compare as floats (treat matching within 0.01 as equal). |

Only include flags that actually fire. Sort the `conflict_flags` list
alphabetically.

---

## Task Workflow

1. Read `payloads/environment_access.json` for the base URL.
2. Read `payloads/request_memo.json` for the specific request parameters.
3. Read `payloads/answer_template.json` for the required output schema.
4. Call `GET {base_url}/api/manifest` to confirm available endpoints and
   entity inventory.
5. Determine which domain the task belongs to from the memo `request_id`
   prefix (`BR_CLOSE`, `COMP_CURRENT`, `COMP_FORECAST`, `PAYROLL_REVIEW`,
   `REGIONAL_VIEW`) and the available endpoints listed in the environment
   access payload. Use only the endpoints listed in that payload — the
   manifest may list more than are available to the current task.
6. Fetch all needed endpoint data. Use the live API; never cache or
   fabricate values. Aggregate, compute, and format according to the
   domain rules above.
7. Round currency to 2 decimals and percentages/ratios to 4 decimals.
8. Return a single JSON object matching the required top-level keys from
   the answer template, with all fields typed as specified.
