---
name: crescent-finance-ops-reporting
description: Prepare Crescent Finance Ops JSON reports from task-local environment_access/request_memo/answer_template files. Use this whenever the user asks for a branch close package, regional management view, current-year compensation summary, payroll review, or compensation forecast from the Crescent Finance Ops API, especially when the prompt says to return one JSON object matching a template.
---

# Crescent Finance Ops Reporting

Use this skill for structured finance reporting jobs over the Crescent Finance Ops API.

Read `environment_access.json`, `request_memo.json`, and `answer_template.json` first. The memo tells you what to report; the template tells you the exact shape; the environment file gives you the base URL and allowed endpoints.

Read [references/task-map.md](references/task-map.md) for the family-specific checklist. Open only the section that matches the memo and the template.

## Core workflow
1. Read the three payload files.
2. Read `/api/manifest` from the task environment to confirm the live endpoint set and entity names.
3. Identify the report family from the required top-level keys and memo language.
4. Gather the source records from the smallest endpoint set that can satisfy the template.
5. Compute the requested aggregates.
6. Assemble one JSON object that matches the template exactly.
7. Verify rounding, ordering, and key presence before answering.

## Output rules
- Return JSON only. Do not wrap the result in markdown or commentary.
- Use the base URL from the task payload; never hardcode a different environment.
- Treat `request_memo.json` as the source of truth for IDs, periods, scenario names, and focus areas.
- Match the template exactly: same top-level keys, same nested keys, no extras.
- Use numeric JSON values for amounts, rates, and counts unless the template explicitly asks for a string.
- Round currency to 2 decimals. Round percentages and ratios to 4 decimals.
- Preserve any ordering the template specifies.
- Use exact entity IDs and names from the API. Do not paraphrase labels.
- Prefer the live API over any draft workbook notes or background hints when they conflict.

## Ordering rules
- Sort `branch_ids` ascending unless the template says otherwise.
- Keep `pay_types` in rate-book order.
- Sort `conflict_flags` alphabetically.
- Order `per_musician` by `musician_id`.
- For rank fields, honor the field direction in the name. `*_rank_desc` means a higher value ranks ahead of a lower one.

## Family notes

### Branch close and regional management
Use the finance endpoints:
- `/api/finance/branches`
- `/api/finance/period-map`
- `/api/finance/accounts`
- `/api/finance/records`

Use branches for name and region lookups, the period map for fiscal-year bucketing, accounts for classification, and records for totals. Compute the current-period statement, the prior-period comparison, the fiscal-year view, the regional context, and branch rankings from the requested branch set.

### Compensation summary and forecast
Use:
- `/api/compensation/rate-book`
- `/api/compensation/rosters`
- `/api/compensation/scenarios` for forecast work

Treat the rate book as the pay-type authority, the roster as the employee-level source, and the scenario data as the forward-looking source. Build quarter totals, annual totals, pay-type totals, growth rates, and treatment counts from those sources, and keep the output aligned with the template.

### Payroll review
Use:
- `/api/payroll/rate-book`
- `/api/payroll/productions`

Build service counts, category totals, per-musician totals, conflict flags, and the top-paid musician from the production schedule and roster/rate data. Make sure the musician rows stay ordered and the conflict flags stay sorted.

## Final check
Before answering, confirm:
- every required key from the template is present
- every list is in the required order
- all rounded values meet the template precision
- no scratch fields or explanation text leaked into the final JSON
