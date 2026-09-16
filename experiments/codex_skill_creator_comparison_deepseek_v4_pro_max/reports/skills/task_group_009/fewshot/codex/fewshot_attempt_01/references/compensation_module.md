## Table of Contents

- Endpoints and Schemas
- Pay Type Computation Rules
- Current-Year Summary Computation
- Roster Treatment Counts
- Scenario Forecast Computation

## Endpoints and Schemas

### GET /api/compensation/rate-book

Returns a rate-book object:

```
{
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
    "Assistant Principal": 0.1,
    "Associate Principal": 0.1,
    "Concertmaster": 0.22,
    "Principal": 0.2,
    "Section Lead": 0.15
  },
  "business_rules": [...]
}
```

Key fields:
- `current_year`: the current fiscal year (2026 in the dataset)
- `minimum_weekly_scale` (MWS): base weekly pay for every rostered employee
- `quarter_weeks`: number of weeks per quarter; always 13/13/13/13
- `title_premium_pct`: additional percentage of MWS by title
- `seniority_weekly`: extra weekly amount based on years_of_service bands

### GET /api/compensation/rosters

Returns a list of employee roster objects:

```
{
  "employee_id": "ENS-XXX-001",
  "ensemble_id": "ENS-XXX",
  "ensemble_name": "Ensemble Name",
  "title": "Principal" or "",
  "years_of_service": 3,
  "overscale_weekly": 0.0,
  "combined_overscale_includes_title": false,
  "weeks_by_quarter": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
  "notes": ""
}
```

### GET /api/compensation/scenarios

Returns an object keyed by scenario_id:

```
{
  "case_example": {
    "description": "Example planning case.",
    "year_plus_1": {"mws_growth": 0.XXX, "overscale_growth": 0.XXX, "seniority_growth": 0.XXX, "title_pct_multiplier": X.X},
    "year_plus_2": {"mws_growth": 0.XXX, "overscale_growth": 0.XXX, "seniority_growth": 0.XXX, "title_pct_multiplier": X.X}
  }
}
```

Growth fields multiply or add to base values; `title_pct_multiplier` multiplies the title_premium_pct.

## Pay Type Computation Rules

For one employee in one quarter:

1. **Minimum Weekly Scale** = MWS * weeks_in_quarter
2. **Titled Position Premium** = MWS * title_premium_pct * weeks_in_quarter (only when title is non-empty AND combined_overscale_includes_title is false)
3. **Seniority** = seniority_weekly_amount * weeks_in_quarter (look up the band matching years_of_service; if years_of_service < 5, seniority is 0)
4. **Overscale** = overscale_weekly * weeks_in_quarter (from the roster record)

All amounts rounded to 2 decimals after each computation.

If `combined_overscale_includes_title` is true for an employee, do NOT add a separate Titled Position Premium. The overscale amount already covers the title premium.

## Current-Year Summary Computation

1. Filter roster entries to the target `ensemble_id`.
2. `roster_count` = number of distinct employee records for the ensemble.
3. `current_year` = rate_book.current_year.
4. Compute per-employee quarterly totals by summing all four pay types for each quarter.
5. `quarter_totals` = sum of all employee totals per quarter, rounded to 2 decimals.
6. `annual_pay_type_totals` = sum of each pay type across all employees and all quarters, rounded to 2 decimals.
7. `annual_total` = sum of all four pay type totals, rounded to 2 decimals.
8. `pay_types` = ordered list from the rate book: ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"].
9. `largest_pay_type` = the pay type with the largest `annual_pay_type_totals` value. If tied, use the order from `pay_types`.
10. `combined_overscale_employee_count` = count of employees where `combined_overscale_includes_title` is true.
11. `partial_quarter_employee_count` = count of employees where any quarter's `weeks_by_quarter` is less than the rate-book quarter_weeks value for that quarter.

## Roster Treatment Counts

Two counts from the roster:

- **combined_overscale_employee_count**: Count employees where `combined_overscale_includes_title` is true. These employees have their title premium embedded in their overscale rate.
- **partial_quarter_employee_count**: Count employees where any of their four `weeks_by_quarter` values is strictly less than the rate-book's `quarter_weeks` value for that quarter. A full-year employee has exactly 13 weeks in every quarter.

## Scenario Forecast Computation

For a forecast task (scenarios endpoint present):

1. Start with the base pay-type totals from the current-year computation (without rounding intermediate steps).
2. For Year + 1:
   - MWS_year_plus_1 = current_MWS_total * (1 + mws_growth)
   - Overscale_year_plus_1 = current_Overscale_total * (1 + overscale_growth)
   - Seniority_year_plus_1: first advance years_of_service by 1 year for every employee, recompute seniority bands, then calculate the total, then multiply by (1 + seniority_growth)
   - Title_year_plus_1 = current_Title_total * title_pct_multiplier
3. For Year + 2:
   - Use year_plus_2 growth rates from the scenario.
   - Advance years_of_service by 2 years total from the base (not 1 from year_plus_1).
   - Compute seniority bands with the advanced years_of_service, then apply seniority_growth.
4. Round all final pay-type totals to 2 decimals.
5. Compute growth rates:
   - `year_plus_1_vs_current` = (annual_total_year_plus_1 - annual_total_current) / annual_total_current, rounded to 4 decimals
   - `year_plus_2_vs_year_plus_1` = (annual_total_year_plus_2 - annual_total_year_plus_1) / annual_total_year_plus_1, rounded to 4 decimals
6. `year_plus_2_quarter_totals`: for Year + 2, compute quarter totals from the forecast pay types. Since the forecast applies uniform growth, distribute the year_plus_2 annual total proportionally by each employee's quarter ratios from the base year.
7. `largest_growth_pay_type`: compute absolute growth (year_plus_2 - current) for each pay type; the one with the largest absolute increase.

For partial-quarter employees in forecast years: use their actual `weeks_by_quarter` from the roster (not the full quarter_weeks) when applying growth. The partial_quarter_employee_count remains the same as the current-year count.

For seniority band recomputation in forecast years: add the forecast year offset (1 for year+1, 2 for year+2) to each employee's `years_of_service`, then look up the new band. This changes which employees qualify for seniority pay.
