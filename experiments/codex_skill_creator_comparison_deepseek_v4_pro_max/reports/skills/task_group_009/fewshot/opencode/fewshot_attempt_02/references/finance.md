# Finance Domain Reference

The finance endpoints (`/api/finance/branches`, `/api/finance/period-map`,
`/api/finance/accounts`, `/api/finance/records`) support branch-level P&L,
fiscal-year aggregation, regional rollups, and branch rankings.

## Period Convention

The period map defines 24 months across two fiscal years:
- **FY2024**: M1 through M12
- **FY2025**: M13 through M24

A `period_convention` object maps these two FY blocks to labels. If a task asks
for `period_convention`, return:

```json
{
  "M1_to_M12": "FY2024",
  "M13_to_M24": "FY2025",
  "current_month": "<period label from request>",
  "prior_month": "<period label from request>"
}
```

Always name the key `period_convention` at the top level, not inside another
object.

## Account Categories and Income Statement Construction

The accounts endpoint maps each `account` string to a `category`:

| Account | Category | Aggregation |
|---------|----------|------------|
| `product_revenue` | `revenue` | sum into `revenue` |
| `service_revenue` | `revenue` | sum into `revenue` |
| `direct_materials_cogs` | `cogs` | sum into `cogs` |
| `direct_labor_cogs` | `cogs` | sum into `cogs` |
| `sales_sga` | `sga` | sum into `sga` |
| `admin_sga` | `sga` | sum into `sga` |
| `occupancy_sga` | `sga` | sum into `sga` |
| `shared_service_allocations` | `allocations` | direct |
| `orders` | `operating` | used for ratios |
| `revenue_units` | `operating` | used for ratios |
| `active_customers` | `operating` | used for ratios |
| `labor_headcount` | `operating` | used for ratios |
| `admin_headcount` | `operating` | used for ratios |
| `backlog` | `operating` | used for ratios |

To build a single-period income statement (e.g., M24), filter finance records
to the target branch and period, then sum `revenue` accounts into `revenue`,
`cogs` accounts into `cogs`, `sga` accounts into `sga`, and use
`shared_service_allocations` directly for `allocations`. Then derive:

- `gross_margin` = `revenue` − `cogs`
- `ebitda` = `gross_margin` − `sga` − `allocations`

## Fiscal-Year Aggregation

To build an FY income statement, sum every period in the year's range for each
category. Sum M1–M12 for FY2024; sum M13–M24 for FY2025. Then compute the same
derived values from the FY totals.

### Fiscal-Year Ratios

The template may request FY-level operating ratios:

- **`ebitda_margin`**: `ebitda` / `revenue`, rounded to 4 decimals.
- **`arpu`**: `revenue` / sum of `revenue_units` for the branch across all
  periods in the fiscal year, rounded to 2 decimals.
- **`sales_per_labor_headcount`**: `revenue` / sum of `labor_headcount` for
  the branch across all periods in the fiscal year, rounded to 2 decimals.

**Important**: For ratios that use operating accounts (`revenue_units`,
`labor_headcount`), sum the operating account values across all periods in the
fiscal year, then divide the corresponding FY currency total by that sum.

### Growth Rates

- `revenue_growth_pct`: (FY2025 `revenue` − FY2024 `revenue`) / FY2024
  `revenue`, rounded to 4 decimals.
- `ebitda_growth_pct`: (FY2025 `ebitda` − FY2024 `ebitda`) / FY2024 `ebitda`,
  rounded to 4 decimals.

## MoM Revenue Variance

Given `current_month` period and `prior_month` period from the request memo,
pull revenue records for the target branch. The variance:

- `amount` = `revenue`(current) − `revenue`(prior), rounded to 2 decimals.
- `pct` = `amount` / `revenue`(prior), rounded to 4 decimals.

## Regional Context

When the answer template includes `region_context`:

1. Look up the target branch in the branches endpoint to find its `region_id`.
2. Collect all branch IDs belonging to that `region_id`.
3. For `fy2025_ebitda`, sum every branch in the region: for each branch, compute
   its FY2025 EBITDA (as described above), then sum them.
4. For `ebitda_rank_desc`: rank the target branch among all branches (across all
   regions) by FY2025 EBITDA, descending (highest = 1). Return the rank as an
   integer.

If the template also includes a separate top-level `region_context` with
`branch_ids` as a list, return the branch IDs in ascending string order.

## Branch Rankings

When the answer template includes `branch_rankings`:

1. **`sales_growth_rank_desc`**: Compute `revenue_growth_pct` for every branch
   across all regions (FY2025 vs FY2024). Rank the target branch descending by
   this growth rate (highest growth = 1). Return the rank as an integer.

2. **`top_sales_growth_branch_id`**: The branch with the highest revenue growth
   percentage across all branches. If multiple tie, pick the branch with the
   lowest (lexicographically first) `branch_id`.

3. **`top_arpu_branch_id`**: The branch with the highest `arpu` for FY2025
   across all branches. If multiple tie, pick the branch with the lowest
   `branch_id`.

## Region Reconciliation Variance

When the template includes `region_reconciliation_variance`:
Compute total region revenue as the sum of FY2025 revenue for every branch in
the region. Then confirm by cross-footing against a simple sum of the revenue
accounts across all branches in the region for all M13-M24 periods. The
difference should be 0.0 if correctly computed. This is typically 0.0 when
there is no discrepancy between the two aggregation paths.

## Currency, Percent, and Ratio Rounding

- Currency values: round to 2 decimals using banker's rounding (`round(x, 2)`).
- Percent values (growth rates, margins): round to 4 decimals (`round(x, 4)`).
- Ratios that are currency-per-unit (e.g., `arpu`): round to 2 decimals.
