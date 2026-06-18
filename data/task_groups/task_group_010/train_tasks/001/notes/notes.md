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
