# Northwind ERP API Reference

## Base URL and Authentication

Base URL is provided per-task as the `TASK_ENV_BASE_URL` placeholder (typically `http://task-env:9007`). No authentication required — all endpoints are open GET. All responses are `application/json`. List endpoints return full collections as a single JSON array (no pagination). Single-record endpoints add `/{id}` to the list path.

---

## GET /products

Returns all products. Response per product:

| Field | Type | Notes |
|---|---|---|
| `sku` | string | Primary key, e.g. `"NW-1000"` |
| `name` | string | |
| `category` | string | `electronics`, `industrial_spares`, `maintenance_kits`, `power` |
| `active` | boolean | `false` means discontinued/inactive |
| `supplier_id` | string | e.g. `"SUP-003"` |
| `unit_cost` | number | USD per unit |
| `safety_stock` | integer | Minimum buffer units |
| `overstock_threshold` | integer | Max effective units before overstock |
| `weight_lb` | number | Ship weight in pounds per unit |

### GET /products/{sku}

Returns a single product (same shape). 404 if not found.

---

## GET /inventory

Returns all inventory records. Each record is scoped to one SKU in one warehouse. A single SKU may appear across multiple warehouses.

| Field | Type | Notes |
|---|---|---|
| `sku` | string | |
| `warehouse_id` | string | `WH_NORTH`, `WH_CENTRAL`, `WH_WEST` |
| `on_hand` | integer | Total units physically present |
| `reserved` | integer | Units allocated to open orders |
| `quarantined` | integer | Units held for quality inspection |
| `last_count_date` | string | `YYYY-MM-DD` |

### Effective Available Stock

```
effective_available = on_hand - reserved - quarantined - safety_stock
```

Apply the product's `safety_stock` from `/products`. Negative effective_available means the warehouse cannot fill even its committed (reserved) demand from on-hand units. Do not treat reserved, quarantined, or safety stock as freely available.

### GET /inventory/{sku}

Not available. Filter the list endpoint client-side.

---

## GET /warehouses

Returns all warehouses.

| Field | Type | Notes |
|---|---|---|
| `warehouse_id` | string | `WH_NORTH`, `WH_CENTRAL`, `WH_WEST` |
| `name` | string | |
| `region` | string | `Northeast`, `Midwest`, `West`, `South` |
| `zip` | string | Origin ZIP for shipping quotes |

### GET /warehouses/{warehouse_id}

Not available. Filter the list endpoint client-side.

---

## GET /customers

Returns all customers.

| Field | Type | Notes |
|---|---|---|
| `customer_id` | string | e.g. `"CUST-2012"` |
| `name` | string | |
| `account_status` | string | `active`, `blocked`, `review_required` |
| `risk_flag` | string | `none`, `fraud_watch`, `credit_watch` |
| `tier` | string | `strategic`, `standard`, `economy` |
| `margin_band` | string | `low`, `medium`, `high` |

### GET /customers/{customer_id}

Returns a single customer object.

### Customer Exception Classification

Used in dispatch and allocation workflows. Check the customer record for each order's `customer_id`. Order of precedence:

1. `account_status == "blocked"` or `risk_flag == "credit_watch"` → **account_blocked** (or fraud_watch if `risk_flag == "fraud_watch"` and account is blocked). Stop all lines.
2. `risk_flag == "fraud_watch"` → **fraud_watch**. Stop all lines.
3. `account_status == "review_required"` → **review_required**. Stop all lines.
4. `account_status == "active"` and `risk_flag == "none"` → **none** (no customer-level exception).

---

## GET /orders

Returns all orders.

| Field | Type | Notes |
|---|---|---|
| `order_id` | string | e.g. `"SO-70000"` |
| `customer_id` | string | Join key to `/customers` |
| `warehouse_id` | string | Requested fulfillment warehouse |
| `destination_zip` | string | For shipping quotes |
| `shipping_speed` | string | `overnight`, `two_day`, `ground` |
| `priority` | string | `low`, `normal`, `high` |
| `required_date` | string | `YYYY-MM-DD` |
| `wave` | string | Wave/batch identifier |
| `lines` | array | Each item has `line_id` (int), `sku` (string), `quantity` (int), `unit_price` (number) |

### GET /orders/{order_id}

Returns a single order object.

---

## GET /suppliers

Returns all suppliers.

| Field | Type | Notes |
|---|---|---|
| `supplier_id` | string | e.g. `"SUP-003"` |
| `name` | string | |
| `region` | string | `Northeast`, `Midwest`, `West`, `South` |
| `quality_status` | string | `approved`, `watch`, `quality_hold` |

### GET /suppliers/{supplier_id}

Not available. Filter the list endpoint client-side.

---

## GET /purchase_orders

Returns all purchase orders.

| Field | Type | Notes |
|---|---|---|
| `po_id` | string | e.g. `"PO-50066"` |
| `sku` | string | |
| `supplier_id` | string | |
| `warehouse_id` | string | Destination warehouse |
| `quantity` | integer | |
| `eta` | string | `YYYY-MM-DD` expected delivery |
| `status` | string | `open`, `confirmed`, `received`, `cancelled` |

### Timely PO Definition

A PO is "timely" when its ETA is on or before the target need date AND its status is `open` or `confirmed`. Exclude `received` (already landed) and `cancelled`. Only count timely POs destined for the same warehouse as the build/order.

### GET /purchase_orders/{po_id}

Not available. Filter the list endpoint client-side.

---

## GET /boms

Returns all Bills of Materials.

| Field | Type | Notes |
|---|---|---|
| `bom_id` | string | e.g. `"BOM-300"` |
| `name` | string | Kit name |
| `warehouse_id` | string | Planned production site |
| `target_date` | string | `YYYY-MM-DD` |
| `components` | array | Each item has `sku` (string), `quantity_per_kit` (int) |

### GET /boms/{bom_id}

Returns a single BOM object.

---

## GET /incidents

Returns all incidents.

| Field | Type | Notes |
|---|---|---|
| `incident_id` | string | e.g. `"INC-90004"` |
| `supplier_id` | string | |
| `sku` | string | |
| `warehouse_id` | string | |
| `incident_type` | string | `RMA` or `WORK_ORDER` |
| `severity` | string | `low`, `medium`, `high`, `critical` |
| `status` | string | `open` or `closed` |
| `open_date` | string | `YYYY-MM-DD` |
| `close_date` | string or null | `null` if open |
| `resolution_cost` | number | USD |
| `root_cause` | string | `supplier_defect`, `carrier_damage`, `customer_return`, `count_variance`, `incorrect_pick`, `engineering_change` |

### Duration Calculation

- **Closed incidents**: calendar days from `open_date` to `close_date`.
- **Open incidents**: calendar days from `open_date` to analysis date.

### GET /incidents/{incident_id}

Not available. Filter the list endpoint client-side.

---

## GET /shipping/quote

Query-parameter endpoint. Required parameters:

| Parameter | Type | Notes |
|---|---|---|
| `warehouse_id` | string | Origin warehouse |
| `destination_zip` | string | Customer destination ZIP |
| `weight_lb` | number | Total shipment weight in pounds |
| `service` | string | `overnight`, `two_day`, `ground` |

Response shape:

| Field | Type | Notes |
|---|---|---|
| `warehouse_id` | string | |
| `destination_zip` | string | |
| `carrier` | string | `"Northwind Parcel"` |
| `speed` | string | Actual service level |
| `service_days` | integer | |
| `zone_distance` | integer | |
| `base_rate` | number | Pre-surcharge |
| `fuel_surcharge_rate` | number | e.g. `0.0925` |
| `total_cost` | number | `base_rate * (1 + fuel_surcharge_rate)` |
| `weight_lb` | number | Echoed |

### Computing Order Shipment Weight

Sum `line.quantity * product.weight_lb` across all lines on the order. Look up each SKU's `weight_lb` from `/products`. Use the sum as `weight_lb` in the quote request with the order's `warehouse_id`, `destination_zip`, and `shipping_speed`.

Use `total_cost`, `service_days`, and `zone_distance` from the response directly. Round `total_cost` to 2 decimal places. The response `speed` may differ from the requested `service` parameter; use what is returned.
