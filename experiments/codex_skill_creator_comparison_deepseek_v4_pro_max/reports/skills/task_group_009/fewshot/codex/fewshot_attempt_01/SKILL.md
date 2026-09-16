---
name: crescent-finance-ops
description: Finance operations reporting for Crescent Arts Collective. Computes branch close packages, compensation summaries and forecasts, weekly payroll reviews, and regional management reports from the Crescent Finance Ops API. Use when the task involves Crescent Arts Collective finance data, branch income statements, period-map conventions, compensation rate-book computations, payroll service calculations, compensation scenario forecasts, or any Crescent-branded reporting package that references an environment_access.json payload with Crescent Finance Ops endpoints.
---

# Crescent Finance Ops

## Overview

Use the Crescent Finance Ops API (a domain-specific REST API) to prepare structured reporting packages. Every task arrives with:

- `environment_access.json` -- base URL and enabled endpoint list
- `request_memo.json` -- target entity IDs, close periods, scenarios, and review focus items
- `answer_template.json` -- required top-level keys, field types, rounding rules, and ordering constraints

The API serves three domains:

1. **Finance** -- branches, period-map, accounts, records
2. **Compensation** -- rate-book, rosters, scenarios
3. **Payroll** -- rate-book, productions

## Quick Start

Approach every Crescent task in this order:

1. Read `answer_template.json` to learn required keys, field types, rounding rules, and ordering constraints.
2. Read `request_memo.json` for target entity IDs and focus items.
3. Read `environment_access.json` for the base URL and available endpoints.
4. Fetch the API data using the allowed endpoints.
5. Compute results following the module-specific patterns in the references below.
6. Return one JSON object conforming exactly to the answer template.

## Module Selection

Match the request to its domain by the endpoints listed in `environment_access.json`:

| Endpoint pattern | Domain | Reference |
|---|---|---|
| `/api/finance/*` | Finance (branch close, regional reporting) | [finance_module.md](references/finance_module.md) |
| `/api/compensation/*` | Compensation (summaries, forecasts) | [compensation_module.md](references/compensation_module.md) |
| `/api/payroll/*` | Payroll (production weekly reviews) | [payroll_module.md](references/payroll_module.md) |

When a request_memo references both `/api/compensation/scenarios` and `/api/compensation/rosters`, it is a **forecast** task. A compensation request without scenarios is a **current-year summary**.

## Structural Conventions

These apply across every Crescent task:

- **Currency rounding**: 2 decimal places exactly (`round(x, 2)`).
- **Percent and ratio rounding**: 4 decimal places (`round(x, 4)`).
- **List ordering**: sort by stable identifier ascending (branch_id, musician_id, etc.) unless a rank field in the template explicitly states otherwise.
- **Period convention**: M1--M12 = FY2024, M13--M24 = FY2025 (always read `/api/finance/period-map` to confirm).
- **Empty/non-applicable fields**: omit a category from per-musician category maps when its amount is zero; include zero-valued keys at the top level only when the answer template declares them required.

## Reference Modules

- **Finance** (branches, period-map, accounts, records): [finance_module.md](references/finance_module.md) -- account aggregation, income statement computation, MoM variance, FY comparisons, region aggregation, and branch rankings.
- **Compensation** (rate-book, rosters, scenarios): [compensation_module.md](references/compensation_module.md) -- pay type computation, title premiums, seniority bands, quarterly and annual totals, roster treatment counts, and scenario forecast arithmetic.
- **Payroll** (rate-book, productions): [payroll_module.md](references/payroll_module.md) -- service rate lookup, rehearsal minimum-call logic, premium stacking, vacation, guarantee and substitute adjustments, conflict flag detection, and per-musician breakdowns.
