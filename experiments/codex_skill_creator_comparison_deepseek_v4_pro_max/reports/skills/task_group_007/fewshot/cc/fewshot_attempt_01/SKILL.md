---
name: northwind-erp-desk
description: >
  Solve Northwind Components desk-operation tasks that arrive with a memo (JSON or markdown),
  a JSON answer template, and a shared REST ERP API at a runner-supplied base URL. Use this
  skill whenever the user mentions dispatching orders, replenishment planning, supplier
  scorecards or quality reviews, allocation transfers, procurement holds, or any Northwind
  desk decision that needs live ERP record lookups and structured JSON output. Also trigger
  when the task includes a file named answer_template.json alongside an order-memo or
  request payload, or when the prompt references an ERP API base URL with endpoints like
  /orders, /inventory, /products, /suppliers, /incidents, or /boms.
---

# Northwind Erp Desk Operations

Use this skill for Northwind Components supply-chain desk tasks. These tasks
follow a single repeatable pipeline: read the desk memo and the answer template,
inspect the live ERP API, cross-reference records, apply business rules, and
output JSON that matches the template exactly.

## Quick-Start Pipeline

Work through these six steps in order. Do not skip the manifest fetch.

### 1. Gather All Local Inputs

Read every file under the task's payload directory. Three kinds of file are
typical:

- **Desk memo** (`.json` or `.md`): names the target records — order IDs, BOM
  IDs, supplier IDs, a wave ID, or a date window. It may also carry planner notes,
  operator remarks, or policy hints that inform the final decision.
- **Answer template** (`answer_template.json`): declares the exact JSON shape
  the solver must produce. Every required key, enum value, sort order, and
  precision rule is authoritative. If a field is listed as required, it must
  appear; if an enum is specified, use only those values.
- **Other references** (rare): an `api_base_url` field inside the memo or
  an explicit `<TASK_ENV_BASE_URL>` placeholder in the prompt tells you the
  API root.

Before any API call, read the answer template thoroughly. It tells you what
to classify, what to count, what to sort, and how to name every key.

### 2. Fetch the API Manifest

```
GET {base_url}/manifest
```

The manifest is a directory of every available endpoint and the schema of the
records each one returns. Use it to confirm field names, resource relationships,
and endpoint paths — never guess a field name from memory.

### 3. Pull the Live ERP Records You Need

Which endpoints you hit depends on the task, but the mapping is predictable:

| If the memo mentions … | Fetch these endpoints |
|---|---|
| Order IDs or a wave ID | `/orders/{order_id}` for each order |
| Products or SKUs | `/products` and `/products/{product_id}` |
| Inventory or warehouse stock | `/inventory` and `/inventory/{sku}` |
| Customers or account status | `/customers/{customer_id}` |
| Warehouses or site names | `/warehouses` and `/warehouses/{warehouse_id}` |
| BOM IDs or kit builds | `/boms/{bom_id}` |
| Suppliers | `/suppliers` and `/suppliers/{supplier_id}` |
| Purchase orders | `/purchase_orders` and `/purchase_orders/{po_id}` |
| Incidents or quality events | `/incidents` and `/incidents/{incident_id}` |
| Shipping or parcel quotes | `/shipping/quote` (check query params) |

Fetch in parallel when the calls are independent — orders, products, and
warehouses can all be pulled at once. Use the full list endpoints (e.g.
`/products`, `/suppliers`, `/warehouses`) when you need the complete catalog.

### 4. Cross-Reference and Classify

Join records on their natural keys. The ERP data model uses these links:

- **Order → Customer**: `order.customer_id` → `customers/{customer_id}`
- **Order → Line items**: each line has `sku`, `quantity`, and may reference a
  `warehouse_id`
- **SKU → Product**: `products/{sku}` gives `status` (active/inactive), `unit_cost`,
  `supplier_id`
- **SKU → Inventory**: `/inventory/{sku}` returns per-warehouse stock records with
  `warehouse_id`, `physical_quantity`, `reserved_quantity`, `quarantined_quantity`,
  and `buffer_quantity`
- **BOM → Components**: `/boms/{bom_id}` lists components with `sku`, `quantity_per`
- **Supplier → Incidents**: `/incidents` records carry `supplier_id`
- **Supplier → POs**: `/purchase_orders` records carry `supplier_id`, `sku`, and `status`
- **Incident → Supplier**: each incident has `supplier_id`, `severity`, `type`,
  `status` (open/closed), `open_date`, `close_date`, `resolution_cost`

### 5. Apply Desk-Specific Business Rules

The logic differs by desk, but always follows a deterministic path. Never
invent rule interpretations — derive them from the memo's policy fields and the
answer template's allowed enum values.

#### Dispatch / Expedite Desk

For each order in the wave:

1. **Inventory status**: check every line SKU's effective available at the
   requested warehouse. Effective available = `physical_quantity` minus
   (`reserved_quantity` + `quarantined_quantity` + `buffer_quantity`). Compare
   against the ordered quantity.
   - `ready`: all lines have enough effective stock
   - `shortage`: at least one line's effective stock is below the ordered qty
   - `low_stock`: effective stock covers the line but the margin is thin (use
     the answer template's enum — if `low_stock` is listed, apply a reasonable
     threshold such as effective remaining < 10% of physical)
   - `inactive_sku`: any line SKU has product.status != "active"
   - `inactive_and_shortage`: both inactive and shortage conditions present

2. **Customer exception**: look up the customer.
   - `none`: customer status is "active" and no account flags
   - `review_required`: any flag or non-standard account state
   - `account_blocked`: customer status contains "blocked" or "suspended"
   - `fraud_watch`: explicit fraud flag
   - `credit_watch`: credit-hold flag

3. **Final decision**: combine inventory status and customer exception using
   the precedence implied by the answer template's `next_action` enum:
   - account_blocked → reject_hold (next: hold_credit_or_fraud)
   - Any customer exception + any inventory issue → manual_review (next: send_account_review)
   - Shortage only, no customer exception → backorder (next: create_backorder)
   - Ready, no customer exception → ship_now (next: release_to_pick)
   - inactive_sku or fraud_watch alone → manual_review (next: escalate_product_master or send_account_review)

4. **SKU lists**: populate `shortage_skus` (effective < ordered), `inactive_skus`
   (product.status != "active"), and `low_stock_skus` (marginal but not shortage)
   sorted ascending.

5. **Shipping quote**: call `/shipping/quote` with the order's warehouse and
   destination. Round `total_cost_usd` to two decimals.

#### Replenishment Desk

Given BOM IDs with build quantities and dates:

1. **Explode each BOM**: multiply `quantity_per` by `build_quantity` for each
   component SKU. Sum across BOMs sharing a SKU to get `total_required`.

2. **Compute effective available at the target warehouse**: same formula as
   dispatch. `target_effective_available` = effective stock minus total_required.
   Negative = gap.

3. **Check timely purchase orders**: `/purchase_orders` filtered to the target
   warehouse, status open or confirmed, with delivery date on or before the
   build date. Sum the quantities for each SKU. This is `timely_po_qty`.

4. **Check inter-warehouse transfers**: for SKUs with a gap, look at inventory
   records at other warehouses. Effective available there (minus their own
   reserved/quarantined/buffer) can be transferred. Prefer the warehouse with
   the largest usable surplus.

5. **Classify `final_action`**:
   - Effective available >= total_required → `no_action_stocked` (exclusion: `stocked_no_gap`)
   - Timely PO covers the entire gap → `timely_po_covered` (exclusion: `timely_po_covers_gap`)
   - Effective available > total_required (overstock) → `overstock_excluded` (exclusion: `target_overstock`)
   - Gap can be fully closed by transfers → `transfer_only`
   - Gap requires purchase → `purchase_required`

6. **Purchase requisitions**: for `purchase_required` SKUs, use `products/{sku}`
   for `supplier_id` and `unit_cost`. `extended_cost` = quantity * unit_cost,
   rounded to two decimals.

7. **Excluded components**: any SKU whose `final_action` is `no_action_stocked`,
   `timely_po_covered`, or `overstock_excluded` goes into `excluded_components`
   with the matching reason and supporting PO IDs.

8. Sort lists as the answer template specifies (usually SKU ascending for
   component_plan, purchase_requisitions, and excluded_components; SKU then
   quantity desc then from_warehouse for transfers).

#### Supplier Scorecard Desk

1. **Fetch all incidents and suppliers** from `/incidents` and `/suppliers`.

2. **Filter incidents** to the date window in the request memo using the
   `open_date` field (inclusive start, inclusive end unless stated otherwise).

3. **Compute duration**: closed incidents use close_date - open_date calendar
   days; open incidents use analysis_date - open_date. Round to the precision
   the memo specifies (usually two decimals).

4. **Aggregate per supplier**: count incidents, sum resolution costs, compute
   percentage share (supplier incident count / total filtered incidents * 100,
   rounded per the memo's precision rule), count RMAs (type == "RMA"), count
   work orders (type == "WORK_ORDER"), count open incidents (status == "open"),
   count severe incidents (severity in the memo's severe_severity_values list).

5. **Apply recommendation policy** using the precedence chain in the memo.
   The memo's policy object lists codes in precedence order with the exact
   conditions. Apply the highest-precedence matching code. Do not write new
   conditions — use exactly the thresholds and criteria in the memo.

6. **Populate `top_escalation_suppliers`** with only suppliers whose
   recommendation_code is the top escalation code, sorted per the memo's sort
   rule (typically incident count desc, then cost desc, then supplier_id asc).

7. **Highest cost** = supplier with max total_resolution_cost. **Highest share**
   = supplier with max incident_percentage. Break ties by supplier_id asc.

#### Allocation Desk

1. **Fetch the wave's orders**: look up each order in the wave. Each order has
   line items — process line by line.

2. **For each line**:
   - Get the SKU's effective available at the requested warehouse.
   - Record `requested_effective_available` as the effective stock at that
     warehouse (before reserving for this line).

3. **Classify the action**:
   - Customer blocked/suspended → manual_review, reason account_blocked
   - Customer has review flag → manual_review, reason account_review_required
   - Customer has fraud flag → manual_review, reason fraud_watch
   - Product inactive → manual_review, reason inactive_product
   - Effective stock >= ordered qty → ship, ship_quantity = ordered qty
   - Effective stock < ordered qty but another warehouse has enough usable
     stock → transfer, ship_quantity = whatever the requested warehouse can
     supply, transfer_quantity = remainder from one source warehouse,
     transfer_from = that warehouse
   - No warehouse can cover → backorder, backorder_quantity = ordered qty
     (or the uncovered remainder), reason insufficient_effective_stock

4. **Transfer requests**: only lines with action transfer generate entries,
   one per line. Use the source and destination warehouses.

5. **Blocked orders list**: orders whose block is at account/customer-risk level
   (not product-only issues). This means account_blocked, account_review_required,
   fraud_watch — but not inactive_product or insufficient_effective_stock.

6. **Order rollup**: per-order outcome. If all lines are ship → ready_to_ship;
   if any line is transfer (and no harder action) → needs_transfer; any
   backorder → has_backorder; any manual_review → manual_review; mixed
   (no manual_review but mix of ship/transfer/backorder) → mixed_actions.

7. **Summary**: count total orders, total lines, ship lines, transfer lines,
   backorder lines, manual_review lines, blocked orders, transfer units, and
   backorder units.

#### Procurement Quality Hold Desk

1. **Fetch the target suppliers** from `/suppliers/{supplier_id}` for each ID
   in the memo. Record their `quality_status`.

2. **Fetch incidents within the memo's analysis window**: filter `/incidents`
   by `open_date` between start and end (inclusive). Then restrict to the
   target supplier IDs.

3. **Fetch purchase orders** for the target suppliers: `/purchase_orders`
   filtered to status open or confirmed, for the target supplier IDs.

4. **Per supplier**:
   - `recent_incident_count`: count of filtered incidents
   - `recent_rma_count`: count where type == "RMA"
   - `severe_or_critical_count`: count where severity in ["high", "critical"]
   - `open_incident_count`: count where status == "open"
   - `affected_skus`: unique sorted SKUs from the supplier's incidents
   - `sample_incident_ids`: up to 5 sorted incident IDs
   - `held_po_ids`: open/confirmed POs for this supplier, sorted
   - **Decision**: apply the memo's policy. The policy maps quality_status,
     incident counts, RMA counts, and severity to one of the allowed decisions
     (typically freeze_new_replenishment, buyer_review_required, or
     monitor_only). Derive the thresholds from the memo's explicit decision
     criteria; if the memo is terse, infer a reasonable precedence:
     - quality_hold with recent incidents → most restrictive
     - High incident count or high severity → middle tier
     - Low incident count, no severity flags → monitor_only

5. **Aggregate**: `held_po_ids` = union of all suppliers' held POs, sorted.
   `release_supplier_ids` = suppliers with monitor_only decision, sorted.
   `summary` counts as specified by the answer template.

### 6. Format the Output JSON

Follow the answer template with mechanical precision:

- **Required top-level keys**: every key listed as required must be present,
  even if its value is `0`, `[]`, or `null`.
- **Enums**: use only the allowed values listed in the template. Do not coin
  new status strings.
- **Sort order**: the template defines sort rules for every list. Apply them
  exactly — ascending string sort for IDs, descending for counts when specified,
  multi-key sorts in the stated priority.
- **Numeric precision**: currency fields round to two decimal places (use
  `round(value, 2)`). Percentage fields round to one decimal place unless the
  template says otherwise. Do not add currency symbols or thousand separators
  inside JSON number fields.
- **Null vs empty**: use `null` for optional fields that have no value (e.g.
  `transfer_from` when action is not `transfer`). Use `[]` for empty lists.
  Use `0` for zero quantities.
- **String vs integer**: `order_id` and `supplier_id` are strings. Quantities
  and counts are integers. Costs and percentages are numbers.
- **Wave/task IDs**: copy the `wave_id` or `task_id` value from the memo or
  prompt, not from the answer template's `required_value` field (the template
  may contain placeholder strings for illustration; use the memo's actual
  identifier).

## API Details

The ERP API lives at the base URL provided by the runner. All endpoints return
JSON. No authentication is needed. The available endpoints include:

- `GET /manifest` — list of all endpoints with record schemas
- `GET /products` — all products; `/products/{product_id}` — single product
- `GET /inventory` — all inventory records; `/inventory/{sku}` — per-SKU
- `GET /warehouses` — all warehouses; `/warehouses/{warehouse_id}` — single
- `GET /orders` — all orders; `/orders/{order_id}` — single order with lines
- `GET /customers` — all customers; `/customers/{customer_id}` — single
- `GET /suppliers` — all suppliers; `/suppliers/{supplier_id}` — single
- `GET /purchase_orders` — all POs; `/purchase_orders/{po_id}` — single
- `GET /boms` — all BOMs; `/boms/{bom_id}` — single
- `GET /incidents` — all incidents; `/incidents/{incident_id}` — single
- `GET /shipping/quote` — shipping quote (query params for origin/destination)

When the full-list endpoint returns a large payload, prefer the targeted
single-record endpoints for orders, BOMs, and specific lookups. Use the full
list only for products, suppliers, warehouses, incidents, and purchase orders
where you need cross-record filtering.

## Key Data-Model Rules

**Effective available inventory** (repeatable formula, used by every desk):

```
effective = physical_quantity - (reserved_quantity + quarantined_quantity + buffer_quantity)
```

Buffer stock and quarantined units are not available for new orders. Reserved
units are already committed. Only effective units can be used for ship,
transfer, or build decisions.

**Product status**: a product with `status != "active"` (e.g. "inactive",
"discontinued", "end_of_life") should flag the SKU as inactive. Inactive
products can still appear in backorder or manual-review paths but should not
be released for automatic ship.

**Customer account**: the customer record's `status` field and any flag fields
(`account_blocked`, `fraud_watch`, `credit_hold`, etc.) determine whether the
order clears automatically or needs manual review. The answer template's
`customer_exception` enum tells you which flags to check.

**Supplier quality**: a supplier's `quality_status` field (`approved`, `watch`,
`quality_hold`) combined with incident history determines replenishment controls.

## Common Pitfalls

- **Skipping the manifest**: always fetch `/manifest` first. Field names in the
  live API may differ from assumptions.
- **Using physical quantity instead of effective**: reserved, quarantined, and
  buffer stock are not usable. Under-counting the gap leads to incorrect
  backorder/transfer decisions.
- **Forgetting to check product status**: an SKU with plenty of effective stock
  but an inactive product status must still be flagged.
- **Currency precision**: round to two decimals after every multiplication or
  summation, not just at the end.
- **Sort order**: the answer template's sort rules are part of the contract.
  Lists that are not sorted per spec will fail validation.
- **Copying template placeholder values**: the answer template may show example
  values or required_value fields for illustration. Always source real values
  from the memo or API.
- **Missing summary keys**: every required key in the answer template must appear
  in the output. An empty list, zero count, or 0.00 cost is still required.
- **Transfer source selection**: when multiple warehouses can supply a transfer,
  choose the one with the largest usable surplus. Transfer only effective stock,
  not protected units.
- **PO eligibility**: only purchase orders with status "open" or "confirmed"
  and delivery date on or before the need-by date count as timely. POs for a
  different warehouse do not count toward that warehouse's coverage.
- **Date comparisons**: include both boundary dates unless the memo explicitly
  says exclusive. Use calendar days for duration arithmetic.
