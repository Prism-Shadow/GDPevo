# Train 001 Notes / 训练任务 001 说明

## Lineage / 来源

English: This task is derived from the SQL database analytics scenario for qualified production usage rollups. It uses the shared operational analytics SQLite database generated under `task_group/task_group_022/env/` and does not introduce any task-local data service.

中文：本任务来自 SQL 数据库分析场景中的合格生产用量汇总。它使用 `task_group/task_group_022/env/` 下生成的共享运营分析 SQLite 数据库，不引入任务级本地数据服务。

## Task Definition / 任务定义

English: The solver must produce the 2026-Q1 AtlasDB usage rollup for EMEA enterprise customer accounts. The output includes the period, qualified account count, total compute hours, ranked top accounts, regional and account breakdowns, and the telemetry-v1 overlap exclusion count.

中文：求解者需要生成 2026 年第一季度 EMEA 企业客户账户的 AtlasDB 用量汇总。输出包括期间、合格账户数、总计算小时数、账户排名、区域和账户明细，以及 telemetry-v1 重叠排除计数。

## Scenario Fit / 场景适配

English: The task requires relational schema discovery, joins across accounts, products, subscriptions, and usage facts, date-window filtering, production-only usage handling, subscription effective-date logic, and deterministic rollup/ranking.

中文：本任务要求理解关系型模式，连接账户、产品、订阅和用量事实表，处理日期窗口、生产用量、订阅生效日期，并生成确定性的汇总和排名。

## Material Map / 材料映射

English: Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. Hidden materials are this note file, `output/answer.json`, and the evaluator under `eval/`.

中文：求解者可见材料为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。隐藏材料为本说明文件、`output/answer.json` 以及 `eval/` 下的评估器。

## Solution and Evaluation Basis / 解法与评估依据

English: The standard answer is computed from `usage_daily` joined to `accounts`, with an active subscription existence check against `subscriptions` for the same account, product, and activity date. The qualifying rows are AtlasDB, EMEA, enterprise, external non-test customer accounts, Q1 dates, production environment, non-backfill rows, and telemetry-v1 rows only when no telemetry-v2 row exists for the same account/product/day. The evaluator recomputes the same answer by SQL and scores structured JSON fields.

中文：标准答案由 `usage_daily` 连接 `accounts` 得出，并通过 `subscriptions` 对同一账户、产品和活动日期做有效订阅存在性检查。合格行限定为 AtlasDB、EMEA、企业客户、外部非测试账户、第一季度日期、生产环境、非回填行，并且同一账户/产品/日期存在 telemetry-v2 时排除 telemetry-v1。评估器通过 SQL 重新计算同一答案，并对结构化 JSON 字段评分。

## Transfer Design / 迁移设计

English: This train task teaches the recurring qualified usage convention used by later tasks: production facts, external customer accounts, date-effective subscriptions, telemetry source precedence, and exact account ranking. Test tasks change product, segment, region, period, and additional outputs.

中文：本训练任务覆盖后续任务会复用的合格用量规则：生产事实、外部客户账户、按日期生效的订阅、遥测来源优先级，以及精确账户排名。测试任务会更换产品、分群、区域、期间和附加输出。

## Construction Record / 构建记录

English: Created for `task_group/task_group_022/train_tasks/001/` on 2026-07-08. No other task folder or shared environment file was modified.

中文：本任务于 2026-07-08 创建在 `task_group/task_group_022/train_tasks/001/`。未修改其他任务文件夹或共享环境文件。
