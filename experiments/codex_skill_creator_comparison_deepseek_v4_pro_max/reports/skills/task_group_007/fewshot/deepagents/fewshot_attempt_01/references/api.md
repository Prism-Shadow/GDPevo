# Northwind ERP API Reference

Base URL is `<TASK_ENV_BASE_URL>`. All responses are JSON. No authentication.

---

## GET /products

Returns all products (array).

| Field | Type | Notes |
|-------|------|-------|
| sku | string | Primary key, e.g. "NW-1000" |
| name | string | Human-readable name |
| active | boolean | Inactive products block automatic fulfillment |
| category | string | e.g. electronics, power, industrial_spares, maintenance_kits |
| supplier_id | string | Links to /suppliers |
| unit_cost | number | USD per unit |
| weight_lb | number | Pounds per unit (for shipping quotes) |
| safety_stock | integer | Minimum stock floor for allocation decisions |
| overstock_threshold | integer | Ceiling for over-stock exclusion checks |

## GET /products/{sku}

Returns a single product object.

```
curl -s "<TASK_ENV_BASE_URL>/products/NW-1007"
```

## GET /inventory

Returns all inventory records (array), one per SKU per warehouse.

| Field | Type | Notes |
|-------|------|-------|
| sku | string | Product SKU |
| warehouse_id | string | WH_NORTH, WH_CENTRAL, WH_WEST |
| on_hand | integer | Physical units in the warehouse |
| reserved | integer | Units already allocated to orders |
| quarantined | integer | Units held for quality inspection |
| last_count_date | string | Last physical count date |

## GET /warehouses

Returns all warehouses (array).

| Field | Type | Notes |
|-------|------|-------|
| warehouse_id | string | WH_NORTH, WH_CENTRAL, WH_WEST |
| name | string | e.g. "New Jersey Regional Warehouse" |
| region | string | Northeast, Midwest, West, South |
| zip | string | 5-digit ZIP for shipping quotes |

## GET /orders

Returns all sales orders (array).

| Field | Type | Notes |
|-------|------|-------|
| order_id | string | e.g. "SO-70000" |
| customer_id | string | Links to /customers |
| warehouse_id | string | Requested fulfillment warehouse |
| wave | string | Wave grouping label |
| priority | string | low, normal, high |
| required_date | string | Customer-requested date |
| shipping_speed | string | ground, two_day, overnight |
| destination_zip | string | Delivery ZIP |
| lines | array | See below |

Each line:

| Field | Type | Notes |
|-------|------|-------|
| line_id | integer | 1-based within order |
| sku | string | Product SKU |
| quantity | integer | Requested units |
| unit_price | number | Selling price per unit |

## GET /orders/{order_id}

Returns a single order object.

## GET /customers

Returns all customers (array).

| Field | Type | Notes |
|-------|------|-------|
| customer_id | string | e.g. "CUST-2000" |
| name | string | Customer name |
| account_status | string | active, blocked, review_required |
| risk_flag | string | none, fraud_watch, credit_watch |
| tier | string | strategic, standard, economy |
| margin_band | string | high, medium, low |

## GET /suppliers

Returns all suppliers (array).

| Field | Type | Notes |
|-------|------|-------|
| supplier_id | string | e.g. "SUP-001" |
| name | string | Supplier name |
| quality_status | string | approved, watch, quality_hold |
| region | string | Northeast, Midwest, South, West |

## GET /purchase_orders

Returns all purchase orders (array).

| Field | Type | Notes |
|-------|------|-------|
| po_id | string | e.g. "PO-50000" |
| sku | string | Product SKU |
| supplier_id | string | Links to /suppliers |
| warehouse_id | string | Destination warehouse |
| quantity | integer | Ordered units |
| status | string | open, confirmed, received, cancelled |
| eta | string | Expected arrival date (YYYY-MM-DD) |

Timely POs for replenishment: status is "open" or "confirmed", same
warehouse as build target, and eta <= build_date + 1 day buffer.

## GET /boms

Returns all Bills of Materials (array).

| Field | Type | Notes |
|-------|------|-------|
| bom_id | string | e.g. "BOM-300" |
| name | string | Kit name |
| warehouse_id | string | Planned build warehouse |
| target_date | string | Original target build date |
| components | array | See below |

Each component:

| Field | Type | Notes |
|-------|------|-------|
| sku | string | Component SKU |
| quantity_per_kit | integer | Units of this SKU per finished kit |

## GET /incidents

Returns all quality/operations incidents (array).

| Field | Type | Notes |
|-------|------|-------|
| incident_id | string | e.g. "INC-90000" |
| supplier_id | string | Linked supplier |
| sku | string | Affected product |
| warehouse_id | string | Where it occurred |
| incident_type | string | RMA or WORK_ORDER |
| severity | string | low, medium, high, critical |
| status | string | open or closed |
| root_cause | string | e.g. carrier_damage, incorrect_pick, count_variance |
| resolution_cost | number | USD |
| open_date | string | YYYY-MM-DD |
| close_date | string | YYYY-MM-DD or null if open |

Severe severity values for filtering: "high" and "critical".

Duration calculation:
- Closed: (close_date - open_date) in calendar days
- Open: (analysis_date - open_date) in calendar days

## GET /shipping/quote

Returns a shipping quote for a single order.

**Required query parameters:**

| Param | Type | Notes |
|-------|------|-------|
| warehouse_id | string | Origin warehouse |
| destination_zip | string | Delivery destination ZIP |
| weight_lb | number | Total shipment weight |
| speed | string | ground, two_day, overnight |

**Response fields:**

| Field | Type | Notes |
|-------|------|-------|
| warehouse_id | string | Origin |
| destination_zip | string | Destination |
| carrier | string | "Northwind Parcel" |
| speed | string | Requested speed |
| weight_lb | number | Shipment weight |
| base_rate | number | Base shipping rate |
| fuel_surcharge_rate | number | Surcharge multiplier |
| zone_distance | integer | Zone code |
| service_days | integer | Estimated transit days |
| total_cost | number | Final cost in USD |

**Example:**

```
curl -s "<TASK_ENV_BASE_URL>/shipping/quote?warehouse_id=WH_NORTH&destination_zip=07102&weight_lb=50&speed=overnight"
```

When quoting for an order, compute weight by summing (product weight_lb x
line quantity) across all lines. Use the order-level shipping_speed and
destination_zip.
