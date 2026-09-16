# Finance Domain

## Period mapping

The period map endpoint provides a mapping from period labels M1..M24 to fiscal years:
- **M1..M12** = FY2024
- **M13..M24** = FY2025

Each period is one month. The `period_convention` output requires four fields: `M1_to_M12`, `M13_to_M24`, `current_month`, and `prior_month`. The fiscal year strings use the format `"FY2024"`, `"FY2025"`.

## Income statement structure

The income statement follows the standard structure:

- **Revenue** = sum of `product_revenue` + `service_revenue` for the period(s) of interest
- **COGS** = sum of `direct_materials_cogs` + `direct_labor_cogs`
- **Gross Margin** = Revenue - COGS
- **SG&A** = sum of `sales_sga` + `admin_sga` + `occupancy_sga`
- **Allocations** = `shared_service_allocations`
- **EBITDA** = Gross Margin - SG&A - Allocations

The records endpoint contains one entry per account per branch. To compute any P&L metric:
1. Filter records to the target branch_id (or region's set of branch_ids)
2. For each record, extract the value for the target period(s)
3. Sum values across accounts belonging to the same category

## Monthly vs fiscal-year aggregation

When asked for a **single-month** income statement (e.g., M24), collect the M24 values from every account record for the target branch.

When asked for a **full fiscal year**, sum all 12 months within the target year:
- FY2024: sum M1 through M12
- FY2025: sum M13 through M24

For `period_convention`, map the requested close_period and prior_period labels to their fiscal year using the period map.

## MoM revenue variance

For `mom_revenue_variance`, compare the target branch's revenue in the close period vs the prior period:
- `amount` = close_period revenue - prior_period revenue (currency, 2 decimals)
- `pct` = amount / prior_period revenue (decimal, 4 decimals)

## EBITDA margin

`ebitda_margin` = EBITDA / Revenue, rounded to 4 decimal places.

## ARPU (Average Revenue Per User)

`arpu` = Revenue / `active_customers` for the same fiscal year scope. For a full fiscal year, sum active_customers across all 12 months first, then divide.

## Sales per labor headcount

`sales_per_labor_headcount` = Revenue / sum of `labor_headcount` across all months in the fiscal year.

## Regional aggregation

When the task asks for a region view:
1. Find all branch_ids belonging to the target region from the branches endpoint
2. Sum each P&L line item across all those branch_ids
3. Sort branch_ids ascending when listing them

## EBITDA ranking

To rank branches by EBITDA within a region or across all branches:
1. Compute FY2025 EBITDA (or the requested year) for every branch
2. Sort descending by EBITDA value
3. The top EBITDA branch has rank 1, the bottom has the highest rank
4. For branch-level rankings within a region, compute the rank of the target branch among its regional peers

## Sales growth ranking

Sales growth = (FY2025 revenue - FY2024 revenue) / FY2024 revenue for each branch. Rank descending: the branch with highest growth gets rank 1.

To find the top sales growth branch across all branches, compute growth for every branch and pick the one with the highest growth rate.

To find the top ARPU branch, compute FY2025 ARPU for every branch and pick the one with the highest value.

## Region reconciliation variance

`region_reconciliation_variance` is the difference between the sum of branch-level EBITDA values and the region-level EBITDA computed from aggregated records. It should be 0.0 when the aggregation matches, or the specific difference otherwise. Compute it as: sum of every branch's EBITDA minus the EBITDA from aggregating records at the region level. If these are identical, the variance is 0.00.

## Operating metric formulas

- **Revenue** = product_revenue + service_revenue
- **COGS** = direct_materials_cogs + direct_labor_cogs
- **Gross Margin** = Revenue - COGS
- **SG&A** = sales_sga + admin_sga + occupancy_sga
- **EBITDA** = Gross Margin - SG&A - shared_service_allocations
- **EBITDA margin** = EBITDA / Revenue
- **ARPU** = Revenue / sum of active_customers for the same periods
- **Sales per labor headcount** = Revenue / sum of labor_headcount for the same periods
- **Revenue growth** = (current - prior) / prior

Always use the records endpoint data for these computations. Do not use hardcoded or cached values.
