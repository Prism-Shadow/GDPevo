# Northwind ERP API Reference

Base URL: `<TASK_ENV_BASE_URL>` (supplied by the task runner).
All endpoints are `GET`, no authentication required.
All responses are JSON arrays or objects.

---

## Entity Collections

### GET /products
Returns all products. Fields: `sku`, `name`, `category`, `active` (bool), `supplier_id`, `unit_cost` (number), `weight_lb` (number), `safety_stock` (integer), `overstock_threshold` (integer).

### GET /products/{sku}
Returns a single product object.

### GET /inventory
Returns all inventory records. Each record: `sku`, `warehouse_id`, `on_hand` (int), `reserved` (int), `quarantined` (int), `last_count_date` (string, YYYY-MM-DD).

### GET /warehouses
Returns all warehouses (usually 3: WH_NORTH, WH_CENTRAL, WH_WEST). Fields: `warehouse_id`, `name`, `region`, `zip`.

### GET /warehouses/{warehouse_id}
Returns a single warehouse object.

### GET /orders
Returns all orders. Fields: `order_id` (string, e.g. SO-70000), `customer_id`, `warehouse_id`, `wave` (string), `priority` (high/normal/low), `required_date` (YYYY-MM-DD), `shipping_speed` (overnight/two_day/ground), `destination_zip`, `lines` (array of line objects).

Each line: `line_id` (int), `sku`, `quantity` (int), `unit_price` (number).

### GET /orders/{order_id}
Returns a single order object.

### GET /customers
Returns all customers. Fields: `customer_id`, `name`, `account_status` (active/blocked/review_required), `tier` (strategic/standard/economy), `risk_flag` (none/fraud_watch/credit_watch), `margin_band` (high/medium/low).

### GET /customers/{customer_id}
Returns a single customer object.

### GET /suppliers
Returns all suppliers. Fields: `supplier_id`, `name`, `region`, `quality_status` (approved/watch/quality_hold).

### GET /suppliers/{supplier_id}
Returns a single supplier object.

### GET /purchase_orders
Returns all purchase orders (POs). Fields: `po_id`, `sku`, `supplier_id`, `warehouse_id`, `quantity` (int), `status` (open/confirmed/received/cancelled), `eta` (YYYY-MM-DD or null).

### GET /purchase_orders/{po_id}
Returns a single PO object.

### GET /boms
Returns all Bills of Materials. Fields: `bom_id`, `name`, `warehouse_id`, `target_date` (YYYY-MM-DD), `components` (array).

Each component: `sku`, `quantity_per_kit` (int).

### GET /boms/{bom_id}
Returns a single BOM object.

### GET /incidents
Returns all quality incidents. Fields: `incident_id`, `supplier_id`, `sku`, `warehouse_id`, `incident_type` (RMA/WORK_ORDER), `severity` (low/medium/high/critical), `status` (open/closed), `open_date` (YYYY-MM-DD), `close_date` (YYYY-MM-DD or null), `resolution_cost` (number), `root_cause` (string).

### GET /incidents/{incident_id}
Returns a single incident object.

---

## Shipping

### GET /shipping/quote

Required query parameters:

| Parameter      | Type   | Description                                |
|----------------|--------|--------------------------------------------|
| `warehouse_id` | string | Origin warehouse (WH_NORTH/WH_CENTRAL/WH_WEST) |
| `destination_zip` | string | 5-digit destination ZIP code           |
| `weight_lb`    | number | Total shipment weight in pounds           |
| `speed`        | string | overnight / two_day / ground               |

Response fields: `warehouse_id`, `destination_zip`, `carrier`, `speed`, `service_days` (int), `zone_distance` (int), `weight_lb` (number), `base_rate` (number), `fuel_surcharge_rate` (number), `total_cost` (number, USD).

`total_cost` is already rounded to 2 decimal places in the API response, but re-round after any aggregation.

---

## Error Responses

Errors are returned as `{"error": "...", "status": 4xx}`. A 404 means the specific ID endpoint path is not supported (the list endpoint works, but individual lookups by ID may not work for all entities). When a detail endpoint fails, filter the list endpoint instead.
