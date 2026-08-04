# Crescent Finance Ops API Skill

This skill provides reusable patterns for building financial reporting, compensation, and payroll computations using the Crescent Finance Ops API.

## API Setup

All endpoints are served from a base URL provided in the task payload under `payloads/environment_access.json` as the `base_url` field (typically `http://task-env:9009`). All requests are HTTP GET with no authentication headers. Query-string filters may be used when implied by the task.

Read the task's `prompt.txt` to understand the objective, then examine the three payload files:

- `payloads/environment_access.json` — base URL and available endpoints
- `payloads/request_memo.json` — target IDs, periods, reporting focus, and narrative notes
- `payloads/answer_template.json` — required JSON structure, field types, and rounding rules

Always produce a single JSON object matching the answer template. The template defines required top-level keys, expected field types, and precision rules.

## Rounding and Output Conventions

- Currency values: **2 decimal places** (`round(value, 2)`)
- Percent and ratio values: **4 decimal places** (`round(value, 4)`)
- Lists: **ascending by stable ID** (e.g., branch_id, musician_id) unless a rank field states otherwise
- Nonzero filters: Only include keys whose values are meaningfully nonzero (use `abs(v) > 0.001` when filtering category maps)

## Finance Endpoints

### `/api/finance/branches`
Returns a list of branch objects with `branch_id`, `branch_name`, `region_id`, `region_name`.

### `/api/finance/period-map`
Returns a list mapping `period` labels (M1–M24) to `fiscal_year`, `month_name`, `month_number`. The convention is:
- **M1–M12** → fiscal year 2024
- **M13–M24** → fiscal year 2025

Period convention labels follow the pattern: `"M1_to_M12": "FY2024"`, `"M13_to_M24": "FY2025"`, `"current_month": "<Mon> <YYYY>"`, `"prior_month": "<Mon> <YYYY>"`.

### `/api/finance/accounts`
Lists every account with its `category` and `metric_type`:

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
| active_customers | operating | count |
| labor_headcount | operating | count |
| orders, revenue_units, admin_headcount, backlog | operating | count |

### `/api/finance/records`
Returns one entry per (account, branch) pair. Each entry has a `values` object mapping period labels to numeric amounts. Aggregate by summing `values[p]` across periods and accounts.

### Financial Metric Formulas

Sum these across the target entity (branch or region) and period range:

- **Revenue** = sum of all accounts in category `revenue`
- **COGS** = sum of all accounts in category `cogs`
- **Gross Margin** = Revenue − COGS
- **SG&A** = sum of all accounts in category `sga`
- **Allocations** = sum of accounts in category `allocations`
- **EBITDA** = Revenue − COGS − SG&A − Allocations
- **EBITDA Margin** = EBITDA / Revenue (ratio, 4 decimals)
- **ARPU** = Revenue / Σ(monthly active_customers across the period range)
- **Sales per Labor Headcount** = Revenue / Σ(monthly labor_headcount across the period range)

For ARPU and sales-per-labor, sum the monthly operating metrics across ALL periods in the range. Do **not** use the monthly average; use the cumulative sum.

Region-level metrics are the sum of all branches belonging to that region. Branch-level EBITDA ranking within a region sorts by FY2025 EBITDA descending.

## Compensation Endpoints

### `/api/compensation/rate-book`
Provides:
- `minimum_weekly_scale` (MWS): base weekly dollar amount
- `pay_types`: ordered list `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`
- `quarter_weeks`: default weeks per quarter, e.g. `{"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13}`
- `seniority_weekly`: list of bands `{min_years, max_years, weekly_amount}`; bands are inclusive on both ends, and the last band has `max_years: null`
- `title_premium_pct`: maps title strings to decimal percentages (e.g., `"Concertmaster": 0.22`)
- `current_year`: the integer year (e.g., 2026)
- `business_rules`: narrative rules (see below)

### `/api/compensation/rosters`
Each roster entry has:
- `employee_id`, `ensemble_id`, `ensemble_name`
- `title` (string or null)
- `overscale_weekly` (dollars)
- `years_of_service` (integer)
- `weeks_by_quarter` (object with Q1–Q4 keys; may differ from the default 13 in the rate book)
- `combined_overscale_includes_title` (boolean)
- `notes`

### Compensation Computation Per Employee

For each employee in the target ensemble:

1. **Total weeks** = Σ weeks_by_quarter across Q1–Q4. Use the roster's actual weeks, not the rate-book default.

2. **Minimum Weekly Scale** = MWS × total_weeks

3. **Seniority**: Determine the band for `years_of_service` (inclusive range). The band's `weekly_amount` × total_weeks.

4. **Titled Position Premium**: If `title` is non-null AND `combined_overscale_includes_title` is **false**, compute `MWS × title_premium_pct[title] × total_weeks`. If `combined_overscale_includes_title` is **true**, skip the title premium entirely (it is already bundled in the overscale amount).

5. **Overscale** = `overscale_weekly` × total_weeks

6. **Quarter totals**: For each quarter Q, compute `(MWS + seniority_weekly + title_premium_weekly + overscale_weekly) × weeks[Q]`.

Aggregate across all employees for ensemble-level totals, annual pay-type totals, and quarter totals.

**Roster treatment counts**:
- `combined_overscale_employee_count`: count of employees where `combined_overscale_includes_title` is `true`.
- `partial_quarter_employee_count`: count of employees where any quarter's weeks differ from the rate-book default (13).

**Largest pay type** is the one with the highest annual total dollar value.

## Compensation Forecast (Scenarios)

### `/api/compensation/scenarios`
Returns named scenario objects. Each has `year_plus_1` and `year_plus_2` with:
- `mws_growth`: growth rate for minimum weekly scale
- `overscale_growth`: growth rate for overscale weekly amount
- `seniority_growth`: growth rate applied to the seniority band's weekly amount
- `title_pct_multiplier`: multiplier applied to each title's premium percentage

### Forecast Computation

Year adjustments are **sequential (multiplicative compounding)**: each year's rate builds on the previous year's rate.

- **Current year**: Use base rate-book values with `years_of_service` unchanged.
- **Year + 1**: Add 1 to `years_of_service` for seniority band assignment. Multiply MWS by `(1 + y1_mws_growth)`, seniority weekly by `(1 + y1_seniority_growth)`, overscale by `(1 + y1_overscale_growth)`, title percentages by `y1_title_pct_multiplier`.
- **Year + 2**: Add 2 to `years_of_service` (from original, not from Year + 1). Apply Year + 2 growth rates **on top of** the Year + 1 values: `y2_rate = y1_rate × (1 + y2_growth)`.

Growth rates between years are computed as:
- `year_plus_1_vs_current` = (Year+1 total − current total) / current total
- `year_plus_2_vs_year_plus_1` = (Year+2 total − Year+1 total) / Year+1 total

### Driver Classification

The largest-growth pay type is determined by **percentage growth** from current to Year + 2: `(y2_amount − current_amount) / current_amount`. Choose the pay type with the highest percentage increase.

## Payroll Endpoints

### `/api/payroll/rate-book`
Provides:
- `service_rates`: per-service or hourly rates for each service type
- `premium_pct`: decimal percentages for role/instrument premiums and vacation
- `conflict_thresholds`: time-based thresholds for flagging issues
- `service_time_limits`: maximum allowed duration per service type
- `weekly_guarantee`: minimum weekly pay for regular players
- `business_rules` (see below)

### `/api/payroll/productions`
Each production has a `roster` (musicians with assigned service IDs, instrument flags, and eligibility booleans) and a `schedule` (services with type, date, times, and duration).

### Service Pay Calculation

| Service Type | Rate Basis | Rate |
|---|---|---|
| Performance | Per service | `service_rates.Performance` |
| Audit | Per service | `service_rates.Audit` |
| 1hr Sound Check | Per service | `service_rates["1hr Sound Check"]` |
| 2hr Sound Check | Per service | `service_rates["2hr Sound Check"]` |
| Rehearsal | Hourly, 3-hour minimum call | `service_rates.Rehearsal` × max(actual_hours, 3.0) |

### Premiums

Applied to the musician's total base service pay across all assigned services:

| Premium | Condition | Rate |
|---|---|---|
| Principal or Lead | `principal` or `lead` is true | `premium_pct.principal_or_lead` |
| Electronic | `electronic` is true | `premium_pct.electronic` |
| Quartet | `quartet` is true | `premium_pct.quartet` |
| First Double | `doubles >= 1` | `premium_pct.first_double` |
| Additional Double | `doubles >= 2` | `premium_pct.additional_double` |
| Vacation | `vacation_eligible` is true | `premium_pct.vacation` of (base + all other premiums) |

Category mapping: role premiums go to `premium`, doubles premiums go to `doubles`, vacation goes to `vacation`.

### Weekly Guarantee

For non-substitute musicians: if base service pay (before premiums) is below `weekly_guarantee`, add a `guarantee_adjustment` to bring the total to the guarantee level. The adjustment = `max(0, weekly_guarantee − base_pay)`.

### Substitute Handling

Substitute musicians (`substitute: true`) are not eligible for the weekly guarantee adjustment. They receive standard service pay and applicable premiums but no guarantee top-up. The `substitute_adjustment` category is used only if a nonzero substitution impact exists.

### Conflict Flags

Check the schedule for these flags (return sorted alphabetically):

- **REHEARSAL_EARLY_START**: Any rehearsal starting before `conflict_thresholds.rehearsal_earliest_start`
- **REHEARSAL_LATE_END**: Any rehearsal ending after `conflict_thresholds.rehearsal_latest_end`
- **SERVICE_OVER_TIME_LIMIT**: Any service whose `duration_hours` strictly exceeds the limit in `service_time_limits` for its type
- **SOUND_CHECK_DURATION_MISMATCH**: A sound check whose actual duration does not match its labeled type (1hr vs 2hr)

## General Patterns

### Payload Interpretation

1. Read the task prompt to understand the business objective and requested outputs.
2. Read `request_memo.json` for target IDs (`target_branch_id`, `ensemble_id`, `production_id`, `scenario_id`), period references, and focus areas.
3. Read `answer_template.json` for the exact required JSON shape. The `required_top_level_keys` list and `field_types` object define every key and value type.
4. Fetch all relevant API data once; build lookup maps by ID for efficient aggregation.

### Data Aggregation

- For branch/region finance: aggregate account values across periods using the account category mapping.
- For compensation: iterate over roster employees and compute per-employee, per-quarter, per-pay-type totals.
- For payroll: iterate over each musician's assigned services, compute base pay, then apply premiums and adjustments.

### Common Pitfalls

- Do not use a fixed 13-week quarter for compensation when the roster shows different weeks for an employee.
- When `combined_overscale_includes_title` is true, do not add a separate title premium—it is already embedded in the overscale amount.
- Do not apply the weekly guarantee to substitute musicians.
- For forecast years, adjust `years_of_service` (+1 for Year+1, +2 for Year+2) before looking up the seniority band, then apply the growth factor to the band's weekly amount.
- Growth compounding is multiplicative, not additive.
- ARPU and sales-per-labor use the sum of monthly operating-metreic values across the period range, not the monthly average.
- Percent and ratio fields always use 4-decimal rounding; currency uses 2-decimal rounding.
