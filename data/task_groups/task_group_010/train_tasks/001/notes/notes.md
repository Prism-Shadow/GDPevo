# train_001 Notes - Energy Credit Trade Strategy for PF-EN-ALTA

## English

### Data and source lineage

This task belongs to scenario `SCN_010_institutional_investment_strategy_portfolio_risk`, using source examples `E001`, `E002`, and `E003` as the broader institutional portfolio-risk design basis. The direct task family is anchored in `E001` energy fixed-income strategy: the solver must combine portfolio holdings, bond characteristics, issuer research, energy-market context, and portfolio constraints to produce a normalized trade recommendation.

The current data source is the shared Asteria environment under `task_group/task_group_010_institutional_portfolio_risk/env/`, especially `data/portfolios.json`, `data/bonds.json`, `data/issuers.json`, `data/policies.json`, and `data/energy_market.json`. The solver-visible local payload `input/payloads/desk_request.json` is a realistic desk intake note with a stale holding snapshot and preferences. It is intentionally not the book of record.

### Task definition and material map

The user asks for an energy-credit trade strategy for portfolio `PF-EN-ALTA`. The visible prompt requires exactly two BUY tickets totaling USD 8.0 million, split evenly. The expected answer is a JSON object matching `input/payloads/answer_template.json`, with trade tickets, post-trade metrics, constraint checks, sales positioning, and data-precedence handling.

Relevant environment materials:

- `PF-EN-ALTA` in `portfolios.json`: current USD 60.0 million portfolio, current holdings, objective, and constraint policy.
- `bonds.json`: candidate and held bond universe, including rating bucket, duration, yield, energy linkage, subsector, and theme tags.
- `issuers.json`: watchlist and credit-outlook checks for candidate issuers.
- `policies.json`: HY cap of 20.0%, duration band of 3.0-5.0 years, issuer-concentration threshold, and subsector-diversification convention.
- `energy_market.json`: positive gas/LNG signals and watchlist caution for refiners.
- `desk_request.json`: stale local request dated 2026-05-12, including the USD 8.0 million/two-ticket mandate and multi-asset income context.

### Solution basis

The standard answer is computed from current environment data as of 2026-05-29. The current PF-EN-ALTA portfolio has USD 60.0 million market value, one HY holding (`BND_EASTERN_LNG_2029`) of USD 5.0 million, and current weighted modified duration of about 3.20 years. The selected package is:

- BUY `BND_BLUEGAS_2030`, USD 4.0 million. This is current, energy-linked, IG, natural gas/LNG, duration 4.0 years, yield 5.95%, and non-watchlist.
- BUY `BND_RIVER_2029`, USD 4.0 million. This is current, energy-linked, HY, merchant power, duration 3.7 years, yield 8.85%, and non-watchlist.

The package avoids watchlisted high-yield distractors such as Driftwood and Pacific Refining, avoids long-duration candidates outside the 3.0-5.0 year band, raises expected portfolio yield from about 5.58% to 5.80%, and keeps HY allocation below the 20.0% cap. Post-trade calculations use the current portfolio plus the USD 8.0 million new allocation:

- Total post-trade market value: USD 68.00 million.
- HY market value: USD 9.00 million (`BND_EASTERN_LNG_2029` USD 5.0 million plus `BND_RIVER_2029` USD 4.0 million).
- HY allocation: 9.0 / 68.0 * 100 = 13.24%.
- Weighted modified duration: `(current duration-dollar total 192.1 + 4.0*4.0 + 4.0*3.7) / 68.0 = 3.28` years.
- Weighted yield to maturity: `(current yield-dollar total + 4.0*5.95 + 4.0*8.85) / 68.0 = 5.80%`.

Sales positioning uses `multi_asset_income` because the local request is for a multi-asset income update, and `lng_export_tailwind` because the strongest current energy signal is global LNG and the package includes BlueGas LNG exposure.

### Evaluation basis

The evaluator has six exact-match scoring points, with raw weights from the group design:

- SP001, weight 3: correct selected two BUY tickets, instrument ids, and USD 4.0 million notionals.
- SP002, weight 2: correct post-trade HY allocation percentage rounded to two decimals.
- SP003, weight 2: correct post-trade weighted modified duration rounded to two decimals.
- SP004, weight 2: correct HY cap and duration-band pass booleans.
- SP005, weight 1: correct selected-issuer, selected-subsector, and watchlist-avoidance flags.
- SP006, weight 2: correct sales target segment, theme, and source-precedence enum.

Likely model pitfalls include using the stale local snapshot instead of current environment data, selecting watchlisted high-yield bonds solely for yield, selecting long-duration LNG/oil bonds outside the duration band, treating all legacy issuer concentration as a blocker for a new two-ticket allocation, omitting the HY effect of `BND_RIVER_2029`, or choosing a free-form sales rationale instead of the required enum.

### Transfer design

As a train task, this is a real portfolio workflow rather than a tutorial. Comparing attempts to the answer should let solvers infer several reusable conventions for later tasks: current environment records override stale local desk materials; HY allocation is computed from post-trade market value; weighted duration uses market-value weights; watchlist and duration eligibility matter before headline yield; and pitch themes are represented by controlled enums rather than prose. These conventions transfer directly to later energy-credit and fixed-income test tasks.

### Construction record

Author: task-builder 1. Created: 2026-06-03. Updated: 2026-06-03. Major changes: created formal train task files, computed answer from current shared env data, and implemented six-point exact-match evaluator.

## 中文

### 数据来源与任务脉络

本任务属于场景 `SCN_010_institutional_investment_strategy_portfolio_risk`，整体设计参考来源示例 `E001`、`E002`、`E003`。本题直接对应 `E001` 的能源固定收益策略工作流：解题者需要综合投资组合持仓、债券特征、发行人研究、能源市场信号和组合约束，形成结构化的交易建议。

当前权威数据来自共享 Asteria 环境，主要包括 `data/portfolios.json`、`data/bonds.json`、`data/issuers.json`、`data/policies.json` 和 `data/energy_market.json`。求解者可见的 `input/payloads/desk_request.json` 是一份真实感较强的交易台需求记录，其中包含过期持仓快照和偏好信息，但它不是最终账簿来源。

### 任务定义与材料地图

用户要求为 `PF-EN-ALTA` 制定能源信用交易策略。可见提示要求两个买入票据，总额 800 万美元，两个票据等额分配。标准输出是符合 `input/payloads/answer_template.json` 的 JSON，包含交易票据、交易后指标、约束检查、销售定位和数据优先级处理。

关键材料用途如下：

- `portfolios.json` 中的 `PF-EN-ALTA`：当前 6000 万美元组合、持仓、目标和约束策略。
- `bonds.json`：候选债券和已有持仓的评级桶、久期、收益率、能源关联、子行业和主题标签。
- `issuers.json`：候选发行人的观察名单和信用展望。
- `policies.json`：20.0% 高收益上限、3.0-5.0 年久期区间、发行人集中度阈值和子行业分散规则。
- `energy_market.json`：天然气/LNG 的正面信号，以及对观察名单炼油发行人的谨慎态度。
- `desk_request.json`：2026-05-12 的过期本地需求记录，包括 800 万美元、两个票据和多资产收益客户背景。

### 解答依据

标准答案使用 2026-05-29 的当前环境数据计算。`PF-EN-ALTA` 当前市值为 6000 万美元，其中已有高收益持仓 `BND_EASTERN_LNG_2029` 为 500 万美元，当前加权修正久期约为 3.20 年。选定交易组合为：

- 买入 `BND_BLUEGAS_2030`，400 万美元。该债券是当前候选、能源相关、投资级、天然气/LNG 子行业，久期 4.0 年，收益率 5.95%，发行人不在观察名单。
- 买入 `BND_RIVER_2029`，400 万美元。该债券是当前候选、能源相关、高收益、商户电力子行业，久期 3.7 年，收益率 8.85%，发行人不在观察名单。

该组合避开 Driftwood 和 Pacific Refining 等观察名单高收益干扰项，也避开超过 3.0-5.0 年久期区间的长久期候选债券；组合预期收益率从约 5.58% 提高到 5.80%，同时高收益比例低于 20.0% 上限。交易后计算将当前组合加上 800 万美元新配置：

- 交易后总市值：6800 万美元。
- 高收益市值：900 万美元，即 `BND_EASTERN_LNG_2029` 的 500 万美元加 `BND_RIVER_2029` 的 400 万美元。
- 高收益比例：9.0 / 68.0 * 100 = 13.24%。
- 加权修正久期：`(当前久期金额合计 192.1 + 4.0*4.0 + 4.0*3.7) / 68.0 = 3.28` 年。
- 加权到期收益率：`(当前收益率金额合计 + 4.0*5.95 + 4.0*8.85) / 68.0 = 5.80%`。

销售定位选择 `multi_asset_income`，因为本地需求来自多资产收益更新；主题选择 `lng_export_tailwind`，因为当前最强能源信号是全球 LNG，并且组合包含 BlueGas LNG 敞口。

### 评估依据

评估器包含六个精确匹配评分点，原始权重与任务组设计一致：

- SP001，权重 3：两个买入票据、工具代码和 400 万美元名义本金正确。
- SP002，权重 2：交易后高收益比例正确，保留两位小数。
- SP003，权重 2：交易后加权修正久期正确，保留两位小数。
- SP004，权重 2：高收益上限和久期区间通过/失败布尔值正确。
- SP005，权重 1：选定发行人、选定子行业和观察名单规避标志正确。
- SP006，权重 2：销售目标客群、能源主题和数据优先级枚举值正确。

常见错误包括使用过期本地快照而不是当前环境数据，只因收益率高而选择观察名单债券，选择久期超出区间的长久期 LNG 或石油债券，把既有遗留发行人集中度误当作新两票据配置的阻断条件，遗漏 `BND_RIVER_2029` 对高收益比例的影响，或用自由文本销售理由替代受控枚举。

### 迁移设计

作为训练任务，本题是正式业务任务，不是教程。解题者通过比对答案可以归纳出后续任务会复用的规则：当前环境记录优先于过期本地材料；高收益比例基于交易后市值计算；加权久期按市值加权；观察名单和久期合规性优先于表面高收益；销售主题要用受控枚举而不是自由文本。这些经验会直接迁移到后续能源信用和固定收益测试任务。

### 构建记录

作者：task-builder 1。创建日期：2026-06-03。更新日期：2026-06-03。主要变更：创建正式训练任务文件，基于当前共享环境数据计算标准答案，并实现六点评估器。
