# Northwind ERP API Catalog

All endpoints live under `<TASK_ENV_BASE_URL>`. Every response is JSON. No auth, no pagination.

## Products

**Collection:** `GET /products`
**Single:** `GET /products/{sku}`

| Field | Type | Meaning |
|-------|------|---------|
| `sku` | string | Primary key, e.g. `NW-1000` |
| `name` | string | Human-readable product name |
| `category` | string | `electronics`, `industrial_spares`, `maintenance_kits`, `power` |
| `active` | boolean | `false` means the product is discontinued/inactive -- do not ship |
| `supplier_id` | string | FK into `/suppliers` |
| `unit_cost` | number | Landed cost per unit in USD |
| `weight_lb` | number | Unit weight in pounds, used in shipping quote calculations |
| `overstock_threshold` | integer | Units above this count are considered overstock |
| `safety_stock` | integer | Buffer quantity the warehouse should retain |

## Inventory

**Collection:** `GET /inventory`
**Filtered:** `GET /inventory?sku={sku}` and/or `GET /inventory?warehouse_id={warehouse_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `sku` | string | FK into `/products` |
| `warehouse_id` | string | FK into `/warehouses`. One of `WH_NORTH`, `WH_CENTRAL`, `WH_WEST` |
| `on_hand` | integer | Physical units present |
| `reserved` | integer | Units already committed to other orders -- not available |
| `quarantined` | integer | Units held for quality inspection -- not available |
| `last_count_date` | string | Last cycle count date, `YYYY-MM-DD` |

**Effective availability** for a SKU at a warehouse is `on_hand - reserved - quarantined`. Negative values mean demand exceeds what's physically available after accounting for prior commitments.

## Warehouses

**Collection:** `GET /warehouses`
**Single:** `GET /warehouses/{warehouse_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `warehouse_id` | string | `WH_NORTH`, `WH_CENTRAL`, `WH_WEST` |
| `name` | string | Regional name |
| `region` | string | `Northeast`, `Midwest`, `West`, `South` |
| `zip` | string | Origin ZIP for shipping quotes. WH_NORTH=07102, WH_CENTRAL=60607, WH_WEST=89502 |

## Orders

**Collection:** `GET /orders`
**Filtered:** `GET /orders?wave={wave_id}`
**Single:** `GET /orders/{order_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `order_id` | string | e.g. `SO-70000` |
| `customer_id` | string | FK into `/customers` |
| `warehouse_id` | string | Requested shipping warehouse |
| `destination_zip` | string | Delivery ZIP, passed to shipping quotes |
| `priority` | string | `high` or `normal` |
| `required_date` | string | Customer-requested delivery date, `YYYY-MM-DD` |
| `shipping_speed` | string | `ground`, `overnight`, or `expedited` |
| `wave` | string | Order wave identifier |
| `lines` | array | Line items ordered |
| `lines[].line_id` | integer | Line number within the order |
| `lines[].sku` | string | FK into `/products` |
| `lines[].quantity` | integer | Units requested |
| `lines[].unit_price` | number | Selling price per unit in USD |

## Customers

**Collection:** `GET /customers`
**Single:** `GET /customers/{customer_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `customer_id` | string | e.g. `CUST-2000` |
| `name` | string | Company name |
| `account_status` | enum | `active` (can ship), `blocked` (must hold), `review_required` (needs manual review before release) |
| `tier` | enum | `strategic`, `standard`, `economy` |
| `margin_band` | enum | `high`, `medium`, `low` |
| `risk_flag` | enum | `none`, `fraud_watch`, `credit_watch` |

**Note:** Different output enums map differently to these fields. Some tasks map `account_status: blocked` to `customer_exception: account_blocked`, while `risk_flag: credit_watch` maps to `customer_exception: credit_watch`, and `risk_flag: fraud_watch` maps to `customer_exception: fraud_watch`. An `account_status: review_required` typically maps to `customer_exception: review_required`. Always check the answer template's allowed values to determine the exact mapping.

## Suppliers

**Collection:** `GET /suppliers`
**Single:** `GET /suppliers/{supplier_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `supplier_id` | string | e.g. `SUP-001` through `SUP-012` |
| `name` | string | Supplier company name |
| `region` | string | `Northeast`, `Midwest`, `West`, `South` |
| `quality_status` | enum | `approved`, `watch`, `quality_hold` |

## Purchase Orders

**Collection:** `GET /purchase_orders`
**Filtered:** `GET /purchase_orders?supplier_id={supplier_id}`
**Single:** `GET /purchase_orders/{po_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `po_id` | string | e.g. `PO-50000` |
| `sku` | string | FK into `/products` |
| `supplier_id` | string | FK into `/suppliers` |
| `warehouse_id` | string | Destination warehouse for the PO |
| `quantity` | integer | Units on order |
| `status` | enum | `open`, `confirmed`, `received`, `cancelled` |
| `eta` | string | Expected arrival date, `YYYY-MM-DD` |

**Replenishment rules:** Only `open` and `confirmed` POs are eligible for coverage. A PO is "timely" when its `eta` is on or before the target build/need date. POs must be for the same `warehouse_id` as the planning site to qualify. `received` POs have already landed and their quantity should already be reflected in inventory. `cancelled` POs are dead.

**Quality hold rules:** When freezing replenishment from a supplier, hold all `open` and `confirmed` POs for that supplier.

## BOMs (Bills of Materials)

**Collection:** `GET /boms`
**Single:** `GET /boms/{bom_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `bom_id` | string | e.g. `BOM-300` |
| `name` | string | Kit/product name |
| `warehouse_id` | string | Build site |
| `target_date` | string | Original target, `YYYY-MM-DD` |
| `components` | array | Required components |
| `components[].sku` | string | FK into `/products` |
| `components[].quantity_per_kit` | integer | Units of this SKU needed per kit |

**Total requirement** for a component is `quantity_per_kit * build_quantity`, summed across all kits sharing that component.

## Incidents

**Collection:** `GET /incidents`
**Single:** `GET /incidents/{incident_id}`

| Field | Type | Meaning |
|-------|------|---------|
| `incident_id` | string | e.g. `INC-90000` |
| `supplier_id` | string | FK into `/suppliers` |
| `sku` | string | FK into `/products` |
| `warehouse_id` | string | Where the incident occurred |
| `incident_type` | enum | `RMA` or `WORK_ORDER` |
| `severity` | enum | `low`, `medium`, `high`, `critical` |
| `status` | enum | `open` or `closed` |
| `open_date` | string | Date incident was opened, `YYYY-MM-DD` |
| `close_date` | string or null | Date incident was closed, `YYYY-MM-DD`. Null when `status` is `open` |
| `resolution_cost` | number | Cost to resolve in USD |
| `root_cause` | string | `incorrect_pick`, `carrier_damage`, `count_variance`, `customer_return`, `engineering_change` |

**Duration calculation:** For closed incidents, calendar days from `open_date` to `close_date`. For open incidents, calendar days from `open_date` to the analysis date supplied by the task.

## Shipping Quote

**Endpoint:** `GET /shipping/quote`

Required query params: `warehouse_id`, `destination_zip`, `weight_lb`.
Optional: `shipping_speed` (when omitted, defaults to ground).

| Field | Type | Meaning |
|-------|------|---------|
| `zone_distance` | integer | Shipping zone |
| `service_days` | integer | Transit days |
| `total_cost_usd` | number | Quote total in USD |

**Weight calculation:** For an entire order, sum `weight_lb` across all lines by looking up each SKU's product weight and multiplying by the line quantity. Pass the total as the `weight_lb` parameter.

## Cross-Entity Relationships

| From | Field | To |
|------|-------|-----|
| Order | `customer_id` | Customer `customer_id` |
| Order | `warehouse_id` | Warehouse `warehouse_id` |
| Order | `warehouse_id`+`destination_zip` | Shipping quote params |
| Order line | `sku` | Product `sku` |
| Product | `supplier_id` | Supplier `supplier_id` |
| Inventory | `sku`+`warehouse_id` | Product+Warehouse pair |
| PO | `supplier_id` | Supplier `supplier_id` |
| PO | `sku`+`warehouse_id` | Product+Warehouse pair |
| BOM component | `sku` | Product `sku` |
| BOM | `warehouse_id` | Warehouse `warehouse_id` |
| Incident | `supplier_id` | Supplier `supplier_id` |
| Incident | `sku` | Product `sku` |
| Incident | `warehouse_id` | Warehouse `warehouse_id` |
