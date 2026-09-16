# Northwind ERP Patterns

## API map
- `GET /products`: `sku`, `name`, `supplier_id`, `unit_cost`, `weight_lb`, `active`, `safety_stock`, `overstock_threshold`
- `GET /inventory`: `sku`, `warehouse_id`, `on_hand`, `reserved`, `quarantined`, `last_count_date`
- `GET /warehouses`: `warehouse_id`, `name`, `region`, `zip`
- `GET /orders`: `order_id`, `customer_id`, `warehouse_id`, `destination_zip`, `shipping_speed`, `priority`, `required_date`, `wave`, `lines`
- `GET /customers`: `customer_id`, `name`, `account_status`, `risk_flag`, `tier`, `margin_band`
- `GET /suppliers`: `supplier_id`, `name`, `quality_status`, `region`
- `GET /purchase_orders`: `po_id`, `sku`, `quantity`, `status`, `eta`, `supplier_id`, `warehouse_id`
- `GET /boms`: `bom_id`, `name`, `warehouse_id`, `target_date`, `components`
- `GET /incidents`: `incident_id`, `supplier_id`, `sku`, `incident_type`, `severity`, `status`, `open_date`, `close_date`, `resolution_cost`
- `GET /shipping/quote`: requires `warehouse_id`, `destination_zip`, `weight_lb`

## Common formulas
- `effective_available = on_hand - reserved - quarantined - safety_stock`
- `order_weight_lb = sum(line.quantity * product.weight_lb)`
- `incident_percentage = incident_count / filtered_incident_population * 100`
- `avg_duration_days`:
  - closed incident: `close_date - open_date`
  - open incident: `analysis_date - open_date`

## Expedite queues
Use this pattern when the prompt asks for per-order release, hold, review, or backorder decisions.

1. Join each order to the customer, inventory, product, and shipping quote records.
2. Compute line availability from the requested warehouse inventory.
3. Classify each line and aggregate to the order level.

Suggested line-level logic:
- `ready`: `effective_available >= quantity` for all active lines and no low-stock or inactive issues
- `low_stock`: positive `effective_available` in the 1-10 range and no shortage or inactive issue
- `shortage`: any active line has `effective_available < quantity`
- `inactive_sku`: any line uses a product with `active = false`
- `inactive_and_shortage`: both inactive and shortage are present

Suggested customer exception precedence:
1. `account_blocked` or `fraud_watch` or `credit_watch` -> `reject_hold` / `hold_credit_or_fraud`
2. `review_required` -> `manual_review` / `send_account_review`
3. inactive SKU without a customer hold -> `manual_review` / `escalate_product_master`
4. shortage without customer hold -> `backorder` / `create_backorder`
5. low stock without customer hold -> `delayed_release` / `delay_and_monitor`
6. ready with no exception -> `ship_now` / `release_to_pick`

Shipping quote:
- Use the order warehouse, destination zip, and computed weight.
- Keep only the returned `zone_distance`, `service_days`, and `total_cost_usd` fields required by the template.

Sorting and summary:
- Sort records by `order_id`.
- Sort SKU lists ascending.
- Compute summary counts from the final records, not from the source memo.

## Kit replenishment
Use this pattern when the prompt asks for BOM coverage, transfer planning, and purchase coverage.

1. Expand each target BOM into component demand.
2. Multiply `quantity_per_kit` by each build quantity and aggregate by SKU.
3. Compute `target_effective_available` at the build warehouse with the shared formula.
4. Sum same-warehouse open or confirmed POs whose `eta` is on or before the build date to get `timely_po_qty`.
5. If a SKU appears in multiple BOMs, allocate demand chronologically by build date so the earliest build consumes stock and transfers first.
6. If `timely_po_qty` closes the gap, exclude the component with `timely_po_covers_gap`.
7. If target stock already covers demand, exclude it as stocked or overstocked according to the template.
8. Otherwise allocate internal transfers from other warehouses with positive effective stock, usually taking the largest available source first.
9. Buy any remaining deficit from the product's supplier at `product.unit_cost`.

Field rules:
- `total_required = aggregated component demand`
- `transfer_qty = quantity covered by transfers`
- `purchase_requisition_qty = remaining uncovered quantity after stock, transfers, and timely POs`
- `coverage_po_ids` and `supporting_po_ids` must be sorted
- `extended_cost = quantity * unit_cost`, rounded to 2 decimals
- For `needed_by`, use the build date tied to the shortage slice being covered; earlier builds get earlier transfer dates and later residual demand gets later PO dates.

Common final actions:
- `timely_po_covered` when open/confirmed POs cover the gap
- `transfer_only` when internal stock can cover the gap
- `purchase_required` when a PR is still needed
- `overstock_excluded` when the target warehouse already has more than the build needs
- `no_action_stocked` when the component is already covered and the template wants it retained as stocked

## Supplier scorecards
Use this pattern when the prompt asks for a supplier-quality scorecard over a date window.

1. Filter incidents by `open_date` inclusively.
2. Group the filtered incidents by `supplier_id`.
3. Count incidents, RMAs, work orders, open incidents, and severe incidents.
4. Sum resolution cost and compute average duration with the open/closed rule above.
5. Compute each supplier's share of the filtered incident population.

Recommendation policy:
- `ESCALATE_SUPPLIER` has highest precedence.
- `PROCESS_REVIEW` comes next.
- `WATCHLIST` comes next.
- `MONITOR` is the fallback.

Observed policy shape:
- Escalate when quality is in hold plus incident burden is high, or when critical RMA risk is present, or when RMA burden and cost are both high.
- Use process review when work-order incidents dominate and are at least 3.
- Use watchlist for watch/hold suppliers with moderate burden, high filtered count, high cost, or multiple severe incidents.
- Otherwise monitor.

Ranking fields:
- `top_escalation_suppliers` includes only suppliers with `ESCALATE_SUPPLIER`
- Sort by incident count descending, then total resolution cost descending, then supplier_id ascending
- `highest_cost_supplier_id` is the max by total resolution cost
- `highest_share_supplier_id` is the max by incident percentage

## Transfer allocation
Use this pattern when the prompt asks for line-level ship, transfer, backorder, and manual-review decisions.

1. Compute requested-warehouse effective stock for each line.
2. If customer, risk, or product status blocks release, mark the line `manual_review`.
3. If the requested warehouse can cover the full line, mark `ship`.
4. If another warehouse can cover the uncovered quantity without protected stock, mark `transfer`.
5. Otherwise mark `backorder`.

Practical rules:
- For `ship`, set `ship_quantity = line quantity`.
- For `transfer`, set `ship_quantity` to the quantity the requested warehouse can release and `transfer_quantity` to the remainder.
- For `backorder`, set `backorder_quantity = line quantity`.
- Choose one source warehouse per transfer line.
- Use `primary_reason` to explain account or product blocks.

Order rollup:
- `ready_to_ship` if every line ships
- `needs_transfer` if the order is ship/transfer only and at least one line transfers
- `has_backorder` if any line backorders
- `mixed_actions` if ship/transfer actions coexist with manual review and no backorder
- `manual_review` if every line is manual review

Blocked orders:
- Include only orders stopped at account or customer-risk level.
- Keep the list sorted ascending.

## Procurement control
Use this pattern when the prompt asks for a replenishment-control decision on suppliers over a window.

1. Filter incidents by the memo's analysis window.
2. Build one supplier row per target supplier.
3. Count recent incidents, RMAs, severe or critical incidents, and open incidents.
4. Collect distinct affected SKUs and up to 5 sorted sample incident IDs.
5. List open or confirmed POs that should be held for each frozen or review-required supplier.
6. Union those held POs into `held_po_ids`.
7. List monitor-only suppliers in `release_supplier_ids`.

Decision guidance:
- Follow the memo's explicit policy if it gives one.
- If the memo is silent, use the conservative pattern from the examples: quality-hold or heavier recent burden freezes replenishment, watch-status suppliers with moderate risk move to buyer review, and lower-risk suppliers monitor.

Output discipline:
- Sort suppliers by `supplier_id`.
- Sort all SKU and incident-id lists.
- Keep `held_po_ids` unique and sorted.
