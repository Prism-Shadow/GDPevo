## Endpoints

| Endpoint | Description |
|---|---|
| `/api/compensation/rate-book` | Pay rates, quarter weeks, seniority bands, title premiums |
| `/api/compensation/rosters` | All employees per ensemble with titles, tenure, overscale |
| `/api/compensation/scenarios` | Forecast growth rates per scenario per year |

## Rate Book Structure

The rate book (`/api/compensation/rate-book`) returns:
- `current_year` — integer year for base computation
- `minimum_weekly_scale` — base weekly pay for all musicians
- `quarter_weeks` — `{Q1: N, Q2: N, Q3: N, Q4: N}`
- `pay_types` — ordered list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `seniority_weekly` — array of `{min_years, max_years, weekly_amount}`
- `title_premium_pct` — `{"Principal": 0.20, "Concertmaster": 0.22, ...}`
- `business_rules` — critical rule strings (see below)

## Business Rules

1. **Quarter weeks**: Use roster quarter weeks, not a fixed 13-week quarter, when
   partial-quarter employees are listed. The weeks_by_quarter values on each
   roster record override the rate book default.

2. **Combined overscale**: If `combined_overscale_includes_title` is true, do
   not add a titled position premium separately for that employee. The overscale
   amount already includes it.

3. **Forecast years**: For forecast years, add one year of service for Year+1
   and two years of service for Year+2 before assigning seniority bands. This
   means an employee with 3 years of service in the current year has 4 years for
   Year+1 seniority and 5 for Year+2.

## Roster Structure

Each roster entry has:
- `employee_id`, `ensemble_id`, `ensemble_name`
- `title` — null or one of: Principal, Concertmaster, Associate Principal, Assistant Principal, Section Lead
- `years_of_service` — integer
- `overscale_weekly` — additional weekly pay above scale
- `combined_overscale_includes_title` — boolean
- `weeks_by_quarter` — `{Q1, Q2, Q3, Q4}` week counts (may differ from 13)
- `notes` — may flag partial-quarter service or side letters

## Per-Employee Pay Computation

For each employee, compute four pay components:

### 1. Minimum Weekly Scale (MWS)

```
mws = minimum_weekly_scale * total_weeks_worked
```

Total weeks = sum of the employee's weeks_by_quarter values.

### 2. Titled Position Premium

Only applies when `title` is non-null AND `combined_overscale_includes_title`
is false:

```
title_premium = mws * title_premium_pct[title]
```

If `combined_overscale_includes_title` is true, title_premium = 0.

### 3. Seniority

Find the seniority band where `years_of_service` falls in
`[min_years, max_years]`. Use the `weekly_amount` from that band:

```
seniority = weekly_amount * total_weeks_worked
```

For forecast years, add the appropriate years to `years_of_service` before
looking up the band.

### 4. Overscale

```
overscale = overscale_weekly * total_weeks_worked
```

### Total per employee

```
employee_total = mws + title_premium + seniority + overscale
```

## Quarter Totals

For each quarter Q, sum `(mws_per_week + title_premium_per_week + seniority_per_week + overscale_weekly) * weeks_in_quarter` across all employees.

The per-week amounts are: `mws_per_week = minimum_weekly_scale`,
`seniority_per_week = seniority_weekly_amount`, and the title/seniority/overscale
amounts as computed above. Multiply each by that employee's weeks in the quarter
from `weeks_by_quarter`.

## Annual Pay Type Totals

Sum each pay type component across all employees for the full year.

## Partial-Quarter Employees

An employee is partial-quarter if any of their `weeks_by_quarter` values differs
from the rate book's default quarter_weeks value. Count unique employees with
any quarter where `weeks` != default.

## Combined Overscale Employee Count

Count employees where `combined_overscale_includes_title` is true. Do not
double-count — each employee is counted once.

## Forecast Scenarios

Scenarios (`/api/compensation/scenarios`) return growth multipliers per year:

```
case_maple_board:
  year_plus_1: { mws_growth, overscale_growth, seniority_growth, title_pct_multiplier }
  year_plus_2: { mws_growth, overscale_growth, seniority_growth, title_pct_multiplier }
```

To compute a forecast year's pay:

1. Start with the current-year roster and rate book.
2. For Year+1, add 1 to each employee's `years_of_service` for seniority lookup.
   For Year+2, add 2.
3. Apply growth rates:
   - `forecast_mws = current_mws * (1 + mws_growth)`
   - `forecast_seniority = current_seniority * (1 + seniority_growth)`
   - `forecast_overscale = current_overscale * (1 + overscale_growth)`
   - `forecast_title_pct = current_title_pct * title_pct_multiplier` (the
     multiplier applies to the premium percentage itself, so the title premium
     is `forecast_mws * (title_pct * title_pct_multiplier)`)
4. Recompute all totals with the grown values.

## Largest Pay Type / Largest Growth Pay Type

For current-year summaries: `largest_pay_type` is the pay type with the highest
annual total across all employees. Break ties by comparing the next-highest
component; use the rate book's `pay_types` order as final tiebreaker.

For forecasts: `largest_growth_pay_type` is the pay type with the largest
absolute growth (year_plus_2 - current) in its annual total.

## Growth Rates

```
year_plus_1_vs_current = (year_plus_1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```

Rounded to 4 decimals.

## Rounding

Currency values to 2 decimals. Growth rates to 4 decimals.
