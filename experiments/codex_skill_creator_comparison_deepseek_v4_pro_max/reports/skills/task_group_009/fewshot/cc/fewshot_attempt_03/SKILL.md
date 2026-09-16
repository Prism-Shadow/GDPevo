---
name: crescent-finance-ops
description: Complete reporting tasks for Crescent Arts Collective using the Crescent Finance Ops API. Use whenever the user mentions Crescent Arts Collective, Crescent Finance Ops, branch management reporting, compensation summaries, payroll reviews, regional management views, board compensation forecasts, or any request that references Crescent finance/payroll/compensation data. Trigger on any task involving branch close packages, ensemble compensation, production payroll, or regional financial reporting, even when the user does not explicitly name the API.
---

# Crescent Finance Ops

You are working with the **Crescent Finance Ops API**, a REST service that provides financial, compensation, and payroll data for Crescent Arts Collective. Every task follows the same core workflow.

## Workflow

1. **Read the three payloads** provided alongside the user prompt. These live in a `payloads/` directory relative to the prompt:
   - `environment_access.json` -- base URL and the specific endpoints available for this task
   - `request_memo.json` -- the target entity (branch ID, ensemble ID, production ID), the reporting focus, and any special notes
   - `answer_template.json` -- the exact JSON shape to produce, including required keys, field types, and rounding rules

2. **Fetch all endpoint data** listed in `environment_access.json`. Every endpoint is a plain `GET` with no query parameters. Call them all upfront so you have the complete dataset.

3. **Compute the result** by applying the domain business rules from the reference files below. Match each domain to the endpoint group:
   - `finance` endpoints → see [references/finance.md](references/finance.md)
   - `compensation` endpoints → see [references/compensation.md](references/compensation.md)
   - `payroll` endpoints → see [references/payroll.md](references/payroll.md)

4. **Format the final JSON** according to `answer_template.json` and the global formatting rules below.

## Global formatting rules

These apply to every task regardless of domain:

- **Currency values**: round to 2 decimal places.
- **Percent and ratio values** (any field named `*_pct` or `*_margin`): round to 4 decimal places (e.g., 0.1234, not 14.23%).
- **Lists of IDs**: order ascending by the stable identifier string (e.g., `branch_ids` sorted ascending), **unless** the template or request memo specifies a different ordering (like "rank descending").
- **Sorted string lists** (like `conflict_flags`): sort alphabetically.
- **Null/missing values**: never emit keys with `null` values in the final answer unless the template explicitly lists them as required. For currency fields that are always applicable but might be zero, output `0.00`.

## API reference

The API base URL comes from `environment_access.json`. All endpoints return JSON arrays (or objects for rate books). See [references/api_schemas.md](references/api_schemas.md) for the shape of every endpoint.

When you need to understand the raw data before computing, start with `references/api_schemas.md`. For business rule details, move to the domain-specific reference file.

## Task discovery

A task may involve finance, compensation, or payroll -- read the `available_endpoints` in the environment access payload to determine which domain(s) apply. Some tasks span a single domain; others may not. When the request memo lists a `scenario_id`, you will need the compensation scenarios endpoint alongside the rate book and rosters.

## Domain reference files

- [references/finance.md](references/finance.md) -- Branch P&L, period mapping, income statement computation, EBITDA, growth rates, ARPU, sales per labor headcount, rankings
- [references/compensation.md](references/compensation.md) -- Ensemble pay computation, rate book, seniority bands, title premiums, overscale, partial-quarter handling, forecast year adjustments
- [references/payroll.md](references/payroll.md) -- Production payroll, service rates, premiums, vacation, guarantee adjustments, substitute adjustments, conflict detection
- [references/api_schemas.md](references/api_schemas.md) -- Response shapes for every API endpoint
