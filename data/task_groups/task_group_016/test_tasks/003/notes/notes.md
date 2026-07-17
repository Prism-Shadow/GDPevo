# test_003 Notes - Potassium Urgent Escalation Variant

## English

### Data/source lineage

This task belongs to `task_group_016`, derived from `SCN_016_healthcare_clinical_protocol_decision_support` and source examples `E001` through `E005`. Its closest lineage is `E004` for potassium replacement protocol decisions and `E005` for Observation-style lab retrieval by code, status, and time. The task design brief in `scratch/task_group_design.md` defines `test_003` as the urgent potassium escalation variant for `CASE-K-919`.

The solver-visible material is limited to `input/prompt.txt` and `input/payloads/answer_template.json`. Clinical facts are expected to come from the shared synthetic clinic runtime through the separately supplied environment access list. The hidden standard answer is `output/answer.json`.

### Task definition and scenario fit

The business task is protocol-bound order-entry decision support, not order placement or open-ended medical advice. The solver must identify the target patient for `CASE-K-919`, determine the current review time, retrieve potassium and renal-function evidence, choose the correct potassium protocol branch, avoid treating the case as routine oral-only repletion, specify urgent monitoring actions, schedule follow-up potassium testing, report contraindication context, and preserve evidence identifiers.

This fits the clinical decision-support scenario because it combines record retrieval, final-vs-nonfinal lab filtering, threshold-based protocol branching, medication and lab code handling, symptom-sensitive escalation, and safety screening. It remains in the same operation family as `train_003` while changing the final branch from routine replacement to urgent escalation.

### Material map

- `input/prompt.txt`: solver-visible case request using `<TASK_ENV_BASE_URL>` and target case id `CASE-K-919`.
- `input/payloads/answer_template.json`: solver-visible output schema, precision rules, enum choices, list ordering expectations, and nullable fields.
- Shared runtime case data: authoritative source for `CASE-K-919`, patient `PAT-3919`, review time, final serum potassium observations, distractor potassium observations, renal-function observation, symptoms, and contraindication context.
- Shared runtime protocol data: source for potassium thresholds, urgent escalation branch, urgent monitoring action vocabulary, potassium medication code, and follow-up serum potassium LOINC/timing conventions.
- `output/answer.json`: hidden standard answer for evaluation.
- `eval/eval.py` and `eval/eval.sh`: deterministic whole-point evaluator.

### Solution and evaluation basis

The standard answer uses patient `PAT-3919` and review time `2026-04-18T14:35:00Z`. The latest eligible final potassium observation is `OBS-K-919-20260418-1320`, value `2.8 mmol/L`, effective `2026-04-18T13:20:00Z`. Replacement or escalation is required, but the correct protocol branch is `urgent_escalation`, not routine oral-only repletion. The oral dose is `null`. The medication object preserves the potassium NDC `40032-917-01` and medication name `potassium chloride`, with route and frequency deferred to `per_urgent_protocol` and status `defer_to_urgent_clinician`. The follow-up serum potassium lab uses LOINC `2823-3` and is scheduled at `2026-04-18T18:00:00Z`. Required urgent actions are `urgent_clinician_notification`, `ekg_now`, and `telemetry_or_ed_evaluation`. The contraindication and safety context is not dialysis dependent, has arrhythmia symptoms, and has eGFR `58`.

The evaluator implements seven whole-point checks with raw weights from the task design, total raw weight `15`:

1. SP001, weight 3: latest final potassium observation id, value, and effective time.
2. SP002, weight 3: urgent escalation classification with replacement required.
3. SP003, weight 2: no routine oral-only final plan, including null oral dose and urgent-clinician deferral fields.
4. SP004, weight 2: urgent monitoring and escalation action set.
5. SP005, weight 2: follow-up potassium timing under the urgent branch.
6. SP006, weight 2: contraindication, eGFR, rhythm-symptom context, and evidence id set.
7. SP007, weight 1: medication and lab codes where applicable.

Each point is all-or-nothing. Numeric potassium values are normalized to one decimal place; eGFR is checked as an integer; action and evidence lists are normalized as sets where order is not the business result.

Likely model pitfalls include selecting a preliminary or stale potassium result, applying the routine oral dose from `train_003` despite the lower potassium and symptom context, omitting EKG or telemetry/ED evaluation, failing to defer medication route and frequency to the urgent protocol, scheduling the follow-up lab on the routine next-morning cadence, or missing the arrhythmia symptom flag.

### Transfer design

The primary train anchors are `train_003` and `train_005`. From `train_003`, a solver should infer the potassium output shape, final-observation preference, potassium medication code, follow-up serum potassium LOINC, evidence-id style, and separation between medication-order fields and urgent-action fields. From `train_005`, a solver should reinforce Observation filtering habits: exact target code, final status, relevant time window, stable resource ids, and exclusion of distracting observations.

The transfer-dependent scoring goals are SP001 through SP005 and SP007. They rely on the same latest-final lab convention, potassium threshold logic, controlled branch enums, code fields, and branch-specific follow-up style exposed by the train tasks. SP006 has more task-specific exploration weight because the rhythm symptoms and eGFR context must be retrieved from this case's runtime records.

### Construction record

- Author: task-builder worker for `task_group_016 test_003`.
- Created date: 2026-07-17.
- Updated date: 2026-07-17.
- Major changes: Created formal task files for `test_tasks/003`, including solver prompt, answer template, standard answer, bilingual notes, and deterministic evaluator.

## 中文

### 数据与来源脉络

本任务属于 `task_group_016`，来源场景是 `SCN_016_healthcare_clinical_protocol_decision_support`，参考源示例为 `E001` 到 `E005`。最直接的来源是 `E004` 的补钾协议决策，以及 `E005` 的按代码、状态和时间检索 Observation 实验室结果任务。`scratch/task_group_design.md` 将 `test_003` 定义为 `CASE-K-919` 的紧急补钾升级变体。

求解器可见材料仅包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。临床事实应来自共享的合成诊所运行环境，并通过单独提供的环境访问清单获取。隐藏标准答案位于 `output/answer.json`。

### 任务定义与场景契合

业务任务是受协议约束的医嘱录入决策支持，而不是实际下达医嘱或开放式医疗建议。求解器需要识别 `CASE-K-919` 对应患者、确定当前审核时间、检索血钾和肾功能证据、选择正确的补钾协议分支、避免把该病例当作常规口服补钾处理、列出紧急监测行动、安排复查血钾、报告禁忌相关背景，并保留证据编号。

该任务符合临床决策支持场景，因为它结合了病历检索、最终与非最终实验室结果过滤、基于阈值的协议分支、药物和实验室代码处理、症状敏感的升级决策以及安全筛查。它与 `train_003` 属于同一操作家族，但最终分支从常规补钾变为紧急升级。

### 材料地图

- `input/prompt.txt`：求解器可见的病例请求，使用 `<TASK_ENV_BASE_URL>` 和目标病例编号 `CASE-K-919`。
- `input/payloads/answer_template.json`：求解器可见的输出结构、精度规则、枚举选项、列表排序要求和可空字段说明。
- 共享运行环境病例数据：`CASE-K-919`、患者 `PAT-3919`、审核时间、最终血钾 Observation、干扰性血钾 Observation、肾功能 Observation、症状和禁忌信息的权威来源。
- 共享运行环境协议数据：血钾阈值、紧急升级分支、紧急监测行动词表、补钾药物代码，以及复查血清钾 LOINC 和时间惯例的来源。
- `output/answer.json`：用于评估的隐藏标准答案。
- `eval/eval.py` 和 `eval/eval.sh`：确定性的整点评估器。

### 解答与评估依据

标准答案使用患者 `PAT-3919`，审核时间为 `2026-04-18T14:35:00Z`。最新符合条件的最终血钾 Observation 是 `OBS-K-919-20260418-1320`，数值 `2.8 mmol/L`，生效时间 `2026-04-18T13:20:00Z`。需要补钾或升级处理，但正确协议分支是 `urgent_escalation`，不是常规单纯口服补钾。口服剂量为 `null`。药物对象保留 potassium NDC `40032-917-01` 和药名 `potassium chloride`，给药途径和频次为 `per_urgent_protocol`，状态为 `defer_to_urgent_clinician`。复查血清钾实验室使用 LOINC `2823-3`，安排在 `2026-04-18T18:00:00Z`。必要紧急行动为 `urgent_clinician_notification`、`ekg_now` 和 `telemetry_or_ed_evaluation`。禁忌和安全背景为非透析依赖、有心律失常症状、eGFR 为 `58`。

评估器实现七个整点评分项，原始权重来自任务设计，总原始权重为 `15`：

1. SP001，权重 3：最新最终血钾 Observation 的编号、数值和生效时间。
2. SP002，权重 3：需要补钾且分支为紧急升级。
3. SP003，权重 2：最终方案不是常规单纯口服补钾，包括口服剂量为空以及紧急临床人员决策字段。
4. SP004，权重 2：紧急监测和升级行动集合。
5. SP005，权重 2：紧急分支下的复查血钾时间。
6. SP006，权重 2：禁忌、eGFR、心律症状背景和证据编号集合。
7. SP007，权重 1：适用的药物和实验室代码。

每个评分项都是全对才得分。血钾数值按一位小数归一化；eGFR 按整数检查；当顺序不是业务结果时，行动和证据列表按集合归一化。

常见错误包括选择初步或过期血钾结果、在低血钾和症状背景下仍套用 `train_003` 的常规口服剂量、遗漏 EKG 或遥测/急诊评估、没有把药物途径和频次交由紧急协议处理、按常规次日早晨安排复查实验室，或漏掉心律失常症状标志。

### 迁移设计

主要训练锚点是 `train_003` 和 `train_005`。从 `train_003`，求解器应推断补钾输出结构、优先使用最终 Observation 的惯例、补钾药物代码、复查血清钾 LOINC、证据编号风格，以及药物医嘱字段与紧急行动字段的区分。从 `train_005`，求解器应强化 Observation 过滤习惯：精确目标代码、最终状态、相关时间窗口、稳定资源编号，以及排除干扰 Observation。

依赖迁移的评分目标是 SP001 到 SP005 以及 SP007。它们依赖训练任务中出现的最新最终实验室结果惯例、血钾阈值逻辑、受控分支枚举、代码字段和按分支安排复查的风格。SP006 更偏向本任务特定探索，因为心律症状和 eGFR 背景必须从本病例运行环境记录中检索。

### 构建记录

- 作者：`task_group_016 test_003` 的 task-builder worker。
- 创建日期：2026-07-17。
- 更新日期：2026-07-17。
- 主要变更：为 `test_tasks/003` 创建正式任务文件，包括求解器提示、答案模板、标准答案、双语说明和确定性评估器。
