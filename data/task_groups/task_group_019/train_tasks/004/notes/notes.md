# train_004 Notes

## English

### Data/source lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003` as the broader licensing-review distribution. The direct family anchor is the contractor eligibility workflow from `E001`: a reviewer reconciles applications, bulletins, bonds, insurance, adverse history, correspondence, complaints, field notes, and violations.

The shared environment is the Cascadia Licensing Review Portal (CLRP) under `task_group/task_group_019/env/`. The target public batch is `HS-2026-Q1B`, whose 11 applications are exposed through `/api/contractors/applications?batch_id=HS-2026-Q1B` and `/exports/contractor_batch_HS-2026-Q1B.csv`. The task-local solver-visible payload is only `input/payloads/answer_template.json`; it defines the output structure and controlled enums without giving the decisions.

### Task definition and material map

The solver-visible prompt asks for a final eligibility screen for batch `HS-2026-Q1B` using `http://localhost:<PORT>`. The expected output is one JSON object with `application_decisions` for all 11 applications, `manual_followup` for cases that require staff action, and `rule_change_summary`.

Important CLRP materials:

- `contractor_applications`: target application IDs, trades, filing dates, exam scores, experience years, financial-statement status, background flags, declared bond and insurance.
- `contractor_bulletins`: 2026 effective trade rules, especially Roofing, Plumbing, Solar, and Fire Protection bond or insurance thresholds.
- `contractor_bonds`: active, short, and cancelled bond records.
- `contractor_insurance`: active, pending, expired, stale, and verified insurance records.
- `contractor_violations` and `contractor_complaints`: adverse prior history and unresolved penalties.
- `contractor_field_notes`: open inspector holds.
- `contractor_correspondence`: material notices and nonblocking mailroom/public-inquiry distractors.

### Solution basis

The standard answer treats `HOLD` as the correct outcome when the file has a remediable eligibility block or manual review item. No Q1B application is a direct `DENY`; the batch has no disqualifying-conduct case. The answer approves only the two files that are clean after material evidence is considered.

Key decisions:

- `CA-2026-0013`: `HOLD`; adverse prior registration review plus unresolved penalties for Northstar Summit Contracting Inc.
- `CA-2026-0014`: `HOLD`; Orchard Summit Construction Group has a cancelled bond.
- `CA-2026-0015`: `APPROVE`; Pioneer Summit Restoration LLC has no material deficiency.
- `CA-2026-0016`: `HOLD`; Quarry Summit Works Co has pending carrier verification.
- `CA-2026-0017`: `HOLD`; Rainier Summit Services LLC has an open field-note hold.
- `CA-2026-0018`: `HOLD`; Soundview Summit Builders LLC has a Fire Protection bond shortfall after the March 20, 2026 Fire Protection bond bulletin.
- `CA-2026-0019`: `HOLD`; Timberline Summit Contracting Inc has an expired/stale insurance row and an unresolved penalty.
- `CA-2026-0020`: `HOLD`; Union Summit Construction Group has unresolved penalty history.
- `CA-2026-0021`: `HOLD`; Vashon Summit Restoration LLC needs experience review and has unresolved penalty history.
- `CA-2026-0022`: `HOLD`; Westlake Summit Works Co has a material correspondence item and missing financial statement.
- `CA-2026-0023`: `APPROVE`; Yarrow Summit Services LLC has active bond and verified insurance, and the remaining low-severity or duplicate records do not create a blocking Q1B deficiency.

The rule-change summary counts 11 total applications, 2 approvals, 9 holds, 0 denials, and 9 manual follow-ups. The Q1 2026 bulletin-changed application set is `["CA-2026-0018"]`: the Fire Protection bond was $14,000, which met the prior $14,000 baseline but failed the $17,000 requirement effective March 20, 2026.

### Evaluation basis

The evaluator has 8 exact-match scoring points with raw weights 1, 2, or 3:

- `SP1`, weight 1: target batch and complete decision list in application ID order.
- `SP2`, weight 2: adverse prior registration and unresolved-penalty holds.
- `SP3`, weight 2: cancelled-bond and bond-shortfall holds.
- `SP4`, weight 2: insurance verification and replacement holds.
- `SP5`, weight 2: field-note and correspondence/documentation holds.
- `SP6`, weight 2: clean approval set.
- `SP7`, weight 3: manual follow-up IDs and controlled reason codes.
- `SP8`, weight 2: rule-change summary counts and changed-by-bulletin set.

The evaluator normalizes neither prose nor synonyms. It expects the controlled enums and stable application IDs from the answer template.

### Transfer design

As a train task, this is a real contractor eligibility review rather than an instructional example. It reinforces several transferable habits for later contractor test tasks: apply effective bulletins by trade and date, distinguish bond cancellation from bond shortfall, treat insurance verification as a hold rather than a denial, route adverse prior registration and unresolved penalties to manual review, and avoid overreacting to closed or low-materiality correspondence when the core eligibility file is otherwise clean. It also teaches that generated CLRP batches can include distractor records whose source status, severity, and linkage matter.

### Construction record

Author: task-builder subagent for `train_004`. Created: 2026-07-07. Updated: 2026-07-07. Major changes: initial prompt, answer template, standard answer, bilingual notes, evaluator, and self-check report.

## 中文

### 数据和来源

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，参考来源样例 `E001`、`E002`、`E003` 的行政许可审查分布。直接对应的是 `E001` 的承包商资格审查：审查员需要核对申请、公告规则、保证金、保险、既往不良记录、来往函件、投诉、现场记录和违规记录。

共享环境是 `task_group/task_group_019/env/` 下的 Cascadia Licensing Review Portal（CLRP）。目标批次是 `HS-2026-Q1B`，共有 11 个申请，可通过 `/api/contractors/applications?batch_id=HS-2026-Q1B` 和 `/exports/contractor_batch_HS-2026-Q1B.csv` 获取。任务本地可见负载只有 `input/payloads/answer_template.json`，用于说明输出结构和枚举值，不泄露判定结果。

### 任务定义和材料地图

面向求解器的提示要求使用 `http://localhost:<PORT>` 对 `HS-2026-Q1B` 做最终资格筛查。输出应为一个 JSON 对象，包含全部 11 个申请的 `application_decisions`、需要人工跟进的 `manual_followup`，以及批次层面的 `rule_change_summary`。

关键 CLRP 材料包括：

- `contractor_applications`：目标申请 ID、行业、申请日期、考试分数、经验年限、财务报表状态、背景状态、申报保证金和保险信息。
- `contractor_bulletins`：2026 年生效的行业规则，尤其是屋面、管道、太阳能和消防行业的保证金或保险门槛。
- `contractor_bonds`：有效、金额不足和已取消的保证金记录。
- `contractor_insurance`：有效、待核验、过期、陈旧和已核验的保险记录。
- `contractor_violations` 与 `contractor_complaints`：既往不良记录和未解决罚款。
- `contractor_field_notes`：检查员开放暂停项。
- `contractor_correspondence`：实质性通知以及非阻断性的邮寄室或公众询问干扰项。

### 答案依据

标准答案中，`HOLD` 表示存在可补正的资格阻断项或需要人工复核的事项。Q1B 批次没有直接 `DENY` 的申请，因为没有达到取消资格的行为类型。只有两个文件在考虑实质性证据后可以批准。

主要判定如下：

- `CA-2026-0013`：`HOLD`；Northstar Summit Contracting Inc 有不良既往注册复核需求和未解决罚款。
- `CA-2026-0014`：`HOLD`；Orchard Summit Construction Group 的保证金已取消。
- `CA-2026-0015`：`APPROVE`；Pioneer Summit Restoration LLC 无实质性缺陷。
- `CA-2026-0016`：`HOLD`；Quarry Summit Works Co 的承保机构核验仍待完成。
- `CA-2026-0017`：`HOLD`；Rainier Summit Services LLC 有开放的现场记录暂停项。
- `CA-2026-0018`：`HOLD`；Soundview Summit Builders LLC 在 2026 年 3 月 20 日消防行业保证金公告生效后保证金不足。
- `CA-2026-0019`：`HOLD`；Timberline Summit Contracting Inc 有过期/陈旧保险记录和未解决罚款。
- `CA-2026-0020`：`HOLD`；Union Summit Construction Group 有未解决罚款历史。
- `CA-2026-0021`：`HOLD`；Vashon Summit Restoration LLC 需要经验复核，并有未解决罚款历史。
- `CA-2026-0022`：`HOLD`；Westlake Summit Works Co 有实质性函件事项且财务报表缺失。
- `CA-2026-0023`：`APPROVE`；Yarrow Summit Services LLC 的保证金有效、保险已核验，其余低严重性或重复记录不足以构成 Q1B 阻断缺陷。

规则变化摘要为：总申请数 11，批准 2，暂停 9，拒绝 0，人工跟进 9。受 2026 年第一季度公告改变结果的申请只有 `["CA-2026-0018"]`：消防行业保证金为 14,000 美元，符合旧规则 14,000 美元基线，但低于 2026 年 3 月 20 日生效的新要求 17,000 美元。

### 评估依据

评估器包含 8 个精确匹配评分点，原始权重均为 1、2 或 3：

- `SP1`，权重 1：目标批次和完整申请列表顺序。
- `SP2`，权重 2：不良既往注册和未解决罚款暂停项。
- `SP3`，权重 2：保证金取消和保证金不足暂停项。
- `SP4`，权重 2：保险核验和保险替换暂停项。
- `SP5`，权重 2：现场记录和函件/文件暂停项。
- `SP6`，权重 2：无缺陷批准集合。
- `SP7`，权重 3：人工跟进 ID 和受控原因代码。
- `SP8`，权重 2：规则变化摘要计数和受公告影响的申请集合。

评估器不接受同义改写或自由文本归一化，只按答案模板中的受控枚举和稳定申请 ID 精确匹配。

### 迁移设计

作为训练任务，本任务是正式承包商资格审查，不是教程。它强化后续承包商测试任务可迁移的习惯：按行业和日期应用已生效公告，区分保证金取消与保证金不足，将保险核验作为暂停而不是拒绝，把不良既往注册和未解决罚款转入人工复核，并且在核心资格文件干净时不要因已关闭或低实质性的函件过度阻断。它也让模型学会 CLRP 生成批次中可能存在干扰记录，必须关注记录状态、严重性和关联方式。

### 构造记录

作者：`train_004` 任务构造子代理。创建日期：2026-07-07。更新日期：2026-07-07。主要变更：初始提示、答案模板、标准答案、双语说明、评估器和自检报告。
