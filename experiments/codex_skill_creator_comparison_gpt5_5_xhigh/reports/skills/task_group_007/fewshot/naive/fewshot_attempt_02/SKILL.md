---
name: northwind-erp-control-json
description: Solve Northwind Components ERP control tasks that require strict JSON answers from local memo/template payloads and the shared Northwind ERP API. Use for expedite dispatch, mixed-warehouse allocation, kit replenishment, supplier incident scorecards, and procurement quality-hold reviews where Codex must fetch live ERP records, apply memo/template rules, compute inventory or incident metrics, and return only schema-conforming JSON.
---

# Northwind ERP Control JSON

Use this skill when a Northwind Components task provides local payloads plus a shared ERP API base URL. Treat the prompt, memo files, and `answer_template.json` as the contract. Fetch live data from the public API; do not inspect environment files, judge APIs, source code, cached answer files, or hidden data.

## Core Workflow

1. Read the prompt, every local payload, and especially `answer_template.json`.
2. Identify the task family from the memo/template keys:
   - Expedite dispatch: order list plus per-order inventory/customer/shipping decisions.
   - Mixed allocation: order wave, line actions, transfer requests, blocked orders, rollup.
   - Kit replenishment: BOM targets, component coverage, transfers, requisitions, exclusions.
   - Supplier scorecard: incidents filtered by date and supplier-level metrics.
   - Procurement quality review: listed suppliers, recent incidents, held POs, release list.
3. Fetch all needed live records from the API base URL supplied in the task. Common endpoints are `/orders`, `/orders/<id>`, `/products`, `/products/<sku>`, `/customers/<id>`, `/inventory?warehouse_id=&sku=`, `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`, `/purchase_orders?supplier_id=&sku=&status=`, `/suppliers`, `/incidents?start=&end=&supplier_id=`, and `/boms/<id>`.
4. Compute in plain data structures first, then serialize one JSON object matching the template. Include required keys even when counts are zero or lists are empty.
5. Validate sorting, enum values, numeric precision, and summary totals before final output. Return no narrative outside JSON.

## Shared Calculations

Effective stock is:

```text
on_hand - reserved - quarantined - product.safety_stock
```

Use effective stock everywhere a task says protected, reserved, quarantined, or buffer stock must not be consumed. Missing inventory for a warehouse/SKU is zero on-hand with the same deductions effectively yielding no usable stock.

For currency, compute with exact arithmetic when practical and round final currency fields to two decimals. Percentages and average durations use the precision stated in the template or memo. Sort IDs lexicographically unless the template says otherwise.

Customer hold precedence:

1. `account_status == "blocked"` is an account block.
2. `account_status == "review_required"` is account review.
3. `risk_flag == "fraud_watch"` is fraud watch.
4. `risk_flag == "credit_watch"` is credit watch when the target enum supports it; otherwise map to the closest account hold enum available in that task.
5. Otherwise there is no customer exception.

Product holds use `product.active == false`.

## Expedite Dispatch

For each memo order ID, fetch the order, customer, every product, warehouse inventory for each line, and a shipping quote.

Inventory lists:

- `shortage_skus`: active line SKUs where effective stock at the order warehouse is less than requested quantity.
- `inactive_skus`: inactive line SKUs.
- `low_stock_skus`: active line SKUs that can cover the requested quantity but whose post-line effective stock is below the product safety stock.

Inventory status:

- `inactive_and_shortage`: at least one inactive SKU and at least one shortage SKU.
- `inactive_sku`: inactive SKU and no shortage.
- `shortage`: shortage and no inactive SKU.
- `low_stock`: no shortage/inactive and at least one low-stock SKU.
- `ready`: none of the above.

Final decision precedence:

- Account blocked, fraud watch, or credit watch: reject or hold using the template's customer-hold decision/action enums.
- Account review: manual review using the account-review action enum.
- Inactive product with no customer hold: manual review or product-master escalation per template.
- Shortage with no customer/product hold: backorder.
- Low stock with no higher issue: delayed release or monitor action when the template offers it.
- Ready with no exception: ship/release now.

Compute shipping quote by summing `quantity * product.weight_lb` for all order lines and calling `/shipping/quote` with the order warehouse, destination ZIP, total weight, and requested shipping speed. Include quote fields exactly as returned, with cost rounded to two decimals if needed.

## Mixed-Warehouse Allocation

Fetch all orders in the wave, customer records, products, and inventory for every line SKU at every warehouse.

For each line:

1. If the customer has an account/risk hold, set `action` to `manual_review`, all quantities to zero, and `primary_reason` to the matching account/risk enum.
2. Else if the product is inactive, set `manual_review`, zero quantities, and `primary_reason` to the product inactive enum.
3. Else compute requested-warehouse effective stock.
4. If requested effective stock covers the line quantity, `ship` the full quantity.
5. Else set `ship_quantity` to the positive requested effective stock, capped at the line quantity. The uncovered quantity is `line quantity - ship_quantity`.
6. Choose one alternate warehouse whose effective stock covers the uncovered quantity. Prefer the largest effective balance, then warehouse ID ascending. If one exists, create a `transfer` line and a matching transfer request for the uncovered quantity.
7. If no alternate warehouse can cover the uncovered quantity, create a `backorder` line with the full uncovered quantity.

For transfer lines, negative requested effective stock never increases the transfer quantity beyond the original line quantity. `blocked_orders` contains orders stopped by account or customer-risk holds, not product-only inactive lines. Roll up each order from its line actions: all shippable means ready, any account/product manual review means manual review unless mixed with non-review actions and the template has `mixed_actions`, any transfer means needs transfer, any backorder means has backorder, and otherwise use the template's closest allowed outcome.

## Kit Replenishment

For each target BOM, fetch the BOM, component products, target warehouse inventory, other-warehouse inventory, same-warehouse POs, and supplier data from each product.

For each component SKU:

- `total_required` is the sum of all target build quantities multiplied by that SKU's BOM quantity per kit.
- `target_effective_available` is effective stock at the target warehouse.
- The initial gap is `max(0, total_required - target_effective_available)`.
- Eligible timely POs are open or confirmed, same warehouse, same SKU, and ETA no later than the component's needed-by build date. `timely_po_qty` is the full quantity of eligible POs; coverage summaries count only the gap they cover.
- If target effective stock exceeds the product `overstock_threshold`, exclude as target overstock.
- If there is no gap, exclude as stocked/no gap.
- If eligible timely POs cover the whole gap, exclude as timely-PO covered.
- Otherwise, after subtracting timely PO coverage, request transfers from other warehouses using their positive effective stock. Allocate from largest effective balance first, then warehouse ID ascending, until the gap is cleared or sources are exhausted.
- Create purchase requisitions for the remaining gap using the product supplier, target warehouse, needed-by date, product unit cost, and rounded extended cost.

Set component final actions from the resulting plan: no action stocked, transfer only, purchase required, timely PO covered, or overstock excluded. Sort transfer requests by the template's keys; if no explicit key is given, use SKU, quantity descending, and source warehouse.

## Supplier Incident Scorecard

Fetch incidents with the date filter named in the memo, normally `open_date` inclusive between start and end, and fetch suppliers for names and quality status.

For each supplier with filtered incidents:

- Count incidents, RMA incidents, work-order incidents, open incidents, and severe incidents where severity is in the memo's severe list.
- Sum `resolution_cost`.
- Duration is calendar-day difference from `open_date` to `close_date` for closed incidents and from `open_date` to the analysis date for open incidents.
- `incident_percentage` is supplier incidents divided by total filtered incidents, rounded to the memo/template precision.
- Apply recommendation policy in the memo's precedence order. Stop at the first matching recommendation.

Build top escalation suppliers from rows whose recommendation is the escalation code and sort by the requested tie-breakers. Highest-cost and highest-share supplier IDs come from the computed rows, using template tie-breakers if provided and supplier ID ascending otherwise.

## Procurement Quality Review

For each target supplier, fetch the supplier, incidents in the analysis window, and purchase orders for that supplier.

Compute recent incident counts, RMA counts, severe/high-or-critical counts, open counts, affected SKUs, and up to five sample incident IDs sorted ascending. Use the memo's analysis window for incident filtering.

Decision pattern:

- `freeze_new_replenishment`: supplier is on quality hold, or the memo defines an equivalent freeze threshold and it is met.
- `buyer_review_required`: supplier has elevated but not freeze-level risk, such as watch status with multiple severe/high-or-critical recent incidents, or any stricter memo-defined review condition.
- `monitor_only`: none of the above.

For freeze or buyer-review suppliers, hold open or confirmed purchase orders for that supplier, sorted by PO ID. If the template gives no other limit, keep the first five held PO IDs per supplier. Monitor-only suppliers have no held POs and appear in the release list. Summaries count reviewed suppliers, decisions, held POs, and recent incidents from the computed rows.

## Final JSON Checks

- Match top-level key names and required nested keys from `answer_template.json`.
- Use allowed enum strings exactly.
- Sort records exactly as specified.
- Emit `null`, empty lists, and zero counts where required; do not omit them.
- Recalculate summary counts from final detail rows after sorting.
- Ensure JSON parses before returning it.
