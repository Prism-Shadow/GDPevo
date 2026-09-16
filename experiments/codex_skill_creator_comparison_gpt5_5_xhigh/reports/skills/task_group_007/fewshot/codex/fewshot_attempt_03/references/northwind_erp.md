# Northwind ERP Reference

## Collections
- `GET /products`: product master data. Key fields: `sku`, `active`, `supplier_id`, `safety_stock`, `overstock_threshold`, `unit_cost`, `weight_lb`.
- `GET /inventory`: stock rows. Query by `sku` and optionally `warehouse_id` when helpful.
- `GET /orders`: sales orders with `order_id`, `wave`, `warehouse_id`, `customer_id`, `shipping_speed`, `destination_zip`, and `lines[]`.
- `GET /customers`: account state with `account_status`, `risk_flag`, `tier`, `margin_band`.
- `GET /suppliers`: supplier master with `quality_status`.
- `GET /purchase_orders`: PO rows with `po_id`, `sku`, `status`, `eta`, `quantity`, `supplier_id`, `warehouse_id`.
- `GET /boms`: kit definitions with `bom_id`, `name`, `warehouse_id`, `target_date`, `components[]`.
- `GET /incidents`: supplier incidents with `incident_id`, `incident_type`, `status`, `severity`, `open_date`, `close_date`, `resolution_cost`, `supplier_id`, `sku`.
- `GET /shipping/quote`: requires `warehouse_id`, `destination_zip`, and `weight_lb`. Response includes `zone_distance`, `service_days`, `speed`, and `total_cost`.

## Working Method
- Fetch collections and filter locally when the API does not narrow the response enough.
- Build lookup maps by `sku`, `order_id`, `customer_id`, `supplier_id`, `po_id`, or `bom_id` as needed.
- Use the request payload as the source of truth for which records matter and how to sort the final output.

## Core Calculations
- Effective stock per warehouse = `on_hand - reserved - quarantined - product.safety_stock`.
- Order quote weight = sum of `line.quantity * product.weight_lb` across all lines.
- Timely PO coverage = same-warehouse open or confirmed purchase orders with ETA on or before the required date.
- Use the template's precision for currency, percentages, and durations.

## Common Output Checks
- Keep required keys only.
- Preserve the template's list ordering.
- Sort nested SKU, PO, incident, and order id lists ascending unless the template says otherwise.
- Round monetary values only at the final output stage.
