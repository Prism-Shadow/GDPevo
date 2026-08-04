# Northwind ERP API Reference

This reference documents the response schemas for the Northwind ERP API. All endpoints return JSON. No authentication is required.

## Products

### `GET /products` → list of all products
### `GET /products/{sku}` → single product

```json
{
  "sku": "NW-1000",
  "name": "Controller A-20",
  "category": "electronics",
  "active": true,
  "supplier_id": "SUP-003",
  "unit_cost": 116.62,
  "safety_stock": 46,
  "overstock_threshold": 139,
  "weight_lb": 12.05
}
```

**Fields:**
- `active` (bool): `false` means the product is discontinued/withdrawn — treat as inactive.
- `safety_stock` (int): minimum units to retain in each warehouse.
- `overstock_threshold` (int): if effective available exceeds this at the target warehouse, the SKU can be excluded from replenishment.
- `unit_cost` (float): USD per unit, used for purchase requisition costing.

---

## Inventory

### `GET /inventory` → list of all inventory records

```json
{
  "sku": "NW-1000",
  "warehouse_id": "WH_NORTH",
  "on_hand": 9,
  "reserved": 5,
  "quarantined": 0,
  "last_count_date": "2025-12-07"
}
```

**Fields:**
- `on_hand` (int): total physical units in the warehouse.
- `reserved` (int): units allocated to existing orders/picks.
- `quarantined` (int): units held for quality inspection; not available for fulfillment.
- `last_count_date` (string): most recent cycle-count date.

**Derived:**
- `effective_available = on_hand - reserved - quarantined`
- `available_after_safety = effective_available - safety_stock` (use product's `safety_stock`)

Inventory is a flat list. To look up a specific SKU at a specific warehouse, filter by `sku` and `warehouse_id`. There is no single-resource inventory endpoint.

---

## Warehouses

### `GET /warehouses` → list of all warehouses

```json
{
  "warehouse_id": "WH_NORTH",
  "name": "New Jersey Regional Warehouse",
  "region": "Northeast",
  "zip": "07102"
}
```

Three warehouses exist: `WH_NORTH` (07102), `WH_CENTRAL` (60607), `WH_WEST` (89502).

---

## Orders

### `GET /orders` → list of all orders
### `GET /orders/{order_id}` → single order

```json
{
  "order_id": "SO-70000",
  "customer_id": "CUST-2012",
  "warehouse_id": "WH_CENTRAL",
  "destination_zip": "38247",
  "wave": "TRAIN_EXPEDITE_A",
  "priority": "high",
  "shipping_speed": "overnight",
  "required_date": "2026-05-19",
  "lines": [
    {
      "line_id": 1,
      "sku": "NW-1049",
      "quantity": 30,
      "unit_price": 113.51
    }
  ]
}
```

**Fields:**
- `wave` (string): the order wave/batch identifier. Filter by this to find orders in a specific wave.
- `shipping_speed` (string): requested delivery speed — used for `/shipping/quote`.
- `destination_zip` (string): destination postal code for shipping quotes.
- `lines[].quantity` (int): units ordered.
- `lines[].unit_price` (float): sell price per unit (not needed for most decisions).

---

## Customers

### `GET /customers` → list of all customers
### `GET /customers/{customer_id}` → single customer

```json
{
  "customer_id": "CUST-2012",
  "name": "Caldera Mfg",
  "account_status": "active",
  "risk_flag": "none",
  "tier": "strategic",
  "margin_band": "medium"
}
```

**Fields:**
- `account_status` (enum): `active`, `blocked`, `on_hold`. Blocked accounts should halt automatic release.
- `risk_flag` (enum): `none`, `fraud_watch`, `credit_watch`, `review_required`. Any non-none flag may require manual review.
- `tier` (enum): `standard`, `strategic`, `critical`. Higher tiers may justify exceptions.
- `margin_band` (enum): `low`, `medium`, `high`.

---

## Suppliers

### `GET /suppliers` → list of all suppliers

```json
{
  "supplier_id": "SUP-003",
  "name": "Branson Relay Group",
  "region": "Midwest",
  "quality_status": "quality_hold"
}
```

**Fields:**
- `quality_status` (enum): `approved`, `watch`, `quality_hold`. Drives procurement control decisions.
- Individual supplier lookup (`/suppliers/{id}`) returns 404; filter the list instead.

---

## Purchase Orders

### `GET /purchase_orders` → list of all POs

```json
{
  "po_id": "PO-50001",
  "sku": "NW-1003",
  "supplier_id": "SUP-006",
  "warehouse_id": "WH_WEST",
  "quantity": 72,
  "status": "open",
  "eta": "2026-06-03"
}
```

**Fields:**
- `status` (enum): `open`, `confirmed`, `cancelled`, `received`. For coverage calculations, count `open` and `confirmed` POs. Ignore `cancelled` and `received`.
- `eta` (string or null): estimated arrival date. A PO is "timely" if `eta <= target_date`.
- Individual PO lookup (`/purchase_orders/{po_id}`) returns 404; filter the list instead.

---

## Bills of Materials

### `GET /boms` → list of all BOMs
### `GET /boms/{bom_id}` → single BOM

```json
{
  "bom_id": "BOM-300",
  "name": "Retrofit Kit 1",
  "warehouse_id": "WH_WEST",
  "target_date": "2026-05-08",
  "components": [
    {
      "sku": "NW-1049",
      "quantity_per_kit": 8
    }
  ]
}
```

**Fields:**
- `components[].quantity_per_kit` (int): units of this SKU needed per finished kit.
- `warehouse_id` (string): the warehouse where this BOM is typically built.

---

## Incidents

### `GET /incidents` → list of all incidents

```json
{
  "incident_id": "INC-90004",
  "sku": "NW-1031",
  "supplier_id": "SUP-003",
  "warehouse_id": "WH_CENTRAL",
  "incident_type": "WORK_ORDER",
  "severity": "medium",
  "status": "closed",
  "open_date": "2026-02-07",
  "close_date": "2026-03-18",
  "resolution_cost": 4825.98,
  "root_cause": "count_variance"
}
```

**Fields:**
- `incident_type` (enum): `RMA` or `WORK_ORDER`.
- `severity` (enum): `low`, `medium`, `high`, `critical`. "Severe" means `high` or `critical`.
- `status` (enum): `open` or `closed`.
- `open_date` (string): date the incident was opened. Filter window uses this field.
- `close_date` (string or null): date closed. Null for open incidents.
- `resolution_cost` (float): USD cost to resolve the incident.
- `root_cause` (string): `incorrect_pick`, `carrier_damage`, `count_variance`, etc.

Individual incident lookup (`/incidents/{id}`) returns 404; filter the list instead.

---

## Shipping Quote

### `GET /shipping/quote?warehouse_id={id}&destination_zip={zip}&weight_lb={weight}`

```json
{
  "warehouse_id": "WH_CENTRAL",
  "destination_zip": "38247",
  "weight_lb": 12.0,
  "zone_distance": 3,
  "service_days": 2,
  "total_cost": 36.17,
  "base_rate": 33.11,
  "fuel_surcharge_rate": 0.0925,
  "carrier": "Northwind Parcel",
  "speed": "ground"
}
```

**Parameters:**
- `warehouse_id` (string, required): origin warehouse.
- `destination_zip` (string, required): delivery postal code.
- `weight_lb` (float, required): total shipment weight in pounds.

**Response fields used in answers:**
- `zone_distance` (int): shipping zone.
- `service_days` (int): estimated transit days.
- `total_cost` (float): total shipping cost in USD. Use this for `total_cost_usd`.

The `speed` may not match the order's `shipping_speed`; the API returns the quote for the parameters given. The system appears to return a quote regardless of the speed parameter.
