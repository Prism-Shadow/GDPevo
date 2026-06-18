# SOP: Expedite / dispatch-queue decision

You get a memo listing specific `order_ids` (the **memo list is the population — not a wave filter**).
For each order produce: inventory status, customer exception, final decision, next action, three SKU
exception lists, and a shipping quote. Output sorted by `order_id`; money 2 dp.

## Data to pull
- `GET /orders/<id>` for each memo order (warehouse, destination_zip, shipping_speed, lines).
- `GET /products` (active, safety_stock, weight_lb).
- `GET /customers` (account_status, risk_flag).
- `GET /inventory` (on_hand, reserved, quarantined per sku+warehouse).
- `GET /shipping/quote` per order.

## Per-line classification (at the order's own warehouse)
Use **effective availability** (see SKILL.md). For each line:
- `effective = on_hand - reserved - quarantined - safety_stock` at the order's warehouse.
- `shortage`  if `effective < quantity`.
- `low_stock` if `effective >= quantity` and `effective < safety_stock`.
- `ready`     otherwise.
- Separately, if `product.active == false`, the SKU is **inactive**.

Collect three sorted, de-duplicated SKU lists per order:
- `shortage_skus`  — lines classified shortage.
- `low_stock_skus` — lines classified low_stock. **Report these even if the order is overall a shortage.**
- `inactive_skus`  — lines whose product is inactive.

A SKU can be both inactive and a shortage; list it in both lists as applicable.

## Order-level `inventory_status` (precedence, first match)
1. inactive present AND any shortage → `inactive_and_shortage`
2. inactive present → `inactive_sku`
3. any shortage → `shortage`
4. any low_stock → `low_stock`
5. else → `ready`

## `customer_exception` (precedence, first match)
1. `account_status == blocked` → `account_blocked`
2. `risk_flag == fraud_watch` → `fraud_watch`
3. `risk_flag == credit_watch` → `credit_watch`
4. `account_status == review_required` → `review_required`
5. else → `none`

(Use exactly the enum values the template allows.)

## `final_decision` / `next_action` (customer gating BEFORE inventory)
Evaluate top-down, first match wins:

| Condition | final_decision | next_action |
|---|---|---|
| account_blocked | reject_hold | hold_credit_or_fraud |
| fraud_watch | reject_hold | hold_credit_or_fraud |
| credit_watch | manual_review | hold_credit_or_fraud |
| review_required | manual_review | send_account_review |
| any inactive SKU | manual_review | escalate_product_master |
| any shortage | backorder | create_backorder |
| any low_stock (no shortage) | delayed_release | delay_and_monitor |
| ready, no exception | ship_now | release_to_pick |

Note the corrected inventory split: an order with a low_stock line but **no** shortage line is
`delayed_release`; once any line is a true shortage (effective < quantity) the order is `backorder`.
This is where using effective (not gross) changes the outcome — a line that gross-could-cover but whose
effective is below quantity makes the order a backorder, not a delayed_release.

## Shipping quote
- weight = sum over ALL order lines of `quantity * product.weight_lb`.
- speed = the order's own `shipping_speed`, unless the memo tells you a specific speed for that order.
- `zone_distance`, `service_days` from the response as integers; `total_cost_usd = round(total_cost, 2)`.
- Provide a quote for every order even if its decision is not ship (memos commonly ask for the quote
  regardless).

## Summary
Recompute from your rows:
- `order_count` = number of orders.
- `decision_counts` = count per final_decision value (the five-key object; must sum to order_count).
- `total_shipping_cost_usd` = sum of the 2-dp per-order totals, 2 dp.
- `blocked_order_ids` = orders with final_decision `reject_hold` (account/fraud blocked), sorted.
- `manual_review_order_ids` = orders with final_decision `manual_review`, sorted.
- `backorder_order_ids` = orders with final_decision `backorder`, sorted.
- `inactive_sku_order_ids` = orders that have any inactive SKU, sorted.
