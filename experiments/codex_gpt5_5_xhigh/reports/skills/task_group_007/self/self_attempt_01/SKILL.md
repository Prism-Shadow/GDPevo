---
name: northwind-erp-control-desk
description: Use this skill for Northwind Components ERP tasks that require joining API records with a local memo and returning strict JSON decisions for order dispatch, inventory allocation, BOM replenishment, supplier incident scorecards, or supplier quality hold controls. Trigger whenever the user mentions Northwind ERP, shared ERP API, orders, waves, warehouses, inventory, BOMs, purchase orders, incidents, suppliers, allocation, expedite queues, replenishment, or supplier quality review.
---

# Northwind ERP Control Desk SOP

This skill is for solving Northwind Components tasks that provide a prompt, a local memo/request file, an answer template, and a live ERP API. The winning pattern is disciplined data joining: read the task contract, fetch only the relevant ERP records, compute derived fields explicitly, then emit exactly the JSON shape requested by the template.

## First Pass

1. Read the task prompt, every visible memo/request payload, and the answer template before calling the API.
2. Treat the answer template as the output contract. Mirror its top-level keys, enum strings, sort orders, summary fields, and rounding rules.
3. Use the API base URL supplied by the runner or environment access note. The public API index is available at `GET /`; use it to confirm endpoints.
4. Do not inspect local environment source files, hidden answer files, judge endpoints, prior runs, or any gold outputs. The API and visible task inputs are enough.
5. Keep scratch calculations in tables or short scripts when the task has more than a few records. These tasks are easy to get wrong by mental arithmetic.

Common API endpoints:

- `GET /products` and `GET /products/<sku>` for `active`, `supplier_id`, `unit_cost`, `weight_lb`, `safety_stock`, and `overstock_threshold`.
- `GET /customers` and `GET /customers/<customer_id>` for `account_status` and `risk_flag`.
- `GET /warehouses` for warehouse IDs, regions, and ZIP codes.
- `GET /inventory?warehouse_id=&sku=` for `on_hand`, `reserved`, and `quarantined`.
- `GET /purchase_orders?supplier_id=&sku=&status=` for PO coverage and supplier holds.
- `GET /orders?wave=` and `GET /orders/<order_id>` for order headers and lines.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` for parcel quotes.
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` for quality windows.
- `GET /suppliers` for supplier names and quality status.
- `GET /boms` and `GET /boms/<bom_id>` for kit component requirements.

## Field Conventions

Use these conventions unless the task memo says otherwise:

- `gross_available = on_hand - reserved - quarantined`.
- `effective_available = max(0, on_hand - reserved - quarantined - product.safety_stock)`.
- Reserved stock, quarantined stock, and safety stock are protected. Do not consume them for automatic ship, transfer, or replenishment coverage decisions.
- Product master status matters. `active: false` is a product exception even when inventory exists.
- Customer account/risk exceptions override ordinary fulfillment decisions. Use this precedence when the template has matching categories: blocked account, review-required account, fraud watch, credit watch, then none.
- Active PO coverage means status `open` or `confirmed`. Ignore `received` and `cancelled` for future coverage or hold lists unless a task explicitly asks for history.
- A PO covers a shortage only when SKU, warehouse, and ETA satisfy the task's needed-by date. Late POs do not cover immediate gaps.
- Currency is normally rounded to two decimals. Percentages and durations use the precision in the template/request.
- Sort every list exactly as specified. If the template is silent, prefer stable ascending identifiers: supplier_id, order_id, line_id, sku, po_id.

## Strict JSON Habits

Return only the final JSON object. Do not include commentary around it.

Before finalizing:

- Confirm every required top-level key is present.
- Confirm every record has all required item keys, even when values are empty lists, `null`, or zero.
- Include all required count buckets in summaries, including zero-count enum buckets.
- Round numeric currency after summing, not before, unless the task says otherwise.
- Use integers for unit quantities and counts.
- Recompute summary totals from the final detail rows, not from an earlier scratch table.

## Order Expedite Workflow

Use this when a task asks for release, hold, review, backorder, shipping quote, or dispatch-control decisions for listed orders.

1. Read the queue memo for the exact order IDs or wave. Fetch each order from `/orders/<order_id>` or `/orders?wave=...`.
2. For each order, fetch its customer, each line's product record, and inventory for the order warehouse and SKU.
3. Compute each line's requested quantity, gross available, effective available, inactive flag, shortage flag, and low-stock flag.
4. Treat a line as a shortage when the requested quantity cannot be covered without consuming protected stock. If gross stock covers the line but effective stock does not, mark the SKU as low stock rather than cleanly ready.
5. Build SKU exception lists independently:
   - `inactive_skus`: inactive product records.
   - `shortage_skus`: SKUs whose requested quantity is not safely available.
   - `low_stock_skus`: SKUs requiring safety-stock/buffer judgment or otherwise flagged by the low-stock rule.
6. Classify inventory status with precedence: inactive plus shortage, inactive only, shortage, low stock, ready.
7. Classify customer exception from the customer record with the task's allowed enum values.
8. Choose final decisions conservatively:
   - no customer exception and ready inventory: release/ship now.
   - low stock but no hard exception: delayed release or monitor, according to template wording.
   - shortage without a higher-priority hold: backorder.
   - inactive product or review-required account: manual review.
   - blocked, fraud-watch, or credit-watch customer: hold or reject-hold.
9. Quote shipping even when the order will not ship if the template requires a quote for every record. Use order warehouse, destination ZIP, order shipping speed, and total order weight: sum `line.quantity * product.weight_lb`.
10. Put the API quote's `zone_distance`, `service_days`, and `total_cost` into the requested quote fields, with currency rounded to two decimals.

## Mixed-Warehouse Allocation Workflow

Use this when a task asks for line-level `ship`, `transfer`, `backorder`, or `manual_review` actions for a wave.

1. Fetch all orders in the wave and sort details by `order_id`, then `line_id`.
2. Fetch all needed customers, products, and inventory records for each relevant SKU at each warehouse.
3. If the customer has an account/risk exception, classify all order lines as manual review for the matching primary reason. These orders belong in account-level blocked/review lists when the template asks for them.
4. If the customer is clear but the product is inactive, classify that line as manual review with an inactive-product reason.
5. Otherwise compute requested-warehouse effective availability.
6. If requested effective availability covers the full line, action is `ship`; `ship_quantity` is the full line quantity and transfer/backorder quantities are zero.
7. If requested effective availability covers part of the line, keep that partial quantity as `ship_quantity` and look for one other warehouse that can cover the uncovered quantity from effective stock.
8. If another warehouse can cover the uncovered quantity, action is `transfer`; set `transfer_from`, `transfer_quantity`, and a transfer request. Choose a deterministic source, preferring enough effective stock and then stable warehouse ordering if there is a tie.
9. If no source warehouse can cover the uncovered quantity, action is `backorder`; `backorder_quantity` is the remaining uncovered quantity.
10. For order rollups, map single-action orders to the template's direct outcome. Use `mixed_actions` when multiple non-manual action types remain on the same order; use `manual_review` when release is stopped by customer or product status.

## BOM Replenishment Workflow

Use this when a production memo names BOMs, build quantities, build dates, a target warehouse, and asks for component coverage, transfers, purchases, exclusions, and totals.

1. Fetch each BOM and build a kit target row from the memo quantity/date plus the BOM name and target warehouse.
2. Expand component demand as `quantity_per_kit * target_build_quantity`. If a SKU appears in multiple BOMs, aggregate its demand, but keep the earliest needed date for coverage timing.
3. Fetch product, target-warehouse inventory, other-warehouse inventory, and open/confirmed POs for each component SKU.
4. Compute target effective availability with the protected-stock formula.
5. Compare demand to target effective availability:
   - If effective availability covers demand, no replenishment is needed.
   - If target stock is already at or above the product overstock threshold, exclude from additional replenishment as overstock.
   - If timely same-warehouse open/confirmed POs cover the gap by the needed date, exclude or mark as PO-covered per template.
6. For remaining gaps, evaluate transfers from other warehouses using their effective availability only. Create transfer requests before buying when feasible.
7. Any remaining gap after target stock, timely POs, and transfers becomes a purchase requisition using the product's supplier and unit cost.
8. Purchase `unit_cost` comes from the product master, not order line price. `extended_cost = quantity * unit_cost`.
9. Coverage PO IDs and supporting PO IDs should be sorted. If only part of a PO is needed for a gap, count only the used quantity in covered-unit totals while still listing the PO ID as support.
10. Summary totals should come from the final component plan, transfer requests, and purchase requisitions.

## Supplier Incident Scorecard Workflow

Use this when the request asks for Q1/monthly supplier incident scorecards, recommendation codes, incident-type splits, costs, percentages, and durations.

1. Read the request's incident date field and window. Most scorecards filter incidents by `open_date` inclusively.
2. Fetch incidents with `/incidents?start=YYYY-MM-DD&end=YYYY-MM-DD`, then apply any additional local filters from the request.
3. Join supplier records for names and `quality_status`.
4. Group only suppliers with at least one filtered incident unless the template says to include zero-incident suppliers.
5. For each supplier compute:
   - incident count.
   - percentage of the full filtered population.
   - total resolution cost.
   - average duration in calendar days.
   - RMA count and WORK_ORDER count.
   - open incident count.
   - severe incident count using the request's severe values, usually `high` and `critical`.
6. Duration rule: closed incidents use `close_date - open_date`; open incidents use `analysis_date - open_date`.
7. Apply recommendation policy in the request's precedence order. Do not invent a different ordering when multiple conditions match.
8. Build escalation lists and highest supplier IDs with deterministic tie-breaking. If the template does not define ties, use supplier_id ascending after the main metric.

## Supplier Replenishment-Control Workflow

Use this when the task asks whether suppliers should be frozen, reviewed, or monitored based on recent quality risk and active POs.

1. Read the target supplier IDs and analysis window from the memo.
2. For each target supplier, fetch supplier master data, incidents in the window, and purchase orders for that supplier.
3. Count recent incidents, RMA incidents, severe/critical incidents, and open incidents. Build sorted affected SKU and sample incident ID lists; cap samples at the template's maximum.
4. Active held POs are only `open` or `confirmed` POs for suppliers whose decision requires a hold or buyer review. Exclude received and cancelled POs.
5. Use conservative decision precedence:
   - `freeze_new_replenishment` for quality-hold suppliers or severe active quality risk such as critical/open incidents.
   - `buyer_review_required` for watch suppliers or suppliers with multiple recent incidents, RMAs, severe incidents, or open incidents that do not meet freeze criteria.
   - `monitor_only` for approved suppliers with low recent risk.
6. Put monitor-only suppliers in the release list. Keep held PO IDs sorted per supplier and as a unique global list.
7. Recompute summary counts from the final supplier decision rows.

## Pitfalls

- Do not use prompt examples as cached facts. Always fetch current API records.
- Do not confuse product `unit_cost` with sales order `unit_price`.
- Do not treat safety stock as available for automatic fulfillment.
- Do not let customer exceptions disappear when inventory is also short; account/risk status still controls release.
- Do not classify inactive SKUs as ordinary shortages. Preserve inactive-product exception lists and reasons.
- Do not include late POs as coverage for a build or replenishment gap.
- Do not include cancelled or received POs in held PO lists for procurement controls.
- Do not forget shipping quotes for held/backorder orders when the template has a quote object for every record.
- Do not round percentages to whole numbers unless the template asks; many scorecards require one decimal.
- Do not emit narrative text, markdown fences, or comments around the JSON.
