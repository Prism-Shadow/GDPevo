# train_004 Notes - Union County Criminal Disposition Audit/Register

## English Review Notes

### Data and Source Lineage

This task belongs to `task_group_018`, based on source scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries` and examples `E001`, `E002`, and `E003`. It is the second Arkansas criminal closeout train task and reinforces the criminal disposition/register conventions from `train_001` with different Union County facts.

The shared environment is the generated Court Operations Portal under `task_group/task_group_018/env/`, especially the read-only tables behind `GET /api/cases`, `GET /api/charges`, `GET /api/docket-entries`, `GET /api/fee-schedules`, and `GET /api/search`. The task-local solver-visible payloads are:

- `input/payloads/union_county_hearing_notes.md`: courtroom outcome notes from Judge Holland's May 20, 2025 docket.
- `input/payloads/finance_memo_and_worksheet.csv`: noisy finance worksheet with stale and conflicting outcomes.
- `input/payloads/answer_template.json`: required JSON shape, enums, currency precision, dates, and ordering rules.

Target cases are `UC-25-0221`, `UC-25-0224`, `UC-25-0230`, `UC-24-0775`, and `UC-25-0238`.

### Task Definition and Scenario Fit

The solver acts as a criminal clerk preparing a disposition audit and register batch. They must reconcile hearing notes, a worksheet, and portal records before entering disposition status, audit decisions, financial postings, docket/register actions, aggregate totals, and exclusions.

This matches the source court-clerk scenario: it combines courtroom notes, CMS identity/status records, charge and fee data, local worksheet conflicts, financial posting, and docket/register preparation. It preserves realistic office-work complexity without being a tutorial.

### Material Map

The hearing notes are the best source for courtroom outcomes: amended count on `UC-25-0221`, no-contest guilty controlled-substance conviction on `UC-25-0224`, guilty plea with missing DOB on `UC-25-0230`, bench-trial guilty with appointed private defense counsel on `UC-24-0775`, and continued/no final order on `UC-25-0238`.

The worksheet introduces conflicts: it incorrectly treats `UC-25-0221` as a controlled-substance conviction with a lab fee, misses the lab fee on `UC-25-0224`, carries a blank DOB for `UC-25-0230`, labels `UC-24-0775` as `APD`, and suggests a draft disposition/financial posting for `UC-25-0238`.

The portal supplies identity, case status, counsel metadata, and Union County fees. The relevant fee schedule is `AR-UC`: circuit criminal court cost `150.00` for disposed criminal cases and crime laboratory fee `75.00` for controlled-substance convictions. No disposition or fee should be posted for the pending continued matter.

### Solution and Evaluation Basis

The standard answer:

- Enters four disposed cases: `UC-24-0775`, `UC-25-0221`, `UC-25-0224`, and `UC-25-0230`.
- Excludes `UC-25-0238` as continued/pending with no final order and next status check `2025-06-17`.
- Uses `TBD from case file` for Helena Cross's missing DOB and recommends `verify_before_entry`.
- Classifies Rafael King's `APD` label as `appointed_private`, using the hearing/memo clarification rather than treating it as public defender counsel.
- Posts court cost `150.00` on each disposed case.
- Posts the `75.00` crime laboratory fee only to `UC-25-0224`, because it is the only final controlled-substance conviction in this task.
- Posts Rafael King's `500.00` fine and no fine on the other cases.
- Computes totals: disposed case count `4`, excluded pending count `1`, court cost total `600.00`, lab fee total `75.00`, fine total `500.00`, and batch total due `1175.00`.

The evaluator has eight whole-point checks with raw weights:

- `SP001` weight 2: correct disposed and pending case sets.
- `SP002` weight 2: correct audit resolutions for DOB, counsel, amendment, lab-fee omission, and pending-status conflicts.
- `SP003` weight 3: correct disposition outcomes, pleas, dates, count treatment, and departure statuses.
- `SP004` weight 3: correct court-cost and crime-lab postings per case.
- `SP005` weight 2: correct fine and total-due amounts per case.
- `SP006` weight 2: correct docket/register action and docket code for each case.
- `SP007` weight 2: correct aggregate register totals.
- `SP008` weight 1: correct detailed exclusion record for `UC-25-0238`.

These points cover at least five distinct outcomes: target status/exclusion, audit/conflict resolution, disposition classification, financial posting, docket/register entry, and aggregate totals. Each scoring point is all-or-nothing with no fractional subcredit inside a point.

Likely model pitfalls include copying the worksheet's `POSS-CS guilty` row for `UC-25-0221`, missing the lab fee for `UC-25-0224`, using a fabricated DOB for `UC-25-0230`, treating `APD` as public defender on `UC-24-0775`, and entering `UC-25-0238` as disposed despite the continuance.

### Transfer Design

As a train task, this is not a simplified worked example. It is intended to let fewshot skill generation infer recurring criminal closeout habits: hearing notes control courtroom disposition outcomes; CMS/environment records corroborate identity and status; fee schedules are applied by jurisdiction and current effective date; missing identifiers use controlled placeholders and verify recommendations; counsel abbreviations can require clarification; and continued/pending matters must be excluded from disposed registers and financial postings.

This anchors later Arkansas criminal test tasks that use similar but not identical conflicts around counsel labels, fee schedules, amended or dismissed charges, missing identity details, docket actions, and aggregate register totals.

### Construction Record

Author: Codex task-builder subagent for `train_004`.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: created the `train_tasks/004/` task folder, local payloads, answer template, standard answer, evaluator, and bilingual notes.

## 中文审阅说明

### 数据和来源

本任务属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，参考示例为 `E001`、`E002` 和 `E003`。它是第二个阿肯色刑事结案登记训练任务，用新的 Union County 事实强化 `train_001` 的刑事处分、费用和登记习惯。

共享环境是只读的 Court Operations Portal，主要使用 `GET /api/cases`、`GET /api/charges`、`GET /api/docket-entries`、`GET /api/fee-schedules` 和 `GET /api/search`。本任务本地可见材料包括庭审记录、带冲突的财务工作表，以及答案模板。目标案号是 `UC-25-0221`、`UC-25-0224`、`UC-25-0230`、`UC-24-0775` 和 `UC-25-0238`。

### 任务定义和场景契合

求解者扮演刑事书记员，需要在录入处分登记前核对庭审记录、工作表和系统记录，输出身份与律师类型审计、处分状态、费用录入、登记动作、汇总金额以及不得结案录入的事项。

该任务符合原始法院书记员场景，因为它要求在庭审结果、CMS 身份和状态、费用表、工作表冲突、财务录入和案件登记之间做长期、多源核对。

### 材料用途

庭审记录是处分结果的主要依据：`UC-25-0221` 是修改后的非毒品定罪，`UC-25-0224` 是受控物质定罪并需要实验室费用，`UC-25-0230` 有缺失 DOB 且需用占位并核验，`UC-24-0775` 的 `APD` 实际是 appointed private defense counsel，`UC-25-0238` 只是继续审理且没有最终命令。

工作表提供真实的噪声和冲突：它错误地给 `UC-25-0221` 加实验室费用，漏掉 `UC-25-0224` 的实验室费用，保留 `UC-25-0230` 的空 DOB，把 `UC-24-0775` 的 `APD` 写成容易误解的标签，并暗示 `UC-25-0238` 可以草稿结案。

环境中的 Union County 费用表给出每个已处分刑事案件的法院成本 `150.00`，以及受控物质定罪的犯罪实验室费用 `75.00`。继续审理的事项不得录入处分或费用。

### 标准答案和评分依据

标准答案将四个案件录入已处分登记，排除 `UC-25-0238`；对 Helena Cross 使用 `TBD from case file` 并建议核验；将 Rafael King 的律师分类为 `appointed_private`；只给 `UC-25-0224` 加 `75.00` 实验室费用；给四个已处分案件各加 `150.00` 法院成本；给 `UC-24-0775` 加 `500.00` 罚金。汇总为已处分 `4` 件、排除 `1` 件、法院成本 `600.00`、实验室费用 `75.00`、罚金 `500.00`、总计 `1175.00`。

评估器包含 8 个整点评分项，权重分别为 2、2、3、3、2、2、2、1。评分覆盖目标案件状态、审计冲突、处分分类、费用录入、登记动作、汇总金额和排除事项，均为确定性的通过或不通过，不在单个评分点内给部分分。

常见错误包括照抄工作表给 `UC-25-0221` 加实验室费用、漏掉 `UC-25-0224` 的实验室费用、为 `UC-25-0230` 编造 DOB、把 `UC-24-0775` 的 `APD` 当成公设辩护人，以及把 `UC-25-0238` 当成已处分案件录入。

### 迁移设计

这是正式训练任务，不是教程。通过求解并对照答案，少样本技能生成应能归纳出若干可迁移习惯：庭审记录优先决定处分结果；环境记录用于核对身份和状态；按辖区和生效日期应用费用表；缺失身份字段使用受控占位并建议核验；律师缩写需要结合备忘录澄清；继续或待定事项不能进入已处分登记或财务录入。

这些经验会支持后续阿肯色刑事测试任务中关于律师标签、费用表、修改或撤销的罪名、缺失身份信息、登记动作和汇总金额的判断。

### 构建记录

作者：`train_004` 的 Codex task-builder subagent。

创建日期：2026-07-18。

更新日期：2026-07-18。

主要变更：创建 `train_tasks/004/` 文件夹、本地材料、答案模板、标准答案、评估器和双语说明。
