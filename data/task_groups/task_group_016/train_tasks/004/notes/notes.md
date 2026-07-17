# train_004 Notes - Complex ESRD/Diabetes Care-Management Routing

## English

### Lineage and task definition

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, using source examples `E001` through `E005`. The direct design brief is the train task `train_004`: for `CASE-CM-411`, the solver reviews a high-risk registry case and produces structured care-management routing, priority problems, referrals, outreach posture, care-plan minimum requirements, escalation conditions, and source-provenance grouping.

The solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt names the target case id and the runtime base URL placeholder `<TASK_ENV_BASE_URL>`, but it intentionally does not expose source-precedence steps, scoring logic, or the standard answer. The expected answer is a single JSON object matching the template.

### Scenario fit and material map

The task represents the chronic high-risk care-management operation family in the group. It is aligned with the source ESRD/diabetes care-management example because the work requires longitudinal registry interpretation, chronic disease threshold review, medication-burden review, SDoH barrier routing, refusal-sensitive outreach, and a bounded downstream plan.

The shared synthetic clinic environment is the source of truth. Relevant public runtime surfaces are expected to include case, patient, problem, medication, care-registry, SDoH, observation, protocol, and read-only query endpoints as staged in `environment_access.md`. The hidden environment blueprint defines Harborview Synthetic Clinic, `CASE-CM-411`, and `PAT-4411` with risk score `0.84`, dialysis context, HbA1c `9.4%`, phosphorus `7.1 mg/dL`, blood pressure `152/88`, 21 active medications, recent volume-overload admission context, transportation barrier, financial medication barrier, and dialysis fatigue. The `CM-HIGH-RISK-2026` protocol supports high-risk complex-care routing, pharmacist referral for polypharmacy/insulin-safety burden, social-work routing for SDoH barriers, and permission-based plain-language outreach.

### Solution and evaluation basis

The standard answer classifies the case as `risk_tier: high` and `program: complex_care_management` for patient `PAT-4411`. The priority problem set is `uncontrolled_diabetes`, `esrd_on_hemodialysis`, `hfpEF_post_volume_overload`, `hyperphosphatemia`, `hypertension`, and `polypharmacy`. Numeric anchors are risk score `0.84`, HbA1c `9.4`, phosphorus `7.1`, blood pressure `152/88`, and active medication count `21`.

Referrals are `dialysis_care_coordination`, `pharmacist`, `social_worker`, and `transportation_benefits`. The outreach stance is `permission_based_plain_language`. The minimum care-plan structure requires at least 3 problems, weekly follow-up, a member-stated priority, and at least 2 disciplines. Escalation conditions are `missed_dialysis_or_volume_overload` and `phq9_increase_or_item9_positive`. Chart-fact provenance covers `risk_score`, `hba1c_percent`, `phosphorus_mg_dl`, and `active_medication_count`; member-disclosure-needed provenance covers `transportation_barrier`, `financial_medication_barrier`, and `dialysis_fatigue`.

The evaluator has eight whole-point scoring goals with raw weights `[3, 3, 2, 2, 2, 2, 2, 1]`, total raw weight `17`:

1. SP001, weight 3: correct high-risk and complex-care classification.
2. SP002, weight 3: correct priority problem set and numeric anchors.
3. SP003, weight 2: correct pharmacist referral.
4. SP004, weight 2: correct social-work and transportation-benefits routing.
5. SP005, weight 2: correct permission-based plain-language outreach stance.
6. SP006, weight 2: correct care-plan minimum structure and weekly cadence.
7. SP007, weight 2: correct clinical and behavioral-health escalation condition set.
8. SP008, weight 1: correct source provenance for chart facts versus member disclosures.

Each point is pass/fail only; there is no partial credit inside a point. Lists are normalized as sets. Numeric anchors are compared at the precision declared in the answer template. Likely model pitfalls include treating all barriers as chart facts, missing dialysis-specific coordination, omitting the pharmacist because no medication list is printed in the prompt, using coercive outreach language, confusing HFpEF volume-overload history with generic heart failure admission, or routing to routine case management despite the high-risk registry result.

### Transfer design

As a train task, this example teaches by comparison rather than by visible instruction. A future skill can infer that the environment record is authoritative, controlled enum values are expected, care-management routing is protocol-bound, SDoH barriers drive social-work and benefits referrals, polypharmacy drives pharmacist review, and initially reluctant or burdened members should receive permission-based plain-language outreach. It also anchors the group convention that `source_provenance` separates chart-extracted values from facts that require member confirmation or disclosure.

### Construction record

Author: Codex task-builder worker. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created formal `train_004` prompt, answer template, standard answer, bilingual notes, and deterministic evaluator from `scratch/task_group_design.md` and `scratch/target_truth_spec.md`.

## 中文

### 来源与任务定义

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，来源示例为 `E001` 到 `E005`。直接设计简述是训练任务 `train_004`：针对 `CASE-CM-411`，解题者需要审查一个高风险登记病例，并输出结构化的照护管理分流、优先问题、转介、外联姿态、照护计划最低要求、升级条件以及来源归属分组。

解题者可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示中只给出目标病例编号和运行环境基础地址占位符 `<TASK_ENV_BASE_URL>`，不会暴露来源优先级步骤、评分逻辑或标准答案。预期答案是一个符合模板的 JSON 对象。

### 场景匹配与材料地图

本任务代表任务组中的慢病高风险照护管理操作族。它与源 ESRD/糖尿病照护管理示例一致，因为任务需要解读纵向风险登记、慢病阈值、用药负担、社会风险分流、拒绝敏感的外联方式以及有边界的后续照护计划。

共享合成诊所环境是事实来源。相关运行时入口预计包括病例、患者、问题清单、用药、照护登记、SDoH、观察值、协议和只读查询端点，具体以 `environment_access.md` 中列出的访问权限为准。隐藏环境蓝图定义了 Harborview Synthetic Clinic、`CASE-CM-411` 和 `PAT-4411`，包含风险分数 `0.84`、透析背景、HbA1c `9.4%`、磷 `7.1 mg/dL`、血压 `152/88`、21 个当前用药、近期容量负荷入院背景、交通障碍、用药费用障碍和透析疲劳。`CM-HIGH-RISK-2026` 协议支持高风险复杂照护分流、多药或胰岛素安全负担触发药师转介、SDoH 障碍触发社工分流，以及基于许可的通俗语言外联。

### 解法与评估依据

标准答案将病例分类为 `risk_tier: high` 和 `program: complex_care_management`，患者为 `PAT-4411`。优先问题集合为 `uncontrolled_diabetes`、`esrd_on_hemodialysis`、`hfpEF_post_volume_overload`、`hyperphosphatemia`、`hypertension` 和 `polypharmacy`。数值锚点为风险分数 `0.84`、HbA1c `9.4`、磷 `7.1`、血压 `152/88`、当前用药数 `21`。

转介为 `dialysis_care_coordination`、`pharmacist`、`social_worker` 和 `transportation_benefits`。外联姿态为 `permission_based_plain_language`。照护计划最低结构要求至少 3 个问题、每周随访、需要成员本人陈述优先事项，并至少涉及 2 个学科。升级条件为 `missed_dialysis_or_volume_overload` 和 `phq9_increase_or_item9_positive`。病历事实来源包括 `risk_score`、`hba1c_percent`、`phosphorus_mg_dl` 和 `active_medication_count`；需要成员披露或确认的来源包括 `transportation_barrier`、`financial_medication_barrier` 和 `dialysis_fatigue`。

评估器包含 8 个整点评分目标，原始权重为 `[3, 3, 2, 2, 2, 2, 2, 1]`，总权重为 `17`：

1. SP001，权重 3：高风险和复杂照护分类正确。
2. SP002，权重 3：优先问题集合和数值锚点正确。
3. SP003，权重 2：药师转介正确。
4. SP004，权重 2：社工和交通福利分流正确。
5. SP005，权重 2：基于许可的通俗语言外联姿态正确。
6. SP006，权重 2：照护计划最低结构和每周节奏正确。
7. SP007，权重 2：临床和行为健康升级条件集合正确。
8. SP008，权重 1：病历事实与成员披露事实的来源归属正确。

每个评分点只有通过或不通过，不在单点内给部分分。列表按集合归一化。数值锚点按答案模板声明的精度比较。常见模型错误包括把所有障碍都当成病历事实、漏掉透析相关协调、因为提示中没有直接打印用药清单而漏掉药师、使用带压迫感的外联措辞、把 HFpEF 容量负荷史误读成普通心衰入院，或在高风险登记结果下仍分到常规个案管理。

### 迁移设计

作为训练任务，本例通过标准答案对比来传递经验，而不是在可见提示中教学。未来技能可以从中推断：运行环境记录更权威，输出应使用受控枚举，照护管理分流受协议约束，SDoH 障碍会驱动社工和福利转介，多药会驱动药师审查，起初犹豫或负担较重的成员应采用基于许可的通俗语言外联。本任务还锚定了任务组约定：`source_provenance` 要区分从病历抽取的值和需要成员确认或披露的事实。

### 构建记录

作者：Codex task-builder worker。创建日期：2026-07-17。更新日期：2026-07-17。主要变更：根据 `scratch/task_group_design.md` 和 `scratch/target_truth_spec.md` 创建正式的 `train_004` 提示、答案模板、标准答案、双语说明和确定性评估器。
