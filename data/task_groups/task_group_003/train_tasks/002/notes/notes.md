# train_002 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, especially source example `E002`. The visible queue is `input/payloads/case_queue.json`; the support-console API provides customer, line, bill, plan, and device records.

Task definition: The solver acts as a contact-center lead and chooses the next support operation plus any follow-up operation for five mobile support cases. The output is controlled by enums to avoid free-form action wording.

Scenario fit: The task models CRM technical support triage where the agent must identify the right layer: SIM, billing suspension, roaming, app permissions, or VPN.

Material map: `/api/cases/<id>` maps cases to customer, line, and device IDs. `/api/lines/<id>`, `/api/devices/<id>`, `/api/bills?customer_id=...`, and `/api/plans/<id>` contain the evidence for action selection.

Solution and evaluation basis: The correct actions are `RESEAT_SIM`, `SEND_PAYMENT_REQUEST` plus `RESUME_LINE_REBOOT`, `TOGGLE_ROAMING`, `GRANT_MESSAGING_PERMISSION` for storage, and `DISCONNECT_VPN`. There are 8 exact-match scoring points.

Transfer design: As a train task, it exposes the distinction between phone-state fixes, billing recovery, and transfer/carrier routes. It reinforces that mobile-data and MMS issues depend on lower-layer connectivity and device state.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

## 中文

数据来源：本任务来自 `SCN_003_crm_service_ticket_resolution`，主要对应 `E002`。可见队列为 `input/payloads/case_queue.json`，共享 API 提供 customer、line、bill、plan 和 device 记录。

任务定义：求解者扮演联络中心负责人，为五个移动支持 case 选择下一步操作和必要的后续操作。输出使用受控枚举，避免自由文本动作带来的评测摩擦。

场景适配：该任务刻画 CRM 技术支持分诊，需要判断问题位于 SIM、账单停机、漫游、应用权限还是 VPN 层。

材料地图：`/api/cases/<id>` 连接 case 与 customer、line、device；`/api/lines/<id>`、`/api/devices/<id>`、`/api/bills?customer_id=...`、`/api/plans/<id>` 提供动作判断证据。

答案与评测依据：正确操作依次是 `RESEAT_SIM`、`SEND_PAYMENT_REQUEST` 加 `RESUME_LINE_REBOOT`、`TOGGLE_ROAMING`、为 storage 执行 `GRANT_MESSAGING_PERMISSION`、以及 `DISCONNECT_VPN`。评测有 8 个精确匹配点。

迁移设计：作为训练任务，它让模型归纳 phone-state 修复、账单恢复、转人工/运营商更新之间的区别，并强化移动数据和 MMS 需要先看底层连接与设备状态。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化任务。
