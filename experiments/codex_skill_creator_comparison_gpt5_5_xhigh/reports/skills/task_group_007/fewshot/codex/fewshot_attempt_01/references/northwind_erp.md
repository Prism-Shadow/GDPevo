# Northwind ERP Reference

## Live API Map

- `GET /orders`: Order header and line data, including `order_id`, `customer_id`, `warehouse_id`, `destination_zip`, `shipping_speed`, `priority`, `wave`, and `lines[]`.
- `GET /customers`: Customer master data, including `customer_id`, `account_status`, `risk_flag`, `tier`, and `margin_band`.
- `GET /products`: Product master data, including `sku`, `active`, `supplier_id`, `safety_stock`, `overstock_threshold`, `weight_lb`, and `unit_cost`.
- `GET /inventory`: Warehouse stock by `sku` and `warehouse_id`, with `on_hand`, `reserved`, `quarantined`, and `last_count_date`.
- `GET /warehouses`: Warehouse master data, including `warehouse_id`, `zip`, and `region`.
- `GET /suppliers`: Supplier master data, including `supplier_id`, `name`, and `quality_status`.
- `GET /purchase_orders`: Purchase order coverage by `po_id`, `sku`, `warehouse_id`, `supplier_id`, `status`, `eta`, and `quantity`.
- `GET /boms`: BOM headers with `bom_id`, `name`, `warehouse_id`, `target_date`, and `components[]`.
- `GET /incidents`: Incident records with `incident_id`, `supplier_id`, `sku`, `incident_type`, `severity`, `status`, `open_date`, `close_date`, and `resolution_cost`.
- `GET /shipping/quote`: Quote by `warehouse_id`, `destination_zip`, `weight_lb`, and optional `speed`. The response includes `zone_distance`, `service_days`, `total_cost`, and shipping metadata.

## Core Formulas

- Effective availability: `on_hand - reserved - quarantined - safety_stock`.
- Shipping weight: `sum(quantity * product.weight_lb)` across all lines in the order or build.
- Timely PO coverage: open or confirmed POs with matching `sku` and `warehouse_id` whose `eta` is on or before the needed date.
- Incident duration: `close_date - open_date` for closed incidents, otherwise `analysis_date - open_date`.

## Decision Gates

- Treat `account_status = blocked` and `risk_flag` values such as `credit_watch` or `fraud_watch` as customer-risk blocks when the template asks for blocking decisions.
- Treat `account_status = review_required` as manual review rather than an automatic release.
- Treat `active = false` on a product as an item-level stop for automatic shipping or replenishment.
- Treat `quality_status = quality_hold` as a hard supplier-control warning and `quality_status = watch` as softer risk.
- Treat `severity` values of `high` and `critical` as severe for incident scorecards.

## Planning Rules

- For transfer planning, use only usable effective stock at the source warehouse and never count protected stock as transferable.
- For line-level allocation, ship only the portion the requested warehouse can clear; transfer or backorder the uncovered remainder according to the template rules.
- For replenishment, reduce the component gap with timely PO coverage before creating purchase requisitions.
- For incident scorecards, filter on the memo's date window exactly as written and keep supplier summaries sorted by `supplier_id`.

## Quote Handling

- Pass the order's `warehouse_id`, `destination_zip`, and total weight to `/shipping/quote`.
- Set `speed` from the order when the task asks for a shipping quote tied to an order's requested shipping speed.
- Map the returned `total_cost` to the template field name when the output expects `total_cost_usd`.
