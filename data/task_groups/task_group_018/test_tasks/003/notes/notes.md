# test_003 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and source examples `E001`, `E002`, and `E003`. It implements a Middlesex County DUI post-hearing clerk-entry review for Victor Hayes (`24-MID-00077`), Fatima Hayes (`24-MID-01001`), and Isaac Nguyen (`24-MID-01007`).

The shared Clerk Operations environment supplies live Middlesex case records, docket/status records, DUI fee schedules, payment policy, live financial obligations, and return-to-court notice context. Solver-visible task-local files are `input/payloads/middlesex_dui_packet.json`, `input/payloads/stale_collateral_extract.csv`, and `input/payloads/answer_template.json`.

### Task Definition and Scenario Fit

The solver acts as a clerk preparing a reconciled DUI post-hearing packet for entry review. The answer must resolve the controlling record for each defendant, map charge outcomes, audit missing identity fields with the official placeholder, complete collateral orders, choose live-ledger or active-schedule financial facts, exclude unsupported candidate lines, compute payment plans, route return-to-court handling, and recompute packet totals.

This fits the scenario because the work combines disposition reconciliation, stale queue triage, collateral form preparation, live ledger review, fee-schedule use, installment calculations, and compliance routing. The task keeps the same long-horizon difficulty drivers as the source examples: multiple records disagree, local packet and live systems control different fields, and final structured output must be precise enough for clerk entry.

### Material Map

`middlesex_dui_packet.json` supplies the local bench sheets, probation referrals, draft license dates, contact slips, cashier snapshots, competing payment requests, finance candidate lines, and local return-to-court notes. `stale_collateral_extract.csv` supplies older queue/worklist rows and one out-of-packet distractor. The shared API supplies current case status, SID values, live obligations, active fee schedules, payment policy dates/amounts, and the existing return-to-court notice for Isaac.

The answer template defines the required shape and controlled enums. The final rework removed the per-defendant `audit_codes` field, removed packet `audit_code_count`, and simplified rejected license-start, rejected monthly-payment, and unsupported-fee detail rows to the objective source/date or source/amount facts. This avoids scoring brittle reason wording while preserving the real audit decisions.

### Solution and Evaluation Basis

The standard answer has three `defendants` ordered by case number and one `packet_totals` block.

Key answer facts:

- Victor is controlled by live records, has a DUI conviction on `2024-06-14`, uses the live ledger, keeps a policy-minimum `25.00` original-principal plan, and does not require return-to-court routing.
- Fatima is controlled by the later packet over the live open snapshot, has a DUI conviction on `2025-06-18`, uses the active fee schedule because no live obligation is open, uses a signed `125.00` original-principal plan, and excludes `DUI-104` as a no-separate-fee line.
- Isaac is controlled by live records, has an amended DUI-reckless posture on `2024-08-19`, uses the live ledger, keeps the live `35.00` plan while attaching the existing `2024-12-09` return-to-court notice, and computes installments over original principal.
- Missing required case-file fields use `TBD from case file`. Placeholder counts are Victor `4`, Fatima `5`, and Isaac `4`, for packet total `13`.
- License starts use the disposition date for all three cases. Rejected license-start rows record the non-controlling candidate source/date pairs.
- Assessed fee codes are `DUI-CONV`, `DUI-LIC`, `DUI-PROB`, and `DUI-TREAT` for all three defendants. Unsupported exclusions total `240.00`.
- Packet totals are principal `2175.00`, balance `1377.89`, 4 source rejections, 7 excluded candidate lines, 7 rejected monthly candidates, 8 rejected license-start candidates, 2 live-disposition cases, 1 local-packet-disposition case, 2 ledger-based cases, and 1 schedule-based case.

The evaluator has 9 exact-match scoring points with raw weights totaling 19:

| ID | Weight | Goal |
| --- | --- | --- |
| SP001 | 1 | Packet scope, ordering, names, conviction postures, order dates, and charge outcomes. |
| SP002 | 2 | Packet-vs-live source precedence and stale collateral extract rejection. |
| SP003 | 2 | Identity fields and official case-file placeholder audit. |
| SP004 | 3 | Collateral orders and rejected license-start candidate sources. |
| SP005 | 2 | Ledger-versus-schedule financial source and amount fields. |
| SP006 | 2 | Assessed fees and unsupported fee or charge exclusions. |
| SP007 | 3 | Payment-plan authority, original-principal math, and rejected monthly candidates. |
| SP008 | 2 | Return-to-court routing and follow-up actions. |
| SP009 | 2 | Packet-level aggregate recomputation from final rows. |

The rework intentionally gives limited weight to scope/source/ledger fields that direct solvers often obtained through mechanical API lookup, while keeping higher-value credit on collateral candidate rejection, original-principal plan math, return-to-court/live-plan routing, and aggregate recomputation. Historical sensitivity against the latest diagnostic predictions changed the old direct-after-second-rework attempts from `0.521739` to `0.473684` each, while the latest train-example post-skill attempts score `1.000000` and `0.368421`, averaging `0.684211`.

### Transfer Design

`train_003` anchors the DUI collateral workflow: stale extracts are conflict sources, license starts come from disposition or delayed surrender rather than copied queue dates, missing case-file fields use the official placeholder, DUI companion charges may be no-separate-fee items, and DUI/probation plans use original principal. `train_002` anchors effective fee-schedule use, unsupported candidate fee exclusion, policy dates/amounts, and full payments plus a smaller final payment. `train_005` anchors live-ledger/current-balance distinctions, approved versus unapproved payment requests, return-to-court routing with a retained live plan, and aggregate consistency checks.

The transfer-dependent scoring points are SP003, SP004, SP006, SP007, SP008, and SP009. SP002 and SP005 also benefit from train-derived source-precedence habits but remain partly discoverable from task-specific exploration. The prompt and payloads do not provide a solver-visible step list or answer path; the transfer comes from applying conventions inferred from the train answers.

### Construction Record

Author: task-builder calibration rework for `test_003`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: reworked after calibration showed direct avg `0.5217` and post-skill avg `0.4130` under the prior rubric. Removed solver-visible `audit_codes`, removed low-signal reason fields from several audit detail rows, reshaped scoring to 9 points with total raw weight 19, lowered mechanical lookup credit, and aligned high-value points with train-derived DUI collateral/payment-plan conventions.

## Chinese

### 数据与来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，参考示例为 `E001`、`E002` 和 `E003`。任务实现 Middlesex County DUI 庭后书记员录入复核，涉及 Victor Hayes (`24-MID-00077`)、Fatima Hayes (`24-MID-01001`) 和 Isaac Nguyen (`24-MID-01007`)。

共享 Clerk Operations 环境提供 Middlesex 实时案件、案卷和状态记录、DUI 费用表、付款政策、实时财务义务以及返庭通知背景。求解器可见的本地文件是 `input/payloads/middlesex_dui_packet.json`、`input/payloads/stale_collateral_extract.csv` 和 `input/payloads/answer_template.json`。

### 任务定义与场景适配

求解器扮演书记员，为 DUI 庭后事项准备经过核对的结构化录入复核包。答案需要确定每名被告的控制来源，映射指控结果，用官方占位符审计缺失身份字段，完成附带命令，选择实时账务或有效费用表财务事实，排除不支持的候选行，计算付款计划，处理返庭路由，并重新计算包级合计。

本任务符合源场景，因为它结合了裁判核对、旧队列分流、附带表格准备、实时账务复核、费用表使用、分期计算和合规路由。任务保留了源样例的长流程难点：多个记录相互冲突，本地 packet 与 live 系统分别控制不同字段，最终结构化输出必须精确到可用于书记员录入。

### 材料地图

`middlesex_dui_packet.json` 提供本地庭审表、缓刑转介、草拟停权日期、联系方式凭证、收款员快照、相互竞争的付款请求、财务候选行和本地返庭备注。`stale_collateral_extract.csv` 提供较旧的队列/工作清单行以及一个不属于本包的干扰案件。共享 API 提供当前案件状态、SID、实时财务义务、有效费用表、付款政策日期/金额，以及 Isaac 已存在的返庭通知。

答案模板定义输出结构和受控枚举。本次重构删除了每名被告的 `audit_codes` 字段、包级 `audit_code_count`，并把被排除停权开始、被排除月付和不支持费用明细简化为客观的 source/date 或 source/amount 事实。这样避免把易碎的 reason 文案作为评分重点，同时保留真实审计判断。

### 解答与评估依据

标准答案包含三个按案号排序的 `defendants` 和一个 `packet_totals` 汇总块。

关键事实如下：

- Victor 由实时记录控制，`2024-06-14` DUI 定罪，使用实时账务，保留政策最低 `25.00` 的原始本金计划，不需要返庭。
- Fatima 由较新的本地 packet 控制并覆盖 live open 快照，`2025-06-18` DUI 定罪；因为没有实时财务义务，所以使用有效费用表；使用已签署的 `125.00` 原始本金计划，并把 `DUI-104` 作为无单独费用行排除。
- Isaac 由实时记录控制，`2024-08-19` 为 amended DUI-reckless，使用实时账务，在返庭处理中保留 live `35.00` 计划并附加 `2024-12-09` 的既有通知，分期仍按原始本金计算。
- 缺失的必填案卷字段使用 `TBD from case file`。占位符数量为 Victor `4`、Fatima `5`、Isaac `4`，包级合计 `13`。
- 三个案件的驾照停权开始均使用裁判日期。被排除停权开始行记录非控制性候选的 source/date。
- 三名被告的应评估费用代码均为 `DUI-CONV`、`DUI-LIC`、`DUI-PROB` 和 `DUI-TREAT`。不支持排除金额合计为 `240.00`。
- 包级合计为本金 `2175.00`、余额 `1377.89`、4 个来源排除、7 个排除候选行、7 个被排除月付候选、8 个被排除停权开始候选、2 个 live 裁判案件、1 个本地 packet 裁判案件、2 个账务来源案件和 1 个费用表来源案件。

评估器包含 9 个 exact-match 评分点，原始权重合计 19：

| ID | 权重 | 目标 |
| --- | --- | --- |
| SP001 | 1 | 包范围、排序、姓名、定罪姿态、命令日期和指控结果。 |
| SP002 | 2 | packet 与 live 的来源优先级，以及旧 collateral extract 的排除。 |
| SP003 | 2 | 身份字段和官方案卷占位符审计。 |
| SP004 | 3 | 附带命令和被排除停权开始候选来源。 |
| SP005 | 2 | 账务与费用表来源选择及金额字段。 |
| SP006 | 2 | 应评估费用和不支持费用或指控排除。 |
| SP007 | 3 | 付款计划来源、原始本金计算和被排除月付候选。 |
| SP008 | 2 | 返庭路由和后续动作。 |
| SP009 | 2 | 从最终行重新计算包级合计。 |

本次重构有意降低 direct 求解者容易通过机械 API 查询获得的范围、来源和账务字段权重，把更高价值的分数放在附带候选排除、原始本金计划计算、返庭/保留 live plan 路由和合计重算上。用最新诊断预测做敏感性检查时，旧的 direct-after-second-rework 两次尝试从 `0.521739` 调整为各 `0.473684`，最新 train-example post-skill 两次尝试为 `1.000000` 和 `0.368421`，平均 `0.684211`。

### 迁移设计

`train_003` 锚定 DUI 附带命令工作流：旧 extract 只是冲突来源，停权开始来自裁判日期或 delayed surrender 而不是复制队列日期，缺失案卷字段使用官方占位符，DUI 伴随指控可能是无单独费用项，DUI/probation 付款计划以原始本金为依据。`train_002` 锚定费用表生效日期、不支持候选费用排除、付款政策日期/金额，以及完整付款加较小尾款。`train_005` 锚定实时账务与当前余额区分、已批准与未批准付款请求、返庭时保留 live 计划，以及合计一致性检查。

依赖迁移的评分点是 SP003、SP004、SP006、SP007、SP008 和 SP009。SP002 与 SP005 也受益于训练中学到的来源优先级习惯，但仍可部分通过本任务探索发现。prompt 和 payload 不提供求解器可见的步骤清单或答案路径；迁移来自对训练答案中惯例的归纳和应用。

### 构建记录

作者：`test_003` 校准重构。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：先前校准显示旧 rubric 下 direct avg 为 `0.5217`、post-skill avg 为 `0.4130`，因此进行了本次重构。删除求解器可见的 `audit_codes`，删除多个审计明细中的低信号 reason 字段，将评分调整为 9 个点、原始总权重 19，降低机械查询可得分数，并使高价值评分点对齐训练任务中可迁移的 DUI 附带命令和付款计划惯例。
