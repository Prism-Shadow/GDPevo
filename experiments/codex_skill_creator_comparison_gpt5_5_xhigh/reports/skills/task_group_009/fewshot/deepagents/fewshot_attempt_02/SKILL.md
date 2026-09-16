---
name: crescent-finance-ops-reporting
description: Use for Crescent Arts Collective Finance Ops API tasks that require a structured JSON reporting answer from finance, compensation, or payroll endpoints, including branch close packages, regional views, compensation summaries and forecasts, and weekly payroll reviews.
---

# Crescent Finance Ops Reporting

## Core Workflow

Use this skill when a task asks for Crescent Arts Collective management reporting from the Finance Ops environment.

1. Read the task prompt, `payloads/request_memo.json`, `payloads/answer_template.json`, and `payloads/environment_access.json`.
2. Resolve the API base URL from the task environment. Fetch only the endpoints listed for the task. If a memo references drafts, notes, or prior workbooks, treat them as context only and reconcile against active API data.
3. Build the answer from the template, not from memory. Preserve the required top-level keys, object names, list ordering, and rounding rules.
4. Do calculations in full precision, then round only final currency fields to 2 decimals and percent or ratio fields to 4 decimals. Sort stable ID lists ascending unless a rank field says otherwise.
5. Before returning JSON, verify subtotals reconcile: income statement formulas, annual totals vs quarter and pay-type totals, payroll category totals vs weekly total, and regional branch sums.

## API Shape

Finance endpoints:

- `/api/finance/branches`: branch metadata with branch and region IDs.
- `/api/finance/period-map`: maps period labels to fiscal years.
- `/api/finance/accounts`: maps account names to categories such as `revenue`, `cogs`, `sga`, `allocations`, and `operating`.
- `/api/finance/records`: one row per branch and account, with `values` keyed by period.

Compensation endpoints:

- `/api/compensation/rate-book`: current year, pay type order, weekly scale, title premiums, seniority bands, quarter weeks, and business rules.
- `/api/compensation/rosters`: employee rows with ensemble, title, years of service, overscale, combined-title treatment, and weeks by quarter.
- `/api/compensation/scenarios`: forecast growth factors by scenario and forecast year.

Payroll endpoints:

- `/api/payroll/rate-book`: service rates, premiums, weekly guarantee, service limits, and conflict thresholds.
- `/api/payroll/productions`: production schedule rows and musician roster assignments.

## Finance Reports

Use `accounts.category` as the account classifier. For a branch, region, period, or fiscal year:

- `revenue`, `cogs`, `sga`, and `allocations` are sums of matching account rows.
- `gross_margin = revenue - cogs`.
- `ebitda = gross_margin - sga - allocations`.
- `ebitda_margin = ebitda / revenue`.
- Revenue growth and EBITDA growth use `(current - prior) / prior`.
- `arpu = revenue / sum(active_customers)` over the same period set.
- `sales_per_labor_headcount = revenue / sum(labor_headcount)` over the same period set.

For branch close packages:

- Use the memo's target branch, current close period, and prior period.
- Derive fiscal-year period sets from `/api/finance/period-map`; do not assume the year from the period label without checking the map.
- Current-period income statement uses only the close period.
- Month-over-month revenue variance compares current-period revenue with prior-period revenue.
- The current fiscal-year view sums every period in the current fiscal year, and growth fields compare to the prior fiscal year.
- Region context uses the target branch's region. Return region branch IDs ascending, region fiscal-year EBITDA, and the target branch's EBITDA rank within that region by descending EBITDA.
- Branch rankings are across all branches. Sales growth rank is descending fiscal-year revenue growth; top ARPU is descending fiscal-year ARPU. Use branch ID as a stable tie-breaker.

For regional views:

- Filter branches by the requested region ID, then aggregate records for that branch set.
- Return branch IDs ascending.
- Fiscal-year sections use the requested comparison years from the memo or template.
- Top and bottom EBITDA branch IDs are based on fiscal-year EBITDA among branches in the region, using branch ID tie-breaks.
- For reconciliation variance, compute the difference between the direct region aggregate and the sum of member branch aggregates for the same metric and period set; it should normally round to zero when both paths use active records.

## Compensation Reports

For each roster row and quarter, use that employee's `weeks_by_quarter`; do not replace partial weeks with a fixed quarter length.

Current-year pay components:

- `Minimum Weekly Scale = minimum_weekly_scale * weeks`.
- `Titled Position Premium = minimum_weekly_scale * title_premium_pct[title] * weeks`.
- If `combined_overscale_includes_title` is true, do not add a separate titled premium for that employee.
- `Seniority = seniority_weekly band amount * weeks`; bands use inclusive min and max years, with null max meaning no upper limit.
- `Overscale = overscale_weekly * weeks`.

Current-year summaries:

- `current_year` comes from the rate book.
- `pay_types` must use rate-book order.
- `roster_count` is the number of rows for the requested ensemble.
- Quarter totals sum all pay components for rows active in each quarter.
- Annual pay-type totals sum each component across all quarters.
- `annual_total` must match both the sum of quarter totals and the sum of pay-type totals after rounding.
- `largest_pay_type` is the pay type with the largest annual total unless the template asks for a different basis.
- `combined_overscale_employee_count` counts rows where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count` counts rows whose quarter weeks differ from the rate-book full quarter weeks.

Forecast summaries:

- First compute the current-year totals using the current-year rules.
- Year plus 1 applies `scenario.year_plus_1` factors to current rates and uses `years_of_service + 1` for seniority band selection.
- Year plus 2 is cumulative: apply year plus 1 factors and then `scenario.year_plus_2` factors to rates, and use `years_of_service + 2` for seniority band selection.
- Apply `mws_growth`, `overscale_growth`, and `seniority_growth` to the matching weekly amounts. Apply `title_pct_multiplier` to the title premium percentages; in year plus 2 the title multiplier is also cumulative.
- `growth_rates` compare annual totals between adjacent forecast years.
- When asked for the largest growth pay type, use percent growth from current to the requested forecast year unless the prompt explicitly asks for dollar growth.

## Payroll Reviews

Build a service lookup from the production schedule and process each musician's `assigned_service_ids`.

Base pay categories:

- `performance`: count assigned `Performance` services times the performance rate.
- `audit`: count assigned `Audit` services times the audit rate.
- `rehearsal`: assigned rehearsal hours times the rehearsal rate, with a 3-hour minimum call per rehearsal service.
- `sound_check`: assigned sound-check services at the rate-book service rate for that sound-check type.

Adjustments and premiums:

- For `substitute: true`, include a `substitute_adjustment` equal to two performance service rates when applicable. Add this amount to the performance base used for premiums and doubles, and report it separately under `substitute_adjustment`.
- For non-substitute regular players, `guarantee_adjustment = max(weekly_guarantee - base_service_pay, 0)`, where base service pay is before premiums, doubles, vacation, guarantee, or substitute adjustment.
- `premium` applies applicable role percentages to base service pay. In the observed schema, use `principal` or `lead` once for `principal_or_lead`, add `quartet` and `electronic` when true, and apply any other explicit rate-book premium only if the roster exposes the matching flag.
- `doubles = base_service_pay * (first_double + additional_double * max(doubles - 1, 0))`.
- `vacation = vacation_pct * (base_service_pay + premium + doubles)` when `vacation_eligible` is true.

Output rules:

- `service_counts` counts schedule services by service type.
- `category_totals` sums each pay category across musicians. Include optional categories such as `substitute_adjustment` when present or required by the template.
- `per_musician` is ordered by `musician_id`; each musician's `categories` object contains only nonzero categories unless the template says otherwise.
- `top_paid_musician_id` is the highest total after all categories, with `musician_id` as a tie-breaker.
- `conflict_flags` are sorted alphabetically. Flag rehearsal start before `rehearsal_earliest_start`, rehearsal end after `rehearsal_latest_end`, any service duration above `service_time_limits[service_type]`, and any sound-check duration that differs from its service-time limit.
