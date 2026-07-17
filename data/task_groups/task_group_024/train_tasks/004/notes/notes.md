# English Notes

- Built train_004 as a portfolio-mix task for Data Platform, quarter 2026-Q1, as of 2026-03-31.
- Solver-visible files are limited to the prompt, answer template, and a small request context with endpoint hints.
- The hidden answer follows the shared portfolio mix rules: product-and-quarter scope, effective status from status history at quarter end, completed statuses only, category precedence, one-decimal percentages, integer basis-point gaps, and follow-up actions only for categories at least 500 bps under target.
- The evaluator has seven scoring points matching the common work-mix scoring plan.

# 中文说明

- 已将 train_004 构建为 Data Platform 在 2026-Q1、截至 2026-03-31 的组合投入结构任务。
- 面向求解器的文件仅包含提示、答案模板，以及带端点提示的小型请求上下文。
- 隐藏答案遵循共享的组合投入规则：按产品和季度限定范围，使用季度末状态历史确定有效状态，仅纳入已完成状态，按类别优先级分类，百分比保留一位小数，差距使用整数基点，并且只在低于目标至少 500 个基点时生成后续动作。
- 评估器包含七个评分点，与通用 work-mix 评分计划一致。

## Integration Audit Addendum

Lineage and materials: this second `E001`-style portfolio task uses Data Platform 2026-Q1 records from the shared work-item export, status history, target table, team table, and category policy. The local request context names scope and endpoint hints without computed outputs.

Solution and evaluation basis: the answer applies the same eligibility, effective-status, category-precedence, target-gap, and follow-up conventions as `train_001`, but on a larger later-quarter product scope. Seven exact-match points score completed-work population, counts, rounded percentages/gaps, under-investment, largest gap, follow-up mapping, and evidence IDs.

Transfer role: it reinforces that work-mix conventions recur across products and quarters, preventing the train skill from depending on a single Identity Platform example. It anchors `test_001`, `test_004`, and `test_005`.

## 集成审核补充

数据来源与材料：第二个 `E001` 风格的 portfolio 任务使用共享工单导出、状态历史、目标表、团队表和分类政策中的 Data Platform 2026-Q1 记录。本地 request context 只给出范围和端点提示，不包含计算输出。

解法与评测依据：答案沿用 `train_001` 的 eligibility、有效状态、分类优先级、目标 gap 和跟进约定，但应用在更大且更晚的产品范围上。七个精确匹配点评分已完成工单总体、计数、取整百分比/gap、低配、最大 gap、跟进映射和证据 ID。

迁移作用：它强化 work-mix 约定会跨产品和季度重复出现，避免训练技能依赖单一 Identity Platform 样例。它锚定 `test_001`、`test_004` 和 `test_005`。
