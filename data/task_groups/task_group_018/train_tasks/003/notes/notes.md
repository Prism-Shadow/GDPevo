# train_003 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_018`, derived from scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and source examples `E001`, `E002`, and `E003`. It implements the assigned train task `train_003`: a Gloucester-style misdemeanor DUI/probation packet for two defendants.

The shared environment data is `task_group/task_group_018/env/data/clerk_ops.json`, especially the Gloucester case records, fee schedules, payment policy, financial obligations, docket entries, and attorney records. The task-local solver-visible payloads are:

- `input/payloads/hearing_packet.json`: sentencing packet and probation/license worksheets for Darla Nguyen (`23-GLO-00218`) and Hannah Foster (`24-GLO-01001`).
- `input/payloads/stale_order_extract.csv`: stale forms-queue extract with older or copied values and one distractor DUI record.
- `input/payloads/answer_template.json`: required output schema, enums, ordering, date formats, and currency precision.

### Task Definition

The solver acts as a clerk preparing a collateral order packet after DUI-related misdemeanor dispositions. The output must reconcile the two local sentencing packets with live environment records and produce structured JSON for conviction posture, charge outcomes, probation fields, license-suspension fields, missing identifier placeholders, financial assessment, installment schedule, and packet totals.

The required environment entry point is the placeholder `{ENV_BASE_URL}` in `prompt.txt`. Solvers should use the environment for live case records, financial ledgers, fee schedule rows, payment policy, and docket confirmation. They should use the local hearing packet for the sentencing packet contents and avoid copying stale extract values into final form fields when they conflict with stronger sources.

### Scenario Fit

This is a direct fit for the scenario because it combines criminal disposition reconciliation, collateral form preparation, fee schedule selection, and installment-order calculation. It mirrors the difficulty of the source examples: multiple sources disagree, fee rows have effective dates, a stale extract contains plausible but wrong values, and the final answer must keep the same conviction posture across probation, license, and payment fields.

### Material Map

- Live case records identify matter type, case number, defendant name and date of birth, charge IDs/statutes, disposition dates, status, sentence facts, probation months, license-suspension months, and similar/distractor records.
- Live financial obligations provide principal, amount paid, current balance, payment-plan status, monthly amount, next due date, and fee components.
- Gloucester fee schedules determine the correct fee code set and effective-date amounts. Darla Nguyen uses the 2023-2024 DUI fee amounts; Hannah Foster uses the 2025 DUI fee amounts plus the DUI probation monitoring fee because the local packet orders probation.
- Gloucester payment policy supplies the `TBD from case file` placeholder, 45-day first-due convention, and permission for a final smaller payment.
- `hearing_packet.json` supplies hearing-specific outcomes, report appointments, local probation addendum information, requested monthly amounts, and missing identity/contact fields.
- `stale_order_extract.csv` supplies noise: Darla's license start was copied from the probation appointment, Hannah's probation and license values are pre-disposition, and Renee Jones is not part of this packet.

### Solution and Evaluation Basis

The standard answer includes two defendants ordered by case number: `23-GLO-00218` Darla Nguyen and `24-GLO-01001` Hannah Foster.

Key answer facts:

- Darla Nguyen has posture `dui_conviction`. `DUI-101` is `convicted`; `DUI-104` is `convicted_no_separate_fee`. She has 24 months probation, report date `2024-04-16` at `09:00`, 12 months license suspension starting `2024-04-09`, treatment required, and missing driver license, phone, and probation officer placeholders.
- Hannah Foster has posture `amended_dui_reckless`. `DUI-210` is `amended`; `DUI-225` is `dismissed`. She has 12 months probation from the local addendum, report date `2025-01-08` at `10:30`, 6 months license suspension starting `2025-01-04`, treatment required, and the same three placeholder fields.
- Darla's financial order uses `DUI-CONV`, `DUI-LIC`, and `DUI-TREAT`; excludes `DUI-104`; principal is `602.50`; amount paid is `592.33`; current balance is `10.17`.
- Hannah's financial order uses `DUI-CONV`, `DUI-LIC`, `DUI-PROB`, and `DUI-TREAT`; principal is `737.50`; amount paid is `295.46`; current balance is `442.04`.
- Installment schedules use `plan_basis` `original_principal`, the packet's approved monthly amounts, first due dates 45 days after order date, and a final smaller payment. Darla: monthly `35.00`, first due `2024-05-24`, 17 regular payments, final `7.50`, 18 installments total, final due `2025-10-24`. Hannah: monthly `90.00`, first due `2025-02-18`, 8 regular payments, final `17.50`, 9 installments total, final due `2025-10-18`.
- Packet totals are principal `1340.00`, current balance `452.21`, payment plans `2`, and placeholder fields `6`.

The evaluator has 9 exact-match scoring points with raw weights:

- `SP001`, weight 2: target defendant set, ordering, names, and conviction posture.
- `SP002`, weight 2: charge-level outcomes and `DUI-104` exclusion treatment.
- `SP003`, weight 3: Darla collateral order fields.
- `SP004`, weight 3: Hannah collateral order fields.
- `SP005`, weight 2: required placeholder use.
- `SP006`, weight 2: Darla fee codes and ledger amounts.
- `SP007`, weight 3: Hannah fee codes and ledger amounts.
- `SP008`, weight 3: installment plan basis, dates, counts, monthly amounts, and final payments for both defendants.
- `SP009`, weight 1: packet totals and follow-up action codes.

Likely model pitfalls include using the stale extract's license start date, copying Hannah's pre-disposition zero-month probation hint, adding a separate `DUI-104` fee for Darla, using 2025 fee rows for Darla, omitting Hannah's DUI probation monitoring fee, using remaining balance rather than original principal as the schedule basis, inventing missing driver-license numbers or officer names, and ordering defendants by packet order instead of case number.

### Transfer Design

As a train task, this task lets a skill-builder infer several transferable conventions after comparing a blind attempt to the answer:

- Hearing packet facts control the post-sentencing form fields, while stale extracts are only warning/distractor material.
- Live financial ledgers and fee schedules should be used for account amounts and fee-code selection.
- Fee schedules depend on jurisdiction, matter type, code applicability, and effective date.
- Unsupported or no-separate-sentence codes should not create independent financial lines.
- Missing required identifiers and contact/order assignments use exactly `TBD from case file`.
- Collateral dates should remain consistent with the conviction/disposition date unless the packet supplies a different trigger.
- Installment schedules use full payments plus one final smaller payment, with first and final due dates calculated from the order date and county payment policy.

These are not presented as solver-visible step-by-step instructions. They are recorded here for review and later train-skill construction.

### Construction Record

Author: task-builder subagent for `train_003`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: created all task-local inputs, hidden notes, standard answer, and exact-match evaluator for the Gloucester DUI/probation packet.

## Chinese

### 数据与来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，参考示例为 `E001`、`E002` 和 `E003`。任务实现的是已分配的训练任务 `train_003`：Gloucester 风格的轻罪 DUI/缓刑文书包，涉及两名被告。

共享环境数据位于 `task_group/task_group_018/env/data/clerk_ops.json`，主要使用 Gloucester 的案件记录、费用表、付款政策、财务义务、案卷记录和律师记录。任务本地、求解器可见的材料包括：

- `input/payloads/hearing_packet.json`：Darla Nguyen (`23-GLO-00218`) 和 Hannah Foster (`24-GLO-01001`) 的量刑、缓刑和驾照停权工作表。
- `input/payloads/stale_order_extract.csv`：旧文书队列导出的过期数据，包含可能错误的旧值和一个干扰 DUI 记录。
- `input/payloads/answer_template.json`：规定输出结构、枚举、排序、日期格式和金额精度。

### 任务定义

求解器扮演书记员，在 DUI 相关轻罪裁判后准备附带命令文书。输出需要把本地量刑包与共享环境中的实时记录相互核对，形成结构化 JSON，包括定罪姿态、指控结果、缓刑字段、驾照停权字段、缺失标识符占位符、财务评估、分期付款安排以及包级合计。

`prompt.txt` 中使用 `{ENV_BASE_URL}` 作为环境入口占位符。求解器应使用环境查询实时案件、财务账、费用表、付款政策和案卷确认信息；本地听审材料用于听审时形成的文书字段；过期导出如果与更可靠来源冲突，不应直接复制。

### 场景适配

本任务符合该场景，因为它同时包含刑事裁判核对、附带文书准备、费用表选择和分期付款计算。它保留了源示例中的难点：多来源冲突、费用生效日期、过期导出中的合理但错误的值，以及在缓刑、驾照和付款字段中保持同一裁判姿态。

### 材料地图

- 实时案件记录用于确认案件类型、案号、被告姓名和生日、指控编号和法规、裁判日期、状态、量刑事实、缓刑月数、驾照停权月数以及相似干扰记录。
- 实时财务义务用于确认本金、已付款、当前余额、付款计划状态、月付款、下次到期日和费用组成。
- Gloucester 费用表用于确定正确费用代码和按生效日期选择金额。Darla Nguyen 使用 2023-2024 DUI 费用；Hannah Foster 使用 2025 DUI 费用，并因本地文书命令缓刑而包含 DUI 缓刑监督费。
- Gloucester 付款政策提供 `TBD from case file` 占位符、45 天首期到期规则，以及允许最后一期为较小金额。
- `hearing_packet.json` 提供听审形成的结果、报到预约、本地缓刑补充信息、批准的月付款和缺失字段。
- `stale_order_extract.csv` 提供噪声：Darla 的驾照开始日期被旧表复制为缓刑报到日期，Hannah 的缓刑和驾照字段是裁判前快照，Renee Jones 不属于本任务文书包。

### 解答与评估依据

标准答案包含两名被告，并按案号排序：`23-GLO-00218` Darla Nguyen 和 `24-GLO-01001` Hannah Foster。

关键答案事实如下：

- Darla Nguyen 的姿态为 `dui_conviction`。`DUI-101` 为 `convicted`；`DUI-104` 为 `convicted_no_separate_fee`。她有 24 个月缓刑，`2024-04-16` `09:00` 报到，驾照停权 12 个月，开始日期为 `2024-04-09`，需要治疗转介，驾照号、电话和缓刑官均使用占位符。
- Hannah Foster 的姿态为 `amended_dui_reckless`。`DUI-210` 为 `amended`；`DUI-225` 为 `dismissed`。她根据本地补充材料有 12 个月缓刑，`2025-01-08` `10:30` 报到，驾照停权 6 个月，开始日期为 `2025-01-04`，需要治疗转介，同样有三个占位符字段。
- Darla 的财务命令使用 `DUI-CONV`、`DUI-LIC` 和 `DUI-TREAT`，排除 `DUI-104`；本金为 `602.50`，已付 `592.33`，当前余额 `10.17`。
- Hannah 的财务命令使用 `DUI-CONV`、`DUI-LIC`、`DUI-PROB` 和 `DUI-TREAT`；本金为 `737.50`，已付 `295.46`，当前余额 `442.04`。
- 分期付款安排使用 `original_principal`，采用文书中批准的月付款金额，首期为命令日后 45 天，并允许最后一期较小。Darla：月付 `35.00`，首期 `2024-05-24`，17 个常规付款，最后一期 `7.50`，共 18 期，最后到期日 `2025-10-24`。Hannah：月付 `90.00`，首期 `2025-02-18`，8 个常规付款，最后一期 `17.50`，共 9 期，最后到期日 `2025-10-18`。
- 包级合计为本金 `1340.00`、当前余额 `452.21`、付款计划 `2` 个、占位符字段 `6` 个。

评估器包含 9 个精确匹配评分点，原始权重如下：

- `SP001`，权重 2：目标被告集合、排序、姓名和定罪姿态。
- `SP002`，权重 2：指控层级结果和 `DUI-104` 排除处理。
- `SP003`，权重 3：Darla 的附带命令字段。
- `SP004`，权重 3：Hannah 的附带命令字段。
- `SP005`，权重 2：占位符使用。
- `SP006`，权重 2：Darla 的费用代码和账务金额。
- `SP007`，权重 3：Hannah 的费用代码和账务金额。
- `SP008`，权重 3：两名被告的分期依据、日期、期数、月付款和最后一期金额。
- `SP009`，权重 1：包级合计和后续操作代码。

常见错误包括使用过期导出的驾照开始日期、复制 Hannah 裁判前的零个月缓刑提示、为 Darla 增加单独的 `DUI-104` 费用、给 Darla 使用 2025 费用、遗漏 Hannah 的 DUI 缓刑监督费、用剩余余额而不是原始本金计算分期、编造缺失的驾照号或缓刑官姓名，以及按文书顺序而不是案号排序。

### 迁移设计

作为训练任务，本任务在盲做并对照答案后，可以让 skill-builder 推断以下可迁移规则：

- 听审包中的事实控制裁判后文书字段，过期导出主要是警示或干扰材料。
- 账户金额和费用代码选择应使用实时财务账和费用表。
- 费用表取决于辖区、案件类型、代码适用条件和生效日期。
- 不支持或没有单独刑罚的代码不应创建独立财务项目。
- 缺失的必要身份、联系方式或分配字段使用精确字符串 `TBD from case file`。
- 附带命令日期应与定罪或裁判日期保持一致，除非文书给出不同触发条件。
- 分期付款采用若干完整付款加最后一个较小付款，并根据命令日期和县付款政策计算首期和末期日期。

这些内容不在求解器可见提示中作为步骤说明出现，而是用于评审和后续训练技能构建。

### 构建记录

作者：`train_003` 任务构建子代理。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：创建 Gloucester DUI/缓刑文书包的全部本地输入、隐藏说明、标准答案和精确匹配评估器。
