---
name: northwind-erp-operations
description: Solve Northwind Components ERP API operational JSON tasks, including dispatch expedite queues, mixed-warehouse allocation, kit replenishment, supplier incident scorecards, and procurement quality controls. Use when a task provides local payload templates or memos plus a Northwind ERP API base URL, and asks for strict JSON from orders, products, customers, inventory, warehouses, shipping quotes, BOMs, suppliers, purchase orders, or incidents.
---

# Northwind ERP Operations

## Workflow

1. Read the prompt and every local payload before calling the API. Treat the answer template as the output contract: required keys, enum values, ordering, rounding, and field names must match it exactly.
2. Use only the public ERP API base URL supplied by the task runner or prompt. Do not inspect environment source files.
3. Fetch the smallest live record set needed: orders, products, customers, inventory, warehouses, shipping quotes, BOMs, suppliers, purchase orders, and incidents as applicable.
4. Join records by IDs, compute derived fields, sort all lists as the template specifies, and return only the final JSON object.
5. Validate before answering: required keys present, enums legal, numeric precision correct, currency rounded to two decimals, percentages rounded as requested, and no narrative text outside JSON.

Use `scripts/northwind_snapshot.py` when a quick API snapshot is useful:

```bash
python3 scripts/northwind_snapshot.py --base-url "$TASK_ENV_BASE_URL" --wave WAVE_ID --quote-orders
```

The script fetches public endpoint data, enriches inventory with effective availability, filters selected orders or waves, and optionally requests shipping quotes for selected orders.

## Shared Calculations

- Effective available inventory for a SKU at a warehouse is `on_hand - reserved - quarantined - product.safety_stock`. This protects reserved, quarantined, and normal buffer stock.
- Transferable quantity from another warehouse is `max(effective_available, 0)`.
- Order shipment weight is the sum of `line.quantity * product.weight_lb` across lines.
- Request shipping quotes with `/shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&speed=...`, using the order warehouse, destination zip, computed weight, and order `shipping_speed`. Map `total_cost` to the template's cost field and round to two decimals.
- Customer exception precedence: blocked account first, then fraud or credit risk, then review-required account, then none. When a template lacks a separate credit-watch reason, map credit holds to the closest account-blocked or account-review enum it provides.
- Product `active: false` prevents automatic release for the affected line or order unless the task gives a different product-master policy.

## Dispatch Expedite Queues

For order queues that ask for fulfillment decisions:

1. Use the memo's order IDs; fetch each order, customer, product, target-warehouse inventory rows, and a shipping quote.
2. For each line, compare required quantity with effective available at the order warehouse.
3. Build SKU exception lists:
   - `inactive_skus`: inactive products.
   - `shortage_skus`: active or inactive lines where effective available is less than requested quantity.
   - `low_stock_skus`: active, non-shortage lines where `effective_available - requested_quantity` is less than the product safety stock.
4. Classify inventory status by precedence: inactive plus shortage, inactive only, shortage, low stock, then ready.
5. Decide by precedence:
   - blocked, fraud, or credit customer hold: reject or hold using the template's credit/fraud action.
   - review-required customer: manual review/account review.
   - inactive product without a stronger customer hold: manual product-master review.
   - shortage: backorder.
   - low stock without shortage: delayed release or monitor.
   - ready: release to pick or ship now.
6. Summaries count final decisions and list IDs for blocked, manual-review, backorder, and inactive-product groups in sorted order.

## Mixed-Warehouse Allocation

For wave allocation tasks:

1. Select all live orders in the requested wave unless the memo lists specific orders. Emit one row per order line sorted by order ID then line ID.
2. Apply order-level customer holds before product or inventory checks. Blocked, review-required, fraud, or credit-risk customers make every line `manual_review` with zero ship, transfer, and backorder quantities.
3. If the customer is clear but the product is inactive, make that line `manual_review` with an inactive-product reason.
4. Otherwise compute requested-warehouse effective availability:
   - if it covers the full line, action is `ship`.
   - if it does not cover the full line, set usable requested stock to `max(effective_available, 0)` and calculate the uncovered quantity.
   - choose a single source warehouse only when one other warehouse's transferable quantity covers the uncovered quantity. Prefer the source with the largest transferable quantity, then warehouse ID ascending. Emit a transfer row and leave usable requested stock as `ship_quantity`.
   - if no one source can clear the uncovered quantity, backorder the uncleared quantity.
5. `blocked_orders` includes only account or customer-risk stopped orders, not product-only manual reviews.
6. Roll up each order: all ship lines is `ready_to_ship`; any transfer without manual/backorder is `needs_transfer`; any backorder without manual is `has_backorder`; all manual is `manual_review`; mixed manual with non-manual actions is `mixed_actions`.

## Kit Replenishment

For BOM build or kit-run replenishment tasks:

1. Use memo build quantities and build dates, not stale BOM target dates. `kit_targets` are sorted by BOM ID.
2. Expand each BOM component quantity by requested build quantity and aggregate `total_required` by SKU. Sort component rows by SKU.
3. For the target warehouse, compute `target_effective_available` with the shared formula. A negative value increases the replenishment gap.
4. Allocate supply chronologically by component due date:
   - target effective stock first;
   - same-warehouse purchase orders with status `open` or `confirmed` and ETA no later than the relevant build need date;
   - transfers from other warehouses using positive transferable quantities without consuming safety stock, splitting across sources when needed;
   - purchase requisition for any remaining gap.
5. Use product `supplier_id` and `unit_cost` for purchase requisitions; extended cost is quantity times unit cost rounded to two decimals.
6. Actions and exclusions:
   - `overstock_excluded` when the target effective stock already covers demand and is at or above the product overstock threshold.
   - `no_action_stocked` with stocked/no-gap reason when target stock covers demand but is not overstock.
   - `timely_po_covered` when eligible same-warehouse POs cover the remaining gap.
   - `transfer_only` when transfers cover the remaining gap.
   - `purchase_required` when any purchase requisition quantity remains.
7. Summary purchase units/cost and transfer units are sums of emitted requisitions and transfers. Timely-PO-covered units are the portion of demand gap actually covered by timely POs, not necessarily the full PO quantity.

## Supplier Incident Scorecards

For supplier scorecard tasks:

1. Filter incidents by the request's date field and inclusive window. Join supplier names and quality statuses.
2. Include one scorecard row for each supplier with at least one filtered incident, sorted by supplier ID.
3. Count incident types exactly as stored, usually `RMA` and `WORK_ORDER`. Count severe incidents using the request's severe severity list.
4. Duration is calendar-day difference: closed incidents use `close_date - open_date`; open incidents use `analysis_date - open_date`. Do not add an inclusive extra day.
5. Percentages use supplier incident count divided by total filtered incidents. Round percentages, durations, and currency at the precision requested by the template.
6. Apply recommendation policies in the explicit precedence order from the request. For natural-language policies, evaluate each condition from highest to lowest precedence and stop at the first match.
7. Sort escalation lists by the requested keys. Highest-cost and highest-share supplier fields come from the computed supplier aggregates, with supplier ID as a deterministic tie-breaker if the prompt is silent.

## Procurement Quality Controls

For procurement-control or quality-hold reviews:

1. Review the supplier IDs named in the memo and filter incidents by open date within the memo analysis window, inclusive.
2. For each supplier, emit counts for recent incidents, RMAs, severe-or-critical incidents, and open incidents. `affected_skus` is the sorted unique SKU list from filtered incidents. `sample_incident_ids` is the first five sorted incident IDs unless the template says otherwise.
3. Use the examples' conservative decision pattern when no stronger local policy is provided:
   - `quality_hold` supplier status: `freeze_new_replenishment`;
   - otherwise two or more severe-or-critical recent incidents: `buyer_review_required`;
   - otherwise `monitor_only`.
4. For freeze or buyer-review suppliers, hold open or confirmed POs for that supplier. When the task template does not specify a count and many POs qualify, report the first five sorted PO IDs per supplier. Monitor-only suppliers have no held POs and belong in the release list.
5. Top-level held PO IDs are the sorted unique union of held supplier-level POs. Summary counts must reconcile to the emitted supplier decisions.
