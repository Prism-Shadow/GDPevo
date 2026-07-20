# train_003 Notes

## English

### Data lineage and task definition

This task belongs to `task_group_018`, derived from source scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries`, especially source example `E003`. It is a Virginia Gloucester County post-sentencing paperwork task for case `VA-CR24-0716-00` and payment petition `VA-PET-716A`.

The solver-visible inputs are:

- `input/prompt.txt`, which names the case and petition and points to the Court Operations Portal through `<TASK_ENV_BASE_URL>`.
- `input/payloads/sentencing_intake_facts.json`, which supplies the courtroom sentence, probation reporting instruction, release date, and missing identifier/contact facts.
- `input/payloads/payment_petition_budget.json`, which supplies the first payment petition, balance, budget, requested monthly amount, and unsupported-item warnings.
- `input/payloads/form_field_excerpt.json`, which describes the CC-1375 and CC-1379-style field groups and the exact placeholder text.
- `input/payloads/answer_template.json`, which defines the required JSON output shape, date and currency precision, enum choices, and list ordering.

The shared environment provides corroborating records through `GET /api/cases`, `GET /api/financial-petitions`, `GET /api/payment-policies`, `GET /api/forms`, and related search endpoints. The relevant generated records are the Gloucester jurisdiction, `VA-CR24-0716-00`, `VA-PET-716A`, policy `POL-VA-GLO-FIRST`, and forms `VA_CC1375` and `VA_CC1379`.

### Scenario fit and material map

The task models a deputy clerk carrying a single DUI sentence into a case-management memo, a CC-1375-style probation referral, and a CC-1379-style license/payment order. It fits the group because it combines disposition facts, form mapping, payment-policy lookup, installment math, and disciplined handling of missing official identifiers. These are the same business objects and data flow as the source Virginia example, but expressed as structured benchmark output and environment-backed records.

Important material use:

- The sentencing intake controls the conviction posture: conviction date `2024-09-18`, DUI first offense, 12 months jail with 11 months suspended, $1,100 fine, $160 costs, 12 months supervised probation, 12-month license suspension, and release on `2024-10-07`.
- The payment petition controls the financial agreement facts: first petition, $1,260 fines/costs balance, $0 restitution, no account fee, $75 monthly request, and current non-default posture.
- The payment policy confirms that Gloucester first-petition installment orders have no down payment, a $50-$100 monthly band, 30 days to first due date, and a 60-day return-to-court offset.
- The form catalog confirms form IDs and placeholder instructions for `VA_CC1375` and `VA_CC1379`.

### Solution and evaluation basis

The standard answer keeps the conviction posture consistent across all deliverables. The CC-1375 referral reports supervised probation for 12 months and a report date-time of `2024-10-10T09:00:00`. The CC-1379 license consequence is a 12-month suspension effective from the conviction date `2024-09-18`, not the release date. The payment order is an initial installment under `POL-VA-GLO-FIRST`: $1,260 total, no restitution, no account fee, no down payment, $75 monthly, first due `2024-11-09`, 16 full installments, a final partial payment of $60, 17 payments total, final due `2026-03-09`, and return to court on `2026-05-08` at `09:00` for nonpayment.

Budget math uses $1,920 monthly income minus $1,340 obligations for $580 disposable income. The selected $75 monthly installment is inside the $50-$100 policy band and is classified as `supported_by_budget`.

Unknown SSN, mailing address, residence address, phone, driver license number, probation officer, and probation office location use exactly `TBD from case file`. The evaluator also checks that answerable fields such as case number, defendant name, total due, report date, and suspension date are not replaced by the placeholder.

The evaluator has 9 whole-point scoring checks:

- `SP001` weight 2: case memo identity, sentence posture, and required work flags.
- `SP002` weight 2: CC-1375 probation referral and report instruction.
- `SP003` weight 2: CC-1379 license suspension tied to conviction date.
- `SP004` weight 3: initial installment classification and balance components.
- `SP005` weight 3: installment schedule math, final partial payment, and final due date.
- `SP006` weight 2: budget review, policy band, and support classification.
- `SP007` weight 2: placeholder discipline.
- `SP008` weight 1: unsupported financial item and restitution exclusions.
- `SP009` weight 1: return-to-court setting.

These points cover at least four distinct outcomes: memo/disposition mapping, probation referral, license consequence, installment policy and math, budget support, placeholder handling, financial exclusions, and return-to-court handling. Each point is deterministic and all-or-nothing.

Likely model pitfalls include copying a stale or noisy charge disposition instead of the sentencing intake, using the release date as the suspension date, treating the first petition as a subsequent/default review, adding unsupported restitution or account-management fees, choosing an installment outside the policy band, omitting the final partial payment, or inventing SSN/address/driver-license/probation-office details.

### Transfer design

As a train task, this provides real solved experience for the Virginia probation/license/payment family. A fewshot skill can infer that court forms must keep sentence posture consistent across separate deliverables, that Gloucester first-petition installment agreements use the local policy rather than invented fees, that payment schedules require exact final partial-payment math, and that unknown form identifiers must use `TBD from case file` rather than fabricated values. This anchors later Virginia test tasks that change the case facts, petition posture, missing fields, and schedule amounts while preserving the same clerk-work conventions.

### Construction record

Author: Codex task-builder subagent for `train_003`.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: Created the full `train_tasks/003` task folder with solver prompt, three local payloads, answer template, standard answer, deterministic evaluator, and bilingual notes.

## 中文

### 数据来源与任务定义

本任务属于 `task_group_018`，来源于 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要锚定源示例 `E003`。任务是 Virginia Gloucester County 的判后文书字段整理，目标案件为 `VA-CR24-0716-00`，付款申请为 `VA-PET-716A`。

求解者可见材料包括：

- `input/prompt.txt`：说明目标案件和申请，并通过 `<TASK_ENV_BASE_URL>` 指向 Court Operations Portal。
- `input/payloads/sentencing_intake_facts.json`：提供庭审判决、缓刑报到、释放日期以及缺失身份和联系方式信息。
- `input/payloads/payment_petition_budget.json`：提供首次付款申请、余额、预算、请求月付款额和不得添加的费用项目。
- `input/payloads/form_field_excerpt.json`：给出 CC-1375 与 CC-1379 风格字段组和精确占位文本。
- `input/payloads/answer_template.json`：定义 JSON 输出结构、日期和金额精度、枚举值以及列表排序要求。

共享环境提供可核对的数据，包括 Gloucester 管辖区、案件 `VA-CR24-0716-00`、申请 `VA-PET-716A`、政策 `POL-VA-GLO-FIRST`、表格 `VA_CC1375` 和 `VA_CC1379`。

### 场景适配与材料用途

该任务模拟法院书记员把一个 DUI 判决整理进案件管理备忘录、CC-1375 风格缓刑转介和 CC-1379 风格驾照暂停及分期付款命令。它符合本任务组，因为它同时涉及处分事实、表格映射、付款政策查询、分期计算和缺失官方身份字段的规范占位处理。

关键材料用途如下：

- sentencing intake 决定判决姿态：定罪日期 `2024-09-18`，DUI first offense，12 个月监禁且 11 个月缓刑，$1,100 罚金，$160 诉讼成本，12 个月监督缓刑，12 个月驾照暂停，`2024-10-07` 释放。
- payment petition 决定财务协议事实：首次申请，罚金和成本余额 $1,260，restitution 为 $0，无 account fee，请求每月 $75，且当前没有 default。
- payment policy 确认 Gloucester 首次分期付款命令无首付款、月付款范围 $50-$100、30 天后首次到期、最终到期后 60 天返庭。
- form catalog 确认 `VA_CC1375` 和 `VA_CC1379` 的表格 ID 与占位要求。

### 解答与评测依据

标准答案在所有交付物中保持一致的定罪姿态。CC-1375 转介记录 12 个月 supervised probation，并要求 `2024-10-10T09:00:00` 报到。CC-1379 的驾照暂停为 12 个月，生效日期使用定罪日期 `2024-09-18`，而不是释放日期。付款命令为 `POL-VA-GLO-FIRST` 下的首次分期：总额 $1,260，无 restitution，无 account fee，无首付款，每月 $75，首次到期 `2024-11-09`，16 次完整付款，最终部分付款 $60，共 17 次，最终到期 `2026-03-09`，如未付款则 `2026-05-08` `09:00` 返庭。

预算计算为 $1,920 月收入减 $1,340 月义务，剩余 $580；选择的 $75 月付款在 $50-$100 政策范围内，因此分类为 `supported_by_budget`。

缺失的 SSN、邮寄地址、居住地址、电话、驾照号、缓刑官和缓刑办公室地点均使用精确文本 `TBD from case file`。评测器还会检查可确定字段没有被错误替换成占位符。

评测包含 9 个整点评分项：

- `SP001` 权重 2：案件备忘录身份、判决姿态和所需后续工作标志。
- `SP002` 权重 2：CC-1375 缓刑转介和报到指令。
- `SP003` 权重 2：CC-1379 驾照暂停，并绑定定罪日期。
- `SP004` 权重 3：首次分期分类和余额组成。
- `SP005` 权重 3：分期次数、最终部分付款和最终到期日期。
- `SP006` 权重 2：预算、政策范围和可支持性分类。
- `SP007` 权重 2：占位字段规范。
- `SP008` 权重 1：排除无依据的费用和 restitution。
- `SP009` 权重 1：返庭日期、时间和触发原因。

这些评分点覆盖备忘录/处分映射、缓刑转介、驾照后果、分期政策和计算、预算支持、占位处理、财务排除和返庭处理等多个不同业务结果。每个评分点都是确定性的整点通过或失败。

常见错误包括：复制噪声 charge disposition 而不是 sentencing intake；把释放日期当作暂停生效日期；把首次申请误判为 subsequent/default review；添加无依据的 restitution 或 account-management fee；选择不符合政策范围的月付款；遗漏最终部分付款；编造 SSN、地址、驾照号或缓刑办公室信息。

### 迁移设计

作为训练任务，本任务为 Virginia probation/license/payment 任务族提供真实解答经验。fewshot skill 可以从中推断：不同文书必须保持同一判决姿态；Gloucester 首次分期应使用本地政策而不是发明费用；付款计划需要精确计算最终部分付款；缺失表格身份信息应使用 `TBD from case file`，不得编造。后续 Virginia 测试任务会改变案件事实、申请状态、缺失字段和付款数额，但保留这些书记员工作惯例。

### 构造记录

作者：Codex task-builder subagent for `train_003`。

创建日期：2026-07-18。

更新日期：2026-07-18。

主要变更：创建完整的 `train_tasks/003` 文件夹，包括求解者 prompt、三个本地 payload、answer template、标准答案、确定性 evaluator 和双语 notes。
