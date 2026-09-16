# Compensation summaries and forecasts

Use this for current-year compensation summaries and Year + 1 / Year + 2 forecast packages.

## Endpoints

- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios`

## Data model

- The rate book provides `current_year`, `minimum_weekly_scale`, `title_premium_pct`, `seniority_weekly`, `quarter_weeks`, and the canonical `pay_types` order.
- `rosters` is one row per employee with `employee_id`, `ensemble_id`, `title`, `years_of_service`, `overscale_weekly`, `combined_overscale_includes_title`, and `weeks_by_quarter`.
- `scenarios` provides the Year + 1 and Year + 2 growth multipliers for each forecast case.

## Current-year summary

- Use the rate-book `pay_types` order exactly.
- Sum employee pay by quarter using the roster quarter weeks. Do not assume every row has 13 weeks.
- Use the current-year seniority band from the rate book and the employee's current `years_of_service`.
- Treat the seniority bands as inclusive ranges on `min_years` and `max_years`; if `max_years` is null, the band is open-ended.
- Compute annual pay types for each employee, then sum across employees:
  - `Minimum Weekly Scale` = minimum weekly scale × total roster weeks
  - `Titled Position Premium` = minimum weekly scale × title percent × total roster weeks
  - `Seniority` = seniority weekly amount from the matching band × total roster weeks
  - `Overscale` = overscale weekly × total roster weeks
- If `combined_overscale_includes_title` is true, suppress a separate titled-position premium for that employee.
- `combined_overscale_employee_count` = number of roster rows with that flag true.
- `partial_quarter_employee_count` = number of roster rows whose quarter weeks differ from the standard quarter weeks in the rate book.
- `largest_pay_type` = the pay type with the largest annual total.

## Forecast summary

- Select the scenario by `scenario_id`.
- For Year + 1 and Year + 2, add 1 or 2 years of service before looking up the seniority band.
- Apply the scenario's year-specific multipliers to the minimum weekly scale, overscale weekly, seniority weekly, and title percentage before calculating the totals.
- Keep the roster quarter weeks unchanged.
- `largest_growth_pay_type` should compare current annual pay-type totals against Year + 2 pay-type totals and return the largest absolute increase.
- Keep the roster-based counts the same unless the prompt says otherwise.

## Output discipline

- Round currency to 2 decimals and percent values to 4 decimals.
- Keep roster-derived lists in stable ascending id order when the template does not specify a different order.
