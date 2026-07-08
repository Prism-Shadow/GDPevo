---
name: crescent-finance-ops-reporting
description: Use this skill for Crescent Arts Collective Finance Ops API tasks that ask for branch close reporting, regional management views, compensation summaries or forecasts, or weekly payroll reviews. It helps convert request memos, answer templates, and the remote Crescent Finance Ops API into one exact JSON answer with the correct formulas, ordering, rounding, and roster/rate-book edge-case handling.
---

# Crescent Finance Ops Reporting

## Core workflow

1. Read the task prompt, `payloads/request_memo.json`, `payloads/answer_template.json`, and `payloads/environment_access.json`.
2. Treat `answer_template.json` as the contract: return exactly one JSON object with the requested keys, field names, list ordering, and numeric rounding. Do not add narrative fields just because the memo asks for background context unless the template includes them.
3. Use the `base_url` from environment access and query the listed remote API endpoints directly. Do not assume a local task server or local cached data.
4. Inspect each endpoint's actual shape before calculating. Some endpoints return arrays, while rate books and scenarios are keyed objects.
5. Use a small script or structured calculation rather than manual arithmetic. Terminal output can truncate large `/records` responses, so fetch into memory before aggregating.
6. Return JSON numbers, not formatted strings. Currency fields round to 2 decimals. Percent, ratio, margin, and growth fields round to 4 decimals as decimal rates, e.g. `0.1234`, not `12.34`.

## General conventions

- Stable IDs are meaningful. Sort ID lists ascending unless the template says a rank or top/bottom fact requires another order.
- For descending ranks, sort by the target metric high-to-low and break ties by stable ID ascending.
- Growth and variance percentages use `(current - comparison) / comparison`.
- If a denominator is zero, do not guess; use `null` only if the template permits it, otherwise recheck the data and memo.
- Names in memos may mention draft workbooks or notes. Reconcile against active API data, not memo prose.
- For objects with fixed category keys, include all template-required categories with `0` when absent. For per-person category maps that explicitly ask for nonzero categories, omit zero categories.

## Finance branch and regional reports

Use:

- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

Build fiscal-year period sets from `/period-map` instead of hardcoding. In the staged data, `M1`-`M12` map to FY2024 and `M13`-`M24` map to FY2025, but future tasks should still read the map.

Account formulas:

- `revenue` = all records whose account category is `revenue`.
- `cogs` = category `cogs`.
- `gross_margin` = `revenue - cogs`.
- `sga` = category `sga`.
- `allocations` = category `allocations`.
- `ebitda` = `gross_margin - sga - allocations`.
- `ebitda_margin` = `ebitda / revenue`.
- `sales_per_labor_headcount` = revenue over the same period set divided by aggregated `labor_headcount`, unless the prompt explicitly asks for average headcount.
- `arpu` = revenue over the same period set divided by `revenue_units`, unless the prompt explicitly defines a different user/customer denominator.

For a close-period income statement, aggregate only the requested period, e.g. `M24`. For current fiscal-year views, aggregate all periods in that fiscal year. For regional reporting, filter branches by `region_id`, then sum branch metrics.

Ranking facts:

- Branch sales or revenue growth ranks compare all branches over the requested fiscal-year pair.
- EBITDA ranks inside regional context usually compare the branches in that target region only.
- `top_*_branch_id` and `bottom_*_branch_id` should be selected after applying the same fiscal-year or period window used for the metric.
- `region_reconciliation_variance` should tie regional totals back to the sum of included branch-level totals; when both are derived from the same records this should round to `0.00`.

Period labels should come from `/period-map` when requested. Include the period code and fiscal year when useful, but preserve any template-provided field names such as `current_month` and `prior_month`.

## Compensation summaries

Use:

- `/api/compensation/rate-book`
- `/api/compensation/rosters`

Filter rosters by `ensemble_id`. Use `rate_book.pay_types` for pay-type ordering and exact labels.

Per employee, per quarter:

1. Use `employee.weeks_by_quarter[quarter]` when present. This matters for partial-quarter players; do not blindly use 13 weeks.
2. `Minimum Weekly Scale` = `minimum_weekly_scale * weeks`.
3. `Titled Position Premium` = `minimum_weekly_scale * title_premium_pct[title] * weeks`, only when the title has a premium and `combined_overscale_includes_title` is false.
4. `Seniority` = seniority band weekly amount for `years_of_service` times weeks. Bands are inclusive of `min_years` and `max_years`; a `null` max means no upper bound.
5. `Overscale` = `overscale_weekly * weeks`.

Then sum by quarter, pay type, and year. `annual_total` is the sum of all pay-type totals and should also equal the sum of quarter totals after rounding tolerance.

Roster treatment counts:

- `roster_count` = number of filtered roster rows.
- `combined_overscale_employee_count` = count of employees where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count` = count of employees with any quarter week count different from `rate_book.quarter_weeks`.

`largest_pay_type` is the pay type with the largest annual total; use rate-book pay-type order to break ties.

## Compensation forecasts

Use:

- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios`

Start with the current-year compensation method above. Select the requested `scenario_id`.

Forecast handling:

- Year + 1 uses one added year of service for seniority-band selection; Year + 2 uses two added years.
- Apply annual growth rates year over year for dollar rates. For example, Year + 2 minimum weekly scale should build on the Year + 1 scaled rate, then apply the Year + 2 `mws_growth`.
- Apply `overscale_growth` to employee overscale weekly amounts and `seniority_growth` to seniority weekly amounts after selecting the aged service band.
- Apply each forecast year's `title_pct_multiplier` to the base title premium percentage for that forecast year.
- Continue to skip separate title premium for employees whose combined overscale includes title.

Forecast `growth_rates` use annual totals:

- `year_plus_1_vs_current` = `(year_plus_1 - current) / current`.
- `year_plus_2_vs_year_plus_1` = `(year_plus_2 - year_plus_1) / year_plus_1`.

For `largest_growth_pay_type`, use the greatest dollar increase from current to Year + 2 unless the memo names a different interval. If the memo asks for a driver explanation but the template only provides the enum field, return only the enum.

## Weekly payroll reviews

Use:

- `/api/payroll/rate-book`
- `/api/payroll/productions`

Select the requested `production_id`. Build a schedule map by `service_id`, then calculate each roster musician from their `assigned_service_ids`.

Service and category calculations:

- `service_counts` counts schedule rows by exact `service_type`.
- Performance and Audit are per-service flat rates from `service_rates`.
- Rehearsal is hourly at the rehearsal rate with a 3-hour minimum call: `max(duration_hours, 3) * rate`.
- Sound checks are per-service flat rates by exact service type, such as `1hr Sound Check` or `2hr Sound Check`, and roll into the `sound_check` category.
- Base service pay is the sum of performance, audit, rehearsal, and sound-check base amounts.
- Role/electronic/quartet premiums are applied to base service pay using `premium_pct`. Apply `principal_or_lead` once if either principal or lead is true. Apply `electronic`, `quartet`, or `concertmaster` only when the roster exposes the corresponding flag or role.
- Doubles are a separate category: 25% of base service pay for the first extra instrument plus 10% for each additional extra instrument.
- Vacation is 4% of base service pay plus premiums, including doubles, when `vacation_eligible` is true.
- Weekly guarantee adjustment applies only to non-substitute regular players when base service pay is below `weekly_guarantee`.
- Do not invent a `substitute_adjustment`; include it only if the rate book, roster, or template makes it applicable. Substitutes do not receive weekly guarantee unless the rate book says otherwise.

Per musician:

- Sum all category amounts to `total`.
- Include only nonzero categories in each musician's `categories` map when the template asks for nonzero categories.
- Sort `per_musician` by `musician_id`.
- `top_paid_musician_id` is the highest total, with `musician_id` ascending as a tie-breaker.

Conflict flags:

- `REHEARSAL_EARLY_START`: rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: duration exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: a sound-check duration does not match the hour count implied by its service type.

Return `conflict_flags` sorted alphabetically.

## Final answer checklist

- The response is a single JSON object with no Markdown fence.
- Top-level keys match `required_top_level_keys`.
- Currency is rounded to 2 decimals; ratios and growth rates to 4 decimals.
- ID lists and per-person lists follow the template's ordering rule.
- Category keys use the template's exact spelling and casing.
- No train-only IDs, memo notes, or explanatory comments are included unless the current task template asks for them.
