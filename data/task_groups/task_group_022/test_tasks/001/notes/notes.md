# Test 001 Notes / 测试 001 说明

## English

Lineage: This task implements `test_001` from the SQL database analytics task group. It is a read-only qualified usage analytics task over the shared SQLite database, using the same production usage family as the train tasks but changing product, segment, region, period, and requested watchlist output.

Task definition: The solver must produce a JSON snapshot for `NEXAQUEUE` North America commercial accounts during 2026-Q2, from 2026-04-01 through 2026-06-30 inclusive. The output includes qualified account count, total compute hours, ranked account metrics, low-adoption accounts below 1,100.00 compute hours, regional breakdown, and exclusion counts.

Material map: The relevant tables are `accounts`, `subscriptions`, `products`, and `usage_daily`. `metric_notes` provides general context but not the final answer. The prompt exposes only the shared DB placeholder and the required answer template.

Solution and evaluation basis: Qualified usage is restricted to external non-test commercial accounts in region `NA`, product `NEXAQUEUE`, production environment, non-backfill rows, active subscription dates, and source precedence that drops `telemetry_v1` when non-backfill `telemetry_v2` exists for the same account, product, and day. The standard result has 2 qualified accounts, 60 qualified usage rows, and 2,194.30 compute hours. The top account is `ACCT-0011`; `ACCT-0008` is the low-adoption watchlist account.

Transfer design: The task transfers the hidden usage conventions from the train qualified-usage and incident-usage tasks: production-only usage, external account filtering, telemetry-v2 precedence, backfill exclusion, and subscription-date qualification. The test-specific work is finding the NexaQueue, NA commercial, Q2 slice and applying the low-adoption watchlist threshold.

Construction record: Created only under `task_group/task_group_022/test_tasks/001/`. The evaluator recomputes the expected answer through SQL against the shared SQLite database and scores account set/count, total compute hours, ranking, low adoption, regional breakdown, telemetry/backfill/non-production exclusions, subscription-date handling, and schema.

## 中文

来源：本任务实现 SQL 数据库分析任务组中的 `test_001`。它是一个只读的合格用量分析任务，使用共享 SQLite 数据库；业务族与训练任务中的生产用量分析相同，但更换了产品、客户分层、区域、时间窗口和观察名单输出。

任务定义：求解者需要为 2026 年第二季度（2026-04-01 至 2026-06-30，含首尾日期）的 `NEXAQUEUE` 北美商业客户生成 JSON 快照。输出包括合格客户数量、总计算小时数、客户排名指标、低采用客户（季度计算小时数低于 1,100.00）、区域拆分和排除行计数。

材料映射：相关表为 `accounts`、`subscriptions`、`products` 和 `usage_daily`。`metric_notes` 提供一般背景，但不直接给出答案。提示词只暴露共享数据库占位符和答案模板。

解答与评估依据：合格用量限定为 `NA` 区域、`commercial` 分层、`NEXAQUEUE` 产品的外部非测试客户；只计生产环境、非回填、处于有效订阅日期内的用量行；当同一账号、产品、日期存在非回填 `telemetry_v2` 时，排除 `telemetry_v1`。标准结果为 2 个合格账号、60 行合格用量、2,194.30 计算小时。排名第一账号为 `ACCT-0011`，低采用观察名单账号为 `ACCT-0008`。

迁移设计：本任务迁移训练任务中的隐藏用量规则，包括只看生产环境、排除内部或测试账号、`telemetry_v2` 优先、排除回填、订阅日期限定。测试任务的特定变化是定位 NexaQueue、北美商业客户、第二季度窗口，并应用低采用阈值。

构建记录：仅在 `task_group/task_group_022/test_tasks/001/` 下创建文件。评估器通过 SQL 从共享 SQLite 数据库重新计算期望答案，并覆盖账号集合与数量、总计算小时、排名、低采用名单、区域拆分、遥测/回填/非生产排除、订阅日期处理和 schema。
