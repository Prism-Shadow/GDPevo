# Crescent Finance Ops API Skill

## Base URL
- Always use `GDPEVO_ENV_BASE_URL` from `environment_access.md`. It overrides any localhost or `127.0.0.1` reference in staged inputs.

## Endpoint Families
| Domain | Endpoints |
|---|---|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` |

Call every endpoint listed in the task’s `environment_access.json`; omitting one usually causes missing data for a required output section.

## Output Rounding
| Field Type | Decimals |
|---|---|
| Currency | 2 |
| Percent, ratio, growth rate | 4 |
| Integer | exact |

Apply rounding **after** all intermediate sums; do not round until the final value is placed in the JSON.

## Ordering & Ranking Conventions
- **Lists of IDs**: ascending stable sort unless a `rank_desc` or `rank_asc` field explicitly dictates otherwise.
- **Per-musician arrays**: order by `musician_id` ascending.
- **Conflict flags**: alphabetical (e.g., `REHEARSAL_EARLY_START`, `SERVICE_OVER_TIME_LIMIT`).
- **Pay-type lists**: preserve the order returned by the rate-book endpoint.
- **Rank fields**: `rank_desc` = 1 is highest/best; `rank_asc` = 1 is lowest.

## Fiscal-Period Mapping
- M1–M12 → first fiscal year (e.g., FY2024).
- M13–M24 → next fiscal year (e.g., FY2025).
- Use the period-map endpoint to confirm exact year bindings when available.

## Common Calculation Patterns
- **MoM variance**: `current_period − prior_period`; percent = `variance / abs(prior_period)`.
- **FY aggregates**: sum the relevant monthly records for the branch/region/ensemble.
- **EBITDA margin**: `ebitda / revenue`.
- **ARPU**: `revenue / active_customer_count` (or equivalent divisor from accounts data).
- **Sales per labor headcount**: `revenue / labor_headcount`.
- **Revenue growth pct**: `(fy_current − fy_prior) / fy_prior`.
- **Compensation quarter totals**: sum weekly/roster pay within Q1–Q4 boundaries.
- **Largest pay type**: highest annual (or forecast-year) total among the four standard pay types (`Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`).
- **Largest growth pay type**: highest absolute or percent increase between two years; tie-break by larger absolute increase.
- **Region reconciliation variance**: `sum(branch_values) − region_total` (should be 0.0 when data is consistent).

## Payroll Category Rules
- Only include **non-zero** categories in each musician’s `categories` object.
- Standard category keys: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`.
- `weekly_total` = sum of all musician totals = sum of all category totals.

## Compensation Roster Counts
- `combined_overscale_employee_count`: count of roster members with any overscale pay in the period.
- `partial_quarter_employee_count`: count of roster members with service in fewer than all weeks of any quarter.

## Output Structure
- Return **exactly one JSON object**.
- Include **every top-level key** listed in the task’s `answer_template.json`; missing keys cause rejection.
- Nest objects exactly as the template specifies; do not flatten or rename fields.
