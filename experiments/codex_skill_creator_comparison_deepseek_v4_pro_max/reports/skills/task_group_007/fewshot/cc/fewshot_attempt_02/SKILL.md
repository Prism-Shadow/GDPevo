---
name: northwind-erp
description: Solve Northwind Components ERP operational tasks. Use whenever the user describes a Northwind Components dispatch, expedite, allocation, replenishment, kit-build, procurement, or supplier-quality task, mentions an ERP API with products, orders, inventory, warehouses, customers, suppliers, incidents, BOMs, purchase orders, or shipping quotes, or provides an answer_template.json with business-decision output shape requirements. The skill applies to any Northwind operational desk workflow, even when the user does not use the exact phrase "Northwind."
---

# Northwind Components ERP

A skill for solving Northwind Components operational desk tasks that require reading
live ERP data from a REST API and producing structured JSON decision files.

## What this skill covers

Common Northwind operational workflows follow a consistent pattern:

1.  Read the task prompt, any memo/payload files, and the answer template.
2.  Discover the API through the shared base URL.
3.  Fetch all relevant ERP records (orders, inventory, customers, products, suppliers, etc.).
4.  Cross-reference the live data against the business rules in the memo.
5.  Populate the answer template exactly.

This skill gives you the reusable rules and API conventions you need to solve any of
these desk workflows correctly on the first pass.

## Always start here

Before making any API calls, read every file the prompt lists. There are typically two
or three payloads:

- **Memo / request file** -- names the wave, BOM, supplier list, date range, or other
  scope, and may include operator notes or business rules.
- **Answer template** (`answer_template.json`) -- describes the exact output shape,
  required keys, field types, allowed enum values, sort orders, and precision rules.
  The template is the authoritative specification for the output.

If the prompt gives you a shared API entry point as `<TASK_ENV_BASE_URL>`, treat that
as the root of all API calls. If the prompt says "the API base URL is supplied by the
runner" or similar, you must substitute the actual base URL wherever the prompt or
memo uses a placeholder.

## API conventions

All endpoints are GET only. No authentication is required.

### Core endpoints

| Endpoint                  | Returns                                             |
| ------------------------- | --------------------------------------------------- |
| `/products`               | All products (SKU, active flag, unit_cost, weight_lb, supplier_id, overstock_threshold, safety_stock) |
| `/products/{sku}`         | Single product                                      |
| `/orders`                 | All orders (order_id, customer_id, warehouse_id, destination_zip, shipping_speed, lines, wave) |
| `/orders/{order_id}`      | Single order                                        |
| `/customers`              | All customers (customer_id, name, account_status, risk_flag, tier, margin_band) |
| `/customers/{customer_id}`| Single customer                                      |
| `/inventory`              | All inventory records (sku, warehouse_id, on_hand, reserved, quarantined) |
| `/warehouses`             | All warehouses (warehouse_id, name, region, zip)     |
| `/warehouses/{id}`        | Single warehouse                                    |
| `/suppliers`              | All suppliers (supplier_id, name, quality_status, region) |
| `/suppliers/{id}`         | Single supplier                                     |
| `/boms`                   | All BOMs (bom_id, name, warehouse_id, components with quantity_per_kit + sku) |
| `/boms/{bom_id}`          | Single BOM                                          |
| `/purchase_orders`        | All POs (po_id, sku, supplier_id, warehouse_id, quantity, status, eta) |
| `/purchase_orders/{po_id}`| Single PO                                           |
| `/incidents`              | All incidents (incident_id, supplier_id, sku, warehouse_id, incident_type, severity, status, open_date, close_date, resolution_cost) |
| `/incidents/{incident_id}`| Single incident                                     |
| `/shipping/quote`         | Shipping quote (see below)                          |

### Shipping quote

`GET /shipping/quote?warehouse_id=<id>&destination_zip=<zip>&weight_lb=<weight>&shipping_speed=<speed>`

`shipping_speed` is one of `ground`, `two_day`, `overnight`. The response includes
`total_cost`, `service_days`, `zone_distance`, `carrier`, and other fields.

To compute an order's total shipping weight: sum `weight_lb × line_quantity` for
every line, using the product record for each SKU.

### Inventory effective available

For any given SKU at a warehouse, the quantity you can actually use is:

```
effective_available = on_hand - reserved
```

Do not include `quarantined` stock in usable supply unless a task memo explicitly
tells you to treat quarantined differently. Reserved stock is spoken for; it must
not be double-counted for new decisions.

When a task mentions "available", "effective available", or "freely available" or
says to exclude "protected stock," always subtract reserved from on_hand.

### Purchase order eligibility

For replenishment tasks, a PO counts as "timely" when:

- `status` is `open` or `confirmed` (never `cancelled` or `received`)
- `warehouse_id` matches the target warehouse
- `eta` is on or before the date the material is needed

In quality-hold tasks, "held" POs are the open or confirmed POs from the suppliers
under review.

## Business-decision patterns

Use the authoritative reference at [references/rules.md](references/rules.md) for the full decision
tables and classification logic. That reference consolidates the patterns seen
across all five Northwind desk workflows. Read it when a task involves any of:

- Expedite / dispatch release decisions
- Allocation line-level actions (ship, transfer, backorder, manual_review)
- Kit-build replenishment (transfer requests, purchase requisitions, exclusions)
- Supplier incident scorecards with recommendation codes
- Procurement quality-hold supplier decisions

## Answer template compliance

The answer template defines exactly what the output must look like. Follow these
rules strictly:

1. **Top-level keys** -- Every key listed under `required_top_level_keys` or
   `top_level_required_keys` must appear. Do not add extra keys.

2. **Sort order** -- Obey every sort directive in the template. Common orders:
   - Records by `order_id` ascending
   - SKU lists ascending
   - Line actions by `order_id` ascending then `line_id` ascending
   - Transfer requests by sku ascending, then quantity descending, then
     from_warehouse_id ascending

3. **Enums** -- Only use values listed in the template's `allowed_values` arrays.
   Do not invent new enum members.

4. **Precision** -- Round currency to two decimal places. Percentages to one
   decimal place. Durations (days) to two decimal places when specified.

5. **Field types** -- Match the declared types (string, integer, number, list).
   Nulls are only allowed where the template says `null` is an option.

## Response discipline

- Return **only** the JSON object. No explanatory text before or after it.
- Keep the JSON valid. No trailing commas, no unquoted keys.
- The output should be a single top-level object (not an array), unless the
  template shows otherwise.
