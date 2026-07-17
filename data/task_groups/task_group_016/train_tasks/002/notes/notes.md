# train_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_016`, scenario `SCN_016_healthcare_clinical_protocol_decision_support`, with source examples `E001` through `E005`. The direct design anchor is the pediatric head-injury workflow represented by source example `E001`, adapted into a synthetic clinic environment case. The task target is `CASE-HEAD-207` for patient `PAT-2207`.

Solver-visible material is intentionally limited to `input/prompt.txt` and `input/payloads/answer_template.json`. Clinical facts, protocol snippets, visit details, observations, and patient identifiers are retrieved from the shared read-only synthetic clinic runtime at `<TASK_ENV_BASE_URL>`.

### Task Definition and Scenario Fit

The solver must produce a structured clinical decision-support output for a pediatric head injury case. The work requires reconciling case details, neuro observations, symptom history, and the clinic protocol into a bounded JSON answer. This fits the scenario because it mirrors protocol-bound clinical office work: facts are spread across records, risk-tier logic matters, and the final output must avoid unsupported findings.

Expected output includes the head-injury assessment, risk tier, disposition, CT/imaging recommendation, present and absent red flags, activity and school restrictions, follow-up timing, evidence identifiers, and safety booleans.

### Material Map

- `input/prompt.txt`: solver-visible business request for `CASE-HEAD-207`; it names the case and environment placeholder without exposing the solution path.
- `input/payloads/answer_template.json`: solver-visible output contract with required fields, enum values, precision, and list semantics.
- Shared clinic environment: source of the case record, pediatric head-injury protocol, GCS/neuro observation records, symptoms, and patient identifier.
- `output/answer.json`: hidden standard answer used for train examples and evaluator validation.
- `eval/eval.py` and `eval/eval.sh`: deterministic whole-point evaluator for the seven rubric checks.

### Solution and Evaluation Basis

The standard answer classifies `CASE-HEAD-207` as `mild_traumatic_brain_injury_without_loss_of_consciousness` for patient `PAT-2207`. Risk tier is `intermediate`; disposition is `home_observation_with_followup`; imaging recommendation is `no_immediate_ct`. Present red flags are `head_impact`, `mild_nausea`, and `coordination_symptom_observe`. Absent red flags are `loss_of_consciousness`, `repeated_vomiting`, `seizure`, and `focal_weakness`. Restrictions are `no_driving_until_symptom_free`, `no_high_risk_sports_until_cleared`, `relative_cognitive_physical_rest`, and `return_to_learn_accommodations`. Follow-up is within 48 hours through `primary_care_or_concussion_recheck`.

Rubric checks use raw weights `[3, 3, 2, 2, 2, 2, 1]`:

| Point | Weight | Whole-point check |
| --- | --- | --- |
| SP001 | 3 | Correct mild TBI classification and no unsupported loss of consciousness or vomiting safety flags. |
| SP002 | 3 | Correct `intermediate` risk tier. |
| SP003 | 2 | Correct home observation disposition and no-immediate-CT imaging recommendation. |
| SP004 | 2 | Correct present and absent protocol red-flag sets. |
| SP005 | 2 | Correct activity, return-to-play, school, and driving restrictions. |
| SP006 | 2 | Correct 48-hour follow-up window and route. |
| SP007 | 1 | Correct evidence IDs and remaining contradiction-avoidance safety flag. |

Likely model pitfalls include inventing loss of consciousness, escalating to ED/CT from a mild/intermediate case, omitting the coordination observation flag, treating the case as normal activity, or returning free text instead of controlled enum values.

### Transfer Design

As a train task, this example exposes transferable conventions for the pediatric head-injury family without serving as a tutorial. A solver comparing attempts to the standard answer can infer that protocol risk tiers come from symptom and neuro details, absent findings are explicit structured outputs, home observation can be paired with no immediate CT when high-risk features are absent, and restrictions must cover cognitive/physical rest, return-to-learn, sports clearance, and driving constraints. It also reinforces the broader task-group convention that environment records and observation IDs are evidence sources and that unsupported clinical claims should be represented by boolean safety checks.

### Construction Record

Author: task-builder worker for `task_group_016 train_002`.

Created: 2026-07-17.

Updated: 2026-07-17.

Major changes: created the formal task folder for `train_002`, including solver prompt, output template, standard answer, bilingual notes, and deterministic evaluator.

## 中文

### 数据与来源脉络

本任务属于 `task_group_016`，场景为 `SCN_016_healthcare_clinical_protocol_decision_support`，来源示例为 `E001` 到 `E005`。直接设计锚点是来源示例 `E001` 中的儿童头部外伤流程，并被改写为合成诊所环境中的病例。目标病例是患者 `PAT-2207` 的 `CASE-HEAD-207`。

求解器可见材料仅包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。临床事实、协议片段、就诊细节、观察记录和患者标识需要从 `<TASK_ENV_BASE_URL>` 对应的共享只读合成诊所运行环境中取得。

### 任务定义与场景契合

求解器需要为一个儿童头部外伤病例生成结构化临床决策支持结果。任务要求把病例细节、神经系统观察、症状经过和诊所协议整合到受控 JSON 输出中。它符合本场景，因为它模拟了协议约束下的临床办公流程：事实分散在多个记录中，风险分层逻辑很重要，最终输出还必须避免没有证据支持的发现。

预期输出包括头部外伤评估、风险层级、处置、CT 或影像建议、存在和不存在的红旗、活动和学校限制、随访时间、证据标识符以及安全检查布尔值。

### 材料映射

- `input/prompt.txt`：面向求解器的 `CASE-HEAD-207` 业务请求，包含病例编号和环境占位符，但不暴露解题路径。
- `input/payloads/answer_template.json`：面向求解器的输出契约，定义必需字段、枚举值、精度和列表语义。
- 共享诊所环境：提供病例记录、儿童头部外伤协议、GCS 和神经系统观察记录、症状以及患者标识。
- `output/answer.json`：隐藏标准答案，用于训练样例和评估器验证。
- `eval/eval.py` 与 `eval/eval.sh`：针对七个评分点的确定性整点评估器。

### 解答与评估依据

标准答案将 `CASE-HEAD-207` 归类为 `mild_traumatic_brain_injury_without_loss_of_consciousness`，患者为 `PAT-2207`。风险层级为 `intermediate`，处置为 `home_observation_with_followup`，影像建议为 `no_immediate_ct`。存在的红旗是 `head_impact`、`mild_nausea` 和 `coordination_symptom_observe`。不存在的红旗是 `loss_of_consciousness`、`repeated_vomiting`、`seizure` 和 `focal_weakness`。限制包括 `no_driving_until_symptom_free`、`no_high_risk_sports_until_cleared`、`relative_cognitive_physical_rest` 和 `return_to_learn_accommodations`。随访要求为 48 小时内通过 `primary_care_or_concussion_recheck` 复查。

评分原始权重为 `[3, 3, 2, 2, 2, 2, 1]`：

| 评分点 | 权重 | 整点检查 |
| --- | --- | --- |
| SP001 | 3 | 轻度创伤性脑损伤分类正确，并且没有无证据的意识丧失或呕吐安全标志。 |
| SP002 | 3 | `intermediate` 风险层级正确。 |
| SP003 | 2 | 居家观察处置和无需立即 CT 的影像建议正确。 |
| SP004 | 2 | 协议中的存在和不存在红旗集合正确。 |
| SP005 | 2 | 活动、返赛、学校和驾驶限制正确。 |
| SP006 | 2 | 48 小时随访窗口和随访路径正确。 |
| SP007 | 1 | 证据 ID 和剩余矛盾避免安全标志正确。 |

常见模型错误包括编造意识丧失、把轻中度病例升级为急诊或 CT、遗漏协调症状观察标志、允许正常活动，或用自由文本替代受控枚举值。

### 迁移设计

作为训练任务，本例暴露儿童头部外伤任务族的可迁移约定，但不是教程。通过比较尝试答案和标准答案，求解器可以推断：协议风险层级来自症状和神经系统细节；缺失发现需要用结构化字段表达；在无高危特征时，居家观察可以与无需立即 CT 同时成立；限制需要覆盖认知和体力休息、返校安排、运动清除以及驾驶限制。本任务也强化了任务组的通用约定：环境记录和观察 ID 是证据来源，缺乏证据支持的临床断言应通过布尔安全检查体现。

### 构建记录

作者：`task_group_016 train_002` 的 task-builder worker。

创建日期：2026-07-17。

更新日期：2026-07-17。

主要变更：创建 `train_002` 的正式任务文件夹，包括求解器提示、输出模板、标准答案、双语说明和确定性评估器。
