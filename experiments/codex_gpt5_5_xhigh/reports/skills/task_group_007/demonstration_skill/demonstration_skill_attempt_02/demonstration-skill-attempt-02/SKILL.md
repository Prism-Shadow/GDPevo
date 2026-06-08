---
name: demonstration-skill-attempt-02
description: Use for Northwind Components ERP tasks that require JSON answers for dispatch expedite queues, warehouse allocation and transfer waves, kit replenishment planning, supplier incident scorecards, or procurement quality-hold reviews using the local ERP API.
---

# Northwind Components ERP JSON Tasks

Use this skill when a task asks for a structured Northwind Components operations answer from visible memo/template files plus the shared ERP API. Produce only the requested JSON object, matching the task's answer template exactly.

## API Workflow

- Use the public API, not environment files. In this benchmark the shared base URL is `http://127.0.0.1:8100`; if the runner or prompt gives a different public base URL, use that.
- If proxy settings interfere, call the API with `curl --noproxy '*' -sS '<url>'` or configure the HTTP client to bypass proxies for `127.0.0.1`.
- Discover endpoints from `/`. Core endpoints:
  - `/orders?wave=&required_date=&customer_id=` and `/orders/<order_id>`
  - `/products` and `/products/<sku>`
  - `/customers` and `/customers/<customer_id>`
  - `/warehouses`
  - `/inventory?warehouse_id=&sku=`
  - `/purchase_orders?supplier_id=&sku=&status=`
  - `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
  - `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
  - `/suppliers`
  - `/boms` and `/boms/<bom_id>`
- Join records by stable IDs: order `customer_id`, order line `sku`, product `supplier_id`, inventory `(warehouse_id, sku)`, PO `supplier_id`/`sku`, incident `supplier_id`/`sku`.
- Keep all output ordering rules from the template. If no stronger rule is provided, sort IDs ascending.

## Shared Calculations

- `effective_available = on_hand - reserved - quarantined - product.safety_stock`.
- Do not treat reserved, quarantined, or safety stock as freely available.
- For order shipping quotes, compute `weight_lb` as the sum of `line.quantity * product.weight_lb`, then call `/shipping/quote` with order `warehouse_id`, `destination_zip`, computed weight, and `shipping_speed`.
- Currency fields are USD rounded to 2 decimals. Percentages in scorecards are rounded to 1 decimal. Average duration is rounded to 2 decimals.
- Incident date filters are inclusive and use `open_date` unless the request states otherwise.
- Calendar duration is `close_date - open_date` for closed incidents and `analysis_date - open_date` for open incidents.
- Severe incidents are severities `high` or `critical` unless the request supplies a different list.

## Customer And Product Exceptions

For order-release tasks, evaluate customer and product gates before stock actions.

- Customer exception precedence:
  - `account_status == "blocked"` -> `account_blocked`
  - `risk_flag == "fraud_watch"` -> `fraud_watch`
  - `risk_flag == "credit_watch"` -> `credit_watch`
  - `account_status == "review_required"` -> `review_required` or allocation reason `account_review_required`
  - otherwise `none`
- A blocked account outranks other customer risk flags.
- Product `active == false` creates an inactive-product exception for that SKU.
- Customer/account risk stops every line on the order for allocation-style tasks. Product inactivity is line-specific and does not make the order an account-blocked order.

## Expedite Queue Decisions

For queue memos listing order IDs, fetch each order and related customer, product, inventory, and quote data. Output `wave_id`, `records`, and `summary`.

Per record:

- `inventory_status`:
  - `inactive_and_shortage` when any SKU is inactive and any line has a shortage.
  - `inactive_sku` when inactive SKUs exist without shortage.
  - `shortage` when any line's effective available quantity is below its order quantity.
  - `low_stock` when there is no shortage/inactive SKU but at least one line is close to stock protection.
  - `ready` otherwise.
- `shortage_skus`: SKUs whose requested-warehouse effective availability is less than the line quantity. Include inactive SKUs here too if they are also short.
- `inactive_skus`: inactive product SKUs.
- `low_stock_skus`: active SKUs that can ship but remain constrained; a reliable rule is requested effective availability is positive but at or below that product's safety stock, including cases where shipping the line consumes all effective stock.
- Decision precedence:
  - `account_blocked`, `fraud_watch`, or `credit_watch` -> `final_decision: "reject_hold"`, `next_action: "hold_credit_or_fraud"`.
  - `review_required` -> `manual_review`, `send_account_review`.
  - inactive SKU with no customer hold -> `manual_review`, `escalate_product_master`.
  - shortage with no customer/product hold -> `backorder`, `create_backorder`.
  - low stock only -> `delayed_release`, `delay_and_monitor`.
  - ready -> `ship_now`, `release_to_pick`.
- `shipping_quote` is still required even when the order is held, reviewed, or backordered.
- Sort `records` by `order_id`. Sort SKU lists ascending.
- `summary.decision_counts` must include every allowed decision key, including zero counts. Summary ID lists are sorted and based on the final per-order decision/status.

## Allocation And Transfer Waves

For a wave allocation memo, fetch all orders with `/orders?wave=<wave_id>`. Output `wave_id`, `line_actions`, `transfer_requests`, `blocked_orders`, `order_rollup`, and `summary`.

Line-action rules:

- Sort by `order_id`, then `line_id`.
- If the customer has a blocking/review/risk exception, every line is `manual_review`; set `primary_reason` to `account_blocked`, `account_review_required`, or `fraud_watch`.
- If the product is inactive and there is no customer-level stop, the line is `manual_review` with `primary_reason: "inactive_product"`.
- Otherwise compute requested-warehouse effective availability.
- If requested effective availability covers the full line quantity: `action: "ship"`, `ship_quantity` is the full line quantity, transfer/backorder quantities are `0`, `primary_reason: "none"`.
- If requested effective availability cannot cover the line, look for one other warehouse whose effective availability can cover the uncovered quantity without protected stock.
  - `ship_quantity = max(requested_effective_available, 0)`.
  - `transfer_quantity = line.quantity - ship_quantity`.
  - Choose a source warehouse with enough positive effective availability; prefer the largest available donor, then stable warehouse ordering if tied.
  - Add a matching `transfer_requests` row.
- If no source warehouse can cover the shortage, use `action: "backorder"`, `backorder_quantity` as the line quantity unless the template explicitly supports partial backorder, and `primary_reason: "insufficient_effective_stock"`.
- For non-transfer lines, `transfer_from` is `null` and `transfer_quantity` is `0`.

Order rollup:

- All lines `ship` -> `ready_to_ship`.
- Any `transfer` and no manual/backorder mix -> `needs_transfer`.
- Any `backorder` and no manual lines -> `has_backorder`.
- All lines `manual_review` -> `manual_review`.
- Mixed manual/product/stock actions -> `mixed_actions`.
- `blocked_orders` contains only orders stopped by customer/account risk, not line-only inactive-product reviews.

## Kit Replenishment Planning

For production memos, fetch each target BOM, products, inventory, and POs. Output `task_id`, `plan_date`, `kit_targets`, `component_plan`, `transfer_requests`, `purchase_requisitions`, `excluded_components`, and `summary`.

Component calculations:

- `total_required` is the sum across all target builds of `target_build_quantity * quantity_per_kit` for the component SKU.
- `target_effective_available` is effective availability at the planning warehouse.
- Initial gap is `max(total_required - target_effective_available, 0)`.
- Eligible timely POs are same-warehouse POs with status `open` or `confirmed` and `eta` on or before the component need date. Sort `coverage_po_ids` ascending.
- `timely_po_qty` is the sum of eligible PO quantities, but `summary.timely_po_covered_units` counts the gap covered by those POs, not the full PO quantity.
- If target effective availability already exceeds `product.overstock_threshold`, use `final_action: "overstock_excluded"` and `exclusion_reason: "target_overstock"`.
- If there is no gap and the target is not overstocked, use `no_action_stocked` with `stocked_no_gap`.
- If timely POs cover the remaining gap, use `timely_po_covered` with `timely_po_covers_gap`.
- Otherwise, use donor warehouses with positive effective availability. Prefer larger donor effective availability first; create transfer requests until donors are exhausted or the gap is closed.
- `transfer_requests` use the target warehouse as `to_warehouse_id`, sort by `sku`, then quantity descending, then `from_warehouse_id`.
- Transfers should be needed by the earliest target build date requiring that component. Purchase requisitions should be needed by the latest target build date requiring that component unless the prompt says otherwise.
- Any gap left after target stock, timely POs, and transfers becomes a purchase requisition using product `supplier_id` and `unit_cost`; `extended_cost = quantity * unit_cost`, rounded to 2 decimals.

Summary:

- `component_count`: count of unique component SKUs in the plan.
- `total_purchase_units`: sum purchase requisition quantities.
- `total_purchase_cost`: sum extended costs rounded to 2 decimals.
- `total_transfer_units`: sum transfer request quantities.
- `timely_po_covered_units`: sum of requirement gaps covered by timely POs.

## Supplier Incident Scorecards

For scorecard requests, fetch incidents in the requested window and supplier master records. Output `analysis_window`, `summary`, `supplier_scorecard`, `top_escalation_suppliers`, `highest_cost_supplier_id`, and `highest_share_supplier_id`.

Per supplier with at least one filtered incident:

- `incident_count`: filtered incidents for that supplier.
- `incident_percentage`: `incident_count / filtered_incident_count * 100`, rounded to 1 decimal.
- `total_resolution_cost`: sum incident `resolution_cost`, rounded to 2 decimals.
- `avg_duration_days`: average calendar duration, rounded to 2 decimals.
- `rma_count` and `work_order_count`: counts by `incident_type`.
- `open_incident_count`: count where incident `status` is `open`.
- `severe_incident_count`: count of high/critical severities.
- `recommendation_code`: apply the request's policy in its stated precedence order. A common policy is:
  - `ESCALATE_SUPPLIER` for quality-hold suppliers with enough incidents, any critical RMA, or high RMA count plus high cost.
  - `PROCESS_REVIEW` when work orders are at least 3 and exceed RMA incidents.
  - `WATCHLIST` for watch/quality-hold status, high incident count, high cost, or multiple severe incidents.
  - `MONITOR` otherwise.

Scorecard output rules:

- Sort `supplier_scorecard` by `supplier_id`.
- `top_escalation_suppliers` includes only `ESCALATE_SUPPLIER` suppliers, sorted by incident count descending, then total resolution cost descending, then supplier ID ascending.
- `highest_cost_supplier_id` is the supplier with the largest total filtered resolution cost.
- `highest_share_supplier_id` is the supplier with the largest incident percentage; resolve ties by the task's ordering rule or supplier ID ascending.

## Procurement Quality-Hold Reviews

For procurement-control memos, evaluate the listed suppliers over the memo's `analysis_window`. Output `analysis_window`, `supplier_decisions`, `held_po_ids`, `release_supplier_ids`, and `summary`.

Per target supplier:

- Count recent incidents using inclusive `open_date` filtering.
- `recent_rma_count`: recent incidents where `incident_type == "RMA"`.
- `severe_or_critical_count`: recent incidents with severity `high` or `critical`.
- `open_incident_count`: recent incidents with `status == "open"`.
- `affected_skus`: sorted unique SKUs from recent incidents.
- `sample_incident_ids`: sorted incident IDs, capped at 5.
- Candidate held POs are supplier POs with status `open` or `confirmed`; ignore `received` and `cancelled`.
- For compact control packets, cap each supplier's `held_po_ids` at the first 5 sorted candidate PO IDs when the supplier decision is a hold/review action. Use an empty held list for monitor-only suppliers.

Decision guidance:

- `freeze_new_replenishment`: quality status `quality_hold`, especially with multiple recent incidents or severe/critical incidents.
- `buyer_review_required`: watch-status supplier with elevated severe/critical risk or enough recent RMA/severe evidence to justify buyer intervention.
- `monitor_only`: watch or approved supplier that has recent issues but does not meet freeze/review thresholds.
- `held_po_ids`: sorted unique union of per-supplier held POs.
- `release_supplier_ids`: sorted supplier IDs whose decision is `monitor_only`.
- Summary counts are derived from `supplier_decisions`, and `total_recent_incidents` is the sum of recent incident counts across reviewed suppliers.

## Common Pitfalls

- Do not use raw `on_hand` as available inventory.
- Do not read local environment data files when the public API is available.
- Do not let account-level manual review become a per-line stock decision.
- Do not omit shipping quotes for non-release expedite decisions.
- Do not count cancelled or received POs as timely coverage or held replenishment.
- Do not count the full PO quantity in `timely_po_covered_units`; count only the shortage gap it covers.
- Keep `null` JSON values as `null`, not empty strings.
- Include zero-valued summary categories required by the template.
- Match template key names exactly; similar fields use different names across tasks, such as `warehouse_id`, `requested_warehouse`, `from_warehouse`, and `from_warehouse_id`.
