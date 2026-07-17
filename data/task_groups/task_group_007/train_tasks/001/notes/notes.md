# train_001 Notes

## English

Data/source lineage: This task belongs to `SCN_007_erp_inventory_order_fulfillment` and uses source examples `E001`, `E002`, and `E003` as scenario references. The task is built from the shared `task_group_007` Northwind Components ERP environment, especially the public API endpoints for orders, customers, products, inventory, warehouses, and shipping quotes. The task-local payload is `input/payloads/expedite_queue_memo.json`, which selects eight orders from wave `TRAIN_EXPEDITE_A`.

Task definition: The solver acts as dispatch control for an expedite queue. The visible task asks for a structured JSON answer matching `input/payloads/answer_template.json`. For each selected order, the solver must inspect the live order, customer account, product master, warehouse inventory, and shipping quote. The required output records inventory status, customer exception, final fulfillment decision, next action, SKU exception lists, and parcel quote fields. Records are sorted by `order_id`; currency is rounded to two decimals.

Scenario fit: The task is a real ERP fulfillment-control workflow. It combines order lines, warehouse stock, safety stock, quarantined and reserved quantities, customer account state, product active flags, shipping speed, destination zone, and final release decisions. This directly matches the task group's fulfillment-control family and anchors conventions needed by later test tasks.

Material map: `env/README.md` documents the API entry points. `/orders/<order_id>` or `/orders?wave=TRAIN_EXPEDITE_A` supplies order lines, warehouse, required date, shipping speed, and destination ZIP. `/customers/<customer_id>` supplies account status and risk flags. `/products/<sku>` supplies active status, safety stock, and weight. `/inventory?warehouse_id=&sku=` supplies on-hand, reserved, quarantined, and last-count data. `/warehouses` supplies origin ZIPs. `/shipping/quote` calculates zone distance, service days, and total cost for the order's warehouse, destination ZIP, total line weight, and requested shipping speed.

Solution and evaluation basis: The standard answer uses effective availability as `on_hand - reserved - quarantined - safety_stock`. A line is a shortage when that effective value is below ordered quantity. A covered line is low stock when the remaining effective quantity after the order is less than the SKU safety stock. Inactive SKUs come from the product master. Account statuses override final release: blocked accounts become `reject_hold`; review-required accounts become `manual_review`; otherwise shortages become `backorder`; otherwise an order can release or delay according to fulfillment state. Shipping quote total weight is the sum of product `weight_lb * quantity`; quote fields are exact API results rounded to cents.

Scoring has eight exact-match points with raw weights: `SP001_order_set_and_count` weight 1; `SP002_inventory_statuses_and_shortages` weight 3; `SP003_inactive_and_low_stock_sku_sets` weight 2; `SP004_customer_exceptions` weight 2; `SP005_final_decisions` weight 3; `SP006_next_actions` weight 2; `SP007_shipping_quotes` weight 2; `SP008_summary_rollups` weight 2. Likely model pitfalls include using `on_hand - reserved` without quarantined or safety stock, treating open stock as available despite inactive product status, letting inventory availability override blocked/review customer status, using the wrong shipping speed or total weight, and omitting low-stock warnings for covered lines.

Transfer design: This is a train task, not a tutorial. After attempting it and comparing with the answer, a skill-builder can infer the fulfillment-control SOP: reconstruct effective stock from several fields, keep SKU shortage/inactive/low-stock exceptions separate from the final order decision, treat customer account state as a release override, and use the shipping quote endpoint rather than approximating freight. These conventions transfer to `test_001`, `test_004`, and the integrated `test_005` board.

Construction record: Author `train_001` task-builder subagent. Created and updated on 2026-06-01. Major changes: created formal prompt, answer template, queue memo, standard answer, evaluator, and bilingual notes for the eight-order `TRAIN_EXPEDITE_A` expedite queue.

## 中文

数据/来源脉络：本任务属于 `SCN_007_erp_inventory_order_fulfillment`，以源示例 `E001`、`E002`、`E003` 作为场景参照。任务使用 `task_group_007` 共享的 Northwind Components ERP 环境，重点使用订单、客户、产品、库存、仓库和运输报价等公开 API。任务本地载荷是 `input/payloads/expedite_queue_memo.json`，其中从 `TRAIN_EXPEDITE_A` 波次中选出八个订单。

任务定义：求解者扮演发运控制人员，处理一个加急队列。可见任务要求输出符合 `input/payloads/answer_template.json` 的结构化 JSON。每个订单都需要检查实时订单、客户账户、产品主数据、仓库库存和运输报价。输出包括库存状态、客户异常、最终履约决策、下一步动作、SKU 异常列表和包裹报价字段。记录按 `order_id` 升序排列，金额保留两位小数。

场景适配：该任务是典型 ERP 履约控制流程，结合了订单行、仓库库存、安全库存、隔离数量、预留数量、客户账户状态、产品启用标记、运输速度、目的地区域和最终放行决策。这与任务组中的履约控制类任务一致，也为后续测试任务提供可迁移规则。

材料地图：`env/README.md` 说明 API 入口。`/orders/<order_id>` 或 `/orders?wave=TRAIN_EXPEDITE_A` 提供订单行、仓库、需求日期、运输速度和目的地邮编。`/customers/<customer_id>` 提供账户状态和风险标记。`/products/<sku>` 提供启用状态、安全库存和重量。`/inventory?warehouse_id=&sku=` 提供现有量、预留量、隔离量和盘点日期。`/warehouses` 提供起运地邮编。`/shipping/quote` 根据仓库、目的地邮编、总重量和订单要求的运输速度计算区域距离、服务天数和总费用。

解答和评价依据：标准答案使用有效可用量 `on_hand - reserved - quarantined - safety_stock`。若有效可用量小于订购数量，则该行是短缺。若某行可覆盖，但扣除订单后剩余有效量低于 SKU 安全库存，则标为低库存。停用 SKU 来自产品主数据。账户状态覆盖最终放行：冻结账户为 `reject_hold`，需复核账户为 `manual_review`；无账户阻断时，短缺为 `backorder`，否则根据履约状态放行或延迟。运输报价总重量为产品 `weight_lb * quantity` 的合计，报价字段取 API 精确结果并按美分四舍五入。

评分包含八个精确匹配点，原始权重为：`SP001_order_set_and_count` 权重 1；`SP002_inventory_statuses_and_shortages` 权重 3；`SP003_inactive_and_low_stock_sku_sets` 权重 2；`SP004_customer_exceptions` 权重 2；`SP005_final_decisions` 权重 3；`SP006_next_actions` 权重 2；`SP007_shipping_quotes` 权重 2；`SP008_summary_rollups` 权重 2。常见陷阱包括只用 `on_hand - reserved` 而忽略隔离量和安全库存，将停用产品当作可发，忽略客户冻结/复核状态的覆盖作用，使用错误的运输速度或重量，以及遗漏已覆盖行的低库存警示。

迁移设计：这是一个训练任务，不是教程。求解并对照答案后，技能构建者可以归纳履约控制 SOP：从多个字段重建有效库存，把 SKU 短缺、停用和低库存异常与订单最终决策分开，客户账户状态优先影响放行，并使用运输报价端点而不是粗略估算运费。这些规则可迁移到 `test_001`、`test_004` 和综合 `test_005` 看板任务。

构建记录：作者为 `train_001` task-builder subagent。创建和更新日期为 2026-06-01。主要变更：为八订单 `TRAIN_EXPEDITE_A` 加急队列创建正式提示、答案模板、队列备忘录、标准答案、评估器和双语说明。
