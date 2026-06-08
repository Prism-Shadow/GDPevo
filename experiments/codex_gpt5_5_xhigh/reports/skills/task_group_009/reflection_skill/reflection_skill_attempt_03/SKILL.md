---
name: crescent-finance-ops
description: Solve Crescent Finance Ops reporting tasks using the provided payloads and allowed local API endpoints. Use for branch or regional financial close packages, current-year ensemble compensation summaries, board compensation forecasts, and production payroll reviews that require JSON answers matching an answer_template.json.
---

# Crescent Finance Ops

## Required Workflow

1. Read only the task input payloads: `environment_access.json`, `request_memo.json`, and `answer_template.json`.
2. Use `environment_access.base_url` and only endpoints listed in `available_endpoints`.
3. Filter by IDs from `request_memo`; do not infer target entities from names or notes.
4. Build the JSON object from `answer_template.required_top_level_keys` and field descriptions.
5. Round only after aggregation:
   - Currency: 2 decimals.
   - Percent, margin, and growth ratios: 4 decimals.
   - Emit JSON numbers, not formatted strings.
6. Reconcile totals before finalizing:
   - Finance EBITDA equals `revenue - cogs - sga - allocations`.
   - Compensation annual total equals sum of quarter totals and pay-type totals.
   - Payroll weekly total equals sum of category totals and per-musician totals.

## Finance Close And Regional Reporting

Use `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.

Derive periods from `/api/finance/period-map`; in this environment `M1`-`M12` map to FY2024 and `M13`-`M24` map to FY2025, but always trust the map. For any branch set and period set:

```text
revenue = sum records where account.category == "revenue"
cogs = sum records where account.category == "cogs"
gross_margin = revenue - cogs
sga = sum records where account.category == "sga"
allocations = sum records where account.category == "allocations"
ebitda = gross_margin - sga - allocations
```

Use account categories, not display names. Treat expense values as positive amounts to subtract. For a monthly income statement, use one period such as `["M24"]`. For a fiscal-year view, use every period whose `fiscal_year` matches the requested year.

Calculate ratios as:

```text
mom_revenue_variance.amount = current_period_revenue - prior_period_revenue
mom_revenue_variance.pct = amount / prior_period_revenue
revenue_growth_pct = (current_fy_revenue - prior_fy_revenue) / prior_fy_revenue
ebitda_growth_pct = (current_fy_ebitda - prior_fy_ebitda) / prior_fy_ebitda
ebitda_margin = ebitda / revenue
arpu = fy_revenue / sum(active_customers across the same FY periods)
sales_per_labor_headcount = fy_revenue / sum(labor_headcount across the same FY periods)
```

For branch and regional context:

- Get a target branch's region from `/api/finance/branches`; get a regional branch set by matching `region_id`.
- Sort branch ID lists ascending.
- Rank regions by FY2025 EBITDA descending; break ties by stable ID ascending.
- Rank branch sales growth by FY2025-vs-FY2024 revenue growth descending; break ties by branch ID.
- Select top ARPU branch using FY2025 ARPU as defined above.
- Select top and bottom regional EBITDA branches by FY2025 EBITDA.
- Set `region_reconciliation_variance` to the difference between regional aggregate EBITDA and the sum of included branch EBITDAs; it should be zero after using the same records.

## Compensation Summaries

Use `/api/compensation/rate-book`, `/api/compensation/rosters`, and, for forecasts, `/api/compensation/scenarios`.

Filter roster rows by `ensemble_id`. Preserve `rate_book.pay_types` order in output. Count:

```text
roster_count = number of rows for the ensemble
combined_overscale_employee_count = count rows where combined_overscale_includes_title is true
partial_quarter_employee_count = count rows where any weeks_by_quarter differs from rate_book.quarter_weeks
```

For each employee, calculate weekly components:

```text
Minimum Weekly Scale = rate_book.minimum_weekly_scale
Titled Position Premium = Minimum Weekly Scale * title_premium_pct[title]
Seniority = seniority_weekly band amount for years_of_service
Overscale = overscale_weekly
```

If `combined_overscale_includes_title` is true, set Titled Position Premium to zero; do not add a separate title premium. Use each row's `weeks_by_quarter`; do not assume 13 weeks for partial-quarter employees. For each quarter, multiply every weekly component by that employee's weeks in that quarter, then aggregate by quarter and pay type.

Set `largest_pay_type` to the annual pay type with the largest dollar total.

### Forecast Scenarios

For current totals, use current-year compensation rules. For Year + 1 and Year + 2:

- Add one year of service for Year + 1 and two years for Year + 2 before choosing the seniority band.
- Compound scenario growths through the horizon:
  - Year + 1 uses `scenario.year_plus_1`.
  - Year + 2 applies Year + 1 factors and then `scenario.year_plus_2` factors.
- Apply `mws_growth` to Minimum Weekly Scale.
- Apply `seniority_growth` to the selected seniority band amount.
- Apply `overscale_growth` to `overscale_weekly`.
- Apply `title_pct_multiplier` to the title premium percentage, using the grown Minimum Weekly Scale.

Calculate annual growth rates from annual totals:

```text
year_plus_1_vs_current = (year_plus_1 - current) / current
year_plus_2_vs_year_plus_1 = (year_plus_2 - year_plus_1) / year_plus_1
```

For `largest_growth_pay_type`, compare each pay type's percentage growth from current to Year + 2. Do not choose by largest absolute dollar increase.

## Payroll Reviews

Use `/api/payroll/rate-book` and `/api/payroll/productions`. Filter by `production_id`.

Count `service_counts` directly from `schedule.service_type` display labels, such as `Performance`, `Audit`, `Rehearsal`, and `1hr Sound Check`. Do not normalize these keys.

For each assigned service:

- `Performance`, `Audit`, and sound-check types pay the per-service rate.
- `Rehearsal` pays `Rehearsal` hourly rate times `max(duration_hours, 3)`.
- Store base service pay in payroll categories `performance`, `audit`, `rehearsal`, or `sound_check`.

For a substitute row (`substitute: true`), apply the local substitute rule before premiums:

```text
substitute_adjustment = 2 * service_rates["Performance"]
add substitute_adjustment to the musician's performance base category
also report substitute_adjustment as its own category
use the adjusted base when calculating premium and doubles
do not apply vacation or weekly guarantee to substitutes
```

For non-substitutes, calculate percentage add-ons on base service pay:

```text
premium = base * (
  electronic ? premium_pct.electronic : 0
  + (principal or lead ? premium_pct.principal_or_lead : 0)
  + (quartet ? premium_pct.quartet : 0)
  + (concertmaster ? premium_pct.concertmaster : 0)
)
doubles = base * (0.25 for the first double + 0.10 for each additional double)
vacation = 0.04 * (base + premium + doubles), only when vacation_eligible
guarantee_adjustment = weekly_guarantee - base, only for non-substitutes when base < weekly_guarantee
```

Include only nonzero categories in each `per_musician` object. Sort `per_musician` by `musician_id`. Set `top_paid_musician_id` by total descending, with `musician_id` as the tie-breaker.

Detect conflict flags from the schedule and sort them alphabetically:

- `REHEARSAL_EARLY_START`: rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: a sound-check duration differs from its named time limit.

## Common Pitfalls

- Use summed annual operating counts for ARPU and sales-per-labor, not average monthly counts.
- Keep Finance Ops service-count keys as schedule labels; payroll category keys are the normalized lowercase fields from the template.
- Substitute payroll adjustments affect premium and doubles calculations and can change the top-paid musician.
- Forecast `largest_growth_pay_type` is based on percentage growth, not absolute dollars.
- Apply stable sorting whenever a template mentions ranks or ordered lists.
