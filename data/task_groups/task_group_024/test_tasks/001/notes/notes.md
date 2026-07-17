# English

Task `test_001` is a portfolio-mix review for Collaboration Suite, scoped to `2026-Q2` with quarter-end/as-of date `2026-06-30`.

The solver-visible prompt points to `<TASK_ENV_BASE_URL>`, `request_context.json`, and `answer_template.json` without exposing the scoring rubric or computed answer. The request context gives only business context, scope, and endpoint hints.

The hidden answer was computed from the common portfolio mix rules: product/quarter filtering, effective quarter-end status from status history, exclusion of cancelled/open work, category precedence, target-vs-actual percentages, gap basis points, under-investment threshold, follow-up action ownership, and evidence sample IDs.

Train anchors: `train_001` and `train_004`. They transfer the closed-work portfolio scope, category precedence, target-gap rounding, under-invested category selection, and `IncreaseAllocation` owner-team action pattern.

# 中文

任务 `test_001` 是 Collaboration Suite 的组合投入结构复盘，范围是 `2026-Q2`，季度结束/截至日期为 `2026-06-30`。

求解者可见的提示只指向 `<TASK_ENV_BASE_URL>`、`request_context.json` 和 `answer_template.json`，不暴露评分细则或计算答案。请求上下文只包含业务背景、范围和端点提示。

隐藏答案按通用 portfolio mix 规则计算：按产品和季度筛选、用状态历史得到季度末有效状态、排除取消和未完成工作、应用类别优先级、计算目标与实际占比、基点差异、低配阈值、后续动作归属团队，以及每类证据样本 ID。

训练锚点：`train_001` 和 `train_004`。它们迁移闭环工作范围、类别优先级、目标差异取整、低配类别选择，以及 `IncreaseAllocation` 归属团队动作模式。

## Integration Audit Addendum

Lineage and materials: this test task is built from the `E001` portfolio-mix family and uses Collaboration Suite 2026-Q2 records from the shared Engineering Ops environment. The local request context names the scope and endpoint families; the answer requires exploration across work items, status history, target percentages, teams, and policy documents.

Solution and evaluation basis: seven exact-match scoring points cover eligible closed-work population, category counts, rounded actual/target/gap rows, under-invested categories, largest negative gap, follow-up action mapping, and evidence samples. High-weight points depend on category precedence and quarter-end effective status, not output formatting alone.

Transfer design: `train_001` and `train_004` anchor the repeatable mix-review SOP. The test changes product, quarter, target values, item volume, and noisy labels, so train skill helps but does not reveal final IDs.

## 集成审核补充

数据来源与材料：该测试任务来自 `E001` portfolio-mix 族，使用共享 Engineering Ops 环境中的 Collaboration Suite 2026-Q2 记录。本地 request context 只给出范围和端点族；答案需要跨 work_items、status_history、target percentages、teams 和政策文档探索。

解法与评测依据：七个精确匹配评分点覆盖 eligible closed-work 总体、类别计数、取整的 actual/target/gap 行、低配类别、最大负 gap、跟进行动映射和证据样本。高权重点依赖类别优先级和季度末有效状态，而不是仅依赖输出格式。

迁移设计：`train_001` 和 `train_004` 锚定可重复的 mix-review SOP。测试改变产品、季度、目标值、工单量和噪声标签，因此训练技能有帮助但不会泄露最终 ID。
