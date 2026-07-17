# test_002 Notes - Pediatric Head Injury With High-Risk Symptoms

## English

### Lineage and Task Definition

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, using source examples `E001` through `E005`. The task is the designed test case `test_002` from `scratch/task_group_design.md`: a pediatric sports head-injury protocol decision for `CASE-HEAD-822`.

The solver-visible prompt provides only the target case id, the base URL placeholder `<TASK_ENV_BASE_URL>`, and the requirement to return JSON matching `input/payloads/answer_template.json`. Runtime environment access is supplied separately by the harness. The expected work is to use the synthetic clinic environment to retrieve the case record, patient identifier, neuro and symptom observations, and relevant head-injury protocol material, then return a structured decision-support object.

### Scenario Fit and Material Map

This task fits the acute pediatric head-injury operation family represented by source example `E001` and train task `train_002`. It requires case-level clinical reconciliation, protocol-bound risk classification, red-flag separation, urgent-route selection, restrictions, and source-id provenance. It also uses task-group conventions reinforced across other tasks: environment records are authoritative, observation ids are evidence objects, and final output uses controlled enums rather than free-text advice.

Material map:

- `input/prompt.txt`: visible business request for `CASE-HEAD-822`.
- `input/payloads/answer_template.json`: visible output schema, enum choices, numeric precision, and set-like list conventions.
- Clinic runtime at `<TASK_ENV_BASE_URL>`: source for case, patient, observation, encounter, and protocol records; the exact access endpoints are listed separately during solving.
- `output/answer.json`: hidden standard answer for calibration and evaluation.
- `eval/eval.py`: deterministic weighted checker for the seven scoring points.

### Solution and Evaluation Basis

The standard answer identifies patient `PAT-2822`. The correct assessment is `pediatric_head_injury_with_concussion_features`, with `high` risk tier, `ed_evaluation_ct_consideration` disposition, and `ct_or_ed_per_protocol` imaging posture. Present red flags are `head_impact`, `brief_loss_of_consciousness`, `repeated_vomiting`, and `worsening_headache`; absent red flags are `abnormal_gcs`, `seizure`, `focal_weakness`, and `basilar_skull_signs`. Restrictions are `no_driving_until_cleared`, `no_high_risk_sports_until_cleared`, and `return_to_learn_accommodations`. Follow-up is immediate emergency-department routing with `timeframe_hours` of `0`. Evidence ids are `CASE-HEAD-822`, `VISIT-HEAD-822`, `OBS-HEAD-822-LOC`, `OBS-HEAD-822-GCS`, `OBS-HEAD-822-VOMIT`, `OBS-HEAD-822-NEURO`, and `EXAM-HEAD-822`. The safety checks assert no false seizure and no false focal weakness.

Evaluation uses seven whole-point checks with raw weights from the task design, total raw weight `12`:

- SP001, weight 1: correct primary assessment plus extraction of the three key present symptoms.
- SP002, weight 1: correct high-risk tier.
- SP003, weight 1: correct ED disposition and CT/ED imaging posture.
- SP004, weight 3: exact present red-flag set and absent red-flag set.
- SP005, weight 2: exact restriction set.
- SP006, weight 1: correct immediate follow-up timing and route.
- SP007, weight 3: correct case/patient ids, evidence ids, and contradiction-avoidance booleans.

Likely model pitfalls include treating the case as home observation because GCS is preserved, adding absent seizure or focal weakness as present red flags, missing the repeated-vomiting plus worsening-headache high-risk combination, returning adult-style driving language only, omitting return-to-learn accommodations, or inventing evidence ids.

### Transfer Design

Primary transfer anchor: `train_002`. The train case teaches the head-injury output shape, the distinction between present and absent red flags, restriction enum style, follow-up route fields, and contradiction-check booleans through a real intermediate-risk case rather than a tutorial. For this test case, SP002 through SP006 depend strongly on transferring that head-injury protocol convention while adapting to a more severe symptom pattern and urgent ED route.

Secondary transfer habits come from the broader task group: use environment records rather than prompt summaries, keep source identifiers exact, and represent clinical decisions as controlled enum/set fields. SP001 and SP007 also require task-specific exploration because the solver must retrieve the actual case facts and evidence ids from noisy clinic data.

### Construction Record

Author: task-builder worker for `task_group_016/test_002`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: created solver prompt, answer template, bilingual notes, standard answer, and evaluator for `test_002` from `scratch/task_group_design.md` and `scratch/target_truth_spec.md`.

## 中文

### 来源与任务定义

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，来源示例为 `E001` 至 `E005`。它对应 `scratch/task_group_design.md` 中的测试任务 `test_002`：针对 `CASE-HEAD-822` 的儿童运动相关头部损伤，生成协议约束下的结构化临床决策支持结果。

求解者可见的 `input/prompt.txt` 只给出目标病例编号、基础 URL 占位符 `<TASK_ENV_BASE_URL>`，以及必须匹配 `input/payloads/answer_template.json` 的 JSON 输出要求。运行环境的具体访问方式由评测框架另行提供。预期工作是在合成诊所环境中检索病例、患者、神经系统和症状观察记录，以及相关头部损伤协议材料，然后返回结构化答案。

### 场景适配与材料地图

该任务属于急性儿童头部损伤流程，与来源示例 `E001` 和训练任务 `train_002` 对齐。任务要求综合病例事实、按协议分层、区分存在和不存在的危险信号、选择紧急路径、设置活动和学习限制，并保留证据记录编号。它也延续任务组的通用约定：环境记录优先，观察记录编号是证据对象，最终结果使用受控枚举而不是自由文本建议。

材料地图：

- `input/prompt.txt`：面向求解者的 `CASE-HEAD-822` 业务请求。
- `input/payloads/answer_template.json`：面向求解者的输出结构、枚举、数值精度和集合型列表约定。
- `<TASK_ENV_BASE_URL>` 下的诊所运行环境：提供病例、患者、观察、就诊和协议记录；具体端点在求解时由环境访问文件列出。
- `output/answer.json`：隐藏标准答案，用于校准和评测。
- `eval/eval.py`：针对七个评分点的确定性加权检查器。

### 解答与评测依据

标准答案中的患者为 `PAT-2822`。正确评估为 `pediatric_head_injury_with_concussion_features`，风险层级为 `high`，处置为 `ed_evaluation_ct_consideration`，影像建议为 `ct_or_ed_per_protocol`。存在的危险信号是 `head_impact`、`brief_loss_of_consciousness`、`repeated_vomiting`、`worsening_headache`；不存在的危险信号是 `abnormal_gcs`、`seizure`、`focal_weakness`、`basilar_skull_signs`。限制包括 `no_driving_until_cleared`、`no_high_risk_sports_until_cleared`、`return_to_learn_accommodations`。随访路径是立即急诊，`timeframe_hours` 为 `0`。证据编号是 `CASE-HEAD-822`、`VISIT-HEAD-822`、`OBS-HEAD-822-LOC`、`OBS-HEAD-822-GCS`、`OBS-HEAD-822-VOMIT`、`OBS-HEAD-822-NEURO` 和 `EXAM-HEAD-822`。安全检查要求不要错误声称癫痫或局灶无力。

评测采用七个整点评分项，原始权重来自任务设计，总权重为 `12`：

- SP001，权重 1：正确的主要评估，并提取三个关键存在症状。
- SP002，权重 1：正确的高风险层级。
- SP003，权重 1：正确的急诊处置和 CT/急诊影像策略。
- SP004，权重 3：存在危险信号集合和不存在危险信号集合完全正确。
- SP005，权重 2：限制集合完全正确。
- SP006，权重 1：立即随访时间和路径正确。
- SP007，权重 3：病例、患者编号、证据编号和避免矛盾的布尔字段正确。

常见错误包括因为 GCS 保留而误判为居家观察，把不存在的癫痫或局灶无力列为存在危险信号，遗漏反复呕吐和头痛加重组成的高风险组合，只给出成人式驾驶限制，遗漏返校学习调整，或者编造证据编号。

### 迁移设计

主要迁移锚点是 `train_002`。该训练任务通过一个真实的中间风险病例体现了头部损伤输出结构、存在和不存在危险信号的区分、限制字段枚举、随访路径字段以及矛盾检查布尔字段，并不是教程。对本测试任务而言，SP002 至 SP006 强依赖从该训练任务迁移头部损伤协议约定，同时需要适应更严重的症状组合和急诊路径。

次级迁移习惯来自整个任务组：优先使用环境记录而不是提示摘要，精确保留来源编号，并把临床决定表示为受控枚举或集合字段。SP001 和 SP007 还需要任务特定探索，因为求解者必须从有噪声的诊所数据中检索本病例事实和证据编号。

### 构建记录

作者：`task_group_016/test_002` 的 task-builder worker。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：根据 `scratch/task_group_design.md` 和 `scratch/target_truth_spec.md` 创建 `test_002` 的提示、答案模板、双语说明、标准答案和评测器。
