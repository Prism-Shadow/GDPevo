---
name: northwind-erp-control-desk
description: Use this skill for Northwind Components ERP tasks that ask for structured JSON decisions for dispatch, allocation, replenishment, procurement control, supplier quality scorecards, BOM kit builds, inventory availability, transfers, purchase orders, incidents, customers, products, warehouses, shipping quotes, or supplier controls. This skill is especially relevant when a prompt provides staged payloads and an answer template and expects exact operational JSON from the live ERP API.
---

# Northwind ERP Control Desk Workflow

Use this workflow to solve Northwind Components operational-control tasks that combine visible task payloads with the public ERP API. The goal is a strict JSON answer matching the provided template, not a narrative report.

## Ground Rules

Read only the prompt, visible payloads, answer template, and public ERP API records made available for the task. Treat the template as the contract: preserve required top-level keys, enum values, list ordering, date formats, and rounding rules exactly.

Before calculating, extract these items from the prompt and payloads:

- Task identifier, wave ID, memo/request ID, analysis window, plan date, target warehouses, order IDs, supplier IDs, BOM IDs, and build quantities.
- Required output keys and all allowed enum values.
- Required sorting rules for records, lines, suppliers, transfers, PO IDs, SKU lists, and summary lists.
- Currency and percentage precision.

Use the live API as source of truth for orders, products, customers, inventory, warehouses, shipping quotes, purchase orders, suppliers, incidents, and BOMs. Prefer endpoint filters when available, then join records locally by stable IDs.

## Common Calculations

Inventory fields usually mean:

- `raw_available = on_hand - reserved - quarantined`
- `protected_available = max(0, raw_available - product.safety_stock)`

Use `protected_available` when the task is deciding whether stock can be released, transferred, or allocated without using operating buffer. This is especially important for dispatch and allocation tasks that mention buffers, protected stock, or transfer feasibility.

Use raw usable availability for a replenishment target site unless the prompt or template specifically says safety stock must also be protected at the target. For transfer sources, use protected availability so a transfer does not drain another warehouse below safety stock.

Customer/account gates:

- `account_status: blocked` maps to an account-blocked hold.
- `risk_flag: fraud_watch` or `credit_watch` is a customer-risk hold.
- `account_status: review_required` prevents automatic release but is weaker than a hard blocked/fraud hold.
- In line-level allocation, if an order is stopped by account review or customer risk, keep that account/risk reason as the line `primary_reason` for the stopped lines.

Product gates:

- `active: false` is an inactive-product/product-master exception.
- For active-account orders, inactive products should become manual review lines or inactive SKU exceptions before considering transfer or backorder.

Always sort identifier lists ascending unless the template gives another rule. Round currency to two decimals, durations to the requested precision, and percentages to the requested precision.

## Dispatch / Expedite Queues

For each memo order, fetch the live order, customer, product, inventory, and shipping records. Sort output records by `order_id`.

For every order line:

- Calculate protected availability at the order warehouse.
- Mark shortage SKUs when protected availability cannot cover the requested quantity.
- Mark inactive SKUs from product master status.
- Use low-stock classification only when there is no shortage but releasing would leave the warehouse near or below the product safety buffer.

Decision precedence that transfers well:

1. Hard account/risk holds: hold or reject according to the template enum.
2. Inactive product: manual review or product-master escalation.
3. Protected-stock shortage: backorder.
4. Account review required: manual account review.
5. Low stock with no hard shortage: delayed release or monitor.
6. Otherwise release to pick/ship now.

For shipping quotes, compute order weight as the sum of `line.quantity * product.weight_lb`. Call the quote endpoint with the order warehouse, destination ZIP, total weight, and requested speed. Map the API quote cost into the template's cost field and round to two decimals.

Build summary counts from the final record list, not from separate hand counts.

## BOM Replenishment / Kit Builds

For kit-build tasks, fetch each BOM and aggregate component demand by SKU:

- `total_required = sum(quantity_per_kit * target_build_quantity)` across all requested BOMs.
- `needed_by` is usually the earliest build date requiring that SKU.
- Keep kit targets sorted by BOM ID.

For each component:

1. Calculate target warehouse raw availability.
2. Find same-warehouse open or confirmed POs whose ETA is on or before the component needed-by date.
3. Keep `coverage_po_ids` sorted and report PO quantity according to the template wording. If the template asks for eligible PO units, use the eligible PO quantity; if it asks for gap coverage, cap at the gap.
4. Subtract target availability and eligible PO coverage before proposing transfers or purchases.
5. Use protected availability at other warehouses for transfer sources.
6. Purchase only the remaining residual from the product's supplier, using product `unit_cost`.

Common action mapping:

- No gap after target stock: `no_action_stocked`.
- Target stock exceeds product overstock threshold: `overstock_excluded`.
- Timely same-warehouse PO coverage clears the gap: `timely_po_covered`.
- Transfer clears the residual without purchase: `transfer_only`.
- Any residual after feasible transfer: `purchase_required`.

Create purchase requisitions and transfer requests only for positive quantities. Sort transfer requests by the template rule, often SKU ascending, quantity descending, and source warehouse ascending.

## Allocation / Transfer Waves

For each order line in the wave, output one line action sorted by `order_id`, then `line_id`.

Use protected availability at the requested warehouse for `requested_effective_available`. Reserved, quarantined, and safety-buffer stock are not freely available.

Line decision flow:

1. If the customer/order is stopped by account block, account review, fraud watch, or credit watch, set `manual_review` with the matching account/risk reason and zero ship/transfer/backorder quantities.
2. Else if the product is inactive, set `manual_review` with inactive-product reason and zero movement quantities.
3. Else if requested protected availability covers the full line, set `ship` with full ship quantity.
4. Else compute the uncovered quantity after any usable requested-warehouse stock. If one source warehouse can cover the uncovered quantity from protected availability, set `transfer`, keep the usable requested stock as `ship_quantity`, and create a matching transfer request.
5. If no source can clear the uncovered quantity, set `backorder`; ship only any usable requested-warehouse quantity and backorder the residual.

When the memo says to choose one source warehouse for a transfer line, do not split that line across multiple sources. Choose deterministically, usually the source with the largest protected surplus, then warehouse ID as a tie-breaker.

`blocked_orders` should include orders stopped at the account or customer-risk level, not orders whose only issue is product inactivity or line stock.

For order rollups, derive the outcome from the set of line actions after all lines are classified. For mixed line outcomes, use the template's most specific allowed value, such as `needs_transfer`, `has_backorder`, `manual_review`, or `mixed_actions`.

## Supplier Incident Scorecards

Filter incidents by the request's date field, usually `open_date`, inclusively between the start and end dates. Group only the filtered population.

For each supplier with filtered incidents:

- Count incidents, RMA incidents, work-order incidents, open incidents, and severe incidents.
- Treat severity values listed by the request, commonly `high` and `critical`, as severe.
- Sum `resolution_cost` and round to two decimals.
- For closed incidents, duration is calendar days from open date to close date.
- For open incidents, duration is calendar days from open date to the analysis date.
- Incident percentage is supplier incident count divided by all filtered incidents, not by that supplier's incidents.

Apply recommendation policies exactly in stated precedence order. Do not collapse conditions or reorder them because the first matching higher-precedence code wins.

Sort supplier rows by supplier ID unless told otherwise. Sort top escalation suppliers by the requested multi-key rule, commonly incident count descending, total cost descending, then supplier ID ascending.

## Procurement Quality Controls

For supplier-control tasks, filter recent incidents by the memo's analysis window and target supplier IDs. Use supplier quality status, recent incidents, and open/confirmed purchase orders together.

For each supplier:

- Count recent incidents, recent RMAs, severe/critical incidents, and open incidents.
- Build `affected_skus` from the filtered incidents and sort ascending.
- Build `sample_incident_ids` from sorted incident IDs and cap at the template maximum.
- Include supplier name and current quality status from the supplier master.

Decision guidance:

- `quality_hold` suppliers usually require `freeze_new_replenishment`.
- `watch` suppliers with meaningful recent quality risk usually require `buyer_review_required`.
- Approved suppliers with no material recent risk usually remain `monitor_only`.
- If the task memo provides a stricter policy for critical incidents, repeated RMAs, open incidents, or severe counts, follow that policy over the defaults above.

For held purchase orders, start from open or confirmed POs for suppliers that are frozen or under buyer review. Decide whether to hold all such supplier POs or only affected-SKU POs from the prompt wording; if the template says all held POs without narrowing to affected SKUs, use supplier-level open/confirmed POs.

## Final Validation

Before returning the answer:

- Confirm every required key from the answer template is present.
- Remove explanatory text outside JSON.
- Check enum spelling exactly.
- Check all lists use the requested sort order.
- Recompute summaries from output rows.
- Confirm currency, percentages, and durations use the requested precision.
- Confirm no local-only or hidden artifacts influenced the answer.
