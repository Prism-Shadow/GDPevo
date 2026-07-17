# test_003 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_003`. The visible files are the Quanta complaint email, response requirements, and answer template. The shared API provides incidents, export runs, messages, enterprise accounts, and SLA contracts.

Task definition: The solver must produce a structured enterprise response package for the target incident, including root cause, failed export window, backfill days, SLA credit, owner assignments, artifact names, share permissions, and response status.

Scenario fit: This is an enterprise CRM complaint investigation task. It combines technical export evidence with SLA and account-management response duties, matching the source example's end-to-end complaint closure.

Material map: `/api/enterprise/incidents/<id>` identifies the incident. `/api/enterprise/export-runs?incident_id=<id>` gives failure dates. `/api/enterprise/messages` and `/api/enterprise/sla/<enterprise_account_id>` provide root-cause context and credit terms.

Solution and evaluation basis: The expected response is derived from failed export runs, internal messages, the enterprise account record, and the SLA contract. There are 7 scoring points focused on the response package, export-run/message evidence, and enterprise consistency audits.

Transfer design: This task transfers response-package conventions from `train_003`: synthesize export runs, messages, and SLA terms; produce channel/folder/report names; assign owners and permissions. The client, root cause, failure length, and credit percent change.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

## 中文

数据来源：本测试任务属于 `SCN_003_crm_service_ticket_resolution`，由 `train_003` 锚定。可见文件为 Quanta 投诉邮件、response requirements 和 answer template。共享 API 提供 incident、export run、消息、企业账号和 SLA 合同。

任务定义：求解者需要为目标 incident 生成结构化企业响应包，包括根因、失败导出窗口、回填天数、SLA credit、负责人、工件名称、共享权限和响应状态。

场景适配：这是企业 CRM 投诉调查任务，把技术导出证据与 SLA、客户管理响应职责结合起来，符合源样例的端到端投诉闭环。

材料地图：`/api/enterprise/incidents/<id>` 标识事件；`/api/enterprise/export-runs?incident_id=<id>` 给出失败日期；`/api/enterprise/messages` 和 `/api/enterprise/sla/<enterprise_account_id>` 提供根因上下文与 credit 条款。

答案与评测依据：期望响应由失败 export run、内部消息、企业账号记录和 SLA 合同共同推导。评测有 7 个得分点，集中在响应包、export-run/message 证据和企业一致性核查。

迁移设计：本任务从 `train_003` 迁移响应包约定：综合 export run、message 和 SLA 证据，产出 channel/folder/report 名称，并分配 owner 与权限。客户、根因、失败长度和 credit 百分比发生变化。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化测试任务。
