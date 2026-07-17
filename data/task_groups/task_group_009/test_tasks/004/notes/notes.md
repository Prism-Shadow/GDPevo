# Notes for test_004

## English

This test task is the all-company branch dashboard, derived from `E001` and anchored by `train_001` and `train_004`. It requires aggregation across all active branches in the shared Finance Ops environment.

The task definition is to produce FY2024/FY2025 revenue, FY2025 EBITDA, revenue growth, EBITDA margin, ARPU, sales per labor headcount, and four branch ranking facts. The visible payloads include only the environment entry point, board memo, and output schema.

The solution uses `/api/finance/branches` for the active branch set, `/api/finance/period-map` for fiscal years, `/api/finance/accounts` for rollups, and `/api/finance/records` for monthly values. The ranking checks require separate branch-level calculations for revenue growth, ARPU, gross-margin growth, and order growth.

There are 7 scoring points with raw weights 1, 1, 1, 3, 3, 1, and 2. Transfer-dependent points are period mapping, account classification, all-company aggregation, same-scope operating ratios, and ranking direction. Intrinsic difficulty comes from doing the same calculations over the full branch universe.

Construction record: created by Codex on 2026-06-02.

## 中文

本测试任务是全公司分支经营 dashboard，来源于 `E001`，迁移锚点为 `train_001` 和 `train_004`。任务需要在共享 Finance Ops 环境中聚合全部 active branches。

标准解法使用 branches 确定分支全集，period-map 确定 FY2024/FY2025，accounts 确定账户滚算，records 提供月度数据。排名需要分别计算收入增长、ARPU、毛利增长和订单增长。

评分点共 7 个，原始权重为 1、1、1、3、3、1、2。迁移依赖点包括期间映射、账户分类、全公司聚合、同范围运营比率和排名方向；任务自身难点是数据范围扩大到所有分支。
