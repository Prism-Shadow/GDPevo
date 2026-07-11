# train_002 Notes

## English

### Lineage and task definition

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, with source examples `E001`, `E002`, and `E003`. It implements the product/category normalization family from the group design: analysts must audit messy fleet fuel-card purchases against controlled reference aliases and vehicle master data.

The solver-visible request asks for the July 2026 north-region fuel mismatch audit. The visible materials are `input/prompt.txt`, `input/payloads/answer_template.json`, and the shared AsterOps workbench reachable through `<TASK_ENV_BASE_URL>`. The relevant public environment endpoints are `/api/catalog`, `/api/fleet/purchases`, `/api/fleet/vehicles`, `/api/reference/fuel_aliases`, and `/api/reference/quality_rules`, plus `/downloads/fleet_purchases_export.csv`. The CSV export is a monthly snapshot that can lag the current API records.

### Solution basis

The target slice is fleet purchases where `region = north` and `purchase_date` is in `2026-07`. There are 14 raw rows in the slice. `FP_N_005` is a void row superseded by amendment `FP_N_006`, so 13 effective purchase records are evaluated for totals and mismatch review.

Fuel product descriptions are normalized using the fuel alias table by priority. This matters for substring traps: `Premium unleaded` must resolve to `premium_unleaded`, not generic `unleaded`; `Unleaded regular` resolves to `unleaded`; `Renewable Diesel B20` resolves to `diesel`. Effective rows whose observed canonical fuel differs from the vehicle `expected_fuel` are mismatch candidates unless a vehicle-level exception applies. For this task, `field_generator` vehicle exceptions keep `FP_BG_0147` and `FP_BG_0198` out of the vehicle mismatch queue. The void/superseded row `FP_N_005` is also listed in `exception_purchase_ids`.

The standard answer is:

- Scope and count: `region = north`, `period = 2026-07`, `purchase_count_evaluated = 13`.
- Mismatch purchases: `FP_BG_0113`, `FP_BG_0131`, `FP_BG_0169`, `FP_BG_0190`, `FP_N_002`.
- Exception purchases: `FP_BG_0147`, `FP_BG_0198`, `FP_N_005`.
- Gallons by fuel: diesel `105.09`, unleaded `174.35`, premium_unleaded `19.91`, electric `29.55`, hybrid `0.00`, unknown `0.00`.
- Vendor mismatch counts: ChargeNet `2`, FleetCard `1`, FuelHub `1`, QuickFuel `1`.
- Alias issue counts over effective rows: priority overlap matches `8`, generic unleaded traps `7`, ambiguous unknown matches `0`, unmapped descriptions `0`. `decision_audit` also records void, amended, superseded, vehicle-exception, zero-gallon, and alias-resolution trace evidence.
- Source delta audit: API-only current purchase `FP_N_006`; CSV-only legacy purchase `FP_CSV_N_901`; stale CSV purchase `FP_N_005`; disagreement transactions `TXN-CSV-N-901` and `TXN-N-005`. The CSV records excluded from operational totals are `FP_CSV_N_901` and `FP_N_005`.

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

Likely model pitfalls include trusting CSV exports without checking current API records, treating amended rows as ordinary duplicates, putting CSV-only legacy rows into operational totals, matching the generic `unleaded` alias before specific aliases, counting vehicle exceptions as mismatch queue items, and omitting zero-valued fuel classes from the gallons object.

### Transfer design

As a train task, this produces transferable experience for later fleet and category-normalization tasks. Comparing a blind attempt to the answer should teach that product aliases need priority matching, status/amendment records must be reconstructed before aggregation, controlled enum values matter, exception records should be separated from ordinary mismatches rather than silently dropped, source exports should be reconciled against the current API before operational totals are trusted, and `decision_audit` should preserve lifecycle plus alias trace evidence.

### Construction record

Author: task-builder subagent for `train_002`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Created the solver prompt, answer template, standard answer, evaluator, and bilingual notes for the north-region July 2026 fleet fuel mismatch audit.

## 中文

### 数据来源和任务定义

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`。它对应任务组设计中的产品和类别标准化工作流：分析员需要把混乱的车队燃油卡采购描述映射到受控燃油类别，并与车辆主数据中的期望燃油类型进行核对。

求解者可见的请求是审计 2026 年 7 月北区燃油采购。可见材料包括 `input/prompt.txt`、`input/payloads/answer_template.json`，以及通过 `<TASK_ENV_BASE_URL>` 访问的共享 AsterOps 工作台。关键环境端点是 `/api/catalog`、`/api/fleet/purchases`、`/api/fleet/vehicles`、`/api/reference/fuel_aliases` 和 `/api/reference/quality_rules`，以及 `/downloads/fleet_purchases_export.csv`。CSV 导出是月度快照，可能落后于当前 API 记录。

### 标准答案依据

目标范围是 `region = north` 且 `purchase_date` 在 `2026-07` 的燃油采购。该范围内有 14 条原始记录。`FP_N_005` 是被修正记录 `FP_N_006` 取代的 void 记录，因此用于汇总和错配审计的有效采购记录数为 13。

燃油描述通过燃油别名表按优先级标准化。这里的关键陷阱是子串匹配：`Premium unleaded` 必须标准化为 `premium_unleaded`，不能落到通用的 `unleaded`；`Unleaded regular` 标准化为 `unleaded`；`Renewable Diesel B20` 标准化为 `diesel`。有效记录中，实际标准燃油类型与车辆 `expected_fuel` 不一致的记录会成为错配候选；但车辆级例外需要从普通错配队列中分离。本任务中，`field_generator` 车辆例外使 `FP_BG_0147` 和 `FP_BG_0198` 不进入车辆错配复核队列。void 或被取代的 `FP_N_005` 也列入 `exception_purchase_ids`。

标准答案包括：

- 范围和数量：`region = north`，`period = 2026-07`，`purchase_count_evaluated = 13`。
- 错配采购：`FP_BG_0113`、`FP_BG_0131`、`FP_BG_0169`、`FP_BG_0190`、`FP_N_002`。
- 例外采购：`FP_BG_0147`、`FP_BG_0198`、`FP_N_005`。
- 各标准燃油类别加仑数：diesel `105.09`，unleaded `174.35`，premium_unleaded `19.91`，electric `29.55`，hybrid `0.00`，unknown `0.00`。
- 供应商错配计数：ChargeNet `2`，FleetCard `1`，FuelHub `1`，QuickFuel `1`。
- 有效记录上的别名问题计数：优先级重叠匹配 `8`，通用 unleaded 子串陷阱 `7`，模糊 unknown 匹配 `0`，未映射描述 `0`。`decision_audit` 还记录 void、amended、superseded、vehicle exception、zero-gallon 和非平凡别名解析 trace。
- 源差异审计：API-only 当前采购 `FP_N_006`，CSV-only 历史采购 `FP_CSV_N_901`，过期 CSV 采购 `FP_N_005`，存在差异的交易为 `TXN-CSV-N-901` 和 `TXN-N-005`。从运营汇总排除的 CSV 记录是 `FP_CSV_N_901` 和 `FP_N_005`。

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

常见模型错误包括只看 CSV 导出而不检查当前 API 记录，把 CSV-only 历史行计入运营汇总，把 amendment 记录当作普通重复记录，先匹配通用 `unleaded` 而不是更具体的别名，把车辆例外计入普通错配队列，以及在加仑数字段中遗漏零值燃油类别。

### 迁移设计

作为训练任务，本任务为后续车队燃油和类别标准化任务提供可迁移经验。求解者将盲做结果与标准答案比较后，应学到燃油别名需要按优先级匹配，状态和修正记录需要先重建有效记录再汇总，受控枚举值必须保持一致，例外记录应从普通错配中分离而不是直接忽略，源导出需要先与当前 API 对账后才能进入运营汇总，并且 `decision_audit` 要保留可追溯的 lifecycle 与 alias trace 证据。

### 构建记录

作者：`train_002` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建北区 2026 年 7 月车队燃油错配审计任务的求解提示、答案模板、标准答案、评估器和双语说明。
## Rework addendum / 返工补充

English: After calibration rework, the train answer includes `decision_audit` with concrete fuel evidence: purchases affected by alias-priority matching, generic-unleaded substring traps, unknown or unmapped aliases, void/amended/superseded records, vehicle exceptions, zero-gallon rows, and alias-resolution trace rows. Later rework added `source_delta_audit`, `transaction_reconciliation`, and `operations_load_decision_audit` for API-only current records, stale CSV rows, CSV-only legacy rows, disagreement transaction keys, and resulting load/review owner decisions. These fields make the transfer-dependent checks auditable as business results.

中文：校准返工后，训练答案在 `decision_audit` 中加入了具体燃料证据：受别名优先级匹配影响的采购、通用 `unleaded` 子串陷阱采购、未知或未映射别名、void/amended/superseded 记录、车辆例外、零加仑记录，以及别名解析 trace。后续返工加入了 `source_delta_audit`、`transaction_reconciliation` 和 `operations_load_decision_audit`，用于记录 API-only 当前记录、过期 CSV 行、CSV-only 历史行、存在差异的交易键，以及由此产生的装载/复核负责方决策。这些字段让依赖迁移的检查成为可审计业务结果。
