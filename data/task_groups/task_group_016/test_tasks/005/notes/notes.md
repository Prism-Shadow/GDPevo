# test_005 Notes - Respiratory Observation Window And Treatment Gate

## English

### Lineage and task definition

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, derived from source examples `E002` and `E005` with supporting protocol-gate conventions from `E004`. The task design brief in `scratch/task_group_design.md` defines `test_005` as a respiratory Observation-window and pneumonia protocol-gate task for `CASE-LAB-927`. The standard answer is taken from `scratch/target_truth_spec.md`.

The solver-visible request asks the solver to use the synthetic clinic runtime environment at `<TASK_ENV_BASE_URL>` and return structured JSON matching `input/payloads/answer_template.json`. The target business question is whether patient `PAT-5927` has final respiratory viral panel and chest imaging Observation resources in the May 2026 target window, which resources qualify or are excluded, and how those observations gate the respiratory pneumonia protocol decision.

### Scenario fit and material map

This task fits the group because it combines the FHIR-style Observation retrieval family with respiratory protocol decision support. It requires finding synthetic clinic records, filtering status and time windows, preserving resource ids, and turning evidence into controlled clinical decision fields rather than free narrative.

- `input/prompt.txt`: visible request naming `CASE-LAB-927`, the runtime base URL placeholder, and the required JSON template.
- `input/payloads/answer_template.json`: visible output schema for identifiers, the half-open window, target respiratory observation codes, matching and excluded Observation ids, latest CXR result, viral result, protocol gate, remaining tests, disposition, and antibiotic strategy.
- Runtime clinic environment: expected source for cases, patients, observations, imaging-like Observation resources, respiratory protocol snippets, and optionally the read-only query endpoint when provided in runtime access.
- `output/answer.json`: hidden standard answer used for evaluation and calibration review.
- `eval/eval.py` and `eval/eval.sh`: hidden deterministic evaluator implementing seven weighted whole-point checks.

### Solution and evaluation basis

The answer uses the half-open window from `2026-05-01T00:00:00Z` through `2026-05-04T00:00:00Z`. Target codes are `SARS_FLU_RSV_PCR` and `CXR-2V`. The qualifying final Observation resources are `OBS-VIRAL-927-20260502-1035` and `OBS-CXR-927-20260502-1110`, ordered by effective time and then id. The related exclusions are `OBS-VIRAL-927-PRELIM-20260502` because it is preliminary, `OBS-CXR-927-20260429` because it is outside the target window, and `OBS-CBC-927-20260502` because it is not one of the target respiratory gate codes.

The latest qualifying CXR is `OBS-CXR-927-20260502-1110`, result `right_middle_lobe_infiltrate`, effective at `2026-05-02T11:10:00Z`. The viral panel result is `negative`. Together, these support `protocol_gate` value `bacterial_pneumonia_supported`. The remaining test recommendation is `PULSE_OX_RECHECK`, the disposition is `outpatient_close_followup`, and the antibiotic posture is `standard_outpatient_beta_lactam_plus_macrolide`.

The evaluator implements the design weights exactly: SP001 target-window Observation boolean results, weight 2; SP002 matched Observation id sets and stable ordering, weight 3; SP003 exclusion of wrong-window, preliminary, and wrong-code resources, weight 2; SP004 protocol gate classification using CXR and viral result, weight 1; SP005 remaining-test recommendation, weight 3; SP006 disposition and antibiotic posture, weight 3; SP007 task, case, patient, and target-code identifiers, weight 2. Each point is all-or-nothing and reports assigned score, pass boolean, earned score, and deterministic check details.

Likely model pitfalls include accepting preliminary viral results, using the prior April CXR, including CBC as a respiratory gate Observation, losing stable Observation id order, treating a negative viral panel as excluding bacterial pneumonia despite a focal infiltrate, or selecting an ED disposition without target-case evidence.

### Transfer design

This is a test task. Its strongest transfer anchors are `train_005` and `train_001`. From `train_005`, a solver can infer that final Observation status controls eligibility, half-open windows must be applied exactly, wrong-code and wrong-window resources should be excluded, and matching Observation ids should be returned in stable effective-time order. From `train_001`, a solver can infer the respiratory disposition vocabulary, remaining-test style, and pneumonia antibiotic posture conventions.

Transfer-dependent scoring goals are SP001 through SP006, with the strongest emphasis on matching observations, remaining-test posture, and the disposition/antibiotic decision. SP007 still requires task-specific environment exploration. The prompt does not reveal the hidden answer path, scoring weights, or source-precedence checklist; it only states the business request and output contract.

### Construction record

Author: Codex task-builder worker for `task_group_016/test_005`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: created the formal task folder for test task 005 with solver prompt, answer template, hidden standard answer, bilingual notes, and deterministic evaluator.

## Chinese / 中文

### 来源和任务定义

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，主要承接源示例 `E002` 与 `E005` 的呼吸道协议判断和 Observation 检索经验，同时借用了 `E004` 的协议门控结构。`scratch/task_group_design.md` 将 `test_005` 定义为 `CASE-LAB-927` 的呼吸道 Observation 时间窗和肺炎协议门控任务，标准答案来自 `scratch/target_truth_spec.md`。

求解者可见输入要求使用 `<TASK_ENV_BASE_URL>` 对应的合成诊所运行环境，并按 `input/payloads/answer_template.json` 返回结构化 JSON。核心业务问题是判断 `PAT-5927` 在 2026 年 5 月目标窗口内是否有最终状态的呼吸道病毒面板和胸片 Observation，哪些资源合格或应排除，以及这些证据如何决定肺炎协议门控、剩余检查、处置和抗生素策略。

### 场景适配和材料地图

本题同时覆盖 FHIR 风格 Observation 检索和呼吸道临床协议决策。它要求查询合成诊所记录，按状态与时间窗过滤，保留资源 id，并把证据转化为受控临床决策字段，而不是自由文本。

- `input/prompt.txt`：可见任务请求，给出 `CASE-LAB-927`、运行环境占位符和输出模板要求。
- `input/payloads/answer_template.json`：可见输出结构，约束标识符、半开时间窗、目标呼吸道 Observation 代码、匹配与排除资源 id、最新胸片结果、病毒结果、协议门控、剩余检查、处置和抗生素策略。
- 运行时诊所环境：用于查询病例、患者、Observation、影像类 Observation、呼吸道协议片段；在运行访问文件提供时，也可使用只读查询接口。
- `output/answer.json`：隐藏标准答案，用于评估和校准复核。
- `eval/eval.py`、`eval/eval.sh`：隐藏确定性评估器，实现七个加权整点评分项。

### 解法和评估依据

本题使用从 `2026-05-01T00:00:00Z` 到 `2026-05-04T00:00:00Z` 的半开时间窗。目标代码为 `SARS_FLU_RSV_PCR` 和 `CXR-2V`。合格的最终 Observation 资源是 `OBS-VIRAL-927-20260502-1035` 与 `OBS-CXR-927-20260502-1110`，按生效时间再按 id 排序。相关排除资源包括：`OBS-VIRAL-927-PRELIM-20260502`，因为它是 preliminary；`OBS-CXR-927-20260429`，因为它在目标窗口外；`OBS-CBC-927-20260502`，因为它不是目标呼吸道门控代码。

最新合格胸片为 `OBS-CXR-927-20260502-1110`，结果是 `right_middle_lobe_infiltrate`，时间为 `2026-05-02T11:10:00Z`。病毒面板结果为 `negative`。两者共同支持 `protocol_gate` 为 `bacterial_pneumonia_supported`。剩余检查建议是 `PULSE_OX_RECHECK`，处置为 `outpatient_close_followup`，抗生素策略为 `standard_outpatient_beta_lactam_plus_macrolide`。

评估器严格使用设计权重：SP001 目标窗口内 Observation 布尔结果，权重 2；SP002 匹配 Observation id 集合及稳定顺序，权重 3；SP003 正确排除窗口外、preliminary 和错误代码资源，权重 2；SP004 基于胸片和病毒结果的协议门控分类，权重 1；SP005 剩余检查建议，权重 3；SP006 处置和抗生素策略，权重 3；SP007 任务、病例、患者和目标代码标识，权重 2。每个评分项只能整点通过或失败，并输出分值、通过布尔值、得分和确定性检查细节。

常见错误包括采纳 preliminary 病毒结果、使用 4 月旧胸片、把 CBC 误当作呼吸道门控 Observation、破坏 Observation id 的稳定顺序、在有局灶浸润时因病毒阴性而否定细菌性肺炎，或在缺少目标病例证据时选择急诊处置。

### 迁移设计

这是测试任务，最重要的迁移锚点是 `train_005` 和 `train_001`。从 `train_005` 可迁移的经验包括：final 状态决定 Observation 是否合格，半开时间窗必须精确应用，错误代码和窗口外资源需要排除，匹配 Observation id 应按生效时间稳定排序。从 `train_001` 可迁移的经验包括：呼吸道处置枚举、剩余检查表达方式和肺炎抗生素策略约定。

依赖迁移的主要评分项是 SP001 到 SP006，其中匹配 Observation、剩余检查姿态和处置/抗生素决策权重最高。SP007 仍需要针对本题的环境探索。提示词没有暴露隐藏答案路径、评分权重或源优先级清单，只给出业务请求和输出契约。

### 构建记录

作者：Codex task-builder worker for `task_group_016/test_005`。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：为测试任务 005 创建正式任务文件夹，包括求解者提示、答案模板、隐藏标准答案、双语说明和确定性评估器。
