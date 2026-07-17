# Crescent Finance Ops Reporting Skill

Use this skill for Crescent Arts Collective finance, compensation, and payroll reporting tasks that provide a memo, an answer template, and Finance Ops API access.

## Core Workflow

1. Read the task prompt, request memo, answer template, and environment access payload.
2. Use the `base_url` and only the endpoints listed in the environment payload for the task domain.
3. Build the answer from active API data, not from memo notes or assumed workbook values.
4. Preserve every top-level key and nested field shape from the answer template.
5. Sort stable identifier lists ascending unless the template explicitly asks for rank order.
6. Round only final reported values: currency to 2 decimals; percentages and ratios to 4 decimals.

## Finance Reporting

Use `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.

Account rollups:

- `revenue` = product revenue + service revenue.
- `cogs` = direct materials COGS + direct labor COGS.
- `gross_margin` = revenue - cogs.
- `sga` = sales SG&A + admin SG&A + occupancy SG&A.
- `allocations` = shared service allocations.
- `ebitda` = revenue - cogs - sga - allocations.

Period conventions:

- Use the period map to identify fiscal years.
- `M1` through `M12` are FY2024; `M13` through `M24` are FY2025.
- When a template asks for `current_month` or `prior_month` as period labels, return the period IDs such as `M24` and `M23`, not expanded month names.

Finance ratios and rankings:

- Revenue variance amount = current period revenue - prior period revenue.
- Revenue variance percent = amount / prior period revenue.
- EBITDA margin = EBITDA / revenue.
- ARPU = FY revenue / summed FY active customers.
- Sales per labor headcount = FY revenue / summed FY labor headcount.
- Branch sales growth rank is descending by FY revenue growth percent, with stable ID tie-breaks.
- Top ARPU branch is the branch with the highest FY revenue divided by summed FY active customers.
- Regional branch sets must be sorted by branch ID.
- For a branch regional context field named like `fy2025_ebitda`, use the full region's FY EBITDA.
- A regional EBITDA rank field in branch context ranks regions against other regions by FY EBITDA descending, not the branch within its region.
- Regional reconciliation variance should be `0` when the region view is built directly from the branch records and no separate control total exists.

## Compensation Summaries

Use `/api/compensation/rate-book` and `/api/compensation/rosters`. Use `/api/compensation/scenarios` only for forecast/scenario tasks.

Current-year pay components:

- Minimum Weekly Scale = `minimum_weekly_scale * weeks_by_quarter[quarter]`.
- Titled Position Premium = minimum weekly scale * title premium percent * weeks.
- Seniority = seniority weekly amount for the employee's years of service * weeks.
- Overscale = overscale weekly amount * weeks.
- Use each employee's `weeks_by_quarter`; do not assume a fixed 13 weeks when partial-quarter schedules are present.
- If `combined_overscale_includes_title` is true, do not add a separate titled position premium for that employee.
- `combined_overscale_employee_count` counts employees whose combined-overscale flag is true.
- `partial_quarter_employee_count` counts employees whose quarter weeks differ from the rate book's quarter weeks in any quarter.
- Preserve the rate book's `pay_types` order.
- `largest_pay_type` is the pay type with the largest annual total.

Forecasts:

- Treat Year + 1 scenario growth as growth from current, and Year + 2 as growth from Year + 1 unless the task says otherwise.
- For forecast years, add one year of service for Year + 1 and two years for Year + 2 before choosing seniority bands.
- Apply MWS, seniority, overscale, and title percent assumptions by pay type; title premiums still obey the combined-overscale rule.
- For `largest_growth_pay_type`, use the pay type with the largest growth rate/driver rather than blindly choosing the largest dollar component when the wording emphasizes growth drivers.

## Payroll Reviews

Use `/api/payroll/rate-book` and `/api/payroll/productions`.

Payroll calculation habits:

- Build pay from each musician's assigned service IDs, not just from the schedule list.
- Rehearsal pay is hourly with a three-hour minimum call.
- Performance, audit, and sound-check rates are per service.
- Map base service pay to reporting categories: `performance`, `audit`, `rehearsal`, and `sound_check`.
- Premiums are computed from the musician's base service pay before vacation.
- Principal or lead premium applies once when either flag is true.
- Add applicable electronic and quartet premiums.
- Doubles are reported separately from the general `premium` category; first double and additional double percentages are additive.
- Vacation applies only when `vacation_eligible` is true and is computed after base service pay and applicable premiums.
- Weekly guarantee adjustments apply only to non-substitute regular players when the selected guarantee convention makes them eligible.
- Per-musician rows must be ordered by `musician_id`; include only nonzero categories for each musician.
- Conflict flags must be sorted alphabetically and drawn from the template enum.

Payroll conflict checks:

- Rehearsal starts before the rate book's earliest start threshold: `REHEARSAL_EARLY_START`.
- Rehearsal ends after the latest end threshold: `REHEARSAL_LATE_END`.
- Any service duration above the service time limit: `SERVICE_OVER_TIME_LIMIT`.
- Sound-check duration that does not match the named sound-check limit: `SOUND_CHECK_DURATION_MISMATCH`.

## Formatting Pitfalls

- Do not rename template fields or add explanatory text outside the JSON object.
- Do not use expanded month names where the template expects period labels.
- Do not round intermediate calculations before aggregating.
- Do not infer missing region or branch totals from memo prose; reconcile to API records.
- Do not add a titled premium when overscale explicitly includes the title premium.
- Do not assume every quarter has 13 paid weeks for every compensation roster member.
