# Finance Domain Rules

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `/api/finance/branches` | All branches with `branch_id`, `branch_name`, `region_id`, `region_name` |
| `/api/finance/period-map` | Every period M1-M24 mapped to `fiscal_year` and `month_name` |
| `/api/finance/accounts` | Account definitions: `account`, `category`, `display_name`, `metric_type` |
| `/api/finance/records` | Per-branch, per-account monthly values keyed by period M1-M24 |

GET all four endpoints once. No filtering parameters, no authentication.

## Period Convention

M1-M12 = FY2024, M13-M24 = FY2025. Use the `/api/finance/period-map` endpoint to confirm this mapping per task rather than hard-coding it.

## Account Categories

Finance records use these accounts. Every account falls into exactly one category.

| Account | Category | Display Name | Metric |
|---------|----------|-------------|--------|
| `product_revenue` | revenue | Product Revenue | currency |
| `service_revenue` | revenue | Service Revenue | currency |
| `direct_materials_cogs` | cogs | Direct Materials COGS | currency |
| `direct_labor_cogs` | cogs | Direct Labor COGS | currency |
| `sales_sga` | sga | Sales SG&A | currency |
| `admin_sga` | sga | Admin SG&A | currency |
| `occupancy_sga` | sga | Occupancy SG&A | currency |
| `shared_service_allocations` | allocations | Shared Service Allocations | currency |
| `orders` | operating | Orders | count |
| `revenue_units` | operating | Revenue Units | count |
| `active_customers` | operating | Active Customers | count |
| `labor_headcount` | operating | Labor Headcount | count |
| `admin_headcount` | operating | Admin Headcount | count |
| `backlog` | operating | Backlog | count |

## Income Statement Rollup (per branch, per period)

```
revenue      = product_revenue + service_revenue
cogs         = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga          = sales_sga + admin_sga + occupancy_sga
allocations  = shared_service_allocations
ebitda       = gross_margin - sga - allocations
```

## Fiscal-Year Aggregation

Sum all monthly values within a fiscal year's period range (M1-M12 for FY2024, M13-M24 for FY2025) for each income-statement line. Then compute ratios:

```
ebitda_margin = fy_ebitda / fy_revenue
arpu          = fy_revenue / fy_revenue_units   (when revenue_units > 0)
sales_per_labor_headcount = fy_revenue / fy_labor_headcount
revenue_growth_pct       = (fy_this - fy_prior) / fy_prior
ebitda_growth_pct        = (fy_this_ebitda - fy_prior_ebitda) / fy_prior_ebitda
```

All ratio values that require revenue_units or labor_headcount use the totals for the same fiscal year.

## Region Context

Filter `/api/finance/branches` by `region_id` to get the region's branch set. Sort branch IDs ascending for the `branch_ids` list. Sum each branch's FY totals to get region totals.

Rank region EBITDA among all regions: sum every region's FY2025 EBITDA, sort descending, and assign rank 1 to the highest. Use desc ranking (1 = best).

## Branch Rankings (enterprise-wide)

- **Sales growth rank (desc):** compute `(FY2025 revenue / FY2024 revenue) - 1` for every branch, sort descending, assign rank 1 to highest growth.
- **Top ARPU branch:** compute FY2025 ARPU for each branch, pick the branch with maximum value.

## Reconciliation Variance

For a region: sum the individual branch FY2025 EBITDA values from the records, compare against the region total computed by summing all branch line items. The reconciliation variance is the computed region EBITDA minus the sum of individual branch EBITDA. A correct dataset produces 0.00.

## Rounding

- Currency values: round to 2 decimal places.
- Ratios and percentages (pct, margin): round to 4 decimal places.
- Integer ranks: use whole numbers (int), no decimals.
