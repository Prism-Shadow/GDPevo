# train_005 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, with the strongest anchor in telecom support example `E002`. The visible worklist names five mobile-data cases; the API provides cases, lines, devices, plans, and bills.

Task definition: The solver must decide the primary and secondary operation for each data-support case, calculate any data-refuel charge, and summarize worklist action families.

Scenario fit: The task captures contact-center data recovery where the correct route depends on distinguishing user phone settings, carrier line settings, usage-limit recovery, and human transfer.

Material map: `/api/cases/<id>` gives case context; `/api/lines/<id>` and `/api/plans/<id>` support refuel and roaming decisions; `/api/devices/<id>` supports data saver, network mode, and mobile-data switch decisions.

Solution and evaluation basis: `CASE-2501` requires 2.0 GB refuel at 2.00 USD/GB; `CASE-2502` requires carrier line roaming enablement; the remaining three are device-setting fixes. There are 8 exact-match scoring points.

Transfer design: As a train task, it reinforces the distinction between phone roaming and carrier line roaming, data-limit recovery with price calculation, and slow-data setting fixes.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

## 中文

数据来源：本任务来自 `SCN_003_crm_service_ticket_resolution`，主要锚定电信支持样例 `E002`。可见 worklist 指定五个移动数据 case；API 提供 cases、lines、devices、plans 和 bills。

任务定义：求解者需要为每个数据支持 case 判断主操作和后续操作，计算数据 refuel 费用，并汇总动作类别。

场景适配：该任务体现联络中心移动数据恢复，关键在于区分用户手机设置、运营商线路设置、流量超限恢复和转人工。

材料地图：`/api/cases/<id>` 提供 case 语境；`/api/lines/<id>` 与 `/api/plans/<id>` 支持 refuel 和 roaming 判断；`/api/devices/<id>` 支持 data saver、network mode 和 mobile data 开关判断。

答案与评测依据：`CASE-2501` 需要 2.0 GB refuel，单价 2.00 USD/GB；`CASE-2502` 需要运营商侧启用线路漫游；其余三个是设备设置修复。评测有 8 个精确匹配点。

迁移设计：作为训练任务，它强化 phone roaming 与 carrier line roaming 的区别、含价格计算的数据超限恢复，以及 slow-data 设置修复。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化任务。
