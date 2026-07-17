# Notes for train_004

## English

This train task is a regional branch-reporting task derived from source example `E001`. It targets `REG-WEST` and requires the solver to use the shared Finance Ops API rather than stale offline branch lists.

The task definition is to build a compact regional management view with FY2024 and FY2025 rollups, growth, FY2025 EBITDA margin, sales per labor headcount, top and bottom branch EBITDA performers, and reconciliation variance. The visible materials are the prompt, environment access, request memo, and answer template.

Material map: `/api/finance/branches` identifies the branches in `REG-WEST`; `/api/finance/period-map` maps M-periods to fiscal years; `/api/finance/accounts` classifies records; `/api/finance/records` provides the monthly branch-account data.

The standard answer includes 7 scoring points with raw weights 2, 2, 3, 2, 2, 2, and 1. Evaluation checks the branch set, FY rollups, dashboard ratios, ranking facts, and zero reconciliation variance.

Transfer design: this is a formal train task that reinforces branch hierarchy source precedence, account category rollups, period mapping, and descending EBITDA ranking. These conventions anchor `test_001` and `test_004`.

Construction record: created by Codex on 2026-06-02 from fixed-seed generated finance data.

## 中文

本训练任务对应 `E001` 的区域管理报表工作流，目标区域为 `REG-WEST`。求解者需要使用共享 Finance Ops API，而不是旧的离线区域清单。

任务要求生成区域层面的 FY2024/FY2025 汇总、收入增长、FY2025 EBITDA margin、sales per labor headcount、区域内 EBITDA 最高和最低的分支，以及区域 EBITDA 与分支合计的勾稽差异。可见材料包括 prompt、环境入口、请求 memo 和答案模板。

标准答案通过 branches、period-map、accounts 和 records 四类环境数据构造。评分点 7 个，原始权重为 2、2、3、2、2、2、1，检查分支集合、年度汇总、指标、排名和勾稽差异。

迁移设计：该任务进一步强化分支层级、账户滚算、期间映射和 EBITDA 降序排名。这些经验会迁移到 `test_001` 和 `test_004`。
