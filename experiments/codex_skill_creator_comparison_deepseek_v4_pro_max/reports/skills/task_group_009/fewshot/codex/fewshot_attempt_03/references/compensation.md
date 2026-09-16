# Compensation Module

## Endpoints

- `GET /api/compensation/rate-book` — base rates, pay types, seniority bands, title premium percentages, quarter weeks, business rules, and current_year.
- `GET /api/compensation/rosters` — employee list per ensemble. Each employee has `employee_id`, `ensemble_id`, `ensemble_name`, `title`, `years_of_service`, `overscale_weekly`, `combined_overscale_includes_title`, `notes`, and `weeks_by_quarter` (object mapping Q1–Q4 to integer weeks).
- `GET /api/compensation/scenarios` — forecast scenarios keyed by scenario_id. Each has `description` and nested `year_plus_1` / `year_plus_2` growth rates: `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier`.

## Pay Types

The rate book defines four ordered pay types:

1. Minimum Weekly Scale
2. Titled Position Premium
3. Seniority
4. Overscale

Preserve this order in any output list of pay types.

## Per-Employee Weekly Pay Computation (Current Year)

For one employee in one quarter:

```python
weeks = employee["weeks_by_quarter"][quarter]  # Q1-Q4

# 1. Minimum Weekly Scale
mws = minimum_weekly_scale * weeks

# 2. Titled Position Premium
title = employee["title"]
if title and not employee["combined_overscale_includes_title"]:
    pct = title_premium_pct[title]
    titled_premium = minimum_weekly_scale * pct * weeks
else:
    titled_premium = 0.0

# 3. Seniority
yos = employee["years_of_service"]
seniority_weekly = 0.0
for band in seniority_weekly:
    if band["min_years"] <= yos and (band["max_years"] is None or yos <= band["max_years"]):
        seniority_weekly = band["weekly_amount"]
        break
seniority = seniority_weekly * weeks

# 4. Overscale
overscale = employee["overscale_weekly"] * weeks
```

## Roster Counts

- **roster_count**: count of employees in the ensemble roster.
- **combined_overscale_employee_count**: count of employees with `combined_overscale_includes_title == true`. This flag means overscale already includes the title premium, so titled position premium is not added separately for these employees.
- **partial_quarter_employee_count**: count of employees whose `weeks_by_quarter` sum (across all four quarters) is less than the standard full-year total. The standard full-year total is the sum of `quarter_weeks` values (typically 13+13+13+13 = 52).

## Per-Quarter Aggregation

For each quarter Q1–Q4, sum all four pay-type amounts across all employees for that quarter.

## Annual Pay-Type Totals

For each pay type, sum that type's amount across all four quarters (all employees included).

## Annual Total

Sum of all four annual pay-type totals.

## Largest Pay Type

Compare the four annual pay-type totals and select the pay type name with the highest summed amount.

## Forecast Years (Current, Year + 1, Year + 2)

Forecasts use a scenario from `/api/compensation/scenarios`. The base data is always the current-year roster and rate-book.

**Current year**: compute exactly like the current-year summary (above) using the current rate book values and roster.

**Year + 1**: apply the scenario's `year_plus_1` growth rates to the base values and add 1 year of service:

- `new_mws = minimum_weekly_scale * (1 + mws_growth)`
- `new_title_pcts`: multiply each title premium percentage by `title_pct_multiplier`
- `new_seniority_bands`: multiply each band's `weekly_amount` by `(1 + seniority_growth)`
- Employee `overscale_weekly`: multiply by `(1 + overscale_growth)`

Then recompute per-employee, per-quarter pay using the adjusted values and `years_of_service + 1`.

**Year + 2**: apply `year_plus_2` growth rates identically to the **original** base values (not Year + 1 values). Add 2 years of service. Recompute.

For each forecast year, compute quarterly totals and pay-type totals using the adjusted rates and the employee roster (weeks_by_quarter unchanged).

## Growth Rates (Forecast)

```python
year_plus_1_vs_current = (year_plus_1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```

Round to 4 decimals.

## Largest Growth Pay Type (Forecast)

For each pay type, compute growth from current to Year + 2:

```python
growth = (year_plus_2_total - current_total) / current_total
```

Select the pay type with the largest growth rate (not absolute amount).

## Rounding

All currency amounts: round to 2 decimals. All growth rates: round to 4 decimals.

## Ordering

Pay types in output lists must follow the rate-book order: Minimum Weekly Scale, Titled Position Premium, Seniority, Overscale.
