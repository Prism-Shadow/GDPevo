# Train 003 Notes / 训练任务 003 说明

## Lineage / 数据血缘

English: This task is derived from the shared SQL analytics scenario and implements train_003 from `scratch/task_group_design.md`. It uses the generated SQLite database in `task_group/task_group_022/env/generated/ops_analytics.sqlite` and the approved data-quality case `DQ-USG-2026-04-A`.

中文：本任务来自共享 SQL 分析场景，对应 `scratch/task_group_design.md` 中的 train_003。任务使用生成的 SQLite 数据库 `task_group/task_group_022/env/generated/ops_analytics.sqlite`，并基于已批准的数据质量案例 `DQ-USG-2026-04-A`。

## Task Definition / 任务定义

English: The solver must submit a safe SQL correction for usage rows misclassified from `HELIOSYNC` to `ATLASDB`, then report April 2026 qualified ATLASDB usage for enterprise accounts after applying the fix.

中文：求解者需要提交安全的 SQL 修正，将误归类为 `HELIOSYNC` 的 usage 行改为 `ATLASDB`，并报告修正后 2026 年 4 月企业客户的合格 ATLASDB 使用量。

## Scenario Fit / 场景适配

English: This is a stateful SQL workflow: the evaluator copies the shared database, executes the submitted SQL, validates intended database effects, and recomputes metrics. It exercises approved-case handling, audit columns, and qualified usage conventions.

中文：这是一个有状态 SQL 工作流：评测器会复制共享数据库、执行提交的 SQL、验证预期数据库变更，并重新计算指标。它覆盖已批准案例处理、审计字段以及合格使用量口径。

## Material Map / 材料映射

English: Solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. Hidden files are `output/answer.json`, `notes/notes.md`, and evaluator files under `eval/`.

中文：求解者可见文件包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。隐藏文件包括 `output/answer.json`、`notes/notes.md` 以及 `eval/` 下的评测文件。

## Solution And Evaluation Basis / 解答与评测依据

English: The approved case lists 14 target usage ids: `USG-DQ-APR-001` through `USG-DQ-APR-014`. All must change from `HELIOSYNC` to `ATLASDB`, with `audit_reason = 'approved correction DQ-USG-2026-04-A'` and a non-null `audit_updated_at`. The hidden answer uses `2026-04-23 10:15:00`, the case creation timestamp.

中文：已批准案例列出 14 个目标 usage id：从 `USG-DQ-APR-001` 到 `USG-DQ-APR-014`。这些行必须从 `HELIOSYNC` 改为 `ATLASDB`，并写入 `audit_reason = 'approved correction DQ-USG-2026-04-A'` 与非空 `audit_updated_at`。隐藏答案使用案例创建时间 `2026-04-23 10:15:00`。

English: Qualified usage includes April 2026 production ATLASDB rows for external enterprise accounts with subscription date coverage, excluding backfills and telemetry-v1 rows when telemetry-v2 exists for the same account/product/day. Subscription coverage is tested with `EXISTS` to avoid double-counting overlapping subscriptions.

中文：合格使用量包括 2026 年 4 月、生产环境、ATLASDB、外部企业客户、且在订阅有效日期内的记录；排除 backfill，并在同一账户/产品/日期存在 telemetry-v2 时排除 telemetry-v1。订阅覆盖使用 `EXISTS` 判断，以避免重叠订阅导致重复计数。

English: Expected metrics after the fix are `changed_row_count = 14`, `total_compute_hours_after_fix = 18680.15`, one affected qualified enterprise account (`ACCT-0001`, 2 corrected rows, 193.99 added compute hours), and top account `ACCT-0001` with 36 qualified rows and 4208.15 compute hours.

中文：修正后的期望指标为 `changed_row_count = 14`，`total_compute_hours_after_fix = 18680.15`，受影响的合格企业账户只有 `ACCT-0001`（2 行修正记录，新增 193.99 compute hours），最高使用账户也是 `ACCT-0001`，共有 36 行合格记录和 4208.15 compute hours。

## Transfer Design / 迁移设计

English: The task teaches the safe pattern for approved usage corrections and post-fix metric recomputation. The analogous test task changes product, segment, month, and output shape, so solvers must transfer the method rather than memorize ids.

中文：本任务训练已批准使用量修正和修正后指标重算的安全模式。对应测试任务会改变产品、客户分层、月份和输出形状，因此求解者需要迁移方法，而不是记忆具体 id。

## Construction Record / 构建记录

English: Created only under `task_group/task_group_022/train_tasks/003/`. No environment files, scratch files, task manifests, or other task folders were modified.

中文：本任务仅在 `task_group/task_group_022/train_tasks/003/` 下创建。未修改环境文件、scratch 文件、任务清单或其他任务目录。
