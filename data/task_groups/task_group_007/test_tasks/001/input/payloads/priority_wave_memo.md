# Priority Wave Memo

Wave: TEST_PRIORITY_D

Operations owner: Fulfillment Control Desk

Need: cutoff decision file for all orders in the wave before releasing the next warehouse batch.

Shared ERP API:
- Orders: GET /orders?wave=TEST_PRIORITY_D
- Order detail: GET /orders/<order_id>
- Customers: GET /customers/<customer_id>
- Product master: GET /products/<sku>
- Inventory: GET /inventory?warehouse_id=<warehouse_id>&sku=<sku>
- Shipping quote: GET /shipping/quote?warehouse_id=<warehouse_id>&destination_zip=<zip>&weight_lb=<weight>&speed=<speed>

Local attachment:
- priority_wave_TEST_PRIORITY_D_inventory_extract.csv is an overnight planning extract. It may not reflect current reservations, quarantine changes, or safety-stock decisions.
