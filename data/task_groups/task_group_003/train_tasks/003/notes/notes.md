# train_003 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, especially enterprise escalation example `E003`. The visible files are the Asteri complaint email, response requirements, and answer template. The shared API supplies enterprise accounts, incidents, export runs, internal messages, and SLA contracts.

Task definition: The solver must prepare structured response-package fields for `INC-7301`: root cause, contributing alert issue, failed export window, backfill scope, SLA credit, owners, artifact names, permissions, and response status.

Scenario fit: This mirrors an enterprise client complaint workflow where support must connect technical failure evidence with account/SLA obligations and internal response artifacts.

Material map: `/api/enterprise/incidents/INC-7301` identifies the incident. `/api/enterprise/export-runs?incident_id=INC-7301` gives failed run dates. `/api/enterprise/messages?query=Asteri` and `/api/enterprise/sla/ENT-3001` provide root cause, alert issue, owners, and credit terms.

Solution and evaluation basis: The root cause is stale credentials after rotation, with archived alert routing as a contributing issue. The failed window is 2026-05-12 to 2026-05-14, with 3 backfill days and a 15 percent SLA credit. There are 8 exact-match scoring points.

Transfer design: As a train task, it teaches by comparison how enterprise service complaints should combine export run evidence, message evidence, SLA terms, owner mapping, artifact naming, and differentiated sharing permissions.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

## 中文

数据来源：本任务来自 `SCN_003_crm_service_ticket_resolution`，主要对应企业升级样例 `E003`。可见文件包括 Asteri 投诉邮件、response requirements 和 answer template。共享 API 提供企业账号、incident、export run、内部消息和 SLA 合同。

任务定义：求解者需要为 `INC-7301` 生成结构化响应包字段，包括根因、告警路由问题、失败导出窗口、回填范围、SLA credit、负责人、工件命名、权限和响应状态。

场景适配：该任务模拟企业客户投诉处理，需要把技术故障证据与客户合同、SLA 义务和内部响应材料连接起来。

材料地图：`/api/enterprise/incidents/INC-7301` 标识事件；`/api/enterprise/export-runs?incident_id=INC-7301` 给出失败日期；`/api/enterprise/messages?query=Asteri` 和 `/api/enterprise/sla/ENT-3001` 提供根因、告警问题、负责人和 credit 条款。

答案与评测依据：根因为凭证轮换后的 stale secret，告警被路由到归档渠道是贡献因素。失败窗口为 2026-05-12 至 2026-05-14，需要 3 天回填和 15% SLA credit。评测有 8 个精确匹配点。

迁移设计：作为训练任务，它通过答案对比帮助模型归纳企业投诉中 export run 证据、消息证据、SLA 条款、owner 映射、工件命名和权限差异。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化任务。
