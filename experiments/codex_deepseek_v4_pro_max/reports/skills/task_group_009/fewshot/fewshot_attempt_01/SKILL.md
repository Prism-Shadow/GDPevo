 # Crescent Finance Ops Skill

 Use this skill for all reporting, analysis, and forecasting tasks against the Crescent Finance Ops API.

 ## Environment Connection

 The API runs at `http://task-env:9009/`. All endpoints are GET with no authentication required.
 Query-string filters are supported to narrow results (e.g., `?branch_id=BR-004`, `?ensemble_id=ENS-REDWOOD`).

 Always fetch **all** data needed for a task before performing computations; do not rely on partial fetches.

 ## Available Endpoints

 ### Finance (Branch / P&L / Periods)

 | Endpoint | Returns |
 |---|---|
 | `/api/finance/branches` | All branches with `branch_id`, `branch_name`, `region_id`, `region_name` |
 | `/api/finance/period-map` | 24 periods (M1–M24) mapping to FY2024 (M1–M12) and FY2025 (M13–M24) |
 | `/api/finance/accounts` | Chart of accounts: `account`, `category`, `display_name`, `metric_type` (`currency` or `count`) |
 | `/api/finance/records` | Per-branch, per-account time-series: `branch_id`, `branch_name`, `region_id`, `account`, and a `values` object keyed by period (M1–M24) |

 ### Compensation

 | Endpoint | Returns |
 |---|---|
 | `/api/compensation/rate-book` | Current-year rates: `minimum_weekly_scale`, `quarter_weeks` (Q1–Q4 each 13 weeks), `seniority_weekly` bands, `title_premium_pct`, `pay_types`, `business_rules`, `current_year` |
 | `/api/compensation/rosters` | All roster entries: `employee_id`, `ensemble_id`, `ensemble_name`, `title`, `years_of_service`, `overscale_weekly`, `weeks_by_quarter`, `combined_overscale_includes_title`, `notes` |
 | `/api/compensation/scenarios` | Named forecast scenarios with `year_plus_1` and `year_plus_2` growth rates for `mws_growth`, `overscale_growth`, `seniority_growth`, and `title_pct_multiplier` |

 ### Payroll

 | Endpoint | Returns |
 |---|---|
 | `/api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, weekly guarantee, business rules |
 | `/api/payroll/productions` | Production details: `production_id`, `title`, `week_start`, `schedule` (list of services), `roster` (list of musicians with flags and assigned services) |

 ## Domain Knowledge

 ### Period Convention

 - M1–M12 = **FY2024**
 - M13–M24 = **FY2025**
 - Current year for compensation is the year from `/api/compensation/rate-book` (`current_year` field, e.g., 2026)
 - When a task references "current month" or "close period," use the period label from the request memo and map it via the period-map endpoint

 ### Finance Accounts & Income Statement Structure

 Category mapping (from `/api/finance/accounts`):

 - **Revenue** = `product_revenue` + `service_revenue`
 - **COGS** = `direct_materials_cogs` + `direct_labor_cogs`
 - **Gross Margin** = Revenue − COGS
 - **SGA** = `sales_sga` + `admin_sga` + `occupancy_sga`
 - **Allocations** = `shared_service_allocations`
 - **EBITDA** = Gross Margin − SGA − Allocations

 Operating metrics for ratios:
 - `labor_headcount`, `admin_headcount` (count type)
 - `orders`, `revenue_units`, `active_customers`, `backlog` (count type)

 To aggregate a P&L line (e.g., Revenue) for a branch and period: sum the `values[period]` for every account whose `category` contributes to that line.

 ### Compensation Model

 Pay types (ordered):
 1. **Minimum Weekly Scale** — `minimum_weekly_scale` × total roster weeks
 2. **Titled Position Premium** — `minimum_weekly_scale` × `title_premium_pct[title]` × weeks (skip if `combined_overscale_includes_title` is true)
 3. **Seniority** — lookup `seniority_weekly` band by `years_of_service` × weeks
 4. **Overscale** — `overscale_weekly` × weeks (raw overscale, separate from titled premium)

 Quarter weeks come from the rate book (`quarter_weeks`), but use the **roster's `weeks_by_quarter`** values when present—some employees may have partial-quarter weeks (less than the standard 13). This affects the `partial_quarter_employee_count`.

 **Combined overscale** includes employees where `combined_overscale_includes_title` is true; an employee with `overscale_weekly > 0` or `combined_overscale_includes_title == true` counts toward `combined_overscale_employee_count`.

 **Partial quarter employees** are those whose `weeks_by_quarter` total is less than the standard full-year week count (typically 52).

 ### Compensation Forecasting

 For a given scenario (from `/api/compensation/scenarios`):
 - **Year + 1**: apply `year_plus_1` growth rates to each pay component
 - **Year + 2**: apply `year_plus_2` growth rates to each pay component
 - Add one year of service for Year + 1 and two years for Year + 2 before re-assigning seniority bands
 - Titled position premium: multiply base premium by `title_pct_multiplier` for the forecast year

 Growth rate between two totals = `(new − old) / old`, rounded to 4 decimal places.

 ### Payroll Model

 Service types and their rates:
 - **Performance**, **Audit**: flat per-service rate (`service_rates`)
 - **Rehearsal**: hourly rate with a 3-hour minimum call — compute as `max(3, duration_hours) × rate`
 - **Sound Check** (1hr or 2hr): flat per-service rate; check duration against `service_time_limits` — flag `SOUND_CHECK_DURATION_MISMATCH` if the `service_type` says "1hr" but `duration_hours` ≠ 1.0, or "2hr" but `duration_hours` ≠ 2.0

 Premiums (applied to base service pay):
 - `concertmaster`: 0.20
 - `principal_or_lead`: 0.15 (if `principal` or `lead` is true)
 - `quartet`: 0.15
 - `electronic`: 0.25
 - `first_double`: 0.25 (if `doubles >= 1`)
 - `additional_double`: 0.10 (for each double beyond the first, i.e., `doubles − 1`)

 Vacation pay = 4% of (base service pay + premiums), only for employees with `vacation_eligible: true`.

 Weekly guarantee adjustment: for non-substitute regular players (`substitute: false`), if base service pay < `weekly_guarantee`, add `weekly_guarantee − base_service_pay`.

 **Conflict flags** (from schedule checks):
 - `REHEARSAL_EARLY_START` — any Rehearsal service where `start_time` < `rehearsal_earliest_start` (09:00)
 - `REHEARSAL_LATE_END` — any Rehearsal service where `end_time` > `rehearsal_latest_end` (18:30)
 - `SERVICE_OVER_TIME_LIMIT` — any service where `duration_hours` exceeds its type's `service_time_limits` entry
 - `SOUND_CHECK_DURATION_MISMATCH` — duration mismatch as described above
 Output conflict flags as a sorted list (alphabetical).

 ### Branch & Region

 Branches belong to regions:
 - REG-NORTH: BR-001, BR-002, BR-003
 - REG-WEST: BR-004, BR-005, BR-006
 - REG-EAST: BR-007, BR-008, BR-011
 - REG-SOUTH: BR-009, BR-010, BR-012

 When computing region aggregates, sum across all branches in the region.

 ## Computation Patterns

 ### Single-Period Income Statement (e.g., M24 for BR-004)

 1. Fetch `/api/finance/records` (filter by branch if supported, or fetch all and filter in code)
 2. For each account belonging to Revenue, COGS, SGA, or Allocations categories, extract `values[period]`
 3. Sum by category to build the P&L

 ### Multi-Period / Fiscal-Year Aggregation

 Sum all period values within the fiscal year range (M1–M12 for FY2024, M13–M24 for FY2025).

 ### MoM Revenue Variance

 `amount` = revenue_current − revenue_prior
 `pct` = amount / revenue_prior

 ### EBITDA Margin

 `ebitda_margin` = EBITDA / Revenue

 ### ARPU (Average Revenue Per Unit)

 `arpu` = Revenue / `revenue_units` (sum for the relevant scope)

 ### Sales Per Labor Headcount

 `sales_per_labor_headcount` = Revenue / `labor_headcount` (sum for the relevant scope)

 ### Branch Rankings

 - **Sales growth rank (desc)**: rank branches by revenue growth from FY2024 to FY2025, largest growth = rank 1
 - **EBITDA rank (desc)**: rank branches by FY2025 EBITDA, largest = rank 1
 - **Top ARPU**: branch with highest ARPU
 - **Top/Bottom EBITDA**: branch with highest/lowest FY2025 EBITDA

 ### Region Reconciliation Variance

 `region_reconciliation_variance` = FY2025 EBITDA (from regional branch rollup) − FY2025 EBITDA (from reported/expected figure). Should be 0.0 when clean.

 ## Output Formatting Rules

 - **Currency values**: always round to 2 decimal places
 - **Percent / ratio values**: always round to 4 decimal places
 - **Lists**: sort by stable ID ascending (e.g., `branch_id`, `musician_id`) unless a rank field dictates otherwise
 - **Conflict flags**: sort alphabetically
 - **Pay types**: use the ordered list from the rate book (`pay_types` field)
 - **Per-musician entries**: ordered by `musician_id` ascending
 - **Category breakdowns in per-musician**: include only nonzero categories

 ## Task Workflow

 When given a task against this API:

 1. **Parse the request memo** to identify the target entity (branch_id, ensemble_id, production_id, region_id, scenario_id) and the required reporting focus
 2. **Fetch all relevant endpoints** in parallel — never make sequential calls when they can be parallelized
 3. **Compute all aggregations** in memory using the rules above
 4. **Apply formatting rules** (2-decimal currency, 4-decimal ratios)
 5. **Return a single JSON object** matching the answer template structure; do not include extra commentary or markdown wrapping — return pure JSON
