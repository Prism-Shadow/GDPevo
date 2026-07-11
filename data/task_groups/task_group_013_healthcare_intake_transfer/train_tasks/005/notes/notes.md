# Hidden Notes / 隐藏说明

These notes are for task builders/evaluators only. Do not expose them in solver-visible input.

## English

Review date: 2026-07-07.

Chronic-care readiness rules used:

- Diagnosis support, recent pathway data, signed consent, and complete program form are enrollment gates.
- Diabetes/hypertension programs require recent HbA1c or BP support.
- `hold_missing_consent` takes precedence when consent is not signed.
- `hold_missing_form` applies only when consent is signed and no clinical review blocker outranks the form issue.
- `clinical_review` applies when diagnosis or supporting lab/vital evidence is missing, or renal risk needs review while gates are incomplete.
- `enroll_with_nurse_escalation` applies when all gates pass and renal flag is present.
- Cadence is weekly for renal flag or poor adherence, biweekly for variable adherence or systolic BP over 150, and monthly otherwise.

Patient derivation:

- CCP-4107: Cardiometabolic Combo is supported by Type 2 diabetes + hypertension with HbA1c/BP data, but consent is not obtained and form is not started. Decision `hold_missing_consent`; missing `consent_signed`, `program_form_complete`; BP 166/93 and variable adherence give `biweekly_checkin`.
- CCP-4116: Cardiometabolic Combo is supported and form is complete, but consent is declined. Renal flag/poor adherence set `weekly_nurse_call`; decision remains `hold_missing_consent`; missing `consent_signed`.
- CCP-4133: Hypertension Pathway is not supported by an active hypertension diagnosis, and form is not started. Renal flag plus incomplete/unsupported gates requires `clinical_review`; missing `diagnosis_support`, `program_form_complete`; cadence `weekly_nurse_call`.
- CCP-4144: Renal Risk Monitoring has complete consent/form and renal flag; diabetes/hypertension data are present. Decision `enroll_with_nurse_escalation`; no missing items; cadence `weekly_nurse_call`.

Coordinator queue includes all four records because each needs coordinator follow-through: three held/review records and one nurse-escalation enrollment.

## 中文

审核日期：2026-07-07。

本任务来自医疗患者接收与转诊场景，训练样本锚定慢病项目准入工作流。求解者只能看到登录式 Northstar Care Intake Portal、任务提示和答案模板；本文件、标准答案和评测脚本均为隐藏材料。

慢病项目就绪规则：

- 诊断支持、近期项目数据、已签署同意书、完整项目表单是入组门槛。
- 糖尿病/高血压路径需要近期 HbA1c 或血压证据。
- 当同意书未签署时，`hold_missing_consent` 优先。
- `hold_missing_form` 只在同意书已签署且没有更高优先级临床阻塞时适用。
- 当缺少诊断支持、实验室/生命体征证据，或肾脏风险伴随未完成门槛时，使用 `clinical_review`。
- 所有门槛通过且存在肾脏风险标记时，使用 `enroll_with_nurse_escalation`。
- 随访频率：肾脏风险或低依从性为每周；依从性波动或收缩压超过 150 为每两周；其余为每月。

逐患者推导：

- CCP-4107：Cardiometabolic Combo 有 2 型糖尿病和高血压及 HbA1c/血压数据支持，但未取得同意且表单未开始。决策为 `hold_missing_consent`；缺失 `consent_signed`、`program_form_complete`；166/93 血压和可变依从性给出 `biweekly_checkin`。
- CCP-4116：Cardiometabolic Combo 有支持且表单完整，但同意书被拒绝。肾脏风险/低依从性给出 `weekly_nurse_call`；决策仍为 `hold_missing_consent`；缺失 `consent_signed`。
- CCP-4133：Hypertension Pathway 没有活动性高血压诊断支持，且表单未开始。肾脏风险叠加未完成/不支持门槛，需要 `clinical_review`；缺失 `diagnosis_support`、`program_form_complete`；频率为 `weekly_nurse_call`。
- CCP-4144：Renal Risk Monitoring 的同意书和表单完整，且有肾脏风险标记；糖尿病/高血压数据存在。决策为 `enroll_with_nurse_escalation`；无缺失项；频率为 `weekly_nurse_call`。

协调员队列包含四条记录，因为三条需要暂缓或临床复核，一条入组后需要护士升级跟进。评测采用 7 个精确匹配评分点，覆盖入组决策、项目选择、缺失项集合、随访频率、协调员队列、升级数量和同意书状态。

构建记录：作者为 train_005 task-builder，主代理于 2026-07-07 将第二语言说明修正为中文。主要变更为补足中文解释，不改变标准答案或评测逻辑。
