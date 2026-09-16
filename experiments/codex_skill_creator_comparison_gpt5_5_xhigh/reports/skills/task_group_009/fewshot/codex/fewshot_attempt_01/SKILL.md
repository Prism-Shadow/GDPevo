---
name: crescent-finance-ops-reports
description: Solve Crescent Finance Ops reporting tasks from the staged API data. Use when asked to prepare branch close packages, regional management views, current-year or forecast compensation summaries, or weekly payroll reviews from the Crescent Finance Ops environment.
---

# Crescent Finance Ops Reports

## Workflow

1. Read the request memo, answer template, and environment access payload.
2. Call `/api/manifest` first to confirm the available endpoints and entity sets.
3. Use the matching reference:
   - [Finance reporting](references/finance.md) for branch close packages and regional views.
   - [Compensation reporting](references/compensation.md) for current-year summaries and forecasts.
   - [Payroll reporting](references/payroll.md) for weekly production payroll reviews.
4. Pull only the endpoints needed for that report family.
5. Compute the requested rollups from live API data.
6. Assemble one JSON object that matches the template exactly.
7. Round currency to 2 decimals and percentages or ratios to 4 decimals.
8. Keep list ordering stable and follow any template-specific ordering rule.

## Guardrails

- Treat memo notes as context, not as source of truth.
- Use IDs from the API when the template asks for IDs.
- Preserve the template field names and nesting exactly.
- Reconcile totals against their subcomponents before returning the result.
