# Notes for train_001

## English

This task is derived from `SCN_009_finance_operational_modeling_management_reporting`, especially source example `E001`. It asks for a branch close package for `BR-004` using the shared Crescent Finance Ops environment. Solver-visible inputs are `prompt.txt`, `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`.

The task fits the scenario because it converts raw monthly branch records into a repeatable management-reporting view. The solver must use the Finance Ops period map, account categories, branch hierarchy, and financial records. The local memo names the target and close periods but does not replace the environment source of truth.

Material map: `/api/finance/period-map` defines the M-period fiscal-year mapping; `/api/finance/accounts` defines account categories; `/api/finance/branches` defines the region membership; `/api/finance/records` contains the branch-account wide monthly data.

The standard answer calculates revenue, COGS, gross margin, SG&A, allocations, and EBITDA from the account records; compares M24 to M23 for revenue variance; rolls FY2025 and FY2024 periods; computes EBITDA margin, ARPU, and sales per labor headcount; and ranks branches and regions from the shared data. The seven scoring points have raw weights 1, 3, 2, 3, 2, 2, and 2. Exact matching is done through `eval/config.json`.

Transfer value: blind solving and answer comparison should teach the period convention, source precedence, account rollup logic, and ranking directions needed later in branch test tasks. Common pitfalls are using the wrong fiscal year for M-periods, treating operating counts like expenses, excluding a branch from the region, or ranking growth in ascending order.

Construction record: created by Codex on 2026-06-02; generated from fixed-seed environment data and task-specific branch close brief.

## 中文

本任务来自 `SCN_009_finance_operational_modeling_management_reporting`，主要对应原始示例 `E001` 的分支机构管理报表工作流。任务要求基于共享 Crescent Finance Ops 环境，为 `BR-004` 构造月结管理结果。求解者可见材料包括 prompt、环境入口、请求 memo 和答案模板。

场景适配点在于：任务不是单次查数，而是把原始月度分支记录、账户分类、期间映射和区域层级转化为可复用的管理报表结果。环境中的 period map、accounts、branches 和 records 是关键来源；本地 memo 只说明目标和口径请求，不能替代环境中的权威层级和期间定义。

标准答案按账户分类汇总收入、COGS、毛利、SG&A、分摊和 EBITDA；比较 M24 与 M23 的收入差异；汇总 FY2025 与 FY2024；计算 EBITDA margin、ARPU、sales per labor headcount；并在共享数据中完成区域和分支排名。评分点共 7 个，原始权重为 1、3、2、3、2、2、2，通过 `eval/config.json` 做精确匹配。

迁移设计：训练后应能学到 M-period 到财年的映射、账户滚算方式、环境优先于本地 memo 的习惯，以及排名方向。这些经验会迁移到后续 branch test 任务。常见错误包括期间映射错误、把运营数量当成费用、区域分支遗漏、以及排名方向反了。
