# Crescent Finance Ops — Skill Reference

## Environment

All tasks target a remote Finance Ops API. Use the base URL provided in each task's `payloads/environment_access.json` (or the override in the repository's `environment_access.md`). Use HTTP, not HTTPS.

### Public API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/finance/branches` | Branch list with region assignments |
| `GET /api/finance/period-map` | Fiscal period → calendar month mapping |
| `GET /api/finance/accounts` | Chart of accounts and categories |
| `GET /api/finance/records` | All branch-period financial records |
| `GET /api/compensation/rate-book` | Pay rates, scales, premiums, quarter weeks, business rules |
| `GET /api/compensation/rosters` | Employee rosters per ensemble with service history |
| `GET /api/compensation/scenarios` | Forecast growth rates and multipliers per scenario |
| `GET /api/payroll/rate-book` | Service rates, premium percentages, guarantee, conflict thresholds |
| `GET /api/payroll/productions` | Weekly production schedules and musician rosters |

---

## Module 1 — Finance (Branch / Regional Reporting)

### Period Map

The period map uses rolling month numbers. M1 through M12 belong to `fiscal_year` 2024; M13 through M24 belong to `fiscal_year` 2025. A period label is formatted as `"Mon YYYY"` (e.g., `"Dec 2025"` for M24).

### Accounts and Categories

Revenue accounts: `product_revenue`, `service_revenue` — sum for total revenue.

COGS accounts: `direct_materials_cogs`, `direct_labor_cogs` — sum for total COGS.

SG&A accounts: `sales_sga`, `admin_sga`, `occupancy_sga` — sum for total SG&A.

Allocations: `shared_service_allocations`.

Operating accounts: `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`.

### Income Statement Formulas (per period or aggregated)

```
revenue = product_revenue + service_revenue
cogs = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga = sales_sga + admin_sga + occupancy_sga
ebitda = gross_margin - sga - shared_service_allocations
```

### EBITDA Margin

```
ebitda_margin = ebitda / revenue   (round to 4 decimals)
```

### ARPU (Average Revenue Per Unit — actually "per month" in practice)

```
arpu = total_fiscal_year_revenue / 12
```

### Sales Per Labor Headcount

```
sales_per_labor_headcount = total_fiscal_year_revenue / sum(labor_headcount_over_periods)
```

Denominator is the sum of the `labor_headcount` account values across all periods in the scope, not an average.

### Revenue Growth Rate

```
revenue_growth_pct = (fy2025_revenue - fy2024_revenue) / fy2024_revenue
```

Round to 4 decimals.

### EBITDA Growth Rate

```
ebitda_growth_pct = (fy2025_ebitda - fy2024_ebitda) / fy2024_ebitda
```

Use the raw signed denominator. Round to 4 decimals.

### Region Reconciliation Variance

```
region_reconciliation_variance = region_consolidated_ebitda - sum(branch_level_ebitdas)
```

The region's consolidated FY2025 EBITDA minus the sum of each branch's independently computed FY2025 EBITDA. Round to 2 decimals.

### Branch Rankings

**Sales growth rank:** Rank all branches descending by `(FY2025 revenue - FY2024 revenue) / FY2024 revenue`. Resolve ties by branch ID ascending.

**Top ARPU branch:** Compute each branch's FY2025 ARPU (revenue / 12) and pick the branch with the highest value.

### Region Context

The `branch_ids` list must be sorted in ascending order. EBITDA rank is 1-based descending (rank 1 = highest EBITDA within the region).

---

## Module 2 — Compensation (Current-Year Summary)

### Rate Book Constants

- `minimum_weekly_scale`: base weekly pay (e.g., 2520.0)
- `quarter_weeks`: weeks per quarter (typically 13 for all four quarters)
- `seniority_weekly`: list of bands `[{min_years, max_years, weekly_amount}, ...]`
- `title_premium_pct`: map of title strings to decimal percentages
- `pay_types`: ordered list `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `current_year`: the fiscal year (e.g., 2026)

### Per-Employee Compensation (Current Year)

For each employee on the roster, compute quarterly pay:

**Minimum Weekly Scale** per quarter = `minimum_weekly_scale × weeks_in_quarter`

**Seniority** per quarter = `seniority_weekly(years_of_service) × weeks_in_quarter`

- Find the band where `min_years ≤ years_of_service ≤ max_years` (if `max_years` is null, any `≥ min_years` qualifies). Employees with 0-4 years of service fall in the 0-4 band (weekly amount 0.0).

**Titled Position Premium** per quarter = `title_premium_pct(title) × minimum_weekly_scale × weeks_in_quarter`

- **Skip this** if `combined_overscale_includes_title` is `true` for the employee. The overscale amount already includes the title premium in that case.

**Overscale** per quarter = `overscale_weekly × weeks_in_quarter`

Total per quarter = sum of the four components above.

### Roster Counts

- `roster_count`: total number of employees in the ensemble roster
- `combined_overscale_employee_count`: count of employees where `combined_overscale_includes_title` is `true`
- `partial_quarter_employee_count`: count of employees with any quarter having weeks ≠ 13, OR with notes containing "Partial-quarter"

### Annual Totals

Sum all employees across all four quarters for each pay type. `annual_total` = sum of all four pay-type totals. `largest_pay_type` = the pay type with the largest annual total.

---

## Module 3 — Compensation (Forecast)

### Scenario Data

Each scenario provides growth rates for year_plus_1 and year_plus_2:
- `mws_growth`: minimum weekly scale growth (decimal)
- `overscale_growth`: overscale growth (decimal)
- `seniority_growth`: seniority pay growth (decimal)
- `title_pct_multiplier`: multiplier on title premium percentage (1.0 = no change)

### Forecast Computation Rules

1. **Years of service**: Add 1 for Year+1, add 2 for Year+2, then look up the seniority band using the adjusted years.

2. **Minimum Weekly Scale**: `base_mws × (1 + mws_growth) × weeks`

3. **Seniority**: `seniority_weekly(adjusted_years_of_service) × weeks × (1 + seniority_growth)`

4. **Titled Position Premium**: `title_premium_pct(title) × title_pct_multiplier × adjusted_mws × weeks`

   - Skip if `combined_overscale_includes_title` is `true`.

5. **Overscale**: `overscale_weekly × weeks × (1 + overscale_growth)`

6. **Growth rates** between years: `(later_total - earlier_total) / earlier_total`, rounded to 4 decimals.

7. **Largest growth pay type**: Compare each pay type's current-year total to its Year+2 total. The pay type with the largest absolute increase (Year+2 − current) is the `largest_growth_pay_type`.

---

## Module 4 — Payroll (Weekly Production)

### Data Sources

- `GET /api/payroll/productions` — each production has a `schedule` (list of service entries) and a `roster` (list of musicians with flags and assigned service IDs).
- `GET /api/payroll/rate-book` — service rates, premium percentages, conflict thresholds, weekly guarantee.

### Service Type to Category Mapping

| Service Type | Category |
|---|---|
| `Performance` | `performance` |
| `Audit` | `audit` |
| `Rehearsal` | `rehearsal` |
| `1hr Sound Check` / `2hr Sound Check` | `sound_check` |

### Service Pay Calculation

- **Rehearsal**: hourly rate × max(duration_hours, 3.0) — three-hour minimum call applies.
- **Performance / Audit**: flat per-service rate.
- **Sound Check**: flat rate per the schedule type (1hr or 2hr).

### Premiums

Premiums are applied to base service pay (the raw service rates, before any adjustments) and are additive. Each premium that applies is calculated as `premium_pct × base_service_pay`:

| Flag | Premium Key | Rate |
|---|---|---|
| `principal == true OR lead == true` | `principal_or_lead` | 0.15 (15%) |
| `quartet == true` | `quartet` | 0.15 (15%) |
| `electronic == true` | `electronic` | 0.25 (25%) |

Premium amounts accumulate into the `premium` category total.

### Doubles Premium

- `doubles == 1`: `first_double` rate (0.25) × base_service_pay
- `doubles >= 2`: `first_double` rate × base_service_pay + `additional_double` rate (0.10) × base_service_pay × (doubles − 1)

Doubles premiums accumulate into the `doubles` category total.

### Vacation

For musicians with `vacation_eligible == true`:
```
vacation = 0.04 × (base_service_pay + all_premiums_including_doubles)
```

Vacation accumulates into the `vacation` category.

### Weekly Guarantee Adjustment

For **non-substitute** musicians where `base_service_pay < weekly_guarantee`:
```
guarantee_adjustment = weekly_guarantee - base_service_pay
```

This applies only to guaranteed regular players. It accumulates into the `guarantee_adjustment` category.

### Substitute Adjustment

Substitute musicians (`substitute == true`) are not eligible for vacation or guarantee. Their `substitute_adjustment` category may hold adjustments. Check whether any production-specific logic applies (e.g., a substitute may have a different pay treatment). If no explicit substitute adjustment rule is provided, the category may be 0.0 for all musicians.

### Musician Total

```
total = base_service_pay + premium + doubles + vacation + guarantee_adjustment + substitute_adjustment
```

### Conflict Flags

Check the production schedule against conflict thresholds:

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any rehearsal starts before `rehearsal_earliest_start` (e.g., "09:00") |
| `REHEARSAL_LATE_END` | Any rehearsal ends after `rehearsal_latest_end` (e.g., "18:30") |
| `SERVICE_OVER_TIME_LIMIT` | Any service's `duration_hours` exceeds its type's `service_time_limits` value |
| `SOUND_CHECK_DURATION_MISMATCH` | `1hr Sound Check` type where `duration_hours ≠ 1.0`, or `2hr Sound Check` type where `duration_hours ≠ 2.0` |

Times are compared as `HH:MM` strings lexicographically or by converting to minutes since midnight.

Return conflict flags as an alphabetically sorted list. Only include flags that actually trigger.

---

## Output Conventions (All Modules)

### Rounding

- **Currency values**: round to 2 decimal places.
- **Percent and ratio values**: round to 4 decimal places.
- Apply rounding only at the final output level, not at intermediate steps (use full-precision arithmetic throughout computation).

### List Ordering

- **Branch IDs**: ascending string sort (e.g., `"BR-004"`, `"BR-005"`, `"BR-006"`).
- **Per-musician lists**: ascending by `musician_id`.
- **Conflict flags**: alphabetically sorted.
- **Pay types**: use the order from the rate book's `pay_types` array.
- **Ranks**: 1-based descending (rank 1 = highest value). For ties, use ascending branch/musician ID as the tiebreaker.

### Field Presence

- Include all `required_top_level_keys` from the answer template.
- Use the exact field names and nesting structure specified.
- For payroll, include all category keys in `category_totals` even if some are 0.0 (represent as `0.0`, not omitted).
- For per-musician detail, only include nonzero categories within each musician's `categories` object.

---

## Common Pitfalls

### Finance Module

- **Period mapping**: Always verify `M1`–`M12` maps to one fiscal year and `M13`–`M24` to the next. Don't assume January = M1 for both years.
- **Account aggregation**: `sales_sga`, `admin_sga`, and `occupancy_sga` are three separate accounts that must be summed for total SG&A. Don't double-count.
- **EBITDA sign**: All components (revenue positive, COGS and SG&A and allocations negative relative to EBITDA) should be computed consistently. Check whether the denominator in EBITDA growth should use the raw (signed) value.
- **Reconciliation variance**: Always compute branch-level EBITDA independently (per-branch, not just dividing region totals) and compare to consolidated region EBITDA. The difference is the reconciliation variance.
- **Sales growth denominator**: Use FY2024 revenue (the prior year), not FY2025.

### Compensation Module

- **Combined overscale with title**: When `combined_overscale_includes_title` is `true`, the overscale amount already compensates for the titled position. Do NOT add a separate Titled Position Premium line item for that employee.
- **Seniority band lookup**: Check `min_years ≤ years_of_service ≤ max_years` inclusive. The 0-4 band pays 0.0 weekly seniority — don't skip the band and fall into a higher band.
- **Partial quarter**: Count employees as partial-quarter if ANY quarter's weeks differ from the standard quarter_weeks value (typically 13), OR if their notes mention "Partial-quarter". Weeks less than 13 are the most reliable indicator.
- **Forecast year indexing**: Year+1 adds 1 to years_of_service; Year+2 adds 2. Growth factors are then applied to the seniority weekly amount derived from the adjusted years.

### Payroll Module

- **Rehearsal minimum**: Rehearsal pay is `max(duration_hours, 3.0) × hourly_rate`. Not `3.0 × hourly_rate` for all rehearsals.
- **Premium base**: Premiums are computed on base service pay (raw service rates only), not on base + prior premiums. All premiums are additive and computed independently from the same base.
- **Guarantee**: The guarantee adjustment compares `base_service_pay` (raw service rates, no premiums) against `weekly_guarantee`. It does not apply to substitutes. The guarantee makes up the shortfall: `weekly_guarantee − base_service_pay` (0.0 if no shortfall).
- **Vacation base**: Vacation is 4% of `base_service_pay + all premiums including doubles`, but computed *before* any guarantee adjustment is added.
- **Service over time limit**: Compare `duration_hours` (a float) against `service_time_limits[service_type]`. It's a strict greater-than check.
- **Sound check mismatch**: Compare the actual `duration_hours` in the schedule against the expected duration implied by the service type name (1.0 for "1hr Sound Check", 2.0 for "2hr Sound Check").
