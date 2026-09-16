# Reusable Decision Frameworks

These frameworks capture the reasoning patterns that repeat across Northwind ERP operational desk tasks. Each task's memo and answer template define the exact enums and thresholds. The frameworks below describe the *method* for applying them, not hardcoded policies.

## Inventory Classification

Every task that classifies inventory per SKU per order follows the same pattern:

1. For each SKU on an order, look up the product record.
2. If `active` is `false`, the SKU is **inactive** -- this overrides availability checks. Classify accordingly (e.g. `inactive_sku` or a compound like `inactive_and_shortage` if combined with shortage).
3. Look up the inventory record for `sku` + `warehouse_id`.
4. Compute effective availability: `on_hand - reserved - quarantined`.
5. Compare effective availability against the order line quantity:
   - Effective >= 0 and effective >= quantity: **ready** or **low_stock** depending on thresholds.
   - Effective < 0: **shortage** (the negative number means prior commitments already exceed physical stock).
   - Effective >= 0 but effective < quantity: check whether the template distinguishes **low_stock** from **shortage**. Low stock typically means stock exists but is insufficient; shortage means no stock at all or negative effective.

### SKU exception lists

When the template requires `shortage_skus`, `inactive_skus`, and `low_stock_skus`:
- `shortage_skus`: SKUs where the order-line quantity exceeds effective availability at the requested warehouse, i.e. `effective < quantity_ordered`.
- `inactive_skus`: SKUs whose product record has `active: false`.
- `low_stock_skus`: SKUs where stock exists but is below a relevant threshold. This may include SKUs where effective inventory is positive but tight, or where effective is >= 0 but below the order quantity (depending on how the template distinguishes low_stock from shortage).

Sort each list ascending by SKU. A SKU can appear in multiple lists simultaneously (e.g. an inactive SKU that also has a shortage).

## Customer Exception Classification

When the template has a `customer_exception` field:

1. Look up the customer record by `customer_id` from the order.
2. Check `account_status` first -- it typically dominates:
   - `blocked` maps to the template's blocked/hold enum (e.g. `account_blocked`).
   - `review_required` maps to the template's review enum (e.g. `review_required`).
3. If account_status is `active`, check `risk_flag`:
   - `fraud_watch` maps to the template's fraud enum.
   - `credit_watch` maps to the template's credit enum.
   - `none` means no exception (`none`).
4. Use the exact enum strings from the answer template's `allowed_values`.

## Fulfillment Decision (Expedite Queue)

The `final_decision` and `next_action` pair derives from combining inventory status and customer exception.

The pattern is: customer-level blocks/review always win ("the customer is the gate"). When the customer is clean, inventory drives the decision. Blocked/fraud/credit accounts always get `reject_hold` regardless of inventory. When inventory is ready and the customer is clean, ship. When inventory is short and the customer is clean, backorder. Inactive SKUs always need manual review regardless of the customer. Compound statuses (inactive_and_shortage) default to manual review.

| Inventory Status | Customer Exception | Typical final_decision | Typical next_action |
|---|---|---|---|
| ready | none | ship_now | release_to_pick |
| ready | review_required | manual_review | send_account_review |
| ready | account_blocked | reject_hold | hold_credit_or_fraud |
| ready | fraud_watch | reject_hold | hold_credit_or_fraud |
| ready | credit_watch | reject_hold | hold_credit_or_fraud |
| low_stock | none | delayed_release | delay_and_monitor |
| low_stock | review_required | manual_review | send_account_review |
| low_stock | blocked/fraud/credit | reject_hold | hold_credit_or_fraud |
| shortage | none | backorder | create_backorder |
| shortage | review_required | manual_review | send_account_review |
| shortage | blocked/fraud/credit | reject_hold | hold_credit_or_fraud |
| inactive_sku | none | manual_review | escalate_product_master |
| inactive_sku | any exception | manual_review | escalate_product_master |
| inactive_and_shortage | none | manual_review | escalate_product_master |
| inactive_and_shortage | any exception | manual_review | send_account_review |

Verify the exact mapping against the template's enums -- different tasks may name these slightly differently.

## Supplier Recommendation (Incident Scorecard)

The recommendation has a strict precedence order. Evaluate from top to bottom, assign the first match:

1. **ESCALATE_SUPPLIER** (priority 1):
   - `quality_status` is `quality_hold` AND `incident_count` >= 3, OR
   - Any incident with type `RMA` and severity `critical`, OR
   - `rma_count` >= 3 AND total `resolution_cost` >= 15000.00

2. **PROCESS_REVIEW** (priority 2):
   - `work_order_count` >= 3 AND `work_order_count` > `rma_count`

3. **WATCHLIST** (priority 3):
   - `quality_status` is `watch` or `quality_hold`, OR
   - `incident_count` >= 4, OR
   - Total `resolution_cost` >= 12000.00, OR
   - `severe_incident_count` >= 2

4. **MONITOR** (priority 4):
   - Default when none of the above apply.

The thresholds above are the ones seen in training tasks. A new task may supply different thresholds in its memo -- always read the memo's recommendation_policy if provided.

### Severe incident count

Count incidents where `severity` is `high` or `critical`. These are the "severe" severity values.

### Percentage calculation

Each supplier's `incident_percentage` = (supplier incident count / total filtered incident count) * 100, rounded to 1 decimal place.

### Top escalation ordering

Suppliers with `ESCALATE_SUPPLIER` only. Sort by: `incident_count` descending, then `total_resolution_cost` descending, then `supplier_id` ascending.

## Replenishment Coverage (Production BOM)

For each component SKU used by the target BOMs:

1. Compute `total_required` = sum over all kits of `quantity_per_kit * build_quantity`.
2. Get target warehouse effective inventory: `on_hand - reserved - quarantined` for `sku` at `warehouse_id`.
3. Compute `target_effective_available` = effective inventory - total_required.
   - Negative means the gap needs filling.
   - Positive means there is surplus.

4. Check timely POs: filter purchase orders for `sku` at `warehouse_id` with status `open` or `confirmed` and `eta` <= target build date. Sum their quantities as `timely_po_qty`.

5. Determine final_action:
   - If `target_effective_available` >= 0: already stocked. The action is `no_action_stocked` or `overstock_excluded` if surplus is above a threshold.
   - If `timely_po_qty` covers the gap (i.e. `target_effective_available + timely_po_qty >= 0`): `timely_po_covered`. Exclude from further planning.
   - Otherwise, try transfers: look at peer warehouses (other warehouse_ids) for the same SKU. For each peer, compute its effective inventory. Transfer only positive effective inventory, up to the remaining gap. Transfer from the warehouse with the most available stock first (descending order of effective inventory).
   - If transfers fill the gap: `transfer_only`.
   - If transfers partially fill: compute `purchase_requisition_qty` = remaining gap after transfers. Action is `purchase_required`.

6. For the component_plan table:
   - `total_required`: as computed.
   - `target_effective_available`: effective inventory - total_required.
   - `timely_po_qty`: sum of qualifying PO quantities.
   - `transfer_qty`: total units to be transferred from peer warehouses.
   - `purchase_requisition_qty`: remaining units to purchase.
   - `final_action`: one of `no_action_stocked`, `overstock_excluded`, `timely_po_covered`, `transfer_only`, `purchase_required`.
   - `coverage_po_ids`: list of PO IDs that are timely and cover the gap. Sorted ascending.
   - `exclusion_reason`: `none` for active components; `target_overstock` if overstock; `timely_po_covers_gap` if PO-covered; `stocked_no_gap` if already stocked.

7. Transfer requests: for each SKU, create one transfer request per source warehouse. Sort by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.

8. Purchase requisitions: for each SKU needing purchase, look up the product's `supplier_id` and `unit_cost`. Create one requisition. Sort by `sku` ascending.

9. Excluded components: SKUs whose `final_action` is `timely_po_covered` or `overstock_excluded`. Include the reason and supporting PO IDs. Sort by `sku` ascending.

## Allocation Desk (Transfer Wave)

For each order line in a transfer wave:

1. Look up the order, customer, product, and inventory as usual.
2. Check the customer first: if `account_status` is `blocked` or `review_required`, or `risk_flag` is `fraud_watch` or `credit_watch`, the entire order is blocked. All lines on that order get `action: manual_review` with the appropriate `primary_reason`.
3. Check product: if `active` is `false`, the line gets `action: manual_review` with `primary_reason: inactive_product`.
4. Compute effective inventory at the requested warehouse: `on_hand - reserved - quarantined`.
5. Compare against line quantity:
   - If `effective >= quantity`: `action: ship`, `ship_quantity = quantity`.
   - If `effective >= 0` but `effective < quantity`: check other warehouses. Can another warehouse supply the gap without dipping into negative effective? If yes: `action: transfer`. Ship what the requested warehouse can (`ship_quantity = effective`). Transfer the remainder using the best single source warehouse (the one with the highest effective availability for that SKU). `transfer_quantity = gap`, `transfer_from = source_warehouse_id`.
   - If no warehouse can cover the gap (all effective values are negative or insufficient after accounting): `action: backorder`, `backorder_quantity = quantity`.

6. The `primary_reason` for ship and transfer lines is `none`. For backorder, it's `insufficient_effective_stock`.

### Choosing the transfer source

When multiple peer warehouses have positive effective inventory for a SKU, pick the one with the highest effective availability. Only transfer from warehouses that actually have positive effective stock after the transfer (do not create a new shortage at the source).

### Order rollup

After processing all lines, determine each order's `outcome`:
- All lines `ship`: `ready_to_ship`.
- Any line `transfer`, no line `backorder` or `manual_review`: `needs_transfer`.
- Any line `backorder`, no `manual_review`: `has_backorder`.
- Any line `manual_review`: `manual_review`.
- Mix of ship, transfer, backorder (no manual_review): `mixed_actions`.

## Procurement Quality Review

For each target supplier:

1. Fetch recent incidents: filter the full incident list to the analysis window by `open_date`. Only incidents whose `open_date` falls within [start_date, end_date] inclusive count.
2. For each supplier, compute:
   - `recent_incident_count`: number of filtered incidents for that supplier.
   - `recent_rma_count`: filtered incidents where `incident_type` is `RMA`.
   - `severe_or_critical_count`: filtered incidents where `severity` is `high` or `critical`.
   - `open_incident_count`: filtered incidents where `status` is `open`.
   - `affected_skus`: unique sorted list of SKUs from the filtered incidents.
   - `sample_incident_ids`: up to 5 incident IDs from the filtered set, sorted ascending.

3. Fetch the supplier's `quality_status` from the suppliers list.
4. Fetch purchase orders for the supplier: filter purchase orders by `supplier_id`, keeping only `open` or `confirmed` status.

5. Apply decision logic (task-specific policy; typical):
   - `freeze_new_replenishment`: when `quality_status` is `quality_hold` with any recent incidents, or when there are severe/critical RMA incidents. Hold all open/confirmed POs.
   - `buyer_review_required`: when `quality_status` is `watch` with recent incidents, or when there are elevated incident counts without reaching the freeze threshold. Hold all open/confirmed POs pending buyer sign-off.
   - `monitor_only`: when the supplier is clean (approved, few incidents, no severe history). No POs held.

6. Collect held PO IDs across all suppliers into `held_po_ids` (sorted, unique).
7. Collect supplier IDs with `monitor_only` decision into `release_supplier_ids` (sorted).

## Summary Aggregation Patterns

Most tasks require a summary block. Common patterns:

- **Count totals**: count how many orders/lines/components/suppliers were processed.
- **Decision/action counts**: count occurrences of each enum value in the records array.
- **Cost totals**: sum relevant cost fields across all records, rounded to 2 decimals.
- **Unit totals**: sum transfer quantities, backorder quantities, purchase quantities.
- **ID lists**: collect order_ids or supplier_ids matching a criterion, sorted ascending, as string lists.
- **Sub-totals**: sum PO-covered units, excluded component counts, etc.

Always derive summary values from the computed records -- do not recompute from raw data or double-count. The summary must be internally consistent with the records array.
