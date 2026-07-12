# Test 003 Notes / 测试任务 003 说明

## Lineage / 数据血缘

English: This task is derived from the shared SQL analytics scenario and implements test_003 from `scratch/task_group_design.md`. It uses the generated SQLite database in `task_group/task_group_022/env/generated/ops_analytics.sqlite` and the approved data-quality case `DQ-USG-2026-05-C`.

中文：本任务来自共享 SQL 分析场景，对应 `scratch/task_group_design.md` 中的 test_003。任务使用生成的 SQLite 数据库 `task_group/task_group_022/env/generated/ops_analytics.sqlite`，并基于已批准的数据质量案例 `DQ-USG-2026-05-C`。

## Task Definition / 任务定义

English: The solver must submit a safe SQL correction for usage rows misclassified from `NEXAQUEUE` to `LUMAFORMS`, then report May 2026 qualified LUMAFORMS usage for commercial accounts after applying the fix.

中文：求解者需要提交安全的 SQL 修正，将误归类为 `NEXAQUEUE` 的 usage 行改为 `LUMAFORMS`，并报告修正后 2026 年 5 月商业客户的合格 LUMAFORMS 使用量。

## Scenario Fit / 场景适配

English: This is a stateful SQL workflow. The evaluator copies the shared database, executes the submitted SQL, validates the exact intended database changes, and recomputes metrics from the mutated copy. It exercises approved-case handling, audit columns, and qualified usage conventions.

中文：这是一个有状态 SQL 工作流。评测器会复制共享数据库、执行提交的 SQL、验证精确的预期数据库变更，并从变更后的副本重新计算指标。它覆盖已批准案例处理、审计字段以及合格使用量口径。

## Material Map / 材料映射

English: Solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. Hidden files are `output/answer.json`, `notes/notes.md`, and evaluator files under `eval/`.

中文：求解者可见文件包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。隐藏文件包括 `output/answer.json`、`notes/notes.md` 以及 `eval/` 下的评测文件。

## Solution And Evaluation Basis / 解答与评测依据

English: The approved case lists 11 target usage ids: `USG-DQ-MAY-001` through `USG-DQ-MAY-011`. All must change from `NEXAQUEUE` to `LUMAFORMS`, with `audit_reason = 'approved correction DQ-USG-2026-05-C'` and a non-null `audit_updated_at`. The hidden answer uses `2026-05-27 09:25:00`, the case creation timestamp.

中文：已批准案例列出 11 个目标 usage id：从 `USG-DQ-MAY-001` 到 `USG-DQ-MAY-011`。这些行必须从 `NEXAQUEUE` 改为 `LUMAFORMS`，并写入 `audit_reason = 'approved correction DQ-USG-2026-05-C'` 与非空 `audit_updated_at`。隐藏答案使用案例创建时间 `2026-05-27 09:25:00`。

English: Qualified usage includes May 2026 production LUMAFORMS rows for external commercial accounts with active-date product subscription coverage, excluding backfills and telemetry-v1 rows when telemetry-v2 exists for the same account/product/day. Subscription coverage is tested with `EXISTS` to avoid double-counting overlapping subscriptions.

中文：合格使用量包括 2026 年 5 月、生产环境、LUMAFORMS、外部商业客户、且在产品订阅有效日期内的记录；排除 backfill，并在同一账户/产品/日期存在 telemetry-v2 时排除 telemetry-v1。订阅覆盖使用 `EXISTS` 判断，以避免重叠订阅导致重复计数。

English: Expected metrics after the fix are `changed_row_count = 11`, `total_compute_hours_after_fix = 3780.05`, affected qualified commercial accounts `ACCT-0032` and `ACCT-0033`, top five accounts led by `ACCT-0056`, and regional totals for APAC, EMEA, LATAM, and NA.

中文：修正后的期望指标为 `changed_row_count = 11`，`total_compute_hours_after_fix = 3780.05`，受影响的合格商业账户为 `ACCT-0032` 和 `ACCT-0033`，前五高使用账户以 `ACCT-0056` 开头，并包含 APAC、EMEA、LATAM 和 NA 的区域汇总。

## Transfer Design / 迁移设计

English: This task transfers the safe approved usage-correction pattern from train_003 while changing the case id, source product, target product, month, segment, and output shape. Solvers must inspect the database and recompute the metrics rather than reuse training literals.

中文：本任务迁移 train_003 中的安全已批准使用量修正模式，但更换了案例编号、源产品、目标产品、月份、客户分层和输出形状。求解者必须检查数据库并重新计算指标，而不能复用训练集字面值。

English: Calibration showed that the first visible prompt over-disclosed the old/new product mapping, allowing direct attempts to earn too much of the state-change score without relying on the train-derived approved-case reading habit. The visible prompt was tightened so the solver must discover the approved mapping from `data_quality_cases`, while the hidden answer and evaluator remain unchanged.

中文：校准显示首版可见提示过度暴露了旧/新产品映射，使直接尝试无需依赖训练中学到的已批准案例读取习惯也能获得过多状态变更分。可见提示已收紧，要求解题者从 `data_quality_cases` 中发现已批准映射；隐藏答案和 evaluator 保持不变。

English: A later scoring calibration reduced the raw weight on the mechanically verifiable update statement and increased the raw weight on post-correction business metrics. This keeps the evaluator focused on the long-horizon requery work rather than awarding most credit for simply finding the target rows.

中文：后续评分校准降低了机械可验证 update 语句的原始权重，并提高了修正后业务指标的原始权重。这样 evaluator 更聚焦于长链路重查工作，而不是因找到目标行就给出大部分分数。

## Construction Record / 构建记录

English: Created only under `task_group/task_group_022/test_tasks/003/`. No environment files, scratch files, task manifests, or other task folders were modified.

中文：本任务仅在 `task_group/task_group_022/test_tasks/003/` 下创建。未修改环境文件、scratch 文件、任务清单或其他任务目录。
