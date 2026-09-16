# Northwind ERP API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided by the task runner)
Authentication: none
All endpoints: read-only GET

---

## Collection endpoints

Every collection endpoint returns a JSON array of all records. No pagination, no filters.

| Endpoint | Returns | Key fields |
|---|---|---|
| `GET /orders` | All sales orders | `order_id`, `customer_id`, `warehouse_id`, `destination_zip`, `priority`, `required_date`, `shipping_speed`, `wave`, `lines[]` |
| `GET /products` | All product master records | `sku`, `name`, `category`, `active`, `unit_cost`, `weight_lb`, `supplier_id`, `safety_stock`, `overstock_threshold` |
| `GET /customers` | All customer accounts | `customer_id`, `name`, `account_status`, `risk_flag`, `tier`, `margin_band` |
| `GET /inventory` | All warehouse x SKU stock records | `sku`, `warehouse_id`, `on_hand`, `reserved`, `quarantined`, `last_count_date` |
| `GET /warehouses` | All warehouse definitions | `warehouse_id`, `name`, `region`, `zip` |
| `GET /suppliers` | All supplier records | `supplier_id`, `name`, `quality_status`, `region` |
| `GET /purchase_orders` | All purchase orders | `po_id`, `sku`, `supplier_id`, `warehouse_id`, `quantity`, `status`, `eta` |
| `GET /boms` | All BOM definitions | `bom_id`, `name`, `warehouse_id`, `target_date`, `components[]` |
| `GET /incidents` | All quality incidents | `incident_id`, `supplier_id`, `sku`, `warehouse_id`, `incident_type`, `severity`, `status`, `open_date`, `close_date`, `resolution_cost`, `root_cause` |

---

## Single-record endpoints

| Endpoint | Notes |
|---|---|
| `GET /orders/{order_id}` | Returns the single order object. |
| `GET /inventory/{sku}` | Returns an **array** of inventory records for that SKU across all warehouses. |
| `GET /warehouses/{warehouse_id}` | Returns the single warehouse object. |
| `GET /customers/{customer_id}` | Returns the single customer object. |
| `GET /suppliers/{supplier_id}` | Returns the single supplier object. |
| `GET /purchase_orders/{po_id}` | Returns the single PO object. |
| `GET /boms/{bom_id}` | Returns the single BOM object with its `components` array. |
| `GET /incidents/{incident_id}` | Returns the single incident object. |

Note: `GET /products/{product_id}` is not implemented. Use `GET /products` and filter client-side by SKU.

---

## Shipping quote endpoint

```
GET /shipping/quote?warehouse_id={id}&destination_zip={zip}&weight_lb={weight}
```

All three query parameters are required.

### Response fields

| Field | Type | Meaning |
|---|---|---|
| `warehouse_id` | string | Origin warehouse |
| `destination_zip` | string | Destination ZIP |
| `weight_lb` | number | Total shipment weight in pounds |
| `carrier` | string | Carrier name (always "Northwind Parcel") |
| `speed` | string | Shipping speed used |
| `base_rate` | number | Base rate before fuel surcharge |
| `fuel_surcharge_rate` | number | Fuel surcharge as decimal (e.g., 0.0925) |
| `total_cost` | number | All-in quote cost (base + surcharge) |
| `service_days` | integer | Transit days |
| `zone_distance` | integer | Shipping zone distance |

### Usage for order shipping quotes

1. Get the order's `warehouse_id`, `destination_zip`, and `lines[]`.
2. Look up each line's `sku` in products to get `weight_lb`.
3. Sum `weight_lb * quantity` across all lines for total weight.
4. Call the quote endpoint with the three required params.
5. Use `total_cost`, `service_days`, and `zone_distance` from the response.

The API currently ignores shipping speed as a query parameter — all calls return ground-zone results. Use the returned `total_cost` directly.

---

## Recommended fetch strategy

```python
import requests, json

BASE = "<TASK_ENV_BASE_URL>"

orders         = requests.get(f"{BASE}/orders").json()
products       = {p["sku"]: p for p in requests.get(f"{BASE}/products").json()}
customers      = {c["customer_id"]: c for c in requests.get(f"{BASE}/customers").json()}
inventory_list = requests.get(f"{BASE}/inventory").json()
warehouses     = {w["warehouse_id"]: w for w in requests.get(f"{BASE}/warehouses").json()}
suppliers      = {s["supplier_id"]: s for s in requests.get(f"{BASE}/suppliers").json()}
pos            = requests.get(f"{BASE}/purchase_orders").json()
boms           = {b["bom_id"]: b for b in requests.get(f"{BASE}/boms").json()}
incidents      = requests.get(f"{BASE}/incidents").json()
```

Build an inventory lookup keyed by `(warehouse_id, sku)` for efficient access. For tasks that only need specific orders, filter by `wave` or `order_id` from the memo before processing.
