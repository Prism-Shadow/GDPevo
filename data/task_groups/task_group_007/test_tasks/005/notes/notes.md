# test_005 Notes

## English

This hidden construction note documents `test_005`, an integrated daily operations board for wave `TEST_BOARD_F` in `task_group_007`. It belongs to `SCN_007_erp_inventory_order_fulfillment` and combines the three recurring task families: fulfillment control, replenishment gaps, and supplier incident escalation.

The solver-visible materials are `input/prompt.txt`, `input/payloads/daily_board_memo.json`, `input/payloads/answer_template.json`, and the shared ERP API. The solver must inspect current order, customer, product, inventory, supplier, purchase-order, and incident data through public API endpoints rather than reading hidden env files. The output is a structured board with per-order decisions, replenishment gaps, incident escalations, ranked priority actions, and summary counts.

Material map: `/orders?wave=TEST_BOARD_F` defines the order population; `/customers` provides account and risk fields; `/products` provides active status, supplier ID, safety stock, cost, and weight; `/inventory` supports effective availability; `/incidents` and `/suppliers` support the escalation section. The local board memo fixes the board date, wave, risk supplier IDs, and allowed decision enums. The solution first builds one evidence row per order, then assigns the most specific decision: customer-risk orders become `customer_hold`, inactive product evidence becomes `data_review`, supplier quality exposure becomes `quality_review`, pure stock gaps become `backorder_or_replenish`, and only clean orders are `release`.

Evaluation uses eight exact-match scoring points with total raw weight 18: board identity (1), per-order decisions (3), reason codes and risk suppliers (3), replenishment gap lines (3), incident escalation suppliers (2), ranked priority actions (2), summary counts (2), and integrated consistency across decisions, shortage lines, and escalation suppliers (2). The evaluator compares each section at field level and returns a structured zero-score JSON for malformed or incomplete predictions rather than raising missing-key errors. The task is intentionally integrated: a direct solver may discover some facts locally, but high-value points benefit from train-derived experience about effective stock, customer overrides, incident filtering, supplier quality control, stable sorting, and controlled JSON output.

Solution basis: the board has twelve orders. `SO-70005` and `SO-70082` are customer holds; `SO-70047` is the only clean release; `SO-70054` is a stock-only replenishment case; `SO-70061` and `SO-70075` require data review because inactive products are involved; the remaining quality-review orders carry supplier-risk evidence from `SUP-003`, `SUP-006`, or `SUP-010`. The replenishment gap section includes only actual shortage lines after effective availability is computed. Incident escalations use the same three supplier-quality metrics as `train_005`, and priority actions are ranked as quality holds first, replenishment next, and customer-hold clearance third.

Transfer anchors: `train_001` anchors fulfillment and customer overrides; `train_002` anchors shortage and replenishment reasoning; `train_003` anchors incident aggregation; `train_004` anchors effective availability and allocation decisions; `train_005` anchors supplier quality controls. Task-specific difficulty comes from the larger `TEST_BOARD_F` order set and the need to combine three operation families in one board.

Construction record: authored as a task-builder rework for `test_005`; created and updated on 2026-06-01.

