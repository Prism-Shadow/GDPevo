---
name: crescent-finance-ops
description: Prepare Crescent Arts Collective finance, compensation, and payroll reports from the Finance Ops API. Use when given prompt.txt with payloads/ for branch close, regional reporting, compensation summaries, payroll reviews, or board forecasts.
---

# Crescent Finance Ops Reporting

This skill provides reusable instructions for generating structured JSON reports from the Crescent Arts Collective Finance Ops API. It covers branch management reporting, regional views, compensation summaries, payroll reviews, and compensation forecasts.

## Input Structure

Every task follows a consistent layout:

- `prompt.txt` — high-level task description and domain context.
- `payloads/environment_access.json` — the task-specific endpoint list and a placeholder base URL (`<TASK_ENV_BASE_URL>`).
- `payloads/request_memo.json` — the concrete request: target IDs, periods, scenarios, and focus areas.
- `payloads/answer_template.json` — the required output shape, key names, field types, and sorting/formatting rules.

Always read all four files before calling any API.

## Environment Resolution

The per-task `payloads/environment_access.json` contains a placeholder `"base_url": "<TASK_ENV_BASE_URL>"`. Replace this placeholder with the actual base URL from the root `environment_access.md` file:

```
Base URL: http://task-env:9009/
```

Append endpoint paths directly. No authentication headers are required for GET requests. Query-string filters may be used when the request_memo implies filtering (e.g., by branch ID, period, or ensemble).

## API Endpoints

### Finance Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/finance/branches` | Branch objects with `branch_id`, `branch_name`, `region_id`, headcount fields |
| `GET /api/finance/period-map` | Maps period labels (`M1`–`M24`) to month names and fiscal-year strings (`FY2024`, `FY2025`) |
| `GET /api/finance/accounts` | Account objects with `account_code`, `account_name`, and `account_category` (e.g., Revenue, COGS, SGA, Allocations) |
| `GET /api/finance/records` | Financial records keyed by `branch_id`, `period` (M1–M24), and `account_code`, each containing a numeric `amount` |

### Compensation Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/compensation/rate-book` | Pay types (`Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`) with rate values |
| `GET /api/compensation/rosters` | Employee/musician roster records with `employee_id`, `ensemble_id`, pay types, weekly amounts, service quarters, and overscale notes |
| `GET /api/compensation/scenarios` | Forecast scenarios with `scenario_id`, `ensemble_id`, growth rates, and year-by-year compensation projections |

### Payroll Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/payroll/rate-book` | Payroll rate information keyed by category |
| `GET /api/payroll/productions` | Production schedules with `production_id`, services (rehearsals, sound checks, performances), musician assignments, CBA flags, start/end times, and duration fields |

## Financial Computations

### Income Statement

Derive line items from account categories and records:

- **Revenue** — sum of records with account category `Revenue`.
- **COGS** — sum of records with account category `COGS`.
- **Gross Margin** = Revenue − COGS.
- **SGA** — sum of records with account category `SGA`.
- **Allocations** — sum of records with account category `Allocations`.
- **EBITDA** = Gross Margin − SGA − Allocations.

### Ratios and KPIs

- **EBITDA Margin** = EBITDA ÷ Revenue (rounded to 4 decimals as a percent).
- **ARPU** (Average Revenue Per Unit/Headcount) = Revenue ÷ headcount.
- **Sales Per Labor Headcount** = Revenue ÷ labor headcount (use the relevant headcount field from the branches endpoint).

### Variance and Growth

- **Month-over-Month Variance**:
  - `amount` = current_period_value − prior_period_value.
  - `pct` = (current − prior) ÷ |prior| (rounded to 4 decimals).
- **Year-over-Year Growth**:
  - `revenue_growth_pct` = (FY_current_revenue − FY_prior_revenue) ÷ |FY_prior_revenue|.
  - `ebitda_growth_pct` = (FY_current_ebitda − FY_prior_ebitda) ÷ |FY_prior_ebitda|.

### Fiscal-Year Aggregation

- Map periods to fiscal years using the period map. M1–M12 belong to one fiscal year; M13–M24 belong to the next.
- Sum records across all periods within a fiscal year for each account category.
- Derive FY-level income statement, then compute margins and KPIs.

### Quarter Aggregation (Compensation)

- Sum weekly compensation amounts by the quarter in which each week falls.
- The roster endpoint indicates the quarter each week or service belongs to.

### Pay Type Aggregation (Compensation)

- Group compensation by the four standard pay types: `Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`.
- Sum amounts per pay type from the roster data, applying rates from the rate book.

### Compensation Forecasting

- A scenario object from `/api/compensation/scenarios` contains annual totals for `current`, `year_plus_1`, and `year_plus_2`, plus quarter and pay-type breakdowns for `year_plus_2`.
- Compute growth rates:
  - `year_plus_1_vs_current` = (year_plus_1 − current) ÷ |current|.
  - `year_plus_2_vs_year_plus_1` = (year_plus_2 − year_plus_1) ÷ |year_plus_1|.
- Identify the pay type with the largest absolute growth (year_plus_2 minus current) as `largest_growth_pay_type`.

### Payroll Computations

- **Service Counts**: Count each type of service (rehearsal, sound check, performance, etc.) from the production schedule.
- **Category Totals**: Sum amounts per payroll category (from the payroll rate book) across all services and musicians.
- **Per-Musician Totals**: Aggregate each musician's pay across all categories they are assigned to.
- **Weekly Total**: Sum of all category totals.
- **Top Paid Musician**: The musician with the highest per-musician total.

### CBA Conflict Flags

Check production service records against the following rules and include any triggered flags. Sort flags alphabetically when returning them:

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | A rehearsal service starts before the allowable early-start threshold specified in the rate book or production schedule. |
| `REHEARSAL_LATE_END` | A rehearsal service ends after the allowable late-end threshold. |
| `SERVICE_OVER_TIME_LIMIT` | A service duration exceeds the maximum time limit for that service type. |
| `SOUND_CHECK_DURATION_MISMATCH` | A sound-check service's actual duration does not match its scheduled duration. |

### Branch Rankings

- Rank branches within a region by a metric in descending order (1 = best/highest).
- `ebitda_rank_desc` within region: rank branches by FY EBITDA, highest first.
- `sales_growth_rank_desc`: rank by revenue growth percentage, highest first.
- `top_sales_growth_branch_id`: the branch with the highest revenue growth in the comparison set.
- `top_arpu_branch_id`: the branch with the highest ARPU in the comparison set.

### Region Reconciliation Variance

- Sum the values for all branches in the region from branch-level data.
- Compare against any region-level totals returned by the API.
- `region_reconciliation_variance` = region_total − sum_of_branch_totals.

## Formatting Rules

These rules apply to every output and are typically stated in `answer_template.json`. When the template is silent, apply these defaults:

- **Currency values**: round to 2 decimal places.
- **Percent and ratio fields**: round to 4 decimal places (e.g., `0.1234` for 12.34%).
- **Lists of IDs**: sort in ascending, stable order by ID string unless a `rank` field explicitly governs the order.
- **Per-musician arrays**: sort by `musician_id` ascending.
- **Conflict flags**: sort alphabetically.
- **Pay type lists**: use the order from the rate book (`Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`).

## Workflow

1. **Read all inputs**: `prompt.txt`, `payloads/environment_access.json`, `payloads/request_memo.json`, `payloads/answer_template.json`.
2. **Resolve the environment**: substitute `<TASK_ENV_BASE_URL>` with the base URL from the root `environment_access.md`.
3. **Identify endpoints**: from `payloads/environment_access.json`, determine which endpoints to call.
4. **Fetch all needed data**: call every relevant endpoint. Use query-string filters when the request_memo implies them (e.g., `?branch_id=BR-004` or `?ensemble_id=ENS-REDWOOD`).
5. **Compute and derive**: follow the computation rules above to produce derived fields not directly in the API response.
6. **Assemble the answer**: produce a single JSON object whose top-level keys match `required_top_level_keys` from the answer template.
7. **Apply formatting**: round currencies to 2 decimals, percents to 4 decimals, sort lists as specified.
8. **Validate**: confirm every required key is present and every value matches its declared field type.

## Domain-Specific Notes

### Branch Close (Finance)

- The `period_convention` object captures the period map: which M-labels map to which FY strings, plus the labels for the current and prior close months.
- `m24_income_statement` uses the records for the target branch at the specified close period.
- `mom_revenue_variance` compares the close period's revenue against the prior period's revenue.
- `fy2025_vs_fy2024` compares full-year aggregates for the target branch.
- `region_context` provides region-level FY2025 EBITDA and the target branch's EBITDA rank within that region.
- `branch_rankings` covers cross-branch comparisons: sales growth rank, top sales growth branch, and top ARPU branch.

### Regional Reporting (Finance)

- Aggregate branch-level records across all branches in the region for FY2024 and FY2025.
- Compute region-level EBITDA and the EBITDA margin, ARPU, and sales per labor headcount for FY2025.
- Identify the top and bottom branch by FY2025 EBITDA within the region.
- Compute `region_reconciliation_variance` if the API provides a region-level total.

### Compensation Summary

- Use the rate book to identify all pay types and their rates.
- From the roster, compute quarterly totals and pay-type totals for the current year.
- `combined_overscale_employee_count`: count of employees who have overscale notes or amounts on their roster entry.
- `partial_quarter_employee_count`: count of employees whose roster indicates service in fewer than all four quarters.
- `largest_pay_type`: the pay type with the largest annual total.

### Payroll Review

- Load the production from `/api/payroll/productions` using the `production_id`.
- Count services by type, sum category totals, compute per-musician totals.
- Check for CBA conflict flags by inspecting service start/end times, durations, and limits from the rate book.
- Return the `top_paid_musician_id`.

### Compensation Forecast

- Load the scenario from `/api/compensation/scenarios` using `scenario_id` and `ensemble_id`.
- Extract annual totals, compute growth rates, and pull year_plus_2 quarter and pay-type detail directly from the scenario object.
- Determine `largest_growth_pay_type` by comparing year_plus_2 pay type totals against current pay type totals (largest absolute increase).

## Error Handling

- If an API endpoint returns an error or unexpected shape, log the status and response body for debugging and do not fabricate data.
- If a required field cannot be computed (e.g., division by zero for a margin when revenue is zero), return `null` or `0` as appropriate to the field type and note the absence in any logging.
- If the request_memo specifies an ID that does not appear in API responses, treat it as a data-missing condition and do not guess values.
