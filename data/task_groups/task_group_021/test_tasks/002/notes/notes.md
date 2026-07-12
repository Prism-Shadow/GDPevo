# test_002 Notes

## English

### Lineage and task definition

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, with source examples `E001`, `E002`, and `E003`. It implements the product/category normalization family from the group design: analysts must audit messy fleet fuel-card purchases against controlled reference aliases and vehicle master data.

The solver-visible request asks for the August 2026 south-region fuel mismatch audit. The visible materials are `input/prompt.txt`, `input/payloads/answer_template.json`, and the shared AsterOps workbench reachable through `<TASK_ENV_BASE_URL>`. The relevant public environment endpoints are `/api/catalog`, `/api/fleet/purchases`, `/api/fleet/vehicles`, `/api/reference/fuel_aliases`, and `/api/reference/quality_rules`, plus `/downloads/fleet_purchases_export.csv`. The CSV export is a monthly snapshot that can lag the current API records.

### Scenario fit and material map

This is a formal test task in the same distribution as `train_002`: it uses the same fuel alias table, vehicle expected-fuel master data, controlled fuel enums, record status conventions, and structured audit output. It also depends on effective-record habits reinforced by `train_005`, where invalid and superseded rows must be separated before aggregation.

The environment data used here is `env/data/asterops_data.json` exposed through the shared API. `fleet_purchases` supplies the purchase slice, `fleet_vehicles` supplies expected fuel and vehicle exceptions, `reference_fuel_aliases` supplies alias priority and canonical fuel classes, and `reference_quality_rules` documents record status values. The task-local `answer_template.json` only defines the required output shape and ordering rules.

### Solution basis

The target slice is fleet purchases where `region = south` and `purchase_date` is in `2026-08`. There are 15 raw rows in the slice. `FP_S_005` is a void row superseded by amendment `FP_S_006`, so 14 effective records are used for gallon totals.

Fuel product descriptions are normalized using the fuel alias table by priority. This matters for substring traps: `Premium unleaded` and `Super unleaded` must resolve before generic `unleaded`; `Fuel service` and `misc fuel` resolve to selected unknown aliases; `CNG pilot fuel` is unmapped. Effective rows whose observed canonical fuel differs from the vehicle `expected_fuel` are mismatch candidates unless a vehicle-level exception applies. `FP_BG_0110` and `FP_S_011` are purchases for vehicle `S-407`, whose `field_generator` exception keeps them out of the ordinary mismatch queue.

The standard answer is:

- Scope and count: `region = south`, `period = 2026-08`, `purchase_count_evaluated = 14`.
- Mismatch purchases: `FP_BG_0048`, `FP_BG_0200`, `FP_S_002`, `FP_S_006`, `FP_S_009`, `FP_S_010`.
- Exception purchases: `FP_BG_0110`, `FP_S_005`, `FP_S_011`.
- Gallons by fuel: diesel `109.95`, unleaded `0.00`, premium_unleaded `54.20`, electric `0.00`, hybrid `9.30`, unknown `82.31`.
- Vendor mismatch counts: FleetCard `2`, QuickFuel `4`.
- Alias issue counts over effective rows: priority overlap matches `5`, generic unleaded traps `4`, ambiguous unknown matches `3`, unmapped descriptions `1`. `decision_audit` also records lifecycle, vehicle-exception, zero-gallon, and alias-resolution trace evidence.
- Source delta audit: API-only current purchase `FP_S_006`; CSV-only legacy purchase `FP_CSV_S_901`; stale CSV purchase `FP_S_005`; disagreement transactions `TXN-CSV-S-901` and `TXN-S-005`. The CSV records excluded from operational totals are `FP_CSV_S_901` and `FP_S_005`.

### Evaluation

The evaluator has 10 scoring points with raw weights `[2, 3, 3, 3, 3, 2, 3, 3, 3, 3]`, total weight 28.

1. Scope fields, effective purchase count, lifecycle evidence, and source-delta counts, weight 2.
2. Gallons by canonical fuel class plus alias and source-exclusion evidence, rounded to two decimals, weight 3.
3. Mismatch purchase IDs plus alias and source-exclusion evidence, weight 3.
4. Exception purchase IDs plus void/superseded and vehicle-exception evidence, weight 3.
5. Vehicle review queue with expected and observed fuel enums plus audit evidence, weight 3.
6. Vendor mismatch counts, weight 2.
7. Alias issue counts plus alias evidence, weight 3.
8. Nontrivial alias-resolution trace, weight 3.
9. API-vs-CSV source delta ID sets, weight 3.
10. Transaction-level reconciliation plus operations load decision audit for source disagreements, weight 3.

The evaluator exact-matches structured business results. Gallon values are normalized to two decimals before comparison, ID lists are sorted where appropriate, and alias trace rows are normalized to business fields rather than free-form prose.

Likely model pitfalls include trusting a CSV export without checking the current API records, putting CSV-only legacy rows into operational totals, treating `Premium unleaded` or `Super unleaded` as generic `unleaded`, treating `Fuel service` or `misc fuel` as unmapped rather than selected unknown aliases, missing the unmapped `CNG pilot fuel` row, putting exempt `S-407` purchases into the normal mismatch queue, counting the void row in gallons, and omitting zero-valued fuel classes from the gallons object.

### Transfer design

Transfer anchors are `train_002` and `train_005`. From `train_002`, solvers should transfer alias priority matching, generic `unleaded` substring-trap handling, controlled fuel enums, mismatch queue construction, two-decimal fuel aggregation, and lifecycle/alias trace evidence. From `train_005`, solvers should transfer the habit of reconstructing effective records and separating exception or review reasons before computing business totals.

Transfer-dependent scoring points are SP1, SP2, SP3, SP4, SP5, SP7, SP8, SP9, and SP10: canonical gallons by fuel class, mismatch IDs, exception IDs, vehicle review queue, alias issue counts, alias-resolution trace, API-vs-CSV source deltas, transaction-level reconciliation, and operations load/review decisions. Task-specific exploration difficulty comes from the south vendors, the generated August records, the lagging monthly export, the lack of a simple seeded-only slice, and the mixed void/amended, unknown/unmapped, diesel, and exempt-equipment edges.

### Construction record

Author: task-builder subagent for `test_002`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Created the solver prompt, answer template, standard answer, evaluator, and bilingual notes for the south-region August 2026 fleet fuel mismatch audit.

## 中文

### 数据来源和任务定义

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`。它对应任务组设计中的产品和类别标准化工作流：分析员需要把混乱的车队燃油卡采购描述映射到受控燃油类别，并与车辆主数据中的期望燃油类型进行核对。

求解者可见的请求是审计 2026 年 8 月南区燃油采购。可见材料包括 `input/prompt.txt`、`input/payloads/answer_template.json`，以及通过 `<TASK_ENV_BASE_URL>` 访问的共享 AsterOps 工作台。关键环境端点是 `/api/catalog`、`/api/fleet/purchases`、`/api/fleet/vehicles`、`/api/reference/fuel_aliases` 和 `/api/reference/quality_rules`，以及 `/downloads/fleet_purchases_export.csv`。CSV 导出是月度快照，可能落后于当前 API 记录。

### 场景适配和材料地图

这是与 `train_002` 同分布的正式测试任务：它使用相同的燃油别名表、车辆期望燃油主数据、受控燃油枚举、记录状态约定和结构化审计输出。它也依赖 `train_005` 强化过的有效记录处理习惯，即先分离无效和被取代记录，再做汇总。

这里使用的环境数据是通过共享 API 暴露的 `env/data/asterops_data.json`。`fleet_purchases` 提供采购切片，`fleet_vehicles` 提供期望燃油和车辆例外，`reference_fuel_aliases` 提供别名优先级和标准燃油类别，`reference_quality_rules` 说明记录状态值。任务本地的 `answer_template.json` 只定义输出结构和排序规则。

### 标准答案依据

目标范围是 `region = south` 且 `purchase_date` 在 `2026-08` 的燃油采购。该范围内有 15 条原始记录，其中 `FP_S_005` 是被 `FP_S_006` 取代的 void 记录，因此 14 条记录作为有效记录参与加仑数汇总。

燃油描述通过燃油别名表按优先级标准化。关键陷阱包括 `Premium unleaded` 和 `Super unleaded` 必须优先于通用 `unleaded`，`Fuel service` 和 `misc fuel` 是 selected-unknown alias，`CNG pilot fuel` 是未映射描述。有效记录中，实际标准燃油类型与车辆 `expected_fuel` 不一致的记录会成为错配候选；但车辆级例外需要从普通错配队列中分离。`FP_BG_0110` 和 `FP_S_011` 属于 `S-407` 的 `field_generator` 例外，因此不进入普通错配队列。

标准答案包括：

- 范围和数量：`region = south`，`period = 2026-08`，`purchase_count_evaluated = 14`。
- 错配采购：`FP_BG_0048`、`FP_BG_0200`、`FP_S_002`、`FP_S_006`、`FP_S_009`、`FP_S_010`。
- 例外采购：`FP_BG_0110`、`FP_S_005`、`FP_S_011`。
- 各标准燃油类别加仑数：diesel `109.95`，unleaded `0.00`，premium_unleaded `54.20`，electric `0.00`，hybrid `9.30`，unknown `82.31`。
- 供应商错配计数：FleetCard `2`，QuickFuel `4`。
- 有效记录上的别名问题计数：优先级重叠匹配 `5`，通用 unleaded 子串陷阱 `4`，模糊 unknown 匹配 `3`，未映射描述 `1`。`decision_audit` 还记录 lifecycle、车辆例外、零加仑和 alias-resolution trace。
- 源差异审计：API-only 当前采购 `FP_S_006`，CSV-only 历史采购 `FP_CSV_S_901`，过期 CSV 采购 `FP_S_005`，存在差异的交易为 `TXN-CSV-S-901` 和 `TXN-S-005`。从运营汇总排除的 CSV 记录是 `FP_CSV_S_901` 和 `FP_S_005`。

### 评估方式

评估器包含 10 个评分点，原始权重为 `[2, 3, 3, 3, 3, 2, 3, 3, 3, 3]`，总权重 28。

1. 审计范围字段、有效采购数量、lifecycle 证据和源差异计数，权重 2。
2. 按标准燃油类别汇总的加仑数、别名证据和源排除证据，保留两位小数，权重 3。
3. 按指定顺序排列的错配采购 ID、别名证据和源排除证据，权重 3。
4. 按指定顺序排列的例外采购 ID、void/superseded 和车辆例外证据，权重 3。
5. 包含期望燃油和观察燃油枚举的车辆复核队列及审计证据，权重 3。
6. 供应商错配计数，权重 2。
7. 别名问题计数和别名证据，权重 3。
8. 非平凡别名解析 trace，权重 3。
9. API-vs-CSV 源差异 ID 集，权重 3。
10. 源差异交易级 reconciliation 与运营装载决策审计，权重 3。

评估器对结构化业务结果做精确匹配。加仑数在比较前归一化到两位小数。不评分解释文字或证据措辞。

常见模型错误包括只看 CSV 导出而不检查当前 API 记录，把 CSV-only 历史行计入运营汇总，把 `Premium unleaded` 当成通用 `unleaded`，把 `Fuel service` 当成未映射而不是 `unknown`，把有例外的 `S-407` 采购放入普通错配队列，以及在加仑数字段中遗漏零值燃油类别。

### 迁移设计

迁移锚点是 `train_002` 和 `train_005`。从 `train_002` 应迁移燃油别名按优先级匹配、通用 `unleaded` 子串陷阱处理、受控燃油枚举、错配队列构造、保留两位小数的燃油汇总，以及 lifecycle/alias trace 证据的记录方式。从 `train_005` 应迁移先重建有效记录、再将例外或复核原因与业务汇总分离的习惯。

依赖迁移的评分点是 SP1、SP2、SP3、SP4、SP5、SP7、SP8、SP9 和 SP10：标准燃油类别加仑数、错配 ID、例外 ID、车辆复核队列、别名问题计数、alias-resolution trace、API-vs-CSV 源差异、交易级 reconciliation，以及运营装载/复核决策。任务特定探索难度来自南区供应商、生成的 8 月记录、滞后的月度导出、不能只看手工种子记录，以及 void/amended、unknown/unmapped、柴油采购和例外设备混合出现。

### 构建记录

作者：`test_002` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建南区 2026 年 8 月车队燃油错配审计任务的求解提示、答案模板、标准答案、评估器和双语说明。
## Rework addendum / 返工补充

English: The final evaluator binds fuel totals, mismatch decisions, exception decisions, alias issue counts, and alias trace rows to `decision_audit` purchase evidence for alias-priority matches, generic-unleaded traps, unknown/unmapped aliases, lifecycle records, vehicle exceptions, and zero-gallon rows. Later rework added API-vs-CSV reconciliation evidence and `operations_load_decision_audit` for API-only current records, stale CSV rows, CSV-only legacy rows, disagreement transactions, and resulting load/review owner decisions. This was added after direct calibration showed the original fuel task was too easy, while keeping the added fields as concrete business evidence.

中文：最终评测器将燃料汇总、错配判断、例外判断、别名问题计数和别名 trace 行绑定到 `decision_audit` 的采购证据，包括别名优先级匹配、通用 `unleaded` 陷阱、未知/未映射别名、lifecycle 记录、车辆例外和零加仑行。后续返工加入了 API-vs-CSV reconciliation 证据和 `operations_load_decision_audit`，包括 API-only 当前记录、过期 CSV 行、CSV-only 历史行、存在差异的交易，以及由此产生的装载/复核负责方决策。该返工是因为 direct calibration 显示原始燃料测试过于容易，同时新增字段仍是具体业务证据。
