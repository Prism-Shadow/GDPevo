---
name: northwind-erp-decision-json
description: Use this skill whenever a task asks for a Northwind Components or shared ERP API dispatch, allocation, replenishment, procurement-control, supplier incident scorecard, BOM, inventory, purchase order, shipping quote, or answer_template JSON. It helps Codex read local task payloads, query the public ERP API, compute decisions and summaries, and return strict JSON matching the provided template.
---

# Northwind ERP Decision JSON

Use this skill for Northwind Components tasks where local payload files define a memo/request and an `answer_template.json`, and the correct answer must be computed from the shared ERP API.

The goal is a single valid JSON object. Do not return markdown fences, commentary, assumptions, or partial records unless the user explicitly asks for analysis instead of the final answer.

## Files To Use

1. Read the user prompt and every file under `input/payloads/`.
2. Treat the local memo/request as task configuration: target IDs, dates, wave names, requested warehouses, build quantities, recommendation policies, allowed actions, sort rules, and precision rules.
3. Treat the public ERP API as the source of truth for live records. Do not inspect task-environment source files, database files, fixtures, or hidden evaluator files.
4. Read `input/payloads/answer_template.json` before computing. Build the output from that template, not from memory.

Optional helpers bundled with this skill:

- `scripts/fetch_erp.py` fetches allowed ERP API paths and can cache the JSON responses.
- `scripts/validate_answer.py` checks a candidate answer against the custom template shape.
- Read `references/northwind_erp_decision_patterns.md` for the detailed domain patterns before solving allocation, dispatch, replenishment, supplier incident, procurement quality, or shipping-quote tasks.

## Solve Workflow

1. **Extract the contract.** List the required top-level keys, required keys for each array item, allowed enum values, ordering rules, date windows, inclusion rules, and rounding precision from the template and memo.
2. **Plan the API joins.** Identify the needed entity sets:
   - Orders usually join to customers, products, inventory, warehouses, and shipping quotes.
   - BOM replenishment joins BOM components, product/supplier data, target-warehouse inventory, other-warehouse inventory, and purchase orders.
   - Supplier scorecards and quality holds join incidents, suppliers, purchase orders, and affected product/SKU fields.
3. **Fetch live evidence.** Query `/manifest` if available, then fetch targeted records or collections from the public endpoints. Use collection endpoints when the task filters by wave, date range, supplier, status, or BOM membership.
4. **Normalize calculations.** Compute effective available inventory, date-window membership, incident durations, percentages, currency, and summary totals in a scratch table before writing the final JSON.
5. **Apply decision precedence.** Account/customer risk and product-master blocks usually stop automatic release before inventory availability is considered. Inventory then decides ship, transfer, backorder, shortage, or replenishment quantities. Supplier recommendations follow the precedence order supplied in the request.
6. **Assemble detail rows first.** Fill every record or line item with the exact keys from the template. Sort arrays using the template's stated sort keys.
7. **Derive summaries from the final detail rows.** Recompute counts, totals, unique ID lists, and rollups from the rows you will output. Do not separately estimate summaries.
8. **Validate and emit.** Parse the final answer as JSON, run the shape checker if useful, confirm no extra prose is present, and return only the JSON object.

## API Fetching

Use the base URL supplied by the task runner or prompt. If using the helper:

```bash
python skill/scripts/fetch_erp.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --path /manifest \
  --path /orders \
  --path /inventory \
  --out-dir api_cache
```

For quote endpoints, include the query string in the path after inspecting the order, warehouse, customer, and service-speed fields:

```bash
python skill/scripts/fetch_erp.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --path "/shipping/quote?origin_warehouse_id=...&destination_warehouse_id=...&service_level=..."
```

If the exact quote parameter names are unclear, inspect `/manifest` and any endpoint error messages rather than guessing silently.

## Validation

After writing a candidate file:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

The validator is intentionally lightweight because the provided templates are custom descriptions, not formal JSON Schema. Use it to catch missing top-level keys, missing required row keys, and obvious type mismatches. Still manually verify calculations, sort order, enum labels, and rounding against the memo/template.

## Quality Bar

- Use the exact enum labels from the current template. Similar labels across tasks are not interchangeable.
- Keep key order close to the template when practical; keep array order exactly as specified.
- Round only at output boundaries unless the memo instructs otherwise.
- Preserve empty lists when the template requires a list and there are no members.
- Use `null` only when the template allows it.
- Do not hard-code entity IDs, wave names, dates, supplier names, SKU lists, costs, counts, or final decisions from previous examples. Every final value must come from the current prompt, current payloads, and current public API records.
