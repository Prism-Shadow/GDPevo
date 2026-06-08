---
name: reflection-skill-attempt-01
description: Use for PanofyBench Northwind Components ERP tasks that require solving dispatch, replenishment, allocation, supplier incident scorecard, or procurement quality-control questions from task prompts plus the shared local ERP API. Provides transferable SOPs for API usage, signed effective inventory, customer/product precedence, BOM coverage, incident metrics, and supplier hold decisions without using train answer lookup tables.
---

# Northwind ERP Reflection Skill

## Scope And Integrity

Use this skill when a Northwind Components task asks for a structured JSON answer from the shared ERP API.

- Read only the task prompt, visible input payloads, and answer template unless the user explicitly authorizes train standards for skill reflection.
- Do not inspect task group `env/`, evaluator code, notes, test tasks, or hidden/standard outputs while solving a task.
- Use the API base URL specified by the user or prompt. In this evaluation condition, prefer `http://127.0.0.1:8100` when the user specifies it, even if prompt text mentions another default.
- Use `curl --noproxy '*'` for localhost API calls if proxy or Python socket restrictions appear.
- Keep all calculations reproducible: cache public API responses under `scratch/` if useful, then generate final JSON strictly from prompt/template/API data.

## API Workflow

Start by discovering live endpoints with `/` and health/manifest with `/health`. Common endpoints:

- `/orders?wave=&required_date=&customer_id=` and `/orders/<order_id>`
- `/customers`, `/products`, `/inventory?warehouse_id=&sku=`, `/warehouses`
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
- `/boms`, `/boms/<bom_id>`
- `/purchase_orders?supplier_id=&sku=&status=`
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `/suppliers`

Prefer targeted endpoint calls from IDs in the memo. If an endpoint returns a full wave or collection, filter back to the exact IDs in the prompt payload.

## Shared Definitions

Use these inventory definitions consistently:

```text
free_available = on_hand - reserved - quarantined
effective_available = free_available - product.safety_stock
usable_quantity = max(0, effective_available)
```

Important details:

- `effective_available` is signed. Preserve negative values in output fields named like `requested_effective_available` or `target_effective_available`.
- For actual ship, transfer, or backorder quantities, do not use negative stock. Use `usable_quantity`.
- Product `safety_stock` is protected operating buffer for allocation and planning decisions.
- Sort IDs and SKUs exactly as templates require. Round currency to two decimals, percentages to the requested precision, and durations to the requested precision.

## Dispatch And Expedite Decisions

For order-level dispatch queues:

- Compute total order weight as `sum(line.quantity * product.weight_lb)` and call `/shipping/quote` with the order warehouse, destination ZIP, requested speed, and weight. Return only the quote fields requested by the template.
- Build SKU exception lists per order:
  - `inactive_skus`: product `active` is false.
  - `shortage_skus`: `effective_available < line.quantity`.
  - `low_stock_skus`: the line can be covered from effective stock, but the effective stock is thin, commonly `effective_available >= line.quantity` and `effective_available < product.safety_stock`.
- Inventory status precedence: inactive plus shortage -> `inactive_and_shortage`; inactive only -> `inactive_sku`; any shortage -> `shortage`; any low stock -> `low_stock`; otherwise `ready`.
- Customer exception precedence: blocked account -> `account_blocked`; fraud risk -> `fraud_watch`; credit risk -> `credit_watch`; review-required account -> `review_required`; otherwise `none`.
- Final decision precedence:
  - Account blocked, fraud watch, or credit watch -> `reject_hold` / `hold_credit_or_fraud`.
  - Review-required account -> `manual_review` / `send_account_review`, even if product or inventory issues also exist.
  - Inactive product with no account exception -> `manual_review` / `escalate_product_master`.
  - Shortage with no customer/product hold -> `backorder` / `create_backorder`.
  - Low stock only -> `delayed_release` / `delay_and_monitor`.
  - Otherwise -> `ship_now` / `release_to_pick`.

## BOM Replenishment Planning

For kit or BOM build requests:

- Use memo build quantities and build dates, not stale BOM target dates, when the prompt provides requested targets.
- Aggregate component demand by SKU across all requested BOMs.
- `target_effective_available` is signed `effective_available` at the planning warehouse.
- Same-warehouse POs are timely only when status is `open` or `confirmed` and `eta <= needed date`. `timely_po_qty` is the full sum of eligible PO quantities, not just the uncovered gap.
- A component is `timely_po_covered` when timely same-warehouse PO quantity covers the positive gap `total_required - target_effective_available`. Summary `timely_po_covered_units` is the covered gap, not the PO total.
- Use `overstock_excluded` / `target_overstock` when planning-site effective stock exceeds the product `overstock_threshold`.
- Transfer from other warehouses only from positive `effective_available`; do not use protected safety stock. Multiple transfer requests are allowed unless the template says otherwise.
- Sort transfer sources per template, usually by SKU, quantity descending, then source warehouse.
- Purchase only the residual gap after target effective stock, timely POs, and feasible transfers.
- For components used in multiple builds, allocate coverage chronologically by build date. Transfers can be needed by the earliest build they support; purchase requisitions should use the build date where the residual shortage remains.
- Purchase supplier and unit cost come from product master. Extended cost is `quantity * unit_cost`, rounded to two decimals.

## Allocation Desk Decisions

For mixed-warehouse allocation waves:

- Always compute and report signed `requested_effective_available`.
- Order-level account/risk controls apply to every line on the order:
  - blocked account -> `manual_review`, reason `account_blocked`
  - review-required account -> `manual_review`, reason `account_review_required`
  - fraud watch -> `manual_review`, reason `fraud_watch`
- Order-level account/risk reasons supersede inactive product reasons.
- If there is no order-level hold, inactive products are line-level `manual_review` with reason `inactive_product`.
- For releasable product lines:
  - If `effective_available >= requested quantity`, action `ship`, `ship_quantity = requested quantity`.
  - If not, set `ship_quantity = usable_quantity` and compute the remaining quantity.
  - Use `transfer` only if one other warehouse can cover the remaining quantity from positive effective stock. Choose the source with the largest effective stock, tie-breaking by warehouse ID.
  - If no single source can clear the remainder, use `backorder`; backorder quantity is the remaining quantity after any usable requested-warehouse stock.
- Roll up orders as:
  - all ship -> `ready_to_ship`
  - all manual review -> `manual_review`
  - any manual review mixed with another action -> `mixed_actions`
  - ship plus backorder, without manual/transfer -> `has_backorder`
  - ship plus transfer, without manual/backorder -> `needs_transfer`
  - other mixtures -> `mixed_actions`
- `blocked_orders` contains orders stopped at account or customer-risk level, not orders with only inactive-product line reviews.

## Supplier Incident Scorecards

For supplier incident scorecards:

- Filter incidents by the date field and inclusive window in the request, normally `open_date`.
- Duration is calendar day difference: closed incidents use `close_date - open_date`; open incidents use `analysis_date - open_date`. Do not add one day.
- Percentages use the full filtered incident population as denominator.
- Severe counts use exactly the severity values named by the prompt.
- Apply recommendation policies in stated precedence order. If a supplier satisfies a higher-precedence recommendation, do not downgrade it because another lower condition also matches.
- Common policy logic:
  - quality hold with enough incidents, any critical RMA, or high RMA cost/count -> supplier escalation
  - work-order-heavy suppliers -> process review
  - watch/quality-hold status, high count, high cost, or multiple severe incidents -> watchlist
  - otherwise monitor
- Top escalation lists use only escalation-code suppliers and the requested sort order.

## Procurement Quality Holds

For supplier replenishment-control reviews:

- Filter recent incidents by the memo analysis window using incident `open_date`.
- For each target supplier, count all recent incidents, RMAs, open incidents, and high/critical incidents; sort `affected_skus` and cap `sample_incident_ids` at five sorted IDs when requested.
- Decision pattern in this task family:
  - `quality_hold` suppliers -> `freeze_new_replenishment`.
  - `watch` suppliers with at least two high/critical recent incidents or similar concentrated risk -> `buyer_review_required`.
  - A watch supplier with only isolated severe risk and otherwise monitorable recent history can remain `monitor_only`.
- For non-monitor decisions, `held_po_ids` is a controlled list of sorted `open` or `confirmed` supplier PO IDs. If the template does not give a larger cap, use the first five per supplier. Do not filter held POs only to affected SKUs unless the prompt explicitly says to.
- `release_supplier_ids` contains only `monitor_only` suppliers.
- Global `held_po_ids` is the sorted unique union of supplier-level held IDs.

## Final JSON Checklist

Before finalizing:

- Match the answer template keys exactly; do not add narrative text.
- Recheck sort orders for every list.
- Keep negative effective availability where the field reports availability, but never emit negative ship, transfer, purchase, or backorder quantities.
- Recompute summary counts and totals from the record lists, not from memory.
- Re-run JSON parsing on the final answer file or payload.
