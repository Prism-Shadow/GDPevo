# train_003 Notes - Potassium Replacement And Follow-Up Lab

## English

### Data/source lineage

This task belongs to `task_group_016`, derived from `SCN_016_healthcare_clinical_protocol_decision_support` and source examples `E001` through `E005`. Its closest lineage is `E004` for potassium replacement protocol work and `E005` for Observation-style lab retrieval by code, status, and time. The task design brief in `scratch/task_group_design.md` identifies `train_003` as the routine potassium replacement and follow-up lab case for `CASE-K-303`.

The solver-visible material is limited to `input/prompt.txt` and `input/payloads/answer_template.json`. The clinical facts are expected to come from the shared synthetic clinic runtime through the separately supplied environment access list. The hidden standard answer is `output/answer.json`.

### Task definition and scenario fit

The business task is an order-entry support recommendation, not an order placement. The solver must identify the target patient for `CASE-K-303`, determine the current review time, retrieve potassium and renal-function evidence, classify the replacement branch, fill the medication recommendation, schedule the follow-up potassium lab, and state whether urgent escalation is needed.

This fits the clinical decision-support scenario because it combines record retrieval, lab status filtering, protocol threshold application, medication coding, follow-up timing, and safety screening. It mirrors the long-horizon workflow of the seed examples without exposing a step list in the prompt.

### Material map

- `input/prompt.txt`: solver-visible case request using `<TASK_ENV_BASE_URL>` and the target case id.
- `input/payloads/answer_template.json`: solver-visible output schema, precision rules, enum choices, list ordering expectations, and nullable fields.
- Shared runtime case data: authoritative source for `CASE-K-303`, patient `PAT-3303`, current review time, final serum potassium observations, distractor potassium observations, renal-function observation, symptoms, and contraindication context.
- Shared runtime protocol data: source for potassium replacement thresholds, oral dose, medication code, and follow-up lab code/timing conventions.
- `output/answer.json`: hidden standard answer used as the train solution.
- `eval/eval.py` and `eval/eval.sh`: deterministic whole-point evaluator.

### Solution and evaluation basis

The standard answer uses `PAT-3303` and clinical review time `2026-02-10T10:15:00Z`. The latest eligible final potassium observation is `OBS-K-303-20260210-0620`, value `3.2 mmol/L`, effective `2026-02-10T06:20:00Z`. Replacement is required and the plan is `routine_oral_repletion`. The oral dose is `30 mEq`. The medication order is potassium chloride oral, NDC `40032-917-01`, route `PO`, frequency `once`, status `recommended`. The follow-up serum potassium lab uses LOINC `2823-3` scheduled for `2026-02-11T08:00:00Z`. The contraindication screen is negative for dialysis dependence and arrhythmia symptoms, with eGFR `64`, so `urgent_actions` is empty.

The evaluator implements seven whole-point checks with raw weights from the task design, total raw weight `15`:

1. SP001, weight 3: latest final potassium observation id, value, and effective time.
2. SP002, weight 2: replacement-required boolean.
3. SP003, weight 3: oral potassium dose calculation.
4. SP004, weight 2: medication code, medication name, route, frequency, and recommendation status.
5. SP005, weight 3: follow-up potassium LOINC and scheduled timestamp.
6. SP006, weight 1: routine/no-urgent-escalation branch and contraindication screen.
7. SP007, weight 1: task, case, patient, current-time, and evidence identifiers.

Each point is all-or-nothing. Numeric values are normalized to the declared precision. Sets such as evidence ids are normalized before comparison when order is not the business result.

Likely model pitfalls include selecting a preliminary or stale potassium result, omitting the renal-function safety screen, confusing potassium lab code `K` with follow-up LOINC `2823-3`, scheduling the follow-up immediately instead of next morning, or recommending urgent escalation despite the negative symptom and renal screen.

### Transfer design

As a train task, this example exposes transferable conventions through the final prompt and answer pair: prefer final observations over preliminary or stale records; use the target case id to join patient, labs, and protocol context; preserve Observation ids as evidence; represent protocol outcomes with controlled enums; separate medication recommendation fields from urgent action fields; and use the serum potassium follow-up LOINC when scheduling the follow-up lab.

Those conventions are intended to transfer especially to `test_003`, where potassium is lower and symptoms change the branch to urgent escalation, and to `test_005`, where Observation-window filtering and stable id handling recur in a respiratory protocol gate.

### Construction record

- Author: task-builder worker for `task_group_016 train_003`.
- Created date: 2026-07-17.
- Updated date: 2026-07-17.
- Major changes: Created formal task files for `train_tasks/003`, including solver prompt, answer template, standard answer, bilingual notes, and deterministic evaluator.

## 中文

### 数据与来源脉络

本任务属于 `task_group_016`，来源场景是 `SCN_016_healthcare_clinical_protocol_decision_support`，参考源示例为 `E001` 到 `E005`。最直接的来源是 `E004` 的补钾协议任务，以及 `E005` 的按代码、状态和时间窗口检索 Observation 实验室结果任务。`scratch/task_group_design.md` 将 `train_003` 定义为 `CASE-K-303` 的常规补钾和复查实验室任务。

求解器可见材料仅包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。临床事实应来自共享的合成诊所运行环境，并通过单独提供的环境访问清单获取。隐藏标准答案位于 `output/answer.json`。

### 任务定义与场景契合

业务任务是生成医嘱录入支持建议，而不是实际下达医嘱。求解器需要识别 `CASE-K-303` 对应患者、确定当前审核时间、检索血钾和肾功能证据、判断补钾分支、填写药物建议、安排复查血钾实验室检查，并说明是否需要紧急升级处理。

该任务符合临床决策支持场景，因为它结合了病历检索、实验室状态过滤、协议阈值应用、药物编码、复查时间安排和安全筛查。它保留了源示例中的长流程工作特征，同时没有在求解器提示中暴露步骤清单。

### 材料地图

- `input/prompt.txt`：求解器可见的病例请求，包含 `<TASK_ENV_BASE_URL>` 和目标病例编号。
- `input/payloads/answer_template.json`：求解器可见的输出结构、精度规则、枚举选项、列表排序要求和可空字段说明。
- 共享运行环境病例数据：`CASE-K-303`、患者 `PAT-3303`、当前审核时间、最终血钾 Observation、干扰性血钾 Observation、肾功能 Observation、症状和禁忌信息的权威来源。
- 共享运行环境协议数据：补钾阈值、口服剂量、药物代码和复查实验室代码及时间惯例的来源。
- `output/answer.json`：隐藏标准答案，用作训练任务答案。
- `eval/eval.py` 和 `eval/eval.sh`：确定性的整点评分器。

### 解答与评估依据

标准答案使用患者 `PAT-3303`，临床审核时间为 `2026-02-10T10:15:00Z`。最新符合条件的最终血钾 Observation 是 `OBS-K-303-20260210-0620`，数值 `3.2 mmol/L`，生效时间 `2026-02-10T06:20:00Z`。需要补钾，计划为 `routine_oral_repletion`。口服剂量为 `30 mEq`。药物建议为 potassium chloride oral，NDC `40032-917-01`，途径 `PO`，频次 `once`，状态 `recommended`。复查血钾实验室 LOINC 为 `2823-3`，安排在 `2026-02-11T08:00:00Z`。禁忌筛查显示非透析依赖、无心律失常症状、eGFR 为 `64`，因此 `urgent_actions` 为空。

评估器实现七个整点评分项，原始权重来自任务设计，总原始权重为 `15`：

1. SP001，权重 3：最新最终血钾 Observation 的编号、数值和生效时间。
2. SP002，权重 2：是否需要补钾的布尔值。
3. SP003，权重 3：口服补钾剂量计算。
4. SP004，权重 2：药物代码、药名、途径、频次和推荐状态。
5. SP005，权重 3：复查血钾 LOINC 和安排时间。
6. SP006，权重 1：常规且无需紧急升级的分支，以及禁忌筛查。
7. SP007，权重 1：任务、病例、患者、当前时间和证据编号。

每个评分项都是全对才得分。数值按声明精度归一化。证据编号等集合在比较前会归一化，因为顺序不是该项的业务结果。

常见错误包括选择初步或过期的血钾结果、遗漏肾功能安全筛查、混淆血钾代码 `K` 与复查 LOINC `2823-3`、把复查安排为立即而非次日早晨，或在症状和肾功能筛查均不支持时错误建议紧急升级。

### 迁移设计

作为训练任务，本例通过提示和标准答案暴露可迁移惯例：优先使用最终 Observation 而非初步或过期记录；用目标病例编号关联患者、实验室和协议上下文；保留 Observation 编号作为证据；用受控枚举表达协议结论；区分药物建议字段与紧急行动字段；安排复查时使用血清钾 LOINC。

这些惯例尤其用于迁移到 `test_003`，其中血钾更低且症状使分支变为紧急升级；也用于迁移到 `test_005`，其中 Observation 时间窗口过滤和稳定编号处理在呼吸协议门控中再次出现。

### 构建记录

- 作者：`task_group_016 train_003` 的 task-builder worker。
- 创建日期：2026-07-17。
- 更新日期：2026-07-17。
- 主要变更：为 `train_tasks/003` 创建正式任务文件，包括求解器提示、答案模板、标准答案、双语说明和确定性评估器。
