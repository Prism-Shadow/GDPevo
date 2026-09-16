## Northwind ERP API Reference

The Northwind Components ERP API is a read-only REST API. All endpoints return JSON arrays or objects. No authentication is required.

### Base URL

The base URL is provided by the task runner as `<TASK_ENV_BASE_URL>`, typically `http://task-env:9007`.

### Endpoints

#### GET /products

Returns all products. Each product object:

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Product SKU identifier (e.g. "NW-1000") |
| name | string | Display name |
| category | string | Product category |
| active | boolean | Whether the product is active for fulfillment |
| unit_cost | number | Unit cost in USD |
| weight_lb | number | Weight in pounds |
| supplier_id | string | Primary supplier |
| safety_stock | integer | Minimum stock buffer in units |
| overstock_threshold | integer | Threshold above which stock is considered excess |

#### GET /products/{sku}

Single product by SKU.

#### GET /inventory

Returns inventory records for all warehouses. Each record:

| Field | Type | Description |
|-------|------|-------------|
| sku | string | SKU |
| warehouse_id | string | Warehouse identifier |
| on_hand | integer | Physical units present |
| reserved | integer | Units reserved for other orders |
| quarantined | integer | Units held for quality inspection |
| last_count_date | string | Last physical count date (YYYY-MM-DD) |

**Effective available** = `on_hand` − `reserved` − `quarantined`

Effective available can be negative when reservations exceed on-hand.

#### GET /inventory/{sku}

Inventory records for a single SKU across all warehouses.

#### GET /warehouses

Returns all warehouses:

| Field | Type | Description |
|-------|------|-------------|
| warehouse_id | string | Warehouse identifier |
| name | string | Display name |
| region | string | Region (Northeast, Midwest, South, West) |
| zip | string | ZIP code for shipping origin |

#### GET /warehouses/{warehouse_id}

Single warehouse by ID.

#### GET /orders

Returns all sales orders. Each order:

| Field | Type | Description |
|-------|------|-------------|
| order_id | string | Order identifier (e.g. "SO-70000") |
| customer_id | string | Customer identifier |
| warehouse_id | string | Requested fulfillment warehouse |
| wave | string | Allocation wave the order belongs to |
| priority | string | Priority: "high", "normal", or "low" |
| required_date | string | Customer-requested date (YYYY-MM-DD) |
| shipping_speed | string | Requested speed: "overnight", "two_day", or "ground" |
| destination_zip | string | Ship-to ZIP code |
| lines | array | Order lines (see below) |

Each line in `lines`:

| Field | Type | Description |
|-------|------|-------------|
| line_id | integer | Line number within the order |
| sku | string | Product SKU |
| quantity | integer | Units requested |
| unit_price | number | Sale price per unit in USD |

#### GET /orders/{order_id}

Single order by ID. Returns the full order object including lines.

#### GET /customers

Returns all customers:

| Field | Type | Description |
|-------|------|-------------|
| customer_id | string | Customer identifier |
| name | string | Customer name |
| account_status | string | "active", "blocked", or "review_required" |
| risk_flag | string | "none", "fraud_watch", or "credit_watch" |
| tier | string | "strategic", "standard", or "economy" |
| margin_band | string | "high", "medium", or "low" |

#### GET /customers/{customer_id}

Single customer.

#### GET /suppliers

Returns all suppliers:

| Field | Type | Description |
|-------|------|-------------|
| supplier_id | string | Supplier identifier |
| name | string | Supplier name |
| quality_status | string | "approved", "watch", or "quality_hold" |
| region | string | Geographic region |

#### GET /suppliers/{supplier_id}

Single supplier.

#### GET /purchase_orders

Returns all purchase orders:

| Field | Type | Description |
|-------|------|-------------|
| po_id | string | PO identifier (e.g. "PO-50000") |
| sku | string | Product SKU |
| supplier_id | string | Supplier |
| warehouse_id | string | Destination warehouse |
| quantity | integer | Units ordered |
| status | string | "open", "confirmed", "received", or "cancelled" |
| eta | string | Expected arrival date (YYYY-MM-DD) |

"Timely" POs = status is "open" or "confirmed" with ETA on or before a target date.

#### GET /purchase_orders/{po_id}

Single PO.

#### GET /boms

Returns all bills of materials:

| Field | Type | Description |
|-------|------|-------------|
| bom_id | string | BOM identifier |
| name | string | Kit/assembly name |
| warehouse_id | string | Build warehouse |
| target_date | string | Planned build date (YYYY-MM-DD) |
| components | array | Component lines |

Each component:

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Component SKU |
| quantity_per_kit | integer | Units needed per kit |

Total required for a component = `quantity_per_kit` × `build_quantity`.

#### GET /boms/{bom_id}

Single BOM.

#### GET /incidents

Returns all quality/supply incidents:

| Field | Type | Description |
|-------|------|-------------|
| incident_id | string | Incident identifier |
| supplier_id | string | Supplier |
| sku | string | Affected product SKU |
| warehouse_id | string | Affected warehouse |
| incident_type | string | "RMA" or "WORK_ORDER" |
| severity | string | "low", "medium", "high", or "critical" |
| status | string | "open" or "closed" |
| open_date | string | Date opened (YYYY-MM-DD) |
| close_date | string or null | Date closed, null if open |
| resolution_cost | number | Cost to resolve in USD |
| root_cause | string | Root cause category |

#### GET /incidents/{incident_id}

Single incident.

#### GET /shipping/quote

Returns a shipping quote for a parcel shipment. Required query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| warehouse_id | string | Origin warehouse |
| destination_zip | string | Ship-to ZIP code |
| weight_lb | number | Total package weight in pounds |
| speed | string | "overnight", "two_day", or "ground" |

Response fields:

| Field | Type | Description |
|-------|------|-------------|
| warehouse_id | string | Origin |
| destination_zip | string | Destination |
| weight_lb | number | Weight |
| speed | string | Service level |
| carrier | string | Carrier name |
| zone_distance | integer | Shipping zone |
| service_days | integer | Estimated transit days |
| base_rate | number | Base rate in USD |
| fuel_surcharge_rate | number | Surcharge as decimal |
| total_cost | number | Total cost in USD |

### Common Conventions

- Currency values: round to 2 decimal places.
- Percentages: round to 1 decimal place.
- Durations: round to 2 decimal places.
- List ordering: sort strings ascending (lexicographic) unless a task specifies otherwise.
- Date filtering: inclusive of both start and end dates.
- Duration for open incidents: calendar days from `open_date` to an `analysis_date`.
- Duration for closed incidents: calendar days from `open_date` to `close_date`.

### Data Model Relationships

- Order → Customer via `customer_id`
- Order → Warehouse via `warehouse_id`
- Order line → Product via `sku`
- Product → Supplier via `supplier_id`
- Inventory → Product + Warehouse via `sku` + `warehouse_id`
- PO → Product + Supplier + Warehouse via `sku` + `supplier_id` + `warehouse_id`
- BOM component → Product via `sku`
- Incident → Supplier + Product + Warehouse via `supplier_id` + `sku` + `warehouse_id`
- Shipping quote → Warehouse + destination ZIP via `warehouse_id` + `destination_zip`
