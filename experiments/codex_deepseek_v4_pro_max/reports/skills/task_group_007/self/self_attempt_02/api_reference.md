## Northwind ERP API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided by the task runner at runtime).
All endpoints are read-only GET. No authentication required.

### Forbidden Endpoints

Do not call under any circumstances:
- `/health`
- Any `/reset` or `/reseed` endpoint
- Any `/judge` endpoint

### List Endpoints

Return JSON arrays of all records.

| Endpoint | Response Fields |
|---|---|
| `GET /manifest` | Array of available endpoint paths |
| `GET /products` | `[{sku, product_name, is_active, unit_price, supplier_id, ...}]` |
| `GET /inventory` | `[{sku, warehouse_id, quantity_on_hand, reserved, quarantined, ...}]` |
| `GET /warehouses` | `[{warehouse_id, name, ...}]` |
| `GET /orders` | `[{order_id, customer_id, lines: [{line_id, sku, quantity, warehouse_id, ...}], ...}]` |
| `GET /customers` | `[{customer_id, name, account_status, risk_flags, ...}]` |
| `GET /suppliers` | `[{supplier_id, name, quality_status, ...}]` |
| `GET /purchase_orders` | `[{po_id, supplier_id, sku, warehouse_id, quantity, status, delivery_date, unit_cost, ...}]` |
| `GET /boms` | `[{bom_id, kit_name, components: [{sku, quantity_per_kit}], ...}]` |
| `GET /incidents` | `[{incident_id, supplier_id, sku, type, severity, status, open_date, close_date, resolution_cost, ...}]` |

### Entity-Scoped Endpoints

Return a single JSON object (or 404 if not found).

| Endpoint | Path Parameter |
|---|---|
| `GET /products/{product_id}` | `product_id` = SKU string |
| `GET /inventory/{sku}` | `sku` = SKU string (returns all warehouse records for that SKU) |
| `GET /warehouses/{warehouse_id}` | `warehouse_id` = e.g. `WH_NORTH` |
| `GET /orders/{order_id}` | `order_id` = e.g. `SO-70000` |
| `GET /customers/{customer_id}` | `customer_id` = e.g. `CUST-1001` |
| `GET /suppliers/{supplier_id}` | `supplier_id` = e.g. `SUP-003` |
| `GET /purchase_orders/{po_id}` | `po_id` = e.g. `PO-5000` |
| `GET /boms/{bom_id}` | `bom_id` = e.g. `BOM-300` |
| `GET /incidents/{incident_id}` | `incident_id` = e.g. `INC-100` |

### Shipping Quote

`GET /shipping/quote` — Returns an object with `{zone_distance, service_days, total_cost_usd}`.

### Query Strategy

1. Call list endpoints first to gather broad data (e.g. `GET /orders` for all orders, `GET /products` for all products).
2. Use entity-scoped endpoints for specific lookups when the list is large or when you need a single record.
3. Call `/manifest` if unsure which endpoints are available.
4. Filter and join data client-side — the API does not support query parameters beyond path segments.
