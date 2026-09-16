---
name: crescent-finance-ops
description: Solve Crescent Finance Ops API reporting tasks for branch and regional finance, orchestra compensation summaries and forecasts, and weekly theatre payroll reviews from task payloads.
---

# Crescent Finance Ops

Use this skill when a task asks for a single JSON answer using Crescent Finance Ops payloads. The task input normally has:

- `payloads/environment_access.json` with the API base URL and allowed endpoints
- `payloads/request_memo.json` with the target branch, region, ensemble, scenario, or production
- `payloads/answer_template.json` with required keys, rounding, sorting, and field types

## Fast Path

Run the bundled solver from the task input directory:

```bash
python /work/skill/scripts/solve_finance_ops.py /path/to/input
```

It prints one JSON object. Before returning it, check that the top-level keys and list ordering match `answer_template.json`. If the payload base URL is a placeholder, the script falls back to `http://task-env:9009/`.

## Manual Rules

Use only the endpoints listed in the task payload. Currency fields are rounded to 2 decimals; percent and ratio fields are rounded to 4 decimals. Keep stable ID lists ascending unless a rank field says descending.

Finance branch and regional reporting:

- Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.
- Sum finance records by account category. `revenue = product/service revenue`; `cogs = direct materials/labor`; `sga = sales/admin/occupancy`; `allocations = shared service allocations`.
- `gross_margin = revenue - cogs`; `ebitda = gross_margin - sga - allocations`; `ebitda_margin = ebitda / revenue`.
- ARPU uses `revenue / active_customers`. Sales per labor headcount uses `revenue / labor_headcount`.
- Current fiscal year periods come from `period-map`; do not assume the close period alone is the fiscal-year total.
- Branch sales growth rankings compare current FY revenue against prior FY revenue across all branches, sorted descending with branch ID as the tie-breaker.
- Branch region context uses the target branch's region. Region EBITDA rank is the region's rank among all regions by current FY EBITDA, not the branch rank within the region.
- Regional top and bottom EBITDA branches are ranked within the target region for the latest requested fiscal year.

Compensation summaries and forecasts:

- Fetch `/api/compensation/rate-book`, `/api/compensation/rosters`, and, for forecasts, `/api/compensation/scenarios`.
- Use each roster row's `weeks_by_quarter`; do not force a fixed 13-week quarter when partial-quarter rows are present.
- For each employee and quarter:
  - Minimum weekly scale = rate-book minimum weekly scale times weeks.
  - Title premium = minimum weekly scale times the title premium percent times weeks, unless `combined_overscale_includes_title` is true.
  - Seniority = the rate-book seniority band for years of service times weeks.
  - Overscale = `overscale_weekly` times weeks.
- Count combined overscale rows where `combined_overscale_includes_title` is true. Count partial-quarter rows where any quarter weeks differ from the rate-book quarter weeks.
- Forecasts compound minimum-scale, overscale, and seniority growth year over year. Add one service year for Year + 1 and two service years for Year + 2 before selecting the seniority band. Apply `title_pct_multiplier` directly for the forecast year.
- For compensation annual totals, reconcile to rounded quarter totals when a cent-level rounding difference appears.
- `largest_growth_pay_type` is the pay type with the largest percentage growth from current annual pay-type total to Year + 2, using rate-book pay-type order as the tie-breaker.

Payroll reviews:

- Fetch `/api/payroll/rate-book` and `/api/payroll/productions`.
- Rehearsal pay is hourly with a 3-hour minimum call. Performance, audit, and sound-check pay are per service.
- Base service categories are `performance`, `audit`, `rehearsal`, and `sound_check`.
- Role premiums stack: principal or lead once, quartet, electronic, and any explicit concertmaster flag. Doubles are separate: first double plus additional double percentages from the rate book.
- Premiums are based on pre-vacation base service pay. Vacation is 4% of base service pay plus role and doubles premiums when `vacation_eligible` is true. Guarantees are based on base service pay before premiums and vacation.
- Non-substitute regular players receive `guarantee_adjustment = max(0, weekly_guarantee - base_service_pay)`.
- Substitute players receive a substitute adjustment equal to two performance services; include that amount in both `performance` and `substitute_adjustment`, and include it in the premium base.
- Conflict flags:
  - `REHEARSAL_EARLY_START` if any rehearsal starts before the rate-book earliest start.
  - `REHEARSAL_LATE_END` if any rehearsal ends after the latest end.
  - `SERVICE_OVER_TIME_LIMIT` if any service duration exceeds the service type limit.
  - `SOUND_CHECK_DURATION_MISMATCH` if a sound-check duration differs from its named duration.
