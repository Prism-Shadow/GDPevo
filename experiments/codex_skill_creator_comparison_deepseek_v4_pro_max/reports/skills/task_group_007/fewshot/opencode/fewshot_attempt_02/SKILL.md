---
name: northwind-erp-desk
description: Complete Northwind Components ERP control-desk decision tasks. Use when the task involves a Northwind ERP API, expedite queues, allocation waves, kit replenishment, supplier scorecards, procurement quality holds, or any Northwind Components operations task with structured JSON output templates. The skill covers API data gathering, cross-record correlation, business-rule classification, shipping quotes, BOM-based component planning, incident analysis, and precise JSON answer formatting. Always reach for this skill whenever you see Northwind, ERP control-desk language (expedite, allocation, replenishment, scorecard, procurement), or a task mentioning a shared ERP API with JSON answer templates.
---

# Northwind ERP Desk

This skill covers the full pattern for Northwind Components ERP control-desk tasks: hitting the REST API, correlating records across endpoints, applying domain business rules, and producing structured JSON output that matches the provided answer template exactly.

## Core workflow

Every Northwind desk task follows this sequence. Do not skip steps.

### 1. Confirm the API entry point

The task gives you an API base URL, usually through `<TASK_ENV_BASE_URL>`. All endpoint paths are relative to it. Save it and use it for every call.

The API is read-only and requires no authentication. Available endpoints include:

```
GET /manifest
GET /products
GET /products/{product_id}
GET /inventory
GET /inventory/{sku}
GET /warehouses
GET /warehouses/{warehouse_id}
GET /orders
GET /orders/{order_id}
GET /customers
GET /customers/{customer_id}
GET /suppliers
GET /suppliers/{supplier_id}
GET /purchase_orders
GET /purchase_orders/{po_id}
GET /boms
GET /boms/{bom_id}
GET /incidents
GET /incidents/{incident_id}
GET /shipping/quote
```

Always start by reading `/manifest` — it confirms the available endpoints and may surface the exact URL structures the environment provides.

### 2. Read every input file

Each task provides at minimum a prompt and an answer template. Read the prompt first, then every file under `input/payloads/`. The answer template defines the exact output schema: required keys, enum values, sorting rules, field types, and precision requirements.

Pay close attention to:

- Required top-level keys
- Enum allowed values for every classification field
- Sort ordering instructions (ascending by which field, tie-breakers)
- Numeric precision (currencies are always 2 decimals, percentages vary)
- Required vs optional fields

### 3. Gather all relevant API data

Identify which endpoints you need from the task scope and fetch them in parallel. The common dependencies:

| Task type | Endpoints needed |
|-----------|-----------------|
| Expedite / Allocation / Transfer | orders, customers, products, inventory, warehouses, shipping/quote |
| Kit Replenishment | boms, products, inventory, warehouses, purchase_orders, suppliers |
| Supplier Scorecard / Procurement | incidents, suppliers, purchase_orders |

Fetch list endpoints first (e.g. `/orders`, `/inventory`), then drill into individual records as needed. When you need detail on specific records, fetch by ID. Parallelize all independent GET calls — the API is stateless and there is no rate-limiting.

For shipping quotes, use the `/shipping/quote` endpoint. You may need to call it per order with relevant parameters.

### 4. Correlate records

Build the relationships between records. The common linkages:

- **Order to Customer**: `order.customer_id` links to `/customers/{customer_id}`
- **Order to Lines to Products**: each line's SKU links to `/products/{sku}` and `/inventory/{sku}`
- **Order to Warehouse**: `order.warehouse_id` (or line-level warehouse) links to `/warehouses/{warehouse_id}`
- **BOM to Components to Products/Inventory/Suppliers**: BOM component SKUs drive the entire replenishment analysis
- **Incident to Supplier**: `incident.supplier_id` links to `/suppliers/{supplier_id}`
- **Purchase Order to Supplier**: `po.supplier_id` links to `/suppliers/{supplier_id}`

Correlate in memory — do not write intermediate files unless the data volume is enormous. For most Northwind tasks the full dataset fits in context.

### 5. Apply business rules methodically

Each task type has its own decision logic. Process records one at a time and apply rules in the order given by the prompt or memo. The answers in the training set show the expected classification patterns:

**Inventory status classification** (expedite / allocation tasks):
Check each SKU against inventory records. Classify as `ready` (sufficient effective stock), `low_stock` (below threshold), `shortage` (negative effective available), `inactive_sku` (product master shows inactive), or `inactive_and_shortage` (both conditions).

**Customer exception classification**:
Check the customer record's status flags. Map to: `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`.

**Fulfillment decision**:
Combine inventory status + customer exception to produce: `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`. Customer-level blocks override inventory status — if the account is blocked, the decision is `reject_hold` regardless of stock. If the account needs review, the decision is `manual_review` regardless of stock.

**Transfer decisions** (allocation tasks):
When `requested_effective_available` cannot cover the line, check other warehouses for the same SKU. Choose one source warehouse that can cover the gap. Leave any usable requested-warehouse quantity as `ship_quantity` and the gap as `transfer_quantity`.

**Recommendation codes** (scorecard tasks):
Apply precedence rules in order. The first matching condition wins:

1. `ESCALATE_SUPPLIER` — quality_hold with sufficient incidents, or critical RMA, or high-cost RMA threshold
2. `PROCESS_REVIEW` — work-order incidents outnumber RMA incidents past a threshold
3. `WATCHLIST` — quality_status is watch/quality_hold, or incident count threshold, or cost threshold, or severe count threshold
4. `MONITOR` — fallback when nothing above matches

**Replenishment decisions** (kit build tasks):
For each component SKU: calculate total required across all BOM targets, compute effective available at the target warehouse, check open POs for timely coverage, identify transfer sources, and classify as `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, or `overstock_excluded`.

**Procurement quality decisions**:
Review supplier quality status, recent incidents (RMA count, severity), and open/confirmed POs. Classify as `freeze_new_replenishment` (quality_hold, critical issues), `buyer_review_required` (watch status with moderate issues), or `monitor_only` (watch but no major concerns).

### 6. Compute shipping quotes

For expedite tasks, every order needs a shipping quote regardless of the fulfillment decision. Use `/shipping/quote` with the order's warehouse and shipping parameters. Include `zone_distance` (int), `service_days` (int), and `total_cost_usd` (rounded to 2 decimals).

### 7. Build aggregations and summary

Every answer template requires a summary section. Compute these after classifying all records:

- Count totals (orders, lines, components, suppliers)
- Decision counts grouped by decision type
- Currency totals (sum all shipping costs, purchase costs)
- Specific flagged lists (blocked orders, manual review orders, backorder orders, inactive SKU orders, escalation suppliers)
- Sort all lists as specified in the template

### 8. Produce the final JSON

Write exactly one JSON object. No narrative text, no markdown fences, no commentary. Validate before returning:

- All required top-level keys present
- All records sorted as specified
- All enum values match the template's allowed values exactly
- All numeric values rounded to the specified precision
- All list fields are arrays (never null, never omitted)
- Currency values are numbers, not strings

## Task-type quick reference

The five control-desk task types:

1. **Expedite Queue**: Order-level fulfillment decisions with inventory status, customer exceptions, shipping quotes. Input: queue memo with order IDs and operator notes.

2. **Kit Replenishment**: BOM-level component planning for kit builds at a target warehouse. Produces component plans, transfer requests, purchase requisitions, and excluded components.

3. **Supplier Scorecard**: Time-windowed incident aggregation per supplier with recommendation codes, escalation lists, and summary statistics.

4. **Allocation Desk**: Line-level decisions for a mixed-warehouse wave. Classifies every line as ship/transfer/backorder/manual_review with transfer requests.

5. **Procurement Quality**: Supplier quality review for targeted supplier IDs. Produces supplier decisions, held PO lists, and release supplier lists.

## Common pitfalls

**Enum values must match exactly.** The answer template defines the allowed values. Do not invent variants, even if they seem reasonable. If the template says `ship_now`, do not write `Ship Now` or `ship-now`.

**Sort order matters.** Every list in the template specifies sort ordering. Apply it after all records are classified. Use the exact tie-breaker sequence given.

**Effective available, not physical stock.** Inventory endpoints return `effective_available` which already accounts for reservations, quarantine, and buffer. Do not add your own deductions to this number.

**Customer blocks override stock.** When a customer is blocked, on fraud watch, or needs review, the line or order decision is always manual_review or reject_hold — even if inventory is ready. The business logic is: account risk trumps stock availability.

**Precision matters.** Currency is always 2 decimal places. Percentages are 1 decimal place (unless the template says otherwise). Durations are 2 decimal places for averages.

**Single JSON object only.** The final answer is one JSON object, not a stream of separate objects or a list. No wrapping text, no markdown code fences, no trailing commentary.

## Reference

For detailed field-by-field schemas of the answer templates and the data model of the ERP API, see [api-reference.md](references/api-reference.md).
