---
name: northwind-erp
description: "Interact with the Northwind Components shared ERP REST API to solve operations desk tasks including dispatch/expedite decisions, replenishment/kit-build planning, supplier incident scorecards, cross-warehouse allocation, and procurement quality-risk controls. Use when working with Northwind operations, ERP queries, order fulfillment, inventory analysis, BOM/kit replenishment, supplier quality review, purchase-order decisions, or shipping quotes. Triggers on Northwind Components, expedite queue, kit build, replenishment, supplier scorecard, allocation desk, procurement control, or any task referencing a shared ERP API at a task environment base URL."
license: MIT
compatibility: designed for deepagents-code
---

# Northwind ERP Operations

## Quick start

The shared Northwind ERP API runs at a base URL provided by the task runner as
`<TASK_ENV_BASE_URL>`. All endpoints return JSON arrays or objects. No
authentication is required.

```bash
# Verify connectivity
curl -s "<TASK_ENV_BASE_URL>/warehouses"
```

Full endpoint catalog and field shapes are in [references/api.md](references/api.md).
Domain-specific decision rules and workflows for each operations desk are in
[references/domains.md](references/domains.md).

## Core formula: effective available inventory

Always compute effective available for any stock decision:

```
effective_available = on_hand - reserved - quarantined
```

This single formula drives every inventory-status check in the system. Values
come from the `/inventory` list. When comparing against a required quantity,
use the effective available at the relevant warehouse, not total on_hand.

Every inventory decision also checks two product-master thresholds:

- **safety_stock**: the floor you must not dip below when allocating
- **overstock_threshold**: the ceiling above which a SKU is over-stocked

Both are on the `/products` record for each SKU.

## Entity relationships

When solving a task, trace the relationship chain needed for the decision:

- **Order** → lines have SKU, quantity, warehouse_id; order has customer_id, shipping_speed, destination_zip
- **Customer** → account_status (active | blocked | review_required), risk_flag (none | fraud_watch | credit_watch), tier
- **Product** → active flag, safety_stock, overstock_threshold, supplier_id, unit_cost, weight_lb
- **Inventory** → on_hand, reserved, quarantined (per SKU × warehouse)
- **Warehouse** → warehouse_id, zip, region
- **Supplier** → quality_status (approved | watch | quality_hold), region
- **Purchase Order** → sku, warehouse_id, supplier_id, quantity, status, eta
- **BOM** → components with quantity_per_kit per SKU
- **Incident** → supplier_id, sku, severity, status, incident_type, resolution_cost, open_date, close_date
- **Shipping Quote** → total_cost, zone_distance, service_days (from warehouse × destination_zip × weight × speed)

## Decision trees by desk

### Expedite / dispatch

```
For each order in the wave:
  1. Fetch order lines and customer.
  2. For each line, compute effective_available at the order warehouse.
  3. inventory_status:
     - All lines covered AND active → "ready"
     - All covered but one dips into safety_stock → "low_stock"
     - Any line short AND all active → "shortage"
     - Any line with inactive product → "inactive_sku" or "inactive_and_shortage"
  4. customer_exception:
     - account_status=blocked → "account_blocked"
     - risk_flag=fraud_watch → "fraud_watch"
     - risk_flag=credit_watch → "credit_watch"
     - account_status=review_required → "review_required"
     - otherwise → "none"
  5. final_decision (precedence order):
     - account_blocked or fraud_watch → "reject_hold"
     - review_required or credit_watch → "manual_review"
     - inactive_sku → "manual_review"
     - shortage → "backorder"
     - low_stock → "delayed_release"
     - ready → "ship_now"
```

### Replenishment / kit build

```
For each kit target:
  1. Load BOM components and quantities_per_kit.
  2. total_required = quantity_per_kit × build_quantity.
  3. Aggregate by SKU across kits.
  4. For each SKU at the target warehouse:
     effective_available = on_hand - reserved - quarantined
     target_effective_available = effective_available - total_required
  5. Check timely POs: open or confirmed, same warehouse, eta ≤ build_date + 1 day.
  6. If timely_po_qty covers the gap → "timely_po_covered", exclude.
  7. If target_effective_available > overstock_threshold → "overstock_excluded".
  8. For remaining gap, check other warehouses (avoid dipping below their safety_stock).
  9. Purchase requisition for any remaining gap.
```

### Supplier incident scorecard

```
  1. Filter incidents by open_date in the analysis window.
  2. Group by supplier_id, join supplier name and quality_status.
  3. Per supplier: counts, percentages (of filtered population), resolution costs,
     average duration, RMA vs WORK_ORDER split, open/closed counts, severe counts.
  4. Apply recommendation policy by precedence:
     ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST > MONITOR.
```

### Allocation / transfer

```
For each line in the wave:
  1. Check customer account_status and risk_flag → manual_review if blocked.
  2. Check product active flag → manual_review if inactive.
  3. Compute effective_available at requested warehouse.
  4. If covers full qty → "ship".
  5. If partial: check other warehouses for transfer (use their effective_available - safety_stock).
  6. If no transfer possible → "backorder".
```

### Procurement quality risk

```
  1. Filter incidents by the analysis window for the target suppliers.
  2. Count recent incidents, RMAs, severe/critical, open incidents per supplier.
  3. Collect affected SKUs from incidents and POs.
  4. Decision (precedence):
     - quality_hold with severe history → "freeze_new_replenishment"
     - watch with moderate severity → "buyer_review_required"
     - otherwise → "monitor_only"
```

## General rules

- Always sort output lists in ascending order by their primary key (order_id,
  sku, supplier_id, etc.) unless the task template says otherwise.
- Round all currency values to exactly two decimal places.
- Use `null` for absent transfer_from values; never use the string `"null"`.
- Shipping quotes require: warehouse_id, destination_zip, weight_lb, and speed.
  Compute line weight from `/products` weight_lb × line quantity. Use the
  order-level shipping_speed and destination_zip for the quote.
- When a PO status is "open" or "confirmed" and its eta is before or on the
  needed date (considering a +1 day buffer if the task allows), it is timely.
- Never duplicate covered quantities between transfer and purchase paths.
