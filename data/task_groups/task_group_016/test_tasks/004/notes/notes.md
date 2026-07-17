# test_004 Notes - High-Risk Care-Management Case With Refusal Sensitivity

## English

### Lineage and task definition

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, using source examples `E001` through `E005`. The direct design brief is the test task `test_004`: for `CASE-CM-908`, the solver reviews a post-heart-failure, diabetes, and CKD high-risk registry case and produces structured care-management routing, priority problems, referrals, outreach posture, care-plan minimum requirements, escalation conditions, and source-provenance grouping.

The solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt names the target case id and the runtime base URL placeholder `<TASK_ENV_BASE_URL>`, but it intentionally does not expose source-precedence steps, scoring logic, train anchors, or the standard answer. The expected answer is a single JSON object matching the template.

### Scenario fit and material map

The task represents the chronic high-risk care-management operation family in the group. It is aligned with the source ESRD/diabetes care-management example because the work requires longitudinal registry interpretation, chronic disease threshold review, medication-burden review, SDoH barrier routing, refusal-sensitive outreach, and a bounded downstream plan. It changes the clinical emphasis from dialysis to recent heart-failure admission, diabetes, and stage 4 CKD while preserving the same protocol-bound routing frame.

The shared synthetic clinic environment is the source of truth. Relevant public runtime surfaces are expected to include case, patient, problem, medication, care-registry, SDoH, observation, protocol, and read-only query endpoints as staged in `environment_access.md`. The hidden environment blueprint defines Harborview Synthetic Clinic, `CASE-CM-908`, and `PAT-4908` with risk score `0.79`, HbA1c `9.1%`, eGFR `28`, blood pressure `158/92`, 14 active medications, recent heart-failure admission context, transportation barrier, financial and food barriers, medication access barrier, and initial reluctance. The `CM-HIGH-RISK-2026` protocol supports high-risk complex-care routing, pharmacist referral for polypharmacy or high-risk medications, social-work routing for SDoH barriers, primary-care follow-up, and permission-based plain-language outreach.

### Solution and evaluation basis

The standard answer classifies the case as `risk_tier: high` and `program: complex_care_management` for patient `PAT-4908`. The priority problem set is `uncontrolled_diabetes`, `chronic_kidney_disease_stage_4`, `heart_failure_recent_admission`, `hypertension`, `polypharmacy`, `transportation_barrier`, and `financial_food_barrier`. Numeric anchors are risk score `0.79`, HbA1c `9.1`, eGFR `28`, blood pressure `158/92`, and active medication count `14`.

Referrals are `pharmacist`, `social_worker`, `transportation_benefits`, and `primary_care`. The outreach stance is `permission_based_plain_language`. The minimum care-plan structure requires at least 3 problems, weekly follow-up, a member-stated priority, and at least 2 disciplines. Escalation conditions are `dyspnea_weight_gain_or_ed_return` and `phq9_increase_or_item9_positive`. Chart-fact provenance covers `risk_score`, `hba1c_percent`, `egfr`, and `active_medication_count`; member-disclosure-needed provenance covers `transportation_barrier`, `financial_food_barrier`, and `medication_access_barrier`.

The evaluator has eight whole-point scoring goals with raw weights `[3, 3, 2, 2, 2, 2, 2, 1]`, total raw weight `17`:

1. SP001, weight 3: correct high-risk complex-care classification.
2. SP002, weight 3: correct priority problem set with numeric anchors.
3. SP003, weight 2: correct pharmacist referral from polypharmacy and high-risk medications.
4. SP004, weight 2: correct social-work and transportation-benefits routing for the barrier pattern.
5. SP005, weight 2: correct refusal-sensitive permission-based plain-language outreach stance.
6. SP006, weight 2: correct care-plan minimum structure and weekly follow-up cadence.
7. SP007, weight 2: correct clinical and behavioral-health escalation condition set.
8. SP008, weight 1: correct source provenance for chart facts versus member disclosures.

Each point is pass/fail only; there is no partial credit inside a point. Lists are normalized as sets. Numeric anchors are compared at the precision declared in the answer template. Likely model pitfalls include routing to routine case management despite the high-risk registry result, carrying over dialysis-specific fields from `train_004`, omitting primary care because the train answer used dialysis care coordination instead, missing SDoH-driven social-work routing, using directive language for an initially reluctant member, or treating member-disclosed access barriers as already chart-confirmed facts.

### Transfer design and test anchors

This is a test task. Its main transfer anchor is `train_004`, the complex ESRD/diabetes care-management routing task. The solver should transfer that high-risk registry and chronic-condition burden trigger complex-care enrollment, polypharmacy or high-risk medications trigger pharmacist review, transportation and financial barriers trigger social-work and benefit routing, initially reluctant members require permission-based plain-language outreach, care plans need a minimum problem count, weekly cadence, member-stated priority, and multiple disciplines, and `source_provenance` separates chart-extracted values from member-confirmed or member-disclosed barriers.

Transfer-dependent scoring goals are SP001 and SP003 through SP008. Task-specific exploration is still required for SP002 and for the concrete values inside SP001, SP003, SP004, SP007, and SP008: this case has CKD stage 4, recent heart-failure admission, a different risk score, eGFR instead of phosphorus, a primary-care referral instead of dialysis coordination, and different social-context facts. The visible prompt does not restate these transfer anchors, so the fewshot skill must infer them from train outputs and apply them to the new case.

### Construction record

Author: Codex task-builder worker. Created: 2026-07-17. Updated: 2026-07-17. Major changes: created formal `test_004` prompt, answer template, standard answer, bilingual notes, and deterministic evaluator from `scratch/task_group_design.md`, `scratch/env_blueprint.md`, and `scratch/target_truth_spec.md`.

## 中文

### 来源与任务定义

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，来源示例为 `E001` 到 `E005`。直接设计简述是测试任务 `test_004`：针对 `CASE-CM-908`，解题者需要审查一个心衰住院后合并糖尿病和 CKD 的高风险登记病例，并输出结构化的照护管理分流、优先问题、转介、外联姿态、照护计划最低要求、升级条件以及来源归属分组。

解题者可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示中只给出目标病例编号和运行环境基础地址占位符 `<TASK_ENV_BASE_URL>`，不会暴露来源优先级步骤、评分逻辑、训练锚点或标准答案。预期答案是一个符合模板的 JSON 对象。

### 场景匹配与材料地图

本任务代表任务组中的慢病高风险照护管理操作族。它与源 ESRD/糖尿病照护管理示例一致，因为任务需要解读纵向风险登记、慢病阈值、用药负担、社会风险分流、拒绝敏感的外联方式以及有边界的后续照护计划。本任务把临床重点从透析转为近期心衰入院、糖尿病和 4 期 CKD，但保留相同的协议化分流框架。

共享合成诊所环境是事实来源。相关运行时入口预计包括病例、患者、问题清单、用药、照护登记、SDoH、观察值、协议和只读查询端点，具体以 `environment_access.md` 中列出的访问权限为准。隐藏环境蓝图定义了 Harborview Synthetic Clinic、`CASE-CM-908` 和 `PAT-4908`，包含风险分数 `0.79`、HbA1c `9.1%`、eGFR `28`、血压 `158/92`、14 个当前用药、近期心衰入院背景、交通障碍、经济和食物障碍、用药可及性障碍以及初始犹豫。`CM-HIGH-RISK-2026` 协议支持高风险复杂照护分流、多药或高风险用药触发药师转介、SDoH 障碍触发社工分流、基层医疗随访，以及基于许可的通俗语言外联。

### 解法与评估依据

标准答案将病例分类为 `risk_tier: high` 和 `program: complex_care_management`，患者为 `PAT-4908`。优先问题集合为 `uncontrolled_diabetes`、`chronic_kidney_disease_stage_4`、`heart_failure_recent_admission`、`hypertension`、`polypharmacy`、`transportation_barrier` 和 `financial_food_barrier`。数值锚点为风险分数 `0.79`、HbA1c `9.1`、eGFR `28`、血压 `158/92`、当前用药数 `14`。

转介为 `pharmacist`、`social_worker`、`transportation_benefits` 和 `primary_care`。外联姿态为 `permission_based_plain_language`。照护计划最低结构要求至少 3 个问题、每周随访、需要成员本人陈述优先事项，并至少涉及 2 个学科。升级条件为 `dyspnea_weight_gain_or_ed_return` 和 `phq9_increase_or_item9_positive`。病历事实来源包括 `risk_score`、`hba1c_percent`、`egfr` 和 `active_medication_count`；需要成员披露或确认的来源包括 `transportation_barrier`、`financial_food_barrier` 和 `medication_access_barrier`。

评估器包含 8 个整点评分目标，原始权重为 `[3, 3, 2, 2, 2, 2, 2, 1]`，总权重为 `17`：

1. SP001，权重 3：高风险复杂照护分类正确。
2. SP002，权重 3：优先问题集合和数值锚点正确。
3. SP003，权重 2：由多药和高风险用药触发的药师转介正确。
4. SP004，权重 2：针对障碍模式的社工和交通福利分流正确。
5. SP005，权重 2：拒绝敏感的、基于许可的通俗语言外联姿态正确。
6. SP006，权重 2：照护计划最低结构和每周随访节奏正确。
7. SP007，权重 2：临床和行为健康升级条件集合正确。
8. SP008，权重 1：病历事实与成员披露事实的来源归属正确。

每个评分点只有通过或不通过，不在单点内给部分分。列表按集合归一化。数值锚点按答案模板声明的精度比较。常见模型错误包括在高风险登记结果下仍分到常规个案管理、照搬 `train_004` 的透析专属字段、因为训练答案使用透析协调而漏掉本题的基层医疗、漏掉由 SDoH 驱动的社工分流、对初始犹豫成员使用指令式语言，或把成员披露的可及性障碍当作已经由病历确认的事实。

### 迁移设计与测试锚点

这是一个测试任务。主要迁移锚点是 `train_004`，即复杂 ESRD/糖尿病照护管理分流任务。解题者应迁移以下经验：高风险登记和慢病负担会触发复杂照护管理；多药或高风险用药触发药师审查；交通和经济障碍触发社工和福利分流；起初犹豫的成员需要基于许可的通俗语言外联；照护计划需要最低问题数、每周节奏、成员陈述的优先事项和多学科参与；`source_provenance` 要区分从病历抽取的值和需要成员确认或披露的障碍。

依赖迁移的评分目标是 SP001 以及 SP003 到 SP008。SP002 以及 SP001、SP003、SP004、SP007、SP008 中的具体取值仍需要本题环境探索：本病例有 4 期 CKD、近期心衰入院、不同风险分数、用 eGFR 代替磷值、需要基层医疗转介而不是透析协调，并且有不同的社会背景事实。可见提示不会重述这些迁移锚点，因此 fewshot 技能必须从训练输出中推断规则并应用到新病例。

### 构建记录

作者：Codex task-builder worker。创建日期：2026-07-17。更新日期：2026-07-17。主要变更：根据 `scratch/task_group_design.md`、`scratch/env_blueprint.md` 和 `scratch/target_truth_spec.md` 创建正式的 `test_004` 提示、答案模板、标准答案、双语说明和确定性评估器。
