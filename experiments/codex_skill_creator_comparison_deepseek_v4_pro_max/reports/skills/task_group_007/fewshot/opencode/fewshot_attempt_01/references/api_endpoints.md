# Northwind ERP API Endpoint Catalog

Base URL: `<TASK_ENV_BASE_URL>` (supplied by the task runner)

Authentication: none required

All endpoints return JSON. List endpoints return arrays; single-record endpoints
return objects.

## Endpoints

### GET /manifest

Returns a list of available endpoint paths. Call this first in every task to
confirm which collections exist. If the manifest fails, use this reference file
as the fallback catalog.

### GET /products

Returns all products.

Response fields per product:
- `product_id` (string) — SKU identifier, e.g. `"NW-XXXX"`
- `name` (string)
- `status` (string) — `"active"` or `"inactive"`

### GET /products/{product_id}

Returns a single product by SKU.

### GET /orders

Returns all sales orders.

Response fields per order:
- `order_id` (string) — e.g. `"SO-XXXXX"`
- `customer_id` (string)
- `warehouse_id` (string) — `"WH_NORTH"`, `"WH_CENTRAL"`, or `"WH_WEST"`
- `lines` (array of objects), each with:
  - `line_id` (integer)
  - `sku` (string)
  - `quantity` (integer)
  - `requested_warehouse` (string, optional — may differ from order-level warehouse)

### GET /orders/{order_id}

Returns a single order.

### GET /customers

Returns all customers.

Response fields per customer:
- `customer_id` (string)
- `name` (string)
- `account_status` (string) — `"active"`, `"blocked"`, `"review_required"`, etc.
- `fraud_flag` (boolean or string)
- `credit_hold` (boolean or string)

### GET /customers/{customer_id}

Returns a single customer.

### GET /inventory

Returns all inventory records (per SKU, per warehouse).

Response fields per record:
- `sku` (string)
- `warehouse_id` (string)
- `on_hand` (integer) — physical units present
- `reserved` (integer) — units allocated to other orders
- `quarantined` (integer) — units held for quality inspection
- `buffer` (integer) — normal operating safety buffer (may also appear as `normal_buffer`)

### GET /inventory/{sku}

Returns inventory for a single SKU across all warehouses.

### GET /warehouses

Returns all warehouses.

Response fields per warehouse:
- `warehouse_id` (string) — `"WH_NORTH"`, `"WH_CENTRAL"`, `"WH_WEST"`
- `name` (string)
- `zone` (integer) — shipping zone number

### GET /warehouses/{warehouse_id}

Returns a single warehouse.

### GET /suppliers

Returns all suppliers.

Response fields per supplier:
- `supplier_id` (string) — e.g. `"SUP-XX"`
- `name` (string)
- `quality_status` (string) — `"approved"`, `"watch"`, or `"quality_hold"`

### GET /suppliers/{supplier_id}

Returns a single supplier.

### GET /purchase_orders

Returns all purchase orders.

Response fields per PO:
- `po_id` (string) — e.g. `"PO-XXXXX"`
- `supplier_id` (string)
- `sku` (string)
- `warehouse_id` (string)
- `status` (string) — `"open"`, `"confirmed"`, `"received"`, or `"cancelled"`
- `quantity` (integer)
- `delivery_date` (string, ISO date format)
- `unit_cost` (number)

### GET /purchase_orders/{po_id}

Returns a single purchase order.

### GET /boms

Returns all bills of materials.

Response fields per BOM:
- `bom_id` (string) — e.g. `"BOM-XX"`
- `name` (string) — kit name
- `components` (array of objects), each with:
  - `sku` (string)
  - `quantity_per_kit` (integer)

### GET /boms/{bom_id}

Returns a single BOM.

### GET /incidents

Returns all quality incidents.

Response fields per incident:
- `incident_id` (string) — e.g. `"INC-XXXXX"`
- `supplier_id` (string)
- `open_date` (string, ISO date format)
- `close_date` (string, ISO date format, null if still open)
- `severity` (string) — `"low"`, `"medium"`, `"high"`, or `"critical"`
- `type` (string) — `"RMA"`, `"WORK_ORDER"`, etc.
- `resolution_cost` (number, in USD)
- `status` (string) — `"open"` or `"closed"`

### GET /incidents/{incident_id}

Returns a single incident.

### GET /shipping/quote

Returns a shipping quote for an order. This is a parameterized endpoint.

Query parameters:
- `order_id` (string, required) — the sales order to quote

Response fields:
- `zone_distance` (integer)
- `service_days` (integer)
- `total_cost_usd` (number)

## Fetching Strategy

Always prefer the list endpoints (`/orders`, `/inventory`, `/products`, etc.)
over single-record endpoints. Fetch all collections you need in parallel, then
filter and cross-reference locally in your process. This is dramatically faster
than fetching one record at a time.

The only single-record endpoints you should use are:
- `/shipping/quote?order_id=...` — this endpoint requires a parameter
- `/manifest` — to discover the endpoint catalog (call this first)

Exception: if the API returns paginated results or the list endpoints are
unavailable, fall back to individual record lookups for the specific IDs named
in the task memo.
