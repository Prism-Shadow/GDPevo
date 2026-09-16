---
name: northwind-erp-operations
description: Solve Northwind Components ERP operational tasks — dispatch control, replenishment planning, supplier quality scoring, allocation decisions, and procurement quality reviews. Use this skill whenever the user mentions Northwind, a shared ERP API, expedite queues, kit builds, BOMs, supplier scorecards, order allocation, transfer waves, quality holds, replenishment decisions, or any task that asks you to read from a Northwind-style ERP REST API and produce a structured JSON decision file. Even if the user doesn't mention Northwind by name, use this skill when the task involves an ERP API with endpoints like /orders, /inventory, /products, /customers, /warehouses, /suppliers, /purchase_orders, /boms, /incidents, or /shipping/quote.
compatibility: Standard Python 3 with requests; no additional dependencies needed.
---

# Northwind ERP Operations

A reusable operations skill for solving Northwind Components ERP decision tasks. The skill covers five operational desks — all sharing the same REST API and data model — and guides the solver through API inspection, entity resolution, effective-inventory arithmetic, customer-risk classification, decision-rule application, and structured JSON output.

## General workflow

Every Northwind task follows the same pattern:

1. **Read the task memo and answer template.** The prompt and payloads in the task workspace define what to produce. The answer template is authoritative for output shape, sorting rules, allowed enum values, and numeric precision.

2. **Inspect the live API.** Use `curl` or a Python script with `requests` to call the shared ERP API at `<TASK_ENV_BASE_URL>`. All endpoints are read-only GETs. The complete endpoint catalog is in [references/api.md](references/api.md).

3. **Resolve entities and build the decision picture.** Cross-reference orders with products, customers, inventory, suppliers, and warehouses. The data model reference at [references/data_model.md](references/data_model.md) documents every entity field and its meaning.

4. **Apply the decision framework.** Each desk type (expedite, replenishment, scorecard, allocation, procurement) has its own rules. See [references/decisions.md](references/decisions.md) for the complete frameworks.

5. **Produce the output.** Return a single JSON object matching the answer template exactly. Respect every sorting rule, enum restriction, and precision requirement. Do not include narrative text outside the JSON.

## API usage

The base URL is always supplied as `<TASK_ENV_BASE_URL>` in the prompt or payloads. Substitute this token with the actual base URL before calling.

### Collection endpoints (GET)

All collection endpoints return full lists with no pagination:

- `GET /orders` — every order with its lines array
- `GET /products` — every product master record
- `GET /customers` — every customer account record
- `GET /inventory` — every warehouse/SKU inventory record
- `GET /warehouses` — all warehouses
- `GET /suppliers` — all suppliers
- `GET /purchase_orders` — all purchase orders
- `GET /boms` — all bill-of-materials definitions
- `GET /incidents` — all quality incidents

### Single-record endpoints (GET)

- `GET /orders/{order_id}` — single order
- `GET /products/{product_id}` — product by SKU (not implemented in the current API; use `/products` and filter client-side)
- `GET /inventory/{sku}` — inventory records for one SKU across all warehouses (returns an array)
- `GET /warehouses/{warehouse_id}` — single warehouse
- `GET /customers/{customer_id}` — single customer
- `GET /suppliers/{supplier_id}` — single supplier
- `GET /purchase_orders/{po_id}` — single PO
- `GET /boms/{bom_id}` — single BOM
- `GET /incidents/{incident_id}` — single incident

### Shipping quotes

`GET /shipping/quote?warehouse_id={id}&destination_zip={zip}&weight_lb={weight}`

Returns the shipping quote for one shipment. Required query params: `warehouse_id`, `destination_zip`, `weight_lb`. The response includes `zone_distance` (integer), `service_days` (integer), and `total_cost` (number, the all-in cost for the quote).

To compute shipping costs for an order:
- Sum the `weight_lb` across all order-line products from `/products`.
- If the prompt does not specify a shipping speed override, use the order's `shipping_speed` field. The API currently ignores the speed parameter in the query and returns a ground rate for all requests; use the returned `total_cost` directly.
- Some tasks ask for quotes even on orders that aren't releasing — always fetch the quote when the task or template requires it.

### Caching strategy

Fetch each collection endpoint once and filter/join in memory. Use Python dictionaries keyed by ID for fast lookups. The data sets are small enough (tens to low hundreds of records) that this is efficient and avoids repeated HTTP calls.

## Key conventions

### Effective available inventory

```
effective_available = on_hand - reserved - quarantined
```

This is the inventory that can actually be released or planned against. Do not use raw `on_hand`. Every inventory record has `on_hand`, `reserved`, and `quarantined` fields.

Negative effective-available means the warehouse is already oversold or overcommitted on that SKU.

### Customer exceptions

Customer records have two relevant fields for release decisions:

| `account_status` | Meaning for operations |
|---|---|
| `active` | No account-level block. |
| `blocked` | Account is blocked; all orders from this customer require hold/reject. |
| `review_required` | Account needs manual review before any release. |

| `risk_flag` | Meaning for operations |
|---|---|
| `none` | No risk flag. |
| `credit_watch` | Credit risk; hold releases pending review. |
| `fraud_watch` | Fraud concern; hold releases pending review. |

When both account_status and risk_flag signal problems, account_status takes precedence in classification.

### Product master flags

- `active`: boolean — `false` means the SKU is inactive. Inactive SKUs on order lines trigger special handling (manual review or escalation).
- `safety_stock`: integer — the normal operating buffer. Inventory at or below safety_stock counts as low stock for expedite decisions.
- `overstock_threshold`: integer — used in replenishment decisions to identify overstocked SKUs that should not receive additional inventory.

### Output precision and sorting

- Currency values: round to exactly 2 decimal places (e.g., `5678.96`, not `5678.9` or `5678.960`).
- Percentages: round to 1 decimal place when specified.
- Duration averages: round to 2 decimal places when specified.
- Lists: apply the sort order declared in the answer template. Common patterns: ascending by ID, by SKU, or by count descending then cost descending then ID ascending.
- Empty lists: use `[]`, never `null` or omission.

### Enum values

Every task template defines its own allowed enum values. Use exactly those values — do not invent alternatives. The decision frameworks in [references/decisions.md](references/decisions.md) map inputs to template-friendly outputs, but always cross-check against the task's own answer template.

## Desk-specific guidance

The detailed decision frameworks for each operational desk are in [references/decisions.md](references/decisions.md). Here is a quick-index of what each desk type needs:

- **Expedite/Dispatch** — Inventory status classification, customer exception mapping, final release decision with next action, shortage/inactive/low-stock SKU lists, shipping quotes.
- **Replenishment/Kit Build** — BOM explosion, component-level effective-available calculation, timely-PO coverage, inter-warehouse transfer proposals, purchase requisitions, exclusion of overstocked/covered components.
- **Supplier Scorecard** — Incident filtering by date range, per-supplier aggregation (counts, costs, durations, RMAs, work orders, open/severe counts), recommendation-code application per policy precedence.
- **Allocation/Transfer Wave** — Line-level action classification (ship/transfer/backorder/manual_review), customer-status gates, single-source transfer proposals, blocked-order lists, order-level rollup outcomes.
- **Procurement Quality Review** — Supplier-focused incident review, hold/freeze/buyer-review/monitor decisions, open/confirmed PO identification, affected-SKU and sample-incident collection.

## Helper script

A helper script at [scripts/northwind_helpers.py](scripts/northwind_helpers.py) provides common utility functions for effective-inventory calculation, entity lookups, and shipping-quote computation. Use it to reduce repetitive arithmetic, but always verify the outputs against the task's specific rules.
