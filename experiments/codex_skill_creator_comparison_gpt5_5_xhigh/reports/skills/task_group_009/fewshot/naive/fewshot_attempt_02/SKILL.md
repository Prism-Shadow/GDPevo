---
name: crescent-finance-ops-reporting
description: Solve Crescent Finance Ops management reporting, compensation, forecast, and payroll JSON tasks from the live business API.
---

# Crescent Finance Ops Reporting

Use this skill when a task asks for a single JSON answer for Crescent Arts Collective or the Crescent Finance Ops API. The task input normally has:

- `payloads/environment_access.json` with the service endpoints.
- `payloads/request_memo.json` with the target branch, region, ensemble, scenario, or production.
- `payloads/answer_template.json` with required keys, field names, rounding, and ordering constraints.

Do not answer from background notes in the prompt. Treat the live business endpoints as authoritative.

## Fast Path

Run the bundled calculator [crescent_ops_solver.py](crescent_ops_solver.py) when Python 3 is available:

```bash
python3 <path-to-this-skill>/crescent_ops_solver.py --input-dir <task input dir> --base-url <base url>
```

If `--base-url` is omitted, the script tries `TASK_ENV_BASE_URL`, `payloads/environment_access.json`, and nearby `environment_access.md`. It prints one JSON object. Before submitting, compare the printed top-level keys to `answer_template.json`.

The script is intentionally generic: it implements formulas and endpoint schemas, not any example answer values.

## General Rules

- Fetch all required endpoint data directly from the base URL. Use only the endpoints listed in the payload or environment access file.
- Round currency fields to 2 decimals and ratio/percent fields to 4 decimals at final output.
- Use decimal percentages as ratios, for example `0.1250` for 12.50%.
- Sort stable ID lists ascending unless a ranking asks for descending metric order.
- For descending rankings, sort by metric descending and use stable ID ascending as the tie breaker. Ranks are 1-based.
- Omit zero-only optional payroll categories, but include every required answer-template key.

## Finance Branch Close

Use `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.

Account category formulas:

- `revenue`: sum accounts whose category is `revenue`.
- `cogs`: sum accounts whose category is `cogs`.
- `gross_margin = revenue - cogs`.
- `sga`: sum accounts whose category is `sga`.
- `allocations`: sum accounts whose category is `allocations`.
- `ebitda = gross_margin - sga - allocations`.

For the close-period income statement, compute those fields for the target branch and requested close period. For month-over-month variance, compare close-period revenue to prior-period revenue:

```text
amount = current_revenue - prior_revenue
pct = amount / prior_revenue
```

For the fiscal-year branch view, use the fiscal year from the close period and the immediately prior fiscal year from `period-map`. Sum all mapped periods in each fiscal year. Compute:

- `ebitda_margin = ebitda / revenue`.
- `arpu = revenue / active_customers`, using the sum of `active_customers` over the same periods.
- `sales_per_labor_headcount = revenue / labor_headcount`, using the sum of `labor_headcount` over the same periods.
- Revenue and EBITDA growth as `(current_year_value - prior_year_value) / prior_year_value`.

For region context, find the target branch's `region_id`, list all branch IDs in that region ascending, sum current fiscal-year EBITDA for the region, and rank that region's current fiscal-year EBITDA among all regions descending.

For branch rankings, rank all branches by current-vs-prior fiscal-year revenue growth. The top sales growth branch is rank 1. Rank ARPU across all branches using current fiscal-year revenue divided by current fiscal-year active-customer sum.

## Finance Regional View

Use the same finance endpoints. Filter branches by `target_region_id` and use `requested_comparison_years`.

For each requested fiscal year, aggregate branch records across all periods mapped to that fiscal year. Output the exact fiscal-year keys requested by the answer template, usually `fyYYYY`.

Compute current-year ratios from regional totals:

- `ebitda_margin = ebitda / revenue`.
- `sales_per_labor_headcount = revenue / labor_headcount`, using summed monthly headcount.
- `revenue_growth_pct = (current_year_revenue - prior_year_revenue) / prior_year_revenue`.

Rank branches inside the region by current-year EBITDA descending for `top_ebitda_branch_id` and ascending for `bottom_ebitda_branch_id`. If no independent regional aggregate endpoint exists, the reconciliation variance is `0.00` because the regional total and branch sum come from the same active records.

## Compensation Current-Year Summary

Use `/api/compensation/rate-book` and `/api/compensation/rosters`.

Filter roster rows by `ensemble_id`. Use the rate book's `pay_types` order and `current_year`.

For each employee and quarter, use the employee's `weeks_by_quarter`; do not assume a fixed 13 weeks when an employee has partial-quarter service.

Weekly pay components:

- `Minimum Weekly Scale = minimum_weekly_scale`.
- `Titled Position Premium = minimum_weekly_scale * title_premium_pct[title]`, only when the employee has a title and `combined_overscale_includes_title` is false.
- `Seniority`: choose the rate-book seniority band containing `years_of_service`.
- `Overscale = overscale_weekly`.

Multiply each component by that employee's weeks in the quarter. Quarter totals are the sum of all pay components in that quarter. Annual pay-type totals are the sum of each pay type across all quarters. Final annual totals tie to the sum of the rounded quarter totals; pay-type totals are rounded independently and can differ by a cent.

Roster treatment counts:

- `combined_overscale_employee_count`: count roster rows where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count`: count roster rows where any `weeks_by_quarter` value differs from the rate-book standard for that quarter.

`largest_pay_type` is the pay type with the largest annual total, tie-broken by the rate-book pay-type order.

## Compensation Forecast

Use `/api/compensation/rate-book`, `/api/compensation/rosters`, and `/api/compensation/scenarios`.

Compute the current year exactly as in the current-year summary. For forecast years, keep the same roster weeks and apply scenario rates:

- Year + 1 MWS = current MWS compounded by `year_plus_1.mws_growth`.
- Year + 2 MWS = current MWS compounded by Year + 1 growth and Year + 2 growth.
- Overscale weekly amounts compound the same way with `overscale_growth`.
- Seniority bands use `years_of_service + 1` for Year + 1 and `years_of_service + 2` for Year + 2; seniority weekly rates then compound by the scenario seniority growth factors.
- Title premium percentages use the forecast year's `title_pct_multiplier` against the base title percentage, then apply to that year's MWS.
- If `combined_overscale_includes_title` is true, do not add a separate title premium in any year.

`growth_rates` compare annual totals: Year + 1 vs current, and Year + 2 vs Year + 1. `largest_growth_pay_type` is the pay type with the largest proportional growth from current annual pay-type total to Year + 2 annual pay-type total, tie-broken by rate-book pay-type order.

## Payroll Weekly Review

Use `/api/payroll/rate-book` and `/api/payroll/productions`.

Filter the production by `production_id`. `service_counts` counts scheduled services by `service_type`, not musician assignments.

For each musician, calculate assigned service base pay:

- Rehearsal: hourly rate times `max(duration_hours, 3.0)`.
- Performance, Audit, and Sound Check: per-service rate from the rate book.
- Sound-check service type remains `sound_check` in pay categories.

For substitutes, add a substitute adjustment equal to two performance service rates. Include it in `substitute_adjustment` and also add the same amount to the musician's performance base before computing premiums.

Base service pay for premium calculations is the sum of performance, audit, rehearsal, and sound-check base categories after the substitute performance-base adjustment.

Premium categories:

- `premium`: base service pay times the sum of applicable non-doubling premiums: `principal_or_lead` once if either flag is true, `quartet`, `electronic`, and `concertmaster` if present.
- `doubles`: base service pay times `first_double` for one extra instrument plus `additional_double` for each extra instrument beyond the first.
- `vacation`: when `vacation_eligible` is true, vacation rate times `base_service_pay + premium + doubles`.
- `guarantee_adjustment`: for non-substitute regular players only, `weekly_guarantee - base_service_pay` when base service pay is below the weekly guarantee.

Musician totals are the sum of nonzero categories. Sort `per_musician` by `musician_id`, and sort each musician's nonzero categories alphabetically. `top_paid_musician_id` is the highest total, tie-broken by `musician_id` ascending.

Conflict flags are sorted alphabetically:

- `REHEARSAL_EARLY_START`: any rehearsal starts before the rate-book earliest rehearsal start.
- `REHEARSAL_LATE_END`: any rehearsal ends after the rate-book latest rehearsal end.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds the rate-book service time limit for its service type.
- `SOUND_CHECK_DURATION_MISMATCH`: any sound-check duration differs from the service time limit for that sound-check type.
