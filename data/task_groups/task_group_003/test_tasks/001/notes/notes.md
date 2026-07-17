# test_001 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by train tasks `train_001` and `train_004`. The visible payload lists five new offline service tickets; the support-console API supplies accounts, outages, diagnostics, and troubleshooting.

Task definition: The solver resolves a new service-ticket batch and returns per-ticket status, diagnostic flags, outage/escalation fields, and summary counts.

Scenario fit: The task is a formal CRM service-ticket resolution task, matching the source examples' account validation, outage analysis, diagnostics, troubleshooting, and escalation workflow.

Material map: `ticket_batch.csv` identifies tickets. `/api/tickets/<id>`, `/api/accounts/<id>`, `/api/outages?service_area=...`, `/api/diagnostics/<id>`, and `/api/troubleshooting/<id>` provide the needed evidence.

Solution and evaluation basis: The batch includes outage gating, authentication gating, successful troubleshooting, and two unresolved escalation families. There are 10 scoring points focused on ticket decisions, batch counts, target-scoped metric evidence, gate-skipped diagnostics, and root-cause escalation evidence.

Transfer design: High-value points depend on transfer from train: outage short-circuit and no diagnostics from `train_001`/`train_004`, diagnostics thresholds from `train_001`, and root-cause-to-team mapping from `train_004`. The new ticket IDs, service areas, and root causes require task-specific exploration.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

## 中文

数据来源：本测试任务属于 `SCN_003_crm_service_ticket_resolution`，由 `train_001` 和 `train_004` 锚定。可见输入列出五个新离线工单；共享 API 提供账号、outage、诊断和排障数据。

任务定义：求解者需要处理新的服务工单批次，输出每个工单的状态、诊断标记、outage/升级字段和汇总计数。

场景适配：这是正式 CRM service-ticket resolution 任务，与源样例中的账号验证、outage 分析、诊断、排障和升级流程一致。

材料地图：`ticket_batch.csv` 给出工单；`/api/tickets/<id>`、`/api/accounts/<id>`、`/api/outages?service_area=...`、`/api/diagnostics/<id>` 和 `/api/troubleshooting/<id>` 提供证据。

答案与评测依据：该批次覆盖 outage gate、authentication gate、成功排障以及两类未解决升级场景。评测有 10 个得分点，集中在工单决策、批次汇总、目标范围 metric 证据、被 gate 跳过的诊断和根因升级证据。

迁移设计：高价值得分点依赖训练迁移：outage 优先和不诊断来自 `train_001`/`train_004`，诊断阈值来自 `train_001`，根因到团队映射来自 `train_004`。新工单、服务区域和根因仍需本任务探索。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化测试任务。
