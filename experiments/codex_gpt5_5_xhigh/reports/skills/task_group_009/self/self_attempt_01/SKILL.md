---
name: crescent-finance-ops
description: Use this skill for Crescent Arts Collective Finance Ops API tasks involving branch close packages, regional finance views, compensation summaries or forecasts, and weekly payroll reviews. It gives the endpoint workflow, finance/compensation/payroll formulas, rounding, ordering, and JSON answer conventions needed to produce management-reporting outputs from the remote Crescent Finance Ops API.
---

# Crescent Finance Ops SOP

## Operating Pattern

Read the task prompt, `payloads/request_memo.json`, `payloads/answer_template.json`, and `payloads/environment_access.json`. Use the `base_url` from the payload, not a local environment. Return exactly one JSON object matching the answer template keys and field names.

Fetch the API data fresh from the remote service. `/api/manifest` is useful for confirming available entities, but calculations usually need the listed business endpoints:

- Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
- Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
- Payroll: `/api/payroll/rate-book`, `/api/payroll/productions`

The endpoints return full datasets; filter client-side by the branch, region, ensemble, scenario, or production in the request memo. Prefer a small script or structured calculations over hand arithmetic. Keep full precision internally and round only final JSON values.

## JSON Conventions

- Currency fields: JSON numbers rounded to 2 decimals.
- Percent, growth, margin, and ratio fields: decimal rates rounded to 4 decimals, not strings and not multiplied by 100.
- Counts and ranks: integers.
- Lists of stable IDs: ascending unless the template asks for rank order.
- Ranked facts: descending metric order for fields ending in `_rank_desc` or top/bottom metrics. Break ties by stable ID ascending.
- Per-entity arrays: sort by stable ID, for example `musician_id`.
- Include all required template keys. For optional or "when applicable" fields, include them only when supported by the data/rules or when the template explicitly requires a zero.

## Finance Branch and Regional Reporting

Use `period-map` to map periods to fiscal years. In the current data, `M1`-`M12` are FY2024 and `M13`-`M24` are FY2025, but still read the endpoint rather than hard-coding.

For each branch-period:

- `revenue` = `product_revenue` + `service_revenue`
- `cogs` = `direct_materials_cogs` + `direct_labor_cogs`
- `gross_margin` = `revenue` - `cogs`
- `sga` = `sales_sga` + `admin_sga` + `occupancy_sga`
- `allocations` = `shared_service_allocations`
- `ebitda` = `gross_margin` - `sga` - `allocations`

For fiscal-year views, sum the relevant monthly periods from `period-map`. For ratios:

- `ebitda_margin` = annual EBITDA / annual revenue
- `arpu` = annual revenue / summed `active_customers`
- `sales_per_labor_headcount` = annual revenue / summed `labor_headcount`
- Growth or variance percent = `(current - prior) / prior`

For region views, get branch membership from `/api/finance/branches`, aggregate branch results for the requested region, and keep `branch_ids` ascending. If a reconciliation variance is requested and the API has no independent region ledger, reconcile the region to the branch rollup and return `0.00`.

Be careful with similarly named ranking fields. A regional context object generally asks for the target branch's region and region-level facts, while separate branch ranking objects ask for branch-level comparisons across the relevant population. Use the template field names to decide the population.

## Compensation Current-Year Summaries

Use `/api/compensation/rate-book` for pay types, current year, weekly minimum scale, title premiums, seniority bands, quarter weeks, and business rules. Filter `/api/compensation/rosters` by `ensemble_id`.

For each roster employee and quarter, use that employee's `weeks_by_quarter`; do not assume 13 weeks when the roster lists partial service.

Pay-type formulas:

- `Minimum Weekly Scale` = `minimum_weekly_scale * weeks`
- `Titled Position Premium` = `minimum_weekly_scale * title_premium_pct[title] * weeks`
- `Seniority` = seniority weekly band for `years_of_service` times `weeks`
- `Overscale` = `overscale_weekly * weeks`

If `combined_overscale_includes_title` is true, do not add a separate titled position premium for that employee; the overscale amount already includes that title treatment. Still include the employee's `overscale_weekly` in Overscale.

Roster review counts:

- `roster_count`: employees in the filtered ensemble.
- `combined_overscale_employee_count`: employees with `combined_overscale_includes_title: true`.
- `partial_quarter_employee_count`: employees where any `weeks_by_quarter[Q]` differs from `rate_book.quarter_weeks[Q]`.

Use `rate_book.pay_types` as the ordered `pay_types` list. `quarter_totals` sum all pay types by quarter; `annual_pay_type_totals` sum each pay type over all quarters; `annual_total` is the sum of annual pay types. `largest_pay_type` is the pay type with the largest annual total, using pay-type order to break ties.

## Compensation Forecasts

Forecast tasks use the same roster and rate book plus `/api/compensation/scenarios`. Compute `current`, `year_plus_1`, and `year_plus_2` annual totals.

For forecast years:

- Add 1 year of service for `year_plus_1` and 2 years for `year_plus_2` before choosing the seniority band.
- Apply scenario growth to the corresponding pay type. Treat `year_plus_2` growth as the next year's growth after `year_plus_1`, so minimum scale, seniority amounts, and overscale rates compound sequentially from current to Year + 1 to Year + 2 unless the prompt states otherwise.
- Apply the scenario year's `title_pct_multiplier` to the base title premium percentage for that forecast year. The titled premium is based on that forecast year's minimum scale. Continue suppressing separate title premium when `combined_overscale_includes_title` is true.

`growth_rates.year_plus_1_vs_current` = `(year_plus_1 annual total - current annual total) / current annual total`. `growth_rates.year_plus_2_vs_year_plus_1` = `(year_plus_2 annual total - year_plus_1 annual total) / year_plus_1 annual total`.

When `year_plus_2_quarter_totals` or `year_plus_2_pay_type_totals` are requested, report the Year + 2 detail, not current-year detail. `largest_growth_pay_type` should compare Year + 2 pay-type total to current pay-type total and choose the largest absolute growth unless the prompt explicitly asks for percentage growth.

## Payroll Reviews

Use `/api/payroll/rate-book` for rates, premiums, time limits, conflict thresholds, vacation rate, and weekly guarantee. Filter `/api/payroll/productions` by `production_id`.

Service base pay:

- Rehearsal is hourly at the rehearsal rate with a 3-hour minimum call: `max(duration_hours, 3) * rehearsal_rate`.
- Performance, Audit, and Sound Check are per-service rates from `service_rates`, using the schedule's `service_type`.

For each musician, sum base service pay for assigned services only. Category base pay maps to `performance`, `audit`, `rehearsal`, and `sound_check`.

Premiums and adjustments:

- Principal or lead premium: apply `principal_or_lead` once when either flag is true.
- Quartet and electronic premiums are separate additive premiums when flagged.
- Doubles premium: `first_double` for the first extra instrument plus `additional_double` for each additional extra instrument, applied to base service pay.
- Put principal/lead, quartet, and electronic amounts in `premium`; put doubles amounts in `doubles`.
- Vacation = vacation percent times base service pay plus premiums, including doubles, only when `vacation_eligible` is true.
- Weekly guarantee adjustment applies only to non-substitute regular players when base service pay is below `weekly_guarantee`; the adjustment is `weekly_guarantee - base_service_pay`. Do not include premiums or vacation in the guarantee test.
- Substitutes do not receive weekly guarantee or vacation unless the rate book/rules explicitly say otherwise. Include `substitute_adjustment` only when an explicit rule or data field supports it.

Conflict flags:

- `REHEARSAL_EARLY_START`: rehearsal starts before `rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: rehearsal ends after `rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: `duration_hours` exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: sound-check duration does not equal the time limit implied by its service type.

Return unique conflict flags sorted alphabetically. `service_counts` counts scheduled services by their API `service_type`. `category_totals` sum all musicians and should reconcile to `weekly_total`. `per_musician` is sorted by `musician_id`; include only nonzero category amounts in each musician's `categories`. `top_paid_musician_id` is the highest total, tie-broken by `musician_id`.

## Final Validation Checklist

Before returning:

- Re-read `answer_template.json` and verify every required top-level key is present.
- Check that all requested IDs match the memo and all lists use the required ordering.
- Confirm totals reconcile: finance statements, compensation annual totals, payroll category totals and musician totals.
- Confirm rounding is final-output only and JSON values are numbers, not formatted currency strings.
- Return only the JSON object, with no prose.
