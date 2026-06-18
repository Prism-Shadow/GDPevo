# SOP: Expedite / dispatch queue decision

**Shape of task:** a memo lists order ids for a wave and asks for a release / hold / review /
backorder decision per order plus a shipping quote, then a wave summary. Output is
`{wave_id, records[], summary}`.

## Per-order inputs

For each order id in the memo (process the live `/orders/<id>` record):
1. Fetch the order, its `/customers/<customer_id>`, and for every line the `/products/<sku>`
   and the `/inventory?warehouse_id=<order.warehouse_id>&sku=<sku>` row.
2. Classify each line with the shared rules:
   - `effective_available = on_hand - reserved - quarantined - safety_stock`
   - shortage if `eff < line.quantity`; else low_stock if `eff < safety_stock`; else ready.
   - inactive if `product.active == false` (independent of stock).
3. Build the three SKU sets (deduped, sorted ascending):
   - `shortage_skus` = SKUs with shortage.
   - `inactive_skus` = SKUs whose product is inactive (a SKU can be in both lists).
   - `low_stock_skus` = SKUs that are coverable but below safety stock.

## inventory_status (order-level rollup of its lines)

Let `has_short`, `has_inactive`, `has_low` be whether any line hit that condition.
- `inactive_and_shortage` if `has_inactive and has_short`
- else `inactive_sku` if `has_inactive`
- else `shortage` if `has_short`
- else `low_stock` if `has_low`
- else `ready`

## customer_exception

Derive from the customer using the shared precedence (blocked → fraud_watch → credit_watch →
review_required → none). Allowed values: `none`, `review_required`, `account_blocked`,
`fraud_watch`, `credit_watch`.

## final_decision and next_action

Apply in this precedence (account/risk first, then inventory). Account exceptions override
inventory entirely.

| Condition (first match wins) | final_decision | next_action |
|---|---|---|
| customer_exception is `account_blocked` or `fraud_watch` | `reject_hold` | `hold_credit_or_fraud` |
| customer_exception is `review_required` or `credit_watch` | `manual_review` | `send_account_review` |
| (account clean) inventory_status includes inactive (`inactive_sku` / `inactive_and_shortage`) | `manual_review` | `escalate_product_master` |
| (account clean) inventory_status is `shortage` | `backorder` | `create_backorder` |
| (account clean) inventory_status is `low_stock` | `delayed_release` | `delay_and_monitor` |
| (account clean) inventory_status is `ready` | `ship_now` | `release_to_pick` |

Notes on the inferred rows (observed training waves exercised the account-exception, shortage,
and inactive-and-shortage paths directly; the `ship_now`/`delayed_release`/
`escalate_product_master` rows are the consistent extension of the same precedence and the
template's enums). If a clean-account order has inactive lines, route to product-master
escalation; only fall through to backorder/delay/ship when nothing higher applies.

## shipping_quote (every record, even non-release decisions)

Quote **always**, regardless of decision — a hold/backorder order still reports its quote.
- weight = `sum(line.quantity * product.weight_lb)`.
- speed = the order's `shipping_speed` (NOT what a note asks for).
- `GET /shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>&weight_lb=<weight>&speed=<speed>`.
- Emit `{zone_distance (int), service_days (int), total_cost_usd (round 2dp)}`.

## summary

Compute from your records:
- `order_count` = number of records.
- `decision_counts` = object with a count for each of the 5 final_decision values (include
  zeros).
- `total_shipping_cost_usd` = sum of all `total_cost_usd`, rounded to 2 dp.
- `blocked_order_ids` = orders with final_decision `reject_hold` (account-blocked/fraud).
- `manual_review_order_ids` = orders with final_decision `manual_review`.
- `backorder_order_ids` = orders with final_decision `backorder`.
- `inactive_sku_order_ids` = orders whose `inactive_skus` list is non-empty.
- All id lists sorted ascending.

`records` sorted by `order_id` ascending.

## Pitfalls
- Quoting at a note's requested speed instead of `order.shipping_speed`.
- Forgetting that an inactive SKU also counts toward `shortage_skus` when it is short.
- Letting an inactive line outrank an account review (account review wins).
- Dropping the shipping quote on non-ship decisions (it is still required).
