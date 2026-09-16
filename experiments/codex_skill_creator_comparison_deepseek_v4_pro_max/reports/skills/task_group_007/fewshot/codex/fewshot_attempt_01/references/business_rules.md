# Northwind ERP Business Rules

Reusable rules observed across the Northwind Components task family. These are
not task-specific answers; they encode the stable cross-task logic that the
solver must apply to each new input.

## 1. Effective Availability

For any inventory record at a warehouse:
```
effective_available = on_hand - reserved - quarantined
```
This is the only meaningful inventory figure. Never use `on_hand` alone for
allocation or replenishment decisions.

For inter-warehouse transfers, the amount that can leave a source warehouse
without falling below the product's `safety_stock` is:
```
usable_for_transfer = max(0, effective_available - safety_stock)
```

## 2. Customer Exception Classification

Map the customer record to a standard exception code:

| account_status | risk_flag | exception |
|---|---|---|
| blocked | any | account_blocked |
| review_required | any | review_required |
| active | fraud_watch | fraud_watch |
| active | credit_watch | credit_watch |
| active | none | none |

## 3. Order Inventory Status (Expedite)

For each order, check all lines against inventory at the order's warehouse:

1. A SKU is **in shortage** if `effective_available < line_quantity` and the product is active.
2. A SKU is **low stock** if `effective_available < safety_stock` but not in shortage.
3. A SKU is **inactive** if `product.active == false`.

Order-level inventory status:

| Has inactive | Has shortage | Status |
|---|---|---|
| yes | yes | inactive_and_shortage |
| yes | no | inactive_sku |
| no | yes | shortage |
| no | no (but low_stock) | low_stock |
| no | no | ready |

## 4. Expedite Decision Table

The (inventory_status, customer_exception) pair determines the final decision
and next action. The complete table is encoded in
`northwind_api.EXPEDITE_DECISION_TABLE` and `northwind_api.expedite_decision()`.

Key precedence: customer exceptions override inventory issues.
- `account_blocked` or `fraud_watch` → always `reject_hold` / `hold_credit_or_fraud`
- `review_required` → always `manual_review` / `send_account_review` (unless inactive)
- `credit_watch` → `manual_review` for non-inactive, `escalate_product_master` for inactive
- `none` → inventory-driven: ready→ship_now, low_stock→delayed_release, shortage→backorder, inactive→manual_review/escalate_product_master

## 5. Shipping Quote

Call `/shipping/quote` with the order's `warehouse_id` (as `warehouse_id`),
`destination_zip`, the order's `shipping_speed`, and total order weight (sum of
`line_quantity × product.weight_lb`). Use `total_cost` from the response,
rounded to 2 decimals.

## 6. Kit Replenishment (BOM-based)

For each BOM at the target warehouse:
1. `total_required[sku] = build_quantity × quantity_per_kit` (sum across BOMs)
2. `target_effective_available = eff_avail_at_target_warehouse - total_required`
3. If target_effective_available >= 0, the component is excluded (overstock or stocked, no gap).
4. Otherwise compute the gap = -target_effective_available.

**Cover the gap in this order:**
1. Check timely POs (status open/confirmed, eta <= build date, same warehouse) → `timely_po_quantity`
2. If timely POs cover the gap, final_action = `timely_po_covered`, excluded.
3. Check usable transfer stock from other warehouses (sorted by usable descending)
4. Remaining uncovered quantity → `purchase_requisition_qty`

**Final actions:**
- `no_action_stocked` — no gap, stock was sufficient (not excluded)
- `transfer_only` — transfers cover the full gap
- `purchase_required` — some quantity must be purchased
- `timely_po_covered` — POs cover the gap → excluded
- `overstock_excluded` — target warehouse has >=0 after build → excluded

**Exclusion reasons:**
- `target_overstock` — effective_available >= total_required at target warehouse
- `timely_po_covers_gap` — open/confirmed POs cover the gap
- `stocked_no_gap` — stock was sufficient and no transfers/purchases needed
- `none` — not excluded

**Transfers:** For each uncovered SKU, source from warehouses with positive
`usable_for_transfer`, preferring the warehouse with the most usable units.
Create one transfer record per source warehouse. Sort by sku ascending, then
quantity descending, then from_warehouse_id ascending.

**Purchase requisitions:** Use the product's `supplier_id` and `unit_cost`.
`needed_by` = latest build date requiring that SKU.
`unit_cost` and `extended_cost` (quantity × unit_cost) rounded to 2 decimals.

## 7. Allocation Line Actions

For each order line in a wave:

1. **Blocked at the order level:** If the customer's exception is in
   {account_blocked, review_required, fraud_watch, credit_watch}, all lines of
   that order → `manual_review`, primary_reason from the exception code.

2. **Inactive product:** If `product.active` is false → `manual_review` with
   reason `inactive_product`.

3. **Inventory check:** Compute `effective_available` at the line's requested
   warehouse. If `effective_available >= line_quantity` → `ship` with
   `ship_quantity = line_quantity`.

4. **Transfer check:** If the requested warehouse cannot fully supply, check
   other warehouses. `usable_for_transfer` at another warehouse may cover the
   shortage. If a single source warehouse can cover the remaining quantity →
   `transfer`. `ship_quantity` is whatever the requested warehouse can release;
   `transfer_quantity` is the uncovered portion.

5. **Backorder:** If no warehouse can cover → `backorder`.

**Primary reasons:**
- `account_blocked` — customer account_status is blocked
- `account_review_required` — customer review_required or credit_watch
- `fraud_watch` — customer risk_flag is fraud_watch
- `inactive_product` — product.active is false
- `insufficient_effective_stock` — no warehouse can cover the line
- `none` — line is shippable

**Transfer requests:** One per (order_id, line_id). Sort by order_id ascending,
then line_id ascending. Choose the source warehouse with the most usable stock.

**Order rollup:** per order, the worst outcome across lines:
- All lines ship → `ready_to_ship`
- At least one transfer, no backorder or manual_review → `needs_transfer`
- At least one backorder, no manual_review → `has_backorder`
- At least one manual_review → `manual_review`
- Mix of ship/transfer/backorder (no manual_review) → `mixed_actions`

## 8. Supplier Incident Scorecard

Filter incidents to the specified date window. For each supplier with at least
one filtered incident:

- `incident_percentage` = (supplier incidents / total filtered incidents) × 100,
  rounded to 1 decimal
- `avg_duration_days` = average of `incident_duration_days()` across the
  supplier's filtered incidents, rounded to 2 decimals
- `severe_incident_count` = count of incidents where severity in {high, critical}
- `open_incident_count` = count of incidents where status is "open"

**Recommendation codes** (evaluated in precedence order — first match wins):

1. `ESCALATE_SUPPLIER` — supplier quality_status is `quality_hold` AND
   filtered incident_count >= 3; OR any incident is critical RMA; OR RMA count
   >= 3 AND total filtered resolution_cost >= 15000.00
2. `PROCESS_REVIEW` — WORK_ORDER count >= 3 AND WORK_ORDER count > RMA count
3. `WATCHLIST` — supplier quality_status is `watch` or `quality_hold`; OR
   filtered incident_count >= 4; OR total resolution_cost >= 12000.00; OR
   severe_incident_count >= 2
4. `MONITOR` — none of the above

**Top escalation:** only suppliers with `ESCALATE_SUPPLIER`, sorted by
incident_count descending, then total_resolution_cost descending, then
supplier_id ascending.

`highest_cost_supplier_id` = supplier with max total_resolution_cost (smallest
supplier_id breaks ties). `highest_share_supplier_id` = supplier with max
incident_percentage (smallest supplier_id breaks ties).

## 9. Procurement Quality Decisions

For each target supplier (from task input), examine recent incidents within the
given analysis window:

- `recent_incident_count` — total incidents in window
- `recent_rma_count` — incidents of type RMA
- `severe_or_critical_count` — severity high or critical
- `open_incident_count` — status open
- `affected_skus` — unique sorted SKUs from incidents
- `sample_incident_ids` — up to 5 sorted incident IDs

**Decision logic:**
- `freeze_new_replenishment` — quality_status is `quality_hold` AND
  incident_count >= 3; OR any incident is critical RMA; OR RMA count >= 2 AND
  quality_status is not `approved`
- `buyer_review_required` — quality_status is `watch`; OR severe/critical >= 2
  but does not trigger freeze
- `monitor_only` — none of the above conditions

**Held PO IDs:** For freeze and buyer_review suppliers, collect all open or
confirmed POs for that supplier (from `GET /purchase_orders`) and include them
in `held_po_ids`. Sort all held POs uniquely.

**Release suppliers:** suppliers whose decision is `monitor_only`.

## 10. Currency and Precision

- All USD currency values: round to 2 decimal places
- All percentages: round to 1 decimal place
- All durations (days): round to 2 decimal places
- Lists of IDs (order_ids, sku, supplier_ids, etc.): sort ascending
