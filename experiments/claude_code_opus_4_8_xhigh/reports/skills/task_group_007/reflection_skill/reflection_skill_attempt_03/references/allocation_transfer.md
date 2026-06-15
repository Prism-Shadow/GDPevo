# SOP: Mixed-warehouse allocation / transfer decision file

Classify **every order line** in a wave as `ship`, `transfer`, `backorder`, or `manual_review`; build
transfer requests where another warehouse can clear a shortage without protected stock; list account/risk
blocked orders; roll up per order; summarize. Sort line_actions by `order_id` asc, then `line_id` asc.

## Data to pull
- `GET /orders?wave=<WAVE>` (all orders + lines in the wave).
- `GET /customers` (account_status, risk_flag).
- `GET /products` (active, safety_stock).
- `GET /inventory` (on_hand, reserved, quarantined per sku+warehouse).

## Per-line fields
- `requested_warehouse` = order's `warehouse_id`.
- `requested_effective_available = on_hand - reserved - quarantined - safety_stock` at the requested
  warehouse (signed; report as-is, may be negative). Reserved + quarantined + safety_stock are all
  protected and not freely available.

## Per-line decision precedence (first match)
1. **Account/customer-risk gate (whole order).** If the order's customer triggers an exception, EVERY
   line of that order → `action = manual_review` with the matching `primary_reason`:
   - `account_status == blocked` → `account_blocked`
   - `risk_flag == fraud_watch` → `fraud_watch`
   - `account_status == review_required` → `account_review_required`
   (credit_watch has no reason in this template, so it does not block here unless the template says so.)
2. **Product gate (per line).** `product.active == false` → `manual_review` / `inactive_product`.
3. **Inventory (per line).**
   - `requested_effective_available >= quantity` → `ship`, `ship_quantity = quantity`,
     `primary_reason = none`.
   - else compute `remaining = quantity - max(0, requested_effective_available)` and look for **one**
     other warehouse whose own effective available `>= remaining`:
     - found → `transfer`: `ship_quantity = max(0, requested_effective_available)`,
       `transfer_from = that warehouse`, `transfer_quantity = remaining`, `primary_reason = none`
       (the shortage is cleared by the transfer, so the reason is none).
       Pick the source greedily by most-available, tie-break warehouse_id ascending.
     - none can cover the full remaining → `backorder`:
       `ship_quantity = max(0, requested_effective_available)`,
       `backorder_quantity = remaining`, `primary_reason = insufficient_effective_stock`.

The corrected rule: **backorder lines carry `primary_reason = insufficient_effective_stock`, not `none`.**
`none` is reserved for lines that are cleanly shippable or fully transfer-covered. The reason field
reflects the underlying blocking cause, not the chosen action.

## Transfer requests
One row per transferring line: `order_id`, `line_id`, `sku`, `from_warehouse`, `to_warehouse`
(= requested_warehouse), `quantity` (= transfer_quantity). Sort by `order_id` asc, then `line_id` asc.

## blocked_orders
Orders stopped at the **account / customer-risk** level (blocked, fraud_watch, review_required) — NOT
orders that only have line-level `inactive_product` reviews. Sorted ascending, unique.

## order_rollup `outcome` (per order, from its line actions)
- all lines `ship` → `ready_to_ship`
- all lines `manual_review` → `manual_review`
- only `transfer` (no backorder/manual_review) → `needs_transfer`
- only `backorder` (no transfer/manual_review) → `has_backorder`
- any mix of differing non-uniform actions (e.g. ship+backorder, ship+manual_review, transfer+backorder)
  → `mixed_actions`

Sort by `order_id` asc.

## Summary (recompute from rows)
`total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`,
`blocked_orders` (count), `transfer_units` (sum transfer_quantity), `backorder_units` (sum
backorder_quantity).
