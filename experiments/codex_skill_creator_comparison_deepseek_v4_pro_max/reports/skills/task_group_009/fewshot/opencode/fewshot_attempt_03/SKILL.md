---
name: crescent-finance-ops
description: Query and compute Crescent Arts Collective financial reports from the Finance Ops API. Use this skill whenever the user asks about Crescent finance data, branch close packages, regional reporting, compensation summaries, payroll reviews, board forecasts, ensemble costs, production payroll, or any task that mentions the Finance Ops API, Crescent Arts Collective, or related finance/compensation/payroll endpoints. Triggers on anything involving branch management reporting, ensemble compensation, touring production payroll, or scenario-based forecasting for Crescent.
---

# Crescent Finance Ops

Use the Crescent Finance Ops API to fetch live operational data and build
accurate financial reports. The API serves three domains: **finance** (branch
and regional P&L), **compensation** (ensemble rate books, rosters, and
forecast scenarios), and **payroll** (production schedules and musician
payroll).

## Quick-start workflow

Every task follows the same four-step skeleton. Resist jumping to conclusions
before the data arrives.

1. **Read the task payloads** -- always read the request memo and answer
   template first; they define what to compute and exactly what shape to return.
2. **Fetch all relevant API endpoints in parallel** -- the API returns full
   datasets with no filtering, so you can fetch everything you need in one
   round. Use the base URL from `environment_access.json`.
3. **Compute every field the answer template requires** -- round currencies to
   2 decimals and percentages/ratios to 4 decimals; sort lists ascending by
   stable ID unless a rank field says otherwise.
4. **Return a single JSON object** matching the template's `required_top_level_keys`,
   `field_types`, and any sorting or rounding rules in its `description`.

If a task includes `scenario_id`, you are doing compensation *forecasting* -- see
[references/business-rules.md](references/business-rules.md) for the growth
application rules.

## Module 1 -- Finance (branch / regional P&L)

**Endpoints:** `/api/manifest`, `/api/finance/branches`, `/api/finance/period-map`,
`/api/finance/accounts`, `/api/finance/records`

### Period convention (fixed)

| Range | Fiscal Year |
|-------|-------------|
| M1 -- M12 | FY2024 |
| M13 -- M24 | FY2025 |

This convention never varies. The period-map endpoint confirms it and provides
month-name mappings.

### Account categories and aggregation

The accounts endpoint lists every account with its `category` and `metric_type`.
Currency accounts aggregate by category:

| Top-level line | Sum of these accounts |
|---|---|
| `revenue` | `product_revenue` + `service_revenue` |
| `cogs` | `direct_materials_cogs` + `direct_labor_cogs` |
| `gross_margin` | `revenue` - `cogs` |
| `sga` | `sales_sga` + `admin_sga` + `occupancy_sga` |
| `allocations` | `shared_service_allocations` |
| `ebitda` | `gross_margin` - `sga` - `allocations` |

Operating (count) accounts are outside this hierarchy. Use `labor_headcount`
for `sales_per_labor_headcount` and `revenue_units` for ARPU. Use the *current*
fiscal year's total revenue / corresponding count for these ratios.

### Building a branch close package

1. Fetch branches, period-map, accounts, and records in parallel.
2. From the request memo, note `target_branch_id` and `close_period`.
3. For the income statement: filter records to the target branch and close
   period, then aggregate by category as above.
4. For MoM revenue variance: compute `close_period` revenue minus `close_period-1`
   revenue (M23 if close is M24, etc.); the `pct` is amount / prior-period revenue.
5. For FY2025 vs FY2024: sum all M13-M24 values per account for FY2025, all
   M1-M12 for FY2024; aggregate to categories; compute growth rates as
   `(FY2025 - FY2024) / FY2024`. Ratios like `ebitda_margin` =
   FY2025 ebitda / FY2025 revenue. `arpu` = FY2025 revenue /
   FY2025 `revenue_units`. `sales_per_labor_headcount` = FY2025 revenue /
   FY2025 `labor_headcount`.
6. For branch rankings: compute every branch's FY2025 revenue growth (M13-M24
   vs M1-M12); sort descending to get the rank number and the top branch ID.
   For ARPU, compute per-branch FY2025 ARPU and find the max.

### Building a regional report

Same as branch close but aggregated across all branches in the region.

1. Use the branches endpoint to find all `branch_id` values belonging to
   `target_region_id`. Sort them ascending.
2. Sum records across those branches for aggregate region totals.
3. The reconciliation variance is always zero when all region branches are
   included (the API is single-source and self-consistent).
4. For per-branch EBITDA within the region: compute each branch's FY2025
   ebitda and identify top / bottom.

## Module 2 -- Compensation (ensemble cost summaries)

**Endpoints:** `/api/compensation/rate-book`, `/api/compensation/rosters`,
`/api/compensation/scenarios`

The rate book defines the pay structure; rosters define who gets what.
[references/business-rules.md](references/business-rules.md) documents every
calculation rule with examples. Read it before computing any compensation
figures.

### Core compensation calculation (single employee)

For each employee on the roster, compute their annual total as the sum of four
pay-type lines over four quarters:

```
quarter_pay = quarter_weeks × pay_type_weekly_rate
```

Where the four pay types are always (in order):

1. **Minimum Weekly Scale** -- the rate book's `minimum_weekly_scale` amount.
2. **Titled Position Premium** -- `minimum_weekly_scale × title_premium_pct[employee.title]`,
   unless `combined_overscale_includes_title` is true (then zero).
3. **Seniority** -- the `weekly_amount` from the `seniority_weekly` band whose
   range encloses the employee's `years_of_service`.
4. **Overscale** -- the employee's `overscale_weekly` amount (zero unless
   otherwise listed).

With `combined_overscale_includes_title: true`, the overscale amount already
covers the title premium, so do not add titled position premium separately.

When `weeks_by_quarter` differs from the flat 13-week default, pro-rate each
quarter using the roster's actual quarter weeks.

### Building a current-year compensation summary

1. Fetch the rate book and all rosters in parallel.
2. Filter roster to the requested `ensemble_id`.
3. Compute each employee's annual total as above, summing over all four
   quarters.

**Roster counts to report:**

- `roster_count` -- total employees on the filtered roster.
- `combined_overscale_employee_count` -- employees where
  `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count` -- employees where any quarter has fewer
  or more weeks than the rate book's `quarter_weeks` default. Do not count
  zero-week quarters; count only employees with a non-zero variance from the
  default (currently 13).

### Building a compensation forecast

1. Fetch the rate book, all rosters, and the scenarios object in parallel.
2. Filter roster to the requested `ensemble_id`.
3. Look up the named scenario under `scenario_id`.

For each forecast year:

- **Current year**: compute exactly like the current-year summary above.
- **Year + 1**: apply `year_plus_1` growth factors to the rate book, add one
  year to each employee's `years_of_service` before assigning seniority bands,
  and recompute all pay types.
- **Year + 2**: apply `year_plus_2` growth factors on top of Year + 1 values,
  add two years total to each employee's `years_of_service`, and recompute.

[references/business-rules.md](references/business-rules.md) has the detailed
step-by-step for applying growth.

## Module 3 -- Payroll (weekly production payroll)

**Endpoints:** `/api/payroll/rate-book`, `/api/payroll/productions`

[references/business-rules.md](references/business-rules.md) documents the full
payroll calculation rules. Read it before computing payroll figures.

### Payroll calculation (single musician, single service)

For each assigned service on the production schedule:

1. **Base pay** -- the `service_rates` value for that service type.
2. **Premiums** -- sum `principal_or_lead` (15% if principal or lead),
   `concertmaster` (20% if `concertmaster_role`), `quartet` (15% if
   `quartet`), `electronic` (25% if `electronic`), and doubles
   (`first_double` 25% for 1 double, plus `additional_double` 10% for each
   beyond the first). All percentages apply to the base service rate.
3. **Vacation** -- 4% of (base + all premiums) when `vacation_eligible` is true.
4. **Guarantee adjustment** -- for guaranteed regular players only (not
   substitutes): if the musician's total base pay + premiums + vacation across
   all their services is below the `weekly_guarantee`, add the difference.
5. **Substitute adjustment** -- for substitute musicians only: substitute pay
   equals the base rate for each assigned service (no premiums, no vacation,
   no guarantee). This is a *replacement* for their line, not additive.

### Conflict flags (CBA compliance)

Check the schedule against `conflict_thresholds` in the rate book:

| Flag | Condition |
|------|-----------|
| `REHEARSAL_EARLY_START` | Any Rehearsal `start_time` is before `rehearsal_earliest_start` |
| `REHEARSAL_LATE_END` | Any Rehearsal `end_time` is after `rehearsal_latest_end` |
| `SERVICE_OVER_TIME_LIMIT` | Any service's actual duration exceeds its type's `service_time_limits` |
| `SOUND_CHECK_DURATION_MISMATCH` | A sound check service duration differs from its labeled length (1hr vs 2hr) |

Sort flags alphabetically. Only include flags that actually fire on the
schedule.

## Common patterns

### API data shape

Every endpoint returns a JSON array (or dict for `/api/compensation/scenarios`).
There is no pagination, no query parameters, no filtering. Fetch everything and
filter locally.

The `/api/manifest` endpoint lists available entities but is optional -- the
dedicated endpoints are the authoritative data sources.

### Per-account records structure

Each record in `/api/finance/records` looks like:

```json
{
  "account": "product_revenue",
  "branch_id": "BR-004",
  "branch_name": "Harbor North",
  "region_id": "REG-WEST",
  "values": { "M1": 100.0, "M2": 110.0 }
}
```

To aggregate: sum `values[period]` across the relevant accounts and branches.

### Rounding rules (always apply)

- Currency fields: `round(x, 2)`
- Percent fields (pct, margin, growth): `round(x, 4)`
- Count fields (headcount, integer counts): integers -- no rounding needed

### Sorting rules (always apply)

- Lists of IDs (branch_ids, pay_types): ascending by stable ID string unless
  a `_rank_desc` field says otherwise.
- `per_musician` arrays: ordered by `musician_id` ascending.
- Pay type lists: always the canonical order: Minimum Weekly Scale, Titled
  Position Premium, Seniority, Overscale.

### Fetch order

Always fetch all needed endpoints in a single parallel round. The API is
stateless and read-only, so there is no ordering dependency. A typical finance
task needs branches + period-map + accounts + records; compensation needs
rate-book + rosters + (optionally) scenarios; payroll needs rate-book +
productions.

## Reference files

- **[references/api-schema.md](references/api-schema.md)** -- Full endpoint
  documentation, field schemas, and entity relationships for every API
  endpoint.
- **[references/business-rules.md](references/business-rules.md)** -- Detailed
  compensation and payroll calculation rules with worked examples. Read this
  before computing any ensemble costs or production payroll.
