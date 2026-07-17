# train_003 Notes

## English

### Data and Source Lineage

This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, using source examples `E001`, `E002`, and `E003`. The direct design anchor is `E003`, the quarterly active allocation view workflow. The task uses the implemented shared environment under `task_group/task_group_010_institutional_portfolio_risk/env/`, specifically `env/data/opportunity_sets.json`, `env/data/prior_views.json`, `env/data/macro_signals.json`, and `env/data/policies.json`. The task-local visible payload is `input/payloads/allocation_request.json`, which names the focused Q2 2026 opportunity-set subset and output fields.

### Task Definition and Scenario Fit

The solver acts as a CIO-desk analyst updating active allocation views for Q2 2026. The required output is a normalized JSON object with lineage fields, eight allocation rows, and one portfolio-level risk overlay. This fits the task group because it requires the same institutional investment strategy work as the source scenario: synthesizing current macro signals with prior allocation positioning, applying controlled portfolio-policy conventions, and producing committee-ready structured decisions instead of prose.

### Material Map

`input/prompt.txt` gives the business request and points solvers toward the relevant shared API surfaces. `input/payloads/allocation_request.json` defines the focus set: Europe, Japan, Emerging Markets, India, Latin America, U.S. Treasuries, Corporate High Yield, and EUR. `input/payloads/answer_template.json` defines the solver-visible schema, enum choices, and ordering expectations without revealing scoring weights or answers. In the shared environment, `opportunity_sets.json` supplies asset classes, `prior_views.json` supplies Q1-to-Q2 lineage records, `macro_signals.json` supplies Q2 signal scores and rationale codes, and `policies.json` supplies the as-of date and policy id.

### Solution and Evaluation Basis

The standard answer was derived from current environment records. Q2 signal scores map to views using the allocation policy, changes are measured against the Q1 prior view embedded in the `Q2_2026` prior-view records, and conviction follows the absolute signal-score bands. The resulting rows are: Europe `OW/UP/MEDIUM/EUROPE_RECOVERY`; Japan `UW/DOWN/MEDIUM/JAPAN_POLICY_RISK`; Emerging Markets `UW/DOWN/MEDIUM/CHINA_DEPENDENCE`; India `OW/UNCHANGED/HIGH/INDIA_OFFSET`; Latin America `OW/UP/MEDIUM/LATAM_DIVERSIFIER`; U.S. Treasuries `OW/UP/MEDIUM/DURATION_SUPPORT`; Corporate High Yield `UW/DOWN/MEDIUM/HY_VALUATION_RISK`; EUR `OW/UP/MEDIUM/EUROPE_RECOVERY`. The overlay is `DURATION_QUALITY_TILT` with primary action `tilt_to_duration_quality`, supported by `DURATION_SUPPORT`, `HY_VALUATION_RISK`, and `CHINA_DEPENDENCE`.

The evaluator has eight exact-match scoring points with raw weights: lineage fields weight 1; equity core views weight 3; diversifier views weight 3; rates/credit/currency views weight 3; all change directions weight 2; all convictions weight 2; all rationale codes weight 2; risk overlay weight 1. Row comparisons are keyed by `opportunity_set` so list order does not create incidental failures. Likely model pitfalls include treating `prior_views.json` as the final Q2 answer, ignoring current macro signals, using free-form rationales instead of enum codes, confusing Japan equity with Japanese government bonds, or making EUR defensive because USD was previously overweight.

### Transfer Design

As a train task, `train_003` lets solvers infer recurring allocation-view conventions for later allocation tasks: current macro signals override stale or prior positioning, prior-quarter rows establish lineage and change direction, signal magnitude controls conviction, rationale codes remain controlled enums, and cross-asset rows should be keyed by exact opportunity-set names. It is a real task rather than a worked example; the solver-visible prompt does not reveal the mapping procedure or scoring rubric, and the transfer is intended to emerge from attempting the task and comparing against this answer.

### Construction Record

Author: task-builder 3. Created: 2026-06-03. Updated: 2026-06-03. Major changes: created the full `train_tasks/003` task package, including visible inputs, bilingual notes, standard answer, and exact-match evaluator.

## 中文

### 数据与来源

本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，来源样例为 `E001`、`E002` 和 `E003`。直接设计锚点是 `E003` 的季度主动配置观点流程。任务使用已经实现的共享环境 `task_group/task_group_010_institutional_portfolio_risk/env/`，重点数据文件包括 `env/data/opportunity_sets.json`、`env/data/prior_views.json`、`env/data/macro_signals.json` 和 `env/data/policies.json`。任务本地可见载荷 `input/payloads/allocation_request.json` 只说明 Q2 2026 的关注机会集和输出字段。

### 任务定义与场景契合

求解者扮演 CIO 办公桌分析师，为 Q2 2026 更新主动配置观点。输出是标准化 JSON，包含来源字段、八条配置观点和一个组合层面的风险覆盖建议。该任务符合本任务组的机构投资策略场景，因为它需要把当前宏观信号、上一季度配置观点和组合政策约定结合起来，并形成适合投资委员会使用的结构化决策。

### 材料说明

`input/prompt.txt` 描述业务请求并提示相关共享 API。`input/payloads/allocation_request.json` 指定关注集合：Europe、Japan、Emerging Markets、India、Latin America、U.S. Treasuries、Corporate High Yield 和 EUR。`input/payloads/answer_template.json` 给出输出结构、枚举值和排序要求，但不泄露评分权重或答案。共享环境中，`opportunity_sets.json` 提供资产类别，`prior_views.json` 提供 Q1 到 Q2 的前序观点记录，`macro_signals.json` 提供 Q2 信号分数和理由代码，`policies.json` 提供日期和政策编号。

### 解答与评估依据

标准答案来自当前共享环境数据。Q2 信号分数根据配置政策映射为 `UW/N/OW`，变化方向与 `Q2_2026` 前序观点记录中的 Q1 观点比较，置信度由信号绝对值区间决定。答案行分别是：Europe `OW/UP/MEDIUM/EUROPE_RECOVERY`；Japan `UW/DOWN/MEDIUM/JAPAN_POLICY_RISK`；Emerging Markets `UW/DOWN/MEDIUM/CHINA_DEPENDENCE`；India `OW/UNCHANGED/HIGH/INDIA_OFFSET`；Latin America `OW/UP/MEDIUM/LATAM_DIVERSIFIER`；U.S. Treasuries `OW/UP/MEDIUM/DURATION_SUPPORT`；Corporate High Yield `UW/DOWN/MEDIUM/HY_VALUATION_RISK`；EUR `OW/UP/MEDIUM/EUROPE_RECOVERY`。覆盖建议是 `DURATION_QUALITY_TILT`，主要动作是 `tilt_to_duration_quality`，理由代码为 `DURATION_SUPPORT`、`HY_VALUATION_RISK` 和 `CHINA_DEPENDENCE`。

评估器包含八个精确匹配评分点，原始权重为：来源字段 1；核心股票观点 3；分散化机会观点 3；利率、信用和货币观点 3；全部变化方向 2；全部置信度 2；全部理由代码 2；风险覆盖建议 1。行比较按 `opportunity_set` 键匹配，避免因为列表顺序造成无关失败。常见错误包括把 `prior_views.json` 当作最终 Q2 答案、忽略当前宏观信号、使用自由文本理由而非枚举代码、混淆日本股票与日本政府债，或因为 USD 上季度超配而误判 EUR 防御性。

### 迁移设计

作为训练任务，`train_003` 让求解者在尝试并对照答案后推断后续配置任务会复用的约定：当前宏观信号优先于旧观点或过时材料，前序观点用于确定变化方向，信号绝对值决定置信度，理由必须使用受控枚举代码，跨资产行应按精确机会集名称匹配。这不是教程或样例题；可见提示没有透露映射流程或评分细节，迁移知识应来自真实解题和答案对比。

### 构建记录

作者：task-builder 3。创建日期：2026-06-03。更新日期：2026-06-03。主要变更：创建完整的 `train_tasks/003` 任务包，包括可见输入、双语说明、标准答案和精确匹配评估器。
