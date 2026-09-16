# Northwind ERP Reference

## API surface

Base URL: `http://task-env:9007/`

Use these public endpoints:

- `GET /orders`
- `GET /orders/{order_id}`
- `GET /customers`
- `GET /customers/{customer_id}`
- `GET /products`
- `GET /products/{sku}`
- `GET /inventory`
- `GET /warehouses`
- `GET /suppliers`
- `GET /purchase_orders`
- `GET /boms`
- `GET /incidents`
- `GET /shipping/quote`

## Endpoint quirks

- `GET /customers/{customer_id}` and `GET /products/{sku}` work.
- For inventory, purchase orders, incidents, and suppliers, use the list endpoint and filter locally; item endpoints are not reliable.
- The quote endpoint expects `warehouse_id`, `destination_zip`, `weight_lb`, and `speed`.

## Shared formulas

- `effective_available = on_hand - reserved - quarantined`
- `free_to_ship = effective_available - safety_stock`
- `shipping_weight_lb = sum(line.quantity * product.weight_lb)`
- `shipping_cost = quote.total_cost`
- `zone_distance` and `service_days` come from the quote response

## Common joins

- Orders -> customers by `customer_id`
- Orders -> products by line `sku`
- Orders -> inventory by `sku` and `warehouse_id`
- Products -> suppliers by `supplier_id`
- BOM components -> products by `sku`
- Incidents -> suppliers by `supplier_id`
- Purchase orders -> suppliers, products, and warehouses by their IDs

## Decision patterns

- Dispatch tasks usually classify each order line from customer status, product active flag, and local effective stock.
- Replenishment tasks usually compute demand from BOMs, then apply target stock, timely POs, transfers, and purchases in that order.
- Supplier scorecards usually filter on `open_date`, then aggregate by supplier and apply the request's policy precedence.

## Working rule

- Keep all output JSON exact to the current template.
- Sort arrays exactly as the template says.
- Do not reuse field names from a different task family unless the template uses them.
