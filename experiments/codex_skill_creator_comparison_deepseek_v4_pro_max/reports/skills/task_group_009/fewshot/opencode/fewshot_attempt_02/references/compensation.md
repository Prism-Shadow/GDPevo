# Compensation Domain Reference

The compensation endpoints (`/api/compensation/rate-book`, `/api/compensation/rosters`,
`/api/compensation/scenarios`) support ensemble pay summaries and multi-year forecasts.

## Rate Book Structure

The rate book provides base rates and business rules:

- `minimum_weekly_scale` (mws): the base weekly pay rate every employee receives.
- `pay_types`: the ordered list of pay types for the API's data model. Always use the
  four enumerated values: "Minimum Weekly Scale", "Titled Position Premium",
  "Seniority", "Overscale".
- `quarter_weeks`: the number of weeks in each quarter (typically 13 each).
- `seniority_weekly`: an array of bands with `min_years`, `max_years`, and
  `weekly_amount`. The employee's `years_of_service` falls into the band where
  `years_of_service >= min_years AND years_of_service <= max_years` (treat `null`
  max_years as infinity).
- `title_premium_pct`: a map of title strings to percentage multipliers (e.g.,
  "Concertmaster": 0.22, "Principal": 0.20, "Section Lead": 0.15,
  "Assistant Principal": 0.10, "Associate Principal": 0.10).

### Business Rules from the Rate Book

1. **Partial-quarter employees**: use the employee's actual `weeks_by_quarter` values
   (not a fixed 13-week assumption) for any employee whose weeks differ from the full
   quarter. An employee is "partial quarter" if any quarter's weeks are less than the
   full `quarter_weeks` value from the rate book.

2. **Combined overscale**: if `combined_overscale_includes_title` is `true` for an
   employee, do NOT add a separate titled position premium for that employee. The
   `overscale_weekly` amount already covers the title premium per a side letter.
   Otherwise, compute the titled position premium normally from the title premium
   percentage.

3. **Forecast seniority**: for Year + 1, add 1 year to each employee's
   `years_of_service` before determining the seniority band. For Year + 2, add 2
   years. Current year uses the `years_of_service` value as-is.

## Per-Employee Pay Calculation (Current Year)

For each employee on the roster:

1. **Minimum Weekly Scale (MWS)**: For each quarter Q, `mws * weeks_by_quarter[Q]`.
   Sum across all four quarters for the annual MWS total.

2. **Titled Position Premium**: Only if `combined_overscale_includes_title` is
   `false` AND the employee has a non-null `title`. For each quarter Q:
   `mws * title_premium_pct[title] * weeks_by_quarter[Q]`. Sum across quarters.

3. **Seniority**: Look up the `weekly_amount` from the seniority band that matches
   the employee's `years_of_service`. For each quarter Q:
   `seniority_weekly_amount * weeks_by_quarter[Q]`. Sum across quarters.

4. **Overscale**: For each quarter Q: `overscale_weekly * weeks_by_quarter[Q]`. Sum
   across quarters.

5. **Quarter total for an employee**: Sum of all four pay types for that quarter.

6. **Annual total for an employee**: Sum of all four pay types across all quarters.

## Ensemble-Level Aggregation (Current Year)

- **`annual_pay_type_totals`**: Sum each pay type across all employees on the roster.
- **`annual_total`**: Sum of all four `annual_pay_type_totals`, or equivalently the
  sum of all four `quarter_totals`.
- **`quarter_totals`**: For each quarter Q, sum every employee's quarter Q total.
- **`roster_count`**: Count of employees on the roster (entries in the roster array
  for the target ensemble).
- **`largest_pay_type`**: The pay type string (from the four enumerated values) with
  the highest `annual_pay_type_totals` value.
- **`combined_overscale_employee_count`**: Count of employees where
  `combined_overscale_includes_title` is `true`.
- **`partial_quarter_employee_count`**: Count of employees where at least one
  quarter's `weeks_by_quarter` is less than the rate book's `quarter_weeks` value
  for that quarter.

## Forecast Calculation (Scenarios)

For a forecast task, the request memo names a `scenario_id` and an `ensemble_id`.

### Scenario Growth Rates

The scenario endpoint returns growth rates per pay type, per year. For each forecast
year (year_plus_1, year_plus_2), there are four growth multipliers:

- `mws_growth`: applied to the Minimum Weekly Scale rate.
- `title_pct_multiplier`: applied to the title premium percentages.
- `seniority_growth`: applied to the seniority weekly amounts.
- `overscale_growth`: applied to the `overscale_weekly` per employee.

### Computing Forecast Year Values

For each forecast year Y:

1. Build a forecast rate book by applying the scenario's growth rates for year Y to
   the current rate book values:
   - `forecast_mws = mws * (1 + mws_growth)`
   - `forecast_title_pcts = {title: pct * title_pct_multiplier for title, pct}`
   - `forecast_seniority_weekly`: each band's `weekly_amount` multiplied by
     `(1 + seniority_growth)`
   - `forecast_overscale_weekly` per employee: `overscale_weekly * (1 + overscale_growth)`

2. Determine seniority bands for year Y: add the appropriate number of years to each
   employee's `years_of_service` (1 for year_plus_1, 2 for year_plus_2).

3. Compute per-employee pay using the same four-type formula as current year, but
   with the forecast rates and updated seniority.

4. Aggregate to ensemble totals for the forecast year.

### Growth Rates Between Years

- `year_plus_1_vs_current`: (annual_total_year_plus_1 − current_annual_total) /
  current_annual_total, rounded to 4 decimals.
- `year_plus_2_vs_year_plus_1`: (annual_total_year_plus_2 − annual_total_year_plus_1)
  / annual_total_year_plus_1, rounded to 4 decimals.

### Largest Growth Pay Type

For growth comparisons, identify which pay type grows the most (in absolute currency
terms) between the earliest and latest year in the forecast window (typically current
vs year_plus_2). Use the pay type's `annual_pay_type_totals` values for the two
endpoint years to compute the delta. Return the pay type enum string.

### Roster Treatment Counts

These use the same definitions as for current-year compensation:
- `combined_overscale_employee_count`: count of employees with
  `combined_overscale_includes_title` = `true` on the roster.
- `partial_quarter_employee_count`: count of employees with at least one quarter
  having fewer weeks than the full `quarter_weeks`.

Note: roster treatment counts are based on the roster data, not on forecast
calculations. They reflect the current-year roster attributes.

## Formatting

- All currency values: round to 2 decimals.
- Growth rates: round to 4 decimals.
- `pay_types` lists: always use the four ordered values from the rate book:
  ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"].
- `largest_pay_type` and `largest_growth_pay_type`: return exactly one of the four
  enum strings.
