# Northwind Components ERP API Reference

Base URL is supplied by the task runner as `<TASK_ENV_BASE_URL>` (or `$TASK_ENV_BASE_URL`).
All endpoints are GET-only. Authentication is not required.

## Endpoints

### GET /products

Returns the full product master list.

Each record:

| Field | Type | Notes |
|---|---|---|
| sku | string | Primary key (e.g. "NW-1000") |
| name | string | Human-readable name |
| category | string | electronics, industrial_spares, maintenance_kits, power, ... |
| active | boolean | false means inactive/discontinued |
| supplier_id | string | "SUP-NNN" |
| unit_cost | number | USD |
| weight_lb | number | Pounds |
| safety_stock | integer | Minimum buffer before reorder |
| overstock_threshold | integer | Above this is overstock |

### GET /products/{sku}

Single product record, or 404.

### GET /inventory

Returns every (sku, warehouse_id) row. Each record:

| Field | Type | Notes |
|---|---|---|
| sku | string | |
| warehouse_id | string | WH_NORTH, WH_CENTRAL, WH_WEST |
| on_hand | integer | Physical count |
| reserved | integer | Held for other orders |
| quarantined | integer | Unsellable |
| last_count_date | string | YYYY-MM-DD |

Effective available = `on_hand - reserved - quarantined`.
Stock below `safety_stock` is low-stock (but not necessarily shortage).
Stock above `overstock_threshold` is overstock.

### GET /inventory/{sku}

Returns inventory records for a single SKU across all warehouses (list), or 404.

### GET /warehouses

Three warehouses:

| warehouse_id | name | region | zip |
|---|---|---|---|
| WH_NORTH | New Jersey Regional Warehouse | Northeast | 07102 |
| WH_CENTRAL | Illinois Central Warehouse | Midwest | 60607 |
| WH_WEST | Nevada West Warehouse | West | 89502 |

### GET /warehouses/{warehouse_id}

Single warehouse record, or 404.

### GET /orders

All orders. Each record:

| Field | Type | Notes |
|---|---|---|
| order_id | string | "SO-NNNNN" |
| customer_id | string | "CUST-NNNN" |
| warehouse_id | string | Warehouse fulfilling |
| priority | string | normal, high |
| wave | string | Wave identifier (may differ from current task wave) |
| shipping_speed | string | overnight, two_day, ground |
| destination_zip | string | 5-digit |
| required_date | string | YYYY-MM-DD |
| lines | list | Array of line objects |

Each line:

| Field | Type |
|---|---|
| line_id | integer |
| sku | string |
| quantity | integer |
| unit_price | number (USD) |

### GET /orders/{order_id}

Single order, or 404.

### GET /customers

All customer records. Each:

| Field | Type | Notes |
|---|---|---|
| customer_id | string | "CUST-NNNN" |
| name | string | |
| tier | string | strategic, standard, economy |
| account_status | string | active, blocked, review_required |
| risk_flag | string | none, fraud_watch, credit_watch |
| margin_band | string | high, medium, low |

### GET /customers/{customer_id}

Single customer, or 404.

### GET /suppliers

12 suppliers (SUP-001 through SUP-012). Each:

| Field | Type | Notes |
|---|---|---|
| supplier_id | string | "SUP-NNN" |
| name | string | |
| region | string | Northeast, Midwest, South, West |
| quality_status | string | approved, watch, quality_hold |

### GET /suppliers/{supplier_id}

Single supplier, or 404.

### GET /purchase_orders

All POs. Each:

| Field | Type |
|---|---|
| po_id | string ("PO-NNNNN") |
| sku | string |
| supplier_id | string |
| warehouse_id | string |
| quantity | integer |
| status | string: open, confirmed, received, cancelled |
| eta | string (YYYY-MM-DD) |

For replenishment tasks, "timely" POs are those with status *open* or *confirmed* and eta <= the build date.

### GET /purchase_orders/{po_id}

Single PO, or 404.

### GET /boms

All bills of materials. Each:

| Field | Type |
|---|---|
| bom_id | string ("BOM-NNN") |
| name | string |
| warehouse_id | string |
| target_date | string (YYYY-MM-DD) |
| components | list of {sku, quantity_per_kit} |

### GET /boms/{bom_id}

Single BOM, or 404.

### GET /incidents

All quality incidents. Each:

| Field | Type |
|---|---|
| incident_id | string ("INC-NNNNN") |
| supplier_id | string |
| sku | string |
| warehouse_id | string |
| incident_type | string: RMA, WORK_ORDER |
| severity | string: low, medium, high, critical |
| status | string: open, closed |
| open_date | string (YYYY-MM-DD) |
| close_date | string or null (YYYY-MM-DD or null for open) |
| resolution_cost | number (USD) |
| root_cause | string |

### GET /incidents/{incident_id}

Single incident, or 404.

### GET /shipping/quote

**Required query params:**

| Param | Type | Example |
|---|---|---|
| warehouse_id | string | WH_CENTRAL |
| destination_zip | string | 38247 |
| weight_lb | number | 123.45 |
| speed | string | overnight, two_day, ground |

Response:

| Field | Type |
|---|---|
| carrier | string |
| warehouse_id | string |
| destination_zip | string |
| weight_lb | number |
| speed | string |
| zone_distance | integer |
| service_days | integer |
| total_cost | number (USD) |
| base_rate | number |
| fuel_surcharge_rate | number |

## Helper Script

Import `northwind_api.py` for deterministic fetch, math, and classification functions:

```python
from northwind_api import (
    get_json, fetch_index, fetch_one, index_by,
    effective_available, usable_for_transfer, inventory_lookup,
    warehouse_effective_availabilities,
    product_weight, order_total_weight,
    classify_customer, classify_inventory_status,
    shortage_skus, inactive_skus, low_stock_skus,
    get_shipping_quote, shipping_quote_for_order,
    timely_pos, timely_po_quantity,
    filter_incidents_by_date, incident_duration_days, group_incidents_by_supplier,
    bom_component_totals,
    expedite_decision, EXPEDITE_DECISION_TABLE,
    allocation_primary_reason, is_allocation_blocked,
    usd, pct1, dur,
)
```
