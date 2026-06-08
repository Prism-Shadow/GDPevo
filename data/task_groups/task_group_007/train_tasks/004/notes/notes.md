# train_004 Notes

## English

Task `train_004` belongs to scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and `E003` as the construction basis. The task follows the assigned brief for a mixed-warehouse allocation task for wave `TRAIN_TRANSFER_B`. It uses the shared Northwind Components ERP environment under `task_group/task_group_007/env/` through the public API surfaces documented in the environment README. The only task-local payloads are `input/payloads/allocation_memo.md` and `input/payloads/answer_template.json`.

The solver-visible business request asks for a line-level allocation decision file. The expected work is to inspect `/orders?wave=TRAIN_TRANSFER_B`, customer master records, product master records, warehouse inventory, and warehouse information as needed. The solver must return a JSON object with `line_actions`, `transfer_requests`, `blocked_orders`, `order_rollup`, and `summary`. The task is intentionally not a tutorial: the memo names the action vocabulary and operational context but does not provide the hidden effective-stock calculation or final routing precedence.

This task fits the group because it combines fulfillment control and allocation, two of the recurring operation families in the design. It exercises the same object relationships as the test tasks: orders reference customers and products; inventory is per warehouse and SKU; customer and product statuses can override otherwise available stock; transfer decisions require comparing the requested warehouse to alternate warehouse stock.

Material map:

- `input/prompt.txt`: the user-facing request and environment entry point.
- `input/payloads/allocation_memo.md`: desk context, wave id, action vocabulary, and output intent.
- `input/payloads/answer_template.json`: controlled output schema, enum choices, ordering rules, numeric units, and required fields.
- Shared API `/orders?wave=TRAIN_TRANSFER_B`: order lines, requested warehouse, required date, destination, priority, and quantities.
- Shared API `/customers/<customer_id>`: account status and risk flag used for manual-review overrides.
- Shared API `/products/<sku>`: product status and product-level safety stock used for release and effective availability.
- Shared API `/inventory?warehouse_id=&sku=`: on-hand, reserved, quarantined, and warehouse-specific stock state.
- Shared API `/warehouses`: warehouse identifiers and names for transfer source/destination validation.

Solution basis: effective available stock is calculated as `on_hand - reserved - quarantined - product.safety_stock`. Account-level overrides are applied before automatic allocation: `account_status=blocked`, `account_status=review_required`, and `risk_flag=fraud_watch` make all lines on the order `manual_review`. Product `active=false` creates a line-level `manual_review` with reason `inactive_product` when there is no stronger account-level override. For releasable active lines, if the requested warehouse effective availability covers the full quantity, the action is `ship`; if requested availability is short but another single warehouse can cover the uncovered balance, the action is `transfer`; otherwise the action is `backorder`. For transfer lines, usable requested-warehouse quantity remains `ship_quantity`, and the transfer covers only the remaining quantity.

The standard answer contains 13 orders and 31 lines. The transfer requests are `SO-70001` line 1, `SO-70050` line 2, and `SO-70085` line 1. The account-blocked order set is `SO-70008`, `SO-70022`, `SO-70029`, `SO-70057`, `SO-70064`, and `SO-70078`. Summary counts are 8 direct ship lines, 3 transfer lines, 2 backorder lines, 18 manual-review lines, 51 transfer units, and 49 backorder units.

Evaluation uses exact-match checks over structured JSON only. Raw scoring weights sum to 17:

- SP1 `wave_id` and complete line action set, weight 2.
- SP2 manual-review line set and primary reasons, weight 3.
- SP3 direct ship line set and ship quantities, weight 2.
- SP4 transfer request set with source, destination, SKU, and quantity, weight 3.
- SP5 backorder line set, quantities, and reason, weight 2.
- SP6 requested-warehouse effective availability values for all lines, weight 2.
- SP7 order rollup outcomes and account-blocked order set, weight 2.
- SP8 summary counts and unit totals, weight 1.

Likely model pitfalls include treating on-hand as available, failing to subtract safety stock, using quarantined or reserved units, applying transfer before account overrides, missing the fraud-watch customer override, treating inactive products as shippable, or backordering the full line when a partial requested-warehouse quantity can ship with a transfer for the balance.

Transfer design: as a train task, `train_004` anchors the effective-stock convention, transfer candidate selection, line-level versus order-level manual review, and customer/account override precedence. Comparing an attempted solution to `output/answer.json` should help a skill-builder infer how later test tasks should handle stale inventory, protected stock, customer holds, and mixed outcomes without exposing those answers in solver-visible input.

Construction record: author `train_004` task-builder subagent; created 2026-06-01; updated 2026-06-01. Major changes: created solver prompt, allocation memo, answer template, standard answer, exact-match evaluator, and notes for `TRAIN_TRANSFER_B`.

