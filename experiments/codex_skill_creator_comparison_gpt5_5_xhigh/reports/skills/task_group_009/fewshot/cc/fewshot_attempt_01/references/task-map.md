# Task Map

Use this file when the memo and template do not make the report family obvious.

## Quick family match

| Template clues | Family | Main endpoints |
| --- | --- | --- |
| `target_branch_id`, `target_branch_name`, `period_convention`, `m24_income_statement`, `mom_revenue_variance`, `fy2025_vs_fy2024`, `region_context`, `branch_rankings` | Branch close | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| `region_id`, `branch_ids`, `fy2024`, `fy2025`, `revenue_growth_pct`, `top_ebitda_branch_id`, `bottom_ebitda_branch_id`, `region_reconciliation_variance` | Regional management | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| `ensemble_id`, `current_year`, `quarter_totals`, `annual_pay_type_totals`, `annual_total`, `largest_pay_type`, `combined_overscale_employee_count`, `partial_quarter_employee_count` | Current-year compensation summary | `/api/compensation/rate-book`, `/api/compensation/rosters` |
| `production_id`, `service_counts`, `category_totals`, `weekly_total`, `conflict_flags`, `per_musician`, `top_paid_musician_id` | Payroll review | `/api/payroll/rate-book`, `/api/payroll/productions` |
| `scenario_id`, `annual_totals`, `growth_rates`, `year_plus_2_quarter_totals`, `year_plus_2_pay_type_totals`, `largest_growth_pay_type`, `combined_overscale_employee_count`, `partial_quarter_employee_count` | Compensation forecast | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |

## Branch close checklist
- Use the memo's `target_branch_id`, `close_period`, and `prior_period`.
- Resolve the branch name and region from the branches endpoint.
- Use the period map to place periods into the correct fiscal-year bucket.
- Compute current-period income statement totals, prior-period revenue variance, fiscal-year comparisons, regional context, and branch rankings.
- Keep ranking fields consistent with their name. A `*_rank_desc` field should reflect descending rank order.

## Regional management checklist
- Keep `branch_ids` sorted ascending unless the template says otherwise.
- Report both fiscal years exactly as requested.
- Compute EBITDA margin and sales-per-labor-headcount from the live totals, then round to 4 decimals.
- Set `region_reconciliation_variance` from the region totals. If the live data ties out, it should be zero.
- Use the region's branch set to choose top and bottom EBITDA branches. Do not pull in branches outside the region.

## Compensation summary checklist
- Keep `pay_types` in the order returned by the rate book.
- Use roster data to build quarter totals and annual pay-type totals.
- The largest pay type is the one with the highest annual total.
- Count the roster treatment flags requested by the memo and template, including overscale and partial-quarter counts.

## Payroll review checklist
- Use the production schedule and payroll rate book together.
- Sum service counts and category totals from the live production data.
- Order `per_musician` by `musician_id`.
- Sort `conflict_flags` alphabetically.
- Set `top_paid_musician_id` to the musician with the highest total.

## Forecast checklist
- Pull current, year-plus-1, and year-plus-2 totals from the scenario data.
- Compute growth rates from the annual totals, not from individual line items.
- Fill `year_plus_2_quarter_totals` and `year_plus_2_pay_type_totals` directly from the scenario detail.
- Set `largest_growth_pay_type` to the pay type with the biggest increase across the forecast horizon.
- Keep the roster-treatment counts aligned with the same logic used for the current-year compensation summary.
