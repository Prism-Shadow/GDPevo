# Branch close and regional reporting

Use this for monthly branch close packages and regional management views.

## Inputs

- `payloads/environment_access.json`
- `payloads/request_memo.json`
- `payloads/answer_template.json`

## Endpoints

- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

## Data model

- `branches` provides `branch_id`, `branch_name`, and `region_id`.
- `period-map` maps M-periods to fiscal years and month labels. Build the mapping from the data; do not hardcode it.
- `records` is one row per branch/account. Each row has `account`, `branch_id`, `branch_name`, `region_id`, and a `values` map keyed by period.

## Calculations

- Resolve `current_month` and `prior_month` from the memo.
- Compute branch month values by summing the relevant account rows:
  - revenue = `product_revenue` + `service_revenue`
  - cogs = `direct_materials_cogs` + `direct_labor_cogs`
  - gross_margin = revenue - cogs
  - sga = `sales_sga` + `admin_sga` + `occupancy_sga`
  - allocations = `shared_service_allocations`
  - ebitda = gross_margin - sga - allocations
- Use the current-period statement block in the template for the target branch.
- `mom_revenue_variance.amount = current_month_revenue - prior_month_revenue`
- `mom_revenue_variance.pct = amount / prior_month_revenue`
- FY totals use the months for each fiscal year from `period-map`.
- `arpu = revenue / sum(active_customers over the fiscal-year months)`
- `sales_per_labor_headcount = revenue / sum(labor_headcount over the fiscal-year months)`
- `region_context.branch_ids` must be the region's branch ids in ascending order.
- `region_context.fy2025_ebitda` is the sum of FY2025 EBITDA for the region branches.
- `region_context.ebitda_rank_desc` is the target branch's rank within the region by FY2025 EBITDA descending.
- Compute `branch_rankings` across the full branch universe:
  - `sales_growth_rank_desc` = target branch rank by FY2025 revenue growth vs FY2024
  - `top_sales_growth_branch_id` = branch with the highest revenue growth
  - `top_arpu_branch_id` = branch with the highest FY2025 ARPU
- `region_reconciliation_variance` should reconcile the region total against the sum of the same branch-level EBITDA values; it should normally be zero when the data ties out.

## Output discipline

- Keep branch and region ids exact.
- Break ranking ties deterministically by `branch_id`.
- Preserve the template's key order when serializing the final object.
