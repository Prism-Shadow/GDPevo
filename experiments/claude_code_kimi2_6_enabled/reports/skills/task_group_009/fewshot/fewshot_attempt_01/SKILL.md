# Crescent Finance Ops API Reporting Skill

## Overview
Generate structured JSON reports from the Crescent Finance Ops API. Each task provides `environment_access.json` (base URL + endpoints), `request_memo.json` (parameters and focus areas), and `answer_template.json` (output schema and rounding rules).

## API Usage
1. **Read `environment_access.json`** for `base_url` and `available_endpoints`.
2. **Read `request_memo.json`** for request-specific filters (e.g., `target_branch_id`, `ensemble_id`, `production_id`, `scenario_id`, `close_period`).
3. **Call all relevant endpoints** using the base URL. Use `GET` with query parameters as needed.
4. **Validate** that returned data matches the memo filters (e.g., branch ID, period, ensemble). Reconcile before computing.

## Common Endpoint Patterns
- **Finance**: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`
- **Compensation**: `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`
- **Payroll**: `/api/payroll/rate-book`, `/api/payroll/productions`

## Calculation Rules
- **Currency values**: round to **2 decimal places**.
- **Percent / ratio / margin / growth rate fields**: round to **4 decimal places**.
- **Rankings**: use **descending** order (rank 1 = highest value) unless explicitly stated otherwise.
- **Lists / arrays of IDs**: sort in **ascending** order unless a rank field specifies otherwise.
- **Variance / reconciliation**: compute and include; a variance of `0.0` confirms reconciliation.
- **Growth rates**: `(new - old) / old`. Margins: `ebitda / revenue`.

## Output Conventions
- Return a **single JSON object** matching the `answer_template.json` schema exactly.
- Include all **required top-level keys** listed in the template.
- Use the exact field names and nested structures from the template.
- For pay-type or category totals, sum all applicable line items and round at the final step.
- For quarter totals, aggregate by quarter label (Q1–Q4) from the underlying period map or date fields.
- For per-musician / per-employee breakdowns, group by ID, sum categories, and round each total.

## Pitfalls
- Do not assume static data; always fetch from the API and reconcile.
- Do not omit zero-variance reconciliation fields.
- Do not round intermediate values; round only final reported numbers.
- Watch for partial-period or partial-quarter employees; count them explicitly when requested.
- Overscale and combined-overscale counts are distinct; report both when asked.
- Conflict flags (e.g., `REHEARSAL_EARLY_START`, `SERVICE_OVER_TIME_LIMIT`) must be surfaced exactly as named in the source data.
