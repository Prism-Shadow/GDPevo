# test_004 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_001`, `train_003`, and `train_004`. The visible payload lists service tickets and enterprise incidents for an executive priority board.

Task definition: The solver must rank the three highest-risk accounts, list enterprise credit-review accounts, notify owners, and summarize service and enterprise queue states.

Scenario fit: The task is a CRM executive escalation board. It combines service-ticket final states, escalation teams, enterprise severity, SLA credit exposure, and owner coordination.

Material map: `escalation_board_request.json` lists candidate records. `/api/tickets/<id>`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>` support ticket status reconstruction. `/api/enterprise/incidents/<id>`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla/<id>` support incident risk and credit review.

Solution and evaluation basis: The highest-risk records combine current critical enterprise credit exposure and unresolved service escalations according to the visible score policy. The evaluator has 6 exact-match points over ranking, the visible score policy, credit review, owner notifications, summaries, and candidate/environment audits.

Transfer design: This test requires transfer across families. Service status and team mapping come from `train_001`/`train_004`; enterprise SLA-credit and owner conventions come from `train_003`. The ranking output is new, so task-specific aggregation is still required.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

## 中文

数据来源：本测试任务属于 `SCN_003_crm_service_ticket_resolution`，由 `train_001`、`train_003` 和 `train_004` 锚定。可见 payload 列出用于 executive priority board 的 service tickets 与 enterprise incidents。

任务定义：求解者需要排名最高风险的三个账号，列出需要 credit review 的企业账号，通知 owner，并汇总服务与企业队列状态。

场景适配：该任务是 CRM executive escalation board，结合了 service-ticket 最终状态、升级团队、企业严重性、SLA credit 风险和 owner 协调。

材料地图：`escalation_board_request.json` 列出候选记录；`/api/tickets/<id>`、`/api/diagnostics/<id>`、`/api/troubleshooting/<id>` 支持工单状态重建；`/api/enterprise/incidents/<id>`、`/api/enterprise/export-runs`、`/api/enterprise/messages`、`/api/enterprise/sla/<id>` 支持 incident 风险和 credit review。

答案与评测依据：最高风险记录由当前 critical enterprise credit exposure 和未解决服务升级共同决定，并按可见 score policy 排名。评测有 6 个精确匹配点，覆盖排名、公开分数规则、credit review、owner notification、汇总和候选/环境核查。

迁移设计：本测试需要跨家族迁移。服务状态和团队映射来自 `train_001`/`train_004`；企业 SLA credit 与 owner 约定来自 `train_003`。排名输出是新的，因此仍需要本任务聚合探索。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化测试任务。
