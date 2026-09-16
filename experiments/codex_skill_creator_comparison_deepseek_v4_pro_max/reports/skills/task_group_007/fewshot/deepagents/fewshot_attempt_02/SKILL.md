---
name: northwind-erp
description: "Northwind Components ERP operations and fulfillment decision support. Use when working with the Northwind ERP API at a task-environment base URL to resolve supply-chain desk decisions: expedite-queue order triage, line-level allocation and transfer planning, BOM replenishment, supplier incident scorecards, and procurement quality hold reviews. Triggers on Northwind, Northwind Components, ERP, fulfillment, expedite, allocation, replenishment, BOM, supplier incident, scorecard, procurement quality, inventory status, customer exception, shipping quote, or answer-template JSON tasks."
---

# Northwind ERP Operations

## Workflow

Every Northwind desk task follows the same four-stage pipeline:

1. **Read the inputs** — the prompt, the memo/payload describing the task, and the answer template that defines the required output shape.
2. **Fetch API data** — call the relevant list endpoints (see [API Reference](references/api_reference.md)). Prefer list endpoints with query-parameter filtering over single-resource GETs, which may return 404 for some resources.
3. **Apply decision rules** — use the logic tables in [Decision Logic](references/decision_logic.md). Follow the cascade: customer/account checks first (they can override everything), then product active status, then inventory effective available, then inter-warehouse transfer possibilities, then purchase requisition as the last resort.
4. **Write the JSON answer** — conform exactly to the answer template. Sort lists as specified. Round currency to 2 decimal places, percentages to 1 decimal place.

## Core Calculations

**Effective available** for any SKU at a warehouse: `on_hand - quarantined - reserved`. Never treat reserved or quarantined units as available for new orders.

**Shipping weight** for an order: sum over all lines of `product.weight_lb * line.quantity`. Use the shipping quote endpoint with the order's `warehouse_id`, `destination_zip`, computed weight, and the `shipping_speed` from the order record (or as specified in the memo).

**Timely PO**: a purchase order with status `open` or `confirmed` whose `eta` is on or before the target date, for the relevant SKU and warehouse.

## Desk Types

### Expedite Queue

Input: a queue memo with order IDs, possibly operator notes. Output: per-order record with `inventory_status`, `customer_exception`, `final_decision`, `next_action`, SKU exception lists, and `shipping_quote`.

Steps:
1. Fetch all orders by their IDs, all customers, all products, and all inventory records for the relevant SKUs and warehouses.
2. For each order, classify the customer exception and inventory status. See [Decision Logic](references/decision_logic.md) for the full mapping.
3. Compute shipping weight and call the quote endpoint with the correct warehouse, zip, weight, and speed.
4. Sort records by order_id ascending. Build the summary with counts.

### Allocation (Line-Level Transfer)

Input: a wave ID and a desk memo. Output: per-line `line_actions`, `transfer_requests`, `blocked_orders`, `order_rollup`, and `summary`.

Steps:
1. Fetch all orders for the wave, all customers, all products, and all inventory (all warehouses, for cross-warehouse transfer evaluation).
2. For each line in each order: check customer status first (blocked → manual_review for all lines; review_required → manual_review; fraud_watch → manual_review). Then check product active status. Then compute effective available.
3. For lines with insufficient stock at the requested warehouse but no customer/product block, scan other warehouses for transfer candidates. Prefer the warehouse with the most effective available.
4. Lines where no warehouse can cover → backorder with reason `insufficient_effective_stock`.
5. Blocked orders are those stopped at account/customer level (not product-only). See [Decision Logic](references/decision_logic.md) for the full line-action table.
6. Sort line_actions by order_id then line_id. Sort transfer_requests by order_id then line_id.

### Replenishment

Input: a production memo with BOM IDs, target quantities, dates, and the planning warehouse. Output: `component_plan`, `transfer_requests`, `purchase_requisitions`, `excluded_components`, and `summary`.

Steps:
1. Fetch all named BOMs, all products, all inventory for the planning warehouse plus other warehouses, all purchase orders for the component SKUs, and all suppliers.
2. For each component SKU, compute `total_required = sum(quantity_per_kit * build_quantity)` across all kits.
3. Check target overstock: if effective available already exceeds the product's `overstock_threshold` AND exceeds total_required, exclude with `target_overstock`.
4. Check timely PO coverage: sum open/confirmed PO quantities with eta ≤ build date. If effective + timely PO >= required, exclude with `timely_po_covers_gap`.
5. For remaining gap: scan other warehouses for transfer stock. Remaining after transfers → purchase requisition.
6. For purchase requisitions, use the supplier from the product record. Unit cost from product. Extended cost = quantity * unit_cost, rounded to 2 decimals.
7. Sort component_plan by SKU ascending. Sort transfer_requests by SKU, quantity descending, from_warehouse ascending. Sort purchase_requisitions and excluded_components by SKU ascending.

### Supplier Scorecard

Input: a request JSON with date range, analysis parameters, and recommendation policy. Output: `supplier_scorecard`, `top_escalation_suppliers`, `highest_cost_supplier_id`, `highest_share_supplier_id`.

Steps:
1. Fetch all incidents, all suppliers. Filter incidents to the specified date window.
2. For each supplier with at least one filtered incident, compute: incident count, percentage of the filtered population (rounded to 1 decimal), total resolution cost, RMA count, WORK_ORDER count, open incident count, severe (high or critical) count, and average duration.
3. Duration for closed incidents: calendar days from open_date to close_date. For open incidents: calendar days from open_date to analysis_date.
4. Apply the recommendation cascade in precedence order: ESCALATE_SUPPLIER, PROCESS_REVIEW, WATCHLIST, MONITOR. See [Decision Logic](references/decision_logic.md) for the exact conditions.
5. Sort scorecard rows by supplier_id ascending. Top escalation list: sorted by incident_count descending, total_resolution_cost descending, supplier_id ascending.

### Procurement Quality Review

Input: a memo with an analysis window and target supplier IDs. Output: per-supplier `supplier_decisions`, `held_po_ids`, `release_supplier_ids`, and `summary`.

Steps:
1. Fetch all incidents, target suppliers, and all purchase orders for those suppliers.
2. Filter incidents to the analysis window. For each supplier, count recent incidents, RMAs, severe/critical, open, affected SKUs, and collect up to 5 sample incident IDs.
3. Apply the decision cascade: quality_hold → freeze_new_replenishment; watch + incidents → buyer_review_required; approved + incidents → buyer_review_required; otherwise → monitor_only. See [Decision Logic](references/decision_logic.md).
4. For suppliers with freeze or buyer_review decisions, collect all of their open/confirmed POs into held_po_ids and the supplier's own held_po_ids list.
5. Sort decisions by supplier_id ascending. Sort all ID lists ascending. Held POs are sorted, unique across all suppliers.

## Helper Module

[erp_helpers.py](scripts/erp_helpers.py) provides deterministic Python functions for effective-available, shipping-weight, date-parsing, rounding, filtering, and fetching. Use it to avoid rewriting the same arithmetic in every task. The module expects the API base URL and handles list-endpoint fetching with query parameters.

## Sorting Rules

Every output list must be sorted as specified by the answer template — never return unsorted or insertion-order lists.

- IDs (order, SKU, supplier, PO, incident): string-ascending.
- Transfer requests: SKU ascending → quantity descending → from_warehouse ascending.
- Line actions: order_id ascending → line_id ascending (as integer).
- Scorecard rows: supplier_id ascending. Top escalation: incident_count descending → total_resolution_cost descending → supplier_id ascending.
