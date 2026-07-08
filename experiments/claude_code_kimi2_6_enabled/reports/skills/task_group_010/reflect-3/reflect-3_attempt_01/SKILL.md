# Portfolio Management JSON Generation Skill

## Purpose
Generate structured portfolio-management decision JSONs by combining shared-environment data with request-specific constraints. The tasks span fixed-income (PF-FI-LUMEN) and multi-asset (PF-MA-HELIO) portfolios.

## When to Use
- You receive a prompt asking to prepare a desk proposal, portfolio review, allocation update, risk meeting memo, or committee decision file.
- The prompt references a `portfolio_id` (PF-FI-LUMEN or PF-MA-HELIO) and points to `input/payloads/committee_request.json` (or similar request file) and `input/payloads/answer_template.json`.
- You must return **only JSON** matching a strict schema.

## SOP

### 1. Read the Three Input Files
Always read, in this order:
1. `input/prompt.txt` — the narrative instruction (what the stakeholder wants).
2. `input/payloads/<request>.json` — the structured request (dates, instruments, bands, candidate shortlists, baseline weights, etc.).
3. `input/payloads/answer_template.json` — the schema contract (required top-level keys, field types, enums, precisions, ordering rules, required values).

> **Key insight:** The answer template is a specification, not an example. Every key, enum value, precision, and ordering rule is enforced.

### 2. Fetch All Shared-Environment Data
Query the Asteria Investment Office environment for the endpoints relevant to the portfolio:

| Endpoint | What It Contains | Used By |
|----------|------------------|---------|
| `/api/environment/portfolio` | Current holdings, quantities, prices, sectors, asset classes | All tasks |
| `/api/environment/index-levels` | Time-series of index levels (e.g., MSCI_EM, NIFTY_50, MSCI_LATAM, BLOOMBERG_USD) | Correlation, return calculations |
| `/api/environment/policies` | CIO bands (HY max, duration min/max, max single-name %, rebalance thresholds) | Constraint checking |
| `/api/environment/prior-views` | Previous allocation views (UW / N / OW) and convictions | Change detection |
| `/api/environment/macro-signals` | Quantitative signal scores (Growth, Rates, Credit Spreads, USD Strength) | View derivation |

Fetch **all five** endpoints even if the prompt only names a subset; cross-referencing is usually required.

### 3. Map Request Requirements to Template Fields
Create a field-by-field checklist. Common mappings:

#### Fixed-Income (PF-FI-LUMEN) Tasks
- `portfolio_id` → always `"PF-FI-LUMEN"` (hard-coded).
- `proposal_date` / `review_date` → from request payload or prompt.
- `trades` / `sells` / `buys` → derived from:
  - **Watchlist instruments** that must be reduced/removed.
  - **HY exposure** that exceeds the policy band.
  - **Cash injection** or **stale exceptions** that fund new positions.
  - **Candidate shortlist** that provides replacement IG instruments.
- `post_trade_hy_exposure_pct` → recalculate after sells/buys; must respect `target_hy_band_max`.
- `post_trade_duration` → net duration after rotation; must stay inside CIO range.
- `watchlist_breach_flag` → `true` if any watchlist instrument remains post-trade.
- `next_step` → depends on whether all constraints are satisfied.

#### Multi-Asset (PF-MA-HELIO) Tasks
- `portfolio_id` → always `"PF-MA-HELIO"`.
- `review_quarter` → often hard-coded (e.g., `"Q2_2026"`).
- `correlation_summary` → compute Pearson correlation of **monthly simple returns** from consecutive index levels for the pairs listed in the request.
- `target_sleeve_actions` → derive from views and risk flags (trim overweight, add underweight, hold neutral, hedge/rotate for risk).
- `allocation_views` → for each opportunity set:
  1. Read `prior_view` from `/api/environment/prior-views`.
  2. Compute or read `signal_score` from macro signals.
  3. Derive `view` (UW / N / OW) from signal score and policy thresholds.
  4. Set `change` by comparing `view` to `prior_view`.
  5. Set `conviction` based on signal strength dispersion.
  6. Pick `rationale_code` from the allowed enum that best matches the dominant macro signal.
- `rebalance_trigger` → select the enum value that matches the primary reason for the committee action.
- `portfolio_risk_concentration_flag` → `true` if any correlation, band, or watchlist threshold is breached.

### 4. Perform Calculations Rigorously

#### Monthly Simple Returns
```
return_t = (level_t - level_{t-1}) / level_{t-1}
```
Use consecutive index levels from the review period. Do **not** annualize.

#### Pearson Correlation
Compute between the return series of each pair. Round to **3 decimal places**.

> **Critical:** Pairs inside the `correlation_summary` object must have their two index IDs sorted **alphabetically**.

#### Post-Trade Portfolio Metrics (Fixed Income)
- **HY exposure %** = sum of HY holdings / total portfolio value.
- **Duration** = weighted average of instrument durations (weight = market value).
- **Cash** = prior cash + proceeds from sells - cost of buys + any injection.
- Round HY exposure to **4 decimal places**, duration to **2**, cash to **2**.

#### Signal Score to View Mapping (Multi-Asset)
- Typical threshold: signal_score > 0.5 → `OW`, < -0.5 → `UW`, else `N`. (Confirm against policy document if provided.)
- `change` is `UP` if view improves from prior, `DOWN` if worsens, `UNCHANGED` if same.

### 5. Apply Business Rules in Priority Order

1. **Watchlist reduction first** — sell watchlist instruments to the extent possible.
2. **HY band compliance** — if post-trade HY % > max band, sell more HY or add IG.
3. **Duration band compliance** — keep duration inside CIO min/max; use duration ballast candidates if needed.
4. **Avoid new watchlist buys** — if the request specifies `avoid_new_watchlist_buy: true`, exclude candidates flagged as watchlist risk.
5. **Stale exception handling** — stale exceptions may be swapped for cleaner candidates of similar profile.
6. **Cash deployment** — inject or deploy cash only after risk constraints are met.

### 6. Enforce Schema Compliance

Before returning JSON, verify every field against the answer template:

- [ ] All `required_top_level_keys` are present.
- [ ] Keys appear in the exact order specified (if an `item_order` is given).
- [ ] `required_value` fields match exactly (e.g., `portfolio_id`, `review_quarter`).
- [ ] Enum fields use only allowed values.
- [ ] Numbers match the specified precision.
- [ ] Lists have the required length.
- [ ] Nested objects contain only the declared sub-fields.
- [ ] No extra commentary, markdown, or keys outside the schema.

> **Common pitfall:** Using `"USD"` in a trade `action` field when the template expects `"buy"` or `"sell"`. Always cross-check the enum list in the template.

### 7. Validate Logical Consistency

- If `watchlist_breach_flag` is `false`, ensure no watchlist instruments remain.
- If `cio_review_flag` is `true`, the `cio_review_reason` must **not** be `"NONE"`.
- `hy_reduction_pct_points` should equal the difference between pre- and post-trade HY %.
- `target_allocations` deviations must sum to zero (or near-zero within rounding).
- `signal_score` sign should match the direction of `view` (positive → OW or N, negative → UW or N).

### 8. Output Only Valid JSON

Return the raw JSON object. Do **not** wrap it in markdown code fences, do not add a preamble like "Here is the JSON:", and do not include any narrative explanation. The downstream consumer parses the response directly.

## Task-Specific Cheat Sheet

| Task Type | Portfolio | Key Calculations | Critical Checks |
|-----------|-----------|------------------|-----------------|
| Desk Proposal | PF-FI-LUMEN | Trades, post-trade HY %, duration, cash | HY band, duration band, watchlist breach |
| Portfolio Review | PF-FI-LUMEN | Watchlist status changes, new position reasons | All watchlist statuses updated, summary flags consistent |
| Allocation Update | PF-MA-HELIO | Target weights, deviations, signal scores | Deviations sum to ~0, macro signal summary dominant signal matches top view |
| Rotation Memo | PF-FI-LUMEN | Sell/buy lists, HY reduction, duration change | Watchlist cleared flag matches sells, CIO review flag consistent with constraints |
| Committee JSON | PF-MA-HELIO | Correlations (monthly returns), sleeve actions, allocation views | Correlation pairs alphabetically sorted, views derived from signals and prior views |

## Remember
- The **answer template is the contract**: every rule, enum, precision, and ordering constraint in it is enforced.
- Fixed-income tasks revolve around **HY exposure, duration, and watchlist**.
- Multi-asset tasks revolve around **correlations, macro signals, and active views**.
- Always fetch **all five environment endpoints** even when the prompt only names a subset; the data is cross-referenced implicitly.
- Return **only** the JSON object—no markdown, no preamble, no trailing commentary.
