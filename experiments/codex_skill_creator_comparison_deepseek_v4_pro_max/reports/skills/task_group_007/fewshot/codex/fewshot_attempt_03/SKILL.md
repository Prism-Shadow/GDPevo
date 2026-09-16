---
name: northwind-erp
description: >-
  Northwind Components ERP supply-chain operations via a REST API. Use for
  dispatch control (expedite queues), replenishment/kit-build planning,
  supplier incident scorecards, allocation-desk order-wave transfer decisions,
  and procurement quality-hold controls. Covers inventory checks, shipping
  quotes, customer account status, purchase-order coverage, inter-warehouse
  transfers, and supplier quality analytics. Always use this skill when a task
  mentions the Northwind ERP API, the task environment base URL
  TASK_ENV_BASE_URL, Northwind Components, or any of the five operations
  desk workflows—or when a task provides a JSON answer template with keys
  matching the Northwind data model.
---

# Northwind ERP Operations

This skill covers the Northwind Components ERP REST API and five common
supply-chain operations workflows. The API is a read-only JSON REST service
authenticated by network presence only.

## Quickstart

1. Read the task prompt and find the API base URL (given as
   `TASK_ENV_BASE_URL`).
2. Read every payload file listed in the prompt (memo, template, request). The
   answer template defines the exact output shape.
3. Fetch live API records—collect all entities needed for computation before
   starting logic.
4. Apply the domain rules described below and in
   [references/operations.md](references/operations.md).
5. Write a single JSON object matching the template. Enforce every sort order,
   precision rule, and key constraint stated in the template.

Never produce narrative text outside the JSON when the task calls for a
JSON-only response.

## Core API

See [references/api.md](references/api.md) for the complete endpoint reference.
All endpoints are `GET` with no authentication.

The API base URL is supplied by the task runner via `TASK_ENV_BASE_URL`.
Substitute that value in all requests. For example:

    GET TASK_ENV_BASE_URL/products
    GET TASK_ENV_BASE_URL/orders/SO-70000
    GET TASK_ENV_BASE_URL/shipping/quote?warehouse_id=WH_NORTH&destination_zip=38247&weight_lb=200&speed=overnight

## Data Model

See [references/data_models.md](references/data_models.md) for field-by-field
entity schemas.

Key entities: products, inventory, warehouses, orders (with line items),
customers, suppliers, purchase orders, BOMs (with components), incidents, and
shipping quotes.

## Operational Domains

See [references/operations.md](references/operations.md) for complete workflow
patterns for each of the five domains. The domains are:

1. **Dispatch Control (expedite queue)** — classify orders by inventory status
   and customer exception; produce ship/hold/backorder/review decisions.
2. **Replenishment (kit build planning)** — compute component requirements
   against available stock, POs, and transfers; produce purchase requisitions
   and transfer requests.
3. **Supplier Quality Scorecard** — filter incidents, aggregate by supplier,
   apply recommendation policy.
4. **Allocation Desk (order-wave transfer)** — line-level inventory
   availability with inter-warehouse transfer sourcing and account blocking.
5. **Procurement Control (quality hold)** — supplier incident risk review for
   replenishment hold/release decisions.

## Rules That Apply Across All Domains

### Effective Available Inventory

For any warehouse-SKU pair, compute:

    effective_available = on_hand - reserved - quarantined - safety_stock

`on_hand`, `reserved`, `quarantined` come from the `/inventory`
endpoint. `safety_stock` comes from the `/products` endpoint for the SKU.
Protected quantities (reserved, quarantined, safety stock) must not be treated
as freely consumable. The result may be negative—a negative value represents a
net shortage already.

### Shipping Quotes

Call `GET /shipping/quote` with the order's `warehouse_id` as the
`warehouse_id` query parameter, the order's `destination_zip`, the order's
total weight (sum over all lines of `weight_lb * quantity`), and the order's
`shipping_speed`. Do not hardcode warehouse ZIP codes. The shipping endpoint
maps warehouse_id to its originating zip internally. `total_cost` in the
response is the rounded-to-2-decimals cost in USD.

### Customer Account Status

Use the `/customers/{customer_id}` endpoint to check `account_status`
(`active`, `blocked`, or `review_required`) and `risk_flag` (`none`,
`fraud_watch`, or `credit_watch`). These determine customer exceptions and
blocking decisions.

### Product Status

Use the `/products/{sku}` endpoint to check `active` (boolean). Inactive
products should be flagged in inventory-status classifications and may block
shipment.

### Inter-Warehouse Transfers

When the requested warehouse lacks effective available stock, check other
warehouses' effective available for the same SKU. Source from warehouses with
positive effective available, preferring the one with the most available units.
A transfer is only valid if the source warehouse has `effective_available > 0`.

### Purchase Order Coverage

For replenishment decisions, POs with status `open` or `confirmed` can
provide timely coverage if they ship to the target warehouse and their ETA is
before or on the needed-by date. Only the quantity portion that fills the gap
should be counted; do not double-count PO quantities across multiple
requirements.

### Sorting and Ordering

Every answer template specifies sort orders. Apply them exactly. Common
patterns: lists of records sorted ascending by the primary ID field (e.g.,
`order_id`, `supplier_id`, `sku`); nested string lists sorted ascending
by string value; multi-key sorts applying primary, then secondary, then tertiary
as stated.

### Currency and Rounding

- All USD amounts must be rounded to 2 decimal places using standard rounding.
- Percentages: round to the precision stated in the template (typically 1
  decimal place).
- Durations (days): round to the precision stated (typically 2 decimal places).

### Safe Arithmetic

- When computing percentages: avoid division by zero. If the denominator is
  zero, the result is `0.0`.
- When averaging durations: only include closed incidents (or as directed by the
  template rules). If there are no qualifying items, the average is `0.0`.

## Scripts

- `scripts/fetch_api.py` — fetch all entity lists or a single entity from the
  Northwind API. Use it for deterministic data collection when the task involves
  many entities.

## Reference Files

- [references/api.md](references/api.md) — complete endpoint reference with
  parameters and response shapes.
- [references/data_models.md](references/data_models.md) — entity field
  descriptions and relationships.
- [references/operations.md](references/operations.md) — detailed workflow
  patterns and decision rules for all five domains.
