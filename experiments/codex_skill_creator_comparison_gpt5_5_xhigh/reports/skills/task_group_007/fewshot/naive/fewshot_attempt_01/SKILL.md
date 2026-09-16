---
name: northwind-erp-operations
description: Solve Northwind Components ERP API tasks that ask for strict JSON decisions for fulfillment waves, warehouse transfers, BOM replenishment, supplier incident scorecards, or procurement quality holds.
---

# Northwind ERP Operations

Use this skill when a task asks for a Northwind Components operations JSON answer using the shared ERP API. Read the prompt, local memo/request payloads, and answer template first. Then use the API records as the source of truth; do not inspect environment source files or use any judge endpoint.

## API Workflow

Use the task runner's `<TASK_ENV_BASE_URL>` and public endpoints only:

- `/orders?wave=...`, `/orders/<order_id>`
- `/products`, `/products/<sku>`
- `/customers`, `/customers/<customer_id>`
- `/warehouses`
- `/inventory?warehouse_id=...&sku=...`
- `/shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&speed=...`
- `/purchase_orders?supplier_id=...&sku=...&status=...`
- `/incidents?start=...&end=...&supplier_id=...&sku=...&incident_type=...&status=...`
- `/suppliers`
- `/boms`, `/boms/<bom_id>`

Build the final object to match the provided template exactly. Return JSON only, sorted as the template states. Round currency to 2 decimals, incident percentages to 1 decimal, and average durations to 2 decimals.

## Shared Inventory Rules

For every stock decision, join inventory to product master data and compute:

```text
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

Treat reserved, quarantined, and safety stock as protected. Effective available may be negative. For a requested quantity, the uncovered quantity is:

```text
gap = requested_quantity - max(0, effective_available)
```

A line is a shortage when `effective_available < requested_quantity`. A fillable line is low stock when releasing it leaves little effective stock; the training pattern uses `effective_available - requested_quantity <= product.safety_stock`.

Inactive products prevent automatic release for that line. Customer/account exceptions take precedence over product and inventory outcomes.

## Expedite Dispatch Decisions

For each memo order ID, fetch the live order, customer, all products, inventory for the order warehouse, and a shipping quote.

Customer exception precedence:

- `account_status == blocked` -> `account_blocked`
- `risk_flag == fraud_watch` -> `fraud_watch`
- `risk_flag == credit_watch` -> `credit_watch` when allowed by the template
- `account_status == review_required` -> `review_required`
- otherwise `none`

Inventory status:

- any inactive SKU and any shortage -> `inactive_and_shortage`
- any inactive SKU -> `inactive_sku`
- any shortage -> `shortage`
- any low-stock fillable SKU -> `low_stock`
- otherwise `ready`

Sort SKU exception lists ascending. `shortage_skus` contains SKUs whose effective available is below the line quantity. `inactive_skus` contains inactive products. `low_stock_skus` contains active, fillable SKUs that meet the low-stock rule.

Final decision precedence:

- blocked, fraud, or credit customer risk -> `reject_hold` / `hold_credit_or_fraud`
- customer review required -> `manual_review` / `send_account_review`
- inactive SKU without a higher customer exception -> `manual_review` / `escalate_product_master`
- shortage -> `backorder` / `create_backorder`
- low stock only -> `delayed_release` / `delay_and_monitor`
- ready -> `ship_now` / `release_to_pick`

For shipping, compute total order weight as `sum(product.weight_lb * line.quantity)`, call `/shipping/quote` with the order warehouse, destination zip, total weight, and requested speed, then copy `zone_distance`, `service_days`, and rounded `total_cost` into the template.

Summaries count final decisions, total shipping cost, and sorted order ID lists by final outcome or exception category.

## Allocation Transfer Waves

Fetch all orders in the wave, then join each order to its customer, products, and inventory for the requested warehouse. For each line:

1. If the customer blocks automatic release, set `manual_review`, zero all quantities, and use the matching reason:
   - blocked account -> `account_blocked`
   - review-required account -> `account_review_required`
   - fraud watch -> `fraud_watch`
   - credit watch, if no explicit reason exists, usually maps to `account_review_required`
2. Else if the product is inactive, set `manual_review`, zero quantities, and use `inactive_product`.
3. Else if requested effective available covers the full quantity, set `ship`, `ship_quantity = quantity`, and all other quantities zero.
4. Else calculate `ship_quantity = max(0, requested_effective_available)` and `transfer_quantity = quantity - ship_quantity`. Look at the other warehouses for the same SKU. If one source warehouse has effective available at least `transfer_quantity`, set `transfer` and choose the source with the largest effective available, breaking ties by warehouse ID.
5. If no single source can clear the uncovered quantity, set `backorder`; backorder the unfilled quantity and use `insufficient_effective_stock`.

For transfer lines, create one transfer request using the selected source, requested warehouse as destination, and transfer quantity. Do not split one order line across multiple source warehouses.

Order rollup:

- all lines ship -> `ready_to_ship`
- all lines manual review -> `manual_review`
- transfer lines with all other lines ship -> `needs_transfer`
- any backorder and no manual-review or transfer lines -> `has_backorder`
- otherwise -> `mixed_actions`

`blocked_orders` contains only orders stopped by customer/account risk, not product-only manual reviews. Summaries are counts of orders, lines by action, blocked orders, transfer units, and backorder units.

## BOM Replenishment Packages

Read the production memo target builds and fetch each BOM. For every component SKU:

1. Aggregate `total_required = sum(quantity_per_kit * target_build_quantity)` across all target builds containing the SKU.
2. Use the planning site or BOM warehouse as the target warehouse.
3. Compute target effective available with the shared inventory rule.
4. Find same-SKU, same-target-warehouse purchase orders with status `open` or `confirmed` and ETA on or before the relevant component build date. Sort coverage PO IDs ascending and sum their quantities as `timely_po_qty`.
5. Let `gap = max(0, total_required - target_effective_available)`. Timely PO covered units are `min(gap, timely_po_qty)`.
6. If there is no remaining gap after timely POs, exclude the component as `timely_po_covers_gap`.
7. If there is no gap before POs, exclude as `target_overstock` when target effective available exceeds the product overstock threshold; otherwise use `stocked_no_gap`.
8. For remaining gap, request transfers from other warehouses using their positive effective available. Allocate from largest effective availability to smallest, breaking ties by warehouse ID, until the remaining gap is zero or no more transferable stock exists.
9. Any remaining gap after transfers becomes a purchase requisition for the product supplier at product unit cost.

Transfer request `needed_by` is the earliest build date for that component. Purchase requisition `needed_by` is the latest build date whose component demand remains uncovered after stock, timely POs, and transfers. If demand is not bucketed by date, use the latest target build date for that SKU.

Set final actions by outcome:

- no gap and stocked -> `no_action_stocked`
- no gap because target is overstocked -> `overstock_excluded`
- timely POs cover the gap -> `timely_po_covered`
- transfers cover the remaining gap -> `transfer_only`
- any purchase requisition remains -> `purchase_required`

Summary totals are unique component count, purchase units, rounded purchase cost, transfer units, and timely-PO-covered units, not total PO quantities.

## Supplier Incident Scorecards

Use the request's date filter, policy, and precision rules. Filter incidents by `open_date` inclusively. Join suppliers for names and quality status.

For each supplier with filtered incidents:

- `incident_count`: filtered incident rows
- `incident_percentage`: supplier count divided by total filtered population times 100
- `total_resolution_cost`: sum of incident resolution costs
- duration: calendar-day difference from `open_date` to `close_date`; for open incidents use `analysis_date`
- `rma_count` and `work_order_count`: count by `incident_type`
- `open_incident_count`: status `open`
- `severe_incident_count`: severity in the severe list from the request, usually high or critical

Apply the recommendation policy in the request, in its stated precedence. Typical conditions include quality hold plus incident volume, any critical RMA, high RMA cost/volume, work-order dominance, watch/quality status, severe counts, and default monitor.

Top escalation suppliers include only `ESCALATE_SUPPLIER`, sorted by incident count descending, total resolution cost descending, then supplier ID ascending. Highest cost/share supplier IDs use the maximum supplier totals; break ties by supplier ID unless the prompt says otherwise.

## Procurement Quality Holds

Read the target supplier IDs and analysis window from the memo. For each supplier:

- Fetch supplier metadata.
- Fetch recent incidents with inclusive `open_date` window.
- Fetch purchase orders for the supplier, retaining status `open` and `confirmed`.
- Count recent incidents, RMAs, open incidents, and high/critical severities.
- Sort unique affected SKUs ascending.
- Sort incident IDs ascending and use the first five as sample IDs.

When the memo gives only broad policy, use this precedence inferred from the training pattern:

- `quality_hold` suppliers with recent incidents -> `freeze_new_replenishment`
- otherwise, at least two high/critical recent incidents -> `buyer_review_required`
- otherwise -> `monitor_only`

For freeze or buyer-review decisions, hold the supplier's open/confirmed POs sorted by PO ID. The training pattern caps per-supplier held PO IDs at the first five when the template gives no larger explicit limit. Monitor-only suppliers have no held POs and appear in `release_supplier_ids`.

Top-level `held_po_ids` is the sorted unique union of supplier held POs. Summary counts suppliers reviewed, decisions by type, held PO count, and total recent incidents.
