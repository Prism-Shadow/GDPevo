# Crescent Finance Ops Playbook

## Input contract

- Use the request memo for scope.
- Use the answer template for required keys, nested shapes, ordering, and rounding.
- Use the environment access payload only to reach the live API.
- Keep full precision while computing. Round only when serializing the final JSON.

## Endpoint map

| Task family | Endpoints |
| --- | --- |
| Branch close / regional reporting | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation summary / forecast | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |
| Payroll review | `/api/payroll/rate-book`, `/api/payroll/productions` |

## Finance reporting

- Use `/api/finance/period-map` to map period labels to fiscal years.
- Aggregate monthly values across the target periods in the memo.
- Use account categories from `/api/finance/accounts` to group values:
  - revenue: `product_revenue`, `service_revenue`
  - cogs: `direct_materials_cogs`, `direct_labor_cogs`
  - sga: `sales_sga`, `admin_sga`, `occupancy_sga`
  - allocations: `shared_service_allocations`
  - operating ratios: `orders`, `revenue_units`, `active_customers`, `labor_headcount`, `admin_headcount`, `backlog`
- Compute:
  - revenue = product revenue + service revenue
  - cogs = direct materials + direct labor
  - gross margin = revenue - cogs
  - sga = sales + admin + occupancy
  - ebitda = gross margin - sga - allocations
  - arpu = revenue / active_customers
  - sales_per_labor_headcount = revenue / labor_headcount
  - growth_pct = `(later - earlier) / earlier`
- For region packages, keep `branch_ids` in ascending branch_id order and treat region reconciliation as the check between the region aggregate and the sum of the included branches.
- Rank branch and region metrics across the full live set unless the memo explicitly limits the scope.

## Compensation reporting

- Keep the pay-type order from the rate book.
- Apply minimum weekly scale, title premium percentages, seniority bands, and overscale weekly values from the live rate book and roster rows.
- Use `weeks_by_quarter` from each roster row. Respect shorter quarters when they appear.
- When `combined_overscale_includes_title` is true, suppress a separate title premium for that employee.
- For Year + 1 and Year + 2 forecasts, add the service-year offset before assigning the seniority band.
- Apply scenario multipliers from the selected forecast case to the appropriate pay components.
- Derive the roster counts from the live roster rows, not from totals:
  - `combined_overscale_employee_count` = rows with `combined_overscale_includes_title = true`
  - `partial_quarter_employee_count` = rows with any quarter below the standard quarter length

## Payroll reporting

- Count `service_counts` from the production schedule's `service_type` values.
- Derive category totals from the schedule and roster together, using the live rate book to interpret pay rules.
- Keep `per_musician` sorted by `musician_id`.
- Include only nonzero category totals inside each musician row.
- Keep `conflict_flags` sorted alphabetically and limited to the template's enum values.
- Set `top_paid_musician_id` to the musician with the highest total. Use stable `musician_id` order to break ties.

## Final checks

- Validate the output object shape against the template before finishing.
- Verify list ordering, numeric rounding, and exact field names.
- If memo notes conflict with live data, trust the live data and the template.
