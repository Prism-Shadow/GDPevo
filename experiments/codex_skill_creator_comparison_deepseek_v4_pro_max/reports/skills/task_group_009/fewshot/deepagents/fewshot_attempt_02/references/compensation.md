# Crescent Compensation — Payroll and Forecast Reference

## Endpoints

| Endpoint | Description |
|---|---|
| `/api/compensation/rate-book` | Pay rates, seniority bands, title premiums, business rules, quarter-week counts |
| `/api/compensation/rosters` | Employee-level data: ensemble, title, years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter |
| `/api/compensation/scenarios` | Forecast scenarios: growth rates per pay type for year_plus_1 and year_plus_2 |

## Rate Book Structure

`current_year`, `minimum_weekly_scale` (base weekly rate), `quarter_weeks` (Q1–Q4, 13 weeks each), `pay_types` (ordered list), `seniority_weekly` (banded by years of service), `title_premium_pct` (pct of minimum_weekly_scale, by title).

## Compensation Business Rules

1. **Quarter weeks** come from the roster, not a fixed 13-week assumption, when an employee has partial-quarter weeks.
2. If `combined_overscale_includes_title` is true, do **not** add a titled-position premium for that employee; the overscale already covers it.
3. For **forecast years**: add one year of service for Year + 1 and two years for Year + 2 when mapping to seniority bands.

## Pay Type Calculation

### Minimum Weekly Scale
Base pay: `weeks_worked × minimum_weekly_scale`. Sum across all employees.

### Titled Position Premium
When an employee has a title and `combined_overscale_includes_title` is false:
```
premium = weeks_worked × minimum_weekly_scale × title_premium_pct[title]
```
Sum across all employees.

### Seniority
```
seniority_weekly = lookup by years_of_service in seniority_weekly bands
seniority_pay = weeks_worked × seniority_weekly
```
Sum across all employees.

### Overscale
```
overscale_pay = weeks_worked × overscale_weekly
```
Sum across all employees.

### Annual Total
Sum of the four pay-type totals.

## Quarter Totals

Per quarter: sum all four pay-type components for all employees in that quarter.

## Largest Pay Type

The pay-type string with the highest annual pay-type total.

## Roster Treatment Counts

- **combined_overscale_employee_count**: number of employees with `combined_overscale_includes_title` = true.
- **partial_quarter_employee_count**: number of employees whose `weeks_by_quarter` has any quarter with fewer weeks than the rate-book `quarter_weeks` value.

## Forecast Calculations

### Current Year
Use current `minimum_weekly_scale`, current `years_of_service`, current `title_premium_pct`, and current `overscale_weekly`. Formula same as above.

### Year + 1 and Year + 2

Scenario provides growth multipliers per pay type:

```
mws_yr       = minimum_weekly_scale × (1 + scenario[year].mws_growth)
title_pct_yr = title_premium_pct × scenario[year].title_pct_multiplier
overscale_yr = overscale_weekly × (1 + scenario[year].overscale_growth)

seniority_yr = lookup by (years_of_service + offset)
               then × (1 + scenario[year].seniority_growth)
```

Offset: +1 for year_plus_1, +2 for year_plus_2. Apply new rates to the same roster and weeks_by_quarter.

### Growth Rates

```
year_plus_1_vs_current     = (total_yr1 - total_current) / total_current
year_plus_2_vs_year_plus_1 = (total_yr2 - total_yr1) / total_yr1
```

### Largest Growth Pay Type

For the year_plus_2 pay-type totals, compute each type's absolute growth from current: `(pt_yr2 - pt_current) / pt_current`. The type with the highest absolute growth rate is `largest_growth_pay_type`.

### Forecast Roster Treatment Counts

Same as current-year treatment counts computed from the roster (counts do not change with growth rates).
