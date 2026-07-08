# Asteria Portfolio Risk And Allocation JSON Skill

Use this skill for Asteria Investment Office tasks that ask for compact JSON answers about credit portfolio trades, fixed-income risk rotations, international equity correlations, active allocation views, or committee decisions that combine those inputs.

## Core Source-Of-Truth Rules

1. Read the local prompt and payloads only to identify the portfolio id, request scope, requested ordering, stale context, review window, allowed enums, and required JSON schema.
2. Treat the shared Asteria API as the current book of record for holdings, quantities, security metadata, issuer status, policies, index levels, macro signals, prior views, and as-of dates.
3. If a local memo or worksheet says it is stale, or its values conflict with API records, use the API. When the template asks for data precedence, use `current_environment_over_stale_payload` for that case.
4. Do not infer missing schema fields from prose. Use `answer_template.json` exactly: required keys, enum spelling, list lengths, precision, and ordering rules.
5. Return only the JSON object when the prompt says so. Do not include narrative comments, calculations, or markdown outside the JSON.

Base API:

```text
<environment_base_url>
```

Useful endpoints:

```text
GET /api/catalog
GET /api/policies
GET /api/portfolios
GET /api/portfolios/<portfolio_id>
GET /api/instruments/bonds
GET /api/issuers
GET /api/market/energy
GET /api/indices
GET /api/index-levels
GET /api/index-levels/<index_id>
GET /api/allocation/opportunity-sets
GET /api/allocation/prior-views
GET /api/macro-signals
```

Most list endpoints accept equality filters such as `?quarter=Q2_2026`, `?candidate=true`, or `?rating_bucket=HY`; still verify the returned shape.

## Standard Workflow

1. Parse the answer template first. Record required keys, enum values, numeric precision, and list ordering.
2. Fetch `/api/policies` and the target `/api/portfolios/<portfolio_id>`. Use the portfolio `as_of_date` for portfolio-specific answers unless the template clearly wants a policy/allocation date.
3. Fetch the domain reference data needed by the task:
   - Credit tasks: `/api/instruments/bonds`, `/api/issuers`, and sometimes `/api/market/energy`.
   - Correlation tasks: `/api/indices` and `/api/index-levels` or `/api/index-levels/<index_id>`.
   - Allocation tasks: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`, and `/api/policies`.
4. Join data explicitly:
   - Holdings use `instrument_id`.
   - Bonds use `issuer_id`; join to issuers for `watchlist`, issuer sector/subsector, and credit outlook.
   - Opportunity-set rows join by exact `opportunity_set` string and requested `quarter`.
   - Index levels join by exact `index_id`.
5. Compute metrics using current API quantities and metadata. Round only at final output.
6. Validate every constraint flag from computed post-trade state, not from intent.
7. Before final JSON, check ordering, enum spelling, booleans as booleans, and numeric precision.

## Credit Trade And Rotation SOP

Use this for energy-credit BUY packages and fixed-income SELL/BUY rotations.

### Eligibility

- A BUY candidate normally must have `candidate: true` in `/api/instruments/bonds`.
- For energy-credit tasks, also require `energy_linked: true` unless the prompt allows broader credit.
- Avoid buying any bond whose issuer has `watchlist: true`, especially when the prompt asks for client-facing income, risk reduction, or watchlist avoidance.
- For risk-reduction rotations, SELL only instruments currently held in the portfolio. Do not use stale memo quantities if current portfolio quantities differ.
- Prefer investment-grade non-watchlist buys for HY/watchlist reduction tasks unless the prompt explicitly requests HY carry and the HY cap remains safe.
- When a prompt supplies a shortlist, reconcile it to the current API: a named candidate may be ineligible because of issuer watchlist status, rating bucket, or current candidate flag.

### Trade Sizing

- If the prompt specifies exact ticket count, total notional, and split, obey it. Example pattern: two BUY tickets totaling 8.0 means two 4.0 tickets.
- If a rotation is sell-funded, keep total BUY quantity equal to total SELL quantity unless the prompt specifies external funding or cash retention.
- Never sell more than current API quantity.
- Use USD millions as the quantity/notional unit.

### Post-Trade Calculations

Let current portfolio market value be `MV`. Treat holdings quantities as USD millions of market value unless the prompt gives a different convention.

For each instrument:

```text
post_quantity = current_quantity + total_buys - total_sells
post_mv = MV + sum(BUY quantities) - sum(SELL quantities)
```

For a funded rotation with equal buys and sells, `post_mv` usually stays unchanged.

Credit metrics:

```text
HY allocation % =
  100 * sum(post_quantity where bond.rating_bucket == "HY") / post_mv

Weighted modified duration =
  sum(post_quantity * bond.modified_duration_years) / post_mv

Weighted yield to maturity % =
  sum(post_quantity * bond.yield_to_maturity_pct) / post_mv

Watchlist exposure USD m =
  sum(post_quantity where joined issuer.watchlist == true)

HY reduction percentage points =
  pre_trade_HY_allocation_pct - post_trade_HY_allocation_pct
```

Constraint checks:

- `hy_cap_pass`: post HY allocation is less than or equal to policy `max_hy_allocation_pct`.
- `duration_band_pass`: post weighted duration is inside inclusive `duration_band_years`.
- `target_hy_reduction_met`: HY reduction is at least policy or prompt target.
- `watchlist_exposure_cleared`: post watchlist exposure is zero when the task asks to clear avoidable watchlist risk.
- `buys_avoid_watchlist`: every BUY issuer has `watchlist: false`.
- Issuer diversification: selected BUY issuers should be distinct, and any requested issuer concentration limit should be tested against post-trade issuer exposure divided by post market value.
- Subsector diversification: count unique subsectors among selected BUYs or the requested package; compare with policy `subsector_min_count_for_diversified` when present.

### Selecting Credit Trades

For income BUY packages:

1. Enumerate eligible candidate BUY combinations of the required size.
2. Reject packages that breach HY cap, duration band, watchlist avoidance, issuer diversification, or subsector diversification.
3. Among passing packages, prefer higher post-trade weighted yield/carry.
4. Use energy macro signals and theme tags as tie-breakers: LNG/gas demand and midstream defensive carry are generally client-friendly; watchlist/high-carry traps and volatile refining exposure are not.
5. If the output needs sales positioning, map the package theme to the closest allowed enum rather than inventing language.

For risk-reduction rotations:

1. Identify current HY and watchlist holdings.
2. Prioritize selling watchlist exposure, then additional HY exposure needed to meet the target reduction.
3. Buy current eligible non-watchlist candidates that preserve duration inside the CIO band.
4. Prefer buys that improve credit quality and reduce exception pressure over buys that merely maximize yield.
5. Choose the risk note code from the dominant reason for the rotation, such as watchlist concentration, HY cap pressure, duration preservation, or carry tradeoff.

Ordering:

- Trade lists often require `SELL` before `BUY`, then `instrument_id` ascending inside each action.
- BUY-only packages often require `instrument_id` ascending.

## Equity Correlation SOP

Use this for international equity concentration and diversification reviews.

### Data Preparation

1. Use the requested index ids from the payload/template. Do not add extra indices unless the schema requests candidates from a separate allowed set.
2. Fetch levels from `/api/index-levels` or per index from `/api/index-levels/<index_id>`.
3. Sort each level series by date ascending.
4. Filter inclusively to the requested `level_start_date` and `level_end_date`. The default policy window is also available in `/api/policies`.
5. Convert levels to monthly simple returns:

```text
return_t = level_t / level_(t-1) - 1
return_observations = number_of_levels - 1
```

### Pearson Correlations

Compute Pearson correlation for each pair over matching monthly return observations:

```text
corr(x,y) =
  sum((x_i - mean_x) * (y_i - mean_y))
  / sqrt(sum((x_i - mean_x)^2) * sum((y_i - mean_y)^2))
```

The sample/population denominator cancels for correlation when both series share the same observations.

Rules:

- Round correlations to three decimals in final JSON.
- Sort the two ids inside every `pair_id` or `pair` alphabetically.
- For a universe-level review, `highest_positive` is the pair with the largest correlation.
- `lowest` or `best_diversifier` is the pair with the smallest correlation, which may be negative.
- Use policy `correlation_high_threshold` to set concentration breach flags.
- Use policy `correlation_low_threshold` as a guide for low-correlation diversifier language, but still choose the lowest pair when the schema asks for the best diversifier.

### Flags And Actions

- Set the portfolio concentration flag true when a requested concentration pair or the highest pair breaches the high threshold.
- Choose concentration codes from the schema:
  - China/Asia or China/EM high correlation: `CHINA_ASIA_DEPENDENCE`.
  - Developed/global benchmark overlap: `GLOBAL_DEVELOPED_OVERLAP`.
  - No breach: `NO_MATERIAL_CONCENTRATION`.
- Diversification candidates should come only from the template's allowed values. Rank by lower correlation to the concentration driver and by supportive macro/allocation view; output in the required order, often alphabetical.
- Sleeve actions should be schema enums. Typical mapping:
  - `trim` or `monitor` for high-correlation concentration sleeves with weak/underweight signals.
  - `add` for diversifying sleeves with low correlation and positive/overweight signals.
  - `rotate` when moving from a concentration sleeve toward a diversifier.
  - `hedge` for currency sleeve risk or explicit hedge requests.
  - `hold` when neither correlation nor active view justifies a change.

## Active Allocation View SOP

Use this for CIO active allocation refreshes and committee allocation sections.

### Required Joins

1. Fetch opportunity-set taxonomy from `/api/allocation/opportunity-sets`; this gives `asset_class` and validates exact names.
2. Fetch macro signals for the target quarter from `/api/macro-signals?quarter=<target_quarter>`.
3. Fetch prior views from `/api/allocation/prior-views?quarter=<target_quarter>`. The matching row's `view` is the comparison view for its `previous_quarter`.
4. Fetch `/api/policies` for allocation mapping thresholds and view ranks.

### Mapping Signal Score To View

Use policy `allocation_mapping.view_score_thresholds`:

```text
if score >= OW_min: view = "OW"
else if score <= UW_max: view = "UW"
else: view = "N"
```

Use policy `allocation_mapping.conviction_thresholds`:

```text
abs(score) >= HIGH_abs_min      -> "HIGH"
abs(score) >= MEDIUM_abs_min    -> "MEDIUM"
abs(score) < LOW_abs_below      -> "LOW"
```

Use policy `allocation_mapping.view_rank` to compute change against the prior view:

```text
rank(current_view) > rank(prior_view) -> "UP"
rank(current_view) < rank(prior_view) -> "DOWN"
otherwise                            -> "UNCHANGED"
```

Carry through `rationale_code` from the macro signal row. Round `signal_score` to three decimals when the template includes it.

### Allocation Output Ordering

- If the template says to use request order, output rows exactly in the payload's opportunity-set order.
- If it says alphabetical, sort by string.
- Do not sort by asset class, score, or conviction unless the template says so.

### Risk Overlay Selection

Select only from allowed overlay enums. A practical priority order:

1. Credit risk reduction when Corporate High Yield, credit spreads, HY valuation, or watchlist pressure is materially negative: `CREDIT_RISK_REDUCTION` / `trim_credit_beta`.
2. Duration quality tilt when duration support or rate-cut support is positive and credit beta is unattractive: `DURATION_QUALITY_TILT` / `tilt_to_duration_quality`.
3. Equity beta extension when growth/risk signals are broadly positive and no concentration breach dominates: `EQUITY_BETA_EXTENSION` / `add_cyclical_equity_beta`.
4. Currency defensive hedge when currency risk or USD defensive positioning is the main issue: `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge`.
5. No material signal: `NO_OVERLAY` / `hold_policy_weights`.

For overlay `rationale_codes`, use allowed macro rationale codes, remove duplicates, and order by business priority: risk controls first, then supportive offsets, then neutral context.

## Multi-Asset Committee SOP

Use this when a task combines correlation findings with allocation views.

1. Compute the requested correlation summary first using the equity correlation SOP.
2. Compute allocation rows for each requested opportunity set using the active allocation SOP.
3. Link target sleeve actions to both signals:
   - High correlation plus weak active view: trim, rotate, or monitor.
   - Low/negative correlation plus positive active view: add or rotate toward it.
   - Currency sleeve: hedge when the prompt frames it as a defensive offset; otherwise hold or monitor based on the active view.
4. Set `rebalance_trigger` to `correlation_cap_breach` when policy high-threshold concentration is breached; otherwise use the most specific allowed trigger, often `committee_review`.
5. Set `portfolio_risk_concentration_flag` from the computed breach, not from memo language alone.
6. Choose `next_step` according to computed feasibility:
   - `approve_rotation` when actions are clear and constraints pass.
   - `approve_with_monitoring` when the committee can proceed but concentration or mixed signals require monitoring.
   - `defer_pending_risk_review` when material data is missing or signals conflict.
   - `reject_constraint_breach` when the proposed action would violate policy.

## JSON Precision And Validation Checklist

- Dates must be `YYYY-MM-DD`.
- Quantities/notionals in USD millions usually use one decimal when specified.
- Portfolio percentages, duration, yield, and HY reduction often use two decimals.
- Correlations and signal scores often use three decimals.
- Use JSON booleans `true` and `false`, not strings.
- Use exact enum casing: `BUY`, `SELL`, `UW`, `N`, `OW`, `UP`, `DOWN`, `UNCHANGED`, `LOW`, `MEDIUM`, `HIGH`.
- Keep required list lengths exactly as the template states.
- Sort pair ids alphabetically inside each pair even if the role names are ordered separately.
- Do not include stale local quantities, stale as-of dates, unsupported actions, unrequested fields, or explanatory text.
- Validate post-trade metrics from the final trade list one more time before returning JSON.
