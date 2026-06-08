---
name: reflection-skill-attempt-03
description: Use for PanofyBench Northwind Components ERP tasks that require producing strict JSON answers from visible task payloads plus the shared ERP API, including expedite queues, mixed-warehouse allocation, BOM replenishment, supplier incident scorecards, and procurement quality-hold reviews.
---

# Northwind ERP Reflection Skill

## Operating Boundaries

- Read the task prompt, answer template, and visible input payloads first. Do not infer output shape; mirror the template exactly.
- Use the shared API base URL supplied by the runner/user. If multiple URLs appear, obey the current user or runner constraint.
- Use public API endpoints only. Useful endpoints include `/`, `/health`, `/orders`, `/orders/<id>`, `/products`, `/products/<sku>`, `/customers`, `/customers/<id>`, `/inventory?warehouse_id=&sku=`, `/purchase_orders?supplier_id=&sku=&status=`, `/suppliers`, `/incidents?start=&end=&supplier_id=`, `/boms`, and `/shipping/quote`.
- Do not inspect environment source files, evaluator code, hidden tests, notes, or answer files unless the user explicitly permits a train-standard reflection phase.
- Return valid JSON only when solving a task. No prose outside the JSON.

## Standard Workflow

1. Extract IDs, waves, dates, target suppliers, BOMs, warehouses, and required enum values from the prompt/template/payloads.
2. Fetch live API records for every referenced object. Build maps for products, customers, inventory by `(warehouse_id, sku)`, suppliers, purchase orders, BOMs, and orders.
3. Compute all line/component/supplier rows from API records, not from memo wording or stale assumptions.
4. Populate every required field, including empty arrays and zero counts.
5. Sort exactly as the template says. If the template is silent, sort IDs/SKUs ascending for deterministic output.
6. Round currency to two decimals and incident percentages to the requested precision.
7. Validate final JSON against the template keys and allowed enum values.

## Inventory Math

- `raw_available = on_hand - reserved - quarantined`.
- `effective_available = on_hand - reserved - quarantined - product.safety_stock`.
- Do not clamp reported effective availability; negative values are meaningful and should be returned where requested.
- For source warehouses in transfer planning, only positive effective availability can be moved.
- A line is a shortage when `effective_available < requested_quantity`.
- A line is low stock when it is not a shortage but `effective_available - requested_quantity < product.safety_stock`.
- Product inactivity is independent of stock. Populate inactive SKU lists even when the final decision is driven by customer/account status.

## Customer And Product Precedence

- Customer exception mapping: blocked account -> `account_blocked`; review account -> `review_required` or `account_review_required` depending on the template enum; fraud risk -> `fraud_watch`; credit risk -> `credit_watch` where available, otherwise map to an account-review style reason if the enum lacks credit.
- Customer/account risk takes precedence over product and inventory for final release decisions.
- Inactive product status prevents automatic release and usually becomes `manual_review` with an inactive-product/product-master reason unless an account exception already controls the row.

## Expedite Queue Rules

- Quote shipping for every memo order, even held or backordered orders.
- Shipping quote weight is `sum(line.quantity * product.weight_lb)`; call `/shipping/quote` with the order warehouse, destination ZIP, order shipping speed, and computed weight. Use `total_cost` as `total_cost_usd`.
- Build `shortage_skus`, `inactive_skus`, and `low_stock_skus` independently, each sorted ascending.
- Inventory status precedence: `inactive_and_shortage`, `inactive_sku`, `shortage`, `low_stock`, then `ready`.
- Final decision precedence:
  - blocked/fraud/credit account risk -> `reject_hold` and `hold_credit_or_fraud`
  - account review -> `manual_review` and `send_account_review`
  - inactive SKU without higher account exception -> `manual_review` and product-master escalation
  - shortage -> `backorder` and `create_backorder`
  - low stock only -> `delayed_release` and `delay_and_monitor`
  - otherwise -> `ship_now` and `release_to_pick`

## Mixed-Warehouse Allocation

- Compute `requested_effective_available` with the un-clamped effective formula.
- Line action precedence:
  - account/risk exception -> `manual_review`, zero ship/transfer/backorder quantities, primary reason from the account/risk enum
  - inactive product -> `manual_review`, zero quantities, `inactive_product`
  - requested warehouse can cover full quantity -> `ship`
  - another single warehouse can cover the uncovered quantity from positive effective stock -> `transfer`
  - otherwise -> `backorder`
- For transfer/backorder candidates, `ship_quantity = max(0, min(requested_effective_available, requested_quantity))`; uncovered quantity is `requested_quantity - ship_quantity`.
- Choose one transfer source with enough positive effective stock for the uncovered quantity; prefer the highest effective availability, then warehouse ID ascending for ties.
- Use `primary_reason: "none"` for both `ship` and `transfer`; use `insufficient_effective_stock` for backorder.
- `blocked_orders` includes only customer/account/risk blocked orders, not product-only manual reviews.
- Order rollup: all ship -> `ready_to_ship`; all manual -> `manual_review`; any backorder without manual -> `has_backorder`; ship/transfer only -> `needs_transfer`; mixed manual with transfer/backorder or other mixed states -> `mixed_actions`.

## BOM Replenishment

- Explode each target BOM as `quantity_per_kit * target_build_quantity`; aggregate by SKU.
- `target_effective_available` is un-clamped effective availability at the planning warehouse.
- Gap is `total_required - target_effective_available`; because effective can be negative, the gap can exceed total required.
- Timely purchase orders are same-warehouse, status `open` or `confirmed`, and ETA on or before the relevant build date for the demand they cover. Track coverage PO IDs sorted ascending.
- Apply available stock, timely POs, and transfers chronologically to component demand buckets. Transfer `needed_by` should match the earliest unmet build date the transfer supports; purchase requisition `needed_by` should match the remaining unmet demand date, often the later build date for components shared across targets.
- Allocate transfers from other warehouses in descending positive effective availability, then warehouse ID ascending. Multiple source warehouses can be used for BOM replenishment.
- If target effective availability is at or above `overstock_threshold`, use `overstock_excluded` / `target_overstock`.
- If no gap remains from stock, use `no_action_stocked` / `stocked_no_gap`.
- If timely POs cover the full gap, use `timely_po_covered` / `timely_po_covers_gap`.
- If any purchase remains after stock, timely POs, and transfers, use `purchase_required`; otherwise transfer-only gaps use `transfer_only`.
- Purchase requisitions use the product supplier and unit cost. `extended_cost = quantity * unit_cost`, rounded to two decimals.
- Summary `timely_po_covered_units` should sum the covered gap units, not just total required units.

## Supplier Incident Scorecards

- Filter incidents by `open_date` inclusively within the requested window.
- Duration is calendar days from `open_date` to `close_date`; for open incidents, use the analysis date. Do not add one day.
- Severe incidents use the severity values from the request, commonly `high` and `critical`.
- Incident percentage denominator is the full filtered incident population.
- Recommendation precedence is strict:
  - `ESCALATE_SUPPLIER`: quality hold with enough incidents, any critical RMA, or the request's RMA/cost escalation condition
  - `PROCESS_REVIEW`: work orders meet the threshold and exceed RMA count
  - `WATCHLIST`: quality watch/hold, incident count, cost, or severe-count watch conditions
  - `MONITOR`: none of the above
- Top escalation suppliers follow the requested sort, usually incident count descending, cost descending, supplier ID ascending.

## Procurement Quality-Hold Reviews

- Filter recent incidents by `open_date` inclusively and target supplier IDs.
- Count recent incidents, RMA incidents, high/critical incidents, and open incidents. Sort affected SKUs and sample incident IDs; cap sample incident IDs at five.
- Decision precedence observed for this domain:
  - supplier `quality_hold` -> `freeze_new_replenishment`
  - watch supplier with at least two high/critical recent incidents -> `buyer_review_required`
  - otherwise -> `monitor_only`
- Do not escalate solely because a supplier is on watch, has open incidents, or has several recent incidents.
- Hold PO IDs only for freeze or buyer-review suppliers. Use open/confirmed PO IDs sorted ascending; if the task gives no explicit cap, cap each supplier's held list to the first five IDs to match the domain convention.
- `release_supplier_ids` are the monitor-only suppliers. Top-level `held_po_ids` is the sorted unique union of supplier held lists.

## Common Pitfalls

- Do not clamp effective availability to zero in fields that ask for effective availability.
- Do not use raw availability for shortage decisions; safety stock is protected.
- Low-stock SKUs can appear alongside shortage or manual-review outcomes because SKU exception lists are independent.
- Transfer rows may have `primary_reason: "none"` even though the transfer was caused by insufficient requested-warehouse stock.
- Account-level manual review blocks all lines on that order; product-only manual review affects only that product line.
- For BOM tasks, source transfers are chosen by available capacity, not by warehouse ID alone.
- For quality-hold tasks, held purchase orders are not the same as all supplier purchase orders; filter by status and apply the task/domain cap.
