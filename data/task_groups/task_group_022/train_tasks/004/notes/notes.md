# train_004 Notes / 训练任务 004 说明

## Lineage / 数据血缘

English: This task belongs to the API-mediated SQL operational analytics task group. It uses the shared SQLite database generated for `task_group_022` and focuses on AtlasDB incident `INC-2026-005`, which is an actual row in the `incidents` table.

中文：本任务属于通过本地 API 暴露 SQL 查询能力的运营分析任务组。任务使用 `task_group_022` 生成的共享 SQLite 数据库，并聚焦 `incidents` 表中真实存在的 AtlasDB 事件 `INC-2026-005`。

## Task Definition / 任务定义

English: The analyst must produce a JSON incident exposure summary. Usage exposure is based on the incident record's own product, start time, resolved time, and impacted region. Because usage is daily, the incident window maps to `activity_date` values between the incident start date and resolved date, inclusive. Follow-up support signals use the seven days after `resolved_at`, with the lower bound exclusive and the upper bound inclusive.

中文：分析人员需要产出 JSON 格式的事件暴露摘要。使用量暴露以事件记录自身的产品、开始时间、解决时间和受影响区域为准。由于使用量表是日粒度，事件窗口映射为从事件开始日期到解决日期之间的 `activity_date`，包含两端。后续支持信号使用 `resolved_at` 后七天，下界不包含，上界包含。

## Scenario Fit / 场景契合

English: The task exercises schema discovery, incident-window interpretation, product and region filtering, active subscription handling, qualified production usage logic, ticket signal filtering, ranking, and exact JSON reporting.

中文：本任务考察模式发现、事件窗口解释、产品和区域过滤、有效订阅处理、合格生产使用量逻辑、工单信号过滤、排序以及精确 JSON 输出。

## Material Map / 材料映射

English: `incidents` supplies the incident window and impacted region. `usage_daily` supplies daily production usage. `accounts` supplies customer, status, and region attributes. `subscriptions` supplies active product entitlement. `tickets` supplies post-incident support signals. `products` confirms AtlasDB's product identifier.

中文：`incidents` 提供事件窗口和受影响区域。`usage_daily` 提供日粒度生产使用量。`accounts` 提供客户、状态和区域属性。`subscriptions` 提供有效产品订阅。`tickets` 提供事件后的支持信号。`products` 用于确认 AtlasDB 的产品标识。

## Solution and Evaluation Basis / 解答与评测依据

English: The standard usage answer filters AtlasDB usage on 2026-05-20 in NA to active, non-internal customer accounts, production environment rows, non-backfill rows, and accounts with an active AtlasDB subscription on the activity date. Subscription matching is an existence check to avoid double-counting accounts with more than one active subscription row. Telemetry v1 rows are excluded only when a telemetry v2 row exists for the same account, product, and date after the other eligibility filters. The resulting impacted accounts are `ACCT-0001` and `ACCT-0017`, with `41960` total API calls.

中文：标准使用量答案将 NA 区域 2026-05-20 的 AtlasDB 使用量过滤为活跃的非内部客户账户、生产环境、非回填记录，并要求该账户在活动日期有有效的 AtlasDB 订阅。订阅匹配使用存在性判断，避免拥有多条有效订阅记录的账户被重复计数。只有在其他资格过滤后，同一账户、产品、日期存在 telemetry v2 记录时，才排除 telemetry v1 记录。最终受影响账户为 `ACCT-0001` 和 `ACCT-0017`，总 API 调用数为 `41960`。

English: Follow-up tickets are AtlasDB tickets created after `2026-05-20 14:59:13` and through `2026-05-27 14:59:13`, scoped to active external accounts in NA. Qualifying ticket signals exclude canceled tickets, duplicates, non-customer-impact tickets, non-defect categories, internal/test accounts, inactive accounts, and tickets explicitly linked to a different incident. The qualifying follow-up account is `ACCT-0005`, with severity mix `P2: 1`.

中文：后续工单为 `2026-05-20 14:59:13` 之后至 `2026-05-27 14:59:13` 之间创建的 AtlasDB 工单，并限定为 NA 区域活跃外部账户。合格工单信号排除取消工单、重复工单、非客户影响工单、非缺陷类别、内部或测试账户、非活跃账户，以及明确关联到其他事件的工单。合格后续账户为 `ACCT-0005`，严重性分布为 `P2: 1`。

## Transfer Design / 迁移设计

English: This train task teaches transferable conventions for later incident tasks: deriving windows from the database, using daily usage windows carefully, avoiding duplicate subscription joins, applying production usage filters, and separating post-incident ticket signals from raw ticket volume.

中文：该训练任务传递后续事件任务可复用的约定：从数据库推导窗口、谨慎处理日粒度使用窗口、避免订阅连接导致重复计数、应用生产使用量过滤，以及区分事件后工单信号与原始工单量。

## Construction Record / 构建记录

English: Created under `task_group/task_group_022/train_tasks/004/` only. No environment files, task group manifest files, scratch files, or other task folders were modified. The evaluator recomputes the hidden standard answer from SQL and scores structured fields.

中文：本任务仅在 `task_group/task_group_022/train_tasks/004/` 下创建。未修改环境文件、任务组清单、scratch 文件或其他任务文件夹。评测器通过 SQL 重新计算隐藏标准答案，并对结构化字段评分。
