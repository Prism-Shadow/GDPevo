# Northwind ERP Data Models

Entity field descriptions, types, constraints, and relationships.

## Products

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Unique identifier, format NW-NNNN |
| name | string | Display name |
| category | string | electronics / industrial_spares / maintenance_kits / power |
| active | boolean | False means discontinued; must not be shipped |
| supplier_id | string | Links to suppliers |
| unit_cost | number | USD per unit, used for purchase requisition costing |
| weight_lb | number | Pounds per unit, used for shipping quote weight |
| safety_stock | integer | Units reserved as buffer; subtract from effective available |
| overstock_threshold | integer | Units above which the warehouse-level position is overstock |

## Inventory

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Product identifier |
| warehouse_id | string | WH_NORTH / WH_CENTRAL / WH_WEST |
| on_hand | integer | Physically counted units |
| reserved | integer | Units allocated to existing orders |
| quarantined | integer | Units held for quality inspection |
| last_count_date | string | YYYY-MM-DD of last cycle count |

No individual inventory detail endpoint exists. Filter the list endpoint instead.

## Warehouses

| Field | Type | Description |
|-------|------|-------------|
| warehouse_id | string | WH_NORTH, WH_CENTRAL, WH_WEST |
| name | string | Human-readable name |
| region | string | Northeast / Midwest / West |
| zip | string | 5-digit originating ZIP for shipping quotes |

## Orders

| Field | Type | Description |
|-------|------|-------------|
| order_id | string | SO-NNNNN |
| customer_id | string | Links to customers |
| warehouse_id | string | Requested fulfillment warehouse |
| wave | string | Named order group for allocation/expedite rounds |
| priority | string | high / normal / low |
| required_date | string | YYYY-MM-DD |
| shipping_speed | string | overnight / two_day / ground |
| destination_zip | string | 5-digit delivery ZIP |
| lines | array | At least one line item |

### Order Line

| Field | Type | Description |
|-------|------|-------------|
| line_id | integer | 1-based within the order |
| sku | string | Product requested |
| quantity | integer | Units requested |
| unit_price | number | Unit sale price |

## Customers

| Field | Type | Description |
|-------|------|-------------|
| customer_id | string | CUST-NNNN |
| name | string | Company name |
| account_status | enum | active / blocked / review_required |
| tier | string | strategic / standard / economy |
| risk_flag | enum | none / fraud_watch / credit_watch |
| margin_band | string | high / medium / low |

## Suppliers

| Field | Type | Description |
|-------|------|-------------|
| supplier_id | string | SUP-NNN |
| name | string | Company name |
| region | string | Northeast / Midwest / South / West |
| quality_status | enum | approved / watch / quality_hold |

## Purchase Orders

| Field | Type | Description |
|-------|------|-------------|
| po_id | string | PO-NNNNN |
| sku | string | Product on order |
| supplier_id | string | Supplying vendor |
| warehouse_id | string | Receiving warehouse |
| quantity | integer | Units ordered |
| status | enum | open / confirmed / received / cancelled |
| eta | string or null | Estimated arrival, YYYY-MM-DD |

Only open and confirmed POs count as timely coverage. Received POs are already in inventory counts. Cancelled POs are ignored.

## BOMs (Bill of Materials)

| Field | Type | Description |
|-------|------|-------------|
| bom_id | string | BOM-NNN |
| name | string | Kit name |
| warehouse_id | string | Default build warehouse |
| target_date | string | Original target date (informational) |
| components | array | Component list |

### BOM Component

| Field | Type | Description |
|-------|------|-------------|
| sku | string | Component product |
| quantity_per_kit | integer | Units needed per one assembled kit |

## Incidents

| Field | Type | Description |
|-------|------|-------------|
| incident_id | string | INC-NNNNN |
| supplier_id | string | Linked supplier |
| sku | string | Affected product |
| warehouse_id | string | Location of incident |
| incident_type | enum | RMA or WORK_ORDER |
| severity | enum | low / medium / high / critical |
| status | enum | open / closed |
| open_date | string | YYYY-MM-DD |
| close_date | string or null | YYYY-MM-DD; null if open |
| resolution_cost | number | USD cost to resolve |
| root_cause | string | carrier_damage / customer_return / incorrect_pick / count_variance / supplier_defect |

## Shipping Quote

| Field | Type | Description |
|-------|------|-------------|
| warehouse_id | string | Origin warehouse |
| destination_zip | string | Delivery ZIP |
| carrier | string | Northwind Parcel |
| speed | string | Requested service level |
| service_days | integer | Estimated transit days |
| zone_distance | integer | Shipping zone |
| weight_lb | number | Shipment weight |
| base_rate | number | Base charge |
| fuel_surcharge_rate | number | Fuel surcharge multiplier |
| total_cost | number | Final cost in USD |
