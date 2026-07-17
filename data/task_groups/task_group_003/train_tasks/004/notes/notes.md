# train_004 Notes

## English

Data lineage: This task is based on `SCN_003_crm_service_ticket_resolution` and combines source examples `E001` and `E002`. The visible payload is a seven-ticket queue snapshot; support-console API records supply account, outage, diagnostics, and troubleshooting evidence.

Task definition: The solver must classify each queue ticket by final status, route team, key blocker, and diagnostic requirement, then produce queue counts.

Scenario fit: This is CRM service-queue quality control. It uses the same lifecycle as offline resolution but emphasizes mixed-case routing and aggregate handoff counts.

Material map: `queue_snapshot.csv` lists target tickets. The relevant API endpoints are `/api/tickets/<id>`, `/api/accounts/<id>`, `/api/outages?service_area=...`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>`.

Solution and evaluation basis: The queue includes one outage hold, one resolved voice profile refresh, three failed tickets, one network engineering escalation, and one tier-2 provisioning escalation. There are 9 exact-match scoring points.

Transfer design: As a train task, it reinforces status vocabulary, account/authentication failure gates, outage handling, escalation team mapping, and rollup conventions that later test tasks reuse.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

## 中文

数据来源：本任务基于 `SCN_003_crm_service_ticket_resolution`，结合 `E001` 和 `E002`。可见输入是七个工单的队列快照；共享 API 提供账号、outage、诊断和排障证据。

任务定义：求解者需要为每个队列工单判断最终状态、路由团队、关键阻塞原因和是否需要诊断，并生成队列计数。

场景适配：这是 CRM 服务队列质检任务，沿用离线工单生命周期，但更强调混合 case 的路由和汇总交接。

材料地图：`queue_snapshot.csv` 列出目标工单；相关 API 是 `/api/tickets/<id>`、`/api/accounts/<id>`、`/api/outages?service_area=...`、`/api/diagnostics/<id>` 和 `/api/troubleshooting/<id>`。

答案与评测依据：队列包含一个 outage 等待、一个 voice profile refresh resolved、三个 failed 工单、一个 network engineering 升级和一个 tier-2 provisioning 升级。评测有 9 个精确匹配点。

迁移设计：作为训练任务，它强化状态枚举、账号/认证失败门控、outage 处理、升级团队映射和汇总计数约定，这些都会在测试任务中复用。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化任务。
