---
name: northwind-erp-control-desk
description: Use this skill for Northwind Components ERP evaluation tasks that ask for strict JSON decisions using the shared ERP API, especially dispatch expedite queues, mixed-warehouse allocation, kit replenishment, supplier incident scorecards, procurement quality holds, inventory coverage, purchase orders, BOMs, shipping quotes, customers, suppliers, and products. It gives SOPs for API usage, field conventions, stock math, decision precedence, ordering, rounding, and common pitfalls.
---

# Northwind ERP Control Desk SOP

Use this skill when a task gives a Northwind Components memo plus an `answer_template.json` and asks for a structured ERP decision file. The work is usually less about prose and more about carefully joining live ERP records, applying the memo policy, and emitting exact JSON.

## Access And Source Discipline

1. Read only the visible task prompt, payload memo/request files, `answer_template.json`, and the environment access note supplied for the run.
2. Use the ERP API base URL from the environment access note. If a prompt mentions local startup commands or a local `127.0.0.1` URL, treat that as task boilerplate unless the run explicitly provides that service. In this environment the remote API is the intended source.
3. Do not inspect environment source files, previous answers, hidden outputs, judge endpoints, or task folders outside the visible input area.
4. Start by requesting `GET /` from the base URL and confirm the available endpoint list. Quote URLs that contain `?` or `&` when using a shell, or the shell may interpret them as patterns.
5. Return only the JSON object requested by the template. Do not add explanation, markdown, comments, or extra keys.

## Core API Endpoints

The public API exposes these resources:

- `/orders?wave=&required_date=&customer_id=` and `/orders/<order_id>` for order headers and lines.
- `/products` and `/products/<sku>` for `active`, `supplier_id`, `unit_cost`, `weight_lb`, `safety_stock`, and `overstock_threshold`.
- `/customers` and `/customers/<customer_id>` for `account_status`, `risk_flag`, tier, and account context.
- `/warehouses` for warehouse IDs and origin ZIP/region metadata.
- `/inventory?warehouse_id=&sku=` for `on_hand`, `reserved`, and `quarantined`.
- `/purchase_orders?supplier_id=&sku=&status=` for PO `status`, `eta`, `quantity`, `sku`, `supplier_id`, and `warehouse_id`.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` for parcel quote fields.
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` for supplier-quality incidents.
- `/suppliers` for supplier names and `quality_status`.
- `/boms` and `/boms/<bom_id>` for kit component requirements.

Build small lookup maps by ID (`sku`, `customer_id`, `supplier_id`, `warehouse_id`, `order_id`) before calculating. This prevents subtle mistakes from repeated manual joins.

## Common Field Conventions

- Order lines use `line_id`, `sku`, `quantity`, and `unit_price`; order headers carry `customer_id`, `warehouse_id`, `destination_zip`, `shipping_speed`, `required_date`, `priority`, and `wave`.
- Product `active: false` is a product-master exception. Do not treat inactive SKUs as automatically releasable just because stock exists.
- Customer `account_status` values include `active`, `blocked`, and `review_required`. Customer `risk_flag` values include `none`, `fraud_watch`, and `credit_watch`.
- Supplier `quality_status` values include `approved`, `watch`, and `quality_hold`.
- PO statuses include `open`, `confirmed`, `received`, and `cancelled`. For forward-looking coverage/holds, count only `open` and `confirmed` unless the task says otherwise.
- Incident statuses include `open` and `closed`; incident types include `RMA` and `WORK_ORDER`; severe severities are normally `high` and `critical` when the memo does not override this.

## Stock And Coverage Math

Use explicit stock definitions and keep them consistent in your scratch work:

- `physical_free = max(0, on_hand - reserved - quarantined)`.
- `effective_available = max(0, physical_free - safety_stock)` when the task says not to use protected stock, operating buffer, or asks for effective availability.
- For expedite-style "low stock" checks, a useful distinction is: the line can be fully supplied from `physical_free`, but shipment would consume or dip into the product safety stock. In that case it is not a hard shortage, but it should be listed as low stock if the template has that bucket.
- A shortage exists when the relevant free/effective quantity cannot cover the requested quantity after applying the task's buffer rule.
- For multi-line orders, classify SKU exceptions independently, then choose the order-level status by precedence rather than averaging lines.

Currency is rounded to two decimals. Percentages and durations use the precision stated in the request/template. Sort every list exactly as the template says, including nested lists such as SKU lists, PO IDs, incident IDs, and order IDs.

## Dispatch Expedite Queue SOP

Use this for tasks that list order IDs and ask for release, hold, review, backorder, inventory status, SKU exception lists, and shipping quotes.

1. For each order ID, fetch the live order, customer, all products on the lines, inventory at the order warehouse for each SKU, and a shipping quote.
2. Compute shipment quote weight as `sum(product.weight_lb * line.quantity)` across order lines. Use the order's `warehouse_id`, `destination_zip`, and `shipping_speed` unless the memo explicitly overrides the speed. Map API `total_cost` to the template's USD cost field and round to two decimals.
3. Map customer exception with a stable precedence:
   - `account_status == blocked` -> `account_blocked`
   - `account_status == review_required` -> `review_required`
   - `risk_flag == fraud_watch` -> `fraud_watch`
   - `risk_flag == credit_watch` -> `credit_watch`
   - otherwise `none`
4. Build `inactive_skus`, `shortage_skus`, and `low_stock_skus` as sorted unique SKU lists.
5. Inventory status precedence:
   - inactive SKU plus any shortage -> `inactive_and_shortage`
   - inactive SKU only -> `inactive_sku`
   - any hard shortage -> `shortage`
   - any low-stock line with no hard shortage -> `low_stock`
   - otherwise `ready`
6. Decision precedence:
   - Account block, fraud watch, or credit watch normally stops release: use the hold/reject action named by the template.
   - Account review, inactive product, or other product-master issue normally becomes manual review/escalation.
   - Hard inventory shortage normally becomes backorder.
   - Low stock without a hard stop normally becomes delayed release/monitor.
   - Ready orders with no customer/product exception release to pick/ship now.
7. Summary counts must be recomputed from the final records, not from intermediate assumptions.

## Mixed-Warehouse Allocation SOP

Use this for wave allocation tasks that require line-level `ship`, `transfer`, `backorder`, or `manual_review` decisions.

1. Pull all orders in the requested wave, then join customers, products, requested-warehouse inventory, and alternate-warehouse inventory.
2. Compute `requested_effective_available` with the protected-stock formula. Reserved, quarantined, and safety-stock buffer are not freely available.
3. Customer/account risks and inactive products prevent automatic release. Use `manual_review` with the closest `primary_reason` before attempting transfer/backorder math.
4. For releasable lines:
   - If requested warehouse effective stock covers the full quantity, action is `ship`; `ship_quantity` is the full line quantity and transfer/backorder fields are zero/null.
   - If requested warehouse covers part of the line and one alternate warehouse can cover the remaining quantity from effective stock, action is `transfer`; keep the usable requested quantity as `ship_quantity`, set one `transfer_from`, and transfer only the uncovered quantity.
   - If no alternate warehouse can clear the remaining quantity, action is `backorder`; use any requested effective stock as `ship_quantity` if the template allows partial shipment, and put the remainder in `backorder_quantity`.
5. When multiple source warehouses can cover a transfer, choose deterministically: prefer the source with the largest effective availability for the SKU, then sort by warehouse ID for ties.
6. `blocked_orders` means account/customer-risk stops, not line-only inactive product reviews.
7. Order rollups should describe the set of line outcomes: all ship -> `ready_to_ship`; transfer-only issue -> `needs_transfer`; any backorder-only issue -> `has_backorder`; all/customer-stopped manual review -> `manual_review`; genuinely mixed line outcomes -> `mixed_actions`.

## Kit Replenishment And BOM SOP

Use this for production planning tasks that name BOMs, target build quantities, a planning warehouse, purchase orders, transfers, exclusions, and purchase requisitions.

1. Fetch each named BOM and use the memo's requested build quantity/date, not stale BOM target dates, for the task plan.
2. For each component SKU, sum total required units across all requested BOMs: `quantity_per_kit * target_build_quantity`. If a SKU appears in multiple BOMs, aggregate it once in `component_plan`.
3. Use target warehouse effective stock as current coverage. Compare it to total required units to find the gap.
4. Count timely PO coverage only for the same SKU and target warehouse, with status `open` or `confirmed`, and an `eta` on or before the component's needed date. Use sorted PO IDs in coverage lists.
5. After stock and timely POs, consider feasible transfers from other warehouses using effective available stock. Create transfer requests only for quantities still needed.
6. Any remaining gap becomes a purchase requisition using the product's `supplier_id`, `unit_cost`, target warehouse, needed date, and `extended_cost = quantity * unit_cost`.
7. Exclude components when the gap is already covered:
   - current effective stock covers requirement -> `stocked_no_gap`
   - timely POs cover the gap -> `timely_po_covers_gap`
   - target inventory is already beyond the product's overstock threshold -> `target_overstock`
8. Summary totals should equal the line-level plan: purchase units/cost, transfer units, covered-by-PO units, and component count.

## Supplier Incident Scorecard SOP

Use this for Q1 or other supplier-quality scorecards based on `/incidents` and `/suppliers`.

1. Filter incidents by the request's date field, usually `open_date`, with inclusive start and end dates.
2. Join supplier names and quality status for each supplier with at least one filtered incident.
3. For each supplier, compute:
   - incident count and share of the full filtered incident population
   - total resolution cost
   - average duration in calendar days
   - RMA and WORK_ORDER counts
   - open incident count
   - severe incident count using the severe values in the request
4. Duration rule: for closed incidents, use `close_date - open_date`; for open incidents, use `analysis_date - open_date`, unless the memo gives a different rule. Do not add an extra day unless explicitly instructed.
5. Apply recommendation policy in the exact precedence order from the request. Once a higher-precedence condition matches, stop evaluating lower codes.
6. Sort scorecard rows and escalation lists exactly as requested. For highest-cost and highest-share fields, choose from the computed supplier rows, with deterministic tie-breaking by supplier ID if the template does not specify a tie rule.

## Procurement Quality-Hold SOP

Use this for supplier replenishment-control tasks that target supplier IDs and ask for freeze/review/monitor decisions.

1. For each target supplier, fetch supplier metadata, filtered recent incidents, and open/confirmed POs for that supplier.
2. Count recent incidents, RMA incidents, severe or critical incidents, and open incidents. Build sorted unique `affected_skus`.
3. `sample_incident_ids` should be sorted and capped at the template limit, commonly five IDs.
4. Use conservative decision precedence when the memo gives policy but not numeric thresholds:
   - `quality_hold` suppliers with recent quality activity or active POs generally warrant `freeze_new_replenishment`.
   - `watch` suppliers, approved suppliers with meaningful recent RMA/severe/open activity, or suppliers needing human judgment generally warrant `buyer_review_required`.
   - Approved suppliers with no material recent risk generally get `monitor_only`.
5. Include open or confirmed PO IDs in `held_po_ids` for suppliers whose decision freezes or requires buyer review. `monitor_only` suppliers normally belong in `release_supplier_ids` and should not add held POs.
6. Recompute global held PO IDs as a sorted unique union from supplier rows.

## Final JSON Quality Check

Before finalizing:

- Validate every required top-level key and every required row key from `answer_template.json`.
- Use only allowed enum strings from the template.
- Ensure all IDs and SKU lists are sorted as specified.
- Recalculate summary counts and totals from the emitted rows.
- Round money to two decimals, percentages/durations to requested precision, and keep integer quantities as integers.
- Include empty arrays where required; do not omit them.
- Remove all scratch notes and return the JSON object only.
