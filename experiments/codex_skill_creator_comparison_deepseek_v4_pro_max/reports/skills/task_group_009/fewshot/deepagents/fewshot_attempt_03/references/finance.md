## Endpoints

| Endpoint | Description |
|---|---|
| `/api/finance/branches` | All branches with region assignments |
| `/api/finance/period-map` | Period-to-fiscal-year mapping (M1–M12 = FY2024, M13–M24 = FY2025) |
| `/api/finance/accounts` | Chart of accounts with categories and metric types |
| `/api/finance/records` | Time-series values per account per branch per period |

## Account Categories

| Category | Accounts | Metric |
|---|---|---|
| revenue | product_revenue, service_revenue | currency |
| cogs | direct_materials_cogs, direct_labor_cogs | currency |
| sga | sales_sga, admin_sga, occupancy_sga | currency |
| allocations | shared_service_allocations | currency |
| operating | orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog | count |

## Period Convention

Periods M1–M12 map to FY2024. Periods M13–M24 map to FY2025. Each period label
(M1, M2, ...) has `fiscal_year`, `month_name`, `month_number`, and `period`.

## Branch Record Structure

Each record in `/api/finance/records` has:
- `account` — account key
- `branch_id` — target branch
- `branch_name` — display name
- `region_id` — parent region
- `values` — object mapping period labels to numeric values

## Income Statement Computation

For a given branch and period (or set of periods), group record values by
account category:

```
revenue  = sum(product_revenue) + sum(service_revenue)
cogs     = sum(direct_materials_cogs) + sum(direct_labor_cogs)
gross_margin = revenue - cogs
sga      = sum(sales_sga) + sum(admin_sga) + sum(occupancy_sga)
allocations = sum(shared_service_allocations)
ebitda   = gross_margin - sga - allocations
```

Round all currency amounts to 2 decimals.

## Ratio Computations

**EBITDA margin** (for a fiscal year or branch within a fiscal year):
```
ebitda_margin = ebitda / revenue
```

**ARPU** (average revenue per active customer):
```
arpu = total_revenue / sum_of_active_customers_across_periods
```
Sum active_customers across all periods in the fiscal year, then divide total
revenue by that sum.

**Sales per labor headcount**:
```
sales_per_labor_headcount = sum_of_revenue_units / sum_of_labor_headcount
```
Sum both revenue_units and labor_headcount across all periods in the fiscal year.

All ratios rounded to 4 decimals.

## Branch Rankings

To compute sales growth ranking across all branches:
1. For each branch, sum all revenue for FY2024 (M1–M12) and FY2025 (M13–M24).
2. Compute `revenue_growth = (fy2025_revenue - fy2024_revenue) / fy2024_revenue`.
3. Rank descending by growth rate (highest growth = rank 1). Use the same formula
   for `top_sales_growth_branch_id`.

For `top_arpu_branch_id`: compute ARPU for FY2025 for every branch and take the
highest.

## Region Context

For a given branch's region:
1. Find all branches in the same region from `/api/finance/branches`.
2. Compute FY2025 EBITDA for each branch in the region.
3. `fy2025_ebitda` = sum of all branches' FY2025 EBITDA.
4. `ebitda_rank_desc` = rank of the target branch within its region by FY2025
   EBITDA (highest = 1).
5. `branch_ids` = ascending list of branch IDs in the region.

## Regional Reporting

For a target region:
1. Sum all currency accounts across all branches in the region for all periods
   in each fiscal year.
2. Compute `revenue_growth_pct = (fy2025_revenue - fy2024_revenue) / fy2024_revenue`.
3. Rank branches within region by FY2025 EBITDA to get `top_ebitda_branch_id`
   and `bottom_ebitda_branch_id`.
4. `region_reconciliation_variance` is the difference between the region-level
   sum and the sum of individual branch EBITDA values. If computed correctly
   from records, this should be 0.

## MoM Revenue Variance

```
amount = M24_revenue - M23_revenue
pct    = amount / M23_revenue
```

Round amount to 2 decimals, pct to 4 decimals.
