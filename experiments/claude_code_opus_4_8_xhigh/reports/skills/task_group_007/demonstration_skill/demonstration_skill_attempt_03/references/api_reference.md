# Northwind ERP API reference

Read-only JSON over plain HTTP GET. **Base URL: `http://127.0.0.1:8015`** (ignore any other
port a memo mentions). List endpoints return JSON arrays; single-record endpoints return an
object. Responses are key-sorted. Filters are exact string matches; omitting a filter returns
all rows.

Query with `curl -s` or Python `urllib`. Example:
`curl -s "http://127.0.0.1:8015/orders?wave=TRAIN_TRANSFER_B"`

## Endpoints

| Endpoint | Notes |
|---|---|
| `GET /health` | status + manifest: record counts and `generation_timestamp` (dataset clock). |
| `GET /products` / `GET /products/<sku>` | product master. |
| `GET /suppliers` | all suppliers (no single-id endpoint; fetch all and index by id). |
| `GET /customers` / `GET /customers/<customer_id>` | customer master. |
| `GET /warehouses` | 3 warehouses: WH_NORTH, WH_CENTRAL, WH_WEST (id, name, region, zip). |
| `GET /inventory?warehouse_id=&sku=` | inventory rows; both filters optional. |
| `GET /purchase_orders?supplier_id=&sku=&status=` | POs; all filters optional. |
| `GET /orders?wave=&required_date=&customer_id=` / `GET /orders/<order_id>` | orders. |
| `GET /boms` / `GET /boms/<bom_id>` | bills of material. |
| `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | `start`/`end` filter on `open_date`, inclusive ISO string compare. |
| `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | `speed` ∈ {ground, two_day, overnight}, default ground. `weight_lb` must be > 0. Returns the computed quote — do not recompute. |

## Record shapes (key fields)

**product** (`/products/<sku>`):
`sku`, `name`, `category` {electronics, industrial_spares, maintenance_kits, power},
`active` (bool), `supplier_id`, `unit_cost`, `weight_lb`, `safety_stock`, `overstock_threshold`.

**customer** (`/customers/<id>`):
`customer_id`, `name`, `account_status` {active, blocked, review_required},
`risk_flag` {none, credit_watch, fraud_watch}, `tier` {economy, standard, strategic},
`margin_band` {low, medium, high}.

**inventory** (`/inventory` row): `warehouse_id`, `sku`, `on_hand`, `reserved`,
`quarantined`, `last_count_date`. Exactly one row per (warehouse, sku); coverage is complete.

**order** (`/orders/<id>`): `order_id`, `customer_id`, `warehouse_id` (single fulfilling
warehouse), `destination_zip`, `wave`, `priority`, `required_date`, `shipping_speed`,
`lines: [{line_id, sku, quantity, unit_price}, ...]`.

**purchase_order**: `po_id`, `supplier_id`, `sku`, `warehouse_id`, `quantity`,
`status` {open, confirmed, received, cancelled}, `eta`. Eligible coverage = open or confirmed.

**bom** (`/boms/<id>`): `bom_id`, `name`, `warehouse_id`, `target_date`,
`components: [{sku, quantity_per_kit}, ...]`.

**supplier**: `supplier_id`, `name`, `region`, `quality_status` {approved, watch, quality_hold}.

**incident**: `incident_id`, `supplier_id`, `sku`, `warehouse_id`,
`incident_type` {RMA, WORK_ORDER}, `severity` {low, medium, high, critical},
`status` {open, closed}, `open_date`, `close_date` (null when open), `resolution_cost`,
`root_cause`.

**shipping quote** (returned object): `base_rate`, `fuel_surcharge_rate`, `zone_distance`
(int), `service_days` (int), `total_cost` (float), plus echoed inputs.

## Handy Python helper

```python
import urllib.request, json
def get(path):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8015" + path))

def effective_available(wh, sku):
    rows = get(f"/inventory?warehouse_id={wh}&sku={sku}")
    if not rows:
        return 0 - get(f"/products/{sku}")["safety_stock"]
    r = rows[0]; p = get(f"/products/{sku}")
    return r["on_hand"] - r["reserved"] - r["quarantined"] - p["safety_stock"]
```
