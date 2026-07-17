# test_003 Notes

## English

### Data and Source Lineage

This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, with source-example lineage from `E003` quarterly active allocation views and secondary scenario support from the cross-asset currency handling in `E002` and `train_005`. The task uses the shared Asteria Investment Office environment, especially `env/data/opportunity_sets.json`, `env/data/prior_views.json`, `env/data/macro_signals.json`, and `env/data/policies.json`. The solver-visible local files are `input/prompt.txt`, `input/payloads/allocation_request.json`, and `input/payloads/answer_template.json`.

The rework was requested after direct calibration scored `0.852941` avg@2, which showed that the original prompt and broad rubric made the task too easy without train-derived allocation experience.

### Task Definition and Scenario Fit

The solver acts as a CIO-desk analyst updating Q3 2026 active allocation views across equities, fixed income, and currencies for a global multi-asset reference model. The expected answer is a normalized JSON object with task lineage, fifteen active allocation rows, a USD-base currency overlay, and three controlled cross-asset judgment enums.

This task fits the group because it is an institutional allocation refresh: the solver must coordinate macro signals, opportunity-set taxonomy, prior-quarter records, controlled rationale codes, and currency-overlay decisions. It stays within the active allocation view family while mixing equity regional views, duration and credit views, and currency views.

### Material Map

`input/prompt.txt` gives the business request without listing endpoint names or a procedural source-mapping checklist. `allocation_request.json` names the target quarter, prior quarter, requested opportunity sets, currency overlay universe, and controlled enum choices for the output. `answer_template.json` defines the exact solver-visible JSON contract, including prior-view lineage, current signal scores to three decimals, rationale-code enums, overlay decisions, and cross-asset judgment choices.

In the shared environment, `opportunity_sets.json` supplies asset classes, `prior_views.json` supplies the prior-quarter lineage records for the target refresh, `macro_signals.json` supplies current Q3 scores and rationale codes, and `policies.json` supplies the as-of date, policy set id, and allocation mapping policy id.

### Solution and Evaluation Basis

The standard answer is derived from the current shared environment. For each requested opportunity set, the answer records the prior view from the Q3 refresh lineage record, the Q3 macro signal score, the final active view, the change versus the prior view, conviction, and the controlled rationale code. The Q3 final views are: U.S. Large Cap `N`, U.S. Small Cap `OW`, Europe `OW`, Japan `N`, Emerging Markets `UW`, India `OW`, Latin America `OW`, U.S. Treasuries `OW`, German Bunds `OW`, Corporate Investment Grade `OW`, Corporate High Yield `UW`, USD `UW`, EUR `OW`, JPY `UW`, and CHF `N`.

The USD-base currency overlay is `reduce_dollar_beta`: reduce USD exposure, add EUR exposure, reduce JPY exposure, and hold CHF exposure. The cross-asset judgments prefer small-cap, Europe, India, and Latin America over U.S. Large Cap and broad EM; prefer duration and investment-grade credit over high-yield beta; and express the currency bias as reducing USD, adding EUR, reducing JPY, and holding CHF.

The evaluator has nine exact-match scoring points with raw weights: task and policy lineage weight 2; prior-view and signal-score lineage weight 3; core equity view rows weight 2; diversifier equity view rows weight 2; fixed-income view rows weight 2; currency view rows weight 2; controlled rationale codes weight 3; currency overlay weight 3; cross-asset judgment enums weight 2. Row checks are keyed by `opportunity_set`, and overlay checks are keyed by `currency`, so incidental list order does not determine correctness.

Likely pitfalls include using the Q3 prior-view record as the final answer, comparing against Q1 rather than Q2 lineage, omitting current signal scores, treating rationale as free text, collapsing the currency overlay into the allocation rows only, or choosing broad equity/rates-credit stance enums from isolated view labels rather than the mixed opportunity-set pattern.

### Transfer Design

This is a test task. `train_003` anchors the allocation-view conventions: current signals drive active views, prior-quarter records drive change direction, signal magnitude controls conviction, and rationale codes remain controlled enums. `train_005` anchors currency handling inside a cross-asset committee workflow and the habit of turning mixed opportunity-set evidence into controlled action enums.

The rework increases transfer dependence by removing endpoint and workflow leakage from the prompt, requiring row-level prior-quarter lineage, adding signal-score evidence, splitting scoring across equity subgroups, fixed income, currencies, and rationale style, and adding a currency overlay plus cross-asset judgment block. A direct solver can still solve the task fairly from the shared environment, but it must reconstruct the active-allocation conventions rather than follow an explicit prompt recipe.

### Construction Record

Author: task-builder 8, reworked by calibration maintainer. Created: 2026-06-03. Updated: 2026-06-03. Major changes: reduced solver-visible procedural leakage; expanded `answer_template.json`; updated `answer.json`; replaced the evaluator with nine targeted scoring points; updated `task_group.yaml` rubric; refreshed bilingual notes.

## 中文

### 数据和来源脉络

本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，主要来源于 `E003` 的季度主动配置观点流程，并由 `E002` 以及 `train_005` 中的跨资产货币处理提供辅助场景依据。任务使用共享的 Asteria Investment Office 环境，重点数据包括 `env/data/opportunity_sets.json`、`env/data/prior_views.json`、`env/data/macro_signals.json` 和 `env/data/policies.json`。求解者可见的本地文件为 `input/prompt.txt`、`input/payloads/allocation_request.json` 和 `input/payloads/answer_template.json`。

本次返工的原因是直接校准得分达到 `0.852941` avg@2，说明原始提示和较宽的评分点让模型在没有训练迁移经验的情况下也能取得过高分数。

### 任务定义和场景契合

求解者扮演 CIO 办公桌分析师，为全球多资产参考模型更新 Q3 2026 主动配置观点，覆盖股票、固定收益和货币。预期输出是规范化 JSON，包含任务脉络、十五条主动配置行、一个以 USD 为基准的货币覆盖对象，以及三个受控的跨资产判断枚举。

该任务符合本任务组，因为它代表机构配置刷新流程：需要同时处理宏观信号、机会集分类、前一季度观点记录、受控理由代码和货币覆盖决策。任务仍然限制在主动配置视图范围内，但混合了区域股票、久期与信用、以及货币观点。

### 材料说明

`input/prompt.txt` 只描述业务请求，不再列出具体端点，也不提供分步骤的数据源映射流程。`allocation_request.json` 给出目标季度、前一季度、关注机会集、货币覆盖范围和输出枚举选择。`answer_template.json` 定义求解者可见的输出契约，包括前序观点脉络、三位小数的当前信号分数、理由代码枚举、货币覆盖决策和跨资产判断枚举。

共享环境中，`opportunity_sets.json` 提供资产类别，`prior_views.json` 提供目标刷新所需的前一季度观点脉络，`macro_signals.json` 提供 Q3 当前信号分数和理由代码，`policies.json` 提供日期、政策组编号和配置映射政策编号。

### 解答和评估依据

标准答案来自当前共享环境。每个请求的机会集都记录前序观点、Q3 宏观信号分数、最终主动观点、相对前序观点的变化方向、置信度和受控理由代码。Q3 最终观点为：U.S. Large Cap `N`，U.S. Small Cap `OW`，Europe `OW`，Japan `N`，Emerging Markets `UW`，India `OW`，Latin America `OW`，U.S. Treasuries `OW`，German Bunds `OW`，Corporate Investment Grade `OW`，Corporate High Yield `UW`，USD `UW`，EUR `OW`，JPY `UW`，CHF `N`。

以 USD 为基准的货币覆盖政策动作为 `reduce_dollar_beta`：降低 USD 暴露、增加 EUR 暴露、降低 JPY 暴露、维持 CHF 暴露。跨资产判断为：相对 U.S. Large Cap 和广义 EM，更偏好 small cap、Europe、India 和 Latin America；相对高收益 beta，更偏好久期和投资级信用；货币偏向为降低 USD、增加 EUR、降低 JPY、维持 CHF。

评估器包含九个精确匹配评分点，原始权重分别为：任务和政策脉络 2；前序观点和信号分数脉络 3；核心股票观点 2；分散化股票观点 2；固定收益观点 2；货币主动观点 2；受控理由代码 3；货币覆盖 3；跨资产判断枚举 2。配置行按 `opportunity_set` 匹配，货币覆盖按 `currency` 匹配，因此单纯列表顺序不会导致失败。

常见错误包括把 Q3 前序观点记录直接当成最终答案、错误地与 Q1 而不是 Q2 脉络比较、遗漏当前信号分数、把理由写成自由文本、只在配置行中处理货币而漏掉覆盖对象，或只看单个观点标签而没有给出混合机会集判断。

### 迁移设计

这是一个测试任务。`train_003` 锚定主动配置观点约定：当前信号决定主动观点，前一季度记录决定变化方向，信号强度决定置信度，理由必须使用受控枚举代码。`train_005` 锚定跨资产委员会工作流中的货币处理方式，以及把混合机会集证据转换为受控行动枚举的习惯。

本次返工通过移除提示中的端点和流程泄漏、要求逐行前序脉络、加入信号分数证据、按股票子组、固定收益、货币和理由风格拆分评分，并增加货币覆盖与跨资产判断模块，提升了迁移依赖。直接求解者仍然可以从共享环境公平完成任务，但必须自行重建主动配置约定，而不是照着提示中的流程配方执行。

### 构建记录

作者：task-builder 8，校准返工维护者更新。创建日期：2026-06-03。更新日期：2026-06-03。主要变化：减少求解者可见流程泄漏；扩展 `answer_template.json`；更新 `answer.json`；将评估器替换为九个更有针对性的评分点；更新 `task_group.yaml` rubric；刷新双语说明。
