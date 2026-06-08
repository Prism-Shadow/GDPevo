---
name: reflection-skill
description: Use to solve Crescent Finance Ops reporting tasks that ask for JSON outputs from the local Finance Ops API, including branch close packages, regional management reports, current-year compensation summaries, compensation forecasts, and weekly payroll/CBA reviews. Trigger when input payloads provide Finance Ops base_url/endpoints and answer_template schemas for task_group_009 style finance, compensation, or payroll calculations.
---

# Crescent Finance Ops Reporting

## Ground Rules

Read only the task `input/` payloads first: `prompt.txt`, `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`. Use the `base_url` and only the endpoints listed in `environment_access.json`. Do not use answer files, notes, evaluator files, or test output material while solving a task.

Return exactly one JSON object matching the template keys and field names. Use JSON numbers for currency, percentages, ratios, and counts. Round currency to 2 decimals and percent/ratio fields to 4 decimals. Prefer decimal arithmetic or integer cents because binary floats can move `.005` ties by a cent.

Sort stable-ID lists ascending unless a field explicitly asks for a descending rank. For ties in rankings, break by ascending stable ID or by the rate-book pay type order.

## API Workflow

Fetch the listed endpoints once and build lookups:

- Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
- Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters`, and `/api/compensation/scenarios` when a forecast scenario is requested
- Payroll: `/api/payroll/rate-book`, `/api/payroll/productions`

Always reconcile request IDs and target IDs from `request_memo.json`, not from memo prose. Treat memo notes as context only; compute from active API data.

## Finance Close And Regional Reports

Use `/api/finance/period-map` to map periods to fiscal years. In the observed data, `M1` through `M12` are FY2024 and `M13` through `M24` are FY2025, but still derive this from the period map.

Aggregate finance records by `account.category`:

- `revenue` = sum all revenue accounts
- `cogs` = sum all COGS accounts
- `gross_margin` = `revenue - cogs`
- `sga` = sum all SG&A accounts
- `allocations` = sum all allocation accounts
- `ebitda` = `revenue - cogs - sga - allocations`

Treat expense records as positive amounts to subtract. For a monthly income statement, sum only the requested branch and period. For annual views, sum all periods in the requested fiscal year.

Compute variances and ratios:

- Month-over-month revenue variance amount = current period revenue minus prior period revenue.
- Month-over-month revenue variance percent = amount divided by prior period revenue.
- Revenue growth percent = `(current FY revenue - prior FY revenue) / prior FY revenue`.
- EBITDA growth percent = `(current FY EBITDA - prior FY EBITDA) / prior FY EBITDA`.
- EBITDA margin = FY EBITDA divided by FY revenue.
- ARPU = FY revenue divided by summed FY `active_customers`.
- Sales per labor headcount = FY revenue divided by summed FY `labor_headcount`.

For region context, get region membership from `/api/finance/branches` and sort branch IDs ascending. Region totals are the sum of member branch records for the requested fiscal year. Region EBITDA rank is across all regions by FY EBITDA descending. Branch-level top/bottom EBITDA fields rank branches inside the target region by FY EBITDA.

For branch rankings, rank all branches by FY revenue growth descending for sales growth. Rank all branches by FY ARPU descending for top ARPU.

`region_reconciliation_variance` is the rounded difference between the region EBITDA aggregation and the sum of its member branch EBITDAs; with branch-level records only this should normally be `0.0`.

## Compensation Current-Year Summaries

Use rate-book `pay_types` order in output. Filter `/api/compensation/rosters` to the requested `ensemble_id`.

For each employee and quarter, use the employee's `weeks_by_quarter`; do not assume 13 weeks:

- Minimum Weekly Scale = `minimum_weekly_scale * weeks`.
- Titled Position Premium = `minimum_weekly_scale * title_premium_pct[title] * weeks`.
- Seniority = seniority band weekly amount for `years_of_service` times `weeks`.
- Overscale = `overscale_weekly * weeks`.

If `combined_overscale_includes_title` is true, set Titled Position Premium to zero for that employee; the title premium is already embedded in overscale. Count those employees in `combined_overscale_employee_count`.

Count `partial_quarter_employee_count` as employees whose `weeks_by_quarter` differs from the rate-book `quarter_weeks` in at least one quarter. Sum pay by quarter and by pay type. `largest_pay_type` is the annual pay type with the largest dollar total.

## Compensation Forecasts

Use the same employee formulas, with scenario adjustments:

- Current = current rate-book values and current service years.
- Year + 1 = add one year of service before choosing seniority band; apply the scenario's Year + 1 growth factors.
- Year + 2 = add two years of service; apply Year + 2 growth sequentially after Year + 1 growth.

Apply growth by component:

- Minimum Weekly Scale rate multiplies by `1 + mws_growth`.
- Seniority weekly band amounts multiply by cumulative `1 + seniority_growth`; choose the band after adding forecast service years.
- Overscale weekly amounts multiply by cumulative `1 + overscale_growth`.
- Title premium percent multiplies by cumulative `title_pct_multiplier`.

Compute annual totals and growth rates from unrounded annual totals, then round the reported values. Year + 2 quarter and pay-type detail comes from the Year + 2 adjusted rates.

For `largest_growth_pay_type`, use the largest relative growth rate from current annual pay-type total to Year + 2 annual pay-type total, not the largest absolute dollar increase. This catches seniority-band movement that can have the highest percentage growth even when Minimum Weekly Scale has the largest dollar delta.

## Weekly Payroll Reviews

Use the production `schedule` for service counts and conflict checks. `service_counts` uses the original schedule `service_type` labels exactly, such as `Performance`, `Audit`, `Rehearsal`, and `1hr Sound Check`; do not normalize those keys.

For each roster musician, calculate assigned service pay from `assigned_service_ids`:

- Performance, Audit, and Sound Check services are flat per-service rates from the payroll rate book.
- Rehearsal is hourly at the rehearsal rate with a 3-hour minimum call: `rate * max(duration_hours, 3)`.
- Place base service pay into category keys `performance`, `audit`, `rehearsal`, and `sound_check`.

Substitute handling is special. If `substitute` is true, add `2 * service_rates["Performance"]` as a substitute adjustment. Include that same amount in the musician's `performance` base before computing premiums and doubles, and also report it as a separate `substitute_adjustment` category. Do not apply the weekly guarantee to substitutes.

Compute premiums after base service pay:

- Add percentage premiums on base service pay for any true flags such as `principal`, `lead`, `quartet`, `electronic`, and `concertmaster` when present.
- Doubles are separate from `premium`: first extra instrument = 25% of base service pay, each additional extra instrument = 10% of base service pay.
- Vacation = vacation percent times `(base service pay + premium + doubles)` when `vacation_eligible` is true.
- Guarantee adjustment = `weekly_guarantee - base service pay` only for non-substitute regular players whose base service pay is below the guarantee.

Sum nonzero categories for each musician total, round reported per-musician category values to 2 decimals, and order `per_musician` by `musician_id`. Category totals are the sum of musician categories. Include `substitute_adjustment` when nonzero. `weekly_total` is the sum of rounded or unrounded musician totals rounded to 2 decimals; both should reconcile if category rounding is consistent.

Conflict flags are a sorted list:

- `REHEARSAL_EARLY_START` when a rehearsal starts before the rate-book earliest start.
- `REHEARSAL_LATE_END` when a rehearsal ends after the rate-book latest end.
- `SERVICE_OVER_TIME_LIMIT` when a service duration exceeds its service-type limit.
- `SOUND_CHECK_DURATION_MISMATCH` when a sound-check duration does not match the hours encoded in its label.

`top_paid_musician_id` is the musician with the highest final total after substitute, premium, doubles, vacation, and guarantee adjustments.

## Final Checks

Before returning JSON, verify every required top-level key exists, no train answer values are being used as a lookup table, all requested target IDs match the memo, sorted fields are sorted, and all currency/ratio rounding matches the template description.
