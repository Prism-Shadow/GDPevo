## Table of Contents

- Endpoints and Schemas
- Account Aggregation Rules
- Income Statement Computation
- MoM Revenue Variance
- Fiscal Year Comparison
- Region Aggregation
- Branch Rankings
- Verification

## Endpoints and Schemas

### GET /api/finance/branches

Returns a list of branch objects:

```
{"branch_id": "BR-NNN", "branch_name": "Branch Name", "region_id": "REG-XXX", "region_name": "Region Name"}
```

Each branch belongs to exactly one region.

### GET /api/finance/period-map

Returns a list of period objects:

```
{"fiscal_year": 2024, "month_name": "Jan", "month_number": 1, "period": "M1"}
```

Period convention: M1--M12 map to FY2024, M13--M24 map to FY2025. Always fetch this endpoint to confirm the convention for the current dataset.

### GET /api/finance/accounts

Returns a list of account objects:

```
{"account": "product_revenue", "category": "revenue", "display_name": "Product Revenue", "metric_type": "currency"}
```

Category mappings:

| Account | Category | Metric Type |
|---|---|---|
| product_revenue | revenue | currency |
| service_revenue | revenue | currency |
| direct_materials_cogs | cogs | currency |
| direct_labor_cogs | cogs | currency |
| sales_sga | sga | currency |
| admin_sga | sga | currency |
| occupancy_sga | sga | currency |
| shared_service_allocations | allocations | currency |
| orders | operating | count |
| revenue_units | operating | count |
| active_customers | operating | count |
| labor_headcount | operating | count |
| admin_headcount | operating | count |

### GET /api/finance/records

Returns a list of record objects, each with per-period values for one account at one branch:

```
{"account": "product_revenue", "branch_id": "BR-NNN", "branch_name": "Branch Name", "region_id": "REG-YYY", "values": {"M1": 118330.31, "M2": 116982.57, ...}}
```

Records cover all 24 periods (M1--M24) for every account at every branch.

## Account Aggregation Rules

- **Revenue** = product_revenue + service_revenue
- **COGS** = direct_materials_cogs + direct_labor_cogs
- **SGA** = sales_sga + admin_sga + occupancy_sga
- **Allocations** = shared_service_allocations
- **Gross Margin** = Revenue - COGS
- **EBITDA** = Gross Margin - SGA - Allocations

For single-period computations, sum the account values for the target period across the relevant accounts for the target branch.

For fiscal-year computations, sum the account values across all 12 periods in the fiscal year, then aggregate accounts as above.

## Income Statement Computation

For a target branch and target period:

1. Identify all records matching `branch_id`.
2. For each record, extract the value for the desired period from `values`.
3. Aggregate values by account category (revenue, cogs, sga, allocations).
4. Compute derived fields (gross_margin, ebitda).
5. Round all currency values to 2 decimal places.

## MoM Revenue Variance

For a target period and its immediate prior period (e.g., M24 and M23):

- `amount` = revenue(current_period) - revenue(prior_period), rounded to 2 decimals
- `pct` = amount / revenue(prior_period), rounded to 4 decimals

Beware: when prior period revenue is zero, pct is undefined; the API data always has positive values.

## Fiscal Year Comparison

To compare FY2025 against FY2024 for a target branch:

1. Sum each account across all 12 periods in each fiscal year.
2. Aggregate accounts into revenue, cogs, gross_margin, sga, allocations, ebitda for each year.
3. Compute derived metrics for FY2025:
   - `ebitda_margin` = ebitda / revenue, rounded to 4 decimals
   - `arpu` = revenue / revenue_units, rounded to 2 decimals (where `revenue_units` is an operating count record)
   - `sales_per_labor_headcount` = revenue / labor_headcount, rounded to 2 decimals
4. Compute growth rates:
   - `revenue_growth_pct` = (fy2025_revenue - fy2024_revenue) / fy2024_revenue, rounded to 4 decimals
   - `ebitda_growth_pct` = (fy2025_ebitda - fy2024_ebitda) / fy2024_ebitda, rounded to 4 decimals

Operating count records (revenue_units, labor_headcount) have numeric values, not currency. Sum them by period the same way, but treat the result as an integer count.

## Region Aggregation

For a target region:

1. Identify all branches where `region_id` matches the target.
2. List `branch_ids` in ascending sort order.
3. Sum each account across all branch records for the fiscal year, then aggregate into category totals.
4. Compute `region_reconciliation_variance`: the absolute difference between the region-level aggregated EBITDA and the sum of each branch's individually-computed EBITDA for the same fiscal year. Round to 2 decimals.

## Branch Rankings

When computing branch rankings across all branches:

- **sales_growth_rank_desc**: Compute revenue_growth_pct (FY2025 vs FY2024) for every branch. Rank from largest (1) to smallest. The target branch's rank is its position.
- **top_sales_growth_branch_id**: The branch with the highest revenue_growth_pct.
- **top_arpu_branch_id**: The branch with the highest ARPU (fy2025_revenue / fy2025_revenue_units), rounded to 2 decimals for ARPU comparison.
- **top_ebitda_branch_id**: The branch in the region with the highest FY2025 EBITDA.
- **bottom_ebitda_branch_id**: The branch in the region with the lowest FY2025 EBITDA.
- **ebitda_rank_desc**: Within the target region, rank branches by FY2025 EBITDA descending. The region's combined EBITDA position among all regions also uses descending rank.

## Verification

After computing all values, verify:

- Revenue = product_revenue + service_revenue for every period/year.
- Gross Margin = Revenue - COGS.
- EBITDA = Gross Margin - SGA - Allocations.
- Growth rates use prior year as denominator.
- All currency values are rounded to 2 decimals; all percentages to 4 decimals.
- Branch and region IDs are sorted ascending in lists.
