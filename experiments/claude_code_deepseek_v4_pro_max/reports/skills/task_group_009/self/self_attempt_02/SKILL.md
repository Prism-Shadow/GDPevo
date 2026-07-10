# Crescent Finance Ops — Transferable Skill Reference

## Environment

```
BASE = http://34.46.77.124:8009
```

Always use HTTP (not HTTPS). Call `GET /health` first to validate connectivity. The `/api/manifest` endpoint lists all available endpoints and public entity summaries (branch names, ensemble names, production titles).

## API Reference

| Domain | Endpoint | Returns |
|--------|----------|---------|
| Finance | `/api/finance/branches` | Branch list with region mappings |
| Finance | `/api/finance/period-map` | Period-to-fiscal-year mapping |
| Finance | `/api/finance/accounts` | Chart of accounts with categories |
| Finance | `/api/finance/records` | Account values by branch × period |
| Compensation | `/api/compensation/rate-book` | Pay rates, seniority bands, quarter weeks |
| Compensation | `/api/compensation/rosters` | Employee roster per ensemble |
| Compensation | `/api/compensation/scenarios` | Forecast growth scenarios |
| Payroll | `/api/payroll/rate-book` | Service rates, premiums, conflict thresholds |
| Payroll | `/api/payroll/productions` | Production schedules and musician rosters |

---

## 1. Period Convention

The period map uses M1–M24 with fiscal years:

| Period Range | Fiscal Year |
|-------------|-------------|
| M1 – M12    | FY2024      |
| M13 – M24   | FY2025      |

When asked for "current close period", translate M_N_ → month_name (from period map) → FY_YYYY_ (from period map). When asked for "current fiscal year", sum across all periods whose fiscal_year matches the target year.

---

## 2. Income Statement Components (Finance)

Every component aggregates the **branch's records across one or more account+period cells**.

### Revenue
```
Revenue = product_revenue + service_revenue
```

### COGS
```
COGS = direct_materials_cogs + direct_labor_cogs
```

### Gross Margin
```
Gross Margin = Revenue − COGS
```

### SG&A
```
SG&A = sales_sga + admin_sga + occupancy_sga
```

### Allocations
```
Allocations = shared_service_allocations
```

### EBITDA
```
EBITDA = Gross Margin − SG&A − Allocations
```

### EBITDA Margin
```
EBITDA Margin = EBITDA / Revenue
```
Always round to 4 decimals.

### ARPU (Average Revenue per Unit)
```
ARPU = Revenue / Σ(revenue_units over the period range)
```
`revenue_units` is an operating account. Sum its values across **all periods in the range**, then divide. Round to 2 decimals.

### Sales per Labor Headcount
```
Sales per Labor Headcount = Revenue / Σ(labor_headcount over the period range)
```
Same approach: sum `labor_headcount` across the period range. Round to 2 decimals.

---

## 3. Variance and Growth (Finance)

### Month-over-Month Revenue Variance
```
amount = Rev_current_period − Rev_prior_period
pct    = amount / Rev_prior_period          # if denominator ≠ 0
```
Round `amount` to 2 decimals, `pct` to 4 decimals.

### Fiscal-Year Revenue Growth
```
Revenue Growth = (FY2025_Rev − FY2024_Rev) / FY2024_Rev
```

### Fiscal-Year EBITDA Growth
```
EBITDA Growth = (FY2025_EBITDA − FY2024_EBITDA) / FY2024_EBITDA
```
Round growth rates to 4 decimals.

---

## 4. Branch and Regional Context (Finance)

### Branch Rankings
Use **all 12 branches** unless the task scopes to a specific region.

- **Sales growth rank (descending)**: Rank all branches by `(FY2025_Rev − FY2024_Rev) / FY2024_Rev`, highest first. Rank 1 = highest growth.
- **Top sales growth branch**: The branch_id at rank 1.
- **Top ARPU branch**: Compute ARPU for all branches (FY2025); highest wins.
- **EBITDA rank within region (descending)**: Rank only branches sharing the target's `region_id`. Rank 1 = highest FY2025 EBITDA.
- **Top / bottom EBITDA branch in region**: Highest and lowest FY2025 EBITDA among region branches.

### Region Aggregation
When computing region totals, sum branch-level values across all branches in that region. Use `GET /api/finance/branches` to determine which `branch_id`s belong to a `region_id`.

### Region Reconciliation Variance
Since all data comes from the same branch-level records, region totals computed by summing branch contributions are internally consistent. If a reconciliation variance field is required, it is typically **0.00** (no discrepancy between aggregate and sum-of-parts).

---

## 5. Compensation — Rate Book Mechanics

### Key Constants (from `/api/compensation/rate-book`)
- `minimum_weekly_scale` (e.g., 2520.00) — the base weekly pay
- `quarter_weeks` — standard weeks per quarter (Q1=13, Q2=13, Q3=13, Q4=13)
- `seniority_weekly` — array of bands: `{min_years, max_years, weekly_amount}`
- `title_premium_pct` — map from title string to decimal multiplier
- `current_year` — integer year
- `pay_types` — ordered list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`

### Per-Employee Compensation Formula
For each employee in the roster:

#### 1. Minimum Weekly Scale
```
MWS = minimum_weekly_scale × weeks_in_quarter
```

#### 2. Titled Position Premium
```
IF combined_overscale_includes_title:
    Title Premium = 0
ELSE:
    Title Premium = minimum_weekly_scale × title_premium_pct[title] × weeks_in_quarter
```
**Critical rule**: When `combined_overscale_includes_title` is `true`, the title premium is baked into overscale and must NOT be added separately. If `false`, add the title premium independently.

#### 3. Seniority
Look up `years_of_service` in the `seniority_weekly` bands (inclusive on both ends, `max_years: null` means no upper bound):
```
seniority_weekly_amount = band.weekly_amount (from matching band)
Seniority = seniority_weekly_amount × weeks_in_quarter
```

#### 4. Overscale
```
Overscale = overscale_weekly × weeks_in_quarter
```

### Quarter Totals
Sum all employees' total comp per quarter (Q1, Q2, Q3, Q4).

### Annual Pay Type Totals
Sum each pay type component across ALL employees and ALL quarters. Use the pay type order from the rate book.

### Annual Total
Sum of all four pay type totals. (Must equal sum of quarter totals.)

### Largest Pay Type
The pay type string with the highest annual total.

### Roster Counts

- **combined_overscale_employee_count**: Count employees where `combined_overscale_includes_title` is `true`.
- **partial_quarter_employee_count**: Count employees who have **any** quarter with `weeks < 13` (the standard `quarter_weeks` value).

---

## 6. Compensation — Forecast Mechanics

### Scenario Structure (from `/api/compensation/scenarios`)
Each scenario has `year_plus_1` and `year_plus_2` blocks containing:
- `mws_growth` — decimal growth rate for MWS
- `overscale_growth` — decimal growth rate for overscale
- `seniority_growth` — decimal growth rate for seniority amounts
- `title_pct_multiplier` — multiplier on the base title premium percentage

### Forecast Year Computation

#### Current Year
Use rate book and roster as-is (no growth, no service-year adjustment).

#### Year + 1
1. Add **1** to each employee's `years_of_service`
2. Look up the seniority band with the adjusted years → get base `weekly_amount`
3. Apply growth to each component:
   - Adjusted MWS = `minimum_weekly_scale × (1 + mws_growth)`
   - Adjusted Seniority = `base_weekly_amount × (1 + seniority_growth)`
   - Adjusted Overscale = `overscale_weekly × (1 + overscale_growth)`
   - Adjusted Title Pct = `title_premium_pct[title] × title_pct_multiplier`
4. Compute per-employee per-quarter comp using adjusted values

#### Year + 2
Same process but add **2** years for service and use the `year_plus_2` growth values.

**Important**: Growth factors apply to the **base** rate book values, not compounded from Year+1. Each forecast year independently derives from the base.

### Growth Rates in Output
```
year_plus_1_vs_current = (Y1_total − current_total) / current_total
year_plus_2_vs_year_plus_1 = (Y2_total − Y1_total) / Y1_total
```
Round to 4 decimals.

### Largest Growth Pay Type
Compare each pay type's **dollar increase** from current to Year+2. The pay type with the largest absolute growth wins. Report the pay type string from the rate book's `pay_types` list.

---

## 7. Payroll — Rate Book Mechanics

### Service Rates (per-service, `/api/payroll/rate-book`)
- **Performance**: flat per-service rate
- **Audit**: flat per-service rate
- **Sound Check** (1hr / 2hr): flat per-service rate
- **Rehearsal**: hourly rate with a **3-hour minimum call**

```
IF service_type == "Rehearsal":
    pay = rehearsal_hourly_rate × MAX(3.0, duration_hours)
ELSE:
    pay = service_rate
```

### Premium Percentages
| Premium Type | Rate | Trigger |
|---|---|---|
| principal_or_lead | 15% | `principal` OR `lead` is `true` |
| quartet | 15% | `quartet` is `true` |
| electronic | 25% | `electronic` is `true` |
| concertmaster | 20% | (if musician has a concertmaster attribute) |
| first_double | 25% | `doubles` ≥ 1 |
| additional_double | 10% | `doubles` ≥ 2, per extra beyond first |

**All premiums are applied to the musician's total base service pay** (the sum of all their assigned service pays). Premiums are NOT per-service.

### Doubles Premium
```
IF doubles >= 1:
    doubles_premium = base × 0.25
IF doubles >= 2:
    doubles_premium += base × 0.10 × (doubles − 1)
```

### Vacation
```
IF vacation_eligible:
    vacation = 0.04 × (base_service_pay + position_premiums + doubles_premiums)
```
Vacation is 4% of base pay **plus all premiums** (both position premiums and doubles).

### Weekly Guarantee Adjustment
```
IF NOT substitute AND base_service_pay < weekly_guarantee:
    guarantee_adjustment = weekly_guarantee − base_service_pay
ELSE:
    guarantee_adjustment = 0
```
Substitute players never receive guarantee adjustments.

### Substitute Adjustment
The rate book does not define a substitute-specific rate or penalty. Unless explicitly defined in the rate book, `substitute_adjustment` is **0.00**.

---

## 8. Payroll — Category Taxonomy

Categories are **mutually exclusive** — each dollar goes to exactly one category:

| Category | What goes in it |
|---|---|
| `performance` | Base pay for Performance services |
| `audit` | Base pay for Audit services |
| `rehearsal` | Base pay for Rehearsal services (after 3-hr minimum) |
| `sound_check` | Base pay for 1hr/2hr Sound Check services |
| `premium` | Position premiums: principal/lead + quartet + electronic + concertmaster |
| `doubles` | Doubling premiums: first_double + additional_double |
| `vacation` | Vacation pay (4% of base + premiums) |
| `guarantee_adjustment` | Top-up to weekly guarantee |
| `substitute_adjustment` | Substitute surcharge (0.00 unless rate book defines one) |

**Critical**: "premium" and "doubles" are separate non-overlapping categories. Position premiums go in "premium"; instrument doubling premiums go in "doubles". They combine for the vacation calculation base but are reported separately.

### Category Totals
Sum each category across all musicians. Only include the keys defined in the output template.

### Per-Musician Output
Order by `musician_id` ascending. For each musician, output only **nonzero** categories. The `total` field is the musician's full weekly pay (sum of all categories).

### Service Counts
Count occurrences of each `service_type` string in the production schedule (not per-musician). One schedule entry = one service count.

### Top Paid Musician
The `musician_id` with the highest total weekly pay.

---

## 9. Payroll — Conflict Flags

Evaluate against the schedule, not the roster. A flag is included at most once (deduplicate), then **sorted alphabetically**.

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any Rehearsal service `start_time < "09:00"` |
| `REHEARSAL_LATE_END` | Any Rehearsal service `end_time > "18:30"` |
| `SERVICE_OVER_TIME_LIMIT` | Any service `duration_hours > service_time_limits[service_type]` |
| `SOUND_CHECK_DURATION_MISMATCH` | Any Sound Check service `duration_hours ≠ service_time_limits[service_type]` |

Time comparisons use string comparison (HH:MM format). Duration comparisons use numeric float.

---

## 10. Output Conventions

### Rounding
| Field type | Round to |
|---|---|
| Currency | 2 decimals |
| Percent / ratio | 4 decimals |
| Integer counts | No rounding needed |

Always round the **final output value**, not intermediate values. Use standard `round(value, N)`.

For payroll: round each per-musician `total` to 2 decimals, and round per-musician `categories` values to 2 decimals. Sum unrounded values across musicians before rounding `category_totals` — this avoids rounding drift. Each musician's `total` must equal the sum of their category values after rounding both.

### Ordering
- **Branch IDs**: Ascending string sort (lexicographic, e.g., `BR-001` before `BR-002`)
- **Per-musician lists**: Ascending by `musician_id`
- **Conflict flags**: Alphabetical sort
- **Pay types**: Use the order from the rate book's `pay_types` array
- **Quarter totals**: Always Q1, Q2, Q3, Q4 order
- **Rank fields**: When a rank says "desc", rank 1 = highest/best. Follow template naming.

### JSON Conventions
- All values are numbers (not strings), except IDs and labels
- Omit keys that are conditional (e.g., `substitute_adjustment` can be 0)
- Include all non-conditional required keys, even if 0.00

---

## 11. Common Pitfalls

1. **Revenue has TWO accounts**: Don't forget `service_revenue` when summing product revenue.

2. **COGS and SG&A are multi-account**: COGS = materials + labor; SG&A = sales + admin + occupancy.

3. **EBITDA ≠ Revenue − COGS − SG&A**: Must also subtract Allocations (shared_service_allocations).

4. **Pre-compute before ranking**: ARPU, growth rates, and EBITDA all require computing the full numerator and denominator BEFORE ranking. Don't rank on partial data.

5. **ARPU / SPLH denominators**: Sum the operating metric (revenue_units / labor_headcount) across the ENTIRE period range before dividing. Don't average monthly ratios.

6. **Rehearsal 3-hour minimum**: Always apply `MAX(3.0, duration_hours)` to rehearsal pay. This is hourly, not per-service.

7. **Combined overscale suppresses title premium**: When `combined_overscale_includes_title` is `true`, the title_premium component is exactly zero for that employee.

8. **Forecast years adjust service years FIRST**: Add 1 (or 2) years to `years_of_service` BEFORE looking up the seniority band. Then apply the seniority growth factor to the band amount.

9. **"premium" ≠ "doubles"**: These are distinct non-overlapping payroll categories. Position-based premiums (principal, lead, quartet, electronic, concertmaster) go in "premium". Instrument doubling premiums go in "doubles".

10. **Guarantee excludes substitutes**: Only non-substitute players whose base service pay falls below the weekly_guarantee threshold receive a guarantee adjustment.

11. **Partial quarter detection**: Compare each quarter's weeks against the rate book's `quarter_weeks` value (13), not against a hardcoded number.

12. **Sound check naming**: Both "1hr Sound Check" and "2hr Sound Check" map to the category key `sound_check`. Merge them when building category totals and per-musician categories.

13. **Region reconciliation**: Branch-level data is the source of truth. Region totals are the sum of branch totals. Reconciliation variance should be 0.00.

14. **Conflict flags are schedule-level, not musician-level**: Check the production schedule, not individual musician assignments.

15. **Growth rate sign**: EBITDA can be negative. If the prior period EBITDA was negative, growth rate interpretation becomes tricky. Use the standard formula but be careful about sign conventions.
