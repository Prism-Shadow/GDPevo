# Finance Module – Branch and Regional Reporting

This reference covers branch income statements, month-over-month variance,
fiscal-year comparisons, regional context, branch rankings, and operating
metrics built from the `/api/finance/` endpoints.

---

## Endpoints and Data Model

### `/api/finance/branches`

Returns a list of branch objects:
```json
{"branch_id": "BR-004", "branch_name": "Harbor North", "region_id": "REG-WEST", "region_name": "West"}
```

Twelve branches across four regions: REG-NORTH (BR-001..003), REG-WEST
(BR-004..006), REG-EAST (BR-007,008,011), REG-SOUTH (BR-009,010,012).

### `/api/finance/period-map`

Returns a list of period objects mapping period labels to fiscal years and
calendar months:
```json
{"fiscal_year": 2024, "month_name": "Jan", "month_number": 1, "period": "M1"}
```

The standard Crescent convention:
- M1 – M12 = the earlier fiscal year (e.g. FY2024)
- M13 – M24 = the later fiscal year (e.g. FY2025)

Always read this endpoint to confirm the actual mapping for the current data.

### `/api/finance/accounts`

Returns the chart of accounts with categories:
```json
{"account": "product_revenue", "category": "revenue", "display_name": "Product Revenue", "metric_type": "currency"}
```

Account-to-category mapping:
| Account | Category | Metric Type |
| --- | --- | --- |
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
| backlog | operating | count |

### `/api/finance/records`

Returns the full ledger. Each record is an account-branch pair with monthly
values keyed by period label:
```json
{
  "account": "product_revenue",
  "branch_id": "BR-004",
  "branch_name": "Harbor North",
  "region_id": "REG-WEST",
  "values": {"M1": 118330.31, "M2": 116982.57, ...}
}
```

Records exist for every branch × currency account combination. Operating
(count-type) accounts are also present.

---

## Single-Period Income Statement

For a given branch and period (e.g. BR-004, M24):

1. Filter all currency-type records whose `branch_id` matches the target.
2. For each category, extract the value at the requested period and sum:
   - `revenue` = sum(product_revenue[M24] + service_revenue[M24])
   - `cogs` = sum(direct_materials_cogs[M24] + direct_labor_cogs[M24])
   - `sga` = sum(sales_sga[M24] + admin_sga[M24] + occupancy_sga[M24])
   - `allocations` = shared_service_allocations[M24]
3. Compute derived fields:
   - `gross_margin` = revenue - cogs
   - `ebitda` = gross_margin - sga - allocations

Round all currency fields to 2 decimal places.

---

## Month-over-Month Revenue Variance

Given a current period (e.g. M24) and prior period (e.g. M23):

1. Compute target branch revenue for current period.
2. Compute target branch revenue for prior period.
3. `amount` = current_revenue - prior_revenue
4. `pct` = amount / prior_revenue

Round amount to 2 decimals, pct to 4 decimals.

---

## Fiscal-Year Comparisons

### Aggregating a full fiscal year for a branch

Determine which periods belong to the fiscal year from the period map.
Sum each category's monthly values across all periods in that fiscal year.

Example: FY2025 = sum of M13 through M24 for each account at the target branch.

### FY metrics template (common fields)

For the requested fiscal year (usually FY2025):

- **Revenue, COGS, Gross Margin, SGA, Allocations, EBITDA**: same category
  aggregation across all periods in the fiscal year.
- **ebitda_margin** = ebitda / revenue, rounded to 4 decimals.
- **ARPU** = revenue / active_customers for the fiscal year. Fetch the
  operating account `active_customers` and sum its monthly values across the
  fiscal year for the target branch. Divide revenue by that sum. Round to
  2 decimals.
- **sales_per_labor_headcount** = revenue / labor_headcount. Same approach
  as ARPU but using `labor_headcount`. Round to 2 decimals.

### Revenue and EBITDA growth

`revenue_growth_pct` = (fy_later_revenue - fy_earlier_revenue) / fy_earlier_revenue
`ebitda_growth_pct` = (fy_later_ebitda - fy_earlier_ebitda) / fy_earlier_ebitda

Both rounded to 4 decimals.

---

## Regional Context

When the answer template asks for region_context (branch close) or a full
regional view:

1. From branches, determine which branch_ids belong to the target region.
2. From records, aggregate revenue/ebitda for all branches in the region
   across the requested fiscal year or period.
3. For region_context in a branch close:
   - `region_id`: from branches data
   - `branch_ids`: list of branch_ids in the region, ascending
   - `fy2025_ebitda`: sum of FY2025 ebitda across all branches in the region
   - `ebitda_rank_desc`: rank of the target branch's FY2025 ebitda among
     all branches (descending, rank 1 = highest ebitda)
4. For a full regional view, compute FY2024 and FY2025 aggregates for the
   region, plus branch-level EBITDA ranking within the region.

### Region reconciliation variance

When the template asks for `region_reconciliation_variance`:

1. Sum a key metric (e.g. FY2025 revenue) across all branches in the region
   from the branch-level records.
2. Subtract the region-level aggregate from step 1 from the region-level
   value computed in the regional view.
3. The result should be 0.0 if data is consistent. Round to 2 decimals.

---

## Branch Rankings

These are global (all-branch) rankings unless constrained to a region.

### Sales growth rank

For every branch, compute FY2025 revenue growth vs FY2024. Sort descending.
Assign rank 1 to highest growth.

### Top sales growth branch

The `branch_id` with rank 1 in sales growth.

### Top ARPU branch

For every branch, compute FY2025 ARPU. Sort descending. The `branch_id` with
highest ARPU is `top_arpu_branch_id`.

### Top/Bottom EBITDA branch (regional view)

Within a region, compute FY2025 EBITDA per branch. Sort descending. The
highest is `top_ebitda_branch_id`, the lowest is `bottom_ebitda_branch_id`.
