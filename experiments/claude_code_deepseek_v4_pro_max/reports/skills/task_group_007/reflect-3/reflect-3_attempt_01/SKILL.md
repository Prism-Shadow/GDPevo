# Northwind Components ERP — Operations Skill

## API

Base URL provided at solve time. Primary endpoints:

| Endpoint | Key query params |
|---|---|
| `/orders?wave=&customer_id=&required_date=` | Wave filter, customer |
| `/orders/<order_id>` | Single order detail |
| `/products` , `/products/<sku>` | Active flag, safety_stock, overstock_threshold, weight_lb, unit_cost, supplier_id |
| `/customers` , `/customers/<customer_id>` | account_status, risk_flag, tier, margin_band |
| `/warehouses` | WH_NORTH, WH_CENTRAL, WH_WEST; zip per warehouse |
| `/inventory?warehouse_id=&sku=` | on_hand, reserved, quarantined — no `buffer` field |
| `/purchase_orders?supplier_id=&sku=&status=` | status: open, confirmed, received, cancelled; eta field |
| `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | Returns zone_distance, service_days, **total_cost** (field name, not total_cost_usd) |
| `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | Date filter on open_date; severity, resolution_cost, incident_type |
| `/suppliers` | quality_status: approved, watch, quality_hold |
| `/boms` , `/boms/<bom_id>` | Components with quantity_per_kit, warehouse_id |

## Effective Availability

Always compute effective available as:

```
effective = on_hand − reserved − quarantined
```

When a memo mentions "normal operating buffer," **also subtract `safety_stock`**:

```
effective_buffered = max(0, on_hand − reserved − quarantined − safety_stock)
```

Always clamp negative effective to 0 before using in gap calculations:

```
gap = max(0, required_quantity − max(0, effective))
```

Decimal precision:
- Currency: **2 decimal places** (`round(val, 2)`)
- Percentages: **1 decimal place** (`round(val, 1)`)
- Duration (days): **2 decimal places**

## Enforced Enum Conventions

Every task uses controlled enumerations. Never deviate from the allowed values in the answer template. Common patterns:

**Customer exception** (precedence order):
1. `account_status == "blocked"` → `"account_blocked"` (takes priority over risk_flag)
2. `risk_flag == "fraud_watch"` → `"fraud_watch"`
3. `risk_flag == "credit_watch"` → `"credit_watch"`
4. `account_status == "review_required"` → `"review_required"`
5. Otherwise → `"none"`

Blocked status always wins over risk flags when both are present.

**Inventory status** (order of evaluation):
1. If any line SKU is **inactive** AND any active SKU has shortage → `"inactive_and_shortage"`
2. If any line SKU is inactive (no shortage) → `"inactive_sku"`
3. If any active SKU has `effective < quantity` → `"shortage"`
4. If any active SKU has `effective >= quantity` but `effective < quantity + safety_stock` → `"low_stock"`
5. Otherwise → `"ready"`

**Line action** (allocation/transfer tasks):
- `"ship"` — requested warehouse can release full line quantity
- `"transfer"` — other warehouse can cover the shortage
- `"backorder"` — cannot be cleared from current effective stock
- `"manual_review"` — account, risk, or product status prevents automatic release

**Replenishment final_action** (BOM/kit build tasks):
- `"no_action_stocked"` — sufficiently stocked
- `"transfer_only"` — covered by inter-warehouse transfers
- `"purchase_required"` — new purchase requisition needed
- `"timely_po_covered"` — existing open/confirmed PO covers the gap
- `"overstock_excluded"` — site effective exceeds overstock_threshold

**Exclusion reasons**: `"none"`, `"target_overstock"`, `"timely_po_covers_gap"`, `"stocked_no_gap"`

**Recommendation codes** (supplier scorecards, in precedence order):
1. `"ESCALATE_SUPPLIER"` — quality_hold + 3+ incidents, OR any critical RMA, OR 3+ RMAs + ≥15000 cost
2. `"PROCESS_REVIEW"` — WORK_ORDER incidents ≥ 3 AND WORK_ORDER > RMA count
3. `"WATCHLIST"` — quality_status in (watch, quality_hold), OR count ≥ 4, OR cost ≥ 12000, OR severe ≥ 2
4. `"MONITOR"` — none of the above

**Procurement control decisions**:
- `"freeze_new_replenishment"` — quality_hold status
- `"buyer_review_required"` — watch status with open incidents or critical incidents
- `"monitor_only"` — no quality concerns

## Field Pitfalls

- **Shipping quote**: API returns `total_cost`, not `total_cost_usd`. Map it to the answer field `total_cost_usd`.
- **Inventory fields**: `on_hand`, `reserved`, `quarantined` — no `qty_` prefix, no `buffer` field.
- **Safety stock**: Use `safety_stock` from the products endpoint as the threshold for low-stock detection. Do not confuse it with `overstock_threshold`.
- **effective >= 0**: Always clamp. Negative effective means 0 available.
- **PO timeliness**: A PO is "timely" only when `warehouse_id` matches the planning site, `status` is `"open"` or `"confirmed"`, and `eta` is on or before the earliest build date that needs the SKU. PO total quantity (not capped at gap) is the `timely_po_qty`.
- **Overstock classification**: `site_effective > overstock_threshold` triggers `overstock_excluded` / `target_overstock`. Check this BEFORE gap-based classification.
- **Received POs**: Already counted in inventory. Do not double-count as timely PO coverage.
- **Cancelled POs**: Ignore entirely.

## Ordering Rules

- **Records/lines**: Sort by `order_id` ascending, then `line_id` ascending.
- **SKU lists**: Sort ascending by SKU string.
- **Transfer requests**: Sort by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.
- **Supplier scorecard rows**: Sort by `supplier_id` ascending.
- **Top escalation**: Sort by `incident_count` descending, then `total_resolution_cost` descending, then `supplier_id` ascending.
- **Blocked/manual-review/backorder order ID lists**: Sort ascending.

## Calculations

**Incident duration**:
- Closed: `(close_date − open_date).days`
- Open: `(analysis_date − open_date).days`

**Incident percentage**: `round(incident_count / total_filtered_incidents × 100, 1)`

**Transfer source selection**: Sort candidate warehouses by effective stock descending; pull from the largest source first. Never transfer more than the source's effective stock.

**Kit build component requirement**:
```
total_required = sum over all kits(build_quantity × quantity_per_kit)
```
Combine quantities across all BOMs that share a component.

**Shipping weight**: Sum over all order lines: `quantity × weight_lb`. If zero, default to 1.0.

## SOP: Expedite Queue Decision

1. Fetch orders for wave, products, customers, inventory, shipping quotes.
2. For each order in the memo (sorted by order_id):
   a. Classify inventory status across all lines.
   b. Classify customer exception using precedence rules above.
   c. Determine final_decision: customer issues (account_blocked → reject_hold; fraud_watch/credit_watch → manual_review; review_required → manual_review) take priority over inventory issues (inactive → manual_review; shortage → backorder; low_stock → delayed_release; ready → ship_now).
   d. Map next_action to the most specific trigger.
   e. Compute shipping quote from the order's warehouse, destination_zip, total weight, and speed.
3. Build summary with counts, blocked/manual/backorder/inactive order lists.

## SOP: Kit Build Replenishment

1. Fetch BOMs, products, all-warehouse inventory, purchase orders.
2. Compute per-SKU total required across all target builds.
3. For each component (sorted by SKU):
   a. Compute site effective and gap.
   b. Identify timely POs (same site, open/confirmed, eta ≤ earliest build date). Timely_po_qty = full PO quantity.
   c. Subtract timely_po_qty from gap. If gap remains, seek transfers from other warehouses (sort sources by effective descending). Transfer only up to source effective.
   d. Any remaining gap becomes purchase_requisition_qty.
   e. Classify final_action: overstock first, then timely PO coverage, then transfer/purchase/no-action.
4. Populate transfer_requests, purchase_requisitions, excluded_components.
5. Summary: component_count, total_purchase_units, total_purchase_cost, total_transfer_units, timely_po_covered_units (gap units covered by timely POs, not full PO quantity).

## SOP: Allocation Desk (Mixed-Warehouse)

1. Fetch orders for wave, products, customers, all-warehouse inventory.
2. Determine if effective should include safety_stock buffer (check memo for "normal operating buffer").
3. For each line (sorted by order_id, line_id):
   a. Check customer status → blocked_orders, primary_reason.
   b. Check product active → manual_review for inactive.
   c. If customer blocked/fraud/credit/review → manual_review with appropriate primary_reason.
   d. Else check inventory: ship if eff ≥ qty; transfer if another WH can cover gap; backorder otherwise.
   e. For transfer, pick the best single source warehouse (most available).
4. Order rollup: classify each order based on its line actions (single action → map; mixed → "mixed_actions").
5. blocked_orders: orders where customer has account_blocked, fraud_watch, or credit_watch risk.

## SOP: Supplier Incident Scorecard

1. Fetch incidents within the date window (inclusive). Fetch all suppliers.
2. Group incidents by supplier_id. Only include suppliers with at least one filtered incident.
3. Per supplier: compute counts, costs, durations, percentages.
4. Apply recommendation policy in strict precedence order — first matching condition wins.
5. Build top_escalation_suppliers list (only ESCALATE_SUPPLIER, ordered as specified).
6. Identify highest_cost_supplier_id and highest_share_supplier_id.

## SOP: Procurement Quality Control

1. Fetch incidents for target suppliers within the analysis window.
2. Fetch supplier quality_status and all open/confirmed POs.
3. Per supplier: count recent incidents, RMAs, severe/critical, open incidents, affected SKUs.
4. Sample up to 5 incident IDs (sorted ascending).
5. Decision: quality_hold → freeze_new_replenishment; watch with open/critical incidents → buyer_review_required; otherwise → monitor_only.
6. held_po_ids: all open/confirmed PO IDs for non-monitor_only suppliers.
7. release_supplier_ids: monitor_only suppliers (sorted).
