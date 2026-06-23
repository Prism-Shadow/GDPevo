# Crescent Finance Ops SOP

Use this skill for Crescent Finance Ops tasks that require calculations from the remote API. Work from the live service, not local task folders.

## Data Access

- Base URL: `<environment_base_url>`.
- Start with `/api/manifest` to confirm available endpoints and public entity IDs.
- Main endpoints:
  - `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
  - `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
  - `/api/payroll/rate-book`, `/api/payroll/productions`
- Load JSON with a real parser. Prefer a short Python/JS script or `jq`; avoid manual copying from pretty-printed output.
- Join by stable IDs (`branch_id`, `region_id`, `account`, `ensemble_id`, `production_id`, `service_id`). Names are useful for display but IDs are safer for filtering.

## Finance Tasks

- Finance records are normalized: one row per `branch_id` plus `account`, with a `values` object keyed by periods `M1` through `M24`.
- Use `/api/finance/period-map` for month/year mapping. In the staged data, fiscal 2024 is `M1`-`M12`; fiscal 2025 is `M13`-`M24`.
- Account conventions:
  - Revenue = `product_revenue + service_revenue`.
  - COGS = `direct_materials_cogs + direct_labor_cogs`.
  - Gross profit = revenue - COGS.
  - SG&A = `sales_sga + admin_sga + occupancy_sga`.
  - Operating income, when allocations are in scope, = revenue - COGS - SG&A - `shared_service_allocations`.
- Common ratios:
  - Gross margin = gross profit / revenue.
  - Operating margin = operating income / revenue.
  - Revenue per order/unit/customer = revenue divided by the requested operating metric.
  - YoY change = current comparable period - prior comparable period; YoY percent = change / prior comparable period.
- For multi-month questions, sum currency and transactional counts such as `orders` and `revenue_units`. For point-in-time metrics such as `active_customers`, headcount, and backlog, use the prompt wording: average for “average/monthly” language, ending value for “ending,” and sum only if explicitly requested.
- Aggregate region or company totals by summing branch rows after filtering the right account(s) and periods.

## Compensation Tasks

- Use `/api/compensation/rate-book` for all rates and business rules; do not hard-code beyond what it returns.
- Current weekly components:
  - Minimum weekly scale = `minimum_weekly_scale`.
  - Seniority = the `seniority_weekly` band containing `years_of_service`.
  - Title premium = minimum weekly scale times `title_premium_pct[title]`, if the employee has a title.
  - Overscale = `overscale_weekly`.
- If `combined_overscale_includes_title` is true, do not add title premium separately for that employee. Still include the overscale amount.
- Quarter/year totals must use each employee's `weeks_by_quarter`, especially partial-quarter rows. Do not assume every employee has 13 weeks in every quarter or 52 weeks annually.
- Employee pay for a quarter = applicable weekly total times that employee's weeks in that quarter. Annual pay = sum across the four quarters.
- Forecast scenarios:
  - Use `/api/compensation/scenarios`.
  - For Year + 1, add one year of service before choosing the seniority band; for Year + 2, add two years.
  - Apply scenario growth rates to minimum weekly scale, seniority amounts, and overscale. Treat Year + 2 as the second forecast year; compound from Year + 1 unless the prompt/template explicitly states a non-compounded method.
  - Apply `title_pct_multiplier` to the title percentage before multiplying by the forecast minimum weekly scale.
- Keep separate subtotals when requested: minimum scale, seniority, title premium, overscale, and total compensation.

## Payroll Tasks

- Use `/api/payroll/rate-book` for service rates, premium percentages, weekly guarantee, conflict thresholds, and time limits.
- Production objects contain `schedule` services and a musician `roster`. Only pay a musician for `assigned_service_ids`.
- Base service pay:
  - `Rehearsal` is hourly at the rehearsal rate with a 3-hour minimum call: `max(duration_hours, 3) * rate`.
  - `Performance`, `Audit`, `1hr Sound Check`, and `2hr Sound Check` are per-service rates, not hourly, even when scheduled duration differs from the label.
- Premiums are applied to base service pay before vacation:
  - Doubles = 25% for the first extra instrument plus 10% for each additional extra instrument.
  - Electronic = 25%.
  - Principal or lead = 15%; apply once if either/both flags are true.
  - Quartet = 15%.
  - Concertmaster = 20% only when a production/prompt exposes that role.
- Vacation = 4% of base service pay plus premiums when `vacation_eligible` is true; otherwise zero.
- Weekly guarantee adjustment applies only to guaranteed regular players when base service pay is below `weekly_guarantee`. In these datasets, substitutes are not regular guaranteed players unless a prompt says otherwise. Keep the guarantee adjustment as a separate line item.
- Schedule checks:
  - Flag services whose `duration_hours` exceeds `service_time_limits[service_type]`.
  - Flag rehearsals starting before `rehearsal_earliest_start` or ending after `rehearsal_latest_end`.
  - For musician-level conflicts, compare assigned service intervals on the same date; overlapping intervals are conflicts for that musician.

## Rounding And Output

- Sum with full precision, then round final numeric outputs.
- Currency: two decimals. Percentages: follow the prompt; otherwise use percent values rounded to two decimals. Counts: integers unless an average is requested.
- Preserve requested output field names and ordering from the prompt/template. If JSON is requested, return plain JSON-compatible values, not formatted currency strings, unless the template shows strings.
- Include IDs with names when ambiguity is possible, especially for branches, ensembles, productions, musicians, and services.
- Sanity-check totals by recomputing from components and verifying no missing periods, employees, or assigned services.

## Common Pitfalls

- Do not use account display names as keys; use `account` codes.
- Do not compare `M1` to `M13` by string sorting alone; use the period map for chronological logic.
- Do not double-count title premium when overscale already includes title.
- Do not use fixed 13-week quarters for partial-quarter compensation rows.
- Do not apply payroll premiums to vacation or guarantee adjustments unless the prompt explicitly changes the rule.
- Do not pay unassigned services to a musician just because they are in the production schedule.
