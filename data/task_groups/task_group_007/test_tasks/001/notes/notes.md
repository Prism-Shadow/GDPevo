# test_001 Hidden Notes

## English

Data/source lineage: This task belongs to `SCN_007_erp_inventory_order_fulfillment` and uses source examples `E001`, `E002`, and `E003` as the distributional basis. The specific brief is `test_001`: priority order wave `TEST_PRIORITY_D` with a stale local inventory extract that conflicts with the live ERP API. Shared environment data comes from `task_group/task_group_007/env/` through public API endpoints only. Task-local visible payloads are `priority_wave_memo.md`, `priority_wave_TEST_PRIORITY_D_inventory_extract.csv`, and `answer_template.json`.

Task definition: The solver must evaluate every order returned by `/orders?wave=TEST_PRIORITY_D`, reconcile customer, product, inventory, and shipping records, and produce final fulfillment decisions, inventory statuses, controlled exception reasons, blocking SKUs, shipping quote values, next actions, and summary counts. The stale extract is deliberately optimistic for several SKUs and must not be used as the final source for live stock decisions.

Scenario fit: The task exercises the fulfillment-control family in the task group. It combines ERP order state, customer account state, live warehouse inventory, product safety stock, and shipping economics. This mirrors the source examples' cross-system reconciliation and final operational decision work while adding a realistic source conflict between a local extract and a live API.

Material map: `/orders?wave=TEST_PRIORITY_D` provides the order set, lines, warehouse, destination ZIP, priority, required date, and shipping speed. `/customers/<customer_id>` supplies account status, margin band, and risk flags. `/products/<sku>` supplies product weight and safety stock. `/inventory?warehouse_id=&sku=` supplies live on-hand, reserved, and quarantined quantities. `/shipping/quote` supplies the scored shipping cost and service days. The CSV extract supplies stale planning quantities and is useful mainly as a conflict source.

Solution and evaluation basis: Live effective availability is computed as `on_hand - reserved - quarantined - safety_stock`. An order is `SHORTAGE` if any line's live effective availability is below required quantity, `LOW_STOCK_COVERED` if all lines are covered but at least one line has fewer than 10 units left after allocation, and `AVAILABLE` otherwise. Account status and risk exceptions override ordinary release. Blocked accounts become `REJECT_ACCOUNT_HOLD`; review-required, fraud-watch, credit-watch, and high-shipping-cost low-margin cases become `MANUAL_REVIEW`; uncovered inventory without a stronger override becomes `BACKORDER_INVENTORY`; low-stock covered orders become `DELAY_STOCK_WATCH`; otherwise the decision is `RELEASE_TO_SHIP`. High shipping cost is flagged for active low-margin customers when `shipping_cost / order_revenue > 0.12`.

The standard answer contains 13 order records. Scoring is exact-match with 8 weighted points: SP1 all final decisions weight 3; SP2 all inventory statuses weight 2; SP3 all per-order exception reason sets weight 3; SP4 all blocking SKU sets weight 2; SP5 shipping cost and service days for every order weight 1; SP6 order, decision, and inventory summary counts weight 1; SP7 manual-review, backorder, and rejected order sets weight 2; SP8 exception reason counts weight 2. Total raw weight is 16. Numeric shipping costs are rounded to cents.

Transfer design: This test is anchored by `train_001` and `train_004`. `train_001` anchors customer override handling, shipping quote use, and final decision enums. `train_004` anchors live effective stock reconstruction and allocation-status classification. The transfer-dependent high-value points are SP1, SP2, SP3, and SP4. Task-specific exploration difficulty comes from the 13-order wave, multi-line orders, stale local extract conflicts, and live API reconciliation.

Likely model pitfalls: trusting the stale CSV instead of live inventory, omitting safety stock from effective availability, treating open stock as available despite quarantines or reservations, missing risk-flag overrides, failing to compute shipping quotes from total order weight, and returning free-text reason labels instead of controlled enums.

Construction record: Author `task-builder subagent test_001`; created 2026-06-01; updated 2026-06-01. Major changes: created the full test task folder, added stale local extract, produced hidden answer, and implemented exact-match scoring.

## Chinese

数据来源：本任务属于 `SCN_007_erp_inventory_order_fulfillment`，基于源示例 `E001`、`E002`、`E003` 的业务分布。任务简报是 `test_001`：处理优先订单波次 `TEST_PRIORITY_D`，其中本地库存抽取文件已经过期，并且与实时 ERP API 冲突。共享环境数据只能通过公开 API 使用；任务可见材料包括 `priority_wave_memo.md`、`priority_wave_TEST_PRIORITY_D_inventory_extract.csv` 和 `answer_template.json`。

任务定义：求解者需要评估 `/orders?wave=TEST_PRIORITY_D` 返回的全部订单，核对客户、产品、库存和运输报价，输出最终履约决策、库存状态、受控异常原因、阻塞 SKU、运输成本、服务天数、下一步动作和汇总统计。本地 CSV 是有意设置的过期计划抽取，不能作为最终库存依据。

场景适配：该任务属于履约控制类工作流，要求综合 ERP 订单、客户账户、实时仓库库存、产品安全库存和运输经济性，符合源示例中的跨系统核对与运营决策特征，同时加入了本地材料与实时系统冲突的真实办公复杂度。

材料地图：`/orders?wave=TEST_PRIORITY_D` 提供订单集合和订单行；`/customers/<customer_id>` 提供账户状态、利润档位和风险标记；`/products/<sku>` 提供重量和安全库存；`/inventory?warehouse_id=&sku=` 提供实时库存、预留和隔离数量；`/shipping/quote` 提供评分所需运输成本和服务天数；CSV 主要用于制造来源冲突。

答案与评估依据：实时有效库存计算为 `on_hand - reserved - quarantined - safety_stock`。若任一订单行有效库存不足，则订单库存状态为 `SHORTAGE`；若全部覆盖但分配后任一行剩余少于 10 件，则为 `LOW_STOCK_COVERED`；否则为 `AVAILABLE`。账户与风险异常优先于普通放行。冻结账户为 `REJECT_ACCOUNT_HOLD`；需要复核、欺诈关注、信用关注、高运输成本低利润订单为 `MANUAL_REVIEW`；没有更高优先级异常但库存不足为 `BACKORDER_INVENTORY`；低库存但可覆盖为 `DELAY_STOCK_WATCH`；否则为 `RELEASE_TO_SHIP`。

迁移设计：本测试由 `train_001` 和 `train_004` 锚定。`train_001` 锚定客户覆盖规则、运输报价和最终决策枚举；`train_004` 锚定实时有效库存重建和分配状态判断。高权重点 SP1、SP2、SP3、SP4 依赖训练经验迁移。任务自身难点来自 13 个订单、多行订单、过期抽取与实时 API 冲突以及长流程核对。

常见错误：直接相信 CSV、漏扣安全库存、忽略预留或隔离库存、遗漏客户风险覆盖规则、没有按订单总重量计算运输报价、使用自由文本原因而不是受控枚举。

构造记录：作者 `task-builder subagent test_001`；创建日期 2026-06-01；更新日期 2026-06-01。主要变更：创建完整测试任务目录，加入过期本地库存抽取，生成隐藏标准答案，并实现精确匹配评估器。
