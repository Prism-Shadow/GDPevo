# train_001 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, mainly source example `E001`, with telecom escalation flavor from `E002`. The visible payload is `input/payloads/ticket_batch.csv`; the shared environment records are under the support-console API, especially tickets, accounts, outages, diagnostics, and troubleshooting records.

Task definition: The solver must resolve four offline service tickets. The expected JSON records the final status, whether diagnostics are needed, diagnostic issue flags, outage ID, escalation team, and a batch summary.

Scenario fit: This is a direct CRM service-ticket lifecycle task: account state and authentication gate the workflow, outages can hold the case, diagnostics and post-troubleshooting metrics decide resolved versus escalated outcomes.

Material map: `ticket_batch.csv` identifies the target tickets. `/api/tickets/<id>` gives ticket metadata, `/api/accounts/<id>` gives account and authentication state, `/api/outages?service_area=...` gives outage candidates, `/api/diagnostics/<id>` and `/api/troubleshooting/<id>` provide metric evidence.

Solution and evaluation basis: The answer uses outage `OUT-9102` for `TCK-5131`, diagnostic thresholds for `TCK-5107` and `TCK-5184`, and account ineligibility for `TCK-5202`. The evaluator has 8 exact-match scoring points with raw weights 1-3.

Transfer design: As a train task, it lets the agent infer the offline support status vocabulary, outage short-circuit convention, diagnostics thresholds, post-troubleshooting success rule, and field escalation mapping.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

## 中文

数据来源：本任务来自 `SCN_003_crm_service_ticket_resolution`，主要锚定 `E001`，并带有 `E002` 的电信升级处理背景。可见输入是 `input/payloads/ticket_batch.csv`，共享环境通过 support-console API 提供 ticket、account、outage、diagnostics 和 troubleshooting 数据。

任务定义：求解者需要处理四个离线客服工单，输出最终状态、是否需要诊断、诊断问题标记、outage ID、升级团队和批次汇总。

场景适配：该任务对应典型 CRM service ticket 生命周期：账号状态和认证决定是否继续，outage 可使工单进入等待，诊断和排障后指标决定 resolved 或 escalated。

材料地图：`ticket_batch.csv` 给出目标工单；`/api/tickets/<id>`、`/api/accounts/<id>`、`/api/outages?service_area=...`、`/api/diagnostics/<id>`、`/api/troubleshooting/<id>` 分别提供工单、账号、故障、诊断和排障证据。

答案与评测依据：标准答案使用 `OUT-9102` 判断 `TCK-5131`，用阈值判断 `TCK-5107` 和 `TCK-5184`，并用账号不合格判断 `TCK-5202`。评测包含 8 个精确匹配得分点，权重为 1 到 3。

迁移设计：作为训练任务，它帮助模型归纳离线客服状态枚举、outage 优先规则、诊断阈值、排障后成功标准和现场升级团队映射。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化任务。
