# Allocation Desk Memo

Wave: TRAIN_TRANSFER_B

The allocation desk needs line-level decisions for the mixed-warehouse transfer review. Use current ERP API records rather than any cached inventory snapshot. Customer and product master statuses are part of the release decision. Inventory quantities that are already reserved, quarantined, or held as normal operating buffer should not be treated as freely available for the wave.

Allowed line actions:

- `ship`: the requested warehouse can release the full line quantity.
- `transfer`: the requested warehouse cannot clear the line alone, but another warehouse can cover the remaining quantity without using protected stock.
- `backorder`: the line cannot be cleared from current effective stock.
- `manual_review`: account, risk, or product status prevents automatic release.

For transfer lines, choose one source warehouse for the uncovered quantity and leave any usable requested-warehouse quantity as `ship_quantity`.
