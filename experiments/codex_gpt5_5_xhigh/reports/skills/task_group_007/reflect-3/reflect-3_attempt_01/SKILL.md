---
name: northwind-erp-operations-control
description: Use this skill for Northwind Components ERP tasks that ask for structured JSON decisions, scorecards, replenishment plans, allocation files, expedite controls, supplier quality reviews, or any task requiring live ERP API joins across orders, customers, products, inventory, warehouses, shipping, BOMs, purchase orders, suppliers, and incidents.
---

# Northwind ERP Operations Control

Use this workflow when a task provides local payloads plus a Northwind ERP API and asks for a JSON answer. Treat the prompt, answer template, and task memo as the contract. Use the public API records as the source of truth for operational data.

## First Pass

1. Read the prompt, memo, and answer template before querying broadly.
2. Identify the exact IDs in scope: order IDs, wave ID, BOM IDs, supplier IDs, date window, target warehouse, and required output ordering.
3. Query the API root to confirm available endpoints, then fetch only the relevant records.
4. Build small keyed maps for products, customers, suppliers, inventory by `(warehouse_id, sku)`, orders by `order_id`, and purchase orders/incidents by supplier or SKU.
5. Compute all numeric fields explicitly, then assemble JSON in the template's key order.
6. Before final output, validate required keys, enum values, sort order, rounding, and summary totals against the row-level data.

## Inventory And Availability

Use protected effective stock for release, transfer, and replenishment decisions:

```text
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

Let this value be negative. Do not silently clamp it to zero in fields named `effective_available`.

For stock actions:

- `ship`: requested warehouse effective stock covers the full line quantity.
- `transfer`: requested warehouse cannot cover the full line, but one alternate warehouse can cover the uncovered quantity from its effective stock.
- `backorder`: neither the requested warehouse nor a single alternate warehouse can clear the uncovered quantity.
- `manual_review`: customer account/risk status or inactive product status blocks automatic release.

For transfer lines, set `ship_quantity` to the usable positive effective stock at the requested warehouse, up to the requested quantity. Set `transfer_quantity` to the remaining uncovered quantity. Choose one source warehouse with enough effective stock for that uncovered amount; using the source with the largest effective availability is a good default when the task gives no tie-breaker.

## Customer And Product Holds

Apply account and risk holds before line-level stock movement:

- `blocked` account: use account-blocked handling.
- `review_required` account: use account-review handling.
- `fraud_watch` risk: use fraud-watch handling.
- `credit_watch` risk: use credit-watch handling when no stronger blocked-account classification is required by the template.

In allocation-style tasks, customer account or risk issues stop every line on that order as `manual_review`, even lines with enough stock. Include those orders in customer-level blocked/review lists when the template asks for orders stopped at account or customer-risk level.

Inactive products also cause `manual_review`. If an order is already stopped by customer account/risk, use the customer reason as the primary reason for all its lines. If the customer is clear, use `inactive_product` for inactive SKU lines.

## Order Waves And Shipping

For expedite and dispatch-control tasks:

1. Fetch each order from the memo or wave, plus its customer, product, inventory, and warehouse records.
2. Classify inventory from protected effective stock. If any active line has `effective_available < quantity`, treat it as a shortage for that SKU.
3. If inactive SKUs are also short, use the combined inactive-and-shortage classification when the template provides one.
4. Account/risk exceptions determine hold or manual-review decisions; otherwise shortages become backorder decisions, and fully covered orders can be released.
5. Compute package weight as the sum of `line.quantity * product.weight_lb`.
6. Call the shipping quote endpoint with the order warehouse, destination ZIP, computed weight, and requested shipping speed. Copy returned zone distance, service days, and total cost, rounded to two decimals.

Summary lists and counts must be derived from final row decisions, not recomputed by a different rule.

## Allocation Files

For mixed-warehouse allocation:

- Sort line actions by `order_id`, then `line_id`.
- Fill `requested_effective_available` with the protected effective stock at the requested warehouse.
- For `manual_review`, set ship, transfer, and backorder quantities to zero unless the template explicitly says otherwise.
- For `backorder`, set `backorder_quantity` to the unfilled requested quantity after any usable requested-warehouse effective stock. If effective stock is negative, ship zero and backorder the full quantity.
- Transfer request rows should mirror only lines whose action is `transfer`.

Order rollups:

- `ready_to_ship`: all lines ship.
- `needs_transfer`: at least one transfer and no manual review or backorder.
- `has_backorder`: at least one backorder and no manual review.
- `manual_review`: all lines are manual review.
- `mixed_actions`: manual review combined with another action, or otherwise mixed outcomes that do not fit the simpler labels.

## BOM Replenishment

For kit-build replenishment:

1. Expand each target BOM by build quantity.
2. Aggregate component demand by SKU across all target builds.
3. Use the memo's requested build dates, not stale BOM target dates, for `build_date`.
4. Compute target warehouse effective availability with the protected-stock formula.
5. Eligible timely POs are same-warehouse, `open` or `confirmed`, and due no later than the component's relevant build need date. Exclude `received` and `cancelled`.
6. Record the full eligible PO quantity in `timely_po_qty` and include sorted coverage PO IDs.
7. If timely same-warehouse POs cover the gap, use the template's timely-PO action/reason and do not add transfers or purchases.
8. If current effective availability exceeds the product overstock threshold, use the template's overstock action/reason instead of treating it as ordinary stocked coverage.
9. After target effective stock and timely POs, use effective surplus from other warehouses for transfers.
10. Purchase only the remaining gap after effective stock, timely POs, and transfers.

For shared components used by multiple builds, reason chronologically. If transfers and current stock cover the earlier build and the purchase remainder is only needed for a later build, put the purchase requisition `needed_by` date on that later build date.

For purchase requisitions:

```text
extended_cost = quantity * product.unit_cost
```

Round currency fields to two decimals. Summary purchase units, transfer units, and costs must equal the detail rows.

## Incident Scorecards

For incident scorecards:

1. Use the API incident date filters inclusively as requested by the task.
2. Group filtered incidents by `supplier_id`.
3. Join supplier names and quality status from the supplier endpoint.
4. Count `RMA` and `WORK_ORDER` from `incident_type`.
5. Count open incidents from the incident `status` field.
6. Count severe incidents using the task's severity set, usually `high` and `critical`.
7. For closed incidents, duration is calendar-day difference from `open_date` to `close_date`. For open incidents, use the task's analysis date as the end date.
8. Percentages use the full filtered incident population as denominator, rounded to one decimal place.
9. Costs are summed and rounded to two decimals; average durations are rounded to two decimals.

Apply recommendation policies in the exact precedence order given by the memo. Stop at the first matching recommendation. For top supplier lists, apply the requested sort exactly, commonly incident count descending, then total cost descending, then supplier ID ascending.

## Supplier Quality Controls

For procurement-control tasks over target suppliers:

- Filter incidents to the task's analysis window and target supplier IDs.
- For each supplier, compute recent incident count, RMA count, severe-or-critical count, open incident count, sorted affected SKUs, and up to five sorted sample incident IDs.
- Fetch supplier quality status and open or confirmed POs for reviewed suppliers.
- Use the task policy when present. If the task gives only broad policy wording, a conservative hierarchy is: `quality_hold` or major repeated/severe activity freezes new replenishment; `watch` status, open incidents, or severe recent incidents require buyer review; clean approved suppliers can be monitor-only.
- Keep `held_po_ids` aligned with the chosen decision and task wording. If the policy is supplier-wide, hold all open or confirmed supplier POs. If the policy is SKU-specific, hold only POs for affected SKUs.
- `release_supplier_ids` should contain only suppliers whose decision is monitor-only.

## Output Discipline

- Return only JSON when the prompt asks for JSON.
- Do not include extra explanatory keys unless the template allows them.
- Preserve required enum spelling exactly.
- Sort lists exactly as the template says. If no tie-breaker is given, use stable ascending IDs.
- Use integers for unit counts and two-decimal numbers for currency.
- Recompute summary counts from the final detail arrays immediately before answering.
