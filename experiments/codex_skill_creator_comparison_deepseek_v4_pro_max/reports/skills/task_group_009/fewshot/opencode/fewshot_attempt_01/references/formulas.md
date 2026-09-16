# Formulas

Every derived metric must use these exact formulas. Values come from the Finance Ops API data.

## Finance Formulas

### Income Statement (per branch, per period)

For a given branch and period (or set of periods):

| Metric | Formula |
|--------|---------|
| revenue | `product_revenue + service_revenue` |
| cogs | `direct_materials_cogs + direct_labor_cogs` |
| gross_margin | `revenue - cogs` |
| sga | `sales_sga + admin_sga + occupancy_sga` |
| allocations | `shared_service_allocations` (single account) |
| ebitda | `revenue - cogs - sga - allocations` |
| ebitda_margin | `ebitda / revenue` |
| arpu | `revenue / active_customers` |
| sales_per_labor_headcount | `revenue / labor_headcount` |

### Growth Rates

| Metric | Formula |
|--------|---------|
| revenue_growth_pct | `(fy2025_revenue - fy2024_revenue) / fy2024_revenue` |
| ebitda_growth_pct | `(fy2025_ebitda - fy2024_ebitda) / fy2024_ebitda` |
| mom_revenue_variance amount | `current_month_revenue - prior_month_revenue` |
| mom_revenue_variance pct | `variance_amount / prior_month_revenue` |

### Period Mapping

M1 through M12 belong to FY2024. M13 through M24 belong to FY2025. The current FY is FY2025 in this system.

When the request memo specifies a close_period (e.g., M24), the prior_period is directly given (e.g., M23). Use these period labels as keys into the records values dict.

### Branch Rankings

To rank branches within a region or across the system:

1. **Sales growth rank (descending)**: Compute `(fy2025_revenue - fy2024_revenue) / fy2024_revenue` for every branch. Rank from highest (1) to lowest. The rank is the 1-based position.
2. **Top ARPU branch**: Compute `fy2025_revenue / fy2025_active_customers` for every branch. The branch with the highest ARPU is top_arpu_branch_id.
3. **Top sales growth branch**: The branch with the highest revenue growth rate.

### Region Aggregation

When computing region-level totals, sum across all branches in the region. For reconciliation_variance, the expected pattern is `sum of branch_ebitda - region_ebitda` from the region context; when internal numbers are consistent this is 0.00.

### Operating Dashboard Ratios

Return only the specific ratios requested in the management_focus or reporting_focus fields. Compute them exactly as defined above.

## Compensation Formulas

### Per-Employee Quarterly Pay

For each employee in the roster:

```
mws_pay = minimum_weekly_scale * weeks_in_quarter  [from roster weeks_by_quarter, NOT rate-book default]
```

```
title_pay = mws_pay * title_premium_pct[title]  [only if title is not null AND combined_overscale_includes_title is false]
```

```
seniority_pay = seniority_weekly_amount * weeks_in_quarter  [look up band from years_of_service]
```

```
overscale_pay = overscale_weekly * weeks_in_quarter  [overscale_weekly from roster]
```

```
total_quarterly = mws_pay + title_pay + seniority_pay + overscale_pay
```

### Annual Aggregation

Sum each pay type across all employees and all quarters:

```
annual_pay_type_totals[pay_type] = sum of that pay type across all employees and quarters
annual_total = sum of all pay_type_totals
quarter_totals[Q] = sum of all employees' total_quarterly for quarter Q
```

### Roster Counts

- **roster_count**: Total number of employees in the ensemble roster
- **combined_overscale_employee_count**: Count of employees with `combined_overscale_includes_title = true`
- **partial_quarter_employee_count**: Count of employees whose `notes` contains "Partial-quarter" or who have any quarter weeks != 13
- **largest_pay_type**: The pay type with the highest annual_pay_type_totals value

### Forecast Formulas

For a given scenario, compute future years using growth rates from the scenario data:

```
future_mws = current_mws * (1 + mws_growth)
future_overscale_weekly = current_overscale_weekly * (1 + overscale_growth)
future_seniority_bands = current_seniority_amount * (1 + seniority_growth)
future_title_pct = current_title_pct * title_pct_multiplier
```

For forecast years, add years to employee's years_of_service before looking up seniority bands: `+1` for year_plus_1, `+2` for year_plus_2.

Then compute per-employee pay using the same quarterly formulas above, substituting the projected rates. Aggregate to annual totals and growth rates:

```
growth_year_plus_1 = (year_plus_1_total - current_total) / current_total
growth_year_plus_2 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```

### Growth Driver Classification

The `largest_growth_pay_type` is the pay type that has the largest absolute dollar increase from current to year_plus_2. Compare `year_plus_2_pay_type_totals[pt] - current_pay_type_totals[pt]` for each pay type.

## Payroll Formulas

### Service Classification

Map each schedule service to its rate:
- **Performance**: `service_rates["Performance"]` per service
- **Audit**: `service_rates["Audit"]` per service
- **Rehearsal**: `service_rates["Rehearsal"]` per hour, with **3-hour minimum call**. Pay = rate * max(3, duration_hours)
- **1hr Sound Check**: `service_rates["1hr Sound Check"]` per service
- **2hr Sound Check**: `service_rates["2hr Sound Check"]` per service

### Per-Musician Calculation

For each musician, for each of their assigned services:

1. **Base service pay**: The service rate as classified above.
2. **Premium pay**: Sum of applicable premiums applied to base service pay (not the rate):
   - **principal_or_lead** (15%): if musician.principal or musician.lead is true
   - **concertmaster** (20%): if title is Concertmaster (use the rate book's premium_pct map; check the musician's title field from rate-book integration)
   - **quartet** (15%): if musician.quartet is true
   - **electronic** (25%): if musician.electronic is true
   - **first_double** (25%): if musician.doubles >= 1
   - **additional_double** (10%): for each double beyond the first (max(0, doubles - 1) * 0.10)

   Note: Premiums apply per-service. For Performance, Audit, and Sound Check services, premiums are applied to the per-service rate. For Rehearsal, premiums apply to the rehearsal pay calculated from hours.

3. **Service total** = base_service_pay + premium_pay

4. **Vacation**: If vacation_eligible, vacation_pay = 4% of (base_service_pay + premium_pay) for that service.

5. Sum all service totals and vacation across the musician's assigned services.

### Category Totals

Sum per-service-type pay across all musicians:
- **performance**: sum of all Performance service base + premiums (not including vacation)
- **audit**: sum of all Audit service base + premiums
- **rehearsal**: sum of all Rehearsal service base + premiums
- **sound_check**: sum of all sound check service base + premiums (both 1hr and 2hr combined)
- **premium**: sum of all premium pay across all services
- **doubles**: sum of all first_double and additional_double premiums across all services
- **vacation**: sum of all vacation pay across all musicians
- **guarantee_adjustment**: for non-substitute musicians only, weekly_guarantee - (base service pay before premiums). If positive, add this amount. If negative, the field is 0.
- **substitute_adjustment**: Deduct substitute service pay from regular musicians. Only applies to actual substitute musicians.

### Substitute Adjustment Logic

The substitute musician's pay contributions are transferred from regular musicians:
1. Identify the substitute musician(s) (substitute: true)
2. Calculate the substitute's base + premium + vacation pay for their assigned services
3. This amount is **deducted** from non-substitute musicians (split or allocated)
4. The substitute's own pay appears as a positive substitute_adjustment line item

In practice: the substitute musicians service pay (base + premiums + vacation for their assigned services) is removed from regular musicians totals and shown under substitute_adjustment for the substitute.

### Conflict Flag Detection

Check the schedule against rate-book conflict_thresholds:

- **REHEARSAL_EARLY_START**: Any rehearsal service with start_time before `rehearsal_earliest_start` ("09:00")
- **REHEARSAL_LATE_END**: Any rehearsal service with end_time after `rehearsal_latest_end` ("18:30")
- **SERVICE_OVER_TIME_LIMIT**: Any service whose duration_hours exceeds its service_time_limit
- **SOUND_CHECK_DURATION_MISMATCH**: A 1hr Sound Check with duration > 1.0 hours, or a 2hr Sound Check with duration > 2.0 hours

Sort conflict flags alphabetically in the output.

### Service Counts

Count distinct services by type across the schedule:
- Count of "Performance" services
- Count of "Audit" services
- Count of "Rehearsal" services
- Count of "1hr Sound Check" services
- Count of "2hr Sound Check" services

Use the schedule array, not musician assignments. A service that no musician is assigned to still counts.

### Top Paid Musician

The musician_id with the highest total pay (after all adjustments). If tie, pick the first alphabetically by musician_id.

### Weekly Total

Sum of all per_musician totals (which already include all adjustments).
