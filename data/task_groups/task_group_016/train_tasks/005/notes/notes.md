# train_005 Notes - Observation Window Retrieval And Protocol Gate

## English

### Lineage and task definition

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, derived from source examples `E004` and `E005` with supporting conventions also shared with `E002`. The task design brief in `scratch/task_group_design.md` defines `train_005` as an observation-window retrieval task for `CASE-LAB-518`. The standard answer is taken from `scratch/target_truth_spec.md`.

The solver-visible request is intentionally concise: use the synthetic clinic runtime environment at `<TASK_ENV_BASE_URL>`, review the target case, and return structured JSON matching `input/payloads/answer_template.json`. The target business question is whether patient `PAT-5518` had final serum potassium observations during the March 2026 window, which observations qualify, which case-relevant distractors are excluded, and how the observation result gates the potassium protocol.

### Material map

- `input/prompt.txt`: visible business request naming `CASE-LAB-518` and the runtime environment placeholder.
- `input/payloads/answer_template.json`: visible schema for the JSON output, including stable id fields, window fields, matched and excluded Observation id lists, latest final potassium value, protocol gate, and repeat-lab recommendation.
- Runtime clinic environment: expected source of cases, patients, observations, and protocols. Relevant endpoint families are cases, patients, observations, protocols, and optionally the read-only query endpoint when provided in runtime access.
- `output/answer.json`: hidden standard answer used for train-set examples and evaluator verification.
- `eval/eval.py` and `eval/eval.sh`: hidden deterministic evaluator for seven weighted whole-point checks.

### Solution and evaluation basis

The answer uses the March 2026 half-open window from `2026-03-01T00:00:00Z` through `2026-04-01T00:00:00Z`. The target Observation code is `K` for serum potassium. Final same-code observations in the window for the target patient are `OBS-K-518-20260305-0810` and `OBS-K-518-20260320-0745`, ordered by effective time and then id. The latest final potassium is `OBS-K-518-20260320-0745`, value `3.6 mmol/L`, effective at `2026-03-20T07:45:00Z`.

Case-relevant exclusions are `OBS-K-518-20260227-0900` because it is outside the March window, `OBS-K-518-PRELIM-20260328` because preliminary observations do not satisfy the protocol gate, and `OBS-NA-518-20260315` because it is the wrong code. Because the latest qualifying potassium is a recent final normal result, `protocol_gate` is `satisfies_recent_final_normal` and no repeat lab should be scheduled.

The evaluator implements the design weights exactly: SP001 window inclusion and `lab_found` result, weight 3; SP002 complete matched Observation id set and order, weight 3; SP003 exclusion of preliminary, wrong-code, and wrong-window resources, weight 2; SP004 latest final value and timestamp, weight 2; SP005 protocol gate, weight 2; SP006 repeat-lab recommendation and timing, weight 2; SP007 task, case, patient, and target-code identifiers, weight 1. Each point is all-or-nothing and reports its assigned score, pass boolean, and earned score.

Likely model pitfalls include treating preliminary observations as valid, using a stale February potassium because it is near the window, including the sodium observation as a potassium result, sorting ids lexically rather than by effective time, or recommending repeat testing despite a normal final in-window potassium.

### Transfer design

As a train task, this example exposes transferable conventions without being a tutorial. Comparing a solver attempt against `output/answer.json` can teach that final Observation status controls protocol eligibility, half-open time windows matter, same-code labs should be ordered by `effective_time`, distractor resources should be named explicitly when requested, and protocol-gate results should be normalized as controlled enum values. These conventions anchor later potassium and respiratory observation-window tasks, especially `test_003` and `test_005`.

### Construction record

Author: Codex task-builder worker for `task_group_016/train_005`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: created the formal task folder for train task 005 with solver prompt, answer template, hidden standard answer, bilingual notes, and deterministic evaluator.

## Chinese / 中文

### 来源和任务定义

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，主要承接源示例 `E004` 与 `E005` 的化验检索和协议判断经验，同时与 `E002` 中的协议化临床判断保持一致。`scratch/task_group_design.md` 将 `train_005` 定义为 `CASE-LAB-518` 的 Observation 时间窗检索任务，标准答案来自 `scratch/target_truth_spec.md`。

求解者可见的输入只说明需要使用 `<TASK_ENV_BASE_URL>` 对应的合成诊所运行环境，并按 `input/payloads/answer_template.json` 返回结构化 JSON。核心业务问题是判断 `PAT-5518` 在 2026 年 3 月窗口内是否有最终状态的血清钾 Observation，哪些资源合格，哪些相关干扰资源应排除，以及该结果如何触发或关闭钾补充协议的后续化验门控。

### 材料地图

- `input/prompt.txt`：可见任务请求，给出 `CASE-LAB-518` 和运行环境占位符。
- `input/payloads/answer_template.json`：可见输出结构，约束病例、患者、时间窗、匹配和排除的 Observation id、最新最终钾值、协议门控和复查化验建议。
- 运行时诊所环境：用于查询病例、患者、Observation 和协议；在运行访问文件提供时，也可使用只读查询接口。
- `output/answer.json`：隐藏标准答案，用于训练样例和评估校验。
- `eval/eval.py`、`eval/eval.sh`：隐藏确定性评估器，实现七个加权整点评分项。

### 解法和评估依据

本题使用从 `2026-03-01T00:00:00Z` 到 `2026-04-01T00:00:00Z` 的半开时间窗。目标 Observation 代码为血清钾 `K`。目标患者在窗口内、代码正确且状态为 final 的 Observation 是 `OBS-K-518-20260305-0810` 和 `OBS-K-518-20260320-0745`，按生效时间再按 id 排序。最新最终钾值来自 `OBS-K-518-20260320-0745`，数值为 `3.6 mmol/L`，时间为 `2026-03-20T07:45:00Z`。

需要排除的相关干扰资源包括：`OBS-K-518-20260227-0900`，因为它在窗口外；`OBS-K-518-PRELIM-20260328`，因为 preliminary 状态不能满足协议门控；`OBS-NA-518-20260315`，因为代码不是钾。由于最新合格钾值是窗口内近期最终正常结果，`protocol_gate` 为 `satisfies_recent_final_normal`，不建议安排复查化验。

评估器严格使用设计权重：SP001 时间窗纳入和 `lab_found` 布尔结果，权重 3；SP002 完整匹配 Observation id 集合及顺序，权重 3；SP003 正确排除 preliminary、错误代码和窗口外资源，权重 2；SP004 最新最终值和时间戳，权重 2；SP005 协议门控结果，权重 2；SP006 复查化验建议和时间，权重 2；SP007 任务、病例、患者和目标代码标识，权重 1。每个评分项只能整点通过或失败，不给项内部分分。

常见错误包括把 preliminary 资源当作有效化验、使用接近窗口但属于 2 月的旧钾值、把钠 Observation 误纳入钾结果、按字符串而不是生效时间排序，或在已有正常最终窗口内钾值时仍建议复查。

### 迁移设计

作为训练任务，本题不是教程，但通过标准答案可以让 few-shot 技能归纳出可迁移规则：Observation 的 final 状态决定协议资格，半开时间窗需要精确处理，同代码化验应按 `effective_time` 排序，在被要求时需要显式列出相关排除资源，并且协议门控结果应使用受控枚举。这些经验会支持后续钾协议任务和呼吸道 Observation 时间窗任务，尤其是 `test_003` 与 `test_005`。

### 构建记录

作者：Codex task-builder worker for `task_group_016/train_005`。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：为训练任务 005 创建正式任务文件夹，包括求解者提示、答案模板、隐藏标准答案、双语说明和确定性评估器。
