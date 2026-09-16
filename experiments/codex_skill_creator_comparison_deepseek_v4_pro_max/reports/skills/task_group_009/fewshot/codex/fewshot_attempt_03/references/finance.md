# Finance Module

## Endpoints

- `GET /api/finance/branches` — branch list with `branch_id`, `branch_name`, `region_id`, `region_name`.
- `GET /api/finance/period-map` — 24-month period map with `fiscal_year`, `month_name`, `month_number`, `period`.
- `GET /api/finance/accounts` — chart of accounts with `account`, `category`, `display_name`, `metric_type`.
- `GET /api/finance/records` — account values per branch per period. Each record has `account`, `branch_id`, `branch_name`, `region_id`, and `values` (object mapping period keys to float amounts).

## Account Categories

| Category | Accounts |
|----------|----------|
| revenue  | product_revenue, service_revenue |
| cogs     | direct_materials_cogs, direct_labor_cogs |
| sga      | sales_sga, admin_sga, occupancy_sga |
| allocations | shared_service_allocations |
| operating | orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog |

## Income Statement Formulas

For a given branch and set of periods (one period or a range), extract account values and aggregate:

```
revenue = sum(product_revenue) + sum(service_revenue)
cogs = sum(direct_materials_cogs) + sum(direct_labor_cogs)
gross_margin = revenue - cogs
sga = sum(sales_sga) + sum(admin_sga) + sum(occupancy_sga)
allocations = sum(shared_service_allocations)
ebitda = gross_margin - sga - allocations
```

## Period and Fiscal Year Aggregation

The period map defines M1–M12 as FY2024 and M13–M24 as FY2025. To aggregate across a fiscal year, sum all 12 period values for that year's range.

## Ratios and Per-Unit Metrics

```
ebitda_margin = ebitda / revenue
arpu = revenue / active_customers
sales_per_labor_headcount = revenue / labor_headcount
```

Use `active_customers` and `labor_headcount` from the same fiscal year range. If the template requires `arpu` or `sales_per_labor_headcount` for a single period, divide that period's revenue by that period's operating count.

## Regional Aggregation

A region contains multiple branches. The manifest endpoint lists branch-to-region membership. To compute regional totals, sum each account category across all branches in the region for the relevant periods, then derive the income statement and ratio lines from those aggregated category totals.

## Branch Rankings

Rankings compare all 12 branches. For each branch, compute the relevant metric (e.g., FY2025 revenue growth vs FY2024, FY2025 ebitda, arpu) and then sort descending (rank 1 = highest). Output the rank integer and the top/bottom branch_id as requested.

## Reconciliation Variance

When a region total is requested alongside branch-level details, compute:

```
region_reconciliation_variance = region_total - sum(branch_level_values_for_that_field)
```

The region total comes from aggregating all branch records for that region. The branch-level values come from the same aggregation, so the variance should be 0.0 when computed consistently. Round to 2 decimals.

## Rounding Rules

Round currency values to 2 decimals. Round percent/ratio values (ebitda_margin, revenue_growth_pct, ebitda_growth_pct, arpu, sales_per_labor_headcount) to 4 decimals.

Growth rates are computed as:

```
growth_pct = (current - prior) / prior
```

where `prior` is non-zero. Round to 4 decimals.

## Ordering

- `branch_ids` in region_context and elsewhere must be in ascending alphabetical order.
- `branch_rankings` use descending order (1 = highest) per the template.
