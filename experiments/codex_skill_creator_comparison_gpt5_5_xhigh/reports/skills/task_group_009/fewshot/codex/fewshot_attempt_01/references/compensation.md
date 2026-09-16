# Compensation Reporting

## Inputs

- `/api/manifest`
- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios`

## Shared rules

- Use `rate-book.current_year` as the reporting year.
- Preserve `rate-book.pay_types` order in outputs.
- `combined_overscale_employee_count` = roster rows with `combined_overscale_includes_title = true`.
- `partial_quarter_employee_count` = roster rows with any quarter week count different from `13`.

## Current-year summary

For each roster row, compute each quarter with the quarter-specific week count:

- `minimum weekly scale = minimum_weekly_scale * weeks`
- `title premium = minimum_weekly_scale * title_pct * weeks`
- Skip the title premium when `combined_overscale_includes_title` is true.
- `seniority = seniority_weekly[band(years_of_service)] * weeks`
- `overscale = overscale_weekly * weeks`

Then:

- Sum quarter totals into annual pay-type totals.
- Set `annual_total = sum(pay_type totals)`.
- Set `largest_pay_type` to the largest annual pay-type total.

## Forecast summary

- For `year_plus_1`, grow minimum scale, title premium, and overscale with the `year_plus_1` rates.
- Make title premium inherit minimum-scale growth, then apply `title_pct_multiplier`.
- Add 1 year of service before seniority band lookup, then apply `year_plus_1.seniority_growth`.
- For `year_plus_2`, compound both scenario years for minimum scale, title premium, and overscale.
- Add 2 years of service before seniority band lookup, then compound both seniority growth steps.
- Use quarter-specific weeks for `year_plus_2_quarter_totals`.
- Set `largest_growth_pay_type` to the pay type with the highest percentage increase from current-year total to year+2 total.
