## Finance API Reference — Crescent Finance Ops

### Endpoints

| Endpoint | Description | Query Params |
|---|---|---|
| /api/manifest | Service overview: public entities, endpoints, record counts, seed | none |
| /api/finance/branches | All 12 branches with region assignments | none |
| /api/finance/period-map | 24-month period calendar (M1–M24), fiscal year mapping | none |
| /api/finance/accounts | Chart of accounts with categories and metric types | none |
| /api/finance/records | Per-period, per-branch account values (timeseries) | period, branch_id |

### Period Convention

M1–M12 = FY2024, M13–M24 = FY2025.
The /api/finance/period-map endpoint returns 24 entries, each with period, fiscal_year, month_name, month_number.

### Chart of Accounts

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
| backlog | operating | count |

### Records Querying

The /api/finance/records endpoint accepts period (e.g. M24) and branch_id (e.g. BR-004). Returns an array of account objects, each with branch_id, branch_name, region_id, account, and values (an object keyed by period strings).

To compute FY totals, query every period in that fiscal year for every relevant branch. Query both current and prior periods for period-over-period comparisons. Query all 12 branches for rankings.

### Derived Metrics

Use standard round-half-up rounding. In Python: Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for currency, Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) for ratios.

- **Revenue** = sum(product_revenue, service_revenue) for given periods
- **COGS** = sum(direct_materials_cogs, direct_labor_cogs)
- **Gross Margin** = Revenue - COGS
- **SG&A** = sum(sales_sga, admin_sga, occupancy_sga)
- **Allocations** = shared_service_allocations
- **EBITDA** = Revenue - COGS - SG&A - Allocations
- **EBITDA Margin** = EBITDA / Revenue (ratio, 4 decimals)
- **ARPU** = Revenue / active_customers (for a given period or range, 2 decimals)
- **Sales per Labor Headcount** = Revenue / labor_headcount (for a given period or range, 2 decimals)

### Revenue Variance (MoM)

- **amount** = M24 revenue - M23 revenue
- **pct** = amount / M23 revenue (4 decimals)

### Revenue / EBITDA Growth (FY vs FY)

- **revenue_growth_pct** = (FY2025 revenue - FY2024 revenue) / FY2024 revenue (4 decimals)
- **ebitda_growth_pct** = (FY2025 EBITDA - FY2024 EBITDA) / FY2024 EBITDA (4 decimals)

### Branch Rankings (system-wide, M13-M24 = FY2025)

- **sales_growth_rank_desc**: Rank all 12 branches by FY2025 vs FY2024 revenue growth descending. 1 = highest growth.
- **top_sales_growth_branch_id**: Branch with rank 1.
- **top_arpu_branch_id**: Branch with highest ARPU across all 12 branches for FY2025. ARPU = sum(M13-M24 revenue) / sum(M13-M24 active_customers).

### Regional Context

From /api/finance/branches, determine which branches belong to the target region.

For branch close reporting:
- region_id: target region ID
- branch_ids: ascending list of branch IDs in the same region
- fy2025_ebitda: sum of FY2025 EBITDA across all branches in the region
- ebitda_rank_desc: rank of the target region among all 4 regions by FY2025 total EBITDA descending (1 = highest region EBITDA)

For regional management views:
- top_ebitda_branch_id: branch in the region with the highest FY2025 EBITDA
- bottom_ebitda_branch_id: branch in the region with the lowest FY2025 EBITDA

### Output Conventions

- Currency: rounded to 2 decimal places using standard round-half-up
- Percent/ratio: rounded to 4 decimal places using standard round-half-up
- Lists: ascending stable IDs unless a rank field dictates descending order
- Period convention object: M1_to_M12 = "FY2024", M13_to_M24 = "FY2025", current_month = period label, prior_month = prior period label
- Region reconciliation variance: region_rev minus sum(branch_rev for branches in region). Should equal 0.0.
