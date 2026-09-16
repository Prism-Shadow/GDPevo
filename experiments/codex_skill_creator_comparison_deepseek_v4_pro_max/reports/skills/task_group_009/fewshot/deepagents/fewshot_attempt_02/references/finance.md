# Crescent Finance — Branch Reporting Reference

## Endpoints

| Endpoint | Description |
|---|---|
| `/api/finance/branches` | List of all branches: `branch_id`, `branch_name`, `region_id`, `region_name` |
| `/api/finance/period-map` | Period-to-fiscal-year mapping: `period` (M1–M24), `fiscal_year`, `month_name`, `month_number` |
| `/api/finance/accounts` | Chart of accounts: `account`, `category`, `display_name`, `metric_type` (`currency` or `count`) |
| `/api/finance/records` | Per-period record values: `account`, `branch_id`, `branch_name`, `region_id`, `values` (map of period → amount) |

## Period Convention

M1–M12 → FY2024, M13–M24 → FY2025. `current_month` and `prior_month` are period labels (e.g. `"M24"`, `"M23"`); fiscal-year periods are `"FY####"` strings.

## Account Categories

**Currency accounts** (`metric_type`: `"currency"`):

| Account | Category |
|---|---|
| `product_revenue` | revenue |
| `service_revenue` | revenue |
| `direct_materials_cogs` | cogs |
| `direct_labor_cogs` | cogs |
| `sales_sga` | sga |
| `admin_sga` | sga |
| `occupancy_sga` | sga |
| `shared_service_allocations` | allocations |

**Count accounts** (`metric_type`: `"count"`): `labor_headcount`, `revenue_units`, `orders`, `active_customers`, `admin_headcount`, `backlog`.

## Formulas

### Income Statement (per branch, per period)

Sum all records for the branch over the given period(s), grouped by account:

```
revenue    = sum(product_revenue + service_revenue)
cogs       = sum(direct_materials_cogs + direct_labor_cogs)
gross_margin = revenue - cogs
sga        = sum(sales_sga + admin_sga + occupancy_sga)
allocations = sum(shared_service_allocations)
ebitda     = gross_margin - sga - allocations
```

### MoM Revenue Variance

```
amount = revenue(current_month) - revenue(prior_month)
pct    = amount / abs(revenue(prior_month))
```

### Fiscal Year Comparison

FY2024 = sum over M1–M12. FY2025 = sum over M13–M24.

```
revenue_growth_pct = (fy2025_revenue - fy2024_revenue) / abs(fy2024_revenue)
ebitda_growth_pct  = (fy2025_ebitda - fy2024_ebitda) / abs(fy2024_ebitda)
```

### Derived FY2025 Metrics

```
ebitda_margin             = fy2025_ebitda / fy2025_revenue
arpu                      = fy2025_revenue / sum(revenue_units for branch M13–M24)
sales_per_labor_headcount = fy2025_revenue / sum(labor_headcount for branch M13–M24)
```

### Region Context

Gather all branches belonging to the region. Region totals = sum of per-branch FY2025 values. `ebitda_rank_desc` = rank of the target branch's FY2025 EBITDA among its region's branches (1 = highest).

### Branch Rankings (all 12 branches)

- **sales_growth_rank_desc**: rank by revenue growth (FY2025 vs FY2024), 1 = highest
- **top_sales_growth_branch_id**: branch with rank 1
- **top_arpu_branch_id**: branch with highest FY2025 ARPU

### Region Reconciliation

```python
branch_ebitda = sum of per-branch FY2025 EBITDA for the region
region_ebitda = sum of all records in the region for FY2025 in ebitda formula
reconciliation_variance = region_ebitda - branch_ebitda
```

When both are derived from the same records, the variance is 0.
