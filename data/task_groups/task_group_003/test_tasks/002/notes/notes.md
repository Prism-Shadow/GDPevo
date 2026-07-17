# test_002 Notes

## English

Data lineage: This test task belongs to `SCN_003_crm_service_ticket_resolution` and is anchored by `train_002` and `train_005`. The visible input is `case_queue.json`; the support-console API contains cases, customer lines, devices, plans, and bills.

Task definition: The solver triages five mobile support cases and returns action enums, final routes, reason codes, and refuel charge fields when a plan-limit case requires them.

Scenario fit: The task models CRM contact-center support across no-service, MMS, slow-data, and roaming issues, preserving the policy-driven branch selection from the source telecom example.

Material map: `/api/cases/<id>` links case IDs to line and device records. `/api/lines/<id>` reveals suspension/contract/roaming state. `/api/devices/<id>` reveals SIM, APN/MMSC, data saver, and phone roaming state.

Solution and evaluation basis: The queue includes unresolvable policy cases, MMS/APN recovery, plan-usage recovery, and carrier-side roaming recovery. There are 10 scoring points focused on business actions, route counts, refuel calculation, source-family classification, target evidence sets, and low-weight inventory/line/device consistency audits.

Transfer design: The main transfer points come from `train_002` and `train_005`: use line, device, bill, and plan records as source of truth; separate device-configuration, carrier-line, plan-allowance/data-recovery, billing-recovery, and human-handoff source families; calculate refuel amounts/prices from the plan. The target queue adds new state combinations, so the solver must inspect current evidence rather than apply memorized codes.

Construction record: Created by Codex on 2026-06-01. Major change: initial test task construction for `task_group_003`.

## 中文

数据来源：本测试任务属于 `SCN_003_crm_service_ticket_resolution`，由 `train_002` 和 `train_005` 锚定。可见输入是 `case_queue.json`；共享 API 包含 cases、lines、devices、plans 和 bills。

任务定义：求解者需要分诊五个移动支持 case，输出动作枚举、最终路由、原因代码，并在 plan-limit case 需要时给出 refuel 金额字段。

场景适配：该任务覆盖 no-service、MMS、slow-data 和 roaming 问题，保留源 telecom 样例中的政策化分支判断。

材料地图：`/api/cases/<id>` 连接 case 与 line/device；`/api/lines/<id>` 暴露停机、合同和线路漫游状态；`/api/devices/<id>` 暴露 SIM、APN/MMSC、data saver 和手机漫游状态。

答案与评测依据：队列覆盖无法自助处理的政策 case、MMS/APN 恢复、plan-usage 恢复和运营商侧漫游恢复。评测有 10 个得分点，集中在业务动作、路由汇总、refuel 计算、source-family 分类、目标证据集合和低权重的 inventory/line/device 一致性核查。

迁移设计：主要迁移来自 `train_002` 和 `train_005`：以 line、device、bill、plan 记录作为事实来源，区分 device-configuration、carrier-line、plan-allowance/data-recovery、billing-recovery 和 human-handoff source families，并从 plan 计算 refuel 数量/价格。目标队列加入新的状态组合，因此必须检查当前证据，而不是套用记忆代码。

构造记录：Codex 创建于 2026-06-01。主要变更：为 `task_group_003` 初始化测试任务。
