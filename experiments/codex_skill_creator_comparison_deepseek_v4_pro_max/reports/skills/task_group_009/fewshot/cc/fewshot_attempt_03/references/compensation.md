# Compensation Domain

## Pay computation

Every musician in a roster has four pay components computed per quarter, then summed for the annual total:

1. **Minimum Weekly Scale** (MWS) = `minimum_weekly_scale` x weeks_worked
2. **Titled Position Premium** = MWS x `title_premium_pct[title]`
3. **Seniority** = `seniority_weekly_amount` x weeks_worked
4. **Overscale** = `overscale_weekly` x weeks_worked

### Pay type ordering

The `pay_types` list always follows the rate book order:
`"Minimum Weekly Scale"`, `"Titled Position Premium"`, `"Seniority"`, `"Overscale"`

### Seniority band lookup

For a given `years_of_service` value, find the band where `min_years <= years_of_service <= max_years`. If the band has `max_years: null`, it matches any years_of_service >= min_years. The employee gets the `weekly_amount` from that band, multiplied by the number of weeks worked.

For **forecast years**, add years before looking up:
- Current year: use the roster's `years_of_service` as-is
- Year + 1: use `years_of_service + 1`
- Year + 2: use `years_of_service + 2`

### Title premium

Only applies when the roster entry has a non-null `title`. Multiply the employee's MWS for the quarter by the `title_premium_pct` for that title.

**Critical rule**: If `combined_overscale_includes_title` is `true`, do NOT add a separate Titled Position Premium for that employee. The overscale amount already includes it. The employee still gets MWS, Seniority, and Overscale, but no separate title line.

### Overscale

Simply `overscale_weekly x weeks_worked`. If overscale_weekly is 0, this component is 0.

### Weeks worked by quarter

Use `weeks_by_quarter` from the roster entry. DO NOT default to 13 weeks for every employee. The rate book's `quarter_weeks` describes the standard quarter length, but the roster's `weeks_by_quarter` is authoritative per employee.

Partial-quarter employees are those whose `weeks_by_quarter` differs from 13 in any quarter, or whose `notes` mentions "Partial-quarter".

## Quarterly totals

For each quarter (Q1-Q4), sum all four pay components across all employees in the ensemble.

## Annual totals

Sum quarterly totals for `annual_total`. Annual totals by pay type sum each pay component across all employees and all quarters.

## Roster treatment counts

- **roster_count**: total number of employees in the ensemble
- **combined_overscale_employee_count**: number of employees with `combined_overscale_includes_title` set to `true`
- **partial_quarter_employee_count**: number of employees where any quarter has `weeks_by_quarter` different from 13, OR where `notes` mentions partial-quarter scheduling

## Largest pay type

Compare the `annual_pay_type_totals` values and return the pay type name with the highest value. If there is a tie, use the order from the pay_types list as tiebreaker.

## Forecast computations

When the task involves scenarios (using `/api/compensation/scenarios`):

1. Fetch the scenario by `scenario_id` from the request memo
2. For **Year + 1**: apply the `year_plus_1` growth rates to the current-year rate book values:
   - New MWS = current `minimum_weekly_scale` x (1 + `mws_growth`)
   - New overscale = current `overscale_weekly` x (1 + `overscale_growth`)
   - New seniority amounts = current `seniority_weekly` amounts x (1 + `seniority_growth`)
   - New title premiums = current `title_premium_pct` x `title_pct_multiplier`
   - Add 1 to every employee's `years_of_service` before seniority lookup
3. For **Year + 2**: apply `year_plus_2` growth rates to the current-year rate book values:
   - Same pattern as above but with `year_plus_2` multipliers
   - Add 2 to every employee's `years_of_service` before seniority lookup

For **Year + 2 quarter and pay type totals**: compute using the Year + 2 adjusted rates.

### Largest growth pay type

Compute the annual total for each pay type in the current year and in Year + 2. Growth = Year + 2 total - current total. The pay type with the highest absolute growth in currency (not percentage) determines `largest_growth_pay_type`.
