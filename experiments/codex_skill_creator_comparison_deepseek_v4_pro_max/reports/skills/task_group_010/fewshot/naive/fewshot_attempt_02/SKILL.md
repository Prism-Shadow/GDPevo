---
name: asteria-investment-office
description: Solve Asteria Investment Office institutional portfolio tasks using the shared Asteria environment API for current book-of-record data. Covers trade strategy, correlation review, allocation views, risk rebalancing, and committee decision synthesis.
---

# Asteria Investment Office

You are supporting the Asteria Investment Office — a fictional institutional investment manager. Every task follows the same core pattern: read the task prompt, read the local answer-template JSON (which defines the exact output schema), read any local request payload for context and preferences, query the shared Asteria environment API at `http://task-env:9010/` for current book-of-record data, compute or derive the required values, and produce a single JSON answer that conforms exactly to the template.

The local request payloads may contain **stale** snapshots, worksheet drafts, or earlier desk notes. Always prefer live environment data over the local payload when they conflict. Explicitly note this precedence in the answer when the template calls for it.

---

## Environment API

The Asteria environment runs at `http://task-env:9010/`. No credentials are required. Use `curl` with `-s` to suppress progress output. All endpoints return JSON.

### Available endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Confirm the service is up. |
| `GET /api/portfolios` | List all portfolios with identifiers and names. |
| `GET /api/portfolios/{portfolio_id}/holdings` | Current holdings for a portfolio, including instrument_id, market_value, quantity, weight, and classification fields. |
| `GET /api/instruments/bonds` | Bond security master: instrument_id, issuer_id, subsector, rating, watchlist status, coupon, maturity, modified_duration, yield_to_maturity, etc. |
| `GET /api/issuers` | Issuer master: issuer_id, name, domicile, credit_rating, watchlist status. |
| `GET /api/market/energy` | Energy-market data: benchmarks, spreads, forward curves relevant to energy-linked bonds. |
| `GET /api/indices` | Index metadata: index_id, name, region, asset_class. |
| `GET /api/index-levels` | Monthly index levels for all indices. |
| `GET /api/index-levels/{index_id}` | Monthly levels for a specific index. |
| `GET /api/allocation/opportunity-sets` | Taxonomy of opportunity sets with their asset classes. |
| `GET /api/allocation/prior-views` | Prior-quarter allocation views (UW/N/OW) per opportunity set. |
| `GET /api/macro-signals` | Macro signal scores per opportunity set (real numbers, positive = favorable). |
| `GET /api/policies` | Policy records including policy_id, HY caps, duration bands, and other constraints. |

### How to query

Call endpoints with `curl -s http://task-env:9010/<path>`. If the response is large, pipe through Python (`python3 -c "import sys,json; ..."`) to extract the needed fields. Do not assume fields exist; read the response first and then map to the answer template.

---

## Task workflow

Every task follows this sequence:

1. **Read the prompt** (`input/prompt.txt`). It identifies the portfolio, the desk or committee context, and which answer template to use.
2. **Read the answer template** (`input/payloads/answer_template.json`). This defines every required field, its type, allowed values, numeric precision, list ordering rules, and required keys. Do not deviate from it — missing a required key or using the wrong precision is an error.
3. **Read the local request payload** (named file in `input/payloads/`). It carries intake context: request parameters, stale snapshots, memo notes, meeting preferences, and candidate shortlists. Mark everything from this file as potentially stale.
4. **Query the environment API**. Fetch current portfolio holdings, bond/issuer records, index levels, policies, allocation views, and macro signals as needed. This is the authoritative source.
5. **Compute derived values**. Calculate correlations, weighted averages, post-trade metrics, and constraint checks using current environment data.
6. **Fill and return the JSON object**. Every field must conform to the answer template. Do not include commentary outside the JSON.

---

## Answer template conventions

### Precision rules

| Unit | Decimal places |
|---|---|
| USD millions (notional, market value) | 1 |
| Percentages (allocation, YTM, HY pct, reduction) | 2 |
| Duration (years) | 2 |
| Correlation coefficients | 3 |
| Macro signal scores | 3 |

### Date format

All dates use `YYYY-MM-DD`. The `as_of_date` must be drawn from the current environment records (e.g., the date returned by the holdings endpoint), never from the local payload unless the payload is confirmed identical.

### List ordering rules

Observed across templates and answers:

- **trade_package items**: sort ascending by `instrument_id`.
- **index lists** (index_set, diversification_candidates): sort ascending alphabetically by index id.
- **pair_id** (correlation pairs): sort the two index ids alphabetically within the pair.
- **sleeve_actions**: sort ascending by sleeve name.
- **rotation trades**: SELL entries first, then BUY; within each action group, sort ascending by `instrument_id`.
- **allocation_views**: follow the order in the request payload's `focus_opportunity_sets` list.
- **watchlist_sell_ids**: ascending `instrument_id` order.
- **rationale_codes** in risk_overlay: business-priority order (highest priority first).

When the template specifies an `ordering` or `item_order`, follow it exactly.

### Enum reference

**Trade actions**: `BUY`, `SELL`, `HOLD`, `NO_TRADE`

**Sleeve actions**: `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`

**Allocation views**: `UW` (underweight), `N` (neutral), `OW` (overweight)

**View changes**: `UP`, `DOWN`, `UNCHANGED`

**Conviction**: `LOW`, `MEDIUM`, `HIGH`

**Rationale codes** (full set):
`GROWTH_IMPROVES`, `RATE_CUT_SUPPORT`, `CREDIT_SPREAD_RISK`, `DOLLAR_DEFENSIVE`, `CHINA_DEPENDENCE`, `LATAM_DIVERSIFIER`, `INDIA_OFFSET`, `DURATION_SUPPORT`, `HY_VALUATION_RISK`, `EUROPE_RECOVERY`, `JAPAN_POLICY_RISK`, `NEUTRAL_BALANCE`

**Sales target segments**: `insurance_general_account`, `pension_liability_matching`, `multi_asset_income`, `private_bank_income`, `endowment_opportunistic`

**Sales themes**: `lng_export_tailwind`, `oil_oversupply_caution`, `midstream_stability`, `transition_bond_selectivity`, `avoid_watchlist_yield_trap`

**Concentration primary codes**: `CHINA_ASIA_DEPENDENCE`, `GLOBAL_DEVELOPED_OVERLAP`, `NO_MATERIAL_CONCENTRATION`

**Risk overlay codes**: `DURATION_QUALITY_TILT`, `CREDIT_RISK_REDUCTION`, `EQUITY_BETA_EXTENSION`, `CURRENCY_DEFENSIVE_HEDGE`, `NO_OVERLAY`

**Risk note codes**: `hy_cap_pressure`, `watchlist_concentration`, `duration_preservation`, `carry_tradeoff`, `no_action`

**Rebalance triggers**: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`

**Next steps**: `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`

**Data precedence**: `current_environment_over_stale_payload`, `local_payload_over_current_environment`, `no_conflict_found`

---

## Stale-data rule

Local request payloads often carry `stale_`-prefixed fields, "not reconciled" comments, or explicit earlier dates. When the environment returns different values for the same data, **always** use the environment values. Set `data_precedence` to `current_environment_over_stale_payload` when the answer template includes that field. Mention in any rationale or desk-note field that the recommendation is based on refreshed environment data.

Do not copy stale holding snapshots, stale exception boards, or stale local notes into the final answer. They inform preferences (e.g., desired HY reduction, preferred sectors) but data values come from the API.

---

## Calculation recipes

### Pearson correlation of monthly simple returns

Used for correlation review tasks. Steps:

1. Fetch monthly index levels from `/api/index-levels/{index_id}` for each index in the universe, filtered to the review window (e.g., 2025-05-30 through 2026-04-30, yielding 12 levels per index).
2. For each index, compute monthly simple returns: `r_t = (level_t - level_{t-1}) / level_{t-1}`. This yields N-1 return observations from N levels.
3. For each pair of indices, compute the Pearson correlation of their aligned return series.
4. Round to 3 decimal places.

The `return_observations` count is (number of levels - 1), e.g., 12 levels → 11 return observations.

When computing in the shell, use Python:

```python
import json, sys, math

# levels_a and levels_b are lists of monthly values in chronological order
def pearson_r(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx)**2 for x in xs) * sum((y - my)**2 for y in ys))
    return num / den if den != 0 else 0.0

returns_a = [(levels_a[i] - levels_a[i-1]) / levels_a[i-1] for i in range(1, len(levels_a))]
returns_b = [(levels_b[i] - levels_b[i-1]) / levels_b[i-1] for i in range(1, len(levels_b))]
r = round(pearson_r(returns_a, returns_b), 3)
```

### Weighted portfolio metrics

Used for post-trade metric computation.

**Weighted modified duration**:
```
sum(market_value_i * modified_duration_i) / sum(market_value_i)
```
for all holdings post-trade. Round to 2 decimals.

**Weighted yield to maturity**:
```
sum(market_value_i * yield_to_maturity_i) / sum(market_value_i)
```
for all holdings post-trade. Round to 2 decimals.

**Total market value**: sum of all holding market values, including new buys / excluding sells. Round to 2 decimals.

**HY allocation pct**:
```
sum(market_value of HY-rated holdings) / total_market_value * 100
```
Round to 2 decimals. "HY" generally means ratings below investment grade (BB+ and lower, or instruments explicitly classified as high-yield in the bond master).

**HY reduction pct points**:
```
pre_trade_hy_pct - post_trade_hy_pct
```
Round to 2 decimals.

**Watchlist exposure**: sum of market values of holdings whose instrument_id or issuer_id is flagged in the watchlist, after trades. Round to 1 decimal.

---

## Task-type specifics

### Trade strategy (like train_001)

- Fetch portfolio holdings, bond master, issuer master, and energy market data.
- Filter bonds by: energy-linked subsector, non-watchlist issuer, current eligibility.
- Select 2 BUY tickets totaling the specified notional, split evenly.
- Verify the selections improve carry (higher YTM than current portfolio average) while respecting HY cap, duration band, issuer diversification, and subsector diversification.
- Position the package to a client segment aligned with the request context.
- Fill `data_precedence` as `current_environment_over_stale_payload` when local snapshots differ from API data.

### Correlation review (like train_002)

- Fetch index metadata and monthly levels for all indices in the universe.
- Compute all pairwise Pearson correlations.
- Identify the **highest positive** correlation pair (concentration risk) and the **lowest** correlation pair (best diversifier).
- Assess concentration: if China and an Asia-Pacific index share high correlation with EM, flag `CHINA_ASIA_DEPENDENCE`.
- Propose diversification candidates among non-overlapping indices.
- Recommend sleeve actions (trim/add/hold) based on correlation findings.

### Allocation view refresh (like train_003)

- Fetch opportunity sets, prior views, macro signals, and policies.
- For each focus opportunity set, derive the current view from the prior view and macro signal score:
  - Positive signal score with neutral/underweight prior → upgrade (OW/UP)
  - Negative signal score with neutral/overweight prior → downgrade (UW/DOWN)
  - Strong positive score with already-overweight prior → UNCHANGED
  - Strong negative score with already-underweight prior → UNCHANGED
- Assign conviction: `HIGH` for strong signal magnitude or persistent views; `MEDIUM` for moderate signals; `LOW` for weak or conflicting signals.
- Assign rationale codes from the enum set, matching the economic narrative to the opportunity set (e.g., `EUROPE_RECOVERY` for Europe OW, `JAPAN_POLICY_RISK` for Japan UW, `CHINA_DEPENDENCE` for EM UW).
- Select a risk overlay code that summarizes the aggregate tilt.

### Risk rebalance (like train_004)

- Fetch portfolio holdings, bond master, issuer master, and policies.
- Identify holdings to sell: HY-rated, watchlisted, or concentrated positions that pressure constraints.
- Select buy candidates from IG-rated, non-watchlist bonds that preserve or extend duration.
- Size trades to meet the HY reduction target and eliminate watchlist exposure.
- Compute post-trade risk metrics and check all exception flags.
- Fill `watchlist_handling` with the list of watchlisted instruments sold and a confirmation that buys avoid the watchlist.

### Committee synthesis (like train_005)

- This task type combines correlation review and allocation view refresh for a single portfolio.
- Compute correlation pairs from the index subset specified in the committee request.
- Fetch allocation views from the environment for the focused opportunity sets.
- Merge findings into a committee decision file: correlation summary, sleeve actions driven by correlation findings, allocation views with signal scores and prior-quarter baselines, and a recommended next step.

---

## Output discipline

Always return **only** the JSON object. No markdown fences, no narrative preamble, no trailing text. The JSON must:

- Include every `required` key from the answer template.
- Use exactly the precision declared per field.
- Use only the enum values listed in the template or in this skill's enum reference.
- Follow all list ordering rules.
- Set `as_of_date` from the environment, not the local payload.
- Reflect current environment data, not stale local snapshots.

When the answer template has a `required_value` for a field, use that exact value.

When a template field has `allowed_values`, do not invent new values. If you believe a value outside the allowed set is justified, re-examine the environment data; the allowed values are exhaustive for the domain.

---

## Quick API reference card

For a compact reference during task execution, see [api_reference.md](api_reference.md).
