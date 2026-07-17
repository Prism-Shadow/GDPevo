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

Construction record: author `train_004` task-builder subagent; created 2026-06-01; updated 2026-06-01. Major changes: created solver prompt, allocation memo, answer template, standard answer, exact-match evaluator, and bilingual notes for `TRAIN_TRANSFER_B`.

## Chinese

任务 `train_004` 属于场景 `SCN_007_erp_inventory_order_fulfillment`，构造依据来自源示例 `E001`、`E002` 和 `E003`。本任务按分配简报设计为 `TRAIN_TRANSFER_B` 波次的混合仓库分配任务，使用共享的 Northwind Components ERP 环境，并通过环境 README 中公开的 API 接口取数。任务本地可见材料只有 `input/payloads/allocation_memo.md` 和 `input/payloads/answer_template.json`。

求解者需要为该波次生成订单行级别的分配决策文件。预期工作包括查询订单波次、客户主数据、产品主数据、仓库库存和仓库信息，并输出包含 `line_actions`、`transfer_requests`、`blocked_orders`、`order_rollup` 和 `summary` 的 JSON。该训练任务不是教程；备忘录只给出动作词表和业务背景，不在可见材料中直接给出隐藏的有效库存公式或最终优先级规则。

本任务符合任务组设计，因为它同时覆盖履约控制和库存调拨两个复用的业务族。订单关联客户和产品，库存按仓库和 SKU 维护，客户或产品状态会覆盖库存可用性，调拨决策需要比较请求仓与其他仓的有效库存，这些对象关系也会在后续测试任务中复用。

材料用途如下：`prompt.txt` 提供用户请求和环境入口；`allocation_memo.md` 提供波次、动作词表和桌面业务背景；`answer_template.json` 定义受控输出结构、枚举、排序规则和字段类型；共享 API 的订单、客户、产品、库存和仓库接口分别用于确定订单行、账户状态、产品状态、安全库存、保留库存、隔离库存和可调拨仓库。

标准答案的依据是：有效可用库存等于 `on_hand - reserved - quarantined - product.safety_stock`。账户级规则先于自动分配执行，`blocked`、`review_required` 和 `fraud_watch` 都会使整单进入 `manual_review`。若没有更强的账户级拦截，产品 `active=false` 会使该行以 `inactive_product` 原因进入人工复核。对可自动释放的有效产品行，若请求仓有效库存足以覆盖全量，则为 `ship`；若请求仓不足但单个其他仓可覆盖缺口，则为 `transfer`；否则为 `backorder`。调拨行中，请求仓可用部分保留为 `ship_quantity`，调拨数量只覆盖剩余缺口。

标准答案包含 13 个订单和 31 个订单行。调拨请求为 `SO-70001` 第 1 行、`SO-70050` 第 2 行和 `SO-70085` 第 1 行。账户级拦截订单为 `SO-70008`、`SO-70022`、`SO-70029`、`SO-70057`、`SO-70064` 和 `SO-70078`。汇总结果为 8 个直接发货行、3 个调拨行、2 个缺货延期行、18 个人工复核行、51 个调拨单位和 49 个缺货单位。

评估器只对结构化 JSON 做精确匹配，原始权重总和为 17：SP1 检查波次和完整行级动作集合，权重 2；SP2 检查人工复核行及原因，权重 3；SP3 检查直接发货行和数量，权重 2；SP4 检查调拨请求集合，权重 3；SP5 检查缺货行和数量，权重 2；SP6 检查所有行的请求仓有效库存，权重 2；SP7 检查订单汇总结果和账户拦截订单集合，权重 2；SP8 检查汇总计数和单位合计，权重 1。

常见错误包括把账面库存直接当作可用库存、没有扣除安全库存、使用已保留或隔离库存、在账户拦截前先做调拨、漏掉欺诈观察客户、把停用产品当作可发货产品，或者在可部分本仓发货加调拨补齐时把整行都延期。

迁移设计：作为训练任务，`train_004` 用于锚定有效库存计算、调拨候选选择、行级和订单级人工复核区别、客户与账户覆盖规则的优先级。求解者在盲做后对照标准答案，应能提炼出后续测试任务所需的库存状态重建、客户拦截、受保护库存和混合结果处理方法。

构造记录：作者为 `train_004` task-builder subagent；创建日期 2026-06-01；更新日期 2026-06-01。主要变更为创建 `TRAIN_TRANSFER_B` 的提示、分配备忘录、答案模板、标准答案、精确匹配评估器和双语说明。
