# Chronic Care Enrollment Panel: Diabetes And Hypertension

## English Notes

This is `train_004` for `task_group_013`, derived from scenario `SCN_013_healthcare_patient_intake_transfer` and anchored mainly in source example `E004`, with chart-readiness conventions also aligned to `E003`. The solver-visible task asks for a chronic-care enrollment panel for program `DMHTN-2026A` using the shared Cedar Ridge Intake Coordination Portal. The visible files are `input/prompt.txt` and `input/payloads/answer_template.json`; the business data comes from the read-only environment tables behind `/programs/DMHTN-2026A/candidates`, `/patients/{patient_id}`, `/chart/{patient_id}`, and `/query`.

The target program has ten current candidates in the generated environment: seed patients `P026` through `P032` plus ordinary same-program candidates `P058`, `P059`, and `P076`. The standard answer treats a patient as program-eligible when the program target is diabetes plus hypertension and the clinical history contains both active conditions. Consent and chart readiness then determine whether the eligible patient can enroll, must be held, or is rejected. Declined consent is a rejection. Missing consent with remediable chart gaps is a hold. Wrong target condition or missing active diabetes-hypertension diagnosis is a rejection. Existing patient demographic/contact rows can satisfy basic demographics; the chart-artifact checks here focus on current active problems, vitals, labs, medications, and program consent, plus whether an active chart exists.

The final answer enrolls `P026`, `P027`, `P029`, `P030`, and `P032`; holds `P058`; and rejects `P028`, `P031`, `P059`, and `P076`. `P028` and `P031` meet clinical eligibility but declined consent and lack an active chart. `P058` meets the diagnosis target but has missing consent, no active chart, stale active problems, and missing current vitals, labs, and medication list. `P059` and `P076` are not valid diabetes-hypertension candidates.

Follow-up cadence is based on enrollment risk. Weekly cadence is used for acute utilization or low adherence: `P026` has recent hospitalization, `P027` has low adherence, and `P030` has a recent ED risk flag. `P029` is biweekly because CKD and medication complexity call for closer monitoring than standard monthly outreach. `P032` is monthly. Held patients are `deferred`; rejected patients are `none`. Outreach uses the program preferred channel when it is reachable and falls back to a reachable patient preference when needed, producing phone for `P027`, `P028`, and `P029`; portal for `P026` and `P032`; email for `P030`, `P031`, `P058`, and `P059`; and SMS for `P076`.

The initial monitoring package is normalized rather than free text. High-touch packages go to `P026`, `P027`, and `P030` with BP cuff, glucometer, A1c/CMP/lipid lab order, medication reconciliation, care-plan setup, and a seven-day first check-in. Standard packages go to `P029` and `P032`; `P029` also receives medication reconciliation and a 14-day first check-in, while `P032` receives the basic standard package and a 30-day first check-in. `P058` receives a deferred consent-and-chart update package. Rejected patients receive `not_applicable`.

The evaluator has seven whole scoring points with raw weights `[3, 3, 2, 2, 1, 2, 1]`: eligible/ineligible candidate sets; status and reason-code sets; cadence; missing chart artifacts; outreach channel; monitoring package; and cohort summary counts. Each point is all-or-nothing and compares normalized sets or enums rather than prose. The provided `output/answer.json` self-scores to `1.0`.

Transfer value: as a train task, this example lets a fewshot skill infer that chronic-care enrollment is not just a candidate-list lookup. It requires reconciling candidate target, active diagnoses, consent, current chart artifacts, reachable outreach, and risk cadence. Those habits transfer directly to the renal-diabetes chronic-care test task while leaving patient identities, program-specific flags, and final values different.

Construction record: created by Codex task-builder for `train_004` on 2026-07-17. The task files are confined to `task_group/task_group_013/train_tasks/004/`.

## 中文说明

这是 `task_group_013` 的 `train_004`，来源于 `SCN_013_healthcare_patient_intake_transfer`，主要参考 `E004` 的慢病项目纳入工作流，并结合 `E003` 中的病历就绪习惯。求解者可见的材料只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`；业务证据来自共享只读环境中的项目候选人、患者详情、病历和查询接口。

目标项目 `DMHTN-2026A` 在环境中有十名当前候选人：种子患者 `P026` 到 `P032`，以及同一项目下的普通候选人 `P058`、`P059`、`P076`。标准答案把“糖尿病加高血压”目标和临床史中同时存在糖尿病、高血压作为项目资格判断基础；随后用同意状态和病历就绪状态决定 `enroll`、`hold` 或 `reject`。拒绝同意是拒绝；缺少同意且病历缺口可补是暂缓；目标病种不符或没有活动性糖尿病高血压诊断是拒绝。

标准答案纳入 `P026`、`P027`、`P029`、`P030`、`P032`；暂缓 `P058`；拒绝 `P028`、`P031`、`P059`、`P076`。`P028` 和 `P031` 临床上符合资格，但拒绝同意且没有活动病历。`P058` 符合诊断目标，但缺少同意、没有活动病历、活动问题过期，并且缺少近期生命体征、化验和用药清单。`P059` 和 `P076` 不是有效的糖尿病高血压候选人。

随访频率按风险和依从性确定。`P026` 有近期住院、`P027` 依从性低、`P030` 有近期急诊风险，因此为 weekly。`P029` 因 CKD 和用药复杂度为 biweekly。`P032` 为 monthly。暂缓患者为 deferred，拒绝患者为 none。外联渠道优先使用项目候选记录中的可达渠道，必要时回退到患者资料中的可达偏好。

初始监测包用结构化枚举表达。高接触包分配给 `P026`、`P027`、`P030`，包含血压计、血糖仪、A1c/CMP/血脂化验单、用药核对、护理计划建立和 7 天首次检查。标准包分配给 `P029` 和 `P032`；`P058` 是暂缓包，需要同意书和病历更新；拒绝患者不适用监测包。

评估器包含七个整点评分项，原始权重为 `[3, 3, 2, 2, 1, 2, 1]`，分别检查资格集合、状态和原因码、随访频率、缺失病历材料、外联渠道、监测包和汇总计数。每项只给满分或零分，不做项内部分分。随附的 `output/answer.json` 自评分为 `1.0`。

迁移价值在于：这个训练任务让 fewshot 技能学习到慢病项目纳入不是简单读取候选人列表，而是需要综合项目目标、活动诊断、同意状态、病历材料、可达外联和风险随访频率。这些经验会迁移到后续肾病糖尿病慢病项目测试任务，但患者、项目特异信号和最终答案不同。
