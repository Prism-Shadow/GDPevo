# test_003 Notes

## English

### Data and source lineage

This task belongs to `task_group_007`, scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and `E003`. It implements the incident analytics operation family described in `scratch/task_group_design.md` and the assigned `test_003` brief in `scratch/task_builder_briefs.md`.

The task uses the shared Northwind Components ERP environment under `task_group/task_group_007/env/`. Solvers should access only the public API, especially `/incidents` and `/suppliers`; they should not inspect environment source files. Task-local visible payloads are `input/payloads/full_year_supplier_incident_request.json` and `input/payloads/answer_template.json`.

### Task definition and material map

The business request is an annual supplier-quality and operations review for incidents opened from `2025-01-01` through `2025-12-31`, inclusive. The expected output is a structured JSON scorecard with the analysis window, overall summary, supplier-level metrics, supplier ranking, highest-cost and highest-share suppliers, and controlled management action sets.

`full_year_supplier_incident_request.json` defines the date window, use of `open_date` for filtering, the analysis date for open incidents, percentage denominators, numeric precision, severe severity values, ranking order, and recommendation-code policy. `answer_template.json` defines the required schema, enum values, rounding rules, and stable ordering requirements.

### Solution and evaluation basis

The standard answer filters incidents by `open_date` in calendar year 2025. It then joins supplier names and `quality_status` from `/suppliers`. Duration is calendar days from `open_date` to `close_date` for closed incidents; for open incidents it is calendar days from `open_date` to `2025-12-31`. Percentages use the filtered full-year population or filtered full-year total cost, not all generated incidents.

The answer contains 152 filtered incidents across 12 suppliers, total resolution cost `545296.07`, 71 RMA incidents, 81 WORK_ORDER incidents, overall RMA average duration `79.10` days, and overall WORK_ORDER average duration `69.16` days. Supplier rows are ordered by `supplier_id`; `supplier_ranking` is ordered by incident count descending, then total cost descending, then `supplier_id` ascending. Management recommendations use the request policy precedence exactly.

The evaluator has 8 exact-match scoring points with raw weights:

- `SP001` weight 2: correct analysis window and full-year summary totals.
- `SP002` weight 3: correct supplier set, names, quality statuses, incident counts, and incident percentages.
- `SP003` weight 2: correct supplier ranking, top-five ranking, and highest-share supplier.
- `SP004` weight 2: correct supplier total costs, cost percentages, and highest-cost supplier.
- `SP005` weight 3: correct overall and supplier RMA/work-order duration averages.
- `SP006` weight 2: correct RMA, work-order, open, severe, and critical-RMA counts by supplier.
- `SP007` weight 3: correct controlled management recommendation code by supplier.
- `SP008` weight 2: correct controlled management action supplier sets.

Likely pitfalls include using all 212 generated incidents instead of the 2025 population, filtering by `close_date`, using the whole dataset as the incident-percentage denominator, treating open incidents as zero-duration, failing to separate RMA from WORK_ORDER duration averages, and applying management recommendation rules without precedence.

### Transfer design

The primary train anchor is `train_003`, which establishes incident filtering, supplier aggregation, filtered-population denominators, duration rules, severe/open counts, ranking, and controlled recommendation codes. The second anchor is `train_005`, which connects supplier incident patterns to procurement-quality hold decisions and replenishment-freeze style recommendations. This test changes the date window to a complete calendar year, increases the filtered population, adds cost-share percentages, and separates per-supplier RMA and WORK_ORDER duration averages.

Transfer-dependent scoring points are `SP002`, `SP004`, `SP005`, `SP006`, and `SP007`, because they depend on the same aggregation, duration, incident-type separation, severity, quality-status, and recommendation-precedence conventions learned from the train tasks. `SP003` and `SP008` also benefit from train experience but require task-specific ranking and policy application over the larger full-year population.

### Construction record

Author: task-builder subagent `test_003`. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created solver prompt, request payload, answer template, standard answer, exact-match evaluator, and bilingual notes for the full-year supplier incident analysis task.

## Chinese

### 数据来源与任务沿革

本任务属于 `task_group_007`，场景为 `SCN_007_erp_inventory_order_fulfillment`，来源示例为 `E001`、`E002` 和 `E003`。它对应 `scratch/task_group_design.md` 中的库存事件分析任务族，以及 `scratch/task_builder_briefs.md` 中分配给 `test_003` 的全年供应商事件分析任务。

任务使用共享的 Northwind Components ERP 环境，即 `task_group/task_group_007/env/`。解题代理应只通过公开 API 使用环境，重点是 `/incidents` 和 `/suppliers`，不应直接查看环境源码或数据文件。任务本地可见材料包括 `input/payloads/full_year_supplier_incident_request.json` 和 `input/payloads/answer_template.json`。

### 任务定义与材料说明

业务目标是为年度供应商质量和运营复盘生成分析结果，筛选 `2025-01-01` 至 `2025-12-31` 期间打开的事件。期望输出为结构化 JSON，包括分析窗口、总体汇总、供应商指标、供应商排名、最高成本和最高占比供应商，以及受控的管理行动集合。

`full_year_supplier_incident_request.json` 规定日期窗口、按 `open_date` 过滤、开放事件使用的分析日期、百分比口径、数值精度、严重等级集合、排名顺序和推荐代码策略。`answer_template.json` 规定输出结构、枚举值、舍入规则和稳定排序要求。

### 标准答案与评测依据

标准答案按 `open_date` 筛选 2025 全年事件，并从 `/suppliers` 补充供应商名称和 `quality_status`。关闭事件的持续时间是 `open_date` 到 `close_date` 的自然日差；开放事件的持续时间是 `open_date` 到 `2025-12-31` 的自然日差。事件百分比使用筛选后的全年事件总数作为分母，成本百分比使用筛选后的全年总成本作为分母。

标准答案包含 152 条筛选事件、12 个供应商，总解决成本为 `545296.07`，其中 RMA 为 71 条，WORK_ORDER 为 81 条，RMA 平均持续 `79.10` 天，WORK_ORDER 平均持续 `69.16` 天。供应商明细按 `supplier_id` 升序排列；`supplier_ranking` 按事件数降序、总成本降序、`supplier_id` 升序排列。管理推荐严格按请求文件中的策略优先级计算。

评测器包含 8 个精确匹配评分点，原始权重如下：

- `SP001` 权重 2：分析窗口和全年汇总总数正确。
- `SP002` 权重 3：供应商集合、名称、质量状态、事件数和事件百分比正确。
- `SP003` 权重 2：供应商排名、前五名和最高占比供应商正确。
- `SP004` 权重 2：供应商总成本、成本百分比和最高成本供应商正确。
- `SP005` 权重 3：总体和供应商层面的 RMA/WORK_ORDER 持续时间均值正确。
- `SP006` 权重 2：供应商层面的 RMA、WORK_ORDER、开放、严重和关键 RMA 数量正确。
- `SP007` 权重 3：每个供应商的受控管理推荐代码正确。
- `SP008` 权重 2：受控管理行动供应商集合正确。

常见错误包括误用全部 212 条生成事件、按 `close_date` 过滤、用全数据集作为百分比分母、把开放事件持续时间当成 0、没有区分 RMA 与 WORK_ORDER 的持续时间均值，以及没有按优先级应用管理推荐规则。

### 迁移设计

主要训练锚点是 `train_003`，它覆盖事件过滤、供应商聚合、筛选集合百分比分母、持续时间规则、开放与严重事件计数、排名和受控推荐代码。第二个锚点是 `train_005`，它把供应商事件模式与采购质量冻结类决策联系起来。本测试把窗口改为完整日历年，扩大了筛选事件规模，增加了成本占比，并要求分供应商计算 RMA 与 WORK_ORDER 持续时间均值。

依赖迁移的评分点是 `SP002`、`SP004`、`SP005`、`SP006` 和 `SP007`，因为它们依赖训练任务中可归纳出的聚合、持续时间、事件类型拆分、严重等级、质量状态和推荐优先级规则。`SP003` 与 `SP008` 也受益于训练经验，但还需要在更大的全年事件集合上应用本任务特定的排名和策略。

### 构建记录

作者：任务构建子代理 `test_003`。创建日期：2026-06-01。更新日期：2026-06-01。主要变更：创建了全年供应商事件分析任务的解题提示、请求载荷、答案模板、标准答案、精确匹配评测器和双语说明。
