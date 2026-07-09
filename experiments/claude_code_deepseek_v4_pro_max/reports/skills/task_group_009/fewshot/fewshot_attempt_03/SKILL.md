# Crescent Finance Ops — Transferable Skill

## Environment

Base URL: `http://34.46.77.124:8009` (use HTTP, never HTTPS).  
This URL overrides any `localhost`/`127.0.0.1` references found in payload files.

### API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Global listing of branches, ensembles, productions, record counts |
| `GET /api/finance/branches` | Branch registry: `branch_id`, `branch_name`, `region_id`, `region_name` |
| `GET /api/finance/period-map` | Fiscal calendar: maps `period` (M1–M24) to `fiscal_year` and `month_name` |
| `GET /api/finance/accounts` | Chart of accounts: `account`, `category`, `display_name`, `metric_type` |
| `GET /api/finance/records` | All financial record values by `account` × `branch_id` across all periods |
| `GET /api/compensation/rate-book` | Compensation constants: MWS, seniority bands, title premium pcts, quarter_weeks, business rules |
| `GET /api/compensation/rosters` | Ensemble rosters: employee-level attributes, weeks by quarter, years of service |
| `GET /api/compensation/scenarios` | Forecast scenarios: growth rates per pay-type component for Year+1 and Year+2 |
| `GET /api/payroll/rate-book` | Payroll constants: service rates, premium pcts, conflict thresholds, guarantee, time limits |
| `GET /api/payroll/productions` | Weekly productions: schedule (services) and roster with musician flags and assigned services |

---

## Rounding & Output Conventions

- **Currency**: round to 2 decimal places (e.g. `123456.78`).
- **Percent / ratio**: round to 4 decimal places (e.g. `0.0138`, `0.2459`).
- **Lists**: ascending by ID string (lexicographic) unless a `_rank` or `_desc` field explicitly dictates descending rank order.
- **Conflict flags list**: sorted alphabetically.
- **Per-musician list**: ordered ascending by `musician_id`.

---

## Task Family 1: Branch Financial Close Reporting

**Endpoints needed:** `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/records`

### Period Convention

From the period map:  
- **M1–M12** → **FY2024**  
- **M13–M24** → **FY2025**

When a task asks for "current fiscal year" context around a close period in M13–M24, that is FY2025. Always derive this from `/api/finance/period-map` rather than hard-coding.

### Income Statement Line Items (for a single branch × single period)

Fetch all records for the target `branch_id`. Sum by account category:

```
Revenue   = product_revenue + service_revenue
COGS      = direct_materials_cogs + direct_labor_cogs
Gross Margin = Revenue - COGS
SG&A      = sales_sga + admin_sga + occupancy_sga
Allocations = shared_service_allocations
EBITDA    = Gross Margin - SG&A - Allocations
```

### MoM Revenue Variance

```
amount = revenue(current_month) - revenue(prior_month)
pct    = amount / revenue(prior_month)
```

### Full Fiscal Year Aggregates

To compute FY2025 totals for a branch: sum the 12 monthly values for M13 through M24.  
To compute FY2024 totals for a branch: sum M1 through M12.

KPI formulas for a full fiscal year:

```
EBITDA Margin = FY_EBITDA / FY_Revenue
ARPU          = FY_Revenue / SUM(revenue_units over the FY)
Sales per Labor Headcount = FY_Revenue / SUM(labor_headcount over the FY)
Revenue Growth Pct = (FY2025_revenue - FY2024_revenue) / FY2024_revenue
EBITDA Growth Pct  = (FY2025_ebitda - FY2024_ebitda) / FY2024_ebitda
```

Always use SUM of period-level values for denominator counts like `revenue_units` and `labor_headcount`.

### Branch Rankings (all 12 branches)

**Sales growth rank:** Compute `revenue_growth_pct` for every branch. Sort descending and assign rank 1 to the highest growth. Report the target branch's rank and the branch_id with rank 1.

**Top ARPU:** Compute ARPU for FY2025 for every branch. Identify the branch_id with the maximum ARPU.

### Region Context

1. Look up the target branch in `/api/finance/branches` to get `region_id` and `branch_name`.
2. Find all branches with the same `region_id` (the `branch_ids` list in ascending order).
3. Compute FY2025 EBITDA for every branch in that region.
4. Sort region branches descending by EBITDA; the target branch's position is `ebitda_rank_desc` (1 = best).
5. The region's total `fy2025_ebitda` is the SUM of all region branches' FY2025 EBITDA.

---

## Task Family 2: Compensation — Current-Year Summary

**Endpoints needed:** `/api/compensation/rate-book`, `/api/compensation/rosters`

### Rate Book Constants

| Field | Meaning |
|---|---|
| `minimum_weekly_scale` (MWS) | Base weekly pay every musician receives |
| `seniority_weekly` | Banded weekly add-on by `years_of_service` |
| `title_premium_pct` | Weekly add-on = MWS × title_pct (by title name) |
| `quarter_weeks` | Default quarter week counts (Q1–Q4, typically 13 each) |
| `pay_types` | Canonical ordered list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]` |
| `current_year` | The calendar year for the current compensation period |

### Per-Employee Weekly Rate

For each roster member of the target ensemble:

```
weekly_mws   = minimum_weekly_scale

weekly_title = if combined_overscale_includes_title is FALSE AND title is not null:
                   minimum_weekly_scale × title_premium_pct[title]
               else:
                   0

weekly_sr    = seniority_weekly[band matching years_of_service]
               (bands: 0-4→0, 5-9→48, 10-14→82, 15-19→126, 20-24→170, 25+→215)

weekly_ov    = overscale_weekly (0.0 if absent)

weekly_total = weekly_mws + weekly_title + weekly_sr + weekly_ov
```

### Quarter Totals

**Critical rule:** Use the employee's actual `weeks_by_quarter` from the roster, NOT the default `quarter_weeks` from the rate book. Employees with "Partial-quarter service schedule" notes may have fewer than 13 weeks in some quarters.

```
Q{X}_total = Σ over employees: weekly_total × weeks_by_quarter["Q{X}"]
```

### Pay-Type Totals

Sum each pay-type component across all employees × all actual weeks:

```
Minimum Weekly Scale   = Σ (weekly_mws   × weeks)
Titled Position Premium = Σ (weekly_title × weeks)
Seniority              = Σ (weekly_sr    × weeks)
Overscale              = Σ (weekly_ov    × weeks)
```

`annual_total` = sum of all four pay-type totals (must equal sum of Q1+Q2+Q3+Q4).

### Derived Counts

- `roster_count`: total employees in the ensemble's roster.
- `combined_overscale_employee_count`: count of employees with `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count`: count of employees whose `notes` field contains `"Partial-quarter"`.
- `largest_pay_type`: the pay type with the highest annual total.

---

## Task Family 3: Payroll — Weekly Production Review

**Endpoints needed:** `/api/payroll/rate-book`, `/api/payroll/productions`

### Service Rates

| Service Type | Rate | Unit |
|---|---|---|
| Performance | 260.25 | Per service (flat) |
| Audit | 260.25 | Per service (flat) |
| 1hr Sound Check | 80.00 | Per service (flat) |
| 2hr Sound Check | 142.50 | Per service (flat) |
| Rehearsal | 58.75 | Per hour (3-hour minimum call) |

### Service Counts

Count each service type from the production schedule. E.g., count how many schedule entries have `service_type == "Performance"`.

### Per-Musician Payroll Calculation

For each musician in the production roster:

**Step 1 — Base service pay.**  
For each assigned service (by `assigned_service_ids`):

- Performance / Audit / Sound Check: flat rate from the rate book.  
- Rehearsal: `max(duration_hours, 3.0) × 58.75`.  

Sum these as `base_pay`.

**Step 2 — Substitute adjustment (if `substitute == true`).**  
Compute `substitute_adjustment = base_pay × 0.40`.  
(The effective base for premium calculations below becomes `base_pay + substitute_adjustment`.)

**Step 3 — Premiums.**  
Compute the sum of applicable premium percentages from the rate book:

| Flag | Premium % |
|---|---|
| `principal == true` | 15% (`principal_or_lead`) |
| `lead == true` | 15% (`principal_or_lead`) |
| `quartet == true` | 15% (`quartet`) |
| `electronic == true` | 25% (`electronic`) |

Apply these to the effective base (`base_pay + substitute_adjustment` if substitute, else `base_pay`):

```
premium_total = effective_base × Σ(applicable premium percents)
```

**Step 4 — Doubles.**  
If `doubles > 0`:

```
doubles_total = effective_base × (0.25 + (doubles - 1) × 0.10)
```

The first extra instrument is 25%; each additional is 10%.

**Step 5 — Vacation.**  
If `vacation_eligible == true`:

```
vacation = 0.04 × (effective_base + premium_total + doubles_total)
```

Substitutes are typically NOT vacation_eligible.

**Step 6 — Guarantee adjustment.**  
Only for non-substitute (`substitute == false`) regular players:

```
if base_pay < weekly_guarantee (2082.00):
    guarantee_adjustment = weekly_guarantee - base_pay
```

Substitutes do NOT receive a guarantee adjustment.

**Step 7 — Musician total.**  

```
musician_total = base_pay + substitute_adjustment + premium_total + doubles_total + vacation + guarantee_adjustment
```

### Category Totals and Per-Musician Categories

Aggregate each pay category across all musicians. Per-musician categories list only non-zero line items with the category name as it appears in the rate book / calculation (e.g. `"performance"`, `"rehearsal"`, `"audit"`, `"sound_check"`, `"premium"`, `"doubles"`, `"vacation"`, `"guarantee_adjustment"`, `"substitute_adjustment"`).

`weekly_total` = sum of all category totals (must equal sum of all per-musician totals).

### Conflict Flags

Evaluate the full production schedule:

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any Rehearsal with `start_time` before `"09:00"` |
| `REHEARSAL_LATE_END` | Any Rehearsal with `end_time` after `"18:30"` |
| `SERVICE_OVER_TIME_LIMIT` | Any service where `duration_hours > service_time_limits[service_type]` |
| `SOUND_CHECK_DURATION_MISMATCH` | Sound check labeled "1hr" but `duration_hours ≠ 1.0`, or labeled "2hr" but `duration_hours ≠ 2.0` |

Compare times as strings lexicographically (HH:MM format).  
Sort the resulting flag list alphabetically.

### Top-Paid Musician

Identify the `musician_id` with the highest `total` in the per-musician list.

---

## Task Family 4: Regional Management Reporting

**Endpoints needed:** `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/records`

### Identifying Branches in the Region

Query `/api/finance/branches` and filter by `region_id`. List `branch_ids` in ascending order.

### Region-Level Aggregates

For each line item (Revenue, SG&A, Allocations, EBITDA), sum the branch-level values across all branches in the region. The same account-category aggregation formulas from Task Family 1 apply at the branch level first, then sum across branches.

```
Region Revenue = Σ branch_revenue (each computed as product_revenue + service_revenue for the fiscal year)
Region SG&A    = Σ (sales_sga + admin_sga + occupancy_sga) over the FY for each branch
Region Alloc   = Σ shared_service_allocations over the FY for each branch
Region EBITDA  = Region Revenue - Region COGS - Region SG&A - Region Allocations
```

EBITDA Margin and Sales per Labor Headcount are computed at the **region level** after summing:

```
region_ebitda_margin = region_ebitda / region_revenue
region_sales_per_labor = region_revenue / Σ(labor_headcount across all region branches over the FY)
```

### Revenue Growth

```
revenue_growth_pct = (fy2025_region_revenue - fy2024_region_revenue) / fy2024_region_revenue
```

### Branch-Level EBITDA Ranking within Region

For each branch in the region, compute FY2025 EBITDA. Sort descending:
- `top_ebitda_branch_id`: the branch with the highest FY2025 EBITDA.
- `bottom_ebitda_branch_id`: the branch with the lowest FY2025 EBITDA.

### Reconciliation Variance

`region_reconciliation_variance` is the difference between region-level EBITDA computed via the region-level accounts and the sum of branch-level EBITDAs. If all data ties out, this should be `0.0`.

---

## Task Family 5: Compensation Forecast

**Endpoints needed:** `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`

### Scenario Structure

Each scenario defines per-year growth factors:

```json
{
  "year_plus_1": { "mws_growth": ..., "overscale_growth": ..., "seniority_growth": ..., "title_pct_multiplier": ... },
  "year_plus_2": { "mws_growth": ..., "overscale_growth": ..., "seniority_growth": ..., "title_pct_multiplier": ... }
}
```

### Forecast Year Compounding

**Critical: growth rates compound year-over-year, not from the base year.**

```
Year+1 MWS        = current_MWS × (1 + Y1.mws_growth)
Year+2 MWS        = Year+1_MWS × (1 + Y2.mws_growth)

Year+1 Overscale  = current_overscale_weekly × (1 + Y1.overscale_growth)
Year+2 Overscale  = Year+1_overscale × (1 + Y2.overscale_growth)

Year+1 Seniority  = seniority_band_lookup(years_of_service + 1) × (1 + Y1.seniority_growth)
Year+2 Seniority  = seniority_band_lookup(years_of_service + 2) × (1 + Y1.seniority_growth) × (1 + Y2.seniority_growth)

Year+1 Title Pct  = title_premium_pct × Y1.title_pct_multiplier
Year+2 Title Pct  = Year+1_title_pct × Y2.title_pct_multiplier
```

**Years of service:** Add 1 for Year+1, add 2 for Year+2 (cumulative from current). If this pushes an employee into a higher seniority band, use the new band's rate scaled by the appropriate growth factor(s).

The `combined_overscale_includes_title` rule still applies: if true, do not add titled position premium separately in any forecast year.

### Annual Totals

Compute the full-year compensation total for the ensemble under each scenario year (current, year_plus_1, year_plus_2) using the per-employee formulas above and the roster's actual `weeks_by_quarter`.

```
annual_totals.current      = compute_year(roster, current params, 0 years_added, no growth)
annual_totals.year_plus_1  = compute_year(roster, Y1 params, 1 year_added)
annual_totals.year_plus_2  = compute_year(roster, Y2 params, 2 years_added)
```

### Growth Rates

```
year_plus_1_vs_current    = (Y1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (Y2_total - Y1_total) / Y1_total
```

### Year+2 Quarter and Pay-Type Totals

Compute quarter totals and pay-type totals for Year+2 using the same breakdown logic as Task Family 2, but with Year+2 parameters.

### Largest Growth Pay Type

Compute each pay type's total for both the current year and Year+2. The largest growth pay type is the one with the highest **percentage growth** from current to Year+2:

```
growth_pct = (Y2_pay_type_total - current_pay_type_total) / current_pay_type_total
```

### Treatment Counts

Same as current-year compensation: `combined_overscale_employee_count` and `partial_quarter_employee_count` come from the base roster (these do not change across forecast years).

---

## Common Pitfalls

1. **Period convention binding.** Always read `/api/finance/period-map` to confirm which fiscal year each M-number maps to. Never assume M1=January of the current calendar year.

2. **Revenue is the sum of two accounts.** Many errors come from including only `product_revenue` or only `service_revenue`. Revenue = both.

3. **Gross Margin is NOT in the accounts list.** It is a derived value: Revenue − COGS.

4. **EBITDA uses all expense categories.** EBITDA = Revenue − COGS − SG&A − Allocations. All four expense groups (direct_materials_cogs, direct_labor_cogs, sales_sga, admin_sga, occupancy_sga, shared_service_allocations) must be included.

5. **Denominators are sums, not period-counts.** ARPU denominator = SUM of `revenue_units` across all 12 periods of the FY, not a single-period value. Same for `labor_headcount` in Sales-per-Labor.

6. **Use actual employee quarter weeks, not the rate-book default.** The rate book's `quarter_weeks` (13/13/13/13) is a reference; the roster's `weeks_by_quarter` is the truth for each employee.

7. **combined_overscale_includes_title.** When true, the `overscale_weekly` already bundles the title premium. Do NOT add `title_premium_pct × MWS` separately for that employee.

8. **Forecast growth compounds year-over-year.** Year+2 MWS is NOT `2520 × (1 + Y1.mws_growth + Y2.mws_growth)`. It is `2520 × (1 + Y1.mws_growth) × (1 + Y2.mws_growth)`. Same for overscale and seniority factors.

9. **Seniority years increment for forecast.** Add 1 year for Year+1, 2 years for Year+2. The seniority band may change as a result; then apply the appropriate growth factor to the new band's rate.

10. **Substitute musicians in payroll.** Substitutes have `substitute_adjustment` instead of `guarantee_adjustment`. They are typically NOT vacation_eligible. For non-substitute regulars, the guarantee applies only when `base_pay < weekly_guarantee`.

11. **Rehearsal minimum call.** Rehearsal pay = `58.75 × max(duration_hours, 3.0)`. A 2.5-hour rehearsal pays for 3.0 hours.

12. **Doubles premium tiering.** First extra instrument = 25%. Each additional extra instrument = 10% each. For `doubles = 2`: 25% + 10% = 35%.

13. **Region reconciliation.** Always verify that the region-level totals from summing branch data match any separately reported region figures. Variance should be 0.0 when data ties out.

14. **Pay-type output order.** When the template lists pay types, use the canonical order from the rate-book's `pay_types` array: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`.
