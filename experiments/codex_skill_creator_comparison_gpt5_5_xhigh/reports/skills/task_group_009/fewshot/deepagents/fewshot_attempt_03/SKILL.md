---
name: crescent-finance-ops
description: Compute Crescent Finance Ops reporting answers from staged task inputs and the Finance Ops API. Use when a task asks for Crescent Arts Collective branch close, regional management, compensation summary or forecast, or touring theatre weekly payroll JSON using payloads/environment_access.json, payloads/request_memo.json, and payloads/answer_template.json.
---

# Crescent Finance Ops

## Workflow

1. Read the task prompt, `payloads/request_memo.json`, `payloads/environment_access.json`, and `payloads/answer_template.json`.
2. Use the base URL in the environment payload. If it is a placeholder, use the task-provided environment URL or pass it with `--base-url`.
3. Prefer the bundled calculator for the report families covered by this skill:

```bash
python3 skill/scripts/finance_ops_solver.py /path/to/task/input --base-url "$TASK_ENV_BASE_URL"
```

The script accepts either the `input/` directory or its parent task directory. It prints one JSON object to stdout.

4. Compare the emitted keys against `answer_template.json`. If the template requests fields outside this skill's known report families, fetch the same endpoints and extend the calculation manually rather than guessing.

## Report Logic

Use active API data, not memo notes or draft workbook references, as the source of truth.

For finance branch and regional reports:

- Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.
- Map account categories from `/api/finance/accounts`.
- Revenue is the sum of revenue-category accounts. COGS, SG&A, and allocations are category sums.
- Gross margin is `revenue - cogs`. EBITDA is `gross_margin - sga - allocations`.
- Fiscal-year totals are sums over the periods mapped to that fiscal year.
- EBITDA margin is `ebitda / revenue`.
- ARPU is `revenue / active_customers`.
- Sales per labor headcount is `revenue / labor_headcount`.
- Growth percentages are `(current - prior) / prior`.
- Branch rankings sort descending by the requested metric, with stable ascending IDs for ties.
- In branch close regional context, EBITDA rank is the target region's FY EBITDA rank among all regions.

For compensation reports:

- Fetch `/api/compensation/rate-book`, `/api/compensation/rosters`, and `/api/compensation/scenarios` when forecasting.
- Use each roster row's `weeks_by_quarter`; do not assume fixed 13-week quarters for employees with partial-quarter service.
- Pay types are emitted in rate-book order.
- Minimum weekly scale equals `minimum_weekly_scale * weeks`.
- Titled position premium equals grown minimum weekly scale times the title percentage times weeks, unless `combined_overscale_includes_title` is true.
- Seniority uses the rate-book band for years of service. Forecasts add one year of service for Year + 1 and two years for Year + 2 before assigning the band.
- Overscale equals `overscale_weekly * weeks`.
- Forecast growth factors are cumulative: apply Year + 1 factors, then apply Year + 2 factors on top for Year + 2. Scenario title multipliers multiply the title percentage.
- Annual compensation totals reconcile to the sum of rounded quarter totals; pay-type totals are rounded independently.
- `largest_growth_pay_type` is the pay type with the largest percentage increase from current to Year + 2.

For payroll reports:

- Fetch `/api/payroll/rate-book` and `/api/payroll/productions`.
- Rehearsals are hourly with a 3-hour minimum call. Performance, audit, and sound check rates are per service.
- Weekly guarantee adjustment applies to non-substitute players when base service pay is below `weekly_guarantee`; test only base service pay, before premiums, doubles, vacation, or guarantee.
- Premiums and doubles are calculated from base service pay, including any substitute performance adjustment.
- Doubles use 25% for the first extra instrument and 10% for each additional extra instrument.
- Vacation is 4% of base service pay plus premiums and doubles when `vacation_eligible` is true.
- Substitute adjustment is a paid performance minimum: add the shortfall to six performance services to both `performance` and `substitute_adjustment`.
- Conflict flags are sorted alphabetically.

## Output Rules

- Return a single JSON object and no prose.
- Round currency to 2 decimals.
- Round percentages and ratios to 4 decimals.
- Sort stable ID lists ascending unless a rank field states otherwise.
- Sort `per_musician` by `musician_id`; include only nonzero categories in each musician's category object.
