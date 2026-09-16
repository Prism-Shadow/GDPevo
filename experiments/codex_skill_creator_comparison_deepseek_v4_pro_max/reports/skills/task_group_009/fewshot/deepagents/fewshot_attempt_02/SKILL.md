---
name: crescent-finance-ops
description: "Computational financial operations for Crescent Arts Collective — branch management reporting, compensation summaries and forecasts, and weekly production payroll. Use when a task requires reading from the Crescent Finance Ops API (branches, records, period-map, accounts, compensation rate-book/rosters/scenarios, or payroll rate-book/productions), computing derived metrics (EBITDA, ratios, variances, growth rates, compensation pay-type totals, payroll service categories), and producing a structured JSON answer. Triggers on requests involving: branch close packages, regional reporting, ensemble compensation, board forecasts, or theatre payroll review."
license: MIT
compatibility: designed for deepagents-code
---

# Crescent Finance Ops

Compute financial reports from the Crescent Finance Ops API. This skill covers three domains: branch management reporting, ensemble compensation, and weekly production payroll.

## Workflow

Every task follows the same four-step pattern:

1. **Load the request context** — read `payloads/environment_access.json` for the base URL and `payloads/request_memo.json` for query parameters.
2. **Read the answer template** — it defines the output shape, field types, and rounding rules.
3. **Fetch and compute** — pull data from the relevant API endpoints and apply the domain rules in the reference files below.
4. **Return one JSON object** — no extra text, no commentary, no markdown wrapping.

## Rounding

- Currency values: 2 decimals
- Percent and ratio fields: 4 decimals
- Lists ordered by ascending stable ID unless a rank field or the template says otherwise.
- `conflict_flags` sorted alphabetically.

## Domain Reference Files

Load the reference file for the domain the request falls into:

- **Branch reporting** (finance endpoints: branches, period-map, accounts, records): read [references/finance.md](references/finance.md).
- **Compensation** (rate-book, rosters, scenarios): read [references/compensation.md](references/compensation.md).
- **Payroll** (rate-book, productions): read [references/payroll.md](references/payroll.md).

A task may combine multiple domains. Load all relevant reference files.

## API Conventions

All endpoints return JSON arrays or objects at the paths listed in `payloads/environment_access.json` and `/api/manifest`. The base URL comes from the task's `payloads/environment_access.json`. No authentication is required.

### Key endpoints by domain

| Domain | Endpoints |
|---|---|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` |

## General Computation Approach

For all domains:

1. Fetch every endpoint listed in the request's `payloads/environment_access.json` once; reuse results across all calculations.
2. Derive all intermediate values (revenue, cogs, gross_margin, sga, allocations, ebitda, etc.) programmatically from category sums, never from hard-coded numbers.
3. Compute ratios only after all numerator and denominator sums are finalized.
4. Check the answer template's `required_top_level_keys` to confirm every key is present before returning.
5. Do not wrap the result in a list, envelope, or markdown code block — return a raw JSON object.
