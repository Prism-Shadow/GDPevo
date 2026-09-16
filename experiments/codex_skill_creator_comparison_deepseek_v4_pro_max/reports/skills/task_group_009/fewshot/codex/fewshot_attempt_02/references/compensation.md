## Compensation API Reference — Crescent Finance Ops

### Endpoints

| Endpoint | Description | Query Params |
|---|---|---|
| /api/compensation/rate-book | Current-year rates: MWS, seniority bands, title premiums, quarter weeks, business rules | none |
| /api/compensation/rosters | Employee rosters per ensemble: quarters, titles, overscale, years of service | ensemble_id |
| /api/compensation/scenarios | Forecast scenario parameters (growth multipliers per pay type per year) | none (returns all scenarios) |

### Rate Book Structure

The rate book returns:
- current_year: integer year
- minimum_weekly_scale: base weekly rate (currency)
- pay_types: ordered list of pay type strings
- quarter_weeks: {Q1, Q2, Q3, Q4} each with week count (13 or variable)
- seniority_weekly: array of bands [{min_years, max_years, weekly_amount}]
- title_premium_pct: map of title string to premium percentage
- business_rules: array of rule strings

### Roster Structure

Each roster entry has:
- employee_id, ensemble_id, ensemble_name
- title (string or null), overscale_weekly (currency), years_of_service (integer)
- weeks_by_quarter: {Q1, Q2, Q3, Q4} (may differ from rate book quarter_weeks for partial-quarter employees)
- combined_overscale_includes_title: boolean
- notes: string

### Pay Calculation

For each employee, per-quarter and annual pay:

1. **Base**: minimum_weekly_scale * weeks_in_quarter (use roster weeks_by_quarter)
2. **Title Premium**: If title is not null AND combined_overscale_includes_title is false: MWS * title_premium_pct[title] * weeks_in_quarter
3. **Seniority**: Look up band where years_of_service >= min_years AND (max_years is null OR years_of_service <= max_years). Pay = band.weekly_amount * weeks_in_quarter.
4. **Overscale**: overscale_weekly * weeks_in_quarter

Sum these four components per employee, then sum across employees.

Rounding: Use standard round-half-up. In Python: Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for currency.

### Current-Year Summary

Required fields: ensemble_id, current_year, roster_count, pay_types (ordered from rate book), quarter_totals, annual_pay_type_totals, annual_total, largest_pay_type, combined_overscale_employee_count, partial_quarter_employee_count.

- largest_pay_type: the pay type with the largest annual_pay_type_totals value (absolute dollar amount)
- combined_overscale_employee_count: count of roster entries where combined_overscale_includes_title is true
- partial_quarter_employee_count: count of roster entries where weeks_by_quarter differs from the rate book quarter_weeks

### Forecast Calculation

For forecast scenarios, compute three years:

**Current year**: exact same as current-year summary above.

**Year + 1**: Apply year_plus_1 growth values to the base rate book, independently.
- mws_y1 = mws * (1 + year_plus_1.mws_growth)
- title_pcts_y1[t] = title_pcts[t] * year_plus_1.title_pct_multiplier
- seniority_bands_y1: each band weekly_amount *= (1 + year_plus_1.seniority_growth)
- Per employee: overscale_y1 = overscale_weekly * (1 + year_plus_1.overscale_growth), years_of_service += 1

**Year + 2**: Chain on top of Year + 1 values for all four components.
- mws_y2 = mws_y1 * (1 + year_plus_2.mws_growth)
- title_pcts_y2[t] = title_pcts_y1[t] * year_plus_2.title_pct_multiplier
- seniority_bands_y2: each band weekly_amount from seniority_bands_y1 multiplied by (1 + year_plus_2.seniority_growth)
- Per employee: overscale_y2 = overscale_y1 * (1 + year_plus_2.overscale_growth), years_of_service += 2 (from original)

Do NOT apply Year + 2 growth independently from the base rate book — always chain from Year + 1 values.

Forecast output:
- annual_totals: {current, year_plus_1, year_plus_2} each rounded currency
- growth_rates: {year_plus_1_vs_current, year_plus_2_vs_year_plus_1} each 4-decimal ratio
- year_plus_2_quarter_totals: Q1-Q4 for Y2 forecast
- year_plus_2_pay_type_totals: by pay type for Y2
- largest_growth_pay_type: pay type with the highest percentage growth rate from current to year_plus_2 (i.e., (y2_total / cur_total - 1) per pay type)
- combined_overscale_employee_count: same as current-year definition
- partial_quarter_employee_count: same as current-year definition

### Sorting / Ordering

- pay_types always in the order returned by the rate book
- Roster count determined by total entries in the roster endpoint result
- All currency: 2 decimal places using standard round-half-up
- Growth rates: 4 decimal places using standard round-half-up
