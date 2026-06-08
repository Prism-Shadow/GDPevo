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

