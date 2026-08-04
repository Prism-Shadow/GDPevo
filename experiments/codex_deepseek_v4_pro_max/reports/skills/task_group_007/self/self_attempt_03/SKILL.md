## When to use

Use this skill when a task involves the Northwind Components ERP API. The skill applies to any of the following business processes:

- **Expedite / dispatch control** — reviewing a queue of orders and deciding whether to release, hold, backorder, or escalate each one based on live inventory, customer account status, product master data, and shipping quotes.
- **Replenishment / production planning** — building a component-coverage plan for one or more kit BOMs at a target warehouse, identifying transfer requests and purchase requisitions where stock is insufficient.
- **Supplier quality scorecard** — aggregating supplier incident data over a date window, computing per-supplier metrics, and assigning controlled recommendation codes from a precedence-ordered policy.
- **Allocation / transfer desk** — processing a mixed-warehouse order wave line by line, deciding ship / transfer / backorder / manual-review actions, and generating inter-warehouse transfer requests.
- **Procurement quality control** — reviewing suppliers on a quality-hold watchlist, inspecting recent incidents, and issuing replenishment-control decisions (freeze, buyer review, or monitor).

## How to use

### 1. Locate the inputs

Every task supplies a text prompt and a `payloads/` directory that contains:

- A task-specific memo or request file (JSON or Markdown) with the task parameters — target order IDs, wave IDs, BOM IDs, date windows, supplier lists, and any embedded policy rules.
- An `answer_template.json` that defines the exact output shape, required keys, field types, allowed enum values, list sort orders, numeric precision, and top-level structure.

Read both files completely before making any API calls.

### 2. Obtain the API base URL

The runner provides the base URL through the placeholder `<TASK_ENV_BASE_URL>`. Never hardcode a URL. Resolve the placeholder before issuing any request.

### 3. Query the ERP API

All data comes from the live API. Do not use cached snapshots, local files, or direct environment-file inspection.

**Available read-only endpoints:**

- `GET /manifest` — Full API resource listing
- `GET /products` — All products
- `GET /products/{product_id}` — Single product
- `GET /inventory` — All inventory records
- `GET /inventory/{sku}` — Inventory for one SKU
- `GET /warehouses` — All warehouses
- `GET /warehouses/{warehouse_id}` — Single warehouse
- `GET /orders` — All orders
- `GET /orders/{order_id}` — Single order
- `GET /customers` — All customers
- `GET /customers/{customer_id}` — Single customer
- `GET /suppliers` — All suppliers
- `GET /suppliers/{supplier_id}` — Single supplier
- `GET /purchase_orders` — All purchase orders
- `GET /purchase_orders/{po_id}` — Single purchase order
- `GET /boms` — All bills of materials
- `GET /boms/{bom_id}` — Single BOM
- `GET /incidents` — All quality incidents
- `GET /incidents/{incident_id}` — Single incident
- `GET /shipping/quote` — Shipping quotes

No authentication is required.

**Forbidden endpoints:** Never call `/health`, any reset/reseed endpoint, or any judge endpoint.

### 4. Apply the business logic

Business rules come from two sources in priority order:

1. **Explicit policy in the memo/request file.** Some tasks embed recommendation policies, precedence rules, decision thresholds, or severity classifications directly in the request payload. Apply these rules literally.
2. **Field constraints in the answer template.** Enum values, required keys, and field relationships defined in the template are binding.

When the memo or template is silent on a point, use the following defaults:

- **Inventory status classification:** Compare per-line required quantity against effective available stock (raw stock minus reservations, quarantines, and normal operating buffer). Classify as `ready`, `low_stock`, `shortage`, `inactive_sku`, or `inactive_and_shortage` depending on availability and product active-status.
- **Customer exception classification:** Inspect the customer record for account status flags (`active`, `blocked`, `review_required`, `fraud_watch`, `credit_watch`). Map to the template's exception enum.
- **Fulfillment decisions:** Derive from the combination of inventory status and customer exception using the precedence: account-blocked/fraud → `reject_hold` or `manual_review`; inactive product → `manual_review`; shortage → `backorder`; low_stock or ready with clean account → `ship_now` or `delayed_release`.
- **Transfer logic:** When a requested warehouse cannot satisfy a line, check other warehouses for usable stock. Prefer the warehouse with sufficient available quantity. If multiple warehouses qualify, prefer the closest or first by sorted warehouse_id.
- **Purchase requisition logic:** When no warehouse can cover a component need, create a purchase requisition using the component's current supplier, unit cost, and the required quantity rounded up to the nearest integer.

### 5. Produce the JSON answer

Return a single JSON object that conforms to `answer_template.json`. Follow these rules without exception:

**Currency:**
- All monetary values in USD.
- Round to exactly 2 decimal places.
- Extended costs = unit cost × quantity, also rounded to 2 decimals.

**Sorting:**
- Sort every list in the order specified by the template.
- Default sort: ascending by the primary identifier (order_id, supplier_id, sku, line_id, bom_id, or similar).
- For tie-breakers, use the secondary and tertiary keys declared in the template or memo.

**Precision:**
- Percentages: 1 decimal place (unless the template says otherwise).
- Durations (days): 2 decimal places.
- Counts: integers.

**Enums:**
- Use exactly the string values listed in the template. No abbreviations, no alternative casing.
- When a field allows `null`, use JSON `null` (not the string `"null"` or an empty string).

**Dates:**
- All dates in `YYYY-MM-DD` format.

**Output:**
- JSON only. No markdown fences, no preamble, no trailing explanation.

### 6. Common workflow by domain

**Expedite queue:**
1. Read the queue memo for the wave_id and order_ids.
2. Fetch each order, its customer, and every product on the order.
3. Fetch inventory for every SKU on every order.
4. For each order, classify inventory_status, customer_exception, and derive final_decision and next_action.
5. Populate shortage_skus, inactive_skus, and low_stock_skus lists per order.
6. Get a shipping quote for each order.
7. Compute summary counts, lists, and total shipping cost.

**Replenishment planning:**
1. Read the production memo for BOM targets (bom_id, build_quantity, build_date, warehouse).
2. Fetch each BOM to get component SKUs and per-kit quantities.
3. Multiply by build_quantity to get total required per component.
4. Fetch inventory at the target warehouse and all other warehouses.
5. Fetch open/confirmed POs for each component at the target warehouse.
6. For each component: calculate gap (required minus effective_available), cover with timely POs and transfers, create purchase requisitions for remaining gaps.
7. Flag excluded components (overstock, PO-covered, already stocked).
8. Compute summary totals.

**Supplier scorecard:**
1. Read the scorecard request for date window, severity values, percentage rule, and recommendation policy.
2. Fetch all incidents. Filter to those whose open_date falls in the analysis window.
3. Fetch all suppliers referenced by the filtered incidents.
4. Group incidents by supplier. Compute: count, percentage of total, resolution cost, average duration, RMA count, work-order count, open count, severe count.
5. Apply the recommendation policy in declared precedence order. The first matching condition wins.
6. Populate top_escalation_suppliers, highest_cost_supplier_id, and highest_share_supplier_id.

**Allocation desk:**
1. Read the allocation memo for wave_id.
2. Fetch all orders in the wave. For each order, fetch the customer and every line's product.
3. Fetch inventory for every SKU at every warehouse.
4. For each line: determine effective available at the requested warehouse. If sufficient, ship. If insufficient, check other warehouses for transfer. If no warehouse can cover, backorder. If account/product blocked, manual_review.
5. Generate transfer_requests for lines where another warehouse covers the shortage.
6. Populate blocked_orders, order_rollup, and summary counts.

**Procurement quality control:**
1. Read the quality hold review memo for analysis window and target supplier_ids.
2. Fetch incidents in the analysis window for each target supplier.
3. Fetch each supplier's current quality_status.
4. Fetch open/confirmed POs for each target supplier.
5. For each supplier: count recent incidents, RMAs, severe/critical, open incidents; list affected SKUs and sample incident IDs (max 5).
6. Apply the decision policy: freeze, buyer review, or monitor.
7. Collect held_po_ids (all open/confirmed POs of suppliers not on monitor_only).
8. Compute summary counts.

## Guardrails

- Do not inspect environment files on disk. Use only the public API endpoints listed above.
- Do not fabricate data. If the API does not return a value needed by the template, use `null` for nullable fields and `0` or `""` for required scalar fields, then flag the record for manual review if the business rules demand it.
- Do not skip records. Every order, line, component, supplier, or incident named in the memo must appear in the output.
- When the memo and template appear to conflict, the template's field constraints take precedence for output shape; the memo's business parameters take precedence for scoping and policy.
- Always resolve `<TASK_ENV_BASE_URL>` from the environment before issuing API calls. If the variable is not set, stop and report the missing configuration.
