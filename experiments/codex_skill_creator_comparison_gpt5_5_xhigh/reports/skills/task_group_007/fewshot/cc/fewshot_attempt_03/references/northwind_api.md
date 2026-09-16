# Northwind ERP API Reference

Use the task-provided base URL. The root endpoint often lists the available routes, and `/health` is a quick connectivity check.

## Endpoints
- `GET /orders?wave=&required_date=&customer_id=`
- `GET /orders/<order_id>`
- `GET /customers/<customer_id>`
- `GET /products/<sku>`
- `GET /inventory?warehouse_id=&sku=`
- `GET /warehouses`
- `GET /purchase_orders?supplier_id=&sku=&status=`
- `GET /suppliers`
- `GET /boms/<bom_id>`
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`

## Common fields
- orders: `order_id`, `wave`, `warehouse_id`, `destination_zip`, `required_date`, `shipping_speed`, `customer_id`, `lines[]`
- lines: `line_id`, `sku`, `quantity`, `unit_price`
- customers: `account_status`, `risk_flag`, `tier`, `name`
- products: `active`, `supplier_id`, `unit_cost`, `weight_lb`, `safety_stock`, `overstock_threshold`
- inventory: `on_hand`, `reserved`, `quarantined`, `last_count_date`
- purchase orders: `po_id`, `status`, `eta`, `quantity`, `sku`, `supplier_id`, `warehouse_id`
- incidents: `incident_id`, `status`, `open_date`, `close_date`, `incident_type`, `severity`, `resolution_cost`, `supplier_id`, `sku`, `warehouse_id`
- boms: `bom_id`, `name`, `warehouse_id`, `target_date`, `components[]`
- shipping quotes: `carrier`, `zone_distance`, `service_days`, `total_cost`

## Calculation notes
- Effective availability = `on_hand - reserved - quarantined`.
- Closed incident duration = `close_date - open_date` in calendar days.
- Open incident duration = `analysis_date - open_date` in calendar days.
- Incident percentage = `incident_count / filtered population * 100`.
- Ship, transfer, backorder, and review rollups should come from the line or item decisions, not memory.
- When looking for PO coverage, use the memo or template's allowed status and date rules rather than a universal assumption.
