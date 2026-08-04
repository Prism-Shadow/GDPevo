---
name: asteria-investment-office
description: Operating rules for Asteria Investment Office portfolio tasks. Use when the task involves an Asteria Investment Office prompt, a shared environment at http://task-env:9010/, local input payloads in input/payloads/, and an answer_template.json output contract. Covers data precedence, API usage, output schema conformance, and cross-task conventions.
---

# Asteria Investment Office Agent Operating Rules

## Task Recognition

An Asteria Investment Office task follows this signature pattern:

- `prompt.txt` at the task root describes the desk, portfolio, and objective.
- `input/payloads/` contains a contextual request JSON or memo (potentially stale) and an `answer_template.json` that defines the exact output schema.
- A shared Asteria environment service at `http://task-env:9010/` holds the current book of record.

## Input File Roles

| File | Role |
|------|------|
| `prompt.txt` | Task instructions: portfolio id, desk, action required, environment hint. |
| `input/payloads/<request>.json` | Intake context: request parameters, stale marks, preferences, candidate lists. This data may be outdated. |
| `input/payloads/answer_template.json` | The output contract: required keys, types, precision, allowed values, ordering rules. |

## Data Precedence Rule

The **shared Asteria environment is the current book of record**. Local payload values may be stale or unreconciled.

1. Query the environment API for the current state of every entity the task references (portfolio holdings, index levels, instrument data, issuer records, prior views, macro signals, policies).
2. When a local payload value conflicts with the environment, use the **environment value** and set the `data_precedence` field to `"current_environment_over_stale_payload"` if the answer template includes it.
3. When no conflict exists, set `data_precedence` to `"no_conflict_found"`.
4. Only use local payload values when the environment lacks the relevant data.

## Environment API

The environment service is a read-only REST API. No authentication is required.

### Base URL

```
http://task-env:9010/
```

### Endpoint Catalog

| Endpoint | Returns |
|----------|---------|
| `GET /` | Service health / root |
| `GET /api/portfolios` | All portfolio records |
| `GET /api/portfolios/{portfolio_id}/holdings` | Current holdings for a portfolio |
| `GET /api/instruments/bonds` | Bond instrument master data |
| `GET /api/issuers` | Issuer records (ratings, watchlist status, sector) |
| `GET /api/market/energy` | Energy market data |
| `GET /api/indices` | Index universe metadata |
| `GET /api/index-levels` | Monthly index level history |
| `GET /api/index-levels/{index_id}` | Level history for a specific index |
| `GET /api/allocation/opportunity-sets` | Opportunity set taxonomy |
| `GET /api/allocation/prior-views` | Prior quarter allocation views |
| `GET /api/macro-signals` | Current macro signal scores |

Replace `{portfolio_id}` and `{index_id}` with the actual identifiers from the task input or from list endpoints.

### Usage Rules

- Call the relevant endpoints to resolve every entity the task references.
- For portfolio tasks, start with `GET /api/portfolios/{portfolio_id}/holdings` to get current holdings.
- For allocation tasks, use `GET /api/allocation/prior-views` and `GET /api/macro-signals` together.
- For index tasks, use `GET /api/index-levels/{index_id}` to get monthly level histories.
- Do not assume local payload values match current environment records.

## Answer Template Conformance

The `answer_template.json` is the authoritative output contract. The output JSON must:

1. **Include every required key** exactly as listed in `required_top_level_keys` (or `required` / `required_keys`).
2. **Match enum values exactly** — no aliases, abbreviations, or inferred values.
3. **Respect precision** — every numeric field must be rounded to the decimal precision declared in the template (e.g., `precision: 2` means two decimal places).
4. **Follow ordering rules** — when the template specifies an ordering (e.g., `ascending by instrument_id`, `SELL before BUY`, or a fixed `item_order` list), apply it.
5. **Match list lengths** — when the template declares a `length` or `required_length`, produce exactly that many items.
6. **Return only the JSON object** — no narrative commentary, markdown fences, or extra text unless the prompt explicitly allows it.

## Cross-Task Conventions

### Correlation Calculations

When computing index correlations:
- Use **Pearson correlation** of **monthly simple returns**.
- Simple return for month t: (level_t − level_{t−1}) / level_{t−1}.
- Round correlation values to **three decimals**.
- When constructing pair identifiers, sort the two index IDs in **ascending alphabetical order** and use that sorted pair as the identifier.

### Trade Actions

| Action | Meaning |
|--------|---------|
| `BUY` | Acquire the instrument |
| `SELL` | Dispose of the instrument |
| `HOLD` | Maintain current position |
| `NO_TRADE` | No action taken |

### Sleeve / Portfolio Actions

| Action | Meaning |
|--------|---------|
| `trim` | Reduce exposure |
| `add` | Increase exposure |
| `hold` | Maintain current allocation |
| `hedge` | Apply offsetting position |
| `monitor` | Watch for re-entry point |
| `rotate` | Shift between related sleeves |

### Allocation View Codes

| Code | Meaning |
|------|---------|
| `UW` | Underweight |
| `N` | Neutral |
| `OW` | Overweight |

### View Change Codes

| Code | Meaning |
|------|---------|
| `UP` | View increased from prior quarter |
| `DOWN` | View decreased from prior quarter |
| `UNCHANGED` | No change from prior quarter |

### Conviction Levels

| Level | Meaning |
|-------|---------|
| `LOW` | Weak signal, low confidence |
| `MEDIUM` | Moderate signal strength |
| `HIGH` | Strong signal, high confidence |

### Rationale Codes

| Code | Meaning |
|------|---------|
| `GROWTH_IMPROVES` | Improving growth outlook |
| `RATE_CUT_SUPPORT` | Rate cuts supportive |
| `CREDIT_SPREAD_RISK` | Widening credit spread risk |
| `DOLLAR_DEFENSIVE` | USD strength as defensive factor |
| `CHINA_DEPENDENCE` | Exposure concentration to China |
| `LATAM_DIVERSIFIER` | Latin America as diversification source |
| `INDIA_OFFSET` | India as offsetting exposure |
| `DURATION_SUPPORT` | Duration supportive of position |
| `HY_VALUATION_RISK` | High-yield valuation stretched |
| `EUROPE_RECOVERY` | European recovery theme |
| `JAPAN_POLICY_RISK` | Japan policy uncertainty |
| `NEUTRAL_BALANCE` | No strong directional signal |

### Sales Positioning (Energy / Credit Desk)

| Segment | Description |
|---------|-------------|
| `insurance_general_account` | Insurance general account |
| `pension_liability_matching` | Pension liability-driven |
| `multi_asset_income` | Multi-asset income mandates |
| `private_bank_income` | Private banking income |
| `endowment_opportunistic` | Endowment opportunistic |

| Theme | Description |
|-------|-------------|
| `lng_export_tailwind` | LNG export growth tailwind |
| `oil_oversupply_caution` | Caution on oil oversupply |
| `midstream_stability` | Midstream stable cash flows |
| `transition_bond_selectivity` | Selective energy transition bonds |
| `avoid_watchlist_yield_trap` | Avoid yield from watchlisted names |

### Risk Overlay Codes

| Overlay Code | Primary Action |
|--------------|----------------|
| `DURATION_QUALITY_TILT` | `tilt_to_duration_quality` |
| `CREDIT_RISK_REDUCTION` | `trim_credit_beta` |
| `EQUITY_BETA_EXTENSION` | `add_cyclical_equity_beta` |
| `CURRENCY_DEFENSIVE_HEDGE` | `add_currency_hedge` |
| `NO_OVERLAY` | `hold_policy_weights` |

### Rebalance Trigger Codes

| Code | Meaning |
|------|---------|
| `correlation_cap_breach` | Correlation exceeded policy cap |
| `hy_cap_pressure` | High-yield allocation near limit |
| `duration_drift` | Duration outside CIO range |
| `watchlist_concentration` | Watchlist exposure too high |
| `committee_review` | Scheduled committee review |

### Next-Step Codes

| Code | Meaning |
|------|---------|
| `approve_rotation` | Approve the proposed rotation |
| `defer_pending_risk_review` | Defer for further risk analysis |
| `approve_with_monitoring` | Approve with ongoing monitoring |
| `reject_constraint_breach` | Reject due to constraint violation |

### Risk Note Codes

| Code | Meaning |
|------|---------|
| `hy_cap_pressure` | HY cap under pressure |
| `watchlist_concentration` | Watchlist concentration concern |
| `duration_preservation` | Duration preservation focus |
| `carry_tradeoff` | Carry vs. risk tradeoff |
| `no_action` | No action required |

### Concentration Codes

| Code | Meaning |
|------|---------|
| `CHINA_ASIA_DEPENDENCE` | China-Asia correlation dependence |
| `GLOBAL_DEVELOPED_OVERLAP` | Global developed market overlap |
| `NO_MATERIAL_CONCENTRATION` | No material concentration found |

## Task Workflow

1. **Read the three input files**: `prompt.txt`, the contextual payload JSON, and `answer_template.json`.
2. **Identify the portfolio ID** and any entity IDs from the prompt and payload.
3. **Query the environment API** for all current records relevant to the task.
4. **Cross-reference** local payload data against environment data. Resolve conflicts in favor of the environment.
5. **Compute required metrics** (correlations, post-trade metrics, constraint checks) using environment data.
6. **Construct the output JSON** matching the answer template schema exactly — every key, type, precision, ordering, and enum value.
7. **Validate** that all constraints in the template are satisfied (list lengths, required keys, enum values).
8. **Return only the JSON object** (unless the prompt says otherwise).
