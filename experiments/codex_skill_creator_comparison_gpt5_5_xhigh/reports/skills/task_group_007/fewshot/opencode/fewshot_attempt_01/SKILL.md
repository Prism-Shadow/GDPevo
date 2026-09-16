---
name: northwind-erp-control
description: Solve Northwind Components / Northwind ERP tasks that turn a memo plus live task-environment API data into a strict JSON decision file. Use this skill whenever the prompt mentions Northwind, `<TASK_ENV_BASE_URL>`, `answer_template.json`, dispatch queues, replenishment plans, allocation waves, supplier scorecards, incident reviews, or any other memo-driven ERP workflow that must come back as schema-locked JSON.
---

# Northwind ERP Control

Use this skill for the Northwind control-desk pattern: read the task memo, query the live ERP API, and return JSON that matches the provided template exactly.

## Workflow
1. Read the prompt, memo, and `answer_template.json` together. Treat the template as the shape contract and the memo as the policy source.
2. Identify the task family and its governing rules: date window, target orders or suppliers, build quantities, exception codes, numeric precision, and sort order.
3. Query only the public task environment API from the prompt's `<TASK_ENV_BASE_URL>`. Use the smallest set of endpoints needed for the task. Common endpoints are:
   - `/manifest` for field discovery when the response shape is unclear
   - `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`, `/shipping/quote`
   - `/boms`, `/purchase_orders`
   - `/incidents`, `/suppliers`
4. Derive every output field from live records. Do not reuse old answers, cached snapshots, or memo text as if it were ground truth.
5. Build the final object in scratch space first, then serialize it as plain JSON only. Do not add markdown, commentary, or code fences.

## Task Patterns

### Dispatch and allocation
- Classify each order or line from current customer, product, and inventory state.
- Let account, fraud, or product status override pure stock availability when the template or memo says those statuses control release.
- When a quote is requested, call the shipping quote endpoint and round money to two decimals.
- Keep IDs, lines, and summary lists sorted exactly as the template requires.

### Replenishment and kit build
- Expand each BOM into component demand for the requested build quantities.
- Compare demand with live inventory, feasible transfers, and eligible purchase-order coverage.
- Separate transfer requests, purchase requisitions, and exclusions exactly as the schema defines.
- Prefer the memo's coverage and exclusion policy over ad hoc judgment.

### Supplier quality and incident review
- Filter incidents to the requested analysis window.
- Aggregate by supplier, then compute counts, percentages, costs, durations, and open/severe splits exactly as requested.
- Apply the memo's recommendation policy in precedence order.
- Use the filtered incident population as the denominator for percentages unless the template says otherwise.

## Output Discipline
- Match every required top-level key exactly.
- Preserve required item keys even when a value is empty, null, or zero.
- Sort every list by the schema's ordering rule before finalizing.
- Round currency to two decimals and percentages or durations to the precision in the template.
- Do not invent fields, labels, or prose.
- If the memo and template seem to conflict, use the template for structure and the memo for decision policy.

## Final Check
Before answering, verify:
- every required key is present,
- every enum value is allowed,
- every list is in the right order,
- every derived total matches the line items,
- the output is valid JSON and nothing else.
