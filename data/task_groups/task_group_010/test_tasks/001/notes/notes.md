# test_001 Notes - PF-EN-BOREAL Energy Credit Package Selection

## English

### Data and Source Lineage

This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk` and stays in the `E001` energy fixed-income strategy family. It uses the shared Asteria environment as the current book of record: `env/data/portfolios.json`, `env/data/bonds.json`, `env/data/issuers.json`, `env/data/policies.json`, and `env/data/energy_market.json`.

The task-local payload `input/payloads/stale_trader_worksheet.json` is a stale 2026-05-08 trader worksheet. It provides realistic desk context, candidate route sketches, and stale candidate marks. It intentionally conflicts with current environment data for duration, rating, yield, and watchlist status.

### Task Definition and Material Map

The solver must prepare a committee-ready energy-credit recommendation for `PF-EN-BOREAL`, a natural-gas/LNG credit sleeve intended for a private-bank income audience. The visible prompt asks the solver to compare plausible cash-add, rotation, and defer routes, but it does not prescribe the exact final trade package or notional split.

Important materials:

- `/api/portfolios/PF-EN-BOREAL`: current USD 55.0 million portfolio with USD 12.0 million in `BND_BLUEGAS_2030`, USD 6.0 million in HY `BND_RIVER_2029`, and other IG energy/utility holdings.
- `/api/instruments/bonds`: current held and candidate bond data, including duration, yield, rating bucket, subsector, and candidate flags.
- `/api/issuers`: current watchlist and outlook data. Driftwood and Pacific Refining are watchlisted in current records.
- `/api/policies`: `POL_CREDIT_DEFAULT`, including 20.0% HY cap, 3.0-5.0 year duration band, 12.0% issuer concentration limit, and two-subsector diversification convention.
- `/api/market/energy`: positive LNG/gas signals and watchlist/refining caution.
- `stale_trader_worksheet.json`: older route sketches and stale marks that should be overridden when current records disagree.

### Solution and Evaluation Basis

The standard answer uses current environment data as of 2026-05-29. The selected route is `R_BALANCED_GAS_MIDSTREAM_ROTATION`, expressed as a balanced rotation with a modest net add:

- SELL `BND_BLUEGAS_2030`, USD 5.0 million.
- BUY `BND_EASTERN_LNG_2029`, USD 5.0 million.
- BUY `BND_GRANITE_2030`, USD 5.0 million.

This package preserves LNG/gas income through Eastern LNG, adds a midstream diversifier through Granite, and trims enough BlueGas exposure to bring the BlueGas issuer concentration to 11.67%, below the 12.0% policy limit. It keeps HY allocation at 18.33%, below the 20.0% cap, and weighted modified duration at 4.02 years, inside the 3.0-5.0 year band.

The ranked route assessment is:

1. `R_BALANCED_GAS_MIDSTREAM_ROTATION`: recommend, because it clears issuer concentration and preserves LNG income.
2. `R_LNG_ONLY_BLUEGAS_TRIM`: reject, because trimming BlueGas but staying pure LNG does not adequately solve the issuer concentration issue under the natural sizing convention.
3. `R_CASH_ADD_LNG_ONLY`: reject, because adding LNG exposure leaves the existing concentration exception unresolved.
4. `R_STALE_HIGH_CARRY_ADD`: reject, because stale marks and current watchlist data make the high-carry route unsuitable.

Current-data conflicts and rejection reasons are intentionally scored. `BND_BLUEGAS_2034` is rejected for current duration and issuer concentration risk; `BND_EASTERN_LNG_2032` is rejected for current duration and stale-mark conflict; `BND_DRIFTWOOD_2031` and `BND_PACREF_2030` are rejected as watchlist yield traps, with PacRef also off the gas/LNG theme.

Post-trade calculations:

- Total market value: USD 55.0 million - 5.0 sold + 10.0 bought = USD 60.00 million.
- Gross trade notional: USD 15.0 million.
- Net new cash: USD 5.0 million.
- HY market value: existing `BND_RIVER_2029` USD 6.0 million plus `BND_EASTERN_LNG_2029` USD 5.0 million = USD 11.0 million.
- HY allocation: 11.0 / 60.0 * 100 = 18.33%.
- Weighted modified duration: `(7*4.0 + 14*4.5 + 13*3.1 + 6*3.7 + 10*4.9 + 5*3.6 + 5*4.1) / 60 = 4.02`.
- Weighted yield to maturity: `(7*5.95 + 14*5.55 + 13*5.35 + 6*8.85 + 10*5.05 + 5*8.05 + 5*5.90) / 60 = 6.04%`.
- BlueGas issuer concentration: 7.0 / 60.0 * 100 = 11.67%.

The evaluator has 9 exact-match scoring points with raw weights `[3, 3, 3, 2, 3, 2, 2, 1, 1]`, total raw weight 20:

- `SP001`, weight 3: recommendation type, selected route, action, and primary conflict.
- `SP002`, weight 3: ranked route shortlist with decision and reason enums.
- `SP003`, weight 3: selected trade package with actions and notionals.
- `SP004`, weight 2: source-precedence decision and detailed conflict map.
- `SP005`, weight 3: candidate rejection reason map.
- `SP006`, weight 2: core post-trade size, cash, HY allocation, and duration metrics.
- `SP007`, weight 2: weighted yield, BlueGas concentration, and constraint flags.
- `SP008`, weight 1: private-bank suitability decision and monitoring trigger.
- `SP009`, weight 1: sales segment and energy theme.

Likely pitfalls are: following the stale worksheet into `BND_EASTERN_LNG_2032`, `BND_BLUEGAS_2034`, Driftwood, or PacRef; reporting only the final trade without route ranking; missing watchlist status; treating a cash add as sufficient despite the existing BlueGas concentration; or copying old field names from the previous test version.

### Transfer Design

This test remains anchored by `train_001` and `train_004`. The transferable conventions are current-environment source precedence, post-trade market-value calculations, HY cap and duration checks, issuer/watchlist handling, selected-subsector diversification, and controlled enum outputs. The rework increases difficulty by requiring a route shortlist, reason-coded candidate rejection map, and client suitability judgment. These are still normal institutional credit-desk tasks, not hidden schema traps.

Transfer-dependent scoring points are `SP001`, `SP002`, `SP004`, `SP005`, `SP007`, and `SP008`. `SP003` and `SP006` also benefit from train-derived calculation discipline but require task-specific exploration of PF-EN-BOREAL and current bond data. `SP009` is intentionally low weight.

### Construction Record

Author: task-builder 6 second rework. Created: 2026-06-03. Updated: 2026-06-03. Major changes: reworked after direct avg@2 remained 0.882353; removed prompt/payload language that strongly pointed to the exact rotation and notional pattern; added multiple route types, ranked shortlist, candidate rejection reason map, source conflict detail, client suitability, and heavier scoring on transfer-dependent business judgment.

## 中文

### 数据来源与任务脉络

本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，仍然保持在 `E001` 的能源固定收益策略工作流中。当前权威数据来自共享的 Asteria 环境，主要包括 `env/data/portfolios.json`、`env/data/bonds.json`、`env/data/issuers.json`、`env/data/policies.json` 和 `env/data/energy_market.json`。

任务本地材料 `input/payloads/stale_trader_worksheet.json` 是 2026-05-08 的过期交易员工作表。它提供真实的交易台背景、候选路线草图和过期候选债券信息，并故意与当前环境中的久期、评级、收益率和观察名单状态发生冲突。

### 任务定义与材料地图

解题者需要为 `PF-EN-BOREAL` 准备一份投资委员会可用的能源信用建议。该组合是天然气/LNG 信用袖套，面向私人银行收入型客户。可见提示要求比较现金加仓、轮换和暂缓等可行路线，但不直接规定最终交易包或名义金额拆分。

关键材料包括：

- `/api/portfolios/PF-EN-BOREAL`：当前 5500 万美元组合，其中 `BND_BLUEGAS_2030` 为 1200 万美元，HY 的 `BND_RIVER_2029` 为 600 万美元，另有 IG 能源和公用事业债券。
- `/api/instruments/bonds`：当前持仓和候选债券数据，包括久期、收益率、评级档、子行业和候选标记。
- `/api/issuers`：当前观察名单和展望数据。Driftwood 和 Pacific Refining 在当前记录中处于观察名单。
- `/api/policies`：`POL_CREDIT_DEFAULT`，包括 20.0% HY 上限、3.0-5.0 年久期区间、12.0% 发行人集中度限制，以及所选能源交易包至少覆盖两个子行业的分散化惯例。
- `/api/market/energy`：正面的 LNG/天然气信号，以及对观察名单和炼油高收益陷阱的谨慎提示。
- `stale_trader_worksheet.json`：较早的路线草图和过期估值信息；当它与当前记录冲突时应被覆盖。

### 解答与评估依据

标准答案使用 2026-05-29 的当前环境数据。被选中的路线是 `R_BALANCED_GAS_MIDSTREAM_ROTATION`，即带有适度净加仓的平衡轮换：

- 卖出 `BND_BLUEGAS_2030`，500 万美元。
- 买入 `BND_EASTERN_LNG_2029`，500 万美元。
- 买入 `BND_GRANITE_2030`，500 万美元。

该方案通过 Eastern LNG 保留 LNG/天然气收入主题，通过 Granite 加入中游分散化，并减持足够的 BlueGas，使 BlueGas 发行人集中度降至 11.67%，低于 12.0% 的政策限制。交易后 HY 比例为 18.33%，低于 20.0% 上限；加权修正久期为 4.02 年，处于 3.0-5.0 年区间内。

路线排序为：

1. `R_BALANCED_GAS_MIDSTREAM_ROTATION`：推荐，因为它既清理发行人集中度，又保留 LNG 收入主题。
2. `R_LNG_ONLY_BLUEGAS_TRIM`：拒绝，因为只减持 BlueGas 并保持纯 LNG 路线，在自然交易规模下仍不能充分解决发行人集中度问题。
3. `R_CASH_ADD_LNG_ONLY`：拒绝，因为只做 LNG 现金加仓会留下现有集中度例外。
4. `R_STALE_HIGH_CARRY_ADD`：拒绝，因为过期信息和当前观察名单使高收益路线不适合私人银行客户。

当前数据冲突和拒绝理由是评分重点。`BND_BLUEGAS_2034` 因当前久期和发行人集中度风险被拒绝；`BND_EASTERN_LNG_2032` 因当前久期和过期标记冲突被拒绝；`BND_DRIFTWOOD_2031` 和 `BND_PACREF_2030` 被视为观察名单高收益陷阱，其中 PacRef 还不符合天然气/LNG 主题。

交易后计算：

- 总市值：5500 万美元 - 卖出 500 万美元 + 买入 1000 万美元 = 6000 万美元。
- 总交易名义金额：1500 万美元。
- 净新增现金：500 万美元。
- HY 市值：现有 `BND_RIVER_2029` 600 万美元，加上 `BND_EASTERN_LNG_2029` 500 万美元，共 1100 万美元。
- HY 比例：11.0 / 60.0 * 100 = 18.33%。
- 加权修正久期：`(7*4.0 + 14*4.5 + 13*3.1 + 6*3.7 + 10*4.9 + 5*3.6 + 5*4.1) / 60 = 4.02`。
- 加权到期收益率：`(7*5.95 + 14*5.55 + 13*5.35 + 6*8.85 + 10*5.05 + 5*8.05 + 5*5.90) / 60 = 6.04%`。
- BlueGas 发行人集中度：7.0 / 60.0 * 100 = 11.67%。

评估器包含 9 个精确匹配评分点，原始权重为 `[3, 3, 3, 2, 3, 2, 2, 1, 1]`，总权重 20。评分重点包括推荐路线、路线排序、交易包、来源优先级、候选拒绝理由、交易后指标、约束标记、客户适配性和销售主题。

常见错误包括：跟随过期工作表选择 `BND_EASTERN_LNG_2032`、`BND_BLUEGAS_2034`、Driftwood 或 PacRef；只给最终交易而不做路线排序；漏掉观察名单状态；把现金加仓误认为能解决现有 BlueGas 集中度；或沿用旧版本测试的字段名。

### 迁移设计

本测试仍由 `train_001` 和 `train_004` 锚定。可迁移的惯例包括：当前环境优先于过期本地材料、按交易后市值计算 HY 比例和加权久期、检查 HY 上限与久期区间、处理发行人与观察名单、检查所选能源子行业分散化，以及使用受控枚举输出。此次重做通过路线排序、候选拒绝理由映射和客户适配性判断增加难度，但这些都是真实信用交易台业务复杂度，而不是隐藏规则或格式陷阱。

依赖迁移的评分点包括 `SP001`、`SP002`、`SP004`、`SP005`、`SP007` 和 `SP008`。`SP003` 与 `SP006` 也受益于训练任务中的计算习惯，但仍需要针对 PF-EN-BOREAL 和当前债券数据进行任务内探索。`SP009` 故意保持低权重。

### 构建记录

作者：task-builder 6 second rework。创建日期：2026-06-03。更新日期：2026-06-03。主要变化：在直接校准 avg@2 仍为 0.882353 后再次重做；删除了强烈指向确切轮换和名义金额模式的提示与材料语言；加入多种路线类型、排序短名单、候选拒绝理由映射、来源冲突细节、客户适配性，并把更多评分权重放在依赖迁移的业务判断上。
