# train_003 Notes

## English

This task belongs to `task_group_007` for scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and especially `E003`. The assigned brief is a Q1 supplier incident scorecard for Northwind Components. The shared generated environment under `task_group/task_group_007/env/` supplies the public ERP API and generated incident and supplier records. The task-local payloads are `input/payloads/q1_scorecard_request.json` and `input/payloads/answer_template.json`.

The solver-visible request asks for a Q1 2026 scorecard using the shared API, not the hidden environment files. The intended work is to query `/incidents?start=2026-01-01&end=2026-03-31` and `/suppliers`, aggregate incidents by `supplier_id`, join supplier names and `quality_status`, and return the structured JSON shape in the template. The date filter is on `open_date`, inclusive. The filtered population has 38 incidents and 12 suppliers with at least one incident.

Material map: `/incidents` provides `incident_type`, `supplier_id`, `open_date`, `close_date`, `status`, `severity`, and `resolution_cost`; `/suppliers` provides supplier names and quality statuses used by the recommendation policy. `q1_scorecard_request.json` fixes the analysis window, duration treatment for open incidents, rounding precision, severe severity values, row ordering, escalation ordering, and controlled recommendation policy. `answer_template.json` defines the output contract without exposing answers.

The standard answer filters incidents opened from 2026-01-01 through 2026-03-31. Duration is calendar days from `open_date` to `close_date`; open incidents use the explicit analysis date 2026-03-31. Percentages use the filtered 38-incident denominator, rounded to one decimal. Costs are rounded to cents and average durations to two decimals. Rows are sorted by supplier id. Recommendation codes use the policy precedence: `ESCALATE_SUPPLIER`, then `PROCESS_REVIEW`, then `WATCHLIST`, then `MONITOR`.

The eight exact-match scoring points are: `SP001` analysis window and summary totals, weight 2; `SP002` supplier set, names, counts, and percentages, weight 3; `SP003` supplier costs and highest-cost supplier, weight 2; `SP004` average duration by supplier, weight 2; `SP005` RMA and work-order split, weight 2; `SP006` open and severe counts, weight 1; `SP007` controlled recommendation codes, weight 3; `SP008` escalation ordering and highest-share supplier, weight 2. These points emphasize business aggregates rather than formatting or free-form rationale.

Likely model pitfalls include using all 2026 incidents rather than Q1, filtering on `close_date` instead of `open_date`, using each supplier's own count as the percentage denominator, excluding open incidents from duration, confusing RMA with work orders, treating supplier display names as stable identifiers, or ignoring recommendation precedence. This train task anchors transferable incident-analytics conventions for later test tasks: filtered-population denominators, duration handling, incident-type separation, supplier-id joins, and controlled management recommendations.

Construction record: authored by task-builder subagent `train_003` on 2026-06-01. Created files for prompt, request payload, answer template, answer, evaluator, and notes. No shared environment, task-group metadata, calibration, seed scenario, or other task folders were edited.

## 中文

本任务属于 `task_group_007`，场景为 `SCN_007_erp_inventory_order_fulfillment`，来源示例包括 `E001`、`E002`，并主要对应 `E003` 的供应商事件分析难度。任务要求为 Northwind Components 生成 2026 年第一季度供应商事件评分卡。共享环境提供公开 ERP API 和生成的事件、供应商数据；任务本地材料包括 `input/payloads/q1_scorecard_request.json` 与 `input/payloads/answer_template.json`。

求解者可见任务要求使用共享 API，而不是直接读取隐藏环境文件。预期流程是查询 `/incidents?start=2026-01-01&end=2026-03-31` 和 `/suppliers`，按 `supplier_id` 聚合事件，连接供应商名称和质量状态，并按模板输出结构化 JSON。日期过滤字段为 `open_date`，且起止日期均包含在内。过滤后共有 38 条事件，涉及 12 个有事件的供应商。

材料用途：`/incidents` 提供事件类型、供应商、开始日期、关闭日期、状态、严重度和处理成本；`/suppliers` 提供供应商名称与质量状态，用于推荐策略。`q1_scorecard_request.json` 固定分析窗口、未关闭事件的时长计算方式、舍入精度、严重度取值、排序规则和受控推荐策略。`answer_template.json` 规定输出结构，但不泄露标准答案。

标准答案筛选 2026-01-01 至 2026-03-31 开启的事件。时长为 `open_date` 到 `close_date` 的自然日差；未关闭事件按明确给出的分析日 2026-03-31 计算。百分比以过滤后的 38 条事件为分母并保留一位小数；成本保留两位小数；平均时长保留两位小数；评分卡行按供应商编号排序。推荐代码按优先级依次判断：`ESCALATE_SUPPLIER`、`PROCESS_REVIEW`、`WATCHLIST`、`MONITOR`。

本任务有 8 个精确匹配评分点：`SP001` 分析窗口与汇总总数，权重 2；`SP002` 供应商集合、名称、数量与百分比，权重 3；`SP003` 供应商成本与最高成本供应商，权重 2；`SP004` 各供应商平均时长，权重 2；`SP005` RMA 与工单类型拆分，权重 2；`SP006` 未关闭与严重事件数量，权重 1；`SP007` 受控推荐代码，权重 3；`SP008` 升级供应商排序与最高占比供应商，权重 2。评分关注业务结果聚合，不评价自由文本。

常见错误包括使用全年事件而不是第一季度事件、按 `close_date` 过滤、百分比分母使用单个供应商数量、在时长中排除未关闭事件、混淆 RMA 和工单、把供应商名称当作稳定主键，或忽略推荐优先级。该训练任务为后续测试任务提供可迁移经验：过滤后总体分母、时长规则、事件类型拆分、供应商编号连接和受控管理建议。

构建记录：由任务构建子代理 `train_003` 于 2026-06-01 创建。已创建提示、请求材料、答案模板、标准答案、评估器和说明文件。未编辑共享环境、任务组元数据、校准、种子场景或其他任务目录。
