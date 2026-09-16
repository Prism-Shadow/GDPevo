# Compensation Domain Rules

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `/api/compensation/rate-book` | Pay types, current_year, quarter_weeks, minimum_weekly_scale, seniority bands, title premium percentages, business rules |
| `/api/compensation/rosters` | Per-ensemble employee records: years_of_service, title, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter, notes |
| `/api/compensation/scenarios` | Forecast growth factors per scenario: `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier` for year_plus_1 and year_plus_2 |

GET all needed endpoints once. No filtering parameters, no authentication.

## Pay Types (in order from rate book)

The rate book `pay_types` array defines the canonical order. Always use that exact order for ordered lists and for `pay_type_totals` keys.

1. Minimum Weekly Scale (MWS)
2. Titled Position Premium
3. Seniority
4. Overscale

## Per-Employee Weekly Computation

For each employee on a roster, compute four pay components per week:

```
mws_weekly        = minimum_weekly_scale                                    (always applies)
seniority_weekly  = lookup(years_of_service, seniority_weekly bands)        (0 if not in a band)
overscale_weekly   = employee.overscale_weekly                              (from roster)
```

**Titled Position Premium:**
- If `combined_overscale_includes_title` is true, skip title premium for this employee.
- Otherwise, if `title` is non-null, look up `title_premium_pct[title]` and compute:
  ```
  title_weekly = minimum_weekly_scale * title_premium_pct[title]
  ```
- If title is null or `combined_overscale_includes_title` is true, `title_weekly = 0`.

Per-week total = `mws_weekly + seniority_weekly + overscale_weekly + title_weekly`

## Quarterly and Annual Aggregation

For each employee, multiply per-week total by the actual weeks worked in each quarter from `weeks_by_quarter`. Sum across all employees in the ensemble for quarter totals. Sum quarter totals for the annual total.

Separate totals by pay type:
- MWS total = sum of `mws_weekly * weeks` across all employees
- Titled Position Premium total = sum of `title_weekly * weeks`
- Seniority total = sum of `seniority_weekly * weeks`
- Overscale total = sum of `overscale_weekly * weeks`

## Roster Treatment Flags

**combined_overscale_employee_count:** Count employees where `overscale_weekly > 0` AND `combined_overscale_includes_title` is true.

**partial_quarter_employee_count:** Count employees where any quarter has fewer weeks than the standard `quarter_weeks` value from the rate book (typically 13).

## Forecast Computation

For a scenario, apply growth factors to the base rate:

```
Year+1 MWS       = current MWS * (1 + year_plus_1.mws_growth)
Year+2 MWS       = Year+1 MWS  * (1 + year_plus_2.mws_growth)
Year+1 seniority = current seniority * (1 + year_plus_1.seniority_growth)
Year+2 seniority = Year+1 seniority * (1 + year_plus_2.seniority_growth)
Year+1 overscale = current overscale * (1 + year_plus_1.overscale_growth)
Year+2 overscale = Year+1 overscale * (1 + year_plus_2.overscale_growth)
Year+1 title_pct = current title_pct * year_plus_1.title_pct_multiplier
Year+2 title_pct = Year+1 title_pct * year_plus_2.title_pct_multiplier
```

Years of service advance: +1 year for Year+1, +2 years for Year+2 (for seniority band lookup). Overscale weekly amounts also grow by the overscale_growth factor, stacked year over year. Week counts from the roster do not change.

## Largest Pay Type / Largest Growth

For current-year summaries, `largest_pay_type` is the pay type with the highest annual total. For forecasts, `largest_growth_pay_type` is the pay type with the highest absolute growth from the base (current) year to Year+2. Compare the four pay-type totals.

Ties: prefer the pay type that appears first in the rate book `pay_types` order.

## Rounding

- Currency values: round to 2 decimal places.
- Growth rates: round to 4 decimal places.
- Counts: integers.
