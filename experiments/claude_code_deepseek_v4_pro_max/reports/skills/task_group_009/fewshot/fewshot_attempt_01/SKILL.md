# Crescent Finance Ops — Solver Skill

## Environment & API Base URL

Use the base URL from `environment_access.md` (HTTP, not HTTPS). If a payload references `localhost` or `127.0.0.1`, override it with the remote URL from `environment_access.md`.

### Key endpoints

| Domain | Endpoint | Returns |
|--------|----------|---------|
| Finance | `/api/finance/branches` | Branch metadata (id, name, region_id) |
| Finance | `/api/finance/period-map` | M1–M24 → fiscal year mapping |
| Finance | `/api/finance/accounts` | Chart of accounts (account, category, metric_type) |
| Finance | `/api/finance/records` | Time-series values by branch × account × period |
| Compensation | `/api/compensation/rate-book` | Scale rates, seniority bands, title premiums, business rules |
| Compensation | `/api/compensation/rosters` | Employee roster with titles, seniority, overscale, quarter weeks |
| Compensation | `/api/compensation/scenarios` | Forecast growth factors per scenario |
| Payroll | `/api/payroll/rate-book` | Service rates, premium pcts, thresholds, guarantee, business rules |
| Payroll | `/api/payroll/productions` | Production schedules + musician rosters with service assignments |

All endpoints return JSON arrays (except `period-map`) and require no query parameters.

---

## Period Convention

M1–M12  → **FY2024**
M13–M24 → **FY2025**

The `period-map` endpoint confirms this mapping. Always derive the fiscal year from this mapping; do not hardcode.

---

## Domain 1: Branch Close & Regional Reporting (Finance API)

### Chart of Accounts & P&L Construction

| Line item | Accounts to sum |
|-----------|----------------|
| **Revenue** | `product_revenue` + `service_revenue` |
| **COGS** | `direct_materials_cogs` + `direct_labor_cogs` |
| **Gross Margin** | Revenue − COGS |
| **SG&A** | `sales_sga` + `admin_sga` + `occupancy_sga` |
| **Allocations** | `shared_service_allocations` |
| **EBITDA** | Gross Margin − SG&A − Allocations |

### Operating metrics (count-type accounts)

| Metric | Formula |
|--------|---------|
| **ARPU** | Revenue ÷ sum of `active_customers` over the period |
| **Sales per Labor Headcount** | Revenue ÷ sum of `labor_headcount` over the period |
| **EBITDA Margin** | EBITDA ÷ Revenue |

Both count-type and currency-type accounts use the same `values` dict keyed by period (M1…M24). For fiscal-year metrics, **sum all 12 monthly values** — do not average counts.

### MoM (Month-over-Month) Variance

```
amount = current_period_revenue − prior_period_revenue
pct    = amount ÷ prior_period_revenue
```

### FY Growth Rates

```
revenue_growth_pct = (FY2025_revenue − FY2024_revenue) ÷ FY2024_revenue
ebitda_growth_pct  = (FY2025_ebitda  − FY2024_ebitda)  ÷ FY2024_ebitda
```

### Branch Rankings

Compute the relevant metric (revenue growth, ARPU, EBITDA) for **every branch** (all 12). Rankings are 1-indexed and descending (rank 1 = highest).

- **sales_growth_rank_desc**: rank of the target branch among all branches by `(FY2025_revenue − FY2024_revenue) ÷ FY2024_revenue`.
- **top_sales_growth_branch_id**: branch with the highest sales growth.
- **top_arpu_branch_id**: branch with the highest FY2025 ARPU.

### Region Context

- `region_id` and `branch_ids`: from the branches endpoint; list branch_ids in **ascending** order.
- `fy2025_ebitda`: sum of FY2025 EBITDA for all branches in the region.
- `ebitda_rank_desc`: rank of the target branch by FY2025 EBITDA **within its region only** (1 = highest EBITDA in region).

### Region Reconciliation

When building a regional report, compute region totals by **summing branch-level values directly** (not from a separate API source). Record the reconciliation variance as the difference between the computed region total and any alternate source; if values tie exactly, variance is `0.00`.

---

## Domain 2: Compensation Summary (Compensation API)

### Rate Book Reference

| Field | Meaning |
|-------|---------|
| `minimum_weekly_scale` | Base weekly pay per musician (always applied) |
| `seniority_weekly` | Array of bands `[{min_years, max_years, weekly_amount}]`; both bounds are **inclusive** (`min_years ≤ yos ≤ max_years`) |
| `title_premium_pct` | Map of title → percentage of MWS: `Concertmaster=0.22`, `Principal=0.20`, `Section Lead=0.15`, `Assistant Principal=0.10`, `Associate Principal=0.10` |
| `quarter_weeks` | Default weeks per quarter (normally `{Q1:13, Q2:13, Q3:13, Q4:13}`) |
| `current_year` | The integer year for "current" calculations |
| `pay_types` | Ordered list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]` |

### Per-Employee Compensation Formula

For each employee in the roster for the requested ensemble, compute per quarter:

```
quarter_weeks = employee.weeks_by_quarter[quarter]  // use actual roster weeks, not default

mws_pay    = minimum_weekly_scale × quarter_weeks

title_pay  = IF employee.title IS NOT NULL
             AND employee.combined_overscale_includes_title == false
             THEN minimum_weekly_scale × title_premium_pct[employee.title] × quarter_weeks
             ELSE 0

seniority_pay = seniority_weekly_band(employee.years_of_service).weekly_amount × quarter_weeks

overscale_pay = employee.overscale_weekly × quarter_weeks
```

**Critical rule**: When `combined_overscale_includes_title` is `true`, do **not** add a separate Titled Position Premium. The overscale weekly amount already embeds it.

**Seniority band lookup**: Find the band where `min_years ≤ years_of_service ≤ max_years` for bounded bands, or `years_of_service ≥ min_years` for the last band with `max_years: null`. Both ends are inclusive: years 0–4 map to `0.0`, years 5–9 map to `48.0`, etc.

### Quarterly & Annual Totals

- `quarter_totals[Q]` = sum of (mws_pay + title_pay + seniority_pay + overscale_pay) across all employees for that quarter.
- `annual_pay_type_totals[pay_type]` = sum of that pay component across all employees and all four quarters.
- `annual_total` = sum of `quarter_totals` across Q1–Q4, or equivalently sum of `annual_pay_type_totals`.

### Roster Counts

- `roster_count`: total number of employee entries in the roster array for the ensemble.
- `combined_overscale_employee_count`: count of employees where `combined_overscale_includes_title == true`.
- `partial_quarter_employee_count`: count of employees where **any** quarter's `weeks_by_quarter` differs from another quarter (i.e., the employee has a non-uniform quarter schedule). Typically identified by notes mentioning "Partial-quarter service schedule."

### Largest Pay Type

The `largest_pay_type` is the pay type with the largest `annual_pay_type_totals` value. Enum: `"Minimum Weekly Scale"`, `"Titled Position Premium"`, `"Seniority"`, `"Overscale"`.

---

## Domain 3: Compensation Forecast (Compensation API + Scenarios)

### Forecast Flow

1. Compute the **current-year** compensation totals using the rate book and roster (same as Domain 2).
2. For **Year + 1**: apply the scenario's `year_plus_1` growth factors to the current-year compensation components. Also **add 1 year** to each employee's `years_of_service` before re-assigning the seniority band.
3. For **Year + 2**: apply the scenario's `year_plus_2` growth factors. Also **add 2 years** (from current) to each employee's `years_of_service` before re-assigning the seniority band.

### Applying Growth Factors

Each scenario provides growth factors for both forecast years:

```
year_plus_N: {
    mws_growth,          // year-over-year growth multiplier for Minimum Weekly Scale
    overscale_growth,     // year-over-year growth multiplier for Overscale
    seniority_growth,     // year-over-year growth multiplier for Seniority weekly amounts
    title_pct_multiplier  // multiplier for title_premium_pct values
}
```

**Growth factors are compounded sequentially**, not applied independently. Compute Y+1 first using the Y+1 factors applied to current rates. Then compute Y+2 by applying the Y+2 factors to the Y+1 results.

Concretely:
- **Y+1 MWS rate** = `current_mws × (1 + y1_mws_growth)`
- **Y+2 MWS rate** = `y1_mws_rate × (1 + y2_mws_growth)` = `current_mws × (1 + y1_mws_growth) × (1 + y2_mws_growth)`

The same compounding applies to overscale and seniority growth rates. Title multiplier is also cumulative: `title_pct × y1_title_pct_multiplier × y2_title_pct_multiplier`.

For each forecast year:
- **MWS**: multiply the compounded base rate by quarter weeks.
- **Overscale**: `employee.overscale_weekly × compounded_growth_factor × weeks`.
- **Seniority**: use the seniority band from the **adjusted** years of service, then `band.weekly_amount × compounded_growth_factor × weeks`.
- **Title Premium**: `current_mws × compounded_growth_factor × title_premium_pct[title] × cumulative_title_multiplier × weeks`.

### Annual Totals & Growth Rates

```
annual_totals.current     = computed from current rate book + roster (current YoS)
annual_totals.year_plus_1 = computed with Y+1 compounded factors + YoS+1
annual_totals.year_plus_2 = computed with Y+2 compounded factors (on top of Y+1) + YoS+2

growth_rates.year_plus_1_vs_current    = (Y+1 − current) ÷ current
growth_rates.year_plus_2_vs_year_plus_1 = (Y+2 − Y+1) ÷ Y+1
```

Note: For YoS, add +1 from current for Y+1, and +2 from current for Y+2 (not cumulative YoS).

### Year + 2 Detail

- `year_plus_2_quarter_totals`: Q1–Q4 totals using Y+2 factors and YoS+2.
- `year_plus_2_pay_type_totals`: pay-type breakdown for Y+2.
- `largest_growth_pay_type`: the pay type with the largest **absolute growth** in annual total from current to Y+2. Compute `Y+2_pay_type_total − current_pay_type_total` for each pay type and pick the largest positive delta.

### Roster Counts (same definitions as Domain 2)

---

## Domain 4: Weekly Payroll Review (Payroll API)

### Service Rates

From the rate book:
- **Performance**: flat `$260.25` per service
- **Audit**: flat `$260.25` per service
- **Rehearsal**: `$58.75` per **hour** with a **3-hour minimum call** (pay = `max(duration_hours, 3) × 58.75`)
- **1hr Sound Check**: flat `$80.00` per service
- **2hr Sound Check**: flat `$142.50` per service

### Premiums

Premiums are percentages of the musician's **base service pay** for the relevant service. Apply premiums per service, not once globally.

| Premium flag | Rate | When |
|-------------|------|------|
| `concertmaster` | 20% | musician has concertmaster role |
| `principal_or_lead` | 15% | `principal == true` or `lead == true` |
| `quartet` | 15% | `quartet == true` |
| `electronic` | 25% | `electronic == true` |
| `first_double` | 25% | `doubles ≥ 1` |
| `additional_double` | 10% | `doubles ≥ 2`, applied per extra instrument beyond the first |

**Doubles premiums are additive**: a musician with `doubles=2` receives `25% + 10% = 35%` on each service. A musician with `doubles=3` receives `25% + 10% + 10% = 45%`.

### Vacation

If `vacation_eligible == true`: vacation = `4% × (base_service_pay + sum_of_all_premiums)`. Compute after premiums, not before.

### Guarantee Adjustment

For musicians who are **guaranteed regular players** (not substitutes): if their total base service pay (before premiums and vacation) is below `weekly_guarantee` (default `$2,082.00`), the guarantee adjustment = `weekly_guarantee − base_service_pay`. Report this under category `guarantee_adjustment`.

### Substitute Adjustment

Substitute musicians (where `substitute == true`) receive a **substitute_adjustment** equal to the total base service pay they would have earned on their assigned services at the standard service rates. This is reported under category `substitute_adjustment`. (Substitutes do not receive the standard guarantee adjustment.)

### Category Totals

Sum each pay category across all musicians. Categories are: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`.

Report only categories that have a nonzero total.

### Service Counts

Count each type of scheduled service across the production schedule. Map service types to labels:
- `"Performance"` → `"Performance"`
- `"Audit"` → `"Audit"`
- `"Rehearsal"` → `"Rehearsal"`
- `"1hr Sound Check"` → `"1hr Sound Check"`
- `"2hr Sound Check"` → `"2hr Sound Check"`

### Per-Musician Output

- Ordered by `musician_id` ascending.
- Each entry: `musician_id`, `name`, `total` (sum of all categories), and `categories` (object with only nonzero category amounts).
- `top_paid_musician_id`: the `musician_id` with the highest `total` (if tied, use ascending ID order as tiebreaker).

### Conflict Flags

Check the production schedule against these thresholds from the rate book:

| Flag | Condition |
|------|-----------|
| `REHEARSAL_EARLY_START` | Any rehearsal service with `start_time` before `rehearsal_earliest_start` (09:00) |
| `REHEARSAL_LATE_END` | Any rehearsal service with `end_time` after `rehearsal_latest_end` (18:30) |
| `SERVICE_OVER_TIME_LIMIT` | Any service whose `duration_hours` exceeds its type's `service_time_limits` entry |
| `SOUND_CHECK_DURATION_MISMATCH` | A sound check service whose `duration_hours` does not match its labeled duration (e.g., a `"1hr Sound Check"` with `duration_hours ≠ 1.0`) |

Output `conflict_flags` as an alphabetically sorted list. Include only flags that are triggered.

---

## Rounding & Formatting Conventions

| Type | Rounding | Example |
|------|----------|---------|
| Currency amounts | **2 decimal places** | `293306.29` |
| Percentages & ratios | **4 decimal places** | `0.0138`, `0.2459` |
| Growth rates | **4 decimal places** | `0.0966` |

Use standard rounding (round half-up or half-even — the data is constructed so borderline cases don't arise).

## List Ordering Conventions

| Context | Order |
|---------|-------|
| `branch_ids` | Ascending string order (e.g., `BR-004` before `BR-005`) |
| `pay_types` | As given by the rate book: `"Minimum Weekly Scale"`, `"Titled Position Premium"`, `"Seniority"`, `"Overscale"` |
| `per_musician` | Ascending by `musician_id` |
| `conflict_flags` | Alphabetically sorted |

---

## Common Pitfalls

1. **Port override**: The payload's `environment_access.json` may reference `localhost:8047`; always use the remote base URL from `environment_access.md` instead.

2. **Period convention**: M1–M12 = FY2024, M13–M24 = FY2025. Do not assume calendar-year quarters — quarters are fiscal and defined by the rate book's `quarter_weeks` plus roster `weeks_by_quarter`.

3. **Count metrics**: For FY totals, **sum** count-type accounts (like `active_customers`, `labor_headcount`) across all 12 months of the fiscal year for the denominator of ARPU and Sales-per-Labor-Headcount. Do not average them.

4. **Rehearsal minimum call**: Rehearsal pay = `$58.75 × max(duration_hours, 3.0)`, even if the scheduled duration is shorter.

5. **Combined overscale**: When `combined_overscale_includes_title == true`, do **not** add a separate Titled Position Premium. The overscale amount already covers it.

6. **Seniority band boundaries**: Bands are `[min_years, max_years]` — **inclusive** on both ends. For example, years 0–4 → `$0.00`, years 5–9 → `$48.00`, years 10–14 → `$82.00`. The last band has `max_years: null` and applies to all years ≥ `min_years`.

7. **Forecast years of service**: Add years of service (+1 for Y+1, +2 for Y+2 from current) **before** looking up the seniority band for that forecast year. The forecast growth factor is then applied to the band's weekly amount. Forecast growth rates compound sequentially: Y+2 rates build on Y+1 rates, not on current rates independently.

8. **Vacation calculation order**: Vacation = `4% × (base_service_pay + premiums)`. Compute premiums first, then add vacation on top.

9. **Guarantee adjustment eligibility**: Only non-substitute (`substitute == false`) musicians can receive a guarantee adjustment. Substitute musicians receive a substitute adjustment instead.

10. **Conflict flag checking**: Check every service in the schedule, not just the ones assigned to a particular musician. A flag is raised if **any** service violates the threshold.

11. **Region reconciliation**: When computing region totals, sum the branch-level values (do not rely on a separate region endpoint). The variance is the difference between this sum and any reported total — it should be `0.00` if reconciled correctly.

12. **Sound check duration mismatch**: Compare the actual `duration_hours` against the nominal hours in the service type name (e.g., `"1hr Sound Check"` → 1.0, `"2hr Sound Check"` → 2.0). Flag if they differ.
