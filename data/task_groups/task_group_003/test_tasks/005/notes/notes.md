# test_005 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by all five train tasks. The visible payload lists proposed CRM updates across service tickets, contact-center cases, and enterprise incidents.

Task definition: The solver audits each proposed update, accepts correct ones, corrects wrong statuses, actions, teams, refuel amounts, or credit percentages using structured reason codes, and fills QA evidence/package-review fields required by the template.

Scenario fit: QA review is a realistic CRM operations workflow: support leaders often check proposed case updates before they affect customer communications, escalation queues, or SLA credits.

Material map: `proposed_updates.json` lists candidate changes. Service ticket evidence comes from `/api/tickets`, `/api/outages`, `/api/diagnostics`, and `/api/troubleshooting`. Contact-case evidence comes from `/api/cases`, `/api/lines`, and `/api/devices`. Enterprise evidence comes from `/api/enterprise/incidents`, `/api/enterprise/export-runs`, `/api/enterprise/messages`, and `/api/enterprise/sla`.

Solution and evaluation basis: The proposal set covers service gates, escalation-team corrections, mobile-device and plan-usage corrections, enterprise credit review, and authentication failure. There are 10 exact-match scoring points focused on business accept/reject decisions, corrected fields, defect breakdown, target service metrics, contact refuel evidence, enterprise credit evidence, and package-review permissions.

Transfer design: This task requires broad transfer. The solver must apply offline ticket status and metric rules from `train_001`/`train_004`, mobile action and refuel rules from `train_002`/`train_005`, and enterprise SLA-credit plus response-package conventions from `train_003`. The audit form and mixed proposal set are task-specific.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

## 中文

数据来源：本测试任务属于 `SCN_003_crm_service_ticket_resolution`，由全部五个训练任务锚定。可见 payload 列出跨 service ticket、contact-center case 和 enterprise incident 的拟议 CRM 更新。

任务定义：求解者需要审核每条拟议更新，接受正确项，用结构化原因代码修正错误的状态、动作、团队、refuel 数量或 credit 百分比，并填写模板要求的 QA evidence/package-review 字段。

场景适配：QA review 是真实 CRM 运营流程，支持负责人常常在更新影响客户沟通、升级队列或 SLA credit 前进行检查。

材料地图：`proposed_updates.json` 列出候选变更。服务工单证据来自 `/api/tickets`、`/api/outages`、`/api/diagnostics` 和 `/api/troubleshooting`；contact-case 证据来自 `/api/cases`、`/api/lines`、`/api/devices`；企业证据来自 `/api/enterprise/incidents`、`/api/enterprise/export-runs`、`/api/enterprise/messages` 和 `/api/enterprise/sla`。

答案与评测依据：proposal 集合覆盖服务 gate、升级团队修正、移动设备和 plan-usage 修正、企业 credit review 以及认证失败。评测有 10 个精确匹配点，集中在业务 accept/reject 决策、修正字段、defect breakdown、目标服务 metric、contact refuel 证据、企业 credit 证据和 package-review 权限。

迁移设计：本任务需要广泛迁移。求解者必须应用 `train_001`/`train_004` 的离线工单状态和 metric 规则、`train_002`/`train_005` 的移动动作和 refuel 规则，以及 `train_003` 的企业 SLA credit 与响应包约定。审计表单和混合 proposal 集合是本任务特有的。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化测试任务。
