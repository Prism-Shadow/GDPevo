# Northwind Desk Decision Logic

## Customer Exception Classification

Map the customer's `account_status` and `risk_flag` to the appropriate exception:

| account_status | risk_flag | Exception |
|----------------|-----------|-----------|
| active | none | `none` |
| active | fraud_watch | `fraud_watch` |
| blocked | any | `account_blocked` |
| review_required | any | `review_required` |
| any | credit_watch (and not blocked) | `credit_watch` |

When `account_status` is `blocked`, the exception is always `account_blocked` regardless of `risk_flag`. When `account_status` is `review_required`, the exception is `review_required`. When `account_status` is `active` but `risk_flag` is `fraud_watch`, use `fraud_watch`. When the only flag is `credit_watch` on an active account, use `credit_watch`.

## Inventory Status Classification (Per-Order)

For each order, evaluate every line's inventory at the requested warehouse:

1. Fetch the product record — if `active` is `false`, that SKU is **inactive**.
2. Compute `effective_available = on_hand - quarantined - reserved` for that SKU at that warehouse.
3. Compare `line.quantity` against `effective_available`:
   - If `effective_available >= line.quantity`: the line is covered.
   - If `effective_available > 0` but `< line.quantity`: the line is **low stock**.
   - If `effective_available <= 0`: the line is in **shortage**.

Combine results across all lines to determine the order-level inventory status:

| Condition | Status |
|-----------|--------|
| All lines covered | `ready` |
| At least one low-stock line, no shortages, no inactive | `low_stock` |
| At least one shortage, no inactive SKUs | `shortage` |
| At least one inactive SKU, no shortages | `inactive_sku` |
| Both inactive SKUs and shortages present | `inactive_and_shortage` |

## Final Decision and Next Action (Expedite Queue)

Combine inventory status and customer exception:

| Inventory Status | Customer Exception | Decision | Next Action |
|-----------------|-------------------|----------|-------------|
| ready | none | `ship_now` | `release_to_pick` |
| ready | review_required | `manual_review` | `send_account_review` |
| ready | credit_watch | `manual_review` | `hold_credit_or_fraud` |
| low_stock | none | `delayed_release` | `delay_and_monitor` |
| low_stock | review_required | `manual_review` | `send_account_review` |
| low_stock | credit_watch | `manual_review` | `hold_credit_or_fraud` |
| shortage | none | `backorder` | `create_backorder` |
| shortage | review_required | `manual_review` | `send_account_review` |
| shortage | credit_watch | `manual_review` | `hold_credit_or_fraud` |
| inactive_sku | none | `manual_review` | `escalate_product_master` |
| inactive_sku | review_required | `manual_review` | `send_account_review` |
| inactive_and_shortage | none | `manual_review` | `escalate_product_master` |
| inactive_and_shortage | review_required | `manual_review` | `send_account_review` |
| * | account_blocked | `reject_hold` | `hold_credit_or_fraud` |
| * | fraud_watch | `reject_hold` | `hold_credit_or_fraud` |

The `account_blocked` and `fraud_watch` exceptions override inventory status entirely — the decision is always `reject_hold`.

## Line-Level Allocation (Transfer Desk)

For each order line in a wave:

1. Check customer — if `account_status` is `blocked`, all lines → `manual_review` with reason `account_blocked`. If `account_status` is `review_required`, all lines → `manual_review` with reason `account_review_required`. If `risk_flag` is `fraud_watch`, all lines → `manual_review` with reason `fraud_watch`. If `risk_flag` is `credit_watch` on blocked account, use `account_blocked`.

2. Check product — if product `active` is `false`, line → `manual_review` with reason `inactive_product`.

3. Compute `effective_available` for the line's SKU at the requested warehouse.

4. Decide action:
   - If `effective_available >= line.quantity`: `ship` with `ship_quantity = line.quantity`.
   - If `effective_available < line.quantity` (but customer/product OK): check other warehouses.
     - For each other warehouse, compute effective_available for the same SKU.
     - If some other warehouse can cover the gap (`effective_available >= line.quantity - requested_warehouse_effective`):
       - Action: `transfer`. `ship_quantity = max(0, requested_warehouse_effective)`.
       - `transfer_quantity = line.quantity - ship_quantity`.
       - Choose one source warehouse — prefer the one with the most effective available units.
     - If no warehouse can cover the gap: `backorder` with reason `insufficient_effective_stock`.

When a customer-level block or review is present, ALL lines for that order get `manual_review` regardless of inventory. Even lines that would otherwise ship.

## Supplier Recommendation Cascade (Scorecard)

Apply rules in this **precedence order**. The first matching rule determines the recommendation:

1. **ESCALATE_SUPPLIER**: Supplier `quality_status` is `quality_hold` AND has at least 3 filtered incidents, OR has any critical-severity RMA, OR has at least 3 RMAs AND at least 15000.00 total filtered resolution cost.

2. **PROCESS_REVIEW**: WORK_ORDER incidents are at least 3 AND exceed RMA incidents.

3. **WATCHLIST**: Supplier `quality_status` is `watch` or `quality_hold`, OR filtered `incident_count` is at least 4, OR total filtered resolution cost is at least 12000.00, OR `severe_incident_count` (high or critical severity) is at least 2.

4. **MONITOR**: None of the above conditions apply.

## Procurement Quality Decision Cascade

For each target supplier, examine recent incidents (within the analysis window):

| Condition | Decision |
|-----------|----------|
| `quality_status` is `quality_hold` | `freeze_new_replenishment` |
| `quality_status` is `watch` AND recent incidents exist | `buyer_review_required` |
| `quality_status` is `watch` but no recent incidents | `monitor_only` |
| `quality_status` is `approved` AND recent incidents exist | `buyer_review_required` |
| `quality_status` is `approved` AND no recent incidents | `monitor_only` |

**Held POs**: For any supplier with decision `freeze_new_replenishment` or `buyer_review_required`, collect all of that supplier's purchase orders with status `open` or `confirmed` (regardless of date) into `held_po_ids`.

## Replenishment Component Logic

For each component in a BOM target build:

1. `total_required = quantity_per_kit * build_quantity` across all kits using that SKU.

2. Get effective available at the planning warehouse for that SKU. Also check the product's `safety_stock` and `overstock_threshold`.

3. `target_effective_available` = effective available. If this is already above `overstock_threshold` AND exceeds total_required, the component is `overstock_excluded` with reason `target_overstock`.

4. Check timely POs: for this SKU at the planning warehouse, sum quantities of POs with status `open` or `confirmed` and `eta` on or before the build date. If `target_effective_available + timely_po_qty >= total_required`, action is `timely_po_covered` with reason `timely_po_covers_gap`.

5. If a gap remains:
   - Check other warehouses for transferable stock (effective available above zero, accounting for their own safety stock conservatively).
   - Remaining gap after transfers → `purchase_requisition`.

6. `final_action` values: `no_action_stocked` (when effective >= required), `transfer_only` (gap covered by transfers alone), `purchase_required` (gap needs purchase after transfers), `timely_po_covered` (POs cover gap), `overstock_excluded` (target already overstocked).

7. When action is `timely_po_covered` or `overstock_excluded`, the component also appears in `excluded_components`. When action is `no_action_stocked`, it goes in excluded_components with reason `stocked_no_gap`.

## Sorting Rules

- Order IDs: sort ascending as strings (lexicographic, e.g. "SO-70000" < "SO-70001").
- SKUs: sort ascending as strings (e.g. "NW-1000" < "NW-1001").
- Line IDs within an order: sort ascending as integers.
- Transfer requests: sort by sku ascending, then quantity descending, then from_warehouse_id ascending.
- Incident IDs and PO IDs: sort ascending as strings.
- Lists of IDs in summaries: sort ascending, unique.
