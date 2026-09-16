---
name: crescent-finance-ops-reporter
description: Produce Crescent Arts Collective Finance Ops reporting JSON by fetching active API data and applying the staged finance, compensation, and payroll rules.
---

# Crescent Finance Ops Reporter

Use this skill when a task asks for a Crescent Arts Collective Finance Ops API reporting result and provides `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`.

## Preferred Solver

Run the bundled deterministic solver, [finance_ops_solver.py](finance_ops_solver.py), from the task `input/` directory or pass that directory explicitly:

```bash
python /path/to/skill/finance_ops_solver.py /path/to/input
```

The solver reads the memo and answer template, fetches only the business endpoints listed in `environment_access.json`, infers the report type, and prints the final JSON object to stdout. If `payloads/environment_access.json` contains a placeholder base URL, set `TASK_ENV_BASE_URL` or rely on the local default task service URL.

Before finalizing, verify that the emitted top-level keys match `answer_template.json` and return only the JSON object.

## Core Rules

- Treat API data as authoritative over memo notes or workbook/background language.
- Currency values use half-up rounding to 2 decimals. Percent and ratio fields use half-up rounding to 4 decimals. Percent fields are decimal ratios, not multiplied by 100.
- Stable ID lists sort ascending unless a rank field explicitly ranks by a metric. Descending rankings sort by metric descending and then stable ID ascending for ties.
- Do not invent fields. Follow `required_top_level_keys` and the nested shape requested by `answer_template.json`.

## Finance Reports

Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.

- Sum record `values` by branch, account category, and requested period set.
- `revenue`, `cogs`, `sga`, and `allocations` come from account categories.
- `gross_margin = revenue - cogs`.
- `ebitda = gross_margin - sga - allocations`.
- Month-over-month revenue variance is current-period revenue less prior-period revenue, with percent over prior-period revenue.
- Fiscal-year comparisons use the fiscal year mapped from the current close period and the preceding fiscal year in the period map.
- `ebitda_margin = ebitda / revenue`.
- `arpu = revenue / active_customers`.
- `sales_per_labor_headcount = revenue / labor_headcount`.
- Branch sales-growth ranking uses fiscal-year revenue growth across all branches.
- Region EBITDA ranking uses current fiscal-year EBITDA summed by region.
- Regional report top/bottom EBITDA branches use current/latest requested fiscal-year EBITDA within the region.
- Region reconciliation variance is the aggregate region EBITDA less the sum of included branch EBITDA; with branch-level records this should reconcile to zero.

## Compensation Reports

Fetch `/api/compensation/rate-book`, `/api/compensation/rosters`, and, for forecasts, `/api/compensation/scenarios`.

- Use roster `weeks_by_quarter`; do not assume a fixed quarter length when roster weeks differ.
- Minimum weekly scale pay is `minimum_weekly_scale * weeks`.
- Title premium is `minimum_weekly_scale * title_premium_pct[title] * weeks`; skip it when `combined_overscale_includes_title` is true.
- Seniority pay uses the rate-book seniority band for `years_of_service`.
- Overscale pay is `overscale_weekly * weeks`.
- `combined_overscale_employee_count` counts roster rows with `combined_overscale_includes_title`.
- `partial_quarter_employee_count` counts roster rows whose `weeks_by_quarter` differs from the rate-book quarter pattern.
- Current-year largest pay type is the pay type with the largest annual total.
- Forecast Year + 1 and Year + 2 compound scenario growth from the prior year for minimum scale, seniority, and overscale. Add one and two service years before assigning seniority bands. Apply the title percent multiplier for the forecast year being calculated.
- Forecast annual totals are the sum of rounded quarter totals. Forecast largest-growth pay type is based on percent growth from current year to Year + 2.

## Payroll Reports

Fetch `/api/payroll/rate-book` and `/api/payroll/productions`.

- Count scheduled services by `service_type`.
- Performance, audit, and sound-check pay are per service. Rehearsal pay is hourly with a 3-hour minimum call per rehearsal.
- Map sound-check services to the `sound_check` category.
- Substitute musicians receive a two-performance-rate `substitute_adjustment`; include the same amount in base performance pay before percentage premiums.
- Percentage premiums apply to base service pay before vacation: principal or lead, quartet, electronic, and doubles. Doubles use the first-double rate for one extra instrument plus the additional-double rate for each extra instrument after the first.
- Weekly guarantee adjustment applies only to non-substitute players when base service pay is below the weekly guarantee.
- Vacation is applied to base service pay plus percentage premium plus doubles when `vacation_eligible` is true.
- Per-musician categories include only nonzero categories and sort musicians by `musician_id`.
- Conflict flags are unique and sorted alphabetically:
  - `REHEARSAL_EARLY_START` when a rehearsal starts before the threshold.
  - `REHEARSAL_LATE_END` when a rehearsal ends after the threshold.
  - `SERVICE_OVER_TIME_LIMIT` when any service duration exceeds its limit.
  - `SOUND_CHECK_DURATION_MISMATCH` when a sound-check duration differs from its named limit.
