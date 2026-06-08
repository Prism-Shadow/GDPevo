# Release Control Memo

Request: TEST_QUALITY_E order release review

Analysis date: 2026-06-01

Northwind release control is preparing this wave for warehouse handoff. Separate orders that can ship now from orders that need manual release control review or inventory backorder handling.

Use live API records as the authoritative source for orders, customers, products, inventory, suppliers, and incidents. For this release review, high and critical open incidents are treated as active severe incidents. The supplier-risk rollup should cover suppliers represented in the wave by ordered SKUs that are under a supplier quality hold or have an active severe incident on the ordered SKU.

Submit the final answer as JSON only.
