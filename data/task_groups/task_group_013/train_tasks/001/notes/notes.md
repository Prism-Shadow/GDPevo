# train_001 Notes - New Patient Access Verification: June Primary Care Intake

## English

Data/source lineage: This task belongs to `SCN_013_healthcare_patient_intake_transfer` and uses the patient access validation family derived mainly from source example `E002`, with chart-readiness and structured intake conventions also aligned with `E003` and `E004`. The shared generated environment is `task_group/task_group_013/env/`, backed by `env/data/clinic.db`. The task-local payloads are `input/payloads/target_roster.json` and `input/payloads/answer_template.json`.

Task definition: The solver receives roster `NPI-JUN-01` and patient IDs `P001` through `P006`. The requested service date, `2026-06-18`, and service line, `primary_care`, come from the `intake_rosters` table. The expected answer is a JSON access-verification result with insurance status, prescription benefit status, preferred-pharmacy network status, lifestyle risk, overall risk, registration status, blocked reason codes, and cohort summary counts.

Material map: `intake_rosters` identifies the target cohort and date. `patients` supplies demographics and contact completeness. `coverage` supplies primary payer, policy, effective dates, status, network, and service-line coverage. `pbm` supplies prescription benefit state and policy matching. `patient_pharmacy` and `pharmacies` determine the rank-1 preferred pharmacy network result. `lifestyle` supplies smoking, alcohol, and exercise values. `clinical_history` supplies chronic-condition burden, medication/allergy complexity, hospitalizations, and risk flags. `chart_artifacts` is available through the portal but only `P005` has a current vitals artifact in this cohort, so it does not remove any access blocker.

Solution basis: Coverage is valid only when active, date-valid, in network, and covering `primary_care`. PBM is valid only when active, approved, and matching the coverage payer-policy pair. Pharmacy status uses the patient's rank-1 preferred pharmacy. Lifestyle scoring uses smoking Never/Former/Current = 0/1/2, alcohol None/Occasional/Moderate/Heavy = 0/1/2/3, and exercise 5+ = -1, 3-4 = 0, 1-2 = 1, None or missing = 2; scores <= 1 are low, 2-3 medium, and >= 4 high. Overall risk is high for high lifestyle risk or high clinical complexity, including complex medication reconciliation. Rejection takes precedence for no usable primary-care coverage or excluded service line; otherwise severe risk yields `clinical_review`; administrative-only blockers yield `hold`; all gates clear yields `approved`.

Key answer evidence: `P001` has valid coverage/PBM but an out-of-network preferred pharmacy and high overall risk. `P002` has valid coverage, rejected inactive PBM, missing preferred email contact, and high overall risk. `P003` has expired coverage that also lacks `primary_care`, an out-of-network preferred pharmacy, and high risk. `P004` has active coverage but no `primary_care` service line, pending PBM, no usable SMS/phone contact, and high risk. `P005` has pending coverage, missing address, and high risk despite valid PBM and in-network pharmacy. `P006` lacks `primary_care` coverage, has a PBM policy mismatch, uses an out-of-network preferred pharmacy, lacks an emergency contact, and is high overall risk because of medication complexity.

Evaluation basis: The evaluator has eight whole scoring points: SP001 insurance statuses, weight 2; SP002 prescription statuses, weight 2; SP003 pharmacy statuses, weight 2; SP004 lifestyle risks, weight 2; SP005 overall risks, weight 2; SP006 registration statuses, weight 3; SP007 blocked reason-code sets, weight 3; SP008 cohort summary counts by registration status and risk, weight 1. Lists are normalized by patient ID, and blocked reason codes are compared as sets. Each point earns all of its assigned weight-normalized score or zero.

Transfer design: As a real train task, this exposes the recurring patient-access conventions without making the prompt a procedural lesson. Comparing a solver attempt with the answer can teach the separation between primary coverage, PBM, preferred pharmacy, lifestyle risk, overall clinical risk, demographic blockers, final status precedence, and cohort rollups. That experience is intended to transfer to `test_001` and to chart/program tasks that reuse contact, clinical-risk, and artifact-readiness distinctions.

Likely model pitfalls: Common errors include treating any active coverage as valid even when `primary_care` is excluded, accepting an approved PBM record with a mismatched policy, checking any pharmacy instead of the rank-1 preferred pharmacy, forgetting that missing exercise increases lifestyle risk, making all administrative blockers `hold` even when high risk requires clinical review, and omitting demographic/contact blockers from reason-code sets.

Construction record: Authored by Codex task-builder for `task_group_013/train_001` on 2026-07-17. Created files under `task_group/task_group_013/train_tasks/001/` only. The standard answer was derived from the generated SQLite environment and the common task-builder business rules.

## 中文

数据来源：本任务属于 `SCN_013_healthcare_patient_intake_transfer`，采用患者准入核验流程，主要对应源示例 `E002`，并与 `E003`、`E004` 中的建档和结构化入组习惯保持一致。共享环境位于 `task_group/task_group_013/env/`，数据来自 `env/data/clinic.db`。本任务本地可见材料为 `input/payloads/target_roster.json` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要处理名单 `NPI-JUN-01` 中的 `P001` 到 `P006`。服务日期 `2026-06-18` 和服务线 `primary_care` 来自 `intake_rosters` 表。输出应为 JSON，包含保险状态、处方权益状态、首选药房网络状态、生活方式风险、总体风险、最终登记状态、阻断原因代码和队列汇总。

材料说明：`intake_rosters` 确定目标患者和日期；`patients` 提供人口学和联系方式完整性；`coverage` 提供主保险、保单、日期、状态、网络和服务线；`pbm` 提供处方权益和保单匹配；`patient_pharmacy` 与 `pharmacies` 用于判断第一优先级药房是否在网；`lifestyle` 提供吸烟、饮酒和运动；`clinical_history` 提供慢病负担、药物和过敏复杂度、近期住院及风险标志；`chart_artifacts` 可通过门户查看，但本队列只有 `P005` 有当前生命体征记录，不能消除准入阻断。

解题依据：保险必须为 active、服务日期有效、院内网络且覆盖 `primary_care`。PBM 必须 active、approved，并且付款方和保单号与保险一致。药房只看患者第一优先级药房。生活方式评分为吸烟 Never/Former/Current = 0/1/2，饮酒 None/Occasional/Moderate/Heavy = 0/1/2/3，运动 5+ = -1、3-4 = 0、1-2 = 1、None 或缺失 = 2；小于等于 1 为 low，2-3 为 medium，大于等于 4 为 high。总体风险在生活方式高风险或临床复杂度高时为 high。没有可用的 primary-care 保险或服务线排除时优先判为 `rejected`；否则严重风险为 `clinical_review`；仅行政阻断为 `hold`；全部通过为 `approved`。

关键证据：`P001` 保险和 PBM 有效，但首选药房不在网且总体高风险。`P002` 保险有效，但 PBM 被拒且未激活，首选 email 联系方式缺失，并且总体高风险。`P003` 保险已过期且不含 `primary_care`，首选药房不在网，总体高风险。`P004` 保险 active 但不含 `primary_care`，PBM pending，短信/电话联系方式不可用，总体高风险。`P005` 保险 pending、地址缺失、总体高风险，即使 PBM 和药房通过也不能批准。`P006` 缺少 `primary_care` 保险，PBM 保单不匹配，首选药房不在网，缺少紧急联系人，并因复杂用药核对而总体高风险。

评估依据：评估器包含八个整点评分项：SP001 保险状态，权重 2；SP002 处方权益状态，权重 2；SP003 药房状态，权重 2；SP004 生活方式风险，权重 2；SP005 总体风险，权重 2；SP006 登记状态，权重 3；SP007 阻断原因代码集合，权重 3；SP008 按登记状态和风险分类的汇总计数，权重 1。患者列表按 ID 归一化，阻断原因按集合比较。每个评分项只能得满分或零分。

迁移设计：这是一个正式训练任务，而不是教程。求解者把自己的结果与标准答案比较后，可以归纳出主保险、PBM、首选药房、生活方式风险、总体临床风险、人口学阻断、最终状态优先级和汇总口径之间的区别。这些经验会迁移到 `test_001`，也会帮助处理复用联系方式、临床风险和建档完整性判断的图表或项目入组任务。

常见错误：容易把任何 active 保险都当成有效而忽略 `primary_care` 服务线；接受保单号不匹配但 approved 的 PBM；查看任意药房而不是第一优先级药房；忘记运动缺失会提高生活方式风险；把所有行政问题都判为 `hold` 而忽略高风险需要临床复核；或者在阻断原因集合中漏掉人口学和联系方式问题。

构建记录：由 Codex task-builder 于 2026-07-17 为 `task_group_013/train_001` 编写。仅在 `task_group/task_group_013/train_tasks/001/` 下创建文件。标准答案来自生成的 SQLite 环境和通用任务构建业务规则。
