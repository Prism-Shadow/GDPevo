---
name: asteria-institutional-portfolio
description: >
  Work with the Asteria Investment Office shared environment to perform
  institutional portfolio operations — credit/energy trade strategies,
  international equity correlation reviews, active allocation view
  refreshes, fixed-income risk rebalances, and multi-asset committee
  decision files. Use this skill whenever the task references Asteria,
  portfolio IDs prefixed with PF-, the Asteria Investment Office,
  or the shared environment at the Asteria base URL.
---

# Asteria Institutional Portfolio Skill

## Environment

All real-time portfolio, instrument, issuer, index, market, macro-signal,
allocation, and policy data lives in a shared Asteria Investment Office
environment reachable over HTTP.  Every task *must* query this environment;
local payload files may contain stale or unchecked values that are
secondary to the current environment records.

### Base URL

```
http://task-env:9010
```

Authentication is not required.  Every call is a plain HTTP `GET`.

### API Catalogue

| Endpoint                                        | Returns                                                     |
|-------------------------------------------------|-------------------------------------------------------------|
| `GET /`                                         | Health / root                                                |
| `GET /api/portfolios`                           | List of all current portfolio ids                           |
| `GET /api/portfolios/{portfolio_id}/holdings`   | Current holdings for a portfolio                            |
| `GET /api/instruments/bonds`                    | Bond master data (id, issuer, coupon, maturity, rating, …)  |
| `GET /api/issuers`                              | Issuer profiles, ratings, watchlist status                   |
| `GET /api/market/energy`                        | Energy-sector market data                                    |
| `GET /api/indices`                              | Index metadata catalogue                                     |
| `GET /api/index-levels`                         | Monthly (or periodic) level history for all indices          |
| `GET /api/index-levels/{index_id}`              | Level history for a single index                             |
| `GET /api/allocation/opportunity-sets`          | Current opportunity-set taxonomy and definitions             |
| `GET /api/allocation/prior-views`               | Prior-quarter active allocation views (UW / N / OW)         |
| `GET /api/macro-signals`                        | Macro signal scores by opportunity set                       |

Replace `{portfolio_id}` and `{index_id}` with the relevant identifiers
obtained from the catalogue endpoints or the task input.

## Standard Workflow

For every Asteria institutional task, follow this ordered process:

1. **Read the prompt** — `input/prompt.txt` defines the task, portfolio scope,
   and any special rules or constraints.
2. **Read the answer template** — `input/payloads/answer_template.json` is
   the mandatory output shape.  Every required field must be present; every
   enum must use an allowed value.
3. **Read all auxiliary payloads** — additional JSON files in
   `input/payloads/` provide intake context (desk requests, review requests,
   committee packets, risk memos, stale snapshots).  Treat these as helpful
   context but *never* as authoritative current-state data.
4. **Query the environment** — call the relevant API endpoints to obtain
   the current book of record.
5. **Produce the answer JSON** — conform exactly to the answer template.
   Return *only* the JSON object (no surrounding commentary) unless the
   prompt explicitly asks for narrative.

### Data Precedence

When the environment and a local payload disagree, prefer the environment
data.  If the prompt explicitly states that local payload values override
environment values, respect that.  Otherwise treat the environment as the
single source of truth.

The answer template may include a `data_precedence` field with allowed
values:
- `current_environment_over_stale_payload`
- `local_payload_over_current_environment`
- `no_conflict_found`

Select the value that reflects the actual reconciliation performed.

## Institutional Domain Knowledge

### Portfolio Naming

Portfolio ids follow the pattern `PF-{asset-class-abbrev}-{codename}`,
e.g. `PF-EN-ALTA`, `PF-INT-NEXVEN`, `PF-FI-LUMEN`, `PF-MA-HELIO`.
Look up the portfolio from the prompt; never hard-code assumptions about
which portfolios exist.

### Instrument Identifiers

Instruments are referenced by string ids such as `BND_BLUEGAS_2030` or
`BND_JUNIPER_2028`.  Always obtain the current instrument list from
`GET /api/instruments/bonds`.  Do not invent instrument ids.

### Index Identifiers

Index ids follow the pattern `IDX_{shortcode}` (e.g. `IDX_EM`, `IDX_CHINA`,
`IDX_INDIA`, `IDX_LATAM`, `IDX_WORLD`, `IDX_EAFE`, `IDX_ACWI_IMI`,
`IDX_AC_ASIA_PAC_EX_JP`, `IDX_EM_EX_CHINA`).  Obtain the current index
catalogue from `GET /api/indices`.

### Correlation Calculations

When the task asks for Pearson correlations:

- Use *monthly simple returns* computed from consecutive index levels:
  `R_t = (Level_t / Level_{t-1}) - 1`.
- Round to **three decimal places**.
- When listing a pair of index ids, sort them **alphabetically**.

When identifying extreme pairs:
- **Highest positive correlation** → highest concentration risk pair.
- **Lowest (most negative) correlation** → best diversification pair.

### Allocation Views & Conviction

| Code   | Meaning       |
|--------|---------------|
| `UW`   | Underweight   |
| `N`    | Neutral       |
| `OW`   | Overweight    |

Conviction levels: `LOW`, `MEDIUM`, `HIGH`.

View changes vs. prior quarter: `UP`, `DOWN`, `UNCHANGED`.

### Rationale Codes

The following rationale codes are recognised across allocation-view tasks.
Select the code that best matches the signal, macro context, and
opportunity-set characteristics (not every code applies to every set):

| Code                    | Typical trigger                                           |
|-------------------------|-----------------------------------------------------------|
| `GROWTH_IMPROVES`       | Improving growth outlook for the region / asset class     |
| `RATE_CUT_SUPPORT`      | Expected rate cuts provide tailwind                        |
| `CREDIT_SPREAD_RISK`    | Widening spread risk or credit deterioration               |
| `DOLLAR_DEFENSIVE`      | USD strength or defensive positioning                      |
| `CHINA_DEPENDENCE`      | Overweight China exposure drags or creates concentration   |
| `LATAM_DIVERSIFIER`     | Latin America offers diversification benefit               |
| `INDIA_OFFSET`          | India provides offset to EM / China exposure               |
| `DURATION_SUPPORT`      | Duration positioning is supported by macro backdrop        |
| `HY_VALUATION_RISK`     | High-yield valuations are stretched or risky               |
| `EUROPE_RECOVERY`       | European recovery thesis supports overweight               |
| `JAPAN_POLICY_RISK`     | Japan policy uncertainty weighs on outlook                 |
| `NEUTRAL_BALANCE`       | Balanced / neutral posture with no strong directional view  |

### Risk & Constraint Checks

Tasks involving credit or fixed-income portfolios operate under standard
institutional constraints.  The answer template will spell out the specific
checks required — typically including some of:

- **HY cap** — high-yield allocation must not exceed a policy ceiling.
- **Duration band** — weighted modified duration must stay inside the CIO range.
- **Issuer diversification** — no single issuer dominates post-trade.
- **Subsector diversification** — exposure spread across energy sub-sectors.
- **Watchlist avoidance** — no BUY tickets for watchlisted issuers.

### Rebalance & Committee Actions

Sleeve or target actions use these verbs:
| Action    | Meaning                                |
|-----------|----------------------------------------|
| `trim`    | Reduce exposure                         |
| `add`     | Increase exposure                       |
| `hold`    | Maintain current allocation             |
| `hedge`   | Apply a currency or risk overlay        |
| `monitor` | Watch but do not trade                  |
| `rotate`  | Shift exposure between related sleeves  |

### Sales Positioning

When the task requires a client-facing income pitch, select from:

**Target segments:**
- `insurance_general_account`
- `pension_liability_matching`
- `multi_asset_income`
- `private_bank_income`
- `endowment_opportunistic`

**Themes:**
- `lng_export_tailwind`
- `oil_oversupply_caution`
- `midstream_stability`
- `transition_bond_selectivity`
- `avoid_watchlist_yield_trap`

### Risk Overlay Codes (CIO Desk)

When a risk overlay is requested:
- `DURATION_QUALITY_TILT` — tilt toward duration and quality.
- Primary actions: `tilt_to_duration_quality`, etc.

### Numeric Precision Rules

Always respect the precision declared in the answer template.  Common
conventions:
- Market values / notional amounts: **1 decimal** (USD millions) or **2
  decimals** depending on the template.
- Percentages (yield, HY allocation): **2 decimals**.
- Duration: **2 decimals** in years.
- Correlations: **3 decimals**.
- Signal scores: **3 decimals**.

### Ordering Rules

- Trade lists: sort ascending by `instrument_id`.
- Index pairs within a correlation result: sort alphabetically.
- Allocation view or sleeve-action lists: follow the item order declared in
  the answer template (usually by `opportunity_set` name).

## Output Rules

- Return **only** the JSON object matching the answer template.
- Do not wrap in markdown code fences unless the prompt explicitly asks.
- Do not include narrative commentary outside the JSON.
- Every `required` field must be present; every enum value must come from
  the allowed-values list.
- Use `as_of_date` from the current environment, not from a stale payload.
