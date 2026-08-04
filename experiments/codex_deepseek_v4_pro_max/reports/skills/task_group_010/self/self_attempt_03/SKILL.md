---
name: asteria-investment-office
description: Resolve Asteria Investment Office institutional portfolio tasks by querying the shared environment API, reconciling stale local payloads, and producing template-conformant JSON answers.
---

# Asteria Investment Office – Institutional Portfolio Task Skill

## Overview

This skill provides reusable operating rules for completing Asteria Investment Office tasks. Each task follows a common pattern: a `prompt.txt` with instructions, one or more JSON payloads in `input/payloads/` providing local request context (possibly stale), and an `answer_template.json` defining the required output schema. The shared Asteria environment API is the current book of record and must be treated as authoritative over any local payload data.

## Environment API

The Asteria environment runs an HTTP service with the following fixed contract:

- **Base URL**: `http://task-env:9010/`
- **Method**: HTTP GET only
- **Authentication**: none required

### Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service root / health check |
| `GET /api/portfolios` | List all portfolios |
| `GET /api/portfolios/{portfolio_id}/holdings` | Holdings for a specific portfolio |
| `GET /api/instruments/bonds` | Bond instrument catalog with security-master detail |
| `GET /api/issuers` | Issuer records (ratings, watchlist status, sector) |
| `GET /api/market/energy` | Energy-market data for credit desks |
| `GET /api/indices` | Equity index metadata and identifiers |
| `GET /api/index-levels` | Monthly index level time series for all indices |
| `GET /api/index-levels/{index_id}` | Monthly levels for a single index |
| `GET /api/allocation/opportunity-sets` | Active allocation opportunity-set taxonomy |
| `GET /api/allocation/prior-views` | Prior-quarter active allocation views |
| `GET /api/macro-signals` | Current macro signal scores and codes |

Replace `{portfolio_id}` and `{index_id}` with the relevant identifier from the task input or from a catalog/list endpoint.

## Task Input Structure

Every task directory contains:

- `prompt.txt` — natural-language instructions describing the assignment, the portfolio context, and which environment endpoints are relevant.
- `input/payloads/` — one or more JSON files providing local request context. **These may contain stale marks, pre-reconciled worksheets, or preferences from an earlier cycle.**
- `input/payloads/answer_template.json` — the exact JSON output contract: required keys, field types, enums, numeric precision, ordering rules, and list lengths.

## Core Operating Rules

### Rule 1: Data Precedence — Environment over Local

The shared Asteria environment API is always the **current book of record**. When a local payload contains data that conflicts with the environment response, the environment wins. This principle is encoded in fields such as `data_precedence` with allowed values:

- `current_environment_over_stale_payload` — environment data is authoritative
- `local_payload_over_current_environment` — rare override; use only when the environment is demonstrably incomplete
- `no_conflict_found` — both sources agree

Before computing an answer, always refresh the relevant data from the environment API. Do not rely on stale dates, holdings snapshots, or exception boards in local payloads without cross-checking.

### Rule 2: Strict Template Conformance

The answer must be a single JSON object matching `answer_template.json` exactly. No narrative commentary outside the JSON. Obey every constraint declared in the template:

- **Required keys** — every key listed under `required`, `required_top_level_keys`, or `required_keys` must be present.
- **Enum values** — fields constrained by `allowed_values` must use exactly one of the listed strings.
- **Numeric precision** — round every numeric field to the `precision` declared (e.g. 1 decimal for USD millions, 2 decimals for percentages and duration, 3 decimals for correlation).
- **List ordering** — sort lists according to the template's declared ordering rule (ascending by `instrument_id`, alphabetical within pairs, payload order for opportunity sets, etc.).
- **List length** — match declared `length` constraints on lists.
- **Fixed/required values** — include `required_value` fields verbatim (e.g. `"portfolio_id": "PF-EN-ALTA"`).

### Rule 3: Query the Environment Before Computing

Follow this workflow for every task:

1. Read `prompt.txt` to understand the assignment and identify relevant endpoints.
2. Read all JSON payloads in `input/payloads/` for local context.
3. Read `answer_template.json` to understand the required output shape.
4. Query the environment API endpoints needed for the task.
5. Cross-reference environment responses with local payload data; resolve conflicts in favor of the environment.
6. Build the answer JSON by populating every field the template requires.
7. Validate that all enums, precision, ordering, and required-value constraints are satisfied.

### Rule 4: Numeric Conventions

| Unit/Semantic | Default Precision | Example Field |
|---------------|-------------------|---------------|
| USD millions (notional, market value, quantity) | 1 decimal | `notional_usd_m`, `quantity_usd_m` |
| USD millions (portfolio totals) | 2 decimals | `total_market_value_usd_m` |
| Percentages (allocation, YTM) | 2 decimals | `hy_allocation_pct`, `weighted_yield_to_maturity_pct` |
| Duration (years) | 2 decimals | `weighted_modified_duration_years` |
| Percentage-point changes | 2 decimals | `hy_reduction_pct_points` |
| Correlation (Pearson) | 3 decimals | `correlation` |
| Signal scores | 3 decimals | `signal_score` |

Always defer to the precision declared in the specific answer template if it differs from the defaults above.

### Rule 5: Correlation Calculations

When correlation values are required:

- Compute **Pearson correlation** of **monthly simple returns** derived from consecutive index levels within the requested review window.
- Round to **three decimal places**.
- When forming pairs, list index IDs in **ascending alphabetical order** within each pair.

### Rule 6: Sorting Conventions

| Context | Sort Rule |
|---------|-----------|
| Trade lists (BUY/SELL) | SELL before BUY, then ascending by `instrument_id` within each action |
| Trade lists (single action) | Ascending by `instrument_id` |
| Index ID lists | Ascending alphabetical |
| Index IDs within a pair | Ascending alphabetical |
| Allocation/opportunity-set rows | As ordered in the request payload's list |
| Sleeve actions | Ascending by sleeve name |
| Rationale codes | Business priority order, highest priority first |

### Rule 7: Common Enumeration Vocabularies

**Active views**: `UW` (underweight), `N` (neutral), `OW` (overweight)

**View changes**: `UP`, `DOWN`, `UNCHANGED`

**Conviction**: `LOW`, `MEDIUM`, `HIGH`

**Trade actions**: `BUY`, `SELL`, `HOLD`, `NO_TRADE`

**Sleeve/portfolio actions**: `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`

**Asset classes**: `Equities`, `Duration`, `Credit`, `Currency`

**Overlay codes**: `DURATION_QUALITY_TILT`, `CREDIT_RISK_REDUCTION`, `EQUITY_BETA_EXTENSION`, `CURRENCY_DEFENSIVE_HEDGE`, `NO_OVERLAY`

**Primary overlay actions**: `tilt_to_duration_quality`, `trim_credit_beta`, `add_cyclical_equity_beta`, `add_currency_hedge`, `hold_policy_weights`

**Rationale codes** (shared across allocation and macro-signal tasks):
`GROWTH_IMPROVES`, `RATE_CUT_SUPPORT`, `CREDIT_SPREAD_RISK`, `DOLLAR_DEFENSIVE`, `CHINA_DEPENDENCE`, `LATAM_DIVERSIFIER`, `INDIA_OFFSET`, `DURATION_SUPPORT`, `HY_VALUATION_RISK`, `EUROPE_RECOVERY`, `JAPAN_POLICY_RISK`, `NEUTRAL_BALANCE`

**Concentration codes**: `CHINA_ASIA_DEPENDENCE`, `GLOBAL_DEVELOPED_OVERLAP`, `NO_MATERIAL_CONCENTRATION`

**Sales target segments**: `insurance_general_account`, `pension_liability_matching`, `multi_asset_income`, `private_bank_income`, `endowment_opportunistic`

**Sales themes**: `lng_export_tailwind`, `oil_oversupply_caution`, `midstream_stability`, `transition_bond_selectivity`, `avoid_watchlist_yield_trap`

**Risk note codes**: `hy_cap_pressure`, `watchlist_concentration`, `duration_preservation`, `carry_tradeoff`, `no_action`

**Rebalance triggers**: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`

**Next steps**: `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`

### Rule 8: Constraint and Exception Flag Patterns

Many answer templates include boolean constraint-check fields. Name these consistently based on domain:

- **High-yield cap**: `hy_cap_pass`
- **Duration band**: `duration_band_pass`
- **Issuer diversification**: `selected_issuer_diversification_pass` or similar
- **Subsector diversification**: `selected_subsector_diversification_pass`
- **Watchlist avoidance**: `watchlist_avoidance_pass` or `buys_avoid_watchlist`
- **HY reduction target**: `target_hy_reduction_met`
- **Watchlist clearance**: `watchlist_exposure_cleared`

### Rule 9: Date Fields

- Use `YYYY-MM-DD` format for all date strings.
- `as_of_date` must reflect the date of the environment data actually used, not a stale date from the local payload.
- When the environment response includes a `snapshot_date` or `as_of_date`, use that value.

### Rule 10: Portfolio-Aware Querying

Tasks span multiple portfolio domains. Identify the portfolio ID from `prompt.txt` or the request payload and query the relevant endpoints:

- **Credit / fixed-income tasks** (`PF-EN-ALTA`, `PF-FI-LUMEN`): `/api/instruments/bonds`, `/api/issuers`, `/api/market/energy`, `/api/portfolios/{id}/holdings`
- **Equity correlation tasks** (`PF-INT-NEXVEN`, `PF-MA-HELIO`): `/api/indices`, `/api/index-levels`, `/api/index-levels/{id}`
- **Allocation view tasks**: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, `/api/policies`
- **Cross-domain committee tasks** (`PF-MA-HELIO`): combine correlation, allocation, and policy endpoints

## Error Handling

- If an environment endpoint returns an unexpected status or shape, prefer the environment's response over local fallback but note the discrepancy in the appropriate field (e.g. `data_precedence`).
- If a required data point is absent from both the environment and the local payload, leave it out only if the answer template marks it optional; otherwise, flag the omission.
- Never fabricate correlation values, yield figures, or index levels — derive them from actual environment responses.
