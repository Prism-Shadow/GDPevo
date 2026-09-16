---
name: northwind-erp-decisions
description: Solve Northwind Components ERP decision tasks that combine local memos/templates with live API lookups and require exact JSON output. Use this whenever the prompt mentions the Northwind ERP API, orders, inventory, warehouses, customers, products, BOMs, purchase orders, incidents, suppliers, shipping quotes, expedite queues, replenishment plans, mixed-warehouse transfer decisions, supplier scorecards, or procurement quality holds, even if it does not explicitly say "Northwind" or "JSON".
---

# Northwind ERP Decisions

Use this skill for the Northwind Components task family that turns live ERP data into strict JSON decisions.

## Read first

1. Open the prompt and every file in `input/payloads/`.
2. Treat `answer_template.json` as the contract. Copy its top-level keys, nested keys, enum values, precision, and ordering rules exactly.
3. Treat any memo file as policy. Follow its filters, date windows, and decision rules.
4. If the prompt says to return only JSON, return only JSON. No markdown, no code fences, no commentary.

## Recognize the task family

The template usually tells you what kind of work this is:

- `wave_id` + `records` + `shipping_quote` -> expedite queue
- `task_id` + `kit_targets` + `component_plan` + `purchase_requisitions` -> kit replenishment
- `analysis_window` + `supplier_scorecard` + `top_escalation_suppliers` -> supplier incident scorecard
- `wave_id` + `line_actions` + `transfer_requests` + `order_rollup` -> mixed-warehouse transfer allocation
- `analysis_window` + `supplier_decisions` + `held_po_ids` + `release_supplier_ids` -> procurement quality control

## Solve in this order

1. Identify the task family from the template and memo.
2. Pull the live records needed from the task environment using the supplied base URL.
3. Compute the decision fields from the live records and the memo rules.
4. Build the output from the template outward.
5. Self-check every required key, sort order, count, and rounded value before finalizing.

## Data sources

Use the documented endpoints the task calls for. Typical families are:

- Expedite queues: `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`, `/shipping/quote`
- Kit and replenishment plans: `/boms`, `/products`, `/inventory`, `/purchase_orders`, `/warehouses`
- Supplier incident scorecards: `/incidents`, `/suppliers`
- Mixed-warehouse transfer decisions: `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`
- Procurement quality controls: `/incidents`, `/suppliers`, `/purchase_orders`, `/products`

Prefer bulk endpoints first, then fetch individual IDs that matter. Use the task's base URL from the prompt or environment note; do not hardcode a host.

## Common rules

- Output valid JSON only.
- Keep every required key, even when the value is empty or zero.
- Match list ordering exactly as the template says.
- Round currency to 2 decimals and percentages to the precision requested by the template.
- Keep internal calculations at full precision until the final writeout.
- Do not invent values from older examples.
- Keep IDs, enum values, and status labels exactly as the template defines them.
- If a summary object exists, derive it from the detailed rows and verify the counts reconcile.

## Family-specific checks

### Expedite queue / hold-or-release

- Classify inventory by the live line status and the product state.
- Use customer or account status to choose the decision and next action.
- Get shipping quotes from the live quote endpoint, not from arithmetic guesswork.
- Keep blocked orders limited to account or customer-risk stops, not product-only review cases.

### Kit replenishment / BOM planning

- Aggregate demand across all requested builds.
- Compute target effective availability after protected stock is excluded where the memo says so.
- Use timely same-warehouse purchase orders before creating new purchase requisitions.
- Create transfer requests only for uncovered quantities that can move from another warehouse.
- List excluded components when stock is already covered or should not receive more stock.

### Supplier incident scorecards

- Filter incidents to the requested date window.
- Count by supplier, then compute percentage, cost, average duration, open count, and severe count.
- Apply the recommendation policy in precedence order.
- Include only suppliers with filtered incidents in the scorecard.
- Build the escalation list from suppliers whose final recommendation is `ESCALATE_SUPPLIER`.

### Mixed-warehouse transfer allocations

- Compute requested-warehouse effective availability after reserved, quarantined, and buffer stock are removed.
- `ship_quantity` is the amount released from the requested warehouse.
- For transfer lines, pick one source warehouse for the uncovered quantity and keep any usable requested-warehouse quantity in `ship_quantity`.
- For blocked lines, use `manual_review` with the correct reason.
- Make the order rollup match the line-level actions exactly.

### Procurement quality controls

- Filter recent incidents to the analysis window.
- Populate supplier status, recent incident/RMA/severe/open counts, affected SKUs, and up to five sample incident IDs.
- Hold only the open or confirmed purchase orders that the decision requires.
- Put monitor-only suppliers in `release_supplier_ids`.
- Keep held PO IDs unique and sorted.

## Final self-check

1. Parse the result as JSON.
2. Verify every required top-level key and nested required key exists.
3. Verify each array is sorted as requested.
4. Verify summary totals reconcile with the detailed rows.
5. Remove any accidental prose or trailing commas.
