---
name: crescent-finance-ops
description: |
  Comprehensive financial reporting for the Crescent Arts Collective Finance Ops API covering three business modules. Finance module for branch P&L, income statements, period-over-period comparisons, regional aggregation, and branch ranking. Compensation module for current-year ensemble pay summaries by quarter and pay type, plus multi-year board forecasts driven by scenario growth rates. Payroll module for weekly theatre production payroll with per-musician service pay, premium rules, vacation, guarantee/substitute adjustments, and CBA conflict-flag detection. Use when a task provides a Crescent Finance Ops base URL and asks for any branch close package, ensemble compensation summary, compensation forecast, regional management report, or weekly payroll review. Also use when the task references payloads/environment_access.json pointing to Crescent endpoints, or describes a request memo with a target branch, ensemble, production, or scenario for this API.
---

# Crescent Finance Ops

Connect to the Finance Ops API and return a single JSON object following the provided `answer_template.json`. Before computing results, always read the current live data from every endpoint the task requires.

## Connection

The task provides `payloads/environment_access.json` with a `base_url` key. Use that base URL for all HTTP GET calls. No authentication is needed.

All endpoints return JSON. Pagination is not required.

## Module Selection

The task defines which module to use through the `available_endpoints` in `environment_access.json` and the `request_memo.json` content:

- **[Finance](references/finance.md)** — endpoints under `/api/finance/`, including branches, period-map, accounts, and records. Used for branch close packages and regional management reports.
- **[Compensation](references/compensation.md)** — endpoints under `/api/compensation/`, including rate-book, rosters, and scenarios. Used for ensemble compensation summaries and board forecasts.
- **[Payroll](references/payroll.md)** — endpoints under `/api/payroll/`, including rate-book and productions. Used for weekly payroll reviews.

Read the relevant reference file when its module endpoints appear in the task.

## Rounding

Currency amounts: round to 2 decimal places.
Percent and ratio values (including growth rates, margins, ARPU, sales_per_labor_headcount): round to 4 decimal places.
Counts and rank integers: whole numbers, no rounding needed.

Use Python's `round(value, n)` for all rounding.

## Answer Template

Always read `payloads/answer_template.json` first. It defines required top-level keys, nested key structure, field types (currency, decimal percent, integer, string, enum, list), and ordering requirements. The template's `required_top_level_keys` is the authoritative output structure. Produce exactly one JSON object whose top-level keys match that list and whose nested structure matches the template's `field_types`. Lists must use ascending stable IDs (branch_id, musician_id, etc.) unless the template or request says otherwise.

## Period Convention (Finance)

The period map spans 24 months across two fiscal years:

- M1–M12  = FY2024
- M13–M24 = FY2025

## Common Workflow

1. GET `/api/manifest` for entity lookups (branch names, region memberships).
2. GET every endpoint in `available_endpoints` from `environment_access.json`.
3. Read `request_memo.json` for the target entity (branch_id, ensemble_id, production_id, region_id, scenario_id, close_period, forecast_years).
4. Read `answer_template.json` for output structure and field types.
5. Compute derived values using the formulas in the module reference.
6. Output the single JSON object following the template, rounding, and ordering rules.
