---
name: crescent-finance-ops
description: >
  Build structured financial reporting, compensation, and payroll answers
  for Crescent Arts Collective by reading request payloads, querying the
  Crescent Finance Ops API, and computing derived metrics according to
  domain-specific rules. Use this skill whenever the task involves close
  packages, regional management views, ensemble compensation summaries,
  board forecasts, weekly payroll reviews, branch rankings, EBITDA
  analysis, ARPU, MoM variance, CBA conflict flags, or musician pay
  computations for Crescent Arts Collective. Also use it when the user
  mentions Crescent, finance ops, branch close, compensation summary,
  payroll package, or asks you to prepare a reporting JSON from a task
  environment with payloads and an answer template.
---

# Crescent Finance Ops Skill

You are acting as a solver for structured finance tasks against the Crescent
Finance Ops API. Every task expects a single JSON object as the final answer.
Your job is to read the task payloads, fetch the right data from the API, apply
domain computation rules exactly, and return a JSON object that matches the
provided answer template.

---

## Core Workflow

Follow this sequence for every task. Do not skip steps.

### 1. Read the three payload files

Every task workspace contains a `payloads/` directory with three JSON files.
Read all three before you start any computation:

- **`payloads/environment_access.json`** - lists the base URL placeholder and
  the specific API endpoints available for this task. Cross-reference with
  `environment_access.md` in the workspace root to get the actual base URL
  (e.g. `http://task-env:9009/`). If `environment_access.md` is absent, use
  the `base_url` field directly.

- **`payloads/request_memo.json`** - names the target entity (branch ID,
  ensemble ID, production ID, region ID, scenario ID), the relevant periods or
  years, and the reporting focus areas. Every field you need to scope your
  data fetch is here.

- **`payloads/answer_template.json`** - defines the exact output shape.
  `required_top_level_keys` tells you what keys must appear. `field_types`
  tells you the type of each value. `description` may contain rounding and
  ordering rules; follow them precisely.

### 2. Fetch API data

Use `curl` to hit the endpoints listed in `environment_access.json`, combined
with the base URL. Always fetch all endpoint data before computing; some
computations require cross-referencing multiple datasets.

The API is read-only and requires no authentication. Example:

```
curl -s http://task-env:9009/api/finance/branches
curl -s http://task-env:9009/api/finance/records
```

Pipe through `python3 -m json.tool` or parse in a Python script as needed.

### 3. Route to the correct computation domain

The task belongs to one of three domains. Identify it from the endpoints in
`environment_access.json` or from the request memo:

| Endpoints under `/api/` | Domain | Reference |
| --- | --- | --- |
| `finance/` | Branch and regional reporting | [references/finance.md](references/finance.md) |
| `compensation/` | Ensemble compensation | [references/compensation.md](references/compensation.md) |
| `payroll/` | Touring production payroll | [references/payroll.md](references/payroll.md) |

Read the corresponding reference file before computing. Each reference
describes the API data model step by step and the exact formulas for every
derived metric the answer template may ask for.

### 4. Compute and build the answer

Work through each `required_top_level_key` in the answer template. Use the
formulas from the reference file. Keep intermediate values at full precision;
only round at the very end according to the rounding rules.

### 5. Return the JSON object

Return the final answer as a single JSON object. Do not wrap it in markdown
fences or add commentary; the caller expects raw JSON.

---

## Rounding Rules

These apply to every task unless the answer template says otherwise:

- **Currency values**: round to 2 decimal places
- **Percent and ratio fields** (growth rates, margins): round to 4 decimal
  places. Growth rates are decimal form (0.0966, not 9.66%).
- **Lists**: keep in ascending order by stable ID (branch_id, musician_id,
  etc.) unless a rank field or explicit ordering rule says otherwise.
- **Conflict flags**: sort alphabetically.

---

## General Computation Patterns

### Period conventions

The `/api/finance/period-map` maps M1-M24 to fiscal years. The convention for
the Crescent environment is:

- **M1 through M12** maps to the earlier fiscal year (e.g. FY2024)
- **M13 through M24** maps to the later fiscal year (e.g. FY2025)

Always read the period map to confirm the exact mapping; do not hardcode it.

### Account categories

Accounts from `/api/finance/accounts` have a `category` field. Aggregate by
category:

- **revenue** = sum of all accounts with category `"revenue"`
  (product_revenue + service_revenue)
- **cogs** = sum of all accounts with category `"cogs"`
  (direct_materials_cogs + direct_labor_cogs)
- **sga** = sum of all accounts with category `"sga"`
  (sales_sga + admin_sga + occupancy_sga)
- **allocations** = sum of all accounts with category `"allocations"`
  (shared_service_allocations)

### Gross margin and EBITDA

```
gross_margin = revenue - cogs
ebitda = gross_margin - sga - allocations
```

These hold for both single-period and fiscal-year aggregations.

### Operating metrics

- **ARPU** = revenue / active_customers, for the target period or fiscal year
- **sales_per_labor_headcount** = revenue / labor_headcount, for the target
  period or fiscal year
- **ebitda_margin** = ebitda / revenue

### Rankings

Rankings use descending order: rank 1 is best (highest value). When a template
asks for `*_rank_desc`, compute the value for every relevant entity, sort
descending, and assign 1 to the highest.

### Reconciliation variance

When a region template asks for `region_reconciliation_variance`, sum the
region-level aggregates and subtract the sum of branch-level aggregates for
the same metric. The result should be zero if the data is consistent.

---

## Python Scripts

For any computation beyond simple aggregation, especially compensation and
payroll, write a small Python script. It keeps the work auditable and reduces
arithmetic errors. Use the API data as input (pipe from curl or save to a temp
file) and print the final answer JSON to stdout.

---

## Reference Files

- [references/finance.md](references/finance.md) - Branch income statements,
  MoM variance, FY comparisons, regional context, branch rankings, ARPU,
  sales-per-labor-headcount, ebitda_margin
- [references/compensation.md](references/compensation.md) - Ensemble roster
  pay by quarter and pay type, treatment counts, board forecasts with growth
  scenarios
- [references/payroll.md](references/payroll.md) - Weekly payroll totals,
  service counts, category totals, per-musician pay, CBA conflict flags
