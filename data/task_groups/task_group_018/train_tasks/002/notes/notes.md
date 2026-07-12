# train_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and especially source example `E002`, with supporting transfer links to `E001` and `E003` for clerk-source reconciliation and form-field discipline. The shared generated environment is `task_group/task_group_018/env/data/clerk_ops.json`, exposed through the clerk operations HTTP service. The task-local visible packet is `input/payloads/lane_traffic_batch_packet.json`; the solver-visible output contract is `input/payloads/answer_template.json`.

### Task Definition and Scenario Fit

The solver acts as a Lane County Justice Court traffic clerk preparing a batch entry for three citations: `CIT-LAN-2024-00411`, `CIT-LAN-2025-00701`, and `CIT-LAN-2025-00702`. The work combines traffic disposition entry, financial assessment, unsupported-charge exclusion, and installment-plan calculation. This matches the scenario because it requires the same court-clerk pattern as the Oregon source example: identify the correct citation/account, choose the applicable fine or fee rows, avoid unsupported additions, and calculate a payment plan that resolves the balance.

### Material Map

The prompt gives the environment placeholder `{ENV_BASE_URL}` and directs the solver to the local packet and template. The local packet identifies the target citations, bench-order facts, candidate fee-code traps, and stale-import warnings. The shared API provides live citation rows, Lane traffic fee schedules by effective date, the Lane payment policy with minimum monthly amount and default first-due-date rule, and stale exports that contain a near-duplicate citation for Evan Turner/Tuner.

### Solution and Evaluation Basis

The correct answer uses the citation number as the account reference for all three entries. `CIT-LAN-2024-00411` remains Evan Turner, no contest, convicted, order date `2024-11-08`; the active traffic base fine on that date is obsolete `TR-BASE` at `115.00`, while `TR-SPEED` is not active and `TR-LATE` is not ordered. Its live plan terms are `45.00` monthly beginning `2024-12-09`, giving two full payments and a final `25.00` payment due `2025-02-09`.

`CIT-LAN-2025-00701` uses the bench packet as the current hearing result over the live pending citation: no contest, convicted, order date `2025-07-23`. The active 2025 `TR-BASE` amount is `130.00`; `TR-231` and `TR-SCHOOL` are excluded. The approved low plan uses Lane policy minimum `35.00`; with no announced first due date, the policy gives 35 days after order, `2025-08-27`. The plan has three full payments and a final `25.00` payment due `2025-11-27`.

`CIT-LAN-2025-00702` is Kara Turner, guilty, convicted, order date `2025-07-29`, with active `TR-BASE` at `130.00`; `TR-LATE` and `TR-SCHOOL` are excluded. Its live plan is `40.00` monthly beginning `2025-08-28`, giving three full payments and a final `10.00` due `2025-11-28`. Batch assessed total is `375.00`, total full payments are `8`, total final-payment amount is `60.00`, and all plans are entered after disposition.

The evaluator has eight exact-match scoring points with raw weights: target citation/account set and ordering (2), plea/disposition/order dates (2), assessed components (3), citation and batch totals (3), excluded candidate codes (2), plan status/monthly/first due dates (2), installment math and final due dates (3), and batch plan aggregates (1). Likely pitfalls are merging `CIT-LAN-2024-00412`, using a stale 2024 export as final authority, applying current 2025 fees to the 2024 order, adding optional school or late fees, treating `TR-231` as an add-on, accepting the below-minimum plan request for Owen Vargas, or rounding the final installment away.

### Transfer Design

As a train task, this is a real calibration task rather than a tutorial. After comparing an attempt to the answer, a skill-builder should infer that citation/account identifiers must be kept stable, live records and bench packets must be reconciled by event timing, fee schedules are selected by county, matter type, code, and effective date, unsupported candidate charges should be excluded unless expressly ordered, and payment plans use full payments plus a final smaller payment. The task also reinforces the group convention that citation numbers can serve as account references where no case number exists.

### Construction Record

Author: Codex task-builder subagent. Created: 2026-07-07. Updated: 2026-07-07. Major changes: created the train_002 prompt, task-local Lane traffic packet, output template, standard answer, exact-match evaluator, and bilingual notes.

## 中文

### 数据与来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，核心锚点是 `E002` 的 Oregon traffic violation 和 extended payment plan 任务，同时也延续 `E001`、`E003` 中的书记员多来源核对与表格字段一致性要求。共享环境数据位于 `task_group/task_group_018/env/data/clerk_ops.json`，通过 clerk operations HTTP 服务暴露。任务本地可见材料是 `input/payloads/lane_traffic_batch_packet.json`，输出格式由 `input/payloads/answer_template.json` 定义。

### 任务定义与场景适配

求解者扮演 Lane County Justice Court 的 traffic clerk，为 `CIT-LAN-2024-00411`、`CIT-LAN-2025-00701`、`CIT-LAN-2025-00702` 三张 citation 准备批量 post-hearing entry。任务包含 disposition entry、financial assessment、排除未支持费用，以及 installment plan 计算。这与源场景一致：书记员需要识别正确 citation/account，选用适用的 fine 或 fee schedule，避免加入未获支持的费用，并计算能结清余额的付款计划。

### 材料地图

Prompt 提供 `{ENV_BASE_URL}` 环境占位符，并指向本地 packet 与 answer template。本地 packet 给出目标 citation、bench order 事实、候选 fee-code 陷阱和 stale import 警告。共享 API 提供 live citation 记录、Lane traffic fee schedule、Lane installment policy，以及包含 Evan Turner/Tuner 近似冲突的 stale export。

### 解答与评测依据

标准答案中三条记录都使用 citation number 作为 account reference。`CIT-LAN-2024-00411` 为 Evan Turner，no contest，convicted，order date 为 `2024-11-08`；该日期适用的 `TR-BASE` 为 `115.00`，`TR-SPEED` 在该日未生效且 `TR-LATE` 未被 ordered，所以不录入。付款计划为每月 `45.00`，首期 `2024-12-09`，两个完整付款后，最后 `25.00` 于 `2025-02-09` 到期。

`CIT-LAN-2025-00701` 使用 bench packet 的当前庭审结果覆盖 live citation 中的 pending 状态：no contest，convicted，order date 为 `2025-07-23`。2025 年有效的 `TR-BASE` 是 `130.00`，排除 `TR-231` 和 `TR-SCHOOL`。由于法官批准最低可行月付且未宣布首期日期，使用 Lane policy 的最低月付 `35.00` 和 order 后 35 天首期，即 `2025-08-27`；三个完整付款后，最后 `25.00` 于 `2025-11-27` 到期。

`CIT-LAN-2025-00702` 为 Kara Turner，guilty，convicted，order date 为 `2025-07-29`，适用 `TR-BASE` `130.00`，排除 `TR-LATE` 和 `TR-SCHOOL`。付款计划为每月 `40.00`，首期 `2025-08-28`，三个完整付款后，最后 `10.00` 于 `2025-11-28` 到期。批量 assessed total 为 `375.00`，完整付款总数为 `8`，final payment 总额为 `60.00`，三项计划均为 disposition 后录入。

评测器包含 8 个 exact-match 评分点，原始权重分别是：目标 citation/account 集合与顺序 2，plea/disposition/order date 2，assessed components 3，citation 与 batch totals 3，排除候选代码 2，plan status/monthly/first due date 2，installment math 与 final due date 3，batch aggregate 1。常见错误包括合并 `CIT-LAN-2024-00412`、把 stale export 当作最终依据、给 2024 order 套用 2025 fee、加入 school 或 late fee、把 `TR-231` 当附加费用、接受低于政策下限的 Owen Vargas 月付请求，或把最后一期余数四舍五入掉。

### 迁移设计

这是训练任务，不是教程。通过做题并对照答案，skill-builder 应能归纳出：citation/account identifier 必须稳定保留；live record 与 bench packet 要按事件时间和内容 reconcile；fee schedule 要按 county、matter type、fee code 和 effective date 选择；候选费用未被明确 ordered 时不能加入；payment plan 应使用若干完整付款加最后较小余款。该任务还强化了无单独 case number 时可用 citation number 作为 account reference 的约定。

### 构造记录

作者：Codex task-builder subagent。创建日期：2026-07-07。更新日期：2026-07-07。主要变更：创建 train_002 的 prompt、本地 Lane traffic packet、answer template、标准答案、exact-match evaluator 与双语 notes。
