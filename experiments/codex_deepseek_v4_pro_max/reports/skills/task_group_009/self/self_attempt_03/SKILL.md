## When to Use This Skill

Use this skill when the task involves:
- Retrieving data from a REST API described in `environment_access.json` payloads
- Producing structured JSON output following an `answer_template.json` payload
- Working with financial, compensation, or payroll operational data
- Interpreting a `request_memo.json` that names the target entity, parameters, and reporting focus
- Reconciling numbers across periods, ensembles, productions, or regions

## Core Workflow

### Step 1 — Read the Three Payload Files

Every task ships with an `input/payloads/` directory containing:

- `environment_access.json` — base URL, service name, and the allowed endpoints list
- `request_memo.json` — identifies the target entity (`target_branch_id`, `ensemble_id`, `production_id`, `target_region_id`) and the reporting focus
- `answer_template.json` — exact JSON schema to return, including required keys, field types, rounding rules, and ordering constraints

Also read `input/prompt.txt` for domain-level framing.

### Step 2 — Fetch All Relevant API Data

Use the base URL from `environment_access.json`. Append each allowed endpoint path exactly. No authentication headers are needed.

Filter query strings are allowed. Use them when the endpoint accepts filtering:
- `/api/finance/records?branch_id=<id>` returns records for only that branch
- `/api/compensation/rosters?ensemble_id=<id>` returns the ensemble roster
- `/api/compensation/scenarios?ensemble_id=<id>&scenario_id=<id>` returns the scenario
- `/api/payroll/productions?production_id=<id>` returns the production with schedule and roster

Fetch all endpoints listed in `environment_access.json` unless you already have everything needed.

### Step 3 — Understand the Data Model

The Finance Ops API serves three domains. Below is the schema discovered from the endpoints:

#### Finance Domain (`/api/finance/*`)

| Endpoint | Returns |
|----------|---------|
| `/api/finance/branches` | Array of `{branch_id, branch_name, region_id, region_name}` |
| `/api/finance/period-map` | Array of `{fiscal_year, month_name, month_number, period}` |
| `/api/finance/accounts` | Array of `{account, category, display_name, metric_type}` |
| `/api/finance/records` | Array of `{account, branch_id, branch_name, region_id, values: {M1..M24}}` |

**Period Convention** (from the period-map):
- M1–M12 → FY2024
- M13–M24 → FY2025

**Account-to-Line Mapping:**
- `revenue` = `product_revenue` + `service_revenue`
- `cogs` = `direct_materials_cogs` + `direct_labor_cogs`
- `sga` = `sales_sga` + `admin_sga` + `occupancy_sga`
- `allocations` = `shared_service_allocations`
- `ebitda` = `revenue` − `cogs` − `sga` − `allocations`

**Operating Metrics:**
- `arpu` = `revenue` / `revenue_units`
- `sales_per_labor_headcount` = `revenue` / `labor_headcount`
- `ebitda_margin` = `ebitda` / `revenue`

#### Compensation Domain (`/api/compensation/*`)

| Endpoint | Returns |
|----------|---------|
| `/api/compensation/rate-book` | Object with `current_year`, `minimum_weekly_scale`, `pay_types`, `quarter_weeks`, `seniority_weekly`, `title_premium_pct`, `business_rules` |
| `/api/compensation/rosters` | Array of employee entries with `employee_id`, `ensemble_id`, `ensemble_name`, `title`, `years_of_service`, `overscale_weekly`, `combined_overscale_includes_title`, `weeks_by_quarter`, `notes` |
| `/api/compensation/scenarios` | Object keyed by `scenario_id`, each with `year_plus_1` and `year_plus_2` objects containing `mws_growth`, `overscale_growth`, `seniority_growth`, `title_pct_multiplier` |

**Employee Pay Composition (per quarter):**
- `minimum_weekly_scale` (MWS) = `rate_book.minimum_weekly_scale × weeks_worked`
- `titled_position_premium` = `rate_book.minimum_weekly_scale × title_premium_pct[title] × weeks_worked` (when `title` is non-null)
- `seniority` = look up band from `rate_book.seniority_weekly` by `years_of_service`, then `band.weekly_amount × weeks_worked`
- `overscale` = `employee.overscale_weekly × weeks_worked`

**Critical Business Rules:**
- If `combined_overscale_includes_title` is `true`, do **not** add a titled position premium separately for that employee.
- Use the roster's actual `weeks_by_quarter` values, not a fixed 13-week assumption, when any employee has a partial-quarter schedule.
- For forecast years (Year + 1, Year + 2): add 1 year of service for Year + 1 and 2 years for Year + 2 **before** determining the seniority band.
- Title premium multiplier (`title_pct_multiplier`) scales the title premium **rate** (not the employee's pay directly). Apply it to `title_premium_pct`.

**Roster Treatment Counts:**
- `combined_overscale_employee_count`: count of employees where `overscale_weekly > 0`.
- `partial_quarter_employee_count`: count of employees whose `weeks_by_quarter` values differ from the standard `rate_book.quarter_weeks`.

#### Payroll Domain (`/api/payroll/*`)

| Endpoint | Returns |
|----------|---------|
| `/api/payroll/rate-book` | Object with `service_rates`, `premium_pct`, `conflict_thresholds`, `service_time_limits`, `weekly_guarantee`, `business_rules` |
| `/api/payroll/productions` | Array of production with `production_id`, `roster`, `schedule` |

**Service Pay Calculation:**
- `Performance` / `Audit`: `service_rate × 1` (per service)
- `Rehearsal`: `hourly_rate × max(3.0, duration_hours)` (3-hour minimum call)
- `Sound Check`: `1hr Sound Check` rate for 1-hour, `2hr Sound Check` rate for 2-hour

**Premium Calculation:**
Premiums are applied to the musician's base service pay (the raw service-rate amount before any premiums). Each applicable premium multiplies base pay:
- `concertmaster`: 0.20
- `principal_or_lead`: 0.15 (when `principal` or `lead` is true)
- `quartet`: 0.15
- `electronic`: 0.25
- `first_double`: 0.25 (when `doubles >= 1`)
- `additional_double`: 0.10 (per each additional double beyond the first, i.e. `doubles - 1` times)

**Vacation:** 4% of (base service pay + all premiums), applied only when `vacation_eligible` is true.

**Weekly Guarantee:** When a musician is not a substitute (`substitute: false`) and total base service pay (before premiums) is below `weekly_guarantee`, add a `guarantee_adjustment` equal to the shortfall.

**Conflict Flags (from schedule checks):**
- `REHEARSAL_EARLY_START`: rehearsal `start_time` is earlier than `conflict_thresholds.rehearsal_earliest_start`
- `REHEARSAL_LATE_END`: rehearsal `end_time` is later than `conflict_thresholds.rehearsal_latest_end`
- `SERVICE_OVER_TIME_LIMIT`: `duration_hours` exceeds `service_time_limits` for that service type
- `SOUND_CHECK_DURATION_MISMATCH`: sound check `duration_hours` is not 1.0 for a "1hr Sound Check" or not 2.0 for a "2hr Sound Check"

Conflict flags must be sorted alphabetically. Only include flags that actually trigger.

### Step 4 — Build the Answer

Follow `answer_template.json` exactly.

**Precision rules (from template descriptions):**
- Currency values: round to 2 decimal places.
- Percent and ratio fields: round to 4 decimal places.
- Lists: ascending by stable ID (`branch_id`, `musician_id`, `employee_id`, etc.) unless a rank field overrides.
- Conflict flags: sorted alphabetically.
- `per_musician` in payroll: ordered by `musician_id`.
- `branch_ids` in region context: ascending order.
- Only include `substitute_adjustment` in category totals when values are non-zero.

**Percent values must be expressed as decimals**, not percentages. For example, 5.2% is `0.052`.

**Enum fields** (like `largest_pay_type`, `largest_growth_pay_type`) must use the exact string from the pay type list: `"Minimum Weekly Scale"`, `"Titled Position Premium"`, `"Seniority"`, or `"Overscale"`.

### Step 5 — Validate Before Returning

Before returning the final JSON:
- Confirm every `required_top_level_key` from the template is present.
- Check rounding: 2 decimals for currency, 4 for percent/ratio.
- Check ordering: lists are in the correct sort order.
- Verify that business rules from the rate books have been applied (combined overscale, seniority band lookups, etc.).
- Spot-check a few values by tracing back to the raw API data.

## Domain-Specific Patterns

### Finance: Branch Close and Regional Views

When computing FY totals, sum all monthly values from the relevant period range:
- FY2024: sum M1 through M12
- FY2025: sum M13 through M24

When computing month-over-month (MoM) variance for a specific branch:
- Amount: `current_period_revenue − prior_period_revenue`
- Percentage: `(current_revenue − prior_revenue) / prior_revenue`

When computing year-over-year growth rates:
- `(FY2025 − FY2024) / FY2024`

For regional aggregation, sum each account's values across all branches in that region for the relevant period range.

### Compensation: Summaries and Forecasts

For each employee, compute pay per quarter by summing MWS, title premium, seniority, and overscale for that quarter's weeks.

For annual totals, sum across all four quarters.

For forecast years, apply growth rates to the rate book base values **before** computing individual employee pay:
- Year + 1 `mws` = `current_mws × (1 + scenario.year_plus_1.mws_growth)`
- Year + 2 `mws` = `year_plus_1_mws × (1 + scenario.year_plus_2.mws_growth)`
- Same pattern for overscale and seniority weekly amounts.
- `title_premium_pct` values are multiplied by `title_pct_multiplier` for each scenario year.

### Payroll: Weekly Production Review

Each musician's pay is the sum of all assigned services. Determine base service pay by service type, apply premiums, apply vacation, then check guarantee.

Service counts (`service_counts`) track the frequency of each service type across the schedule, not per musician.

`substitute_adjustment` appears as a category in totals only when substitutes are present and their per-service rates differ from regular rates (in the current data model, substitutes are paid at the same rates but are flagged for conflict checks and do not receive guarantee adjustments).

## Rounding and Formatting Reference

| Type | Rounding | Example |
|------|----------|---------|
| Currency | 2 decimal places | `123456.78` |
| Percent / Ratio | 4 decimal places | `0.0523` (5.23%) |
| Count / Integer | integer | `42` |
| Enum strings | exact match | `"Minimum Weekly Scale"` |
| ID strings | as-is | `"BR-004"` |

## Common Pitfalls

- **Forgetting the 3-hour rehearsal minimum.** Always apply `max(3.0, duration_hours)` for rehearsal pay.
- **Applying title premium when `combined_overscale_includes_title` is true.** Skip the separate title premium for those employees.
- **Using fixed 13-week quarters for partial-quarter employees.** Use `weeks_by_quarter` from the roster.
- **Not advancing seniority years for forecast scenarios.** Add 1 year for Year + 1, 2 years for Year + 2.
- **Omitting non-zero-only categories in payroll.** Include all seven standard categories; only append `substitute_adjustment` when applicable.
- **Misordering lists.** Follow the template's ordering instruction for each list field.
- **Rounding percents as whole numbers.** Always express as decimals to 4 places.
