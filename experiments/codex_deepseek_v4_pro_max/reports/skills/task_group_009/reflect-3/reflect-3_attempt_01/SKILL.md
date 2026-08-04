 # Crescent Finance Ops Skill

 ## Overview

 This skill covers multi-domain financial and compensation reporting against the Crescent Finance Ops REST API. Tasks span branch financial close packages, regional management views, compensation summaries, payroll reviews, and compensation forecasts. Every task follows the same pattern: read the request memo and answer template, query the relevant API endpoints, compute derived metrics, and return a single JSON object matching the template exactly.

 ## Workflow

 1. Read the three payloads in the task input directory:
    - `prompt.txt` — natural-language task description
    - `request_memo.json` — structured request parameters (target IDs, periods, focus areas)
    - `answer_template.json` — required JSON shape, key names, field types, and formatting rules
 2. Query every endpoint listed in `environment_access.json` (or the global environment access document). GET requests need no authentication headers.
 3. Join and aggregate the returned data according to the request memo parameters.
 4. Build the answer as a single JSON object whose keys and structure match the answer template exactly. Follow all rounding and ordering rules.

 ## API Endpoints

 All endpoints are relative to a base URL provided in the environment access payload. The available endpoints form three domains:

 **Finance** — branch P&L and operating data
- `GET /api/finance/branches` — branch master list with `branch_id`, `branch_name`, `region_id`, `region_name`
- `GET /api/finance/period-map` — fiscal-period lookup: each object has `fiscal_year`, `month_name`, `month_number`, `period` (e.g. "M1"–"M24")
- `GET /api/finance/accounts` — chart of accounts with `account`, `category`, `display_name`, `metric_type`
- `GET /api/finance/records` — monthly values per branch per account; each record has `branch_id`, `account`, and a `values` map keyed by period

**Compensation** — musician compensation rate book, rosters, and scenario planning
- `GET /api/compensation/rate-book` — current-year minimum weekly scale, seniority bands, title premium percentages, quarter-week definitions, and business rules
- `GET /api/compensation/rosters` — employee-level data: `employee_id`, `ensemble_id`, `title`, `overscale_weekly`, `combined_overscale_includes_title`, `years_of_service`, `weeks_by_quarter`
- `GET /api/compensation/scenarios` — forecast scenarios with year-over-year growth rates for MWS, overscale, seniority, and title-pct multiplier

**Payroll** — weekly theatre-production payroll
- `GET /api/payroll/rate-book` — service rates, premium percentages, conflict thresholds, weekly guarantee, and business rules
- `GET /api/payroll/productions` — production schedule and roster with assigned service IDs

## Finance Domain — Calculation Rules

### Period Convention

The period map uses a continuous month numbering. Typically M1–M12 belong to one fiscal year and M13–M24 to the next.

- `period_convention.current_month` and `prior_month` use the **period code** from the period-map (e.g. `"M24"`, `"M23"`), never a spelled-out month name.
- `period_convention.M1_to_M12` and `M13_to_M24` use the format `"FY2024"`, `"FY2025"` (prefix `"FY"` followed by the four-digit year).

### Income Statement Line Items

Derive every line from the raw account data. Do not use pre-computed totals—always sum the underlying accounts:

| Line | Formula |
|------|---------|
| revenue | `product_revenue` + `service_revenue` |
| cogs | `direct_materials_cogs` + `direct_labor_cogs` |
| gross_margin | revenue − cogs |
| sga | `sales_sga` + `admin_sga` + `occupancy_sga` |
| allocations | `shared_service_allocations` |
| ebitda | gross_margin − sga − allocations |

### Ratios and Per-Unit Metrics (Fiscal-Year Level)

- **ebitda_margin** = FY ebitda ÷ FY revenue (decimal, rounded to 4 places)
- **arpu** = FY revenue ÷ **total** FY active_customers across all 12 months (not average monthly customers)
- **sales_per_labor_headcount** = FY revenue ÷ **total** FY labor_headcount across all 12 months (not average monthly headcount)

### Rankings

All rank fields use **descending** order (rank 1 = highest value). When ranking branches, always rank across the full branch universe unless the field is explicitly scoped to a region. `ebitda_rank_desc` inside `region_context` ranks only within that region.

### Regional Aggregation

Sum each line item across every branch in the region for the requested fiscal year(s). `branch_ids` must be in ascending order. The `region_reconciliation_variance` is zero when values are summed directly from branch data (no separate region-level source).

## Compensation Domain — Calculation Rules

### Current-Year Pay

For each employee in the target ensemble, compute four pay-type amounts **per quarter**, then sum across quarters:

- **Minimum Weekly Scale**: `rate_book.minimum_weekly_scale × weeks_in_quarter`
- **Titled Position Premium**: `title_premium_pct × minimum_weekly_scale × weeks` — omit this line entirely when `combined_overscale_includes_title` is `true`
- **Seniority**: look up the employee's `years_of_service` in the seniority bands table and multiply the matching `weekly_amount` by weeks
- **Overscale**: `overscale_weekly × weeks`

Pay types must be listed in the order they appear in the rate book's `pay_types` array.

### Forecast Years (Year + 1, Year + 2)

Use the scenario object identified by `scenario_id`. For each forecast year:

1. **Add service years**: +1 for Year+1, +2 for Year+2, **then** look up the seniority band.
2. **Compound the growth factors** across years:
   - Year+1 MWS = current MWS × (1 + y1.mws_growth)
   - Year+2 MWS = Year+1 MWS × (1 + y2.mws_growth)
   - Same compounding pattern for overscale growth and seniority growth factors.
3. **Title pct multiplier** compounds: Year+2 multiplier = y1.title_pct_multiplier × y2.title_pct_multiplier.
4. Apply the resulting MWS, overscale factor, seniority factor, and title multiplier to every employee's base values using the same per-quarter logic as the current year.

### Growth Rates

- `year_plus_1_vs_current` = ( Year+1 annual total − current annual total ) ÷ current annual total
- `year_plus_2_vs_year_plus_1` = ( Year+2 annual total − Year+1 annual total ) ÷ Year+1 annual total
- `largest_growth_pay_type` compares **percentage growth** of each pay type from the current year to Year+2. Pick the pay type with the highest percentage increase.

### Roster Treatment Counts

- **combined_overscale_employee_count**: count employees where `combined_overscale_includes_title` is `true`
- **partial_quarter_employee_count**: count employees where any quarter in `weeks_by_quarter` has fewer than the standard quarter weeks (typically 13)

## Payroll Domain — Calculation Rules

### Service Rates

| Service Type | Rate |
|-------------|------|
| Rehearsal | Hourly rate × hours; minimum 3-hour call per service |
| Performance | Flat per-service rate |
| Audit | Flat per-service rate |
| 1hr Sound Check | Flat per-service rate |
| 2hr Sound Check | Flat per-service rate |

### Premiums (per service, applied to base service pay)

- `principal_or_lead`: musician is principal **or** lead → pct × base
- `quartet`: musician.quartet is true → pct × base
- `electronic`: musician.electronic is true → pct × base
- `concertmaster`: musician.title is Concertmaster → pct × base

### Doubles (per service)

- 1 extra instrument: `first_double` pct × base
- Each additional extra instrument: `additional_double` pct × base

### Vacation

4% of (base service pay + all premiums + doubles) when `vacation_eligible` is true.

### Weekly Guarantee

Applies only to **non-substitute** musicians. If total pay before guarantee is below `weekly_guarantee`, add the shortfall as a guarantee adjustment.

### Conflict Flags

Check every scheduled service against the conflict thresholds in the payroll rate book:

- **REHEARSAL_EARLY_START**: rehearsal start time is earlier than `rehearsal_earliest_start`
- **REHEARSAL_LATE_END**: rehearsal end time is later than `rehearsal_latest_end`
- **SERVICE_OVER_TIME_LIMIT**: actual duration exceeds the service-type time limit
- **SOUND_CHECK_DURATION_MISMATCH**: a "1hr Sound Check" whose duration is not 1.0, or a "2hr Sound Check" whose duration is not 2.0

Return the flags as a sorted list.

### Service Counts

Count occurrences of each distinct `service_type` value from the production schedule. Use the exact strings as they appear in the schedule data.

## Formatting Rules (All Domains)

- **Currency values**: Python `round(value, 2)`. Do not apply intermediate rounding during computation—only round final values.
- **Decimal percent / ratio values**: Python `round(value, 4)`.
- **Integer fields** (counts, ranks): whole numbers.
- **Lists**: sort by stable ID ascending (e.g. `branch_id`, `musician_id`) unless the template specifies otherwise.
- **Objects with zero values**: include keys whose value is zero only when the template mandates a fixed set of keys (e.g. `category_totals`). For `per_musician.categories`, include only non-zero entries.
- **JSON key order**: follow the order shown in the answer template or use the natural insertion order from the data.
