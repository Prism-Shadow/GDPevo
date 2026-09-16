# Northwind ERP API Reference

Base URL: provided by the task environment as `<TASK_ENV_BASE_URL>` or equivalent. No authentication required.

## List Endpoints (GET)

All list endpoints return JSON arrays. Most support query-parameter filtering.

### GET /products

Filterable by `sku`, `supplier_id`, `active`.

Fields per record:

| Field | Type | Description |
|-------|------|-------------|
| `sku` | string | SKU identifier, e.g. "NW-1000" |
| `name` | string | Product name |
| `active` | boolean | Whether the product is active for fulfillment |
| `category` | string | electronics, industrial_spares, maintenance_kits, power, etc. |
| `supplier_id` | string | Primary supplier |
| `unit_cost` | number | Unit cost in USD |
| `weight_lb` | number | Weight in pounds |
| `safety_stock` | integer | Safety stock floor |
| `overstock_threshold` | integer | Threshold above which stock is overstock |

### GET /inventory

Filterable by `sku`, `warehouse_id`.

Fields per record:

| Field | Type | Description |
|-------|------|-------------|
| `sku` | string | SKU |
| `warehouse_id` | string | WH_NORTH, WH_CENTRAL, or WH_WEST |
| `on_hand` | integer | Physical units present |
| `reserved` | integer | Units reserved for existing orders |
| `quarantined` | integer | Units under quality hold |
| `last_count_date` | string | YYYY-MM-DD of last cycle count |

### GET /warehouses

Filterable by `warehouse_id`.

| Field | Type | Description |
|-------|------|-------------|
| `warehouse_id` | string | WH_NORTH, WH_CENTRAL, WH_WEST |
| `name` | string | Human-readable name |
| `region` | string | Northeast, Midwest, West, South |
| `zip` | string | Warehouse ZIP code |

### GET /orders

Filterable by `order_id`, `customer_id`, `wave`, `warehouse_id`.

Fields per record:

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | e.g. "SO-70000" |
| `customer_id` | string | e.g. "CUST-2012" |
| `destination_zip` | string | Delivery ZIP |
| `warehouse_id` | string | Requested fulfillment warehouse |
| `priority` | string | high, normal |
| `required_date` | string | YYYY-MM-DD |
| `shipping_speed` | string | overnight, two_day, ground |
| `wave` | string | Wave identifier |
| `lines` | array | Order lines (see below) |

Each line in `lines`:

| Field | Type | Description |
|-------|------|-------------|
| `line_id` | integer | Line number within the order |
| `sku` | string | Product SKU |
| `quantity` | integer | Requested units |
| `unit_price` | number | Price per unit in USD |

### GET /customers

No query-parameter filtering; fetch the full list and filter client-side.

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | e.g. "CUST-2012" |
| `name` | string | Company name |
| `account_status` | string | active, blocked, review_required |
| `risk_flag` | string | none, fraud_watch, credit_watch |
| `tier` | string | strategic, standard, economy |
| `margin_band` | string | high, medium, low |

### GET /suppliers

Filterable by `supplier_id`.

| Field | Type | Description |
|-------|------|-------------|
| `supplier_id` | string | e.g. "SUP-003" |
| `name` | string | Supplier name |
| `quality_status` | string | approved, watch, quality_hold |
| `region` | string | Northeast, Midwest, West, South |

### GET /purchase_orders

Filterable by `sku`, `supplier_id`, `status`, `warehouse_id`.

| Field | Type | Description |
|-------|------|-------------|
| `po_id` | string | e.g. "PO-50066" |
| `sku` | string | Product SKU |
| `supplier_id` | string | Supplier |
| `warehouse_id` | string | Destination warehouse |
| `quantity` | integer | Ordered units |
| `status` | string | open, confirmed, received, cancelled |
| `eta` | string | YYYY-MM-DD estimated arrival |

### GET /boms

Filterable by `bom_id`.

| Field | Type | Description |
|-------|------|-------------|
| `bom_id` | string | e.g. "BOM-300" |
| `name` | string | Kit name |
| `warehouse_id` | string | Planning warehouse |
| `target_date` | string | YYYY-MM-DD |
| `components` | array | Components (see below) |

Each component:

| Field | Type | Description |
|-------|------|-------------|
| `sku` | string | Component SKU |
| `quantity_per_kit` | integer | Units needed per kit |

### GET /incidents

Filterable by `supplier_id`, `sku`, `status`, `warehouse_id`.

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | string | e.g. "INC-90004" |
| `supplier_id` | string | Supplier |
| `sku` | string | Affected SKU |
| `warehouse_id` | string | Warehouse where incident occurred |
| `incident_type` | string | RMA or WORK_ORDER |
| `severity` | string | low, medium, high, critical |
| `status` | string | open or closed |
| `root_cause` | string | e.g. supplier_defect, carrier_damage |
| `resolution_cost` | number | USD |
| `open_date` | string | YYYY-MM-DD |
| `close_date` | string or null | YYYY-MM-DD, null when open |

### GET /shipping/quote

Required query params: `warehouse_id`, `destination_zip`, `weight_lb`.
Optional: `speed` (ground, two_day, overnight; defaults to ground).

| Field | Type | Description |
|-------|------|-------------|
| `warehouse_id` | string | Origin warehouse |
| `destination_zip` | string | Destination ZIP |
| `weight_lb` | number | Shipment weight |
| `speed` | string | Service level |
| `carrier` | string | "Northwind Parcel" |
| `zone_distance` | integer | Shipping zone |
| `service_days` | integer | Transit days |
| `base_rate` | number | Base rate USD |
| `fuel_surcharge_rate` | number | Surcharge as decimal |
| `total_cost` | number | Total cost USD (use this) |

## Single-Resource Endpoints (GET /{resource}/{id})

The paths `/products/{sku}`, `/orders/{order_id}`, and `/boms/{bom_id}` return a single record from the corresponding list. Other single-resource paths (`/customers/{id}`, `/warehouses/{id}`, `/suppliers/{id}`, `/incidents/{id}`, `/inventory/{sku}`, `/purchase_orders/{id}`) **may return 404**. When they do, fall back to the list endpoint and filter client-side by the identifier field.

## Core Calculations

**Effective available** = `on_hand - quarantined - reserved`. Never treat reserved or quarantined units as freely available for new fulfillment.

**Shipping weight** = sum over order lines of `product.weight_lb * line.quantity`.

**Currency** = round to 2 decimal places. **Percentages** = round to 1 decimal place.

**Timely POs** = purchase orders with status `open` or `confirmed` and `eta` on or before the target date, for the relevant warehouse.
