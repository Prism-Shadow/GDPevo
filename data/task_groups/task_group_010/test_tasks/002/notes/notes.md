# PF-INT-ORION Expanded International Equity Correlation Review

## English Notes

Data lineage: this is `test_002` for `task_group_010_institutional_portfolio_risk`, derived from scenario `SCN_010_institutional_investment_strategy_portfolio_risk` and source examples `E001`, `E002`, and `E003`, with the closest source-example fit coming from `E002` international equity correlation review. The task uses the implemented shared Asteria Investment Office environment under `env/`, especially `env/data/portfolios.json`, `env/data/policies.json`, `env/data/indices.json`, and `env/data/index_levels.json`. The task-local solver-visible payload is `input/payloads/orion_review_request.json`.

Task definition: the solver must prepare a compact JSON correlation review for portfolio `PF-INT-ORION`. The visible prompt asks for the expanded 14-index universe, the 2025-05-30 through 2026-04-30 level window, Pearson correlations from consecutive monthly simple returns, three-decimal rounding, concentration flags, diversification actions, and a hedging next step. The standard answer includes 11 return observations, 91 alphabetical pair calculations, the highest positive pair `IDX_EM`/`IDX_WORLD` at `0.974`, and the lowest pair `IDX_CHINA`/`IDX_LATAM` at `-0.825`.

Scenario fit: this remains inside the institutional CIO desk workflow defined for the group. The task is a risk-review deliverable over portfolio holdings, shared policy thresholds, and market data, and it requires moving from raw index levels to normalized committee-ready decisions. It is intentionally close to `train_002` and the correlation portion of `train_005`, but uses a broader regional index set and a new portfolio.

Material map: `prompt.txt` gives the business request and output requirement. `orion_review_request.json` supplies the request id, target portfolio, review window, expanded index universe, and concern codes. `answer_template.json` fixes the JSON shape, allowed enums, ordering rules, and three-decimal precision. The shared env portfolio record gives Orion's current sleeves and high-threshold policy. The index-level fixture supplies the raw levels used for all pair calculations.

Solution and evaluation basis: the answer was computed from current env index levels, not from any stale local summary. Correlations are Pearson correlations of monthly simple returns calculated from consecutive index levels. Pair ids are alphabetical, and the pair list is sorted by pair id. The flags mark China/Asia dependence, Latin America diversification, and a high-threshold breach because multiple relevant correlations exceed the `0.80` policy threshold and Latin America is strongly negative versus China and other broad equity sleeves. The diversification actions are to trim China, rotate Emerging Markets toward EM ex China, and add Latin America. The hedging next step is `hedge_china_asia_beta`.

Evaluation has seven exact-match scoring points with raw weights: SP001 review window and index universe, weight 1; SP002 full pair correlation grid, weight 2; SP003 highest and lowest pairs, weight 3; SP004 concentration flags, weight 3; SP005 diversification action set, weight 2; SP006 hedging next-step enum, weight 2; SP007 concentration threshold boolean, weight 1. The evaluator rounds numeric values to three decimals and normalizes pair/action ordering before comparison. Likely pitfalls include using levels rather than returns, using only Orion's held indices instead of the expanded universe, reversing pair ids, skipping the full pair grid, treating Latin America as merely low rather than a positive diversifier, or choosing a generic monitor action instead of a hedge next step.

Transfer design: this test task is anchored by `train_002` for the correlation window, monthly simple-return convention, pair-id sorting, and concentration/diversification logic. It is also anchored by `train_005` for connecting correlation findings to controlled sleeve actions and an implementation next step. The task-specific difficulty comes from the expanded 14-index pair grid and the fact that the highest pair is global/EM while the committee still expects China/Asia dependence to be recognized from the broader pair pattern.

Construction record: created by task-builder 7 on 2026-06-03. Files added only under `test_tasks/002/`: prompt, payloads, standard answer, evaluator, and notes.

## 中文说明

数据来源：这是 `task_group_010_institutional_portfolio_risk` 的 `test_002`，来自场景 `SCN_010_institutional_investment_strategy_portfolio_risk` 和源示例 `E001`、`E002`、`E003`，其中与 `E002` 的国际股票相关性复核最接近。任务使用已经实现的 Asteria Investment Office 共享环境，重点使用 `env/data/portfolios.json`、`env/data/policies.json`、`env/data/indices.json` 和 `env/data/index_levels.json`。本任务本地可见材料是 `input/payloads/orion_review_request.json`。

任务定义：求解者需要为组合 `PF-INT-ORION` 准备紧凑的 JSON 相关性复核。可见提示要求使用 2025-05-30 到 2026-04-30 的指数点位窗口、14 个指数的扩展集合、连续月度简单收益率的 Pearson 相关系数、三位小数、集中度标志、分散化动作和对冲下一步。标准答案包含 11 个收益率观测、91 个按字母顺序排列的配对计算、最高正相关配对 `IDX_EM`/`IDX_WORLD` 为 `0.974`，最低配对 `IDX_CHINA`/`IDX_LATAM` 为 `-0.825`。

场景适配：该任务仍属于机构 CIO 办公室的组合风险复核流程。它要求从组合持仓、共享政策阈值和市场数据出发，把原始指数点位转化为委员会可使用的结构化决策结果。它与 `train_002` 以及 `train_005` 中的相关性部分保持近距离迁移关系，但换成了新的组合和更宽的区域指数集合。

材料地图：`prompt.txt` 给出业务请求和输出要求。`orion_review_request.json` 给出请求编号、目标组合、复核窗口、扩展指数集合和关注代码。`answer_template.json` 固定 JSON 结构、枚举、排序规则和三位小数精度。共享环境中的组合记录提供 Orion 当前股票袖珍组合和高相关阈值政策；指数点位数据提供所有配对计算的原始数据。

解法与评估依据：答案从当前共享环境的指数点位计算，而不是从任何本地摘要计算。相关系数使用连续指数点位转换出的月度简单收益率计算 Pearson 相关系数。配对内的指数编号按字母顺序排列，配对列表也按配对编号排序。由于多个相关系数超过 `0.80` 的政策阈值，且 Latin America 与 China 以及多个广泛股票袖珍组合显著负相关，答案标记 China/Asia 依赖、Latin America 分散化和高阈值突破。分散化动作为削减 China、将 Emerging Markets 轮换到 EM ex China，并增配 Latin America。对冲下一步为 `hedge_china_asia_beta`。

评估包含七个精确匹配评分点及原始权重：SP001 复核窗口和指数集合，权重 1；SP002 完整配对相关性网格，权重 2；SP003 最高和最低配对，权重 3；SP004 集中度标志，权重 3；SP005 分散化动作集合，权重 2；SP006 对冲下一步枚举，权重 2；SP007 集中度阈值布尔值，权重 1。评估器在比较前会把数字四舍五入到三位小数，并规范化配对和动作排序。常见错误包括直接对指数点位求相关、只使用 Orion 持仓指数而忽略扩展集合、配对编号顺序错误、漏掉完整配对网格、没有把 Latin America 识别为分散化来源，或把下一步写成普通监控而不是对冲。

迁移设计：本测试任务由 `train_002` 锚定，迁移内容包括相关性窗口、月度简单收益率约定、配对编号排序以及集中度/分散化判断。它也由 `train_005` 锚定，迁移内容包括把相关性发现转化为受控的袖珍组合动作和实施下一步。任务自身难点在于 14 个指数带来的 91 个配对计算，以及最高相关配对是全球/新兴市场关系，但委员会仍需要从整体相关结构中识别 China/Asia 依赖。

构建记录：由 task-builder 7 于 2026-06-03 创建。仅在 `test_tasks/002/` 下新增 prompt、payloads、标准答案、评估器和 notes。
