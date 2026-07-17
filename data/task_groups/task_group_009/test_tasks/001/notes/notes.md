# Notes for test_001

## English

This test task extends the branch reporting workflow from `E001` and is anchored by `train_001` and `train_004`. It targets `BR-009`, with a noisy local memo that omits one South-region branch.

The task asks for a branch close package: M24 income statement, M24/M23 revenue variance, FY2025 branch metrics, regional context, and branch ranking facts. The visible payloads provide environment access, the target branch and periods, and the output schema.

Material map: Finance Ops period map resolves the fiscal-year convention; account metadata controls rollups; branches define the correct South-region membership; records provide monthly values. The stale memo is a source-conflict distractor.

Evaluation has 8 scoring points with weights 2, 2, 1, 2, 3, 2, 2, and 3. Transfer-dependent points include period convention, account rollup, same-scope ARPU and labor-headcount ratios, regional branch inclusion, and ranking direction. Task-specific difficulty comes from exploring a different branch and region.

Likely pitfalls include following the stale local memo, treating M1-M12 as the current year, omitting allocations from EBITDA, or computing ARPU from a single month instead of the fiscal-year record set.

Construction record: created by Codex on 2026-06-02.

## 中文

本测试任务延续 `E001` 的分支管理报表流程，并由 `train_001` 与 `train_004` 提供迁移锚点。目标分支是 `BR-009`，本地 memo 故意遗漏一个 South 区域分支，用于测试来源优先级判断。

任务要求输出 M24 income statement、M24/M23 收入差异、FY2025 分支指标、区域上下文和分支排名。可见材料只给环境入口、目标分支/期间和输出结构，不提供计算步骤。

评分点共 8 个，权重为 2、2、1、2、3、2、2、3。迁移依赖点包括期间映射、账户滚算、同范围 ARPU 和 labor-headcount 比率、区域分支包含关系和排名方向。任务自身难点来自新的分支、区域和完整数据探索。常见错误包括相信旧 memo、把 M1-M12 当作当前年度、遗漏 allocations，或使用错误范围的客户数/人数计算运营比率。
