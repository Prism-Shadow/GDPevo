# train_005 Notes

## English

Data/source lineage: This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, using source examples `E001`, `E002`, and `E003` as the scenario basis. The task follows the builder brief for `train_005`: committee JSON for `PF-MA-HELIO` linking international equity correlations with active allocation views. The standard answer is computed from the shared Asteria environment under `task_group/task_group_010_institutional_portfolio_risk/env/`, specifically `data/portfolios.json`, `data/index_levels.json`, `data/policies.json`, `data/prior_views.json`, and `data/macro_signals.json`. The only task-local business payload is `input/payloads/committee_request.json`, which names the target portfolio, quarter, relevant index ids, and opportunity sets.

Task definition: The solver must prepare a compact committee-ready JSON for `PF-MA-HELIO` as of `2026-05-29`, for `Q2_2026`. The visible request asks for two correlation findings across the portfolio's relevant non-US equity indices, target sleeve actions, allocation rows for Emerging Markets, India, Latin America, and USD, a rebalance trigger, a concentration flag, and a next-step enum. The output must conform to `input/payloads/answer_template.json`.

Scenario fit: This task combines two recurring operation families from the group: international equity correlation review and cross-asset active allocation view updates. It mirrors the source examples' need to turn market data, portfolio context, and active views into normalized committee decisions. It also reinforces the shared convention that current environment records override stale local notes.

Material map: `committee_request.json` identifies `PF-MA-HELIO`, the `Q2_2026` review quarter, the equity indices `IDX_EM`, `IDX_CHINA`, `IDX_INDIA`, and `IDX_LATAM`, and the four allocation opportunity sets. `portfolios.json` provides the current portfolio date and holdings. `index_levels.json` provides monthly levels from `2025-05-30` through `2026-04-30`; monthly simple returns from consecutive levels are used for Pearson correlations. `policies.json` provides the correlation high threshold of `0.80` and the allocation mapping thresholds. `prior_views.json` provides prior Q2 view rows relative to Q1. `macro_signals.json` provides current Q2 scores and rationale codes.

Solution and evaluation basis: Among the four equity indices in the packet, the highest concentration pair is sorted pair `["IDX_CHINA", "IDX_EM"]` with correlation `0.915`; the strongest diversifier pair is sorted pair `["IDX_CHINA", "IDX_LATAM"]` with correlation `-0.825`. Because the high pair exceeds the `0.80` threshold, `portfolio_risk_concentration_flag` is `true` and `rebalance_trigger` is `correlation_cap_breach`. Allocation rows are derived from Q2 macro scores and Q2 prior-view records: Emerging Markets score `-0.373` maps to `UW`, `DOWN`, `MEDIUM`, `CHINA_DEPENDENCE`; India score `0.732` maps to `OW`, `UNCHANGED`, `HIGH`, `INDIA_OFFSET`; Latin America score `0.480` maps to `OW`, `UP`, `MEDIUM`, `LATAM_DIVERSIFIER`; USD score `-0.218` maps to `N`, `DOWN`, `LOW`, `NEUTRAL_BALANCE`. Target actions are `trim` Emerging Markets, `add` India, `add` Latin America, and `hedge` USD. The next step is `approve_with_monitoring`.

Scoring goals use six exact-match points: SP001 correlation pair roles, sorted pair ids, and rounded correlations, raw weight 3; SP002 target sleeve actions, raw weight 3; SP003 allocation view rows, raw weight 2; SP004 rebalance trigger, raw weight 2; SP005 concentration flag, raw weight 2; SP006 next-step enum, raw weight 1. Numeric fields are normalized to three decimals in the evaluator. Likely pitfalls include using stale local notes, using levels directly rather than monthly returns, failing to sort pair ids, computing correlations over the wrong index set, treating prior views as final views, or using prose instead of controlled enums.

Transfer design: As a train task, this gives solvers experience with the same correlation convention used elsewhere in the group, including monthly simple returns, Pearson correlation, three-decimal rounding, sorted pair ids, and threshold-driven concentration flags. It also reinforces allocation-view mapping from macro scores, prior-view lineage, change direction, conviction tiers, and controlled rationale codes. These habits transfer to later multi-asset and international equity test tasks without making this task a tutorial.

Construction record: Author `task-builder 5`; created `2026-06-03`; updated `2026-06-03`. Major change: created the full `train_005` task package with visible prompt and payloads, hidden bilingual notes, standard answer, and exact-match evaluator.

## Chinese

数据来源：本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，以源示例 `E001`、`E002`、`E003` 为场景基础。任务遵循 `train_005` 的构建简报：为 `PF-MA-HELIO` 生成委员会 JSON，把国际股票相关性结果与主动配置观点相连接。标准答案来自共享 Asteria 环境，主要使用 `data/portfolios.json`、`data/index_levels.json`、`data/policies.json`、`data/prior_views.json` 和 `data/macro_signals.json`。本任务唯一的本地业务载荷是 `input/payloads/committee_request.json`，其中给出目标组合、季度、相关指数和机会集合。

任务定义：求解者需要为 `PF-MA-HELIO` 准备截至 `2026-05-29`、针对 `Q2_2026` 的紧凑委员会 JSON。可见请求要求输出两项相关性发现、目标袖套操作、Emerging Markets、India、Latin America 和 USD 的配置观点行、再平衡触发项、集中风险标志和下一步枚举。输出必须符合 `input/payloads/answer_template.json`。

场景契合：该任务结合了任务组中的两个重复操作族：国际股票相关性审查和跨资产主动配置观点更新。它对应源示例中把市场数据、组合背景和主动观点转化为标准化委员会决策的工作方式，同时强化当前环境记录优先于过期本地备注的约定。

材料地图：`committee_request.json` 标识 `PF-MA-HELIO`、`Q2_2026`、指数 `IDX_EM`、`IDX_CHINA`、`IDX_INDIA`、`IDX_LATAM`，以及四个配置机会集合。`portfolios.json` 提供当前组合日期和持仓。`index_levels.json` 提供从 `2025-05-30` 到 `2026-04-30` 的月度指数点位；解答使用相邻点位计算月度简单收益，再计算 Pearson 相关性。`policies.json` 提供 `0.80` 的高相关阈值和配置映射阈值。`prior_views.json` 提供 Q2 相对于 Q1 的既有观点记录。`macro_signals.json` 提供 Q2 当前分数和理由代码。

解答与评估依据：在可见包列出的四个股票指数中，最高集中风险组合为排序后的 `["IDX_CHINA", "IDX_EM"]`，相关系数为 `0.915`；最强分散化组合为排序后的 `["IDX_CHINA", "IDX_LATAM"]`，相关系数为 `-0.825`。高相关组合超过 `0.80` 阈值，因此 `portfolio_risk_concentration_flag` 为 `true`，`rebalance_trigger` 为 `correlation_cap_breach`。配置观点由 Q2 宏观分数和 Q2 既有观点记录推出：Emerging Markets 分数 `-0.373` 映射为 `UW`、`DOWN`、`MEDIUM`、`CHINA_DEPENDENCE`；India 分数 `0.732` 映射为 `OW`、`UNCHANGED`、`HIGH`、`INDIA_OFFSET`；Latin America 分数 `0.480` 映射为 `OW`、`UP`、`MEDIUM`、`LATAM_DIVERSIFIER`；USD 分数 `-0.218` 映射为 `N`、`DOWN`、`LOW`、`NEUTRAL_BALANCE`。目标操作为削减 Emerging Markets、增加 India、增加 Latin America、对 USD 做 hedge。下一步为 `approve_with_monitoring`。

评分目标为六个精确匹配点：SP001 相关性角色、排序后的指数对和四舍五入相关系数，原始权重 3；SP002 目标袖套操作，原始权重 3；SP003 配置观点行，原始权重 2；SP004 再平衡触发项，原始权重 2；SP005 集中风险标志，原始权重 2；SP006 下一步枚举，原始权重 1。评估器会把数值字段规范到三位小数。常见错误包括使用过期本地备注、直接对指数点位而不是月度收益计算相关性、未排序指数对、使用错误指数集合、把既有观点当成最终观点，或输出自由文本而非受控枚举。

迁移设计：作为训练任务，它让求解者接触任务组内复用的相关性约定，包括月度简单收益、Pearson 相关、三位小数、排序指数对和阈值驱动的集中风险标志。同时它强化宏观分数到配置观点的映射、既有观点沿袭、变化方向、信心水平和受控理由代码。这些经验会迁移到后续多资产和国际股票测试任务，但本任务本身不是教程。

构建记录：作者 `task-builder 5`；创建日期 `2026-06-03`；更新日期 `2026-06-03`。主要变更：创建完整的 `train_005` 任务包，包括可见 prompt 和 payload、隐藏双语 notes、标准答案和精确匹配评估器。
