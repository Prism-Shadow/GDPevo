# SOP: Mixed-warehouse allocation wave

**Shape of task:** classify every order **line** in a wave as ship / transfer / backorder /
manual_review, emit single-source transfer requests, list account-blocked orders, roll each
order up to an outcome, and summarize. Output is
`{wave_id, line_actions[], transfer_requests[], blocked_orders[], order_rollup[], summary}`.

## Scope

Enumerate the wave's orders from the live API: `GET /orders?wave=<WAVE>`. The memo usually
does **not** list order ids — trust the wave membership. Process every line of every order.

## Per-line classification (in this order)

For each line, with `requested_warehouse = order.warehouse_id`:

1. **Account / product gate (manual_review)** — these stop the line before any stock math:
   - If the order's customer has an account/risk exception (blocked / fraud_watch /
     credit_watch / review_required), **every line of that order** is `manual_review` with
     `primary_reason` = `account_blocked`, `fraud_watch`, or `account_review_required`
     (map credit_watch to `account_review_required` if a dedicated reason is absent — use the
     template's allowed values). The order goes in `blocked_orders`.
   - Else if the line's `product.active == false`, that **single line** is `manual_review`
     with `primary_reason = inactive_product`. This does **not** block the order; other lines
     are decided normally (order can be `mixed_actions`). Do **not** add it to `blocked_orders`.

2. **Stock math (when the line is not gated):**
   - `req_eff = effective_available(requested_warehouse, sku)` (report this as
     `requested_effective_available`, negative allowed).
   - `ship_qty = min(line.quantity, max(req_eff, 0))`.
   - `shortfall = line.quantity - ship_qty`.
   - If `shortfall == 0` → **ship**: `ship_quantity = ship_qty`, others 0,
     `primary_reason = none`.
   - Else look for **one** other warehouse to cover the *entire* shortfall:
     - Compute `effective_available` at each other warehouse; consider only those with a
       positive value `>= shortfall`. Pick the warehouse with the **highest** effective
       availability. → **transfer**: `ship_quantity = ship_qty`, `transfer_from = <that wh>`,
       `transfer_quantity = shortfall`, `primary_reason = none`.
     - If **no single** warehouse can cover the full shortfall → **backorder**:
       `ship_quantity = 0`, `backorder_quantity = line.quantity` (the **full** line quantity,
       not the shortfall), `primary_reason = insufficient_effective_stock`.

   This is "single-source, all-or-nothing" transfer: unlike the kit-replenishment SOP, you do
   not split a line across multiple source warehouses, and a coverable line ships its usable
   requested-warehouse quantity while transferring the remainder.

`primary_reason` allowed values: `none`, `account_blocked`, `account_review_required`,
`fraud_watch`, `inactive_product`, `insufficient_effective_stock`.

## transfer_requests

One entry per line whose action is `transfer`:
`{order_id, line_id, sku, from_warehouse, to_warehouse=requested_warehouse, quantity=transfer_quantity}`.
Sort by `order_id` then `line_id` ascending.

## blocked_orders

Orders stopped at the **account / customer-risk** level (account_blocked, fraud_watch,
account_review_required / credit_watch). **Not** orders that only have product-inactive line
reviews. Sorted ascending, unique.

## order_rollup (one entry per order)

Roll up the set of line actions for the order:
- all lines `ship` → `ready_to_ship`
- all lines `manual_review` → `manual_review`
- actions are a subset of {ship, transfer} (at least one transfer) → `needs_transfer`
- any line is `manual_review` mixed with non-review actions → `mixed_actions`
- otherwise (a `backorder` mixed with ship/transfer, no review) → `has_backorder`

(Equivalently: pure-ship→ready_to_ship; pure-review→manual_review; ship/transfer only→
needs_transfer; review present with other actions→mixed_actions; else backorder present→
has_backorder.) Sort by `order_id` ascending. Outcomes allowed: `ready_to_ship`,
`needs_transfer`, `has_backorder`, `manual_review`, `mixed_actions`.

## summary (all integers, from your records)

`total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`,
`manual_review_lines`, `blocked_orders` (count), `transfer_units` (sum of transfer_quantity),
`backorder_units` (sum of backorder_quantity).

`line_actions` sorted by `order_id` then `line_id` ascending.

## Pitfalls
- Splitting a backorder across two partial sources — transfers here are single-source and must
  cover the **whole** shortfall, or it is a backorder.
- Backordering the shortfall instead of the **full line quantity**.
- Putting product-inactive orders into `blocked_orders` (only account/risk orders go there).
- Forgetting that a clean-account order with one inactive line is `mixed_actions`, not
  `manual_review`.
- Using cached snapshot quantities instead of live `/inventory` (the memo explicitly warns
  against this).
