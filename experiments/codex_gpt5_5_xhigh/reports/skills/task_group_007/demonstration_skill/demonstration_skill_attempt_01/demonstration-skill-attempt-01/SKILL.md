---
name: task-group-007-fewshot-attempt-01
description: Use for Northwind Components ERP decision tasks that require JSON outputs for order expedition, kit replenishment, supplier incident scorecards, allocation transfer decisions, or procurement quality holds using the local shared API.
---

# Northwind ERP Decision Skill

## Scope

Use this skill when a task asks for a structured Northwind Components operations answer from the shared ERP API. Typical tasks involve:

- Expedite queue fulfillment decisions.
- Kit/BOM replenishment planning.
- Supplier incident scorecards.
- Mixed-warehouse order allocation and transfer decisions.
- Procurement controls for suppliers with recent quality risk.

Return only the requested JSON. Always read the task prompt, memo, and answer template first; the template controls exact top-level keys, enum values, field names, sorting, and precision.

## API Usage

Use the public local API, not environment files. In this evaluation the base URL is:

```text
http://127.0.0.1:8100
```

Useful endpoints:

- `GET /` lists available routes.
- `GET /health` returns manifest and record counts.
- `GET /orders?wave=&required_date=&customer_id=` and `GET /orders/<order_id>`.
- `GET /customers` and `GET /customers/<customer_id>`.
- `GET /products` and `GET /products/<sku>`.
- `GET /inventory?warehouse_id=&sku=`.
- `GET /warehouses`.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`.
- `GET /boms` and `GET /boms/<bom_id>`.
- `GET /purchase_orders?supplier_id=&sku=&status=`.
- `GET /suppliers`.
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`.

Some collection endpoints may return more records than needed. Filter locally to the memo's order IDs, wave, BOM IDs, supplier IDs, or date window. Use `curl --noproxy '*'` or a Python HTTP client with proxy bypass if the environment has proxy settings.

## Shared Calculations

Effective availability for a SKU at a warehouse is:

```text
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

This protected-stock formula is used for requested warehouses, transfer-source warehouses, target kit sites, and over/short calculations. Do not treat reserved, quarantined, or safety-stock units as freely available.

Currency fields are rounded to two decimals. Percentages in scorecards are rounded to one decimal. Duration averages are rounded to two decimals, though JSON may naturally display a whole result as `58.0`.

Sort all lists exactly as the answer template says. Common sort orders are by ID ascending, SKU ascending, or the explicit tie-break chain in the memo.

## Expedite Queue Decisions

Inputs usually provide a memo with a wave ID and order IDs. For each order:

1. Fetch the order, customer, products, requested-warehouse inventory, warehouses, and shipping quote.
2. Compute line effective availability at the order warehouse.
3. Build SKU exception lists:
   - `shortage_skus`: active or inactive SKUs where requested quantity is greater than effective availability. If effective availability is negative, the shortage is still the full requested line quantity for decision purposes.
   - `inactive_skus`: products where `active` is false.
   - `low_stock_skus`: active SKUs with enough effective availability to fill the line, but remaining or current effective availability is still thin; train examples treat positive effective availability below the product safety-stock level as low stock.
4. Classify `inventory_status` by precedence:
   - inactive and shortage present: `inactive_and_shortage`.
   - inactive only: `inactive_sku`.
   - any shortage: `shortage`.
   - low stock only: `low_stock`.
   - otherwise: `ready`.
5. Classify `customer_exception` from customer fields:
   - `account_status=blocked` overrides risk flags and becomes `account_blocked`.
   - `account_status=review_required` becomes `review_required`.
   - `risk_flag=fraud_watch` or `credit_watch` becomes the matching exception when the account is otherwise active.
   - otherwise `none`.
6. Decide final fulfillment by precedence:
   - Account blocked, fraud watch, or credit watch stops release: `reject_hold` with `hold_credit_or_fraud`.
   - Account review required stops automatic release: `manual_review` with `send_account_review`.
   - Inactive product without account block requires product-master escalation: usually `manual_review` with `escalate_product_master`.
   - Shortage without customer/product block: `backorder` with `create_backorder`.
   - Low stock without shortage: `delayed_release` with `delay_and_monitor`.
   - Clean ready order: `ship_now` with `release_to_pick`.
7. Quote shipping even when the order will not ship. Use total shipment weight `sum(product.weight_lb * line.quantity)` and call `/shipping/quote` with the order warehouse, destination ZIP, total weight, and order `shipping_speed`. Output `zone_distance`, `service_days`, and `total_cost_usd` from `total_cost`.

Summary fields are derived from the records: counts by decision, total shipping cost, and sorted order-ID lists for blocked, manual review, backorder, and inactive-SKU cases.

## Kit Replenishment Planning

Inputs name target BOMs, build quantities, target warehouse, and build dates. For each BOM, fetch the BOM and product data.

Component rules:

- `total_required` is the sum across all target BOMs of `quantity_per_kit * build_quantity`.
- `target_effective_available` uses the shared effective availability formula at the planning warehouse.
- Initial gap is `total_required - target_effective_available`.
- If target effective availability is above the product overstock threshold, exclude the component with `final_action=overstock_excluded` and `exclusion_reason=target_overstock`.
- If there is no positive gap and no overstock issue, use `no_action_stocked` and `stocked_no_gap`.
- Eligible timely POs are open or confirmed purchase orders for the same SKU and target warehouse that arrive early enough for the build need. If timely PO quantity covers the positive gap, use `timely_po_covered`, list sorted `coverage_po_ids`, and do not create transfer or purchase requests.
- For uncovered gaps, use transfer-source warehouses only up to their positive effective availability. Do not use protected stock. Split transfers by source as needed, sorted per template.
- Purchase requisition quantity is the remaining gap after target stock, timely POs, and feasible transfers. Use `product.supplier_id`, target warehouse, `product.unit_cost`, and `quantity * unit_cost` for extended cost.

Date guidance:

- Transfer `needed_by` is the earliest build date where the component shortage affects the run.
- Purchase requisition `needed_by` is the build date by which the remaining purchased units are needed, often the later build when transfers cover the first shortage.

Summary pitfalls:

- `timely_po_qty` in `component_plan` is the full eligible PO quantity, but `summary.timely_po_covered_units` is the gap units covered by timely POs, not necessarily the full PO quantity.
- `total_purchase_cost` is the sum of rounded requisition extended costs.

## Supplier Incident Scorecards

Use the request's incident date filter, normally `open_date` inclusive between start and end. Join incidents to supplier records.

For each supplier with at least one filtered incident:

- `incident_count`: filtered incident count.
- `incident_percentage`: supplier count divided by all filtered incidents, percent rounded to one decimal.
- `total_resolution_cost`: sum of filtered `resolution_cost`, rounded to two decimals.
- `avg_duration_days`: average calendar-day duration. Closed incidents use `close_date - open_date`; open incidents use `analysis_date - open_date`.
- `rma_count` and `work_order_count`: counts by `incident_type`.
- `open_incident_count`: incidents with `status=open`.
- `severe_incident_count`: incidents whose severity is `high` or `critical`, unless the request lists different severe values.
- `recommendation_code`: apply the request's recommendation policy in stated precedence order, not in arbitrary order.

Policy pattern from the training requests:

- `ESCALATE_SUPPLIER` can be triggered by quality hold plus incident volume, any critical RMA, or high RMA count with high total cost.
- `PROCESS_REVIEW` can be triggered when work-order incidents are at least three and exceed RMA incidents.
- `WATCHLIST` can be triggered by watch/quality-hold status, incident volume, high total cost, or multiple severe incidents.
- `MONITOR` is the fallback.

Build top-level fields from supplier rows:

- `top_escalation_suppliers`: only suppliers with `ESCALATE_SUPPLIER`, sorted by incident count descending, total cost descending, then supplier ID ascending.
- `highest_cost_supplier_id`: supplier with max total filtered resolution cost.
- `highest_share_supplier_id`: supplier with max incident share/count.

## Allocation And Transfers

For a mixed-warehouse order wave, evaluate every order line sorted by `order_id`, then `line_id`.

Manual-review precedence:

1. Customer `account_status=blocked`: `action=manual_review`, `primary_reason=account_blocked`.
2. Customer `account_status=review_required`: `manual_review`, `primary_reason=account_review_required`.
3. Customer `risk_flag=fraud_watch`: `manual_review`, `primary_reason=fraud_watch`.
4. Product inactive: `manual_review`, `primary_reason=inactive_product`.

For manual-review lines, set `ship_quantity=0`, `transfer_from=null`, `transfer_quantity=0`, and `backorder_quantity=0`.

Inventory actions when no manual-review condition applies:

- Compute `requested_effective_available` at the order warehouse.
- If requested effective availability covers the line quantity, `action=ship`, `ship_quantity=line.quantity`, reason `none`.
- If requested warehouse has partial positive availability, keep that as `ship_quantity`; if it is zero or negative, ship zero from the requested warehouse.
- The uncovered quantity is `line.quantity - ship_quantity`.
- If one other warehouse has enough positive effective availability to cover the uncovered quantity, use `action=transfer`, choose one source warehouse, set `transfer_quantity` to the uncovered quantity, and add a matching transfer request.
- If no single source can cover the uncovered quantity, use `action=backorder`, `backorder_quantity=line.quantity` when requested effective availability is not usable, otherwise the remaining uncovered quantity.

Order-level outputs:

- `blocked_orders` contains orders stopped by account or customer-risk reasons only. Do not include orders that only have product inactive manual review.
- `order_rollup`:
  - all shippable lines: `ready_to_ship`;
  - any account/risk manual review at order level: `manual_review`;
  - transfer lines with no manual-review/backorder conflict: `needs_transfer`;
  - ship plus backorder: `has_backorder`;
  - product-only manual review mixed with another action: `mixed_actions`.

Summaries are counts of line actions, unique orders, transfer units, and backorder units.

## Procurement Quality Hold Review

Use the memo's target supplier IDs and inclusive analysis window. Fetch suppliers, recent incidents, products for affected SKUs, and purchase orders.

For each supplier:

- `quality_status`: from supplier record.
- `recent_incident_count`: incidents whose `open_date` is in the analysis window.
- `recent_rma_count`: recent incidents with `incident_type=RMA`.
- `severe_or_critical_count`: severity `high` or `critical`.
- `open_incident_count`: recent incidents still open.
- `affected_skus`: sorted unique SKUs from recent incidents.
- `sample_incident_ids`: sorted incident IDs, capped at five.

Decision pattern:

- `freeze_new_replenishment`: quality-hold suppliers with substantial recent incident volume or open/severe risk.
- `buyer_review_required`: watch suppliers with multiple severe/critical recent incidents or enough risk to require a buyer decision but not a full freeze.
- `monitor_only`: lower-risk watch/approved suppliers; include these supplier IDs in `release_supplier_ids`.

Held PO guidance:

- Hold only for suppliers whose decision is `freeze_new_replenishment` or `buyer_review_required`.
- Consider open or confirmed POs for that supplier; do not hold received or cancelled POs.
- Training examples list held PO IDs sorted ascending and cap long supplier PO lists at the first five IDs per held supplier.
- Top-level `held_po_ids` is the sorted unique union of per-supplier held PO IDs.

Summary counts are derived from supplier decisions: reviewed suppliers, freeze/buyer-review/monitor counts, held PO count, and total recent incident count.

## Common Pitfalls

- Do not read environment files; the public API has all operational records needed.
- Do not use raw `on_hand` as available stock. Always subtract reserved, quarantined, and safety stock.
- Customer/account exceptions override otherwise shippable inventory.
- Product inactive is a line/product issue, not an account-blocked order.
- Shipping quotes are still required for expedite orders that become review, hold, or backorder.
- Apply recommendation and decision precedence exactly; many rows satisfy lower-precedence rules too.
- Use inclusive date windows for incident filters unless the request says otherwise.
- Keep JSON numeric precision and ordering stable; most wrong answers come from list order, rounding, or counting the wrong population.
