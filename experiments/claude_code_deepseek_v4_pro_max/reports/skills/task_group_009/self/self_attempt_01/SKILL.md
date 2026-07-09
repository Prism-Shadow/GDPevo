# Crescent Finance Ops — Solver Skill

## Environment

All API calls use HTTP against the remote base URL from `environment_access.md` / `payloads/environment_access.json`. Each task payload contains a `base_url` field that may reference localhost; **ignore it** — use the remote URL from `environment_access.md` instead.

**Remote base:** `http://<host>:<port>` (see `environment_access.md`).

Verify connectivity with `GET /health` → `{"status":"ok"}`.

---

## Finance Ops — Branch & Regional Reporting

### Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/finance/branches` | All 12 branches with `branch_id`, `branch_name`, `region_id`, `region_name` |
| `GET /api/finance/period-map` | Period-to-FY mapping: M1–M12 = FY2024, M13–M24 = FY2025 |
| `GET /api/finance/accounts` | 14 accounts with `account`, `category`, `display_name`, `metric_type` |
| `GET /api/finance/records` | 168 records: for each `(account, branch_id)` a dict of `{period: value}` |

### Account Categories

| Account | Category | Used For |
|---|---|---|
| `product_revenue` | revenue | Revenue |
| `service_revenue` | revenue | Revenue |
| `direct_materials_cogs` | cogs | COGS |
| `direct_labor_cogs` | cogs | COGS |
| `sales_sga` | sga | SG&A |
| `admin_sga` | sga | SG&A |
| `occupancy_sga` | sga | SG&A |
| `shared_service_allocations` | allocations | Allocations |
| `orders` | operating | Operating metrics |
| `revenue_units` | operating | Operating metrics |
| `active_customers` | operating | ARPU denominator |
| `labor_headcount` | operating | Sales-per-labor denominator |
| `admin_headcount` | operating | Operating metrics |
| `backlog` | operating | Operating metrics |

### Income Statement Formulas

```
revenue     = product_revenue + service_revenue
cogs        = direct_materials_cogs + direct_labor_cogs
gross_margin = revenue - cogs
sga         = sales_sga + admin_sga + occupancy_sga
ebitda      = gross_margin - sga - shared_service_allocations
ebitda_margin = ebitda / revenue
arpu        = revenue / sum(active_customers over all periods in scope)
sales_per_labor_headcount = revenue / sum(labor_headcount over all periods in scope)
```

### Period Conventions

- **Single month:** lookup `records[account][branch_id].values[period]`. Example: M24 is the current close period (Dec FY2025), M23 is the prior period (Nov FY2025).
- **Fiscal year aggregates:** sum all 12 periods in the fiscal year.
  - FY2024: M1 through M12
  - FY2025: M13 through M24
- **MoM variance:** `amount = current_revenue - prior_revenue`, `pct = amount / prior_revenue`.
- **period_convention output:** maps period ranges to fiscal year strings:
  - `M1_to_M12`: `"FY2024"`
  - `M13_to_M24`: `"FY2025"`
  - `current_month` / `prior_month`: use the period identifiers (e.g. `"M24"`, `"M23"`)

### ARPU and Sales-Per-Labor-Headcount

These are **FY-level ratios** only, not monthly. The denominators are **sums** of the headcount/customer counts over all periods in the fiscal year (not averages).

### Branch Rankings

- **Sales growth rank:** rank all 12 branches descending by FY2025/FY2024 revenue growth. Rank 1 = highest growth. Return the **1-based index** (not 0-based).
- **EBITDA rank within region:** rank branches in the same region descending by FY2025 EBITDA. Rank 1 = highest EBITDA. Return the 1-based index.
- **Top sales growth / top ARPU:** the branch_id at rank 1 of the respective descending sort.

### Region Context

- **Region branch IDs:** filter `GET /api/finance/branches` by `region_id`, sort ascending.
- **Region EBITDA:** sum FY2025 EBITDA of all branches in the region.
- **Reconciliation variance:** `region_ebitda - sum(branch_ebitda)`. Should be zero since records are additive by construction.

---

## Compensation Ops — Current-Year Summaries & Forecasts

### Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/compensation/rate-book` | MWS, seniority bands, title percentages, quarter weeks, business rules |
| `GET /api/compensation/rosters` | 109 roster rows across 4 ensembles with employee details |
| `GET /api/compensation/scenarios` | 4 forecast scenarios with year+1/year+2 growth rates |

### Rate Book Fields

- `minimum_weekly_scale` (e.g. 2520.00) — base MWS rate
- `quarter_weeks` — always `{"Q1":13, "Q2":13, "Q3":13, "Q4":13}` for current year
- `seniority_weekly` — list of bands: `{min_years, max_years, weekly_amount}`. `max_years: null` means unbounded upper.
- `title_premium_pct` — dict mapping title name to percentage (applied to MWS). Titles: Concertmaster (22%), Principal (20%), Section Lead (15%), Associate Principal (10%), Assistant Principal (10%).
- `current_year` — integer (e.g. 2026)
- `pay_types` — ordered list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `business_rules` — three critical rules (see below)

### Business Rules (exact text)

1. "Use roster quarter weeks, not a fixed 13-week quarter, when partial-quarter employees are listed."
2. "If combined_overscale_includes_title is true, do not add a titled position premium separately for that employee."
3. "For forecast years, add one year of service for Year + 1 and two years of service for Year + 2 before assigning seniority bands."

### Roster Fields

- `employee_id`, `ensemble_id`, `ensemble_name`
- `title` — string or `null`. Maps to `title_premium_pct` keys.
- `years_of_service` — integer for current year seniority band lookup
- `overscale_weekly` — additional weekly dollar amount
- `combined_overscale_includes_title` — if `true`, skip titled position premium for this employee
- `weeks_by_quarter` — `{Q1: N, Q2: N, Q3: N, Q4: N}`. Not always 13; partial quarters are possible.
- `notes` — string, sometimes empty

### Per-Employee Compensation Formula

For each employee, for each quarter:

```
mws_pay          = minimum_weekly_scale * quarter_weeks

title_pct        = title_premium_pct[title]  (0 if title is null)
title_pay        = minimum_weekly_scale * title_pct * quarter_weeks
                   ← SKIP entirely if combined_overscale_includes_title is true

seniority_weekly = seniority_weekly[band_for(years_of_service)]
seniority_pay    = seniority_weekly * quarter_weeks

overscale_pay    = overscale_weekly * quarter_weeks
```

Total for the quarter = mws_pay + title_pay + seniority_pay + overscale_pay.

### Seniority Band Lookup

Find the band where `min_years <= years_of_service <= max_years`. The `max_years: null` band matches all years ≥ `min_years`. The 0–4 year band has `weekly_amount: 0.0` (no seniority pay for junior employees).

### Treatment Counts

- **combined_overscale_employee_count:** count of roster rows where `combined_overscale_includes_title == true`. Count them even if `overscale_weekly` is 0.
- **partial_quarter_employee_count:** count of roster rows where any quarter has `weeks != 13`.

### Forecast (Multi-Year) Extensions

#### Scenario pull

Fetch `GET /api/compensation/scenarios`, select by `scenario_id`. Each scenario has `year_plus_1` and `year_plus_2` blocks, each containing:
- `mws_growth` — growth rate applied to base MWS
- `overscale_growth` — growth rate applied to each employee's `overscale_weekly`
- `seniority_growth` — growth rate applied to each band's `weekly_amount`
- `title_pct_multiplier` — multiplier on the title percentage (e.g. 1.0 = no change, 0.98 = reduce by 2%)

#### Forecast year computation

For each forecast year Y+1 or Y+2:

```
forecast_mws       = base_mws * (1 + scenario.mws_growth)
forecast_overscale = employee.overscale_weekly * (1 + scenario.overscale_growth)
forecast_seniority_bands = each band.weekly_amount * (1 + scenario.seniority_growth)
forecast_title_pct = base_title_pct * scenario.title_pct_multiplier
forecast_yos       = employee.years_of_service + offset (1 for Y+1, 2 for Y+2)
```

Then apply the per-employee formula using the forecast values.

**Critical:** Growth rates are applied to the base (current-year) values independently for each year, not compounded. The Y+2 rates are not applied on top of the Y+1 rates.

#### Largest growth pay type

Compute each pay type's absolute dollar growth from current year to Year+2: `Y2_pay_type_total - current_pay_type_total`. The type with the largest positive difference is the largest growth pay type. Return the enum value (e.g. `"Minimum Weekly Scale"`).

**Note:** This is based on **absolute dollar change**, not percentage growth. A pay type with a small base but large percentage change will not beat a large-base pay type with moderate percentage growth. Compare `Y+2_total - current_total` across all four pay types.

---

## Payroll Ops — Weekly Payroll Review

### Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, weekly guarantee |
| `GET /api/payroll/productions` | 17 productions, each with `schedule` and `roster` |

### Rate Book Fields

```
service_rates:
  Rehearsal:          58.75  (hourly)
  Performance:       260.25  (per service)
  Audit:             260.25  (per service)
  1hr Sound Check:    80.00  (per service)
  2hr Sound Check:   142.50  (per service)

premium_pct:
  principal_or_lead:  0.15
  electronic:         0.25
  quartet:            0.15
  concertmaster:      0.20
  first_double:       0.25
  additional_double:  0.10
  vacation:           0.04

conflict_thresholds:
  rehearsal_earliest_start: "09:00"
  rehearsal_latest_end:     "18:30"

service_time_limits:
  Rehearsal:          5.0
  1hr Sound Check:    1.0
  2hr Sound Check:    2.0

weekly_guarantee: 2082.00
```

### Business Rules (exact text)

1. "Service rates and premiums come from this rate book."
2. "Rehearsal pay is hourly with a three-hour minimum call."
3. "Performance, audit, and sound-check rates are per service."
4. "Premiums are applied to the musician's base service pay before vacation."
5. "The doubles premium is 25% for the first extra instrument and 10% for each additional extra instrument."
6. "Vacation is 4% of base service pay plus premiums when vacation_eligible is true."
7. "A weekly guarantee adjustment applies only to guaranteed regular players when base service pay is below weekly_guarantee."

### Production Structure

Each production has:
- `production_id`, `title`, `week_start`
- `schedule` — list of service objects: `{service_id, date, service_type, start_time, end_time, duration_hours}`
- `roster` — list of musician objects: `{musician_id, name, instrument, assigned_service_ids[], lead, principal, quartet, electronic, doubles, substitute, vacation_eligible}`

### Per-Service Pay Calculation

```
1. Base rate:
   - Rehearsal:      58.75 * max(3.0, duration_hours)
   - Performance:    260.25
   - Audit:          260.25
   - 1hr Sound Check: 80.00
   - 2hr Sound Check: 142.50

2. Premiums (non-doubles, computed on base rate):
   - principal_or_lead:  15% if principal==true OR lead==true
   - electronic:         25% if electronic==true
   - quartet:            15% if quartet==true
   - concertmaster:      20% if concertmaster==true (rare; never triggered in train data)
   All non-doubles premiums sum to a single premium pool.

3. Doubles premium (computed on base rate):
   - first_double:       25% if doubles >= 1
   - additional_double:  10% × (doubles − 1) if doubles >= 2
   Doubles go into a separate "doubles" category.

4. Vacation: 4% × (base_rate + all_premiums + all_doubles)
   Only if vacation_eligible == true.

5. Service total = base_rate + premiums + doubles + vacation
```

### Category Totals (top-level aggregation)

| Category Key | What Goes In |
|---|---|
| `performance` | Sum of all Performance base rates |
| `audit` | Sum of all Audit base rates |
| `rehearsal` | Sum of all Rehearsal base rates (after 3hr minimum) |
| `sound_check` | Sum of all 1hr + 2hr Sound Check base rates |
| `premium` | Sum of all non-doubles premiums (principal/lead, electronic, quartet, concertmaster) |
| `doubles` | Sum of all doubles premiums (first_double + additional) |
| `vacation` | Sum of all vacation amounts |
| `guarantee_adjustment` | Sum of weekly guarantee top-ups |
| `substitute_adjustment` | 0.0 when no substitute-specific rate differential applies (from rate book rules, substitutes simply get no vacation and no guarantee) |

### Weekly Guarantee

After computing each non-substitute musician's total pay across all services, if `total < 2082.00`, add a `guarantee_adjustment` of `2082.00 - total`. The musician's total becomes 2082.00. Substitutes are excluded from the guarantee.

### Per-Musician Totals

- Ordered by `musician_id` ascending.
- Include only nonzero category amounts in the per-musician `categories` object.
- `top_paid_musician_id` = the musician_id with the highest total.

### Service Counts

Count occurrences of each `service_type` in the schedule. Keys use the exact service_type strings: `"Rehearsal"`, `"1hr Sound Check"`, `"2hr Sound Check"`, `"Performance"`, `"Audit"`.

### Conflict Flags (return sorted alphabetically)

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any Rehearsal with `start_time < "09:00"` |
| `REHEARSAL_LATE_END` | Any Rehearsal with `end_time > "18:30"` |
| `SERVICE_OVER_TIME_LIMIT` | Any Rehearsal with `duration_hours > 5.0` |
| `SOUND_CHECK_DURATION_MISMATCH` | Any 1hr/2hr Sound Check where `duration_hours != expected` (1.0 or 2.0) |

Return only flags that actually trigger. If none trigger, return `[]`.

---

## Rounding & Output Conventions (all modules)

| Type | Precision | Example |
|---|---|---|
| Currency (`currency`) | 2 decimal places | `round(val, 2)` → `12345.67` |
| Percent / ratio (`decimal percent`) | 4 decimal places | `round(val, 4)` → `0.0966` (NOT `9.66%`) |
| Lists of IDs | Ascending string sort unless rank order specified | `["BR-004", "BR-005", "BR-006"]` |
| `per_musician` list | Ascending by `musician_id` string | |
| `conflict_flags` list | Alphabetically sorted | `["REHEARSAL_EARLY_START", "SERVICE_OVER_TIME_LIMIT"]` |

**Percent representation:** Growth rates, EBITDA margin, and other ratio fields are expressed as **decimals** (e.g. `0.0966` not `9.66%`).

---

## Common Pitfalls

### Finance
- **Revenue is two accounts:** Always sum `product_revenue` + `service_revenue`. Missing one will understate revenue.
- **EBITDA excludes allocations:** `ebitda = revenue - cogs - sga - allocations`. Do not forget allocations.
- **ARPU / Sales-per-labor are FY-level only:** The denominators are sums of the count metrics across all 12 periods in the fiscal year, not monthly averages.
- **Reconciliation variance should be zero:** Region totals are the sum of branch totals. Any nonzero variance indicates a computation error.

### Compensation
- **combined_overscale_includes_title:** When `true`, **skip** the Titled Position Premium for that employee entirely. The overscale amount already bundles the title premium. Do not double-count.
- **Title is null:** When `title` is `null`, `title_pct` is 0. The employee gets no Titled Position Premium (affects computation even without `combined_overscale_includes_title`).
- **Forecast YoS offsets:** Add +1 for Y+1, +2 for Y+2 before looking up seniority bands. An employee with 4 YoS becomes 5 YoS in Y+1, potentially crossing into a new band.
- **Forecast rates are non-compounded:** Each year's growth rates apply to the **base** (current year) values, not to the previous forecast year.
- **Partial quarter detection:** Partial quarters use roster `weeks_by_quarter` (which can differ from the fixed 13-week standard). Check all four quarters.
- **Pay type order:** Always use the rate book's `pay_types` list: `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`.

### Payroll
- **Rehearsal 3-hour minimum:** `max(3.0, duration_hours)` before multiplying by hourly rate. A 5.5hr rehearsal pays for 5.5hrs (not 3), a 2.5hr rehearsal pays for 3hrs.
- **Premium vs Doubles categories:** These are **separate** category totals. Principal/lead, electronic, quartet premiums go in `premium`. First_double and additional_double go in `doubles`. The vacation calculation includes BOTH, but the category totals keep them split.
- **No concertmaster flag in train data:** The premium exists in the rate book but the roster flag was not observed in any production.
- **Substitutes:** No vacation eligibility, no weekly guarantee. `substitute_adjustment` category = 0.0 when no substitute rate differential applies (the rate book specifies no substitute rate).
- **Sound check types:** Both `"1hr Sound Check"` and `"2hr Sound Check"` map to the `sound_check` category. Service counts use the full type string as key.
- **Per-musician categories:** Only include categories with nonzero amounts. The `guarantee_adjustment` appears only for those who receive the top-up.
