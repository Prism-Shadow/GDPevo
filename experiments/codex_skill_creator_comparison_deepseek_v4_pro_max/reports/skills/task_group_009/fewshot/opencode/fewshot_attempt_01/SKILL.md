---
name: crescent-finance-ops
description: Generate structured finance, compensation, and payroll reports for Crescent Arts Collective by fetching data from the Crescent Finance Ops API and computing derived metrics. Use this skill whenever a task references Crescent Arts Collective, a branch/ensemble/production ID (like BR-XXX, ENS-XXX, PROD-XXX), the Finance Ops API, close-period or fiscal-year reporting, compensation summaries, weekly payroll packages, regional management views, or board compensation forecasts. Do not use for generic finance questions unrelated to this system.
---

# Crescent Finance Ops Reporting

Use this skill when generating operational reports for Crescent Arts Collective from the Finance Ops API. The skill covers three reporting domains: finance (branch/regional close reports), compensation (ensemble summaries and forecasts), and payroll (weekly production packages).

## Workflow

Every task in this system follows the same pattern:

1. **Read the three input files** from the `payloads/` directory:
   - `prompt.txt` — natural-language task description and reporting focus
   - `request_memo.json` — target entity ID, period/year parameters, and review focus areas
   - `answer_template.json` — exact output JSON schema with required keys, field types, and formatting rules

2. **Read the environment access file** at `payloads/environment_access.json` for the base URL. All API calls use this base URL.

3. **Fetch all relevant API data** in parallel. Map the request memo to the correct API endpoints (see [Domain Reference](references/domain-reference.md)).

4. **Compute derived metrics** following the exact formulas in [Formulas](references/formulas.md).

5. **Assemble the output JSON** to match the answer template schema. Follow all formatting rules in [Output Conventions](references/output-conventions.md). Write the final JSON to `answer.json` or wherever the task specifies.

## Step 1: Understand the Request

Read `payloads/prompt.txt` first for the task context and reporting focus. Then read `payloads/request_memo.json` to extract the target parameters:

- **Branch close reports**: `target_branch_id`, `close_period` (M-format), `prior_period`
- **Compensation summaries**: `ensemble_id`, `summary_type`
- **Payroll reviews**: `production_id`
- **Regional reports**: `target_region_id`, `requested_comparison_years`
- **Compensation forecasts**: `ensemble_id`, `scenario_id`, `forecast_years`

Finally, read `payloads/answer_template.json` for the output schema. Pay attention to `required_top_level_keys`, `field_types`, and any rounding or ordering rules in the `description` field.

## Step 2: Fetch API Data

Read `payloads/environment_access.json` for the `base_url`. Common endpoints by domain:

| Domain | Uses |
|--------|------|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` |

The request memo usually includes `available_endpoints` — fetch all of them at the start. See [Domain Reference](references/domain-reference.md) for the data structures returned by each endpoint.

Fetch all needed endpoints in parallel using curl or similar HTTP calls. All endpoints return JSON arrays or objects.

## Step 3: Compute Results

Use the formulas in [Formulas](references/formulas.md) to derive metrics from raw API data. Key computations include:

- **Finance**: Revenue, COGS, gross margin, SG&A, allocations, EBITDA, EBITDA margin, ARPU, sales per labor headcount, growth rates
- **Compensation**: Pay type totals from rate book × roster weeks, quarter totals, overscale counts
- **Payroll**: Per-service type pay, category totals, premium calculations, conflict flag detection
- **Forecast**: Apply scenario growth rates to current-year compensation

The [Formulas](references/formulas.md) reference covers every computation with worked examples. Do not improvise; these formulas are the single source of truth for all derived values.

## Step 4: Format the Output

Apply the output conventions in [Output Conventions](references/output-conventions.md):

- Currency values rounded to 2 decimal places
- Percentage and ratio values rounded to 4 decimal places
- Lists ordered by ascending stable ID unless a rank field states otherwise
- All required top-level keys present in the exact structure from the answer template

Write the result as a single JSON object. The task prompt will indicate where to save it (typically `answer.json` in the working directory).

## Common Pitfalls

- **Period mapping**: M1–M12 are FY2024, M13–M24 are FY2025. Do not confuse month numbers with period labels.
- **Revenue = product_revenue + service_revenue**: These are separate accounts; sum them.
- **COGS = direct_materials_cogs + direct_labor_cogs**: Same pattern.
- **SG&A = sales_sga + admin_sga + occupancy_sga**: Three accounts.
- **EBITDA = revenue - COGS - SG&A - allocations**: Not revenue - COGS - SG&A alone.
- **EBITDA margin = EBITDA / revenue**: Not divided by gross margin.
- **ARPU uses active_customers, not revenue_units**: `revenue / active_customers`.
- **Sales per labor headcount uses labor_headcount**: Not admin_headcount.
- **Growth rates**: `(new - old) / old`; ensure the denominator uses the older period.
- **Compensation**: Use roster quarter weeks (from the roster record), not a fixed 13-week default, for employees with partial-quarter schedules.
- **combined_overscale_includes_title**: When true, do not add a separate titled position premium for that employee; the overscale amount already includes it.
- **Forecast years**: Add one year of service for Year+1 and two years for Year+2 before assigning seniority bands.
- **Payroll rehearsal pay**: Hourly with a 3-hour minimum call duration.
- **Vacation**: 4% of base service pay plus premiums, only when `vacation_eligible` is true.
- **Payroll guarantee adjustment**: Applies only to regular players (not substitutes) when base service pay is below the weekly guarantee amount.
- **Substitute adjustment**: Deduct substitute service pay (audit + performance + doubles) from each regular musician's total. Add substitute pay as a separate line item for the substitute musician only.
