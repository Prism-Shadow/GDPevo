# Crescent Arts Collective — Finance Ops Reporting Skill

## Environment & API Usage
- **Base URL**: Use `GDPEVO_ENV_BASE_URL` from `environment_access.md`; never default to localhost.
- **Endpoint families**:
  - `/api/finance/branches`, `/period-map`, `/accounts`, `/records` — for branch/region close and management packages.
  - `/api/compensation/rate-book`, `/rosters`, `/scenarios` — for compensation summaries and forecasts.
  - `/api/payroll/rate-book`, `/productions` — for weekly payroll reviews.
- **Strategy**: Fetch all referenced endpoints, cache by entity ID, and compute in memory. Most reports need joined data (e.g., branches + records + period-map, or productions + rate-book + roster).

## Fiscal Period Convention
- **M1–M12** map to **FY2024**.
- **M13–M24** map to **FY2025**.
- `current_month` / `prior_month` are literal period labels (e.g., `"M24"`, `"M23"`).
- FY boundaries are fixed; do not derive from calendar date.

## Calculation Rules
- **Currency**: round to **2 decimals** (standard `round(value, 2)`).
- **Percents / ratios / growth rates**: round to **4 decimals** (e.g., `0.2459`).
- **EBITDA margin**: `ebitda / revenue`.
- **Revenue growth**: `(fy2025_revenue - fy2024_revenue) / fy2024_revenue`.
- **EBITDA growth**: `(fy2025_ebitda - fy2024_ebitda) / fy2024_ebitda`.
- **MoM variance**: `current_period_revenue - prior_period_revenue`; percent = `amount / prior_period_revenue`.
- **Regional reconciliation variance**: sum of branch-level figures minus region-level figure; expect `0.0` when data is clean.
- **ARPU** and **sales_per_labor_headcount**: treated as currency (2 decimals).

## Ranking & Ordering
- **Branch rankings** (sales growth, EBITDA, ARPU) are **descending** (`rank_desc`).
  - Rank 1 = highest value.
  - Ties: use stable branch-ID order or the API’s implicit order; the skill should be deterministic.
- **Lists**:
  - `branch_ids`: ascending alphanumeric unless a rank field states otherwise.
  - `per_musician`: ordered by `musician_id` ascending.
  - `conflict_flags`: sorted **alphabetically**.
  - `pay_types`: preserve rate-book order or list ascending if unspecified.

## Payroll Conflict Flags
- Detectable from production schedule + roster + rate-book rules:
  - `REHEARSAL_EARLY_START`
  - `REHEARSAL_LATE_END`
  - `SERVICE_OVER_TIME_LIMIT`
  - `SOUND_CHECK_DURATION_MISMATCH`
- Only emit flags that are actually triggered; empty list `[]` if none.

## Compensation Patterns
- **Pay types** (from rate book): `Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`.
- **Quarter totals**: Q1–Q4 derived from roster start/end dates and weekly scale rules.
- **Annual total**: sum of all pay-type annual totals.
- **Largest pay type**: by annual total (or by Y+2 total for forecasts).
- **Largest growth pay type**: by absolute or percent growth between years; return the enum string exactly.
- **Roster counts**:
  - `combined_overscale_employee_count`: employees with any overscale entry.
  - `partial_quarter_employee_count`: employees whose service does not cover a full quarter.

## Output Field Conventions
- Return exactly **one JSON object** with all required top-level keys from the answer template.
- Never omit a required key; use `0` or `0.0` for missing currency, `0` for missing counts, `[]` for empty lists.
- Do not include extra keys beyond the template.
- When a field is an enum (e.g., `largest_pay_type`), match the exact template string.

## Common Pitfalls
- **Do not compute FY from calendar year**; use the fixed M1–M12 / M13–M24 mapping.
- **Do not round intermediate values**; round only at the final output step to avoid compounding error.
- **Check for zero denominators** before division; if zero, output `0.0` for the percent/ratio field.
- **Reconciliation**: verify that branch-level aggregates equal the region total before returning `region_reconciliation_variance`.
- **Musician categories in `per_musician`**: include only **nonzero** categories.
- **Service counts**: map exact service type strings from the production schedule to integer counts.
