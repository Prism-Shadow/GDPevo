# Northwind ERP API Reference

This reference covers the data model returned by each endpoint and the common patterns for extracting decision-relevant fields.

## Endpoints and data model

### GET /manifest

Returns the list of available endpoints. Always call first to confirm the environment.

```json
{
  "endpoints": ["/orders", "/products", "/inventory", ...]
}
```

### GET /orders

Returns all orders. Each order has:

```json
{
  "order_id": "SO-10001",
  "customer_id": "CUST-1001",
  "warehouse_id": "WH_NORTH",
  "order_date": "2026-05-20",
  "status": "open",
  "lines": [
    {
      "line_id": 1,
      "sku": "SK-X001",
      "quantity": 5
    }
  ],
  "shipping": {
    "speed": "overnight",
    "carrier": "FleetEx"
  }
}
```

Key fields for decisions:
- `order_id` — primary key
- `customer_id` — links to customer record for exception checks
- `warehouse_id` — drives inventory lookups and shipping quotes
- `lines` — each line's SKU and quantity drive inventory checks
- `status` — typically "open" for control-desk tasks

### GET /orders/{order_id}

Returns a single order. Same shape as the list entry. Use when you need detail on specific orders.

### GET /products

Returns all products. Each product has:

```json
{
  "sku": "SK-X001",
  "name": "Torque Sensor Module",
  "category": "sensor",
  "is_active": true,
  "unit_cost": 245.00,
  "supplier_id": "SUP-A01"
}
```

Key fields:
- `sku` — primary key, links to order lines and inventory
- `is_active` — `false` means the SKU is discontinued; affected lines get `inactive_sku` status
- `unit_cost` — used for purchase requisition cost calculations
- `supplier_id` — links to supplier record

### GET /products/{product_id}

Returns a single product. `{product_id}` is the SKU string.

### GET /inventory

Returns all inventory records. Each record has:

```json
{
  "sku": "SK-X001",
  "warehouse_id": "WH_NORTH",
  "physical_qty": 120,
  "reserved_qty": 35,
  "quarantine_qty": 5,
  "buffer_qty": 10,
  "effective_available": 70
}
```

Key fields:
- `effective_available` — the number you use for decision-making. Already subtracts reserved, quarantine, and buffer from physical. **Do not subtract further.**
- Negative `effective_available` means the SKU is in shortage at that warehouse.

### GET /inventory/{sku}

Returns inventory records for one SKU across all warehouses. Same shape per record.

### GET /warehouses

Returns all warehouses:

```json
{
  "warehouse_id": "WH_NORTH",
  "name": "North Distribution Center",
  "zone": 3,
  "address": {...}
}
```

Key fields:
- `warehouse_id` — primary key (WH_NORTH, WH_CENTRAL, WH_WEST)
- `zone` — used in shipping quote calculations

### GET /warehouses/{warehouse_id}

Returns a single warehouse record.

### GET /customers

Returns all customers. Each customer has:

```json
{
  "customer_id": "CUST-1001",
  "name": "Apex Manufacturing",
  "account_status": "active",
  "credit_hold": false,
  "fraud_watch": false,
  "review_required": false
}
```

Key fields:
- `account_status` — "active", "blocked", "suspended"
- `credit_hold` — true means the account is on credit hold
- `fraud_watch` — true means the account is flagged for fraud
- `review_required` — true means the account needs manual review

Classification mapping:
- `account_status` = "blocked" → `account_blocked`
- `fraud_watch` = true → `fraud_watch`
- `credit_hold` = true → `credit_watch`
- `review_required` = true → `review_required`
- None of the above → `none`

### GET /customers/{customer_id}

Returns a single customer record.

### GET /suppliers

Returns all suppliers:

```json
{
  "supplier_id": "SUP-A01",
  "name": "Acme Component Supply",
  "quality_status": "approved",
  "contact": {...}
}
```

Key fields:
- `quality_status` — "approved", "watch", "quality_hold"

### GET /suppliers/{supplier_id}

Returns a single supplier record.

### GET /purchase_orders

Returns all purchase orders. Each PO has:

```json
{
  "po_id": "PO-50066",
  "supplier_id": "SUP-B02",
  "warehouse_id": "WH_WEST",
  "sku": "SK-X003",
  "quantity": 335,
  "unit_cost": 85.00,
  "status": "confirmed",
  "order_date": "2026-05-01",
  "expected_delivery": "2026-06-03"
}
```

Key fields:
- `status` — "open", "confirmed", "received", "cancelled". For replenishment, only "open" and "confirmed" are eligible.
- `expected_delivery` — must be on or before the build date for "timely" coverage.
- `warehouse_id` — must match the target build warehouse for direct coverage.

### GET /purchase_orders/{po_id}

Returns a single PO record.

### GET /boms

Returns all bills of materials:

```json
{
  "bom_id": "BOM-100",
  "name": "Retrofit Kit 1",
  "components": [
    {"sku": "SK-X003", "quantity_per_kit": 5},
    {"sku": "SK-X004", "quantity_per_kit": 12}
  ]
}
```

Key fields:
- `components` — each has `sku` and `quantity_per_kit`. Total required = build_quantity × quantity_per_kit.

### GET /boms/{bom_id}

Returns a single BOM record.

### GET /incidents

Returns all incidents. Each incident has:

```json
{
  "incident_id": "INC-90004",
  "supplier_id": "SUP-A01",
  "sku": "SK-X002",
  "type": "RMA",
  "severity": "high",
  "open_date": "2026-01-15",
  "close_date": "2026-02-20",
  "resolution_cost": 4500.00,
  "status": "closed"
}
```

Key fields:
- `type` — "RMA" or "WORK_ORDER"
- `severity` — "low", "medium", "high", "critical"
- `open_date` — date filter field for time-windowed analysis
- `close_date` — null for open incidents
- `resolution_cost` — cost to resolve the incident
- `status` — "open" or "closed"

### GET /incidents/{incident_id}

Returns a single incident record.

### GET /shipping/quote

Returns a shipping quote. Query parameters: warehouse_id, shipping_speed, destination details.

```json
{
  "zone_distance": 3,
  "service_days": 1,
  "total_cost_usd": 1234.56
}
```

Key fields for answer templates:
- `zone_distance` — integer
- `service_days` — integer
- `total_cost_usd` — number, round to 2 decimal places

## Numeric precision rules

Every answer template specifies precision. Follow these rules:

| Value type | Precision | Format |
|-----------|-----------|--------|
| Currency (USD) | 2 decimal places | `12345.67` |
| Percentages | 1 decimal place | `23.7` |
| Average duration | 2 decimal places | `58.22` |
| Counts | integer | `38` |
| Zone distance | integer | `3` |
| Service days | integer | `2` |

When computing averages, compute to full precision first, then round at the end to the specified decimal places. For percentages, compute as (count / total × 100) then round to 1 decimal place.

## Sorting conventions

When a template says "sort ascending by X", use string comparison for string fields and numeric comparison for numeric fields. Apply tie-breakers in the order given. For example, "sort by order_id ascending, then line_id ascending" means primary sort on order_id, secondary on line_id.
