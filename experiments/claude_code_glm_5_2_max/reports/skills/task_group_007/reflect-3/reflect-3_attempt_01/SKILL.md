# Northwind ERP Fulfillment Solver Skill

Executable experience for solving Northwind ERP fulfillment evaluation tasks against the shared remote API. Covers expedite-queue dispatch, BOM replenishment, supplier incident scorecards, allocation/transfer, and quality-hold procurement review.

## API Access

Base URL: `<remote-env-url>` (remote, HTTP/1.0, closes each connection).

```
curl -sS --max-time 30 '<url>'
```

### Endpoints (all GET unless noted)
- `/health` — manifest with record counts and seed.
- `/products` and `/products/<sku>` — fields: sku, name, category, active, safety_stock, overstock_threshold, supplier_id, unit_cost, weight_lb.
- `/customers` and `/customers/<customer_id>` — fields: customer_id, name, tier, margin_band, account_status (active|review_required|blocked), risk_flag (none|credit_watch|fraud_watch).
- `/warehouses` — warehouse_id (WH_NORTH, WH_CENTRAL, WH_WEST), name, zip, region.
- `/inventory` — filter by ?warehouse_id=&sku=. Fields: on_hand, reserved, quarantined, last_count_date. No record means 0 stock.
- `/purchase_orders` — filter by ?supplier_id=&sku=&status=. Fields: po_id, sku, quantity, eta, status (open|confirmed|received|cancelled), supplier_id, warehouse_id.
- `/orders` — filter by ?wave=&required_date=&customer_id=. Each order has: order_id, customer_id, warehouse_id, destination_zip, shipping_speed (ground|two_day|overnight), priority, required_date, wave, lines[]. Each line: line_id, sku, quantity, unit_price.
- `/orders/<order_id>` — single order.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — returns zone_distance, service_days, total_cost, base_rate, carrier, fuel_surcharge_rate.
- `/incidents` — filter by ?start=&end=&supplier_id=&sku=&incident_type=&status=. Fields: incident_id, supplier_id, sku, warehouse_id, incident_type (RMA|WORK_ORDER), severity (low|medium|high|critical), status (open|closed), open_date, close_date (null if open), resolution_cost, root_cause.
- `/suppliers` — fields: supplier_id, name, region, quality_status (approved|watch|quality_hold).
- `/boms` and `/boms/<bom_id>` — fields: bom_id, name, warehouse_id, target_date, components[] (sku, quantity_per_kit).

### Record counts (seed 7007)
54 products, 40 customers, 3 warehouses, 162 inventory records, 92 POs, 88 orders, 212 incidents, 12 suppliers, 9 BOMs.

---

## Core Business Rules

### Effective Available Stock
```
effective_available = on_hand - reserved - quarantined - safety_stock
```
This single formula drives inventory_status, shortage/low-stock classification, transfer feasibility, and BOM replenishment gaps. safety_stock comes from the product master, not the inventory record.

### Inventory Status Classification (per order)
For each order line at the order's warehouse:
- If product is **inactive** (active=false): line goes to `inactive_skus` list; the SKU is NOT checked for inventory.
- Compute effective_available for active SKUs.
- **shortage_skus**: SKUs where effective_available < 0 (no stock above safety stock at all). These trigger backorder.
- **low_stock_skus**: SKUs where 0 ≤ effective_available < line quantity. Some stock exists but not enough to fill the line. These trigger delayed_release if no shortage exists.
- If effective_available ≥ quantity: line is fully available.

Order-level inventory_status (precedence):
1. `inactive_and_shortage` — has inactive SKU(s) AND has shortage SKU(s) among active lines
2. `inactive_sku` — has inactive SKU(s) but no shortage among active lines
3. `shortage` — has shortage SKU(s), no inactive SKUs
4. `low_stock` — has low_stock SKU(s), no shortage, no inactive
5. `ready` — all lines fully available

**Important**: low_stock_skus and shortage_skus should BOTH be populated for orders that have both types (they are independent lists, not mutually exclusive at the order level). Each individual SKU goes into exactly one list based on its effective_available and quantity.

### Customer Exception Mapping
Check account_status first, then risk_flag:
1. account_status = `blocked` → customer_exception = `account_blocked`
2. risk_flag = `fraud_watch` → customer_exception = `fraud_watch`
3. risk_flag = `credit_watch` → customer_exception = `credit_watch`
4. account_status = `review_required` → customer_exception = `review_required`
5. otherwise → `none`

When account_status is blocked AND risk_flag is credit_watch, use `account_blocked` (account status takes precedence).

### Decision Precedence (expedite queue / allocation)
1. **account_blocked / fraud_watch / credit_watch** → final_decision = `reject_hold`, next_action = `hold_credit_or_fraud`
2. **review_required** → final_decision = `manual_review`, next_action = `send_account_review`
3. **inactive product** → final_decision = `manual_review`, next_action = `escalate_product_master`
4. **shortage** → final_decision = `backorder`, next_action = `create_backorder`
5. **low_stock** → final_decision = `delayed_release`, next_action = `delay_and_monitor`
6. **ready** → final_decision = `ship_now`, next_action = `release_to_pick`

Account status (including review_required) takes precedence over inactive product. Inactive product takes precedence over inventory issues. (Confirmed: review_required → send_account_review is preferred over inactive → escalate_product_master when both apply.)

### Shipping Quote
- Total weight = Σ (product.weight_lb × line.quantity) for ALL lines including inactive SKUs.
- Query: `/shipping/quote?warehouse_id=<order_warehouse>&destination_zip=<order_dest>&weight_lb=<total>&speed=<order_shipping_speed>`
- Extract: zone_distance (integer), service_days (integer), total_cost_usd = round(total_cost, 2).
- Always compute the shipping quote regardless of the fulfillment decision.

### Rounding
- All currency values rounded to 2 decimal places.
- Percentages rounded to 1 decimal place.
- Durations rounded to 2 decimal places.

---

## Task-Specific SOPs

### Task 1: Expedite Queue (Dispatch Control)
**Input**: Wave ID + list of order IDs from a memo.
**Output**: wave_id, records[], summary.

For each order (sorted by order_id):
1. Fetch order, customer, product, inventory data.
2. Classify each line: inactive_sku / shortage (eff < 0) / low_stock (0 ≤ eff < qty) / available.
3. Determine inventory_status (precedence above).
4. Determine customer_exception (mapping above).
5. Determine final_decision and next_action (precedence above).
6. Compute shipping_quote.
7. Populate shortage_skus, inactive_skus, low_stock_skus (each sorted ascending by SKU).

Summary:
- order_count: total orders
- decision_counts: {ship_now, delayed_release, manual_review, backorder, reject_hold} with integer counts
- total_shipping_cost_usd: sum of all shipping_quote.total_cost_usd, rounded to 2 decimals
- blocked_order_ids: orders with reject_hold decision (sorted ascending)
- manual_review_order_ids: orders with manual_review decision (sorted ascending)
- backorder_order_ids: orders with backorder decision (sorted ascending)
- inactive_sku_order_ids: orders with any inactive SKU (sorted ascending)

### Task 2: BOM Replenishment
**Input**: Production memo with BOM IDs, build quantities, build dates, target warehouse.
**Output**: task_id, plan_date, kit_targets, component_plan, transfer_requests, purchase_requisitions, excluded_components, summary.

Steps:
1. For each BOM, compute component demand: total_required = Σ (quantity_per_kit × build_quantity) across all BOMs using that SKU.
2. For shared SKUs (used in multiple BOMs), use the **earliest build_date** as needed_by.
3. Compute effective_available at the target warehouse for each component.
4. Find timely POs: status in (open, confirmed), warehouse_id = target, eta ≤ needed_by date. Sum their quantities as timely_po_qty.
5. Determine exclusion and action (precedence):
   - **target_overstock**: effective_available > overstock_threshold → action = `overstock_excluded`, excluded. (This takes precedence even if stock covers the requirement.)
   - **stocked_no_gap**: effective_available ≥ total_required → action = `no_action_stocked`, excluded.
   - **timely_po_covers_gap**: effective_available + timely_po_qty ≥ total_required → action = `timely_po_covered`, excluded.
   - Otherwise: gap = total_required - effective_available - timely_po_qty > 0 → try transfer then purchase.
6. For components with a gap:
   - Compute spare at each other warehouse: spare = max(0, effective_available at that warehouse).
   - Transfer from the warehouse with **most spare first** (to minimize number of transfers).
   - Transfer qty = min(gap, spare). Subtract from gap.
   - If gap remains after transfers: purchase_requisition_qty = remaining gap.
   - If only transfer covers: final_action = `transfer_only`.
   - If purchase needed: final_action = `purchase_required`.
7. Purchase requisition: supplier_id from product, unit_cost from product, extended_cost = unit_cost × qty, needed_by = earliest build date.
8. Transfer request fields: sku, from_warehouse_id, to_warehouse_id, quantity, needed_by.
   - Sort: sku ascending, then quantity descending, then from_warehouse_id ascending.
9. Summary:
   - component_count: total components
   - total_purchase_units: sum of purchase requisition quantities
   - total_purchase_cost: sum of extended costs (2 decimals)
   - total_transfer_units: sum of transfer quantities
   - timely_po_covered_units: total PO units from timely POs for excluded components (sum of timely_po_qty for components with exclusion_reason = timely_po_covers_gap)

**Common misjudgments**:
- `target_overstock` takes precedence over `stocked_no_gap` when effective > overstock_threshold.
- Use the warehouse with the MOST spare for transfers (not alphabetical order).
- timely_po_covered_units = total PO quantity (335), NOT the gap covered (106).

### Task 3: Supplier Incident Scorecard
**Input**: Date filter on open_date, analysis_date, recommendation policy.
**Output**: analysis_window, summary, supplier_scorecard, top_escalation_suppliers, highest_cost_supplier_id, highest_share_supplier_id.

Steps:
1. Filter incidents: open_date between start_date and end_date (inclusive).
2. Group by supplier_id.
3. For each supplier with filtered incidents:
   - incident_count = count
   - incident_percentage = round(incident_count / total_filtered_count × 100, 1)
   - total_resolution_cost = sum of resolution_cost (2 decimals)
   - avg_duration_days: closed incidents = (close_date - open_date).days; open incidents = (analysis_date - open_date).days; average rounded to 2 decimals
   - rma_count = count where incident_type = RMA
   - work_order_count = count where incident_type = WORK_ORDER
   - open_incident_count = count where status = open
   - severe_incident_count = count where severity in (high, critical)
4. Recommendation code (precedence: ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST > MONITOR):
   - **ESCALATE_SUPPLIER**: (quality_hold AND incident_count ≥ 3) OR any critical RMA OR (rma_count ≥ 3 AND total_resolution_cost ≥ 15000.00)
   - **PROCESS_REVIEW**: work_order_count ≥ 3 AND work_order_count > rma_count
   - **WATCHLIST**: quality_status in (watch, quality_hold) OR incident_count ≥ 4 OR total_resolution_cost ≥ 12000.00 OR severe_incident_count ≥ 2
   - **MONITOR**: none of the above
5. Scorecard sorted by supplier_id ascending.
6. top_escalation_suppliers: ESCALATE_SUPPLIER suppliers, sorted by incident_count desc, then total_resolution_cost desc, then supplier_id asc.
7. highest_cost_supplier_id: supplier with max total_resolution_cost (ties broken by supplier_id ascending).
8. highest_share_supplier_id: supplier with max incident_percentage (ties broken by supplier_id ascending).
9. Summary: filtered_incident_count, supplier_count, total_resolution_cost (2 decimals), overall_rma_count, overall_work_order_count.

### Task 4: Allocation / Transfer Desk
**Input**: Wave ID with mixed-warehouse orders.
**Output**: wave_id, line_actions, transfer_requests, blocked_orders, order_rollup, summary.

For each line (sorted by order_id, then line_id):
1. Check account/risk status:
   - blocked → manual_review, reason = account_blocked
   - fraud_watch → manual_review, reason = fraud_watch
   - credit_watch → manual_review, reason = account_review_required
   - review_required → manual_review, reason = account_review_required
   - If any of these: ship_quantity=0, transfer_from=null, transfer_quantity=0, backorder_quantity=0
2. Check product active status:
   - If inactive → manual_review, reason = inactive_product
3. Check inventory:
   - If eff ≥ qty → **ship** (ship_quantity=qty, no transfer/backorder)
   - If eff < qty:
     - ship_quantity = max(0, eff) (usable stock at requested warehouse)
     - uncovered = qty - ship_quantity
     - Check other warehouses for spare (max(0, eff at each))
     - If any warehouse has spare ≥ uncovered → **transfer** from the one with most spare
       - transfer_from = that warehouse, transfer_quantity = uncovered
     - Else → **backorder** (backorder_quantity = uncovered)
   - reason = insufficient_effective_stock for transfer and backorder

Line action fields: order_id, line_id, sku, requested_warehouse, requested_effective_available, action (ship|transfer|backorder|manual_review), ship_quantity, transfer_from (enum or null), transfer_quantity, backorder_quantity, primary_reason.

transfer_requests: order_id, line_id, sku, from_warehouse, to_warehouse, quantity. Sort by order_id, then line_id ascending.

blocked_orders: orders where ALL lines are manual_review due to account/risk (NOT inactive_product). Sort ascending. This includes orders with account_blocked, fraud_watch, credit_watch, or review_required as the reason.

order_rollup (per order):
- `manual_review` — ALL lines are manual_review
- `ready_to_ship` — ALL lines are ship
- `needs_transfer` — lines are only ship and/or transfer (no backorder, no manual_review)
- `has_backorder` — lines are only ship and/or backorder (no transfer, no manual_review)
- `mixed_actions` — any other combination (including manual_review + backorder, or transfer + manual_review)

**Critical**: manual_review rollup only applies when ALL lines are manual_review. If an order has manual_review on some lines and other actions on others, the rollup is `mixed_actions`.

Summary: total_orders, total_lines, ship_lines, transfer_lines, backorder_lines, manual_review_lines, blocked_orders (count), transfer_units, backorder_units.

### Task 5: Quality Hold / Procurement Review
**Input**: Target supplier IDs, analysis window (start/end dates on open_date).
**Output**: analysis_window, supplier_decisions, held_po_ids, release_supplier_ids, summary.

For each target supplier (sorted by supplier_id):
1. Filter incidents by open_date in analysis window and supplier_id.
2. Compute: recent_incident_count, recent_rma_count, severe_or_critical_count (high|critical), open_incident_count, affected_skus (sorted unique), sample_incident_ids (sorted, max 5).
3. Get all open/confirmed POs for the supplier (all warehouses, all SKUs).
4. Decision logic:
   - quality_hold → `freeze_new_replenishment`
   - watch + severe_or_critical_count ≥ 2 → `buyer_review_required`
   - watch + severe_or_critical_count < 2 → `monitor_only`
   - approved → `monitor_only`
5. held_po_ids per supplier: all open/confirmed PO IDs for freeze and buyer_review decisions; empty list for monitor_only.
6. release_supplier_ids: suppliers with monitor_only decision (sorted).

Summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count, held_po_count, total_recent_incidents.

**Common misjudgments**:
- A watch supplier with only 1 severe incident should be `monitor_only`, not `buyer_review_required`. The threshold is severe ≥ 2.
- held_po_ids should be populated for both freeze and buyer_review decisions (pending review).
- sample_incident_ids: sorted ascending, maximum 5 entries.

---

## Common Misjudgments and Pitfalls

1. **Effective stock formula**: Always subtract safety_stock from the product master. The inventory record does not contain safety_stock.
2. **Account status precedence**: account_status=blocked produces "account_blocked" exception even when risk_flag=credit_watch is also set. Do not use risk_flag to override account_status for the exception value.
3. **review_required vs inactive**: When both apply (customer under review AND product inactive), the next_action is `send_account_review` (account takes precedence), NOT `escalate_product_master`.
4. **target_overstock precedence**: If effective_available > overstock_threshold, classify as `target_overstock` / `overstock_excluded` EVEN IF the stock covers the requirement. This takes precedence over `stocked_no_gap`.
5. **Transfer warehouse selection**: Use the warehouse with the MOST spare effective stock first. Do not use alphabetical order. This minimizes the number of transfer requests.
6. **timely_po_covered_units**: This is the total PO quantity (all eligible PO units), NOT the gap that was covered.
7. **Order rollup manual_review**: Only apply `manual_review` rollup when ALL lines in the order are manual_review. Mixed manual_review + other actions → `mixed_actions`.
8. **blocked_orders**: Includes orders stopped at account or risk level (blocked, fraud_watch, credit_watch, review_required). Does NOT include orders with only inactive_product lines.
9. **low_stock_skus not cleared**: When an order has shortage lines, low_stock_skus should still be populated for lines that are in the low_stock range (0 ≤ eff < qty). Do not clear low_stock_skus for shortage orders.
10. **Shipping weight**: Include ALL line items in weight calculation, including inactive SKUs. The shipping quote is always computed regardless of the fulfillment decision.
11. **Watch supplier threshold**: A watch supplier needs severe_or_critical_count ≥ 2 for buyer_review_required. One severe incident is not enough; it stays monitor_only.
12. **Sample incident cap**: sample_incident_ids is capped at 5 entries, sorted ascending.

---

## Reusable SOP Template

```
1. Identify the task type (expedite / BOM / scorecard / allocation / quality-hold).
2. Fetch all required data from the API (products, customers, inventory, orders, POs, incidents, suppliers, BOMs).
3. Build lookup maps: products by SKU, inventory by (warehouse_id, sku), customers by customer_id, suppliers by supplier_id.
4. For each entity (order/line/component/supplier):
   a. Compute effective_available = on_hand - reserved - quarantined - safety_stock.
   b. Apply classification rules (inventory_status, customer_exception, etc.).
   c. Apply decision precedence (account → product → inventory).
   d. Compute derived values (shipping quotes, transfer quantities, purchase costs).
5. Sort all lists by their specified ordering keys.
6. Round all currency to 2 decimals, percentages to 1 decimal, durations to 2 decimals.
7. Build summary from individual records.
8. Validate JSON structure against the answer template.
```

## Output Field Shapes Quick Reference

### Expedite Queue Record
```json
{
  "order_id": "string",
  "inventory_status": "ready|low_stock|shortage|inactive_sku|inactive_and_shortage",
  "customer_exception": "none|review_required|account_blocked|fraud_watch|credit_watch",
  "final_decision": "ship_now|delayed_release|manual_review|backorder|reject_hold",
  "next_action": "release_to_pick|delay_and_monitor|send_account_review|create_backorder|hold_credit_or_fraud|escalate_product_master",
  "shortage_skus": ["sorted SKU strings"],
  "inactive_skus": ["sorted SKU strings"],
  "low_stock_skus": ["sorted SKU strings"],
  "shipping_quote": {"zone_distance": int, "service_days": int, "total_cost_usd": float}
}
```

### BOM Component Plan
```json
{
  "sku": "string",
  "total_required": int,
  "target_effective_available": int,
  "timely_po_qty": int,
  "transfer_qty": int,
  "purchase_requisition_qty": int,
  "final_action": "no_action_stocked|transfer_only|purchase_required|timely_po_covered|overstock_excluded",
  "coverage_po_ids": ["sorted strings"],
  "exclusion_reason": "none|target_overstock|timely_po_covers_gap|stocked_no_gap"
}
```

### Supplier Scorecard Row
```json
{
  "supplier_id": "string", "supplier_name": "string",
  "incident_count": int, "incident_percentage": float (1 decimal),
  "total_resolution_cost": float (2 decimals), "avg_duration_days": float (2 decimals),
  "rma_count": int, "work_order_count": int,
  "open_incident_count": int, "severe_incident_count": int,
  "recommendation_code": "ESCALATE_SUPPLIER|PROCESS_REVIEW|WATCHLIST|MONITOR"
}
```

### Allocation Line Action
```json
{
  "order_id": "string", "line_id": int, "sku": "string",
  "requested_warehouse": "WH_NORTH|WH_CENTRAL|WH_WEST",
  "requested_effective_available": int,
  "action": "ship|transfer|backorder|manual_review",
  "ship_quantity": int, "transfer_from": "string|null",
  "transfer_quantity": int, "backorder_quantity": int,
  "primary_reason": "none|account_blocked|account_review_required|fraud_watch|inactive_product|insufficient_effective_stock"
}
```

### Quality Hold Supplier Decision
```json
{
  "supplier_id": "string", "supplier_name": "string", "quality_status": "approved|watch|quality_hold",
  "recent_incident_count": int, "recent_rma_count": int,
  "severe_or_critical_count": int, "open_incident_count": int,
  "affected_skus": ["sorted strings"], "sample_incident_ids": ["sorted strings, max 5"],
  "decision": "freeze_new_replenishment|buyer_review_required|monitor_only",
  "held_po_ids": ["sorted strings"]
}
```
