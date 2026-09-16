---
name: skill
description: Solve Crescent Finance Ops reporting tasks that require reading `request_memo.json`, `answer_template.json`, and `environment_access.json` to produce one JSON object for branch close, regional management, compensation summaries or forecasts, or weekly payroll reviews. Use when the user mentions Crescent Arts Collective, Crescent Finance Ops, branch or region EBITDA reports, compensation by quarter and pay type, payroll packages, or any similar JSON report built from the Finance Ops API.
---

# Crescent Finance Ops Reporting

## Workflow

1. Read the prompt, request memo, answer template, and environment access payload.
2. Identify the task family from the template and memo.
3. Fetch only the live endpoints needed for that family.
4. Compute from live data, not from memo notes or draft workbook hints.
5. Return one JSON object only.

## Task Families

### Finance branch close and regional reporting

Use:
- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

Treat `/api/finance/period-map` as the source for fiscal year boundaries. In these tasks, `M1`-`M12` map to FY2024 and `M13`-`M24` map to FY2025.

Compute the core financial statements from the account categories in the live data. Revenue is product revenue plus service revenue. COGS is direct materials plus direct labor. Gross margin is revenue minus COGS. SG&A is sales plus admin plus occupancy. EBITDA is gross margin minus SG&A minus allocations.

Compute operating ratios from the same fiscal slice. ARPU is revenue divided by active customers. Sales per labor headcount is revenue divided by labor headcount. Compute growth rates as `(later - earlier) / earlier`.

Treat branch rankings as global across the branch set unless the memo explicitly narrows the scope. Use the region list only for `region_context`, and rank region EBITDA against all regions when a rank is requested.

### Compensation summaries and forecasts

Use:
- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios`

Keep the pay-type order from the rate book. Apply the live minimum weekly scale, title premium percentages, seniority bands, overscale weekly amounts, and scenario multipliers instead of hardcoding them.

Use the roster `weeks_by_quarter` values as the quarter lengths. Do not assume every quarter is the same when a roster row says otherwise. If `combined_overscale_includes_title` is true, do not add a separate title premium for that employee.

For forecasts, add one year of service for Year + 1 and two years of service for Year + 2 before selecting the seniority band.

Count `combined_overscale_employee_count` from roster rows with `combined_overscale_includes_title = true`. Count `partial_quarter_employee_count` from roster rows with any quarter below the standard quarter length.

### Payroll reviews

Use:
- `/api/payroll/rate-book`
- `/api/payroll/productions`

Count service rows from the production schedule by `service_type`. Derive category totals and per-musician totals from the schedule, roster, and live rate book. Keep `per_musician` sorted by `musician_id`. Keep `conflict_flags` sorted alphabetically and limited to the flag values named in the template.

Pick `top_paid_musician_id` from the highest per-musician total. Break ties by stable `musician_id` order.

## Formatting Rules

- Match the template's required top-level keys exactly.
- Round currency values to 2 decimals and percent or ratio values to 4 decimals at the end of the calculation.
- Preserve any list ordering the template specifies. Otherwise use ascending stable IDs.
- Output one JSON object only, with no prose or code fences.

## Reference

See [references/playbook.md](references/playbook.md) for endpoint mapping, formulas, and common checks.
