---
name: northwind-erp-json-solver
description: Solve Northwind Components ERP API tasks that require strict JSON answers from local prompt payloads, answer templates, and public ERP endpoints for orders, inventory, products, customers, suppliers, incidents, BOMs, purchase orders, warehouses, and shipping quotes.
---

# Northwind ERP JSON Solver

Use this skill for Northwind Components tasks where the prompt provides local payload files and a `<TASK_ENV_BASE_URL>` for the shared ERP API. Produce only the JSON object requested by the task template.

## Required Workflow

1. Read the task prompt, every file under `input/payloads/`, and especially `answer_template.json`.
2. Extract requested IDs, date windows, waves, target suppliers, BOMs, build quantities, and any recommendation policy from the local payloads.
3. Fetch live data only through the public API base URL from the runner or prompt. Do not inspect environment source files or private judge endpoints.
4. Build the result in memory with exact template keys, allowed enum values, requested ordering, and required numeric precision.
5. Validate every count, sum, sorted list, and union list before returning. Return no prose outside the JSON.

Useful helper: `scripts/northwind_erp.py` can fetch API paths, compute effective inventory for one SKU/warehouse, and quote an order shipment.

## Public API Records

Use the endpoints named in the task or environment note:

- `/products`, `/products/<sku>`
- `/customers`, `/customers/<customer_id>`
- `/warehouses`
- `/inventory?warehouse_id=&sku=`
- `/purchase_orders?supplier_id=&sku=&status=`
- `/orders?wave=&required_date=&customer_id=`, `/orders/<order_id>`
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `/suppliers`
- `/boms`, `/boms/<bom_id>`

Core record fields seen across tasks:

- Product: `sku`, `active`, `supplier_id`, `unit_cost`, `weight_lb`, `safety_stock`, `overstock_threshold`.
- Inventory: `warehouse_id`, `sku`, `on_hand`, `reserved`, `quarantined`.
- Order: `order_id`, `wave`, `customer_id`, `warehouse_id`, `destination_zip`, `shipping_speed`, `lines`.
- Customer: `account_status`, `risk_flag`, `tier`.
- Supplier: `supplier_id`, `name`, `quality_status`.
- Incident: `incident_id`, `supplier_id`, `sku`, `open_date`, `close_date`, `status`, `incident_type`, `severity`, `resolution_cost`.
- Purchase order: `po_id`, `supplier_id`, `sku`, `warehouse_id`, `status`, `quantity`, `eta`.

## Shared Calculations

- `effective_available = on_hand - reserved - quarantined - product.safety_stock`.
- Use only `open` or `confirmed` POs unless the prompt says otherwise.
- Date filters on incidents use `open_date` inclusively when the payload specifies an inclusive window.
- Calendar duration is `close_date - open_date` for closed incidents, or `analysis_date - open_date` for open incidents.
- Shipping weight is the sum of `line.quantity * product.weight_lb`; quote with the order warehouse, destination ZIP, total weight, and requested speed.
- Currency: round to two decimals. Percentages in scorecards: round to one decimal. Average durations: round to two decimals.
- Sort all lists exactly as the template says. Sort SKU and ID lists ascending unless another ordering is specified.

## Order Allocation And Expedite Tasks

Fetch the target orders by explicit IDs or by wave. Join each order to its customer, each line to its product, and requested-warehouse inventory.

Customer/account precedence:

- `account_status == "blocked"` stops automatic release. Use an account-blocked/reject-hold or manual-review outcome according to the template.
- `risk_flag == "fraud_watch"` or `risk_flag == "credit_watch"` is a customer-risk hold unless the template has a more specific enum.
- `account_status == "review_required"` causes manual review.
- Product inactivity causes product-master manual review or an inactive SKU status. If both customer and product issues exist, use the template's higher-precedence customer hold/review action unless it asks to expose both.

Line inventory decisions:

- For each line, compute requested-warehouse `effective_available` before allocating this task's order.
- `ship`: product and customer are clear and requested effective stock covers the full line quantity.
- `transfer`: requested stock cannot cover the full line, but one other warehouse can cover the uncovered quantity from positive effective stock. Leave any usable requested-warehouse quantity as `ship_quantity`.
- `backorder`: product and customer are clear, and neither requested stock nor one transfer source can clear the line.
- `manual_review`: account, risk, or inactive product prevents automatic release.

Expedite inventory status:

- `shortage_skus`: active line SKUs where requested effective stock is less than line quantity.
- `inactive_skus`: inactive product SKUs.
- `low_stock_skus`: active non-shortage SKUs where requested effective stock is positive but below the product `safety_stock`.
- Status precedence: `inactive_and_shortage`, `inactive_sku`, `shortage`, `low_stock`, then `ready`.
- Final decision precedence: hard customer holds, account reviews, inactive product escalation, backorder for shortages, delayed release for low stock if the template uses it, otherwise ship.

For transfer requests, choose a single source warehouse for the uncovered quantity. Use positive effective stock only, prefer the source with the largest available quantity that can cover the gap, and tie-break by warehouse ID. If no single source can cover the gap, backorder rather than splitting unless the prompt permits multiple sources.

Order rollups usually follow this precedence:

- all lines ship: `ready_to_ship`
- any account/risk-only manual review: `manual_review`
- all non-ship lines are transfers or ship plus transfer: `needs_transfer`
- any backorder with otherwise shippable lines: `has_backorder`
- mixed product-review/manual/backorder/transfer outcomes: `mixed_actions`

## BOM Replenishment Tasks

For each target build:

1. Fetch the BOM and product records.
2. Expand components as `quantity_per_kit * target_build_quantity`.
3. Aggregate `total_required` per SKU across all target builds, while retaining build-date layers for `needed_by`.
4. Compute target-warehouse effective availability for each SKU.
5. Compute the initial gap as `max(0, total_required - target_effective_available)`.

Exclusion and coverage rules:

- `target_overstock`: target effective availability is greater than the product `overstock_threshold`.
- `stocked_no_gap`: target effective availability covers the full requirement without overstock.
- `timely_po_covers_gap`: same-warehouse open or confirmed POs with `eta <= needed_by` cover the remaining gap. Report coverage PO IDs sorted ascending and count only the gap covered, not all PO units, in covered-units summaries.

Replenishment sequence:

1. Exclude target overstock and stocked components.
2. Apply timely same-warehouse PO coverage.
3. Use transfers from other warehouses with positive effective availability, allocating largest effective source first and preserving chronological build needs.
4. Create purchase requisitions for any remaining gap. Use product `supplier_id`, `unit_cost`, and `extended_cost = quantity * unit_cost`.

Set `final_action` from the actual residual: overstock excluded, no action stocked, timely PO covered, transfer only, or purchase required. Transfer and purchase `needed_by` should correspond to the build-date layer the quantity is satisfying.

## Supplier Incident Scorecards

Fetch incidents for the requested date window and suppliers from `/incidents`, then join suppliers from `/suppliers`.

For each supplier with filtered incidents:

- Count total incidents, RMA incidents, WORK_ORDER incidents, open incidents, and severe incidents (`high` or `critical` unless the payload defines a different severe set).
- Sum resolution cost.
- Compute percentage as supplier incident count divided by total filtered incident population.
- Compute average duration using the payload's open/closed duration rule.
- Apply the payload recommendation policy in stated precedence order. Do not invent recommendation codes outside the template.

Top-level scorecard values:

- `filtered_incident_count`: number of incidents after filtering.
- `supplier_count`: suppliers with at least one filtered incident.
- Overall RMA and work-order counts: counts over the full filtered population.
- Top escalation list: only suppliers with the escalation recommendation, sorted by the template's ordering.
- Highest cost/share IDs: choose by the computed metric; tie-break deterministically by supplier ID if unspecified.

## Supplier Quality Hold Reviews

Use target supplier IDs and the requested incident window. For each supplier:

- `affected_skus`: sorted unique SKUs from recent incidents.
- `sample_incident_ids`: first five sorted incident IDs unless the template says otherwise.
- `held_po_ids`: sorted open or confirmed POs selected for suppliers whose decision holds replenishment. The examples cap this per-supplier list at five sorted PO IDs when the template is silent and many candidates exist.
- `release_supplier_ids`: suppliers with a monitor/release decision.

Decision guidance when the payload gives only generic choices:

- `freeze_new_replenishment`: supplier is on `quality_hold`, or the task policy defines an equivalent hard stop.
- `buyer_review_required`: supplier is on `watch` with multiple severe or critical incidents, or the policy defines an intermediate review trigger.
- `monitor_only`: no hard stop or buyer-review trigger applies.

Top-level `held_po_ids` is the sorted unique union of the per-supplier held lists actually included in the rows.

## Final Validation Checklist

- Top-level keys exactly match the template.
- Every enum value is one allowed by the template.
- All required lists are sorted as specified.
- Counts equal list lengths and category counts from rows.
- Totals equal summed rounded line values where the template expects currency totals.
- No task memo IDs, notes, or intermediate diagnostics leak into the final JSON unless the template explicitly requires them.
