---
name: northwind-erp-json
description: Solve Northwind Components ERP API tasks that require JSON-only operational decisions or scorecards from local prompts, payload templates, and live ERP endpoints, including order allocation or expedite waves, BOM replenishment plans, supplier incident scorecards, and procurement quality controls.
---

# Northwind ERP JSON

Use this skill for Northwind Components tasks that combine local payload files with the shared ERP API and require a strict JSON answer.

## Workflow

1. Read the prompt, every file under `input/payloads/`, and especially the answer template. Treat the template as the output contract for keys, enum values, ordering, rounding, and summaries.
2. Get the API base URL from the task prompt or runner. Fetch only public ERP endpoints needed for the requested entities: products, inventory, warehouses, orders, customers, suppliers, purchase orders, BOMs, incidents, and shipping quotes.
3. Prefer deterministic computation with `jq` or Python. The helper at `scripts/northwind_erp.py` can fetch records and provides reusable formulas for effective stock, dates, grouping, rounding, and quotes.
4. Build row-level records first, sort them as required, then derive rollups and summaries from those records. Return JSON only, with empty lists and zero counts included when required.

Some individual resource endpoints may not be available even when list endpoints are. If a detail route returns 404, fetch the list endpoint and filter by id.

## Shared Formulas

Use product master data for `active`, `safety_stock`, `overstock_threshold`, `supplier_id`, `unit_cost`, and `weight_lb`.

For an inventory record:

```text
raw_available = on_hand - reserved - quarantined
effective_available = raw_available - product.safety_stock
usable_units = max(0, effective_available)
```

Safety stock is protected. Do not use reserved, quarantined, or safety-stock units for shipping, transfer, kit coverage, or source-warehouse availability unless the prompt explicitly overrides this.

For order shipping quotes, compute order weight as the sum of `line.quantity * product.weight_lb`. Call:

```text
GET /shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&speed=...
```

Use the order's `shipping_speed` as `speed` when present. Read `zone_distance`, `service_days`, and `total_cost` from the API response, and round currency to two decimals in the final answer.

## Order Decisions

Join each order to its customer, product lines, requested warehouse inventory, and shipping quote.

Customer/product precedence:

- Customer-level stops apply to every line/order before automatic release: blocked account, review-required account, fraud watch, and credit watch.
- Product inactivity is a product-master stop. In line-level allocation tasks it can stop only that line when the account is otherwise releasable.
- Still compute inventory exception lists even when a customer stop determines the final order decision.

Inventory classification:

- A line is short when requested-warehouse `usable_units` is less than the line quantity.
- A SKU is low-stock when it is active and shippable but the requested warehouse is close to protected stock, typically when effective availability is positive but no greater than that SKU's safety stock.
- An order with inactive and short lines should preserve both exception lists and use the template's combined status if one exists.

Allocation pattern:

- `ship`: requested warehouse can cover the full line.
- `transfer`: requested warehouse can ship a partial or zero quantity and one source warehouse can cover the uncovered quantity from its usable units.
- `backorder`: current usable stock across allowed warehouses cannot clear the uncovered quantity.
- `manual_review`: account, risk, or inactive-product rules prevent automatic release.

For transfer lines, `ship_quantity` is the requested warehouse's usable portion capped at the line quantity; `transfer_quantity` is the remaining line quantity. Source warehouses contribute only positive effective availability. If several sources can cover a line, use the task's ordering rule; otherwise choose a deterministic source and explain it only through the required fields.

Expedite pattern:

- Map blocked, fraud-watch, or credit-watch customers to hold/reject style decisions when those enum values exist.
- Map review-required accounts to manual review.
- With no account stop, inactive products route to product-master review, shortages to backorder, low stock to delayed release/monitoring, and ready orders to ship/release.
- Always include the shipping quote even for held, review, or backorder orders when the template asks for it.

## BOM Replenishment

For each requested build, fetch the BOM and multiply each component's `quantity_per_kit` by the requested build quantity. Aggregate `total_required` by SKU, but keep per-date requirements for `needed_by` decisions.

For the target warehouse:

1. Compute `target_effective_available`.
2. If the target is already above the product overstock threshold, exclude or mark overstock as the template allows.
3. Compute the gap after target usable stock.
4. Count eligible timely POs: same SKU, same target warehouse, status `open` or `confirmed`, ETA on or before the component need date.
5. If timely POs cover the gap, record their sorted PO ids and avoid extra transfer/purchase.
6. Otherwise use positive effective availability from non-target warehouses for transfers, then create purchase requisitions for the remaining gap using product `supplier_id` and `unit_cost`.

When a component is needed on multiple build dates, allocate stock, timely POs, and transfers chronologically. Transfer requests normally use the date when those transferred units are first needed; purchase requisitions use the date of the remaining uncovered requirement. Sort transfer rows exactly as the template says, often by SKU, quantity descending, then source warehouse.

## Supplier Incidents

Filter incidents by the prompt's date field and inclusive window, usually `open_date`. Join supplier names and `quality_status`.

Per supplier, compute:

- incident count and percentage of the filtered incident population
- resolution-cost sum
- average duration in calendar days; closed incidents use `close_date - open_date`, open incidents use `analysis_date - open_date`
- incident-type counts
- open incident count
- severe count using the prompt's severity set, usually `high` and `critical`
- affected SKU list and sample incident ids when requested

Apply recommendation or control policies exactly in the prompt, in stated precedence order. For scorecards, evaluate each policy condition from the grouped metrics and supplier status before falling through to the default monitor code.

For procurement control tasks without a more explicit policy, the few-shot pattern is:

- `quality_hold` suppliers freeze new replenishment.
- Non-hold suppliers with a severe/critical cluster require buyer review.
- Otherwise monitor.

Hold PO ids only for suppliers whose decision is not monitor-only. Use `open` or `confirmed` purchase orders, sort ids ascending, and apply any template cap or local memo limit. If the template gives no cap but the shape calls for sample-like control lists, cap per-supplier held PO ids at the first five sorted ids before forming the top-level unique union.

## Output Checks

- Match every required key and enum spelling from `answer_template.json`.
- Sort every list by the stated fields; sort ids lexicographically unless told otherwise.
- Round currency to two decimals, percentages to the requested precision, and durations to the requested precision.
- Recompute summary counts, units, costs, and id lists from the final rows.
- Emit valid JSON only. Do not include commentary outside the JSON.
