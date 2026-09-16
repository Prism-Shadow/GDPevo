---
name: finance-ops-json-reporter
description: Use this skill whenever a prompt asks you to pull data from a finance operations task environment and return one structured JSON report or forecast. Trigger it for monthly close packages, regional management views, compensation summaries or forecasts, and payroll review requests, especially when the prompt includes an environment access file, a request memo, and an answer template.
---

# Finance Ops JSON Reporter

This skill turns a task bundle into one JSON object.

## Read first

Read the prompt, `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json` together. The template is the contract. The memo names the target entity and report focus. The access file tells you which API family to use. If the prompt and template disagree, trust the template for output shape and the memo for scope.

Training examples are shape references only. Derive every value from the live API.

## Workflow

1. Identify the report family from the memo and available endpoints.
2. Resolve every entity ID and label from live data. Do not infer branch names, region membership, pay types, roster counts, or period mappings from memory.
3. Build a small scratch table from the raw data before you calculate totals, ratios, or rankings.
4. Compute each requested field from source records or rate books, then cross-check the totals against each other.
5. Write one JSON object only. No prose, no markdown, no code fences.
6. Match the template's keys, nesting, and field names exactly. Do not add extra keys.
7. Apply the template's ordering rules:
   - keep lists in the requested order
   - sort branch IDs ascending when requested
   - sort `per_musician` by `musician_id`
   - sort flag lists exactly as specified
8. Round currency values to 2 decimals and percent or ratio values to 4 decimals unless the template says otherwise.
9. Before finishing, do a final shape check against the template.

## Common formulas

- `variance_amount = current - prior`
- `growth_pct = variance_amount / prior`
- `ebitda_margin = ebitda / revenue`
- `sales_per_labor_headcount = revenue / labor_headcount`
- `region_reconciliation_variance = computed region total - sum of included branch totals`

Use the report's requested comparison horizon. Do not assume calendar quarters or fiscal-year boundaries unless the period map confirms them.

## Finance reports

Use the finance endpoints when the task asks for close packages, branch reporting, regional views, or FY comparisons.

- Use `/api/finance/period-map` to map period labels to fiscal years and current/prior period conventions.
- Use `/api/finance/branches` to resolve branch names, branch IDs, and region membership.
- Use `/api/finance/accounts` and `/api/finance/records` to compute income statements, month-over-month movement, FY comparisons, EBITDA, margins, and regional rollups.
- Derive rankings from the computed values, then break ties with stable ID order if needed.
- Treat the requested branch or region from the memo as the scope boundary.

## Compensation reports

Use the compensation endpoints when the task asks for current-year summaries or forecast scenarios.

- Use `/api/compensation/rate-book` and `/api/compensation/rosters`.
- For scenario questions, also use `/api/compensation/scenarios`.
- Sum quarter totals, annual totals, and pay-type totals from the underlying roster and rate data.
- Keep pay-type names exactly as they appear in the rate book.
- Report overscale and partial-quarter counts exactly as requested in the memo.

## Payroll reports

Use the payroll endpoints when the task asks for weekly payroll review or production-level checks.

- Use `/api/payroll/rate-book` and `/api/payroll/productions`.
- Compute service counts, category totals, weekly total, per-musician totals, top-paid musician, and any conflict flags from the production data.
- Keep `conflict_flags` in the exact sorted enum order required by the template.
- Include only nonzero category entries in each musician's `categories` object.

## Final check

- Every required top-level key is present.
- Every nested field matches the template name and type.
- Every list is sorted or ordered as requested.
- Every total reconciles with its source data.
- The response contains only the JSON object.
