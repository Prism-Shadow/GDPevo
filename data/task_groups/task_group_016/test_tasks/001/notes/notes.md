# test_001 Notes - Adult Respiratory Escalation With Allergy Conflict

## English

### Data and Source Lineage

This task belongs to `task_group_016`, derived from scenario `SCN_016_healthcare_clinical_protocol_decision_support` and source examples `E001` through `E005`. The closest source lineage is `E002`, the adult respiratory SOAP/protocol decision-support example, with supporting conventions from `E005` for observation and evidence identifiers. The task design brief in `scratch/task_group_design.md` defines `test_001` as an adult respiratory escalation task for `CASE-RESP-914`.

The intended data source is the shared synthetic clinic runtime environment for `task_group_016`. The solver-visible local files are `input/prompt.txt` and `input/payloads/answer_template.json`; the clinical facts are retrieved from the runtime environment rather than embedded in the prompt. The hidden standard answer is copied from the `test_001` standard answer in `scratch/target_truth_spec.md`.

### Task Definition and Scenario Fit

The solver must produce a structured respiratory decision-support result for `CASE-RESP-914`. The expected output records the case id, patient id, primary respiratory assessment, risk level, disposition, red flags, recommended tests, medication posture, stabilization actions, follow-up ownership, return or escalation precautions, evidence ids, and safety checks.

This fits the task group because it requires protocol-bound clinical reasoning over a synthetic office record: acute visit facts, oxygen saturation, respiratory distress, chest imaging, allergy context, and respiratory protocol thresholds must be reconciled into a controlled JSON decision. It is not open-ended medical advice; it evaluates structured office-work retrieval and protocol application.

### Material Map

- `input/prompt.txt`: solver-visible business request naming `CASE-RESP-914` and the runtime base URL placeholder.
- `input/payloads/answer_template.json`: solver-visible output schema, controlled enums, required keys, set-ordering rules, and numeric precision.
- Runtime environment at `<TASK_ENV_BASE_URL>`: source for case, patient, encounter note, observations, imaging, allergy list, medications, and respiratory protocol snippets.
- Expected evidence objects: `CASE-RESP-914`, `IMG-RESP-914-CXR`, and `OBS-RESP-914-SPO2`.
- `output/answer.json`: hidden standard answer for evaluation.
- `eval/eval.py` and `eval/eval.sh`: deterministic weighted evaluator for the seven rubric goals.

### Solution and Evaluation Basis

The standard answer classifies the case as `community_acquired_pneumonia` with `high` risk and `ed_transfer` disposition. The relevant red flags are `hypoxemia_below_90`, `pleuritic_chest_pain`, `respiratory_distress`, `persistent_fever`, and `worsening_shortness_of_breath`. The required tests are `CXR-2V`, `PULSE_OX_RECHECK`, and `SARS_FLU_RSV_PCR`. Because the case requires ED transfer and has an active penicillin allergy, the antibiotic posture is `defer_antibiotic_selection_to_ed`; medication, dose, route, frequency, and duration are `null`, and the allergen avoidance set contains `penicillin`. Stabilization actions are `supplemental_oxygen` and `urgent_ed_transfer`. Follow-up ownership is the `emergency_department` with `0` hours, and the escalation precautions are `chest_pain`, `confusion`, `hypoxia`, `persistent_fever`, and `worsening_shortness_of_breath`.

The evaluator has seven whole-point checks with raw weights from the design:

1. SP001, weight 3: correct CAP assessment, high risk, target case/patient identifiers, and red-flag set.
2. SP002, weight 3: correct ED-transfer disposition.
3. SP003, weight 2: exact required diagnostic test set.
4. SP004, weight 2: allergy-safe ED antibiotic posture, null outpatient medication fields, allergen avoidance set, and safety flag.
5. SP005, weight 2: exact stabilization action set before transfer.
6. SP006, weight 1: exact return/escalation precautions and follow-up ownership.
7. SP007, weight 3: exact evidence ids and contradiction-avoidance safety checks.

The raw weight sum is 16. Each scoring point is pass/fail and earns either its full assigned weight share or zero. The checks span respiratory diagnosis, ED disposition, diagnostic testing, allergy-safe medication posture, stabilization, follow-up/escalation precautions, and evidence/safety consistency. Likely model pitfalls include treating the case as outpatient pneumonia, prescribing an outpatient beta-lactam despite allergy, omitting oxygen or urgent transfer actions, missing viral testing or pulse-ox recheck, using broad free text instead of enum fields, or asserting a normal chest x-ray or clear lung findings that contradict the record.

### Transfer Design

This is a test task. The main transfer anchor is `train_001`, which uses the same adult respiratory protocol family and the same structured output conventions. Transfer-dependent scoring goals are SP002, SP004, SP005, and SP006. A successful train-derived skill should infer that respiratory disposition is threshold-bound, active allergies constrain antibiotic posture, controlled test and precaution enums should be used, and contradictory normal-CXR or clear-lung claims should be avoided.

`train_003` also weakly anchors SP005 by reinforcing structured action lists with status-like fields, although this task uses transfer stabilization rather than potassium medication ordering. Task-specific exploration remains necessary for SP001, SP003, and SP007 because the solver must retrieve this case's focal findings, imaging evidence, oxygen observation, and exact evidence identifiers from the environment. The prompt deliberately names the case and output requirement without exposing the hidden protocol sequence or standard answer.

### Construction Record

- Author: task-builder worker for `task_group_016 test_001`
- Created: 2026-07-17
- Updated: 2026-07-17
- Major changes: created the formal test task folder with prompt, answer template, bilingual notes, standard answer, and deterministic evaluator.

## Chinese / 中文

### 数据与来源脉络

本任务属于 `task_group_016`，来源场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，参考源示例为 `E001` 至 `E005`。最直接的来源是 `E002` 成人呼吸系统 SOAP 和协议决策支持示例，同时借用 `E005` 中关于观察记录和证据标识符的约定。`scratch/task_group_design.md` 将 `test_001` 定义为针对 `CASE-RESP-914` 的成人呼吸系统升级处置任务。

预期数据来自 `task_group_016` 的共享合成诊所运行环境。求解者可见的本地文件只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`；临床事实需要从运行环境中检索，而不是写在提示词里。隐藏标准答案来自 `scratch/target_truth_spec.md` 中的 `test_001` 标准答案。

### 任务定义与场景适配

求解者需要为 `CASE-RESP-914` 生成结构化的呼吸系统决策支持结果。输出应包含病例编号、患者编号、主要呼吸系统评估、风险等级、处置去向、危险信号、建议检查、用药姿态、稳定化措施、随访归属、返诊或升级警示、证据编号，以及安全检查。

该任务符合本任务组，因为它要求在合成门诊记录中进行协议化临床推理：急性就诊事实、血氧饱和度、呼吸窘迫、胸部影像、过敏背景和呼吸系统协议阈值都需要被整合为受控 JSON 决策。它不是开放式医疗建议，而是评估结构化办公检索和协议应用能力。

### 材料地图

- `input/prompt.txt`：求解者可见的业务请求，指定 `CASE-RESP-914` 和运行环境基础 URL 占位符。
- `input/payloads/answer_template.json`：求解者可见的输出结构、受控枚举、必填键、集合排序规则和数值精度。
- `<TASK_ENV_BASE_URL>` 运行环境：病例、患者、就诊记录、观察值、影像、过敏列表、用药和呼吸系统协议片段的来源。
- 预期证据对象：`CASE-RESP-914`、`IMG-RESP-914-CXR` 和 `OBS-RESP-914-SPO2`。
- `output/answer.json`：用于评估的隐藏标准答案。
- `eval/eval.py` 与 `eval/eval.sh`：针对七个评分目标的确定性加权评估器。

### 解答与评估依据

标准答案将该病例归类为 `community_acquired_pneumonia`，风险等级为 `high`，处置为 `ed_transfer`。相关危险信号为 `hypoxemia_below_90`、`pleuritic_chest_pain`、`respiratory_distress`、`persistent_fever` 和 `worsening_shortness_of_breath`。必需检查是 `CXR-2V`、`PULSE_OX_RECHECK` 和 `SARS_FLU_RSV_PCR`。由于该病例需要急诊转运且存在活动性青霉素过敏，抗生素姿态为 `defer_antibiotic_selection_to_ed`；用药、剂量、途径、频率和疗程均为 `null`，过敏规避集合包含 `penicillin`。稳定化措施为 `supplemental_oxygen` 和 `urgent_ed_transfer`。随访归属为 `emergency_department`，时间为 `0` 小时；升级警示为 `chest_pain`、`confusion`、`hypoxia`、`persistent_fever` 和 `worsening_shortness_of_breath`。

评估器包含七个整点评分项，原始权重来自设计：

1. SP001，权重 3：CAP 评估、高风险、目标病例/患者标识符和危险信号集合正确。
2. SP002，权重 3：急诊转运处置正确。
3. SP003，权重 2：必需诊断检查集合完全正确。
4. SP004，权重 2：急诊场景下的过敏安全抗生素姿态、门诊用药空值、过敏规避集合和安全标志正确。
5. SP005，权重 2：转运前稳定化措施集合完全正确。
6. SP006，权重 1：返诊或升级警示以及随访归属完全正确。
7. SP007，权重 3：证据编号和避免矛盾断言的安全检查正确。

原始权重总和为 16。每个评分点都是通过或不通过，只能获得该点评分份额的全部或 0 分。评分覆盖呼吸系统诊断、急诊处置、诊断检查、过敏安全用药姿态、稳定化、随访/升级警示，以及证据和安全一致性。常见错误包括把病例当作门诊肺炎、在过敏情况下开门诊 beta-lactam、漏掉吸氧或紧急转运措施、漏掉病毒检测或血氧复测、使用自由文本而不是枚举字段，或声称胸片正常或肺部清亮而与记录矛盾。

### 迁移设计

这是一个测试任务。主要迁移锚点是 `train_001`，它属于同一成人呼吸系统协议家族，并使用相同的结构化输出约定。依赖迁移的评分目标为 SP002、SP004、SP005 和 SP006。成功的训练派生技能应能推断：呼吸系统处置受阈值约束，活动性过敏会限制抗生素姿态，检查和警示应使用受控枚举，并且应避免正常胸片或肺部清亮等矛盾断言。

`train_003` 也对 SP005 有较弱锚定作用，因为它强化了带有状态类字段的结构化动作列表，虽然本任务使用的是转运稳定化措施，而不是钾补充医嘱。SP001、SP003 和 SP007 仍需要任务特定探索，因为求解者必须从环境中检索该病例的局灶性发现、影像证据、血氧观察值和精确证据编号。提示词只给出病例和输出要求，刻意不暴露隐藏协议顺序或标准答案。

### 构建记录

- 作者：`task_group_016 test_001` task-builder worker
- 创建日期：2026-07-17
- 更新日期：2026-07-17
- 主要变更：创建正式测试任务文件夹，包括提示词、答案模板、双语说明、标准答案和确定性评估器。
