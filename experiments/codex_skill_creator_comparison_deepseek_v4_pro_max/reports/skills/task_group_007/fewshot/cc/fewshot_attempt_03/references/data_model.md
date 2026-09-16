# Northwind ERP Data Model

Every entity in the Northwind ERP API. Use this reference to understand field meanings, relationships, and derived values.

---

## Products

| Field | Type | Meaning |
|---|---|---|
| sku | string | Primary key (e.g., "NW-1000") |
| name | string | Human-readable product name |
| category | string | Product category ("electronics", "industrial_spares", "maintenance_kits", "power") |
| active | boolean | false means the SKU is discontinued/inactive |
| unit_cost | number | Per-unit purchase cost in USD |
| weight_lb | number | Unit weight in pounds |
| supplier_id | string | FK to suppliers.supplier_id |
| safety_stock | integer | Normal operating buffer; at or below this is low stock |
| overstock_threshold | integer | Inventory at or above this threshold is overstocked |

---

## Inventory

| Field | Type | Meaning |
|---|---|---|
| sku | string | FK to products |
| warehouse_id | string | FK to warehouses |
| on_hand | integer | Physical units in the warehouse |
| reserved | integer | Units committed to open orders |
| quarantined | integer | Units in QA hold, not releasable |
| last_count_date | string | YYYY-MM-DD of last physical count |

**Derived**: effective_available = on_hand - reserved - quarantined

---

## Orders

| Field | Type | Meaning |
|---|---|---|
| order_id | string | Primary key (e.g., "SO-70000") |
| customer_id | string | FK to customers |
| warehouse_id | string | FK to warehouses; the order's preferred fulfillment site |
| destination_zip | string | Destination postal code |
| priority | string | "low", "normal", or "high" |
| required_date | string | YYYY-MM-DD requested delivery |
| shipping_speed | string | "ground", "two_day", or "overnight" |
| wave | string | Wave/batch identifier |
| lines[] | array | Order line items |

### lines[] fields

| Field | Type | Meaning |
|---|---|---|
| line_id | integer | Line number within the order |
| sku | string | FK to products |
| quantity | integer | Units ordered |
| unit_price | number | Sale price per unit in USD |

---

## Customers

| Field | Type | Meaning |
|---|---|---|
| customer_id | string | Primary key (e.g., "CUST-2000") |
| name | string | Company name |
| account_status | string | "active", "blocked", or "review_required" |
| risk_flag | string | "none", "credit_watch", or "fraud_watch" |
| tier | string | "strategic", "standard", or "economy" |
| margin_band | string | "high", "medium", or "low" |

---

## Warehouses

| Field | Type | Meaning |
|---|---|---|
| warehouse_id | string | Primary key ("WH_NORTH", "WH_CENTRAL", "WH_WEST") |
| name | string | Descriptive name |
| region | string | "Northeast", "Midwest", "West", "South" |
| zip | string | Origin ZIP for shipping quotes |

---

## Suppliers

| Field | Type | Meaning |
|---|---|---|
| supplier_id | string | Primary key (e.g., "SUP-001") |
| name | string | Supplier company name |
| quality_status | string | "approved", "watch", or "quality_hold" |
| region | string | Geographic region |

---

## Purchase Orders

| Field | Type | Meaning |
|---|---|---|
| po_id | string | Primary key (e.g., "PO-50000") |
| sku | string | FK to products |
| supplier_id | string | FK to suppliers |
| warehouse_id | string | FK to warehouses; destination for inbound stock |
| quantity | integer | Units ordered |
| status | string | "open", "confirmed", "received", "cancelled" |
| eta | string | YYYY-MM-DD expected arrival |

**Timely PO** for replenishment: a PO is "timely" when its eta falls on or before the build date AND its warehouse_id matches the planning site AND its status is "open" or "confirmed".

---

## BOMs (Bill of Materials)

| Field | Type | Meaning |
|---|---|---|
| bom_id | string | Primary key (e.g., "BOM-300") |
| name | string | Kit name |
| warehouse_id | string | Default planning warehouse |
| target_date | string | Default target build date (may be overridden by task) |
| components[] | array | Component list |

### components[] fields

| Field | Type | Meaning |
|---|---|---|
| sku | string | FK to products |
| quantity_per_kit | integer | Units of this SKU per one kit |

---

## Incidents

| Field | Type | Meaning |
|---|---|---|
| incident_id | string | Primary key (e.g., "INC-90000") |
| supplier_id | string | FK to suppliers |
| sku | string | FK to products |
| warehouse_id | string | FK to warehouses |
| incident_type | string | "RMA" (return) or "WORK_ORDER" (internal rework) |
| severity | string | "low", "medium", "high", or "critical" |
| status | string | "open" or "closed" |
| open_date | string | YYYY-MM-DD first reported |
| close_date | string or null | YYYY-MM-DD resolved; null if open |
| resolution_cost | number | Cost to resolve in USD |
| root_cause | string | "incorrect_pick", "carrier_damage", "customer_return", "count_variance" |

---

## Shipping Quote response

| Field | Type | Meaning |
|---|---|---|
| zone_distance | integer | Shipping zone |
| service_days | integer | Transit days |
| total_cost | number | All-in cost in USD |
| base_rate | number | Base rate before surcharge |
| fuel_surcharge_rate | number | Fuel surcharge as decimal |
| carrier | string | "Northwind Parcel" |
| speed | string | Shipping speed |
| warehouse_id | string | Origin warehouse |
| destination_zip | string | Destination ZIP |
| weight_lb | number | Total weight |
