---
name: crescent-finance-ops
description: Solve Crescent Finance Ops API reporting tasks that ask for one JSON object from request_memo.json and answer_template.json. Use for Crescent Arts Collective branch close packages, regional management views, compensation summaries and forecasts, and touring-theatre payroll reviews using the Finance Ops finance, compensation, or payroll endpoints.
---

# Crescent Finance Ops

Use this skill when the task provides an `input/payloads/` directory with `request_memo.json`, `answer_template.json`, and `environment_access.json` for the Crescent Finance Ops API.

## Fast Path

Run the bundled helper and then return the JSON object it prints:

```bash
python skill/scripts/solve_finance_ops.py <task-dir-or-input-dir> --base-url <base-url>
```

If the payload `environment_access.json` contains a real base URL, `--base-url` may be omitted. If it contains the placeholder `<TASK_ENV_BASE_URL>`, pass the URL from the task environment instructions or set `TASK_ENV_BASE_URL`.

The helper uses only Python standard-library modules. It detects the request type from `request_memo.json`, fetches only the relevant API endpoints, applies the reporting formulas, rounds values, and writes a single JSON object to stdout.

Before finalizing, compare the top-level keys and field names against `payloads/answer_template.json`. Return the JSON object only, with no markdown fence or explanation.

## Manual Rules

Use these rules if you need to inspect or adapt the helper logic.

Finance branch and regional reporting:

- Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.
- Sum monthly record values by branch, account, and requested fiscal-year periods. Account categories come from `/api/finance/accounts`.
- Compute `revenue` from revenue accounts, `cogs` from cogs accounts, `sga` from SG&A accounts, and `allocations` from allocation accounts.
- Compute `gross_margin = revenue - cogs`, `ebitda = gross_margin - sga - allocations`, `ebitda_margin = ebitda / revenue`, `arpu = revenue / active_customers`, and `sales_per_labor_headcount = revenue / labor_headcount`.
- Month-over-month revenue variance is current-period revenue minus prior-period revenue, with percent divided by prior-period revenue.
- Revenue and EBITDA growth percentages compare the later fiscal year to the earlier fiscal year.
- Branch rankings are descending by the requested metric with stable ID ordering for ties. Region branch lists use ascending branch IDs.

Compensation summaries and forecasts:

- Fetch `/api/compensation/rate-book` and `/api/compensation/rosters`; fetch `/api/compensation/scenarios` for forecast requests.
- Use each roster row's `weeks_by_quarter`; do not assume all employees worked fixed 13-week quarters.
- Minimum weekly scale pay is `minimum_weekly_scale * weeks`.
- Title premium is `minimum_weekly_scale * title_premium_pct[title] * weeks`, except rows where `combined_overscale_includes_title` is true.
- Seniority pay uses the seniority band for `years_of_service`. For forecast years, add one service year for Year + 1 and two service years for Year + 2 before selecting the band.
- Overscale pay is `overscale_weekly * weeks`.
- Forecast scale, overscale, and seniority growth compounds year by year. Apply each forecast year's `title_pct_multiplier` to the base title premium percentage for that year.
- `largest_pay_type` is the largest annual pay-type total. `largest_growth_pay_type` is the pay type with the largest percentage growth from current year to Year + 2.
- Count `combined_overscale_employee_count` from roster rows where `combined_overscale_includes_title` is true. Count `partial_quarter_employee_count` from rows whose weeks differ from the rate-book quarter weeks.

Payroll reviews:

- Fetch `/api/payroll/rate-book` and `/api/payroll/productions`.
- Performance, audit, and sound-check rates are per service. Rehearsal pay is hourly with a three-hour minimum call.
- For each musician, base service pay is the sum of assigned service amounts before premiums.
- Substitute rows receive a separate substitute adjustment equal to two performance-rate services; apply musician premiums and doubles to base service pay plus this substitute adjustment.
- Principal or lead, quartet, electronic, and concertmaster premiums are additive percentages of the premium base.
- Doubles are 25% for the first extra instrument and 10% for each additional extra instrument, applied to the premium base.
- Vacation is 4% of the premium base plus musician premiums and doubles when `vacation_eligible` is true.
- Weekly guarantee adjustment applies only to non-substitute players when base service pay is below the rate-book weekly guarantee. Calculate it from base service pay only.
- Conflict flags come from the schedule: rehearsal before the earliest start, rehearsal after the latest end, any service over its duration limit, and sound-check duration mismatches. Sort flags alphabetically.

## Rounding

Round currency values to 2 decimals. Round percentages and ratios to 4 decimals. Use final raw totals for totals, not the sum of already rounded displayed categories.
