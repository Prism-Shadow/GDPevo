# train_001 Notes - Adult Respiratory Protocol Assessment

## English

### Data and Source Lineage

This task belongs to `task_group_016`, derived from scenario `SCN_016_healthcare_clinical_protocol_decision_support` and source examples `E001` through `E005`. The closest source lineage is `E002`, the adult respiratory SOAP/protocol decision-support example, with supporting conventions from `E005` for observation and evidence identifiers. The task design brief in `scratch/task_group_design.md` defines `train_001` as an adult respiratory protocol assessment for `CASE-RESP-102`.

The intended data source is the shared synthetic clinic runtime environment for `task_group_016`. The solver-visible local files are `input/prompt.txt` and `input/payloads/answer_template.json`; the clinical facts are retrieved from the runtime environment rather than embedded in the prompt.

### Task Definition and Scenario Fit

The solver must produce a structured nurse-practitioner decision-support summary for `CASE-RESP-102`. The expected output records the case id, patient id, primary respiratory assessment, risk level, disposition, red flags, recommended tests, medication plan, stabilization actions, follow-up route and timing, return precautions, evidence ids, and safety checks.

This fits the task group because it requires clinical protocol reasoning over a synthetic office record: acute visit facts, oxygen saturation, chest imaging, allergies, active medication context, and protocol thresholds must be reconciled into a structured decision. It is not open-ended medical advice; it is a controlled protocol-output task.

### Material Map

- `input/prompt.txt`: solver-visible business request naming `CASE-RESP-102` and the runtime base URL placeholder.
- `input/payloads/answer_template.json`: solver-visible output schema, controlled enums, required keys, set-ordering rules, and numeric precision.
- Runtime environment at `<TASK_ENV_BASE_URL>`: source for case, patient, encounter note, observations, imaging, allergy list, medications, and respiratory protocol snippets.
- Expected evidence objects: `CASE-RESP-102`, `IMG-RESP-102-CXR`, and `OBS-RESP-102-SPO2`.
- `output/answer.json`: hidden standard answer for calibration and fewshot skill generation.
- `eval/eval.py` and `eval/eval.sh`: deterministic weighted evaluator for the seven rubric goals.

### Solution and Evaluation Basis

The standard answer classifies the case as `community_acquired_pneumonia` with `moderate` risk and `outpatient_close_followup`. The relevant red flags are `hypoxemia_92_93` and `pleuritic_chest_pain`. The required tests are `CXR-2V`, `PULSE_OX_RECHECK`, and `SARS_FLU_RSV_PCR`. Because active allergies include penicillin and sulfonamide, the outpatient antibiotic strategy is `doxycycline_outpatient` with doxycycline `100 mg` by `PO` route, `BID`, for `5` days, while avoiding both allergens. There are no immediate stabilization actions. Follow-up is `primary_care_recheck` in `48` hours, and the return precautions are `chest_pain`, `confusion`, `hemoptysis`, `hypoxia`, `persistent_fever`, and `worsening_shortness_of_breath`.

The evaluator has seven whole-point checks with raw weights from the design:

1. SP001, weight 3: correct primary respiratory classification, moderate risk, target identifiers, red flags, and diagnosis evidence.
2. SP002, weight 3: correct outpatient disposition without ED-style stabilization actions.
3. SP003, weight 2: exact required diagnostic test set.
4. SP004, weight 3: allergy-safe antibiotic strategy, doxycycline selection, allergen avoidance set, and safety flag.
5. SP005, weight 2: exact medication dose, route, frequency, and duration.
6. SP006, weight 2: exact return-precaution set.
7. SP007, weight 1: correct follow-up timing/route and contradiction-avoidance safety checks.

The raw weight sum is 16. Each scoring point is pass/fail and earns either its full assigned weight share or zero. The checks span respiratory diagnosis, disposition, diagnostic testing, allergy-safe treatment, medication ordering details, return precautions, and follow-up/safety consistency. Likely model pitfalls include treating the CXR as normal, ignoring the oxygen saturation threshold, choosing a beta-lactam despite allergy, omitting viral testing, adding ED transfer actions for a moderate outpatient case, or writing free-text advice instead of the controlled JSON schema.

### Transfer Design

As a train task, this example teaches transferable conventions only through the solved input/answer pair. Useful inferred conventions include: environment records are authoritative over short prompts; respiratory disposition is threshold-bound; active allergies constrain antibiotic posture; diagnostic test outputs use controlled codes; return precautions are represented as enum sets; and contradiction checks such as no normal-CXR or clear-lung claim are explicit structured booleans. These conventions transfer to respiratory test tasks and to observation/protocol tasks that use evidence ids and controlled actions.

### Construction Record

- Author: task-builder worker for `task_group_016 train_001`
- Created: 2026-07-17
- Updated: 2026-07-17
- Major changes: created the formal train task folder with prompt, answer template, bilingual notes, standard answer, and deterministic evaluator.

## Chinese / 中文

### 数据与来源脉络

本任务属于 `task_group_016`，来源场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，参考源示例为 `E001` 至 `E005`。最直接的来源是 `E002` 成人呼吸系统 SOAP 和协议决策支持示例，同时借用 `E005` 中关于观察记录和证据标识符的约定。`scratch/task_group_design.md` 将 `train_001` 定义为针对 `CASE-RESP-102` 的成人呼吸系统协议评估任务。

预期数据来自 `task_group_016` 的共享合成诊所运行环境。求解者可见的本地文件只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`；临床事实需要从运行环境中检索，而不是写在提示词里。

### 任务定义与场景适配

求解者需要为 `CASE-RESP-102` 生成结构化的执业护士决策支持摘要。输出应包含病例编号、患者编号、主要呼吸系统评估、风险等级、处置去向、危险信号、建议检查、用药方案、稳定化措施、随访路径和时间、返诊警示、证据编号，以及安全检查。

该任务符合本任务组，因为它要求在合成门诊记录中进行协议化临床推理：急性就诊事实、血氧饱和度、胸部影像、过敏史、当前用药背景和协议阈值都需要被整合为结构化决策。它不是开放式医疗建议，而是受控的协议输出任务。

### 材料地图

- `input/prompt.txt`：求解者可见的业务请求，指定 `CASE-RESP-102` 和运行环境基础 URL 占位符。
- `input/payloads/answer_template.json`：求解者可见的输出结构、受控枚举、必填键、集合排序规则和数值精度。
- `<TASK_ENV_BASE_URL>` 运行环境：病例、患者、就诊记录、观察值、影像、过敏列表、用药和呼吸系统协议片段的来源。
- 预期证据对象：`CASE-RESP-102`、`IMG-RESP-102-CXR` 和 `OBS-RESP-102-SPO2`。
- `output/answer.json`：用于校准和 fewshot 技能生成的隐藏标准答案。
- `eval/eval.py` 与 `eval/eval.sh`：针对七个评分目标的确定性加权评估器。

### 解答与评估依据

标准答案将该病例归类为 `community_acquired_pneumonia`，风险等级为 `moderate`，处置为 `outpatient_close_followup`。相关危险信号为 `hypoxemia_92_93` 和 `pleuritic_chest_pain`。必需检查是 `CXR-2V`、`PULSE_OX_RECHECK` 和 `SARS_FLU_RSV_PCR`。由于活动性过敏包括青霉素和磺胺类，门诊抗生素策略为 `doxycycline_outpatient`，用药为 doxycycline `100 mg`、`PO`、`BID`、`5` 天，并避免这两类过敏原。不需要立即稳定化措施。随访为 `48` 小时内 `primary_care_recheck`，返诊警示包括 `chest_pain`、`confusion`、`hemoptysis`、`hypoxia`、`persistent_fever` 和 `worsening_shortness_of_breath`。

评估器包含七个整点评分项，原始权重来自设计：

1. SP001，权重 3：主要呼吸系统分类、中等风险、目标标识符、危险信号和诊断证据正确。
2. SP002，权重 3：门诊处置正确，且没有急诊转运式稳定化措施。
3. SP003，权重 2：必需诊断检查集合完全正确。
4. SP004，权重 3：抗生素策略、doxycycline 选择、过敏原规避集合和安全标志正确。
5. SP005，权重 2：剂量、给药途径、频率和疗程完全正确。
6. SP006，权重 2：返诊警示集合完全正确。
7. SP007，权重 1：随访时间和路径正确，且避免正常胸片或肺部清亮等矛盾断言。

原始权重总和为 16。每个评分点都是通过或不通过，只能获得该点评分份额的全部或 0 分。评分覆盖呼吸系统诊断、处置去向、诊断检查、过敏安全治疗、用药医嘱细节、返诊警示，以及随访和安全一致性。常见错误包括把胸片当作正常、忽略血氧阈值、在过敏情况下选择 beta-lactam、漏掉病毒检测、为中等风险门诊病例添加急诊转运措施，或输出自由文本而不是受控 JSON。

### 迁移设计

作为训练任务，本任务只通过真实任务输入和标准答案让技能生成器推断可迁移经验。可迁移约定包括：运行环境记录比简短提示更权威；呼吸系统处置受阈值约束；活动性过敏会限制抗生素方案；诊断检查使用受控代码；返诊警示用枚举集合表示；正常胸片或肺部清亮等矛盾断言通过结构化布尔字段显式检查。这些约定可迁移到呼吸系统测试任务，也可迁移到使用证据编号和受控动作的观察值/协议任务。

### 构建记录

- 作者：`task_group_016 train_001` task-builder worker
- 创建日期：2026-07-17
- 更新日期：2026-07-17
- 主要变更：创建正式训练任务文件夹，包括提示词、答案模板、双语说明、标准答案和确定性评估器。
