# Northwind ERP Operations Reference

Detailed workflows and decision rules for each of the five supply-chain domains.

## Table of Contents

1. [Dispatch Control (Expedite Queue)](#1-dispatch-control-expedite-queue)
2. [Replenishment (Kit Build Planning)](#2-replenishment-kit-build-planning)
3. [Supplier Quality Scorecard](#3-supplier-quality-scorecard)
4. [Allocation Desk (Order-Wave Transfer)](#4-allocation-desk-order-wave-transfer)
5. [Procurement Control (Quality Hold)](#5-procurement-control-quality-hold)

---

## 1. Dispatch Control (Expedite Queue)

Task pattern: A memo lists order_ids for a named wave. The task asks for an inventory-status classification, customer-exception check, final fulfillment decision, next action, SKU exception lists, and a shipping quote for each order.

### Data to Collect

- All orders from /orders filtered to the wave_id.
- /customers/{customer_id} for each order.
- /products/{sku} for every SKU across all order lines.
- All /inventory records.
- /warehouses for warehouse metadata.

### Step-by-Step

1. Filter orders to the target wave.
2. For each order, compute the total shipment weight: sum across all lines of product.weight_lb * line.quantity.
3. For each order, call GET /shipping/quote with the order warehouse_id, destination_zip, total weight, and shipping_speed.
4. Classify inventory status for each order:
   - Compute effective_available at the order warehouse for every line SKU.
   - If any SKU belongs to an inactive product: classify inactive_and_shortage if there are also shortages, otherwise inactive_sku.
   - Otherwise, if any line has quantity > effective_available: classify shortage.
   - Otherwise, if any line has effective_available < product.overstock_threshold (but sufficient for the order): classify low_stock.
   - Otherwise: classify ready.
5. Populate SKU exception lists:
   - shortage_skus: SKUs where effective_available < line.quantity.
   - inactive_skus: SKUs of inactive products on the order.
   - low_stock_skus: SKUs where effective_available < product.overstock_threshold AND effective_available >= line.quantity. Do not include SKUs already in shortage_skus or inactive_skus.
6. Determine customer exception for the order:
   - account_blocked: customer account_status is blocked.
   - review_required: account_status is review_required OR risk_flag is fraud_watch or credit_watch (when account_status is not already blocked).
   - none: otherwise.
7. Determine final_decision (apply in this precedence order):
   - reject_hold: customer_exception is account_blocked.
   - manual_review: customer_exception is review_required OR inventory_status involves inactive AND the customer is not blocked.
   - backorder: inventory_status is shortage (or inactive_and_shortage) AND there is no blocking account status AND no active review_required flag.
   - ship_now: inventory_status is ready AND customer_exception is none.
   - delayed_release: inventory_status is low_stock AND customer_exception is none.
   - If multiple conditions match, use the first matching rule above.
8. Map next_action from final_decision:
   - ship_now -> release_to_pick
   - delayed_release -> delay_and_monitor
   - manual_review -> send_account_review (for customer issues) or escalate_product_master (for inactive product issues without customer exceptions). If both customer and product issues exist on the same order, use send_account_review.
   - backorder -> create_backorder
   - reject_hold -> hold_credit_or_fraud
9. Build summary: order_count, decision_counts per type, total_shipping_cost_usd (sum of all total_cost rounded to 2 decimals), blocked_order_ids, manual_review_order_ids, backorder_order_ids, inactive_sku_order_ids.
10. Sort all lists per the template.

### next_action Selection Note

When an order has both customer-exception and product-master issues:
- Prefer customer-facing actions (send_account_review) over product-master actions (escalate_product_master) when the customer is actively under review.
- Use escalate_product_master only when the inventory_status involves inactive products AND customer_exception is none.

---

## 2. Replenishment (Kit Build Planning)

Task pattern: A production memo names BOMs, target build quantities, target build dates, and a planning warehouse. The answer requires component-level coverage analysis, transfer requests, purchase requisitions, exclusions, and summary totals.

### Data to Collect

- The named BOMs from /boms/{bom_id}.
- All /products.
- All /inventory records.
- All /purchase_orders.
- All /warehouses.

### Step-by-Step

1. Read the production memo for bom_ids, build quantities, build dates, and warehouse_id.
2. Fetch each BOM to get component SKUs and quantity_per_kit.
3. Compute total_required per component SKU: sum across all BOMs targeting that SKU of quantity_per_kit * target_build_quantity.
4. Compute effective_available for each component SKU at the target warehouse.
5. Check POs for timely coverage:
   - Filter POs for the component SKU at the target warehouse.
   - Status must be open or confirmed.
   - ETA must be <= target_build_date.
   - Sum the eligible PO quantities = timely_po_qty.
6. Compute target_effective_available + timely_po_qty. If this covers total_required, the component is timely_po_covered or no_action_stocked; it goes to excluded_components.
7. For components still short, check other warehouses:
   - Compute effective_available at each other warehouse for the SKU.
   - Source transfers from warehouses with positive effective_available.
   - Prefer the warehouse with the most available units.
   - Transfer quantity = min(remaining gap, source_warehouse.effective_available).
   - Needed_by = earliest target_build_date among BOMs requiring this component.
8. After transfers, any remaining gap becomes a purchase_requisition:
   - Use the product supplier_id from /products.
   - unit_cost = product.unit_cost.
   - extended_cost = unit_cost * purchase_requisition_qty, rounded to 2 decimals.
   - needed_by = earliest target_build_date among BOMs requiring this component.
9. Final_action per component:
   - no_action_stocked: target_effective_available >= total_required (already stocked, exclude).
   - transfer_only: transfers cover the gap exactly; no purchase needed.
   - purchase_required: purchase_requisition_qty > 0 (may also include transfers).
   - timely_po_covered: POs cover the gap; component is excluded.
   - overstock_excluded: target_effective_available > total_required (already have too much).
10. Excluded components: any component where final_action is timely_po_covered or overstock_excluded or no_action_stocked. Record the reason and supporting PO IDs.
11. Build summary: component_count, total_purchase_units, total_purchase_cost, total_transfer_units, timely_po_covered_units.

### transfer_qty vs purchase_requisition_qty

- transfer_qty is the amount that can be sourced from other warehouses.
- purchase_requisition_qty = max(0, total_required - target_effective_available - timely_po_qty - transfer_qty).
- If target_effective_available is already negative, treat it as a deficit that must be covered.

---

## 3. Supplier Quality Scorecard

Task pattern: A scorecard request defines an incident date filter, analysis date, recommendation policy, and output shape. The answer is a supplier-level aggregation of incidents with a recommendation code.

### Data to Collect

- All /incidents.
- All /suppliers.

### Step-by-Step

1. Filter incidents: open_date between start_date and end_date (inclusive).
2. Group incidents by supplier_id. Only suppliers with at least one filtered incident get a scorecard row.
3. For each supplier, compute:
   - incident_count: count of filtered incidents.
   - incident_percentage: (supplier_incident_count / total_filtered_incident_count) * 100, rounded to 1 decimal.
   - total_resolution_cost: sum of resolution_cost, rounded to 2 decimals.
   - avg_duration_days: For closed incidents, (close_date - open_date).days. For open incidents, (analysis_date - open_date).days. Average all durations, rounded to 2 decimals. If no incidents with duration data, return 0.0.
   - rma_count: count where incident_type is RMA.
   - work_order_count: count where incident_type is WORK_ORDER.
   - open_incident_count: count where status is open.
   - severe_incident_count: count where severity is high or critical.
4. Apply recommendation policy in precedence order. Check each code conditions top to bottom; use the first match:
   - ESCALATE_SUPPLIER: supplier quality_status is quality_hold with at least 3 filtered incidents, OR any critical RMA, OR at least 3 RMAs AND total filtered resolution cost >= 15000.00.
   - PROCESS_REVIEW: WORK_ORDER incidents >= 3 AND WORK_ORDER > RMA count.
   - WATCHLIST: supplier quality_status is watch or quality_hold, OR filtered incident_count >= 4, OR total filtered resolution cost >= 12000.00, OR severe_incident_count >= 2.
   - MONITOR: none of the above apply.
5. Build top_escalation_suppliers: supplier_ids with recommendation_code ESCALATE_SUPPLIER, sorted by incident_count descending, then total_resolution_cost descending, then supplier_id ascending.
6. Build summary: filtered_incident_count, supplier_count (suppliers with >=1 incident), total_resolution_cost (sum across all filtered incidents), overall_rma_count, overall_work_order_count.
7. highest_cost_supplier_id: supplier with max total_resolution_cost. Ties: pick first by supplier_id ascending.
8. highest_share_supplier_id: supplier with max incident_percentage. Ties: pick first by supplier_id ascending.

### Edge Cases

- A supplier may have zero RMAs and zero WORK_ORDERS. Counts are 0.
- avg_duration_days for a supplier with only open incidents: use (analysis_date - open_date).days.
- avg_duration_days for a supplier with no incidents: 0.0.
- Avoid division by zero in percentage: if total_filtered_incident_count is 0, all percentages are 0.0.

---

## 4. Allocation Desk (Order-Wave Transfer)

Task pattern: A wave of orders is evaluated line-by-line for inventory availability. Lines may ship, transfer from another warehouse, backorder, or be held for manual review. Customer account and product master statuses affect the decision.

### Data to Collect

- All /orders filtered to the wave.
- /customers/{customer_id} for each order.
- /products/{sku} for each line SKU.
- All /inventory records.
- /warehouses.

### Step-by-Step

1. Filter orders to the target wave.
2. For each line, compute requested_effective_available at the order warehouse.
3. Determine the line action in this precedence:
   - Customer checks first (applied at order level, blocking all lines):
     - manual_review with primary_reason = account_blocked: customer account_status is blocked.
     - manual_review with primary_reason = fraud_watch: customer risk_flag is fraud_watch (and account is not blocked).
     - manual_review with primary_reason = account_review_required: account_status is review_required (and account is not blocked, not fraud).
   - Product checks per line (only when customer is clear):
     - manual_review with primary_reason = inactive_product: product.active is false.
   - Inventory checks per line (only when customer and product are clear):
     - ship: requested_effective_available >= line.quantity. Set ship_quantity = line.quantity.
     - transfer: requested_effective_available < line.quantity AND another warehouse can cover the gap using only its positive effective_available. Set ship_quantity = max(0, requested_effective_available), transfer_quantity = line.quantity - ship_quantity, transfer_from = source_warehouse_id.
     - backorder: requested_effective_available < line.quantity AND no other warehouse has enough effective_available. Set backorder_quantity = line.quantity (not just the gap).
   - primary_reason for ship/transfer lines is none. For backorder lines where no other warehouse can cover, it is insufficient_effective_stock.
4. Build transfer_requests: one entry per transfer line (order_id, line_id, sku, from_warehouse, to_warehouse, quantity).
5. Build blocked_orders: all order_ids where any line has primary_reason in account_blocked, fraud_watch, or account_review_required. Sort ascending, deduplicated.
6. Build order_rollup: one entry per order, with outcome:
   - ready_to_ship: all lines are ship.
   - needs_transfer: at least one line is transfer and none are backorder/manual_review.
   - has_backorder: at least one line is backorder and none are manual_review.
   - manual_review: any line is manual_review.
   - mixed_actions: combination of ship/transfer/backorder (none manual_review) with multiple action types.
7. Build summary: total_orders, total_lines, ship_lines, transfer_lines, backorder_lines, manual_review_lines, blocked_orders, transfer_units, backorder_units.

### Transfer Sourcing

- Prefer the warehouse with the highest positive effective_available for the SKU.
- Only count effective_available that is actually available (positive). Do not dip into safety stock of the source warehouse.
- Transfer_quantity = the amount needed to fill the gap, up to the source warehouse effective_available.

---

## 5. Procurement Control (Quality Hold)

Task pattern: A quality hold review memo names specific supplier_ids and a recent-incident date window. The output supplies supplier-level decisions (freeze, buyer review, monitor) with affected SKUs, sample incident IDs, held PO IDs, and summary counts.

### Data to Collect

- All /incidents.
- All /suppliers.
- All /purchase_orders.
- All /products.

### Step-by-Step

1. Filter incidents to the analysis_window (start to end, inclusive on both ends). These are recent incidents.
2. For each target supplier, compute:
   - quality_status: from /suppliers.
   - recent_incident_count: count of filtered incidents for this supplier.
   - recent_rma_count: count where incident_type is RMA.
   - severe_or_critical_count: count where severity is high or critical.
   - open_incident_count: count where status is open.
   - affected_skus: sorted unique SKUs across filtered incidents.
   - sample_incident_ids: up to 5 sorted filtered incident_ids for this supplier. Take the first 5 after sorting ascending.
   - held_po_ids: all open or confirmed PO ids for SKUs supplied by this supplier. Match PO.sku to the product supplier_id. Include all such POs regardless of warehouse.
   - decision: choose based on the policy rules below.
3. Decision policy (apply in precedence):
   - freeze_new_replenishment: recent_incident_count >= 8 AND open_incident_count >= 2 AND recent_rma_count >= 3.
   - buyer_review_required: severe_or_critical_count >= 2 OR (recent_rma_count >= 1 AND recent_incident_count >= 3 AND quality_status is watch or quality_hold).
   - monitor_only: none of the above.
4. held_po_ids: union of all held_po_ids across all supplier_decisions, sorted ascending.
5. release_supplier_ids: supplier_ids where decision is monitor_only, sorted ascending.
6. Build summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count, held_po_count = len(held_po_ids), total_recent_incidents (sum across reviewed suppliers).
7. Sort supplier_decisions by supplier_id ascending.

### PO Matching for Held POs

For each supplier, find POs where:
- po.status is open or confirmed.
- po.sku belongs to a product whose supplier_id matches the target supplier.
- Include all such POs regardless of warehouse.

### Decision Precedence

Only one decision per supplier. Check conditions for freeze_new_replenishment first, then buyer_review_required, and default to monitor_only. When monitor_only, held_po_ids for that supplier is empty [] and no POs are held.

---

## Cross-Domain Rules Summary

| Rule | Applies To |
|------|-----------|
| effective_available = on_hand - reserved - quarantined - safety_stock | All domains |
| Inactive products block shipment | Dispatch, Allocation |
| Customer account_status drives blocking | Dispatch, Allocation |
| customer risk_flag drives manual review | Dispatch, Allocation |
| PO status open/confirmed = timely coverage | Replenishment |
| Transfer only from warehouses with effective_available > 0 | Replenishment, Allocation |
| Sort by primary ID ascending unless template says otherwise | All domains |
| Round USD to 2 decimals, percentages to stated precision | All domains |
| Use <TASK_ENV_BASE_URL> for all API calls | All domains |
