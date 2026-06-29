---
name: task-group-009-fewshot-attempt-02
description: SOP for Crescent Finance Ops benchmark tasks involving branch and regional management reporting, current-year and forecast compensation summaries, and weekly payroll reviews using local Finance Ops API payloads. Use when Codex must read task prompt/payloads, fetch allowed Finance Ops API endpoints, compute finance, compensation, payroll, ranking, rounding, and answer-template JSON fields, while avoiding restricted test outputs, notes, evaluator files, and environment internals.
---

# Crescent Finance Ops SOP

Use this skill to solve Crescent Finance Ops tasks from the task prompt and payloads only. Return exactly one JSON object matching `payloads/answer_template.json`; do not include Markdown, explanations, or extra keys.

## Guardrails

- Read only the task prompt and its `payloads/*.json`, plus endpoints listed in `payloads/environment_access.json`.
- Do not read `env/`, any `test_tasks/*/output`, `test_tasks/*/notes`, `test_tasks/*/eval`, or evaluator code/configs.
- Prefer active API data over memo notes or stale workbook language.
- Fetch only the base URL and endpoint paths supplied by the payload. Treat endpoint responses as source of truth.
- Preserve answer-template key names, pay-type strings, service-type strings, and enum values exactly.

## Standard Workflow

1. Read `prompt.txt`, `payloads/request_memo.json`, `payloads/environment_access.json`, and `payloads/answer_template.json`.
2. Fetch each listed API endpoint from `base_url`.
3. Filter by the target identifier in the memo, such as `branch_id`, `region_id`, `ensemble_id`, `scenario_id`, or `production_id`.
4. Compute all requested fields from raw source data with full precision.
5. Round only final output values: currency to 2 decimals, percentages/ratios/growth rates to 4 decimals.
6. Sort lists by stable ID ascending unless the template or field name asks for a rank/top/bottom order.
7. Verify totals reconcile: annual totals equal pay-type/quarter totals within final rounding; payroll weekly total equals the sum of per-musician totals from unrounded components.

## API Surfaces

- Finance endpoints:
  - `/api/finance/branches`: branch metadata with `branch_id`, `branch_name`, `region_id`, `region_name`.
  - `/api/finance/period-map`: maps period labels such as `M1` to fiscal years/months.
  - `/api/finance/accounts`: account metadata with `account`, `category`, `metric_type`.
  - `/api/finance/records`: branch/account records with a `values` object keyed by period.
- Compensation endpoints:
  - `/api/compensation/rate-book`: current year, weekly scale, quarter weeks, pay-type order, title premiums, seniority bands, and business rules.
  - `/api/compensation/rosters`: employee roster rows with ensemble, title, service years, quarter weeks, overscale, and combined overscale flags.
  - `/api/compensation/scenarios`: forecast assumptions by `scenario_id`.
- Payroll endpoints:
  - `/api/payroll/rate-book`: service rates, premium percentages, time limits, vacation rate, weekly guarantee, and conflict thresholds.
  - `/api/payroll/productions`: production schedules and musician rosters.

## Finance Reporting

Aggregate finance records by account category and period:

- `revenue`: sum accounts where category is `revenue`.
- `cogs`: sum category `cogs`.
- `gross_margin`: `revenue - cogs`.
- `sga`: sum category `sga`.
- `allocations`: sum category `allocations`.
- `ebitda`: `revenue - cogs - sga - allocations`.
- `ebitda_margin`: `ebitda / revenue`.
- `arpu`: annual revenue divided by annual summed `active_customers`.
- `sales_per_labor_headcount`: annual revenue divided by annual summed `labor_headcount`.

Use the period map to identify fiscal years. In the observed convention, `M1`-`M12` are the prior fiscal year and `M13`-`M24` are the current fiscal year, but always rely on `/api/finance/period-map` rather than hard-coding.

For branch close packages:

- Monthly income statement fields use only the requested close period.
- Month-over-month revenue variance is `current_period_revenue - prior_period_revenue`; percent is `amount / prior_period_revenue`.
- Fiscal-year comparison uses all periods for each fiscal year, not just the close period.
- `revenue_growth_pct` is `(current_year_revenue - prior_year_revenue) / prior_year_revenue`.
- `ebitda_growth_pct` is `(current_year_ebitda - prior_year_ebitda) / prior_year_ebitda`.
- Region context `branch_ids` are all branches in the target branch's region, sorted ascending.
- Region context `fy####_ebitda` is the region sum for that fiscal year.
- Region context EBITDA rank is the target region's rank among all regions by fiscal-year EBITDA descending.
- Branch sales-growth ranking ranks all branches by fiscal-year revenue growth descending; rank 1 is highest.
- Top ARPU branch uses fiscal-year ARPU across all branches.

For regional packages:

- Filter branches by `target_region_id`; output `branch_ids` ascending.
- Fiscal-year regional metrics are sums across included branches and all periods in the requested fiscal year.
- Branch-level EBITDA top/bottom uses fiscal-year EBITDA within the region; break ties by `branch_id` ascending.
- `region_reconciliation_variance` should be the difference between EBITDA recomputed from regional component sums and the sum of branch-level EBITDA. This should normally round to `0.00`; investigate if not.

## Compensation Current-Year Summary

Filter `/api/compensation/rosters` by `ensemble_id`. Use `rate-book.pay_types` order for pay-type lists and output objects.

For each employee and quarter:

- Use that employee's `weeks_by_quarter`; do not assume every employee has the default 13 weeks.
- Minimum Weekly Scale = `minimum_weekly_scale * quarter_weeks`.
- Titled Position Premium = `minimum_weekly_scale * title_premium_pct[title] * quarter_weeks` when `title` is present and `combined_overscale_includes_title` is false.
- Seniority = `seniority_weekly_band(years_of_service) * quarter_weeks`.
- Overscale = `overscale_weekly * quarter_weeks`.
- Employee quarter total is the sum of all applicable pay types.

Counts and classifications:

- `roster_count`: number of roster rows for the ensemble.
- `combined_overscale_employee_count`: count rows where `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count`: count rows where any `weeks_by_quarter[Q]` differs from the rate-book quarter weeks for that quarter.
- `largest_pay_type`: pay type with the largest annual total; break ties by rate-book pay-type order.

## Compensation Forecast

For forecast tasks, compute the current year first using the current-year compensation rules. Then apply the selected scenario cumulatively:

- Year + 1 minimum scale = current scale * `(1 + year_plus_1.mws_growth)`.
- Year + 2 minimum scale = Year + 1 scale * `(1 + year_plus_2.mws_growth)`.
- Year + 1 overscale = current overscale * `(1 + year_plus_1.overscale_growth)`.
- Year + 2 overscale = Year + 1 overscale * `(1 + year_plus_2.overscale_growth)`.
- Year + 1 seniority weekly amount = seniority band after adding 1 service year, then multiply by `(1 + year_plus_1.seniority_growth)`.
- Year + 2 seniority weekly amount = seniority band after adding 2 service years, then multiply by both seniority growth factors cumulatively.
- Title premium uses the forecast year's scaled minimum weekly scale, the base title percentage, and cumulative `title_pct_multiplier` values.
- If `combined_overscale_includes_title` is true, do not add a separate title premium in any forecast year.

Growth rates:

- `year_plus_1_vs_current`: `(annual_total_y1 - annual_total_current) / annual_total_current`.
- `year_plus_2_vs_year_plus_1`: `(annual_total_y2 - annual_total_y1) / annual_total_y1`.
- `largest_growth_pay_type`: pay type with the largest relative growth from current to Year + 2, not the largest absolute dollar increase. Break ties by pay-type order.

## Payroll Review

Filter `/api/payroll/productions` by `production_id`. Build a schedule map by `service_id`, then calculate each musician from their `assigned_service_ids`.

Base service pay:

- Performance, Audit, and Sound Check are paid per service at `service_rates[service_type]`.
- Rehearsal is hourly at `service_rates["Rehearsal"] * max(duration_hours, 3)`.
- Category names in output are lowercase: `performance`, `audit`, `rehearsal`, `sound_check`.
- Count services by exact `service_type` for `service_counts`.

Premiums and adjustments:

- Premium base is the musician's base service pay before guarantee and vacation. Include any substitute performance uplift in this base.
- Principal or lead premium: apply `principal_or_lead` once when `principal` or `lead` is true.
- Quartet premium: apply when `quartet` is true.
- Electronic premium: apply when `electronic` is true.
- Concertmaster premium: apply only if the roster exposes a concertmaster flag/role.
- Doubles premium: if `doubles > 0`, apply `first_double` for the first extra instrument plus `additional_double * (doubles - 1)`.
- `premium` category is the sum of non-doubles premiums; `doubles` is separate.
- Weekly guarantee applies only to non-substitute regular players when base service pay is below `weekly_guarantee`; output `guarantee_adjustment = weekly_guarantee - base_service_pay`.
- Substitute players receive a performance-equivalent adjustment when their performance service count is below the substitute minimum observed in the rate package. When no explicit field is present, use a six-Performance-service minimum: `substitute_adjustment = max(0, 6 - performance_count) * service_rates["Performance"]`. Add this uplift to `performance` and also report it under `substitute_adjustment`.
- Vacation applies only when `vacation_eligible` is true: `vacation = vacation_pct * (base_service_pay + premium + doubles)`. Exclude guarantee adjustment from the vacation base.

Conflict flags:

- `REHEARSAL_EARLY_START`: any rehearsal starts before `conflict_thresholds.rehearsal_earliest_start`.
- `REHEARSAL_LATE_END`: any rehearsal ends after `conflict_thresholds.rehearsal_latest_end`.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds `service_time_limits[service_type]`.
- `SOUND_CHECK_DURATION_MISMATCH`: any sound-check duration differs from its named/service time limit.
- Sort `conflict_flags` alphabetically.

Payroll output:

- Omit zero categories from each `per_musician[].categories`.
- Sort `per_musician` by `musician_id` ascending.
- `top_paid_musician_id` is the musician with highest unrounded total; break ties by `musician_id` ascending.
- Compute `category_totals` from unrounded musician category components, then round final values.
- Compute `weekly_total` from unrounded per-musician totals, then round.

## Rounding And JSON Pitfalls

- Currency: round to 2 decimals with decimal half-up behavior for `.005` cases.
- Percent, ratio, and growth fields: round to 4 decimals, represented as decimal rates such as `0.1234`, not `"12.34%"`.
- Do not round each row before summing; carry full precision until final object fields.
- Include optional payroll categories such as `substitute_adjustment` only when applicable unless the template explicitly requires them.
- Keep JSON numbers numeric, not strings.
- Keep answer-template object structure; do not add audit trails, formulas, comments, or source citations to the final JSON.
