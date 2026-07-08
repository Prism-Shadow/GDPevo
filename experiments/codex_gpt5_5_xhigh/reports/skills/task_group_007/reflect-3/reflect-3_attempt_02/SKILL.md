---
name: northwind-erp-structured-decisions
description: Use this skill for Northwind Components ERP tasks that require a strict JSON answer from live API records, especially prompts about expedite queues, allocation waves, BOM kit replenishment, purchase orders, supplier incidents, supplier quality holds, inventory coverage, shipping quotes, or operational control decisions. Trigger this whenever the user provides a Northwind ERP prompt with an answer_template.json or asks for a structured dispatch, replenishment, allocation, or supplier-quality decision file.
---

# Northwind ERP Structured Decisions

Use this workflow to solve Northwind Components ERP tasks that combine staged task inputs with live public API data and require JSON matching a provided answer template.

## Ground Rules

Read the task prompt, every visible input payload, and the answer template before querying the API. The template is the contract: preserve required keys, enum values, sort orders, field names, number precision, and JSON-only output.

Use only the public ERP API and the task's visible input files. Do not inspect environment source directories, hidden outputs, answer files, eval reports, or unrelated attempts. During test solving, do not use any training or judging endpoint.

Build small local indexes after fetching API data:

- Products by `sku`
- Customers by `customer_id`
- Suppliers by `supplier_id`
- Inventory by `warehouse_id|sku`
- Orders by `order_id` and wave
- Purchase orders by `supplier_id`, `sku`, `warehouse_id`, and status
- Incidents by `supplier_id` and date window
- BOMs by `bom_id`

## Common Calculations

Use `raw_available = max(0, on_hand - reserved - quarantined)`.

When the task mentions release, allocation, shortage, protected stock, operating buffer, safety stock, or feasible transfers, use protected availability:

`protected_available = max(0, raw_available - product.safety_stock)`

Treat safety stock as unavailable for automatic release or transfer. This matters for dispatch, allocation, and kit replenishment tasks. If a template separately asks for low-stock classification, classify a line as low stock only after it can satisfy demand without becoming a protected-stock shortage.

Round money to two decimals and percentages to the precision stated in the template. Recompute summaries from the final rows rather than hand-editing them.

Always sort lists exactly as requested by the template. If no special order is given, sort IDs and SKUs ascending for stable output.

## Customer And Product Stops

Map customer status before making automatic release decisions:

- `account_status: blocked` usually becomes an account-blocked hold.
- `account_status: review_required` usually becomes account review/manual review.
- `risk_flag: fraud_watch` or credit risk should stop automatic release when the template has a compatible enum.
- Active accounts with no risk are normal unless inventory or product status blocks them.

Inactive products stop automatic line or order release. Product-master stops are not the same as customer/account blocked orders; include them in product exception lists, but do not count them as account-blocked orders unless the template says to combine them.

For order-level dispatch decisions, use this precedence unless the prompt gives a different policy:

1. Hard account or customer-risk hold.
2. Inactive product or product-master issue.
3. Protected-stock shortage.
4. Account review.
5. Low-stock delay.
6. Ready to ship.

## Shipping Quotes

For order shipping quotes, calculate total order weight from live product weights:

`sum(line.quantity * product.weight_lb)`

Call the shipping quote endpoint with the order warehouse, destination ZIP, calculated weight, and the order's requested speed unless the prompt overrides the speed. The API may return `total_cost`; map it to the template's `total_cost_usd` field and round to two decimals.

## Expedite Queue Pattern

For each listed order:

1. Fetch the live order, customer, product, inventory, and quote data.
2. Classify each line using protected availability.
3. Build sorted `shortage_skus`, `inactive_skus`, and `low_stock_skus`.
4. Set the order inventory status from the strongest inventory exception.
5. Set the customer exception from live account/risk records.
6. Choose the final decision and next action by applying the customer/product/inventory precedence.
7. Reconcile summary counts and ID lists from the final records.

Do not assume the full wave is in scope if the memo lists specific order IDs. Use the memo's order list and sort the output records by `order_id`.

## Kit Replenishment Pattern

For BOM build planning:

1. Use the build quantities and build dates from the memo, not stale default BOM target dates.
2. Fetch live BOMs and aggregate component demand by SKU across all requested builds.
3. Use protected availability at the target warehouse for `target_effective_available`.
4. Treat same-warehouse purchase orders as timely when status is `open` or `confirmed` and `eta <= needed_by`. Do not discard a live open/confirmed PO only because its ETA is before the memo issue date.
5. Use product overstock thresholds: if target protected availability is already at or above the overstock threshold, exclude the component as target overstock.
6. Apply same-warehouse timely POs before new replenishment.
7. Use inter-warehouse transfers only from source protected availability; never consume a source warehouse's safety stock.
8. Create purchase requisitions only for the remaining uncovered quantity, using the product supplier, unit cost, and rounded extended cost.

Keep component rows sorted by SKU. Keep transfer requests sorted by the template rule, commonly SKU, quantity descending, then source warehouse. Keep purchase requisitions sorted by SKU.

For excluded components, include stocked, timely-PO-covered, and target-overstock rows only when the template has an excluded component section. Use supporting PO IDs only when the exclusion is based on PO coverage.

## Allocation Wave Pattern

For line-level allocation:

1. Use protected availability for `requested_effective_available`.
2. Stop account-blocked, account-review, or fraud-risk orders as `manual_review` before automatic stock decisions.
3. Stop inactive product lines as `manual_review` with the product reason.
4. If the requested warehouse can cover the full line from protected stock, action is `ship`.
5. If it cannot, choose `transfer` only when one source warehouse can cover the uncovered quantity from protected stock. Leave usable requested-warehouse quantity as `ship_quantity`, and transfer only the remainder.
6. If no source can cover the uncovered quantity, use `backorder` and report the uncovered quantity.

For manual-review lines, keep ship, transfer, and backorder quantities at zero unless the template explicitly asks for theoretical partial quantities. Account/customer-risk stopped orders belong in `blocked_orders`; product-only manual reviews do not.

Build order rollups from final line actions. Prefer the strongest operational blocker: manual review, then backorder, then transfer, then ready to ship. Use `mixed_actions` only when the template or examples clearly call for preserving mixed line states.

## Supplier Incident Scorecards

Filter incidents by `open_date` inclusively between the request start and end dates. Group only suppliers with at least one filtered incident unless the template says to include zero-incident suppliers.

For each supplier:

- Count total incidents, RMA incidents, work-order incidents, open incidents, and severe incidents.
- Treat `high` and `critical` as severe when the request names those severities.
- Calculate incident percentages against the full filtered incident population.
- Sum resolution cost and round to two decimals.
- Calculate duration as calendar-day difference from `open_date` to `close_date` for closed incidents, or to the analysis date for open incidents. Do not add an extra inclusive day unless the prompt says so.
- Apply recommendation policies in the exact precedence order given by the request.

For top escalation lists, filter to the requested recommendation code and sort by the policy's tie-breakers. Choose highest-cost and highest-share suppliers from the final scorecard rows after rounding rules are applied.

## Supplier Quality Control Pattern

For procurement quality-control tasks:

1. Filter incidents by the memo's analysis window using inclusive `open_date`.
2. For each target supplier, report quality status, recent counts, affected SKUs, and up to five sorted sample incident IDs.
3. Fetch open or confirmed purchase orders for the supplier when the template asks for held POs.
4. Use memo policy first. If it gives only broad guidance, use a conservative default:
   - `quality_hold` plus recent incidents means `freeze_new_replenishment`.
   - `watch` suppliers with recent severe, open, or repeated incidents generally need `buyer_review_required`.
   - Use `monitor_only` only for suppliers with low recent risk and acceptable quality status.
5. Hold PO IDs only for suppliers whose decision actually blocks or pauses replenishment under the chosen policy.

Reconcile `held_po_ids`, release suppliers, decision counts, held PO count, and total incident count directly from supplier rows.

## Final Validation

Before returning the answer:

- Compare every top-level key against the answer template.
- Check every enum value exactly.
- Check every list sort order.
- Recalculate all counts, quantities, costs, percentages, and ID lists from the final rows.
- Verify no narrative text surrounds the JSON.
- Verify no training-only or judge-only workflow appears in the solution.
