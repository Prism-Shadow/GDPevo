# Compensation Module – Ensemble Pay and Forecasts

This reference covers ensemble roster compensation by quarter and pay type,
treatment counts, and multi-year board forecasts from the `/api/compensation/`
endpoints.

---

## Endpoints and Data Model

### `/api/compensation/rate-book`

Returns the compensation rate book. Key fields:

```json
{
  "business_rules": [...],
  "current_year": 2026,
  "minimum_weekly_scale": 2520.0,
  "pay_types": ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"],
  "quarter_weeks": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
  "seniority_weekly": [
    {"min_years": 0, "max_years": 4, "weekly_amount": 0.0},
    {"min_years": 5, "max_years": 9, "weekly_amount": 48.0},
    {"min_years": 10, "max_years": 14, "weekly_amount": 82.0},
    {"min_years": 15, "max_years": 19, "weekly_amount": 126.0},
    {"min_years": 20, "max_years": 24, "weekly_amount": 170.0},
    {"min_years": 25, "max_years": null, "weekly_amount": 215.0}
  ],
  "title_premium_pct": {
    "Concertmaster": 0.22,
    "Principal": 0.2,
    "Section Lead": 0.15,
    "Assistant Principal": 0.1,
    "Associate Principal": 0.1
  }
}
```

### `/api/compensation/rosters`

Returns all ensemble rosters. Each employee record:

```json
{
  "employee_id": "ENS-REDWOOD-001",
  "ensemble_id": "ENS-REDWOOD",
  "ensemble_name": "Redwood Pops",
  "title": "Concertmaster" | null,
  "years_of_service": 3,
  "overscale_weekly": 0.0,
  "combined_overscale_includes_title": false,
  "weeks_by_quarter": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
  "notes": ""
}
```

### `/api/compensation/scenarios`

Returns forecast scenarios keyed by scenario_id. Each scenario has
`year_plus_1` and `year_plus_2` with fields: `mws_growth`, `overscale_growth`,
`seniority_growth`, `title_pct_multiplier`.

---

## Business Rules (from rate book)

These three rules must be applied exactly:

1. **Quarter weeks**: Use the actual `weeks_by_quarter` from each employee's
   roster record when partial-quarter employees are present (identified by
   notes like "Partial-quarter service schedule" or by quarter weeks that
   differ from the rate book's standard 13). For all other employees, use
   the standard `quarter_weeks` from the rate book.

2. **Combined overscale**: If `combined_overscale_includes_title` is true for
   an employee, do not add a titled position premium separately. The
   overscale amount already covers the title premium.

3. **Forecast years**: For Year + 1, add 1 year of service to each employee's
   `years_of_service`. For Year + 2, add 2 years. Re-compute the seniority
   band from the adjusted years before applying scenario growth rates.

---

## Pay Type Calculations (per employee, per quarter)

For each employee in the target ensemble, compute four pay components:

### Minimum Weekly Scale

```
mws = minimum_weekly_scale * quarter_weeks
```

Where quarter_weeks comes from the roster record if the employee has
partial-quarter weeks; otherwise from the rate book's `quarter_weeks`.

### Titled Position Premium

If the employee has a title and `combined_overscale_includes_title` is false:

```
title_premium = minimum_weekly_scale * title_premium_pct[title] * quarter_weeks
```

If `combined_overscale_includes_title` is true, title premium = 0.

### Seniority

Look up the employee's `years_of_service` in the `seniority_weekly` bands.
Floored to the nearest band where `min_years <= years_of_service <= max_years`
(max_years of null means no upper bound).

```
seniority = seniority_weekly_amount * quarter_weeks
```

### Overscale

```
overscale = overscale_weekly * quarter_weeks
```

---

## Current-Year Compensation Summary

For the given ensemble:

1. **roster_count**: number of employees in the ensemble roster.
2. **pay_types**: the ordered list directly from the rate book's `pay_types`.
3. **quarter_totals**: for each quarter, sum all four pay components across
   all employees.
4. **annual_pay_type_totals**: for each pay type, sum across all employees
   and all four quarters.
5. **annual_total**: sum of all annual_pay_type_totals.
6. **largest_pay_type**: the pay type string with the highest
   annual_pay_type_total.
7. **combined_overscale_employee_count**: count of employees where
   `combined_overscale_includes_title` is true.
8. **partial_quarter_employee_count**: count of employees whose
   `weeks_by_quarter` has any quarter differing from the standard (13) OR
   whose notes mention "Partial-quarter".

All currency fields to 2 decimals.

---

## Board Compensation Forecast

Given an ensemble, scenario_id, and forecast years (current, year_plus_1,
year_plus_2):

### Current year

Same as the current-year summary's `annual_total`.

### Year + 1

1. Add 1 to each employee's `years_of_service`. Look up new seniority band.
2. For each employee, per quarter:
   - `mws` = minimum_weekly_scale * (1 + mws_growth) * quarter_weeks
   - `title_premium` = minimum_weekly_scale * (1 + mws_growth)
     * title_premium_pct[title] * title_pct_multiplier * quarter_weeks
   - `seniority` = new_seniority_amount * (1 + seniority_growth)
     * quarter_weeks
   - `overscale` = overscale_weekly * (1 + overscale_growth)
     * quarter_weeks
3. Sum across all employees and quarters for the annual total.

### Year + 2

Same as Year + 1 but add 2 to years_of_service and use the
`year_plus_2` scenario parameters.

### Growth rates

```
year_plus_1_vs_current = (year_plus_1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```

Rounded to 4 decimals.

### Year + 2 detail

Compute Year + 2 quarter totals and pay type totals the same way as
the current-year summary, using Year + 2 scenario parameters.

### largest_growth_pay_type

For each pay type, compute: (year_plus_2_pay_type_total - current_pay_type_total).
The pay type with the largest absolute increase is `largest_growth_pay_type`.

### Treatment counts

Same definitions as current-year: `combined_overscale_employee_count` and
`partial_quarter_employee_count`.
