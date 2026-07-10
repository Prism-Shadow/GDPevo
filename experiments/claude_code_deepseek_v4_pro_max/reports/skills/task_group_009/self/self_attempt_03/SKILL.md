# Crescent Finance Ops — Transferable Skill

## Environment
All tasks use the same remote API base; there is no local env, no setup script, and no mock server. Always use the base URL from `environment_access.md`.

- HTTP only (no HTTPS)
- Key public endpoints:

```
GET {BASE}/api/manifest
GET {BASE}/api/finance/branches
GET {BASE}/api/finance/period-map
GET {BASE}/api/finance/accounts
GET {BASE}/api/finance/records
GET {BASE}/api/compensation/rate-book
GET {BASE}/api/compensation/rosters
GET {BASE}/api/compensation/scenarios
GET {BASE}/api/payroll/rate-book
GET {BASE}/api/payroll/productions
```

- All payloads (`request_memo.json`, `answer_template.json`, `environment_access.json`) live under `payloads/`.
- The `environment_access.json` in payloads may list `localhost`; the top-level `environment_access.md` overrides it — always use the remote URL from `environment_access.md`.

---

## Task Domains

There are five recurring task types across the train set:

| Domain | Endpoints Used | What It Produces |
|--------|---------------|-----------------|
| **Branch Close (Finance)** | `/api/finance/branches`, `/period-map`, `/accounts`, `/records` | Monthly P&L, MoM variance, FY comparison, region & ranking |
| **Compensation Summary** | `/api/compensation/rate-book`, `/rosters` | Current-year comp by quarter & pay type, roster counts |
| **Payroll Review** | `/api/payroll/rate-book`, `/productions` | Weekly payroll total, per-musician, category totals, CBA flags |
| **Regional View (Finance)** | `/api/finance/branches`, `/period-map`, `/accounts`, `/records` | Multi-branch regional aggregates, FY comparisons, branch EBITDA ranks |
| **Compensation Forecast** | `/api/compensation/rate-book`, `/rosters`, `/scenarios` | Current + 2 forecast years, growth rates, Y+2 quarter/pay-type detail |

---

## Rounding & Ordering Conventions

- **Currency fields**: round to **2 decimals** with `round(value, 2)`.
- **Percent / ratio / growth fields**: round to **4 decimals** with `round(value, 4)`.
- **Lists of branch IDs**: sort **ascending** (e.g. `['BR-004','BR-005','BR-006']`).
- **per_musician arrays**: sort by `musician_id` ascending.
- **conflict_flags**: sort alphabetically.
- **Pay types**: use the order from the rate book (`Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`).
- **Category totals** in payroll should sum exactly to `weekly_total`. Compute per-musician rounded values first, then aggregate category totals from the per-musician arrays so the numbers reconcile exactly (avoid floating-point drift).

---

## Finance Records — Core Data Model

### Period Map
- M1–M12 = FY2024, M13–M24 = FY2025.
- Each period has `fiscal_year`, `month_name` (Jan–Dec), `month_number` (1–12).

### Accounts (account → category mapping)

| Account | Category | Metric Type |
|---------|----------|-------------|
| `product_revenue` | revenue | currency |
| `service_revenue` | revenue | currency |
| `direct_materials_cogs` | cogs | currency |
| `direct_labor_cogs` | cogs | currency |
| `sales_sga` | sga | currency |
| `admin_sga` | sga | currency |
| `occupancy_sga` | sga | currency |
| `shared_service_allocations` | allocations | currency |
| `orders` | operating | count |
| `revenue_units` | operating | count |
| `active_customers` | operating | count |
| `labor_headcount` | operating | count |
| `admin_headcount` | operating | count |
| `backlog` | operating | count |

### Income Statement Derivation
```
revenue  = product_revenue + service_revenue
cogs     = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga      = sales_sga + admin_sga + occupancy_sga
allocations = shared_service_allocations
ebitda   = gross_margin - sga - allocations
```

### Key Ratios
```
ebitda_margin = ebitda / revenue          (decimal, 4 decimals)

arpu          = total FY revenue / SUM of monthly active_customers      (2 decimals)
  — "ARPU" = Average Revenue Per User. Use sum of monthly counts (customer-months),
    not an average.

sales_per_labor_headcount = total FY revenue / SUM of monthly labor_headcount  (2 decimals)
```

### Period Aggregation
- Use the period labels (M1, M2, … M24) as keys into `records[n].values`.
- For a fiscal year total, sum all 12 period values for each relevant account.
- For multi-branch region totals, sum across all branches in the region.

### Branches & Regions
12 branches across 4 regions:
- **REG-NORTH**: BR-001 (Aurora North), BR-002 (Granite Bay), BR-003 (Lakeview)
- **REG-WEST**: BR-004 (Harbor North), BR-005 (Pine Hill), BR-006 (Mesa Ridge)
- **REG-EAST**: BR-007 (Riverbend), BR-008 (Old Port), BR-011 (Summit Yard)
- **REG-SOUTH**: BR-009 (Beacon South), BR-010 (Coral Point), BR-012 (Valley Forge)

### Rankings
- **sales_growth_rank_desc**: Rank all 12 branches by revenue growth (FY2025 vs FY2024), descending (rank 1 = highest growth).
- **ebitda_rank_desc** (within region): Rank branches inside the target region by FY2025 EBITDA, descending.
- **top_sales_growth_branch_id**: The branch with the highest revenue growth across all 12.
- **top_arpu_branch_id**: The branch with the highest FY2025 ARPU across all 12.

### Region Reconciliation Variance
In the regional view, `region_reconciliation_variance` should be the difference between region-level EBITDA and the sum of individual branch EBITDAs. When all data comes from the same API, this is normally `0.0`.

---

## Compensation — Core Data Model

### Ensemble → Roster
Each ensemble has a roster of employees. Key fields per employee:

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | string | e.g. `ENS-REDWOOD-001` |
| `ensemble_id` | string | |
| `title` | string or null | Concertmaster, Principal, Associate Principal, Assistant Principal, Section Lead, or null |
| `years_of_service` | int | Used to determine seniority band |
| `overscale_weekly` | float | Weekly overscale amount |
| `combined_overscale_includes_title` | bool | If true, do NOT add a separate Titled Position Premium |
| `weeks_by_quarter` | {Q1: N, Q2: N, Q3: N, Q4: N} | Usually 13; partial when ≠ 13 |

### Rate Book
- `minimum_weekly_scale`: base weekly rate (e.g. 2520.0)
- `current_year`: integer year (e.g. 2026)
- `quarter_weeks`: fixed at {Q1: 13, Q2: 13, Q3: 13, Q4: 13}
- `pay_types`: ordered list — `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `seniority_weekly`: list of bands with `min_years`, `max_years` (null for unbounded), `weekly_amount`
- `title_premium_pct`: map of title → percentage of MWS

### Compensation Formulas (per employee, per quarter)
```
MWS Pay        = minimum_weekly_scale × weeks_in_quarter

Title Premium  = IF NOT combined_overscale_includes_title AND title is not null:
                   minimum_weekly_scale × title_premium_pct[title] × weeks_in_quarter

Seniority Pay  = seniority_weekly[band] × weeks_in_quarter
                 — Find band where min_years ≤ years_of_service ≤ max_years
                 — max_years may be null (no upper bound)

Overscale Pay  = overscale_weekly × weeks_in_quarter
```

Total per quarter = sum of MWS + Title Premium + Seniority + Overscale across all employees.
Total per pay type = same sum grouped by pay type.

### Roster Treatment Counts
- `roster_count`: number of employees in the ensemble roster
- `combined_overscale_employee_count`: count of employees with `combined_overscale_includes_title == true`
- `partial_quarter_employee_count`: count of employees where any quarter's weeks ≠ 13

### Largest Pay Type
Compare the annual totals (sum across Q1–Q4) for each pay type. The largest by amount wins.

---

## Compensation Forecast — Scenario Model

### Scenarios
Each scenario defines growth parameters for two forward years (`year_plus_1`, `year_plus_2`):

| Parameter | Applies To | How |
|-----------|-----------|-----|
| `mws_growth` | `minimum_weekly_scale` | Multiplier: `mws × (1 + growth)` |
| `overscale_growth` | Each employee's `overscale_weekly` | Multiplier: `overscale × (1 + growth)` |
| `seniority_growth` | Each seniority band's `weekly_amount` | Multiplier: `band_amount × (1 + growth)` |
| `title_pct_multiplier` | Each title's premium percentage | Multiplier on the existing title_pct |

### Compounding Rule
Growth rates compound year-over-year. Year+1 builds on the current base; Year+2 builds on Year+1:
```
Year+1 MWS = base_mws × (1 + y1.mws_growth)
Year+2 MWS = Year+1 MWS × (1 + y2.mws_growth)
```
Same compounding applies to overscale, seniority, and title percentages.

### Seniority Year Offset
- **Current**: use `years_of_service` as-is
- **Year+1**: `years_of_service + 1` before selecting seniority band
- **Year+2**: `years_of_service + 2` before selecting seniority band

### Growth Rates Output
```
year_plus_1_vs_current     = (year_plus_1_total - current_total) / current_total
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / year_plus_1_total
```
Rounded to 4 decimals.

### Largest Growth Pay Type
Compare the **current-year** pay type totals against the **Year+2** pay type totals. The pay type with the largest absolute dollar increase is `largest_growth_pay_type`.

---

## Payroll — Core Data Model

### Productions
Each production has a `schedule` (list of services) and a `roster` (list of musicians and their assignments).

### Service Rates (from rate book)
| Service Type | Rate | Basis |
|-------------|------|-------|
| Performance | 260.25 | Per service |
| Audit | 260.25 | Per service |
| Rehearsal | 58.75 | Hourly, **3-hour minimum call** |
| 1hr Sound Check | 80.00 | Per service |
| 2hr Sound Check | 142.50 | Per service |

### Rehearsal Pay
`Rehearsal pay = rehearsal_rate × MAX(duration_hours, 3.0)`

### Premiums (applied to base service pay, pre-vacation)
Premiums do **NOT** apply to substitutes. For regular musicians:

| Premium | Trigger | Rate |
|---------|---------|------|
| Principal or Lead | `principal == true` or `lead == true` | 15% of base |
| Quartet | `quartet == true` | 15% of base |
| Electronic | `electronic == true` | 25% of base |
| First Double | `doubles ≥ 1` | 25% of base |
| Additional Doubles | `doubles ≥ 2` | 10% per extra instrument |

### Doubles Category
Doubles premiums go into the **`doubles`** category total (separate from general `premium`).

### Vacation
Applies only when `vacation_eligible == true`.
```
vacation = (base_service_pay + all_premiums) × 0.04
```

### Weekly Guarantee Adjustment
Applies to **regular** (non-substitute) musicians whose base service pay is below `weekly_guarantee` (2082.00).
```
guarantee_adjustment = weekly_guarantee - base_service_pay
```

### Substitutes
- Get **only** base service pay (no premiums, no vacation, no guarantee adjustment).
- `substitute_adjustment` in category totals is 0.0 when no explicit substitute adjustment rule exists.

### Conflict Flags (CBA)
Detected from schedule data. Collect into a set, then sort alphabetically.

| Flag | Condition |
|------|-----------|
| `REHEARSAL_EARLY_START` | Rehearsal start time < 09:00 |
| `REHEARSAL_LATE_END` | Rehearsal end time > 18:30 |
| `SERVICE_OVER_TIME_LIMIT` | Actual duration > service time limit (Rehearsal: 5.0h, Performance: 3.0h, Audit: 3.0h, Sound Check: 1.0/2.0h) |
| `SOUND_CHECK_DURATION_MISMATCH` | 1hr Sound Check duration ≠ 1.0h, or 2hr Sound Check duration ≠ 2.0h |

### Service Counts (normalized)
- `1hr Sound Check` and `2hr Sound Check` both count under the `sound_check` key.
- Other types use the lowercased service type name: `performance`, `audit`, `rehearsal`.

### Per-Musician Output
- `categories` map includes **only nonzero** category amounts.
- Order by `musician_id` ascending.
- Top-paid musician is the one with the highest `total`.

---

## Common Pitfalls

1. **Rounding reconciliation**: Round per-musician category amounts **before** aggregating into category totals. Then round the totals. Then compute `weekly_total` as `sum(category_totals)`. This prevents 1-cent mismatches.

2. **Combined overscale**: When `combined_overscale_includes_title == true`, skip the Titled Position Premium for that employee. The overscale amount already embeds the title premium. This flag is set per employee, not per ensemble.

3. **Seniority band bounds**: The seniority band `max_years` can be `null` (meaning unlimited upper bound). Always check for `null` — do not use `≤ null` which would fail in some languages.

4. **Period mapping**: M1–M12 = FY2024, M13–M24 = FY2025. Never hardcode; always derive from `/api/finance/period-map` if available, but the convention above is fixed per the seed.

5. **Forecast compounding**: Year+2 builds on Year+1 values (compounding), not on the base year. Using independent growth from base will produce Year+2 totals that are lower than Year+1 when the second-year growth rate is smaller — a clear sign of error.

6. **Substitute handling in payroll**: Substitutes receive zero premiums, zero vacation, and zero guarantee adjustment. Their `categories` map will typically only contain `performance` and/or `audit` keys. Do not apply doubles or electronic premiums to substitutes.

7. **ARPU denominator**: Use the **sum** of monthly `active_customers` counts (customer-months), not the average. Same pattern for `sales_per_labor_headcount` using the sum of monthly `labor_headcount`.

8. **Empty/list fields**: Category totals in payroll must include all expected keys even if the value is 0.0 (e.g. `substitute_adjustment: 0.0`). `per_musician.categories`, however, includes only nonzero keys.

9. **Income statement completeness**: Every income statement block (`m24_income_statement`, `fy2025`, `fy2024`) needs all six line items: revenue, cogs, gross_margin, sga, allocations, ebitda. Compute each independently (don't just aggregate — derive gross_margin and ebitda from their components).

10. **Sorting order**: Branch IDs sort lexicographically (e.g. `BR-010` comes before `BR-002`? No — `BR-001` through `BR-012` sort naturally by the numeric part. When in doubt, sort by the full string.)
