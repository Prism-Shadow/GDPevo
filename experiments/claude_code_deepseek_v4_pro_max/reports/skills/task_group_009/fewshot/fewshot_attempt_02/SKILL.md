# Crescent Finance Ops — Transferable Skill

## Environment

All tasks use a single remote Finance Ops API. The base URL is provided in the task's `environment_access.json` (or overridden by `environment_access.md`). Always use HTTP, never HTTPS. Do not use localhost unless the override explicitly points there.

## API Reference

### Finance Domain

| Endpoint | Returns |
|---|---|
| `GET /api/finance/branches` | Array of `{branch_id, branch_name, region_id, region_name}` for all 12 branches |
| `GET /api/finance/period-map` | Array of `{fiscal_year, month_name, month_number, period}` mapping M1–M24 |
| `GET /api/finance/accounts` | Array of `{account, category, display_name, metric_type}` — currency or count |
| `GET /api/finance/records` | Array of `{account, branch_id, branch_name, region_id, values: {M1…M24}}` |

**Period Convention:**
- M1 – M12 → earlier fiscal year (typically FY2024)
- M13 – M24 → later fiscal year (typically FY2025)
- Current year's mapping is always available from the period-map endpoint; query it, do not hardcode.

**Account Categories:**

| account | category | metric_type |
|---|---|---|
| product_revenue, service_revenue | revenue | currency |
| direct_materials_cogs, direct_labor_cogs | cogs | currency |
| sales_sga, admin_sga, occupancy_sga | sga | currency |
| shared_service_allocations | allocations | currency |
| active_customers, labor_headcount, orders, revenue_units, admin_headcount, backlog | operating | count |

### Compensation Domain

| Endpoint | Returns |
|---|---|
| `GET /api/compensation/rate-book` | `{current_year, minimum_weekly_scale, quarter_weeks: {Q1-Q4}, seniority_weekly: [{min_years, max_years, weekly_amount}], title_premium_pct: {title→pct}, pay_types: [...], business_rules: [...]}` |
| `GET /api/compensation/rosters` | Array of `{employee_id, ensemble_id, ensemble_name, title, years_of_service, overscale_weekly, combined_overscale_includes_title, weeks_by_quarter: {Q1-Q4}, notes}` |
| `GET /api/compensation/scenarios` | Map of `{scenario_id: {description, year_plus_1: {mws_growth, overscale_growth, seniority_growth, title_pct_multiplier}, year_plus_2: {...}}}` |

### Payroll Domain

| Endpoint | Returns |
|---|---|
| `GET /api/payroll/rate-book` | `{service_rates: {type→rate}, premium_pct: {name→pct}, weekly_guarantee, conflict_thresholds: {rehearsal_earliest_start, rehearsal_latest_end}, service_time_limits: {type→hours}, business_rules: [...]}` |
| `GET /api/payroll/productions` | Array of `{production_id, title, week_start, schedule: [{service_id, service_type, date, start_time, end_time, duration_hours}], roster: [{musician_id, name, instrument, assigned_service_ids, doubles, lead, principal, electronic, quartet, substitute, vacation_eligible}]}` |

---

## Calculation Formulas

### 1. Branch Income Statement (per period or per FY sum)

```
Revenue        = sum(product_revenue + service_revenue)
COGS           = sum(direct_materials_cogs + direct_labor_cogs)
Gross Margin   = Revenue − COGS
SG&A           = sum(sales_sga + admin_sga + occupancy_sga)
Allocations    = sum(shared_service_allocations)
EBITDA         = Gross Margin − SG&A − Allocations
```

Per-period: use values for a single period key (e.g. M24).
Per-FY: sum values across all 12 period keys in that fiscal year (e.g. M13–M24 for FY2025).

### 2. Branch Ratios and Derived Metrics (FY level only)

```
EBITDA Margin             = EBITDA / Revenue

ARPU (Avg Revenue Per User/Active Customer)
  = FY Revenue / Σ active_customers across all 12 FY periods
  Use the sum of the count metric, not an average.

Sales per Labor Headcount
  = FY Revenue / Σ labor_headcount across all 12 FY periods
  Use the sum of the count metric, not an average.
```

### 3. MoM Revenue Variance (Branch)

```
amount = revenue(current_period) − revenue(prior_period)
pct    = amount / revenue(prior_period)
```

### 4. Period-over-Period Growth Rates (Branch or Region)

```
revenue_growth_pct = (FY{later}_revenue − FY{earlier}_revenue) / FY{earlier}_revenue
ebitda_growth_pct  = (FY{later}_ebitda  − FY{earlier}_ebitda)  / FY{earlier}_ebitda
```

### 5. Regional Aggregation

Sum each account across all branches in the region, then apply the income statement formulas above per FY. Branch membership is determined from `/api/finance/branches` — filter by `region_id`.

Region-level `revenue`, `sga`, `allocations`, and `ebitda` are reported for each FY. Additionally FY2025 needs `ebitda_margin` and `sales_per_labor_headcount` computed at the region level (aggregate revenue ÷ aggregate metric sum).

`region_reconciliation_variance` should always be `0.0` — regional totals are the direct sum of branch-level data.

### 6. Branch Rankings

**Sales Growth Rank Descending:** compute `revenue_growth_pct` for every branch, sort descending (highest = rank 1), report the target branch's rank.

**Top ARPU Branch:** compute ARPU for every branch, pick the branch with the highest value.

**Region EBITDA Rank Descending:** compute FY2025 EBITDA for each branch in the target region, sort descending, report the target branch's rank (1 = highest EBITDA in region).

**Top/Bottom EBITDA Branch in Region:** the branch with highest and lowest FY2025 EBITDA in the region.

### 7. Compensation — Current Year Summary

For each employee in the target ensemble, per quarter:

```
Base                = weeks_in_quarter × minimum_weekly_scale

Title Premium       = weeks_in_quarter × minimum_weekly_scale × title_premium_pct[title]
                      SKIP if combined_overscale_includes_title is true
                      SKIP if title is null/None

Seniority           = weeks_in_quarter × seniority_weekly_amount
                      Find the band where years_of_service is between
                      min_years and max_years (max_years may be null = no upper bound)

Overscale           = weeks_in_quarter × overscale_weekly
```

Quarter total for an employee = Base + Title Premium + Seniority + Overscale.
Quarter total for the ensemble = sum of all employee quarter totals.
Annual total = sum(Q1 + Q2 + Q3 + Q4).

Annual pay type totals = sum of each pay type component across all employees and all quarters.

**largest_pay_type:** the pay type with the highest annual total (enum string, not the dollar amount).

**roster_count:** count of employees in the ensemble roster.

**combined_overscale_employee_count:** count of employees where `combined_overscale_includes_title` is true.

**partial_quarter_employee_count:** count of employees where any quarter has `weeks < standard_quarter_weeks[that_quarter]`. The standard is from the rate book's `quarter_weeks`.

**pay_types:** ordered list matching the rate book's `pay_types` array.

### 8. Compensation — Forecast (Current, Year+1, Year+2)

**Current year:** same as current year summary (Section 7).

**Year+1:** apply the scenario's `year_plus_1` growth multipliers to the rate book base values, then add 1 year to each employee's `years_of_service` before looking up seniority bands. Keep the roster structure identical.

```
Year+1 MWS          = current MWS × (1 + mws_growth)
Year+1 seniority    = current seniority_weekly_amount × (1 + seniority_growth)
Year+1 overscale    = employee.overscale_weekly × (1 + overscale_growth)
Year+1 title pct    = title_premium_pct × title_pct_multiplier
Year+1 yos          = employee.years_of_service + 1
```

Then recompute per-employee quarterly totals using Year+1 parameters. Annual total is the sum.

**Year+2:** apply `year_plus_2` growths on top of Year+1 values, add 2 years total to `years_of_service`.

**Growth Rates (between scenarios):**

```
year_plus_1_vs_current = (Y1_total − current_total) / current_total
year_plus_2_vs_year_plus_1 = (Y2_total − Y1_total) / Y1_total
```

**year_plus_2_pay_type_totals:** the breakdown by pay type for Year+2 only (same structure as annual_pay_type_totals but for the forecast year).

**year_plus_2_quarter_totals:** quarterly totals for Year+2 only (Q1–Q4).

**largest_growth_pay_type:** the pay type with the largest absolute dollar increase from current to Year+2 (current pay_type_total → year_plus_2 pay_type_total). Return the enum string.

**combined_overscale_employee_count** and **partial_quarter_employee_count:** use current roster data (same as the current year task).

### 9. Payroll — Weekly Package

For each musician, for each assigned service:

```
Base Service Pay:
  - Performance / Audit: service_rates[service_type] per service
  - Sound Check: service_rates[service_type] per service
  - Rehearsal: service_rates["Rehearsal"] × max(duration_hours, 3.0)
               (3-hour minimum call applies)

Premium multipliers (applied to Base Service Pay, additive):
  - principal_or_lead: 0.15  if principal=true or lead=true
  - concertmaster:    0.20  if the musician is designated concertmaster (check roster title or role)
  - electronic:       0.25  if electronic=true
  - quartet:          0.15  if quartet=true
  - first_double:     0.25  if doubles ≥ 1
  - additional_double:0.10  per each double beyond the first (i.e. (doubles-1) × 0.10)

Premiums = Base Service Pay × Σ(applicable premium pcts)

Vacation = 0.04 × (Base Service Pay + Premiums)  if vacation_eligible=true

Weekly Guarantee Adjustment:
  If substitute=false AND Base Service Pay < weekly_guarantee:
    guarantee_adjustment = weekly_guarantee − Base Service Pay
  Otherwise: 0

Substitute Adjustment:
  For substitute=true: substitute earns Base Service Pay + Premiums,
  but substitute_adjustment is the amount the regular guarantee would have
  been (i.e. weekly_guarantee − Base Service Pay if Base Service Pay < guarantee,
  else 0). This is a separate category.
```

Musician total = sum of all categories for that musician.

**Service Counts:** map each distinct `service_type` from the schedule to its count of occurrences. Use the schedule's own `service_type` strings.

**Conflict Flags** (check ALL services in the schedule, not just assigned ones):

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any Rehearsal with `start_time` earlier than `conflict_thresholds.rehearsal_earliest_start` ("09:00") |
| `REHEARSAL_LATE_END` | Any Rehearsal with `end_time` later than `conflict_thresholds.rehearsal_latest_end` ("18:30") |
| `SERVICE_OVER_TIME_LIMIT` | Any service where `duration_hours > service_time_limits[service_type]` |
| `SOUND_CHECK_DURATION_MISMATCH` | A "1hr Sound Check" with duration ≠ 1.0 hours, or a "2hr Sound Check" with duration ≠ 2.0 hours |

Conflicts are flagged against the schedule globally (not per-musician, not just assigned services).

**Top Paid Musician:** the musician with the highest `total` pay. If tie, use the lower `musician_id`.

### 10. Substitute Payroll Details

Substitutes (`substitute=true`):
- Get base service pay + premiums (same rates as regular players)
- Do NOT get vacation pay
- Do NOT get guarantee adjustments
- Do get a `substitute_adjustment` (the amount they would have received as a guarantee adjustment if they were regular — computed as `max(0, weekly_guarantee − base_service_pay)`)

Non-substitutes (`substitute=false`):
- Get base service pay + premiums + vacation (if eligible) + guarantee_adjustment (if applicable)
- Get a `guarantee_adjustment` equal to `max(0, weekly_guarantee − base_service_pay)`

---

## Output Conventions

### Rounding
- **Currency values:** round to 2 decimal places
- **Percent and ratio values:** round to 4 decimal places
- Use standard `round()` (round half to even / banker's rounding)

### Ordering
- **Lists of branch IDs:** ascending string sort (e.g. `["BR-004","BR-005","BR-006"]`)
- **per_musician:** ascending by `musician_id`
- **conflict_flags:** alphabetical sort
- **pay_types:** the order from the compensation rate book's `pay_types` array
- All lists use ascending stable identifiers unless a rank order is explicitly requested

### Field Naming
- JSON keys are always snake_case as shown in answer templates
- `null` is never used for numeric fields — use `0` or `0.0` instead
- Empty lists use `[]`, not `null`

### Common Pitfalls
1. **Period convention is dynamic:** always read `/api/finance/period-map` to determine which periods belong to which FY. Do not assume M13 always equals FY2025.
2. **ARPU and sales_per_labor_headcount use summed counts, not averages:** sum the count metric across all 12 periods in the FY, then divide.
3. **Forecast seniority:** add years of service BEFORE looking up the seniority band. Year+1 adds 1, Year+2 adds 2. Crossing a band boundary can cause disproportionate growth.
4. **combined_overscale_includes_title:** when true, skip the separate title premium. The overscale amount already bundles it.
5. **Rehearsal minimum:** rehearsal pay is per-hour with a 3-hour minimum per rehearsal service, not per day.
6. **Premiums are additive:** a musician can have principal, doubles, electronic, and quartet all at once. Each applicable premium pct is added together before multiplying base pay.
7. **Vacation base:** vacation is 4% of (base service pay + all premiums), not just base pay.
8. **Conflict flags are schedule-level, not musician-level:** check every service in the schedule, even if no musician is assigned to it.
9. **Substitute adjustment is a positive category total:** it represents pay the substitute actually receives.
10. **Region reconciliation variance is always 0.0:** the data is internally consistent; simple summation of branch data yields the regional totals.
