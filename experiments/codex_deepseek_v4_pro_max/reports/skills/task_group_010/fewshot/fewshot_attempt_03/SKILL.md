 # Asteria Investment Office — Institutional Portfolio Workflows

 ## Overview

 This skill covers the shared Asteria Investment Office simulation environment, its REST API, data models, and the template-driven JSON workflow used across credit desks, CIO allocation reviews, correlation analysis, risk rebalance exercises, and multi-asset committee outputs.

 The environment exposes current portfolio, instrument, index, issuer, macro-signal, and policy records as the official book of record. Local task payloads provide intake context that may contain stale marks or preferences; the environment always takes precedence unless the task explicitly instructs otherwise.

 ## Environment Access

 - **Base URL**: `http://task-env:9010/`
 - **Method**: HTTP GET for all endpoints (no POST/PUT/DELETE)
 - **Authentication**: None
 - **Placeholders**: Endpoints with `{name}` in the path must have the placeholder replaced with the relevant identifier from the task input or from an allowed catalog/list endpoint.

 ### Endpoint Catalog

 | Endpoint | Purpose |
 |---|---|
 | `GET /` | Health check / root |
 | `GET /api/portfolios` | List all portfolios |
 | `GET /api/portfolios/{portfolio_id}/holdings` | Current holdings for a portfolio |
 | `GET /api/instruments/bonds` | Bond instrument master |
 | `GET /api/issuers` | Issuer reference data (ratings, watchlist status, sector) |
 | `GET /api/market/energy` | Energy market data |
 | `GET /api/indices` | Index metadata (names, asset classes, regions) |
 | `GET /api/index-levels` | All monthly index levels |
 | `GET /api/index-levels/{index_id}` | Monthly levels for a specific index |
 | `GET /api/allocation/opportunity-sets` | Active allocation opportunity-set taxonomy |
 | `GET /api/allocation/prior-views` | Prior-quarter allocation views per opportunity set |
 | `GET /api/macro-signals` | Current macro signal scores |
 | `GET /api/policies` | Policy records (CIO duration ranges, HY caps, thresholds) |

 All responses are JSON. Date strings use `YYYY-MM-DD` format. Monetary values are in USD unless noted.

 ## General Workflow

 Every task follows the same six-step pattern:

 1. **Read the task prompt** (`prompt.txt`) — establishes the desk role, portfolio id, high-level objective, and output expectations.
 2. **Read the local payload(s)** — JSON files in `input/payloads/` providing task-specific constraints, preferences, review windows, stale snapshots, or committee memos.
 3. **Read the answer template** (`answer_template.json`) — declares the exact output shape: required keys, allowed values, numeric precision, sort orders, and list lengths.
 4. **Query the environment** — call the relevant endpoints from the catalog above to retrieve current records. Always prefer environment data over stale payload values.
 5. **Process and cross-reference** — apply computations (correlations, weighted metrics, constraint checks), map payload instructions to environment data, and resolve any conflicts with the data-precedence rule.
 6. **Fill the template and return** — produce the JSON object matching the template exactly. Output only the JSON object unless the prompt explicitly allows narrative.

 ### Required Shell Tooling

 The environment is accessed exclusively through HTTP GET calls. Use `curl -s` for every API call:

 ```bash
 curl -s "http://task-env:9010/api/portfolios"
 curl -s "http://task-env:9010/api/portfolios/PF-EN-ALTA/holdings"
 curl -s "http://task-env:9010/api/instruments/bonds"
 curl -s "http://task-env:9010/api/issuers"
 curl -s "http://task-env:9010/api/market/energy"
 curl -s "http://task-env:9010/api/indices"
 curl -s "http://task-env:9010/api/index-levels"
 curl -s "http://task-env:9010/api/index-levels/IDX_EM"
 curl -s "http://task-env:9010/api/allocation/opportunity-sets"
 curl -s "http://task-env:9010/api/allocation/prior-views"
 curl -s "http://task-env:9010/api/macro-signals"
 curl -s "http://task-env:9010/api/policies"
 ```

 Pipe through `python3 -m json.tool` or `jq` for readability when inspecting, and use `python3 -c` for arithmetic and data processing.

 ## Data Models

 ### Portfolio

 A portfolio object has at minimum:
- `portfolio_id` (string): e.g. `PF-EN-ALTA`, `PF-INT-NEXVEN`, `PF-FI-LUMEN`, `PF-MA-HELIO`
- `name` (string): descriptive name
- `as_of_date` (string): `YYYY-MM-DD` date of the current snapshot

 The holdings endpoint returns a list of positions, each with:
- `instrument_id` (string)
- `market_value_usd` (number): current mark-to-market in USD
- `quantity` (number): par or units held
- Additional fields depending on asset class (duration, YTW, rating, sector for bonds; weight for equities).

 ### Bond Instrument

 Returned by `/api/instruments/bonds`. Each bond has:
- `instrument_id` (string): e.g. `BND_BLUEGAS_2030`
- `issuer_id` (string)
- `coupon` (number): annual coupon rate
- `maturity_date` (string): `YYYY-MM-DD`
- `rating` (string): credit rating (e.g. `AA`, `A`, `BBB`, `BB`, `B`)
- `sector` (string): industry sector
- `subsector` (string): finer industry classification (e.g. `LNG`, `Pipeline`, `Chemicals`, `Telecom`, `Data_Center`, `Metals_Mining`)
- `ytw` (number): yield-to-worst as decimal (e.g. 0.062 for 6.2%)
- `modified_duration` (number): modified duration in years
- `is_high_yield` (boolean): true if rating is BB+ or below
- `in_watchlist` (boolean): true if the issuer is on the credit watchlist

 ### Issuer

 Returned by `/api/issuers`. Each issuer has:
- `issuer_id` (string)
- `issuer_name` (string)
- `rating` (string): issuer-level credit rating
- `sector` (string)
- `subsector` (string)
- `in_watchlist` (boolean)
- `country` (string): domicile country

 ### Index

 Returned by `/api/indices`. Each index has:
- `index_id` (string): e.g. `IDX_EM`, `IDX_CHINA`, `IDX_WORLD`
- `index_name` (string): descriptive name
- `asset_class` (string): e.g. `Equities`
- `region` (string): e.g. `Global`, `Emerging`, `Developed`, `Asia_Pacific`, `Latin_America`

 Common index universe (all prefixed `IDX_`):
 `ACWI_IMI`, `AC_ASIA_PAC_EX_JP`, `CHINA`, `EAFE`, `EM`, `EM_EX_CHINA`, `INDIA`, `LATAM`, `WORLD`

 ### Index Levels

 Returned by `/api/index-levels` and `/api/index-levels/{index_id}`. Each entry has:
- `index_id` (string)
- `level_date` (string): `YYYY-MM-DD` (month-end dates)
- `level_value` (number): index level at close

 ### Opportunity Sets

 Returned by `/api/allocation/opportunity-sets`. Each entry has:
- `opportunity_set` (string): e.g. `Europe`, `Japan`, `Emerging Markets`, `India`, `Latin America`, `U.S. Treasuries`, `Corporate High Yield`, `USD`, `EUR`
- `asset_class` (string): `Equities`, `Duration`, `Credit`, or `Currency`

 ### Prior Views

 Returned by `/api/allocation/prior-views`. Each entry maps an opportunity set to its prior-quarter view (`UW`, `N`, or `OW`).

 ### Macro Signals

 Returned by `/api/macro-signals`. Each entry has:
- `opportunity_set` (string)
- `signal_score` (number): a composite macro signal, typically in range [-1, 1]
- `signal_date` (string): `YYYY-MM-DD`

 ### Policies

 Returned by `/api/policies`. Contains:
- `policy_id` (string): e.g. `POLICY_SET_2026_05`
- CIO duration range (min/max years)
- HY allocation cap (percentage)
- Correlation concentration thresholds
- Other portfolio-level risk limits

 ## Common Computations

 ### Pearson Correlation from Monthly Levels

 For index correlation reviews:

 1. Collect monthly-end level values for each index across the review window.
 2. Compute monthly simple returns: `r_t = (level_t / level_{t-1}) - 1`
 3. The return-observation count is one fewer than the level count (`N_levels - 1`).
 4. Compute Pearson r between each pair's return series using standard formula:
    `r = Σ[(x_i - x̄)(y_i - ȳ)] / sqrt[Σ(x_i - x̄)² · Σ(y_i - ȳ)²]`
 5. Round to three decimal places.

 Use Python for computation:
 ```python
 import json, math, statistics
 # levels = {idx_id: [v1, v2, ...]}  sorted by date
 def returns(levels):
     return [(levels[i]/levels[i-1]) - 1.0 for i in range(1, len(levels))]
 def pearson(xs, ys):
     n = len(xs)
     mx, my = statistics.mean(xs), statistics.mean(ys)
     num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
     den = math.sqrt(sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys))
     return round(num/den, 3) if den != 0 else 0.0
 ```

 ### Weighted Portfolio Metrics (Bond Portfolios)

 For portfolios with bond holdings:

- **Total market value** = sum of all `market_value_usd` across holdings, plus any new trade notional.
  Round to precision 1 or 2 as specified by the template.

- **HY allocation %** = (sum of `market_value_usd` for holdings where `is_high_yield == true`) / `total_market_value` × 100.
  Round to precision 2.

- **Weighted modified duration** = Σ(holding.market_value_usd × holding.modified_duration) / total_market_value.
  Round to precision 2.

- **Weighted YTW %** = Σ(holding.market_value_usd × holding.ytw) / total_market_value × 100.
  Round to precision 2.

 Post-trade metrics incorporate the proposed trades:
- **BUY**: add the trade notional to market value; use the bond's instrument data for duration, YTW, and HY classification.
- **SELL**: subtract the trade quantity from market value and remove the sold instrument's contribution.

 ### HY Reduction (Percentage Points)

 `hy_reduction_pct_points = pre_trade_hy_pct - post_trade_hy_pct`
 (A positive number indicates HY was reduced.)

 ### Watchlist Exposure

 `post_trade_watchlist_exposure_usd_m` = sum of market values (in USD millions) of holdings whose instruments have `in_watchlist == true` after proposed trades.

 ## Template Conventions

 ### Answer Template Structure

 Every `answer_template.json` follows this pattern:
- `description` / `type`: metadata
- `required` / `required_top_level_keys`: top-level keys that must be present
- `properties` / `fields`: per-field constraints
  - `type`: `string`, `number`, `boolean`, `object`, `list`, `enum`
  - `required_value`: the exact value this field must take
  - `precision`: number of decimal places (e.g. 1, 2, 3)
  - `allowed_values`: the closed set of acceptable strings
  - `format`: date format or other constraint hint
  - `ordering` / `item_order`: how list items must be sorted or ordered
  - `length`: exact number of items in a list (when specified)

 ### Data Precedence

 The environment service is the system of record. Local payloads may contain stale snapshots or desk preferences from prior worksheets. When the environment and a local payload conflict:

- **Default rule**: current environment data overrides stale payload data.
- When filling the `data_precedence` field in templates that include it, use `"current_environment_over_stale_payload"` unless the prompt explicitly instructs otherwise.
- If the payload's data is fully consistent with the environment, use `"no_conflict_found"`.

 ### Sort Ordering Conventions

 Templates specify ordering rules. The standard conventions are:

- **Alphabetical ascending**: sort string lists by their natural string order (e.g. index IDs, instrument IDs).
- **Alphabetical within pair**: for two-element `pair_id` lists, sort the two IDs alphabetically so the smaller ID comes first.
- **SELL before BUY**: in trade lists with mixed actions, SELL entries precede BUY entries; within each action group, sort by `instrument_id` ascending.
- **Payload order**: when a template says "Sort rows by the request payload's focus_opportunity_sets order", preserve the order from the request payload array.
- **Business priority**: when specified, highest business priority first (not alphabetical).

 ### Numeric Precision

 Always match the `precision` declared in the template:
- Precision 1: `4.0`, `12.0`, `0.0`
- Precision 2: `13.24`, `3.28`, `5.80`
- Precision 3: `0.974`, `-0.825`, `0.915`

 Use Python `round(value, n)` to round. For precision 1 or 2 display, ensure trailing zeros are preserved in JSON (Python's `round` naturally handles this: `round(4.0, 1)` → `4.0`).

 ## Enum Value Catalogs

 ### Action Types

 Used in trade packages and sleeve actions:

 | Enum | Applies To |
 |---|---|
 | `BUY`, `SELL`, `HOLD`, `NO_TRADE` | Bond trade actions |
 | `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate` | Sleeve/opportunity-set actions |

 ### Allocation Views

 **View**: `UW` (Underweight), `N` (Neutral), `OW` (Overweight)

 **Change**: `UP` (increased weight vs prior), `DOWN` (decreased weight vs prior), `UNCHANGED`

 **Conviction**: `LOW`, `MEDIUM`, `HIGH`

 ### Rationale Codes

 | Code | Meaning |
 |---|---|
 | `GROWTH_IMPROVES` | Growth outlook is improving |
 | `RATE_CUT_SUPPORT` | Rate cuts provide tailwind |
 | `CREDIT_SPREAD_RISK` | Credit spreads pose tightening/widening risk |
 | `DOLLAR_DEFENSIVE` | USD strength as defensive posture |
 | `CHINA_DEPENDENCE` | Exposure tied to China beta |
 | `LATAM_DIVERSIFIER` | Latin America as low-correlation diversifier |
 | `INDIA_OFFSET` | India as EM offset / domestic growth story |
 | `DURATION_SUPPORT` | Duration exposure provides portfolio ballast |
 | `HY_VALUATION_RISK` | High-yield valuations are stretched |
 | `EUROPE_RECOVERY` | European cyclical recovery theme |
 | `JAPAN_POLICY_RISK` | Japan policy normalization risk |
 | `NEUTRAL_BALANCE` | Return to neutral for portfolio balance |

 ### Sales Positioning

 **Target Segment**: `insurance_general_account`, `pension_liability_matching`, `multi_asset_income`, `private_bank_income`, `endowment_opportunistic`

 **Theme**: `lng_export_tailwind`, `oil_oversupply_caution`, `midstream_stability`, `transition_bond_selectivity`, `avoid_watchlist_yield_trap`

 ### Risk Overlay Codes

 | Code | Primary Action |
 |---|---|
 | `DURATION_QUALITY_TILT` | `tilt_to_duration_quality` |
 | `CREDIT_RISK_REDUCTION` | `trim_credit_beta` |
 | `EQUITY_BETA_EXTENSION` | `add_cyclical_equity_beta` |
 | `CURRENCY_DEFENSIVE_HEDGE` | `add_currency_hedge` |
 | `NO_OVERLAY` | `hold_policy_weights` |

 ### Concentration Codes

 `CHINA_ASIA_DEPENDENCE`, `GLOBAL_DEVELOPED_OVERLAP`, `NO_MATERIAL_CONCENTRATION`

 ### Risk Note Codes

 `hy_cap_pressure`, `watchlist_concentration`, `duration_preservation`, `carry_tradeoff`, `no_action`

 ### Rebalance Triggers

 `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`

 ### Next Step

 `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`

 ### Data Precedence

 `current_environment_over_stale_payload`, `local_payload_over_current_environment`, `no_conflict_found`

 ## Task-Type Quick Reference

 ### Energy Credit Desk (Trade Strategy)

 **Typical endpoints:** `/api/portfolios/{id}/holdings`, `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`
 **Key outputs:** `trade_package`, `post_trade_metrics`, `constraint_checks`, `sales_positioning`
 **Key checks:** HY cap, duration band, issuer diversification, subsector diversification, watchlist avoidance
 **Trade actions:** Usually `BUY` only (new funding); size and split specified by payload

 ### Equity Correlation Review

 **Typical endpoints:** `/api/indices`, `/api/index-levels` (per-index or all)
 **Key outputs:** `review_window`, `index_set`, `extreme_pairs`, `concentration`, `diversification_candidates`, `sleeve_actions`
 **Key computation:** Pearson r on monthly simple returns over the review window
 **Key conventions:** Pair IDs alphabetically sorted, correlations rounded to 3 decimals

 ### CIO Allocation View Refresh

 **Typical endpoints:** `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`
 **Key outputs:** `allocation_views` (per opportunity set), `risk_overlay`
 **View derivation:** Combine prior views, macro signal scores, and policy context to determine UW/N/OW, change direction, conviction, and rationale
 **Ordering:** Preserve the payload's focus_opportunity_sets order

 ### Fixed-Income Risk Rebalance

 **Typical endpoints:** `/api/portfolios/{id}/holdings`, `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`, `/api/policies`
 **Key outputs:** `rotation.trades` (SELL + BUY), `risk_metrics`, `exception_flags`, `watchlist_handling`
 **Key checks:** HY cap, duration band, HY reduction target, watchlist clearance
 **Trade ordering:** SELL before BUY; alphabetical within each action

 ### Multi-Asset Committee (Correlation + Allocation)

 **Typical endpoints:** `/api/portfolios/{id}/holdings`, `/api/indices`, `/api/index-levels`, `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`
 **Key outputs:** `correlation_summary`, `target_sleeve_actions`, `allocation_views`, `rebalance_trigger`
 **Combines:** Correlation review (concentration + diversifier pairs) with allocation view refresh, then derives sleeve actions and rebalance trigger

 ## Common Pitfalls

 1. **Using stale payload data**: Always query the environment for current marks. The payload may contain a snapshot from an earlier date. Cross-check and override.
 2. **Wrong sort order**: Templates are explicit about ordering (alphabetical, SELL-before-BUY, payload order, business priority). Violating sort order produces an incorrect answer.
 3. **Precision mismatch**: Rounding to 2 decimals when the template says precision 1, or failing to include trailing zeros. Use Python's `round()` and verify.
 4. **Missing required keys**: The answer template's `required` / `required_top_level_keys` list is authoritative. Every listed key must be present.
 5. **Enum violations**: When a field has `allowed_values`, only those exact strings are valid. Do not invent new codes or use freeform text.
 6. **Pair ordering**: When a template says pair IDs must be sorted alphabetically, always put the lexicographically smaller ID first.
 7. **Return observations miscount**: The return-observation count for a correlation window is `N_levels - 1`, not `N_levels`. If the window spans 12 month-ends, you have 11 return observations.
 8. **Including narrative**: Output only the JSON object unless the prompt explicitly permits commentary. No markdown fences, no preamble, no trailing text.
