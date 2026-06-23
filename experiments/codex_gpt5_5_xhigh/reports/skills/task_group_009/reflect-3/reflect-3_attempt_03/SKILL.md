# Crescent Finance Ops Reporting Skill

Use this skill for Crescent Finance Ops tasks that ask for branch close reporting, regional management reporting, compensation summaries or forecasts, and payroll review JSON outputs.

## Environment Habits

- Use the remote Finance Ops base URL from the task's `environment_access.json`. Do not assume or inspect a local environment.
- Read the task memo and answer template first. Treat the template as the source of truth for field names, nesting, ordering, rounding, and whether ratios are decimal percentages.
- Pull the complete active endpoint data needed for the request, then filter in memory by the requested branch, region, ensemble, production, scenario, period, or year. Avoid relying on memo notes when active API data disagrees.
- For finance tasks, fetch branches, period map, accounts, and records together. Use the period map to derive fiscal-year membership instead of hard-coding month labels unless the active period map confirms them.
- For compensation tasks, fetch the rate book and rosters; fetch scenarios only for forecast requests.
- For payroll tasks, fetch both the payroll rate book and productions. Use the production schedule and roster assignments together, not the schedule alone.

## General Output Rules

- Return exactly one JSON object matching the answer template. Do not add explanations, citations, or extra wrapper keys.
- Currency fields are numbers rounded to 2 decimals. Percent, growth, margin, and ratio fields are decimal numbers rounded to 4 decimals.
- Keep IDs stable and sorted ascending unless the field is explicitly a rank, top, bottom, or ordered-by-value field.
- Preserve template key spelling exactly, including spaces and capitalization in compensation pay type names.
- For rankings, sort descending by the metric requested, with stable ID ascending as the tie-breaker.
- Compute with unrounded intermediate values and round only when assigning final JSON fields.

## Finance Reporting

- Use account categories from `/api/finance/accounts`:
  - revenue = product revenue + service revenue
  - cogs = direct materials COGS + direct labor COGS
  - gross margin = revenue - cogs
  - sga = sales SG&A + admin SG&A + occupancy SG&A
  - allocations = shared service allocations
  - ebitda = gross margin - sga - allocations
- Month-over-month variance is current period revenue minus prior period revenue; percent variance is amount divided by prior period revenue.
- Fiscal-year comparisons sum all periods in each fiscal year from the period map. Do not mix current close month values into full-year totals unless the template asks for a specific period.
- EBITDA margin is EBITDA divided by revenue.
- ARPU and sales per labor headcount use revenue divided by the summed active customer or labor headcount values over the same selected periods. Do not annualize by dividing the denominator by average months unless the template explicitly asks for averages.
- Regional finance rollups are the sum of the included branch metrics. `region_reconciliation_variance` should be the rounded difference between the region rollup and the sum of its branch-level components; it is normally zero when both are sourced from the same active records.
- Branch and region sets come from `/api/finance/branches`; output branch ID lists in ascending order.

## Compensation Current-Year Summaries

- Use the rate book's `pay_types` order in output.
- For each roster employee and quarter, use that employee's `weeks_by_quarter`. Do not assume 13 weeks when a partial-quarter schedule is present.
- Minimum Weekly Scale = rate book minimum weekly scale times roster weeks.
- Titled Position Premium = minimum weekly scale times the title premium percent times roster weeks, except when `combined_overscale_includes_title` is true.
- Seniority = the weekly seniority band for the employee's years of service times roster weeks.
- Overscale = `overscale_weekly` times roster weeks.
- Annual pay-type totals are the sum across all employees and quarters. Quarter totals are the sum of all pay types for that quarter.
- `combined_overscale_employee_count` counts employees with `combined_overscale_includes_title: true`, not all employees with overscale pay.
- `partial_quarter_employee_count` counts employees whose `weeks_by_quarter` differs from the rate book's standard quarter weeks in any quarter.

## Compensation Forecasts

- Start from the current-year roster and rate book. Use the requested scenario for growth assumptions.
- For Year + 1 and Year + 2, add one or two years of service before assigning the seniority band.
- Apply forecast growth by pay type according to the scenario:
  - minimum weekly scale growth changes the minimum weekly scale used for both scale and title-premium calculations.
  - title premium multipliers adjust the title percentage.
  - seniority growth adjusts seniority weekly amounts after selecting the forecast-year seniority band.
  - overscale growth adjusts `overscale_weekly`.
- Keep combined-overscale title treatment in force for all forecast years: do not add a separate title premium for employees whose overscale includes title.
- Growth rates compare annual totals for the named years: Year + 1 versus current, and Year + 2 versus Year + 1.
- `largest_growth_pay_type` should be based on the largest absolute pay-type increase requested by the template; when unclear, compare forecast detail year against current using the same pay-type totals.

## Payroll Reviews

- Build pay from assigned services per musician. The production schedule defines service type, duration, and conflict checks; each roster member's `assigned_service_ids` determines what they are paid for.
- Rehearsal pay is hourly with the rate book's three-hour minimum call. Performance, audit, and sound-check pay are per service from the rate book.
- Use category keys from the template for category totals and per-musician nonzero category maps: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, and `substitute_adjustment` when applicable.
- Apply principal/lead, quartet, electronic, concertmaster, and doubles premium rules from the rate book to the musician's base service pay. Check whether the template expects additive premiums or a specific premium grouping before finalizing totals.
- Vacation applies only when `vacation_eligible` is true and should follow the rate book's stated base-plus-premium convention.
- Weekly guarantee adjustments apply only to guaranteed regular players, not substitutes. Confirm whether the adjustment is measured against base service pay alone or against pre-guarantee total pay when the task wording is specific.
- Conflict flags come from the schedule:
  - rehearsal starts before the earliest allowed time
  - rehearsal ends after the latest allowed time
  - service duration exceeds the service time limit
  - sound-check duration mismatches the labeled one-hour or two-hour service
- Sort `conflict_flags` alphabetically and `per_musician` by `musician_id`.

## Pitfalls

- Do not use local files, stale workbook notes, or inferred gold values when active API data is available.
- Do not average headcount/customer denominators for finance productivity ratios unless the prompt explicitly asks for an average.
- Do not add title premium when a roster row says overscale already includes title.
- Do not lose partial-quarter employees by applying a blanket 13-week quarter.
- Do not rank IDs lexicographically before sorting by the requested metric; rank by metric first, then use ID as a tie-breaker.
- Do not include training-only validation methods, judge calls, or feedback in production/test solving.
