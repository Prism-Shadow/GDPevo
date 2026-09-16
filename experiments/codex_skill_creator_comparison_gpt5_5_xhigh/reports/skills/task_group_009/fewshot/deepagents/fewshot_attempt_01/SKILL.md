---
name: crescent-finance-ops
description: Produce Crescent Finance Ops JSON reports from task payloads and the Finance Ops API. Use for Crescent Arts Collective branch close reports, regional finance views, current-year compensation summaries, compensation forecasts, and touring production weekly payroll reviews that provide request_memo.json, answer_template.json, and environment_access.json payloads.
---

# Crescent Finance Ops

Use this skill when a task asks for one JSON object from the Crescent Finance Ops API. Always read the task prompt, `payloads/request_memo.json`, `payloads/answer_template.json`, and `payloads/environment_access.json`. Resolve the actual API base URL from the task environment, then compute from live API data rather than draft memo notes or background workbook claims.

## Fast Path

Run the bundled solver when the payload shape matches one of the supported report families:

```bash
python3 skill/scripts/crescent_finance_ops.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --memo payloads/request_memo.json \
  --template payloads/answer_template.json
```

If `payloads/environment_access.json` contains a real URL, `--env-file payloads/environment_access.json` may be used instead of `--base-url`. The script uses only Python standard library modules and emits the final JSON to stdout.

Supported memo families:

- `target_branch_id`: branch close management report.
- `target_region_id`: regional finance management view.
- `ensemble_id` without `scenario_id`: current-year compensation summary.
- `ensemble_id` with `scenario_id`: compensation forecast.
- `production_id`: weekly payroll review.

## Finance Rules

Fetch `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, and `/api/finance/records`.

Use account categories from `/api/finance/accounts`:

- `revenue`: sum revenue accounts.
- `cogs`: sum COGS accounts.
- `gross_margin = revenue - cogs`.
- `sga`: sum SG&A accounts.
- `allocations`: sum allocation accounts.
- `ebitda = gross_margin - sga - allocations`.
- `ebitda_margin = ebitda / revenue`.
- `arpu = revenue / active_customers`.
- `sales_per_labor_headcount = revenue / labor_headcount`.

Period labels map to fiscal years through `/api/finance/period-map`; do not infer the year from the numeric label without the map. For growth percentages, use `(current - prior) / prior`.

For branch close reports:

- Use the memo close period and prior period for the monthly income statement and month-over-month revenue variance.
- Use the fiscal year containing the close period as the current fiscal year and the preceding mapped fiscal year as the comparison year.
- Rank branch sales growth across all branches by current-fiscal-year revenue growth descending; break ties by ascending branch ID.
- Rank regional EBITDA context across all regions by current-fiscal-year EBITDA descending; break ties by ascending region ID.
- Choose top ARPU across all branches using current-fiscal-year revenue divided by active customers.

For regional reports:

- Select branches whose `region_id` matches `target_region_id`; return branch IDs sorted ascending.
- Aggregate region values by summing all selected branch records for each requested fiscal year.
- Choose top and bottom EBITDA branch IDs within the region from current-fiscal-year EBITDA; break ties by ascending branch ID.
- Compute reconciliation variance as aggregate regional EBITDA less the sum of branch-level EBITDA for the same region and year.

## Compensation Rules

Fetch `/api/compensation/rate-book`, `/api/compensation/rosters`, and `/api/compensation/scenarios` when forecasting.

For each roster row and quarter:

- Minimum Weekly Scale = `minimum_weekly_scale * weeks_by_quarter[quarter]`.
- Titled Position Premium = minimum weekly scale times the title premium percent times weeks, unless `combined_overscale_includes_title` is true.
- Seniority = seniority band weekly amount for `years_of_service` times weeks.
- Overscale = `overscale_weekly * weeks`.
- Use roster `weeks_by_quarter`; do not replace partial-quarter rows with fixed 13-week quarters.

Current-year summaries return the rate-book `current_year`, the rate-book pay type order, roster count, quarter totals, annual pay-type totals, annual total, largest annual pay type, count of combined-overscale rows, and count of partial-quarter rows.

Forecasts:

- `current` uses the current-year formula.
- `year_plus_1` adds one service year before selecting seniority bands and applies the scenario's Year + 1 growth factors.
- `year_plus_2` adds two service years before selecting seniority bands and compounds Year + 1 and Year + 2 growth factors for minimum scale, seniority weekly amounts, and overscale.
- Use the forecast year's own `title_pct_multiplier` against the base title premium percent, applied to the adjusted minimum weekly scale.
- `largest_growth_pay_type` is the pay type with the largest percentage growth from current to Year + 2; break ties by the rate-book pay type order.

## Payroll Rules

Fetch `/api/payroll/rate-book` and `/api/payroll/productions`.

For each assigned service:

- Performance, audit, and sound-check rates are per service.
- Rehearsal pay is hourly using `max(duration_hours, 3)` times the rehearsal rate.
- Classify sound-check services under `sound_check`.

For each musician:

- If `substitute` is true, add `2 * service_rates["Performance"]` to the performance base and also report that amount as `substitute_adjustment`.
- Premium percentage is the sum of applicable role premiums: one `principal_or_lead` premium if either flag is true, plus `quartet`, `electronic`, and `concertmaster` if present.
- Doubles premium is `first_double` for the first extra instrument plus `additional_double` for each additional extra instrument.
- Apply role premiums and doubles to base service pay after any substitute performance adjustment.
- Vacation is the vacation percentage times base service pay plus role premiums plus doubles, only when `vacation_eligible` is true.
- Guarantee adjustment is `weekly_guarantee - base_service_pay` when positive for non-substitute musicians.

Conflict flags:

- `REHEARSAL_EARLY_START`: any rehearsal starts before the threshold.
- `REHEARSAL_LATE_END`: any rehearsal ends after the threshold.
- `SERVICE_OVER_TIME_LIMIT`: any service duration exceeds its limit.
- `SOUND_CHECK_DURATION_MISMATCH`: any sound-check duration differs from its listed service limit.

Return `per_musician` sorted by `musician_id`, with only nonzero category names in each musician's `categories`. Sort `conflict_flags` alphabetically.

## Output Discipline

Round currency to 2 decimals and percentages/ratios to 4 decimals only at final output. Keep intermediate calculations unrounded. Return a single JSON object and no explanatory prose.
