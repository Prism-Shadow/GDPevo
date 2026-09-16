# Finance Reporting

## Inputs

- `/api/manifest`
- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

## Period map

- `M1` to `M12` => `FY2024`
- `M13` to `M24` => `FY2025`

## Account categories

- `revenue`: `product_revenue`, `service_revenue`
- `cogs`: `direct_materials_cogs`, `direct_labor_cogs`
- `sga`: `sales_sga`, `admin_sga`, `occupancy_sga`
- `allocations`: `shared_service_allocations`
- `operating`: `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`

## Branch close package

For the target branch:

- Build the `M24` income statement from the current-month values.
- `gross_margin = revenue - cogs`
- `ebitda = gross_margin - sga - allocations`
- `mom_revenue_variance.amount = M24 revenue - M23 revenue`
- `mom_revenue_variance.pct = amount / M23 revenue`
- Build `FY2025` from `M13` to `M24` and `FY2024` from `M1` to `M12`.
- `sales_per_labor_headcount = FY2025 revenue / FY2025 labor_headcount`
- `arpu = FY2025 revenue / FY2025 active_customers`

For branch rankings:

- Rank branches by FY2025 revenue growth pct descending.
- Use the rank-1 branch for `top_sales_growth_branch_id`.
- Use the highest FY2025 ARPU branch for `top_arpu_branch_id`.

## Regional view

- Use the branch metadata to get `region_id`.
- Use all branch IDs in that region, sorted ascending, for `branch_ids`.
- Sum FY2025 EBITDA across member branches for `fy2025_ebitda`.
- Rank that region EBITDA against all regions, descending, for `ebitda_rank_desc`.
- Set `region_reconciliation_variance = region FY2025 EBITDA - sum(branch FY2025 EBITDA)`.
