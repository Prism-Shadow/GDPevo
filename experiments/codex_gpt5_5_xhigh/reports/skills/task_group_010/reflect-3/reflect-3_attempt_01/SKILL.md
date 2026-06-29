# Asteria Investment Office JSON Workflow

Use this skill when solving Asteria Investment Office tasks that require a strict JSON answer built from the shared environment service plus a local prompt/template packet.

## Source Discipline

- Treat the shared Asteria environment as the book of record. Local request payloads often contain stale worksheet dates, stale quantities, or desk preferences that must be reconciled to current API records.
- Read the local prompt and `answer_template.json` first. Use it as the contract for required keys, enum values, list order, numeric precision, and required portfolio/task identifiers.
- Use only current input files and the live environment API. Do not rely on prior run outputs, hidden answers, or generated notes.
- Prefer the most specific API record for facts:
  - Portfolio date, holdings, market value, and portfolio policy: `/api/portfolios/<portfolio_id>`.
  - Policy thresholds and mapping rules: `/api/policies`.
  - Bond terms and candidate flags: `/api/instruments/bonds`.
  - Issuer watchlist status: `/api/issuers`.
  - Index metadata and levels: `/api/indices`, `/api/index-levels`, or `/api/index-levels/<index_id>`.
  - Allocation taxonomy, prior views, and signals: `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`.
- Use equality filters when helpful, such as `?quarter=Q2_2026`, `?candidate=true`, or `?rating_bucket=HY`.

## JSON Contract Habits

- Return only the JSON object requested by the prompt. Do not add prose outside JSON.
- Copy enum strings exactly, including casing, spaces, underscores, and punctuation.
- Preserve required list ordering from the template. Common patterns:
  - Instrument pairs sorted alphabetically within `pair` or `pair_id`.
  - Index sets sorted alphabetically when requested.
  - Allocation rows in the local request's focus order, not display order unless the template says otherwise.
  - Trade rotations sorted by the template rule; when specified, `SELL` rows come before `BUY` rows, then sort instrument ids ascending within each action.
- Round numeric outputs to the precision declared in the template. Keep trailing zero-friendly values as numbers, not strings.
- Use the current portfolio/API `as_of_date` for portfolio-based tasks. For allocation lineage, if the template asks for a generic `policy_id`, prefer the top-level policy set id from `/api/policies` when present; use a subpolicy id only when the field explicitly asks for that subpolicy.

## Credit And Bond Workflows

- Join portfolio holdings to bond security-master records by `instrument_id`, then join to issuers by `issuer_id` for watchlist checks.
- Current market value after an equal-funded rotation is normally unchanged. New-money BUY packages increase market value by the total BUY notional.
- Weighted duration:
  - `sum(quantity_usd_m * modified_duration_years) / total_market_value_usd_m`.
- Weighted yield to maturity:
  - `sum(quantity_usd_m * yield_to_maturity_pct) / total_market_value_usd_m`.
- HY allocation percentage:
  - `100 * sum(quantity_usd_m where rating_bucket == "HY") / total_market_value_usd_m`.
- HY reduction in percentage points:
  - `pre_trade_hy_allocation_pct - post_trade_hy_allocation_pct`.
- Watchlist exposure:
  - Sum exposure whose issuer has `watchlist: true`, not just bonds with watchlist-like theme tags.
- For BUY-only energy packages, first filter to current candidates, energy-linked bonds when required, and non-watchlist issuers when a watchlist-avoidance check exists.
- Do not chase headline yield if it creates a client-facing or watchlist problem. High carry must still satisfy HY caps, duration bands, issuer/subsector diversification checks, and the stated pitch theme.
- For risk-reduction rotations, avoid over-trading. Size sells to clear watchlist exposure, meet stated HY reduction/cap targets, and preserve duration/carry with eligible non-watchlist buys.

## Correlation Reviews

- Use monthly simple returns from consecutive index levels:
  - `return_t = level_t / level_(t-1) - 1`.
- The number of return observations is `number_of_levels - 1`.
- Pearson correlation should be computed on the aligned monthly return vectors, not on index levels.
- For an "extreme pairs" request, calculate every pair in the requested index universe unless the prompt explicitly narrows the set.
- `highest_positive` is the largest correlation value. `lowest` or `best_diversifier` is the smallest value, which may be negative.
- Apply the correlation high threshold from policy, commonly for concentration flags. A materially high China/Asia or China/EM relationship should set the concentration flag when it exceeds the threshold.
- For diversification candidates, prefer genuinely low or negative-correlation sleeves over merely less-correlated high-beta substitutes.

## Allocation View Mapping

- Use the opportunity-set taxonomy to fill `asset_class`.
- Use macro signals for the requested quarter to derive active views and rationale codes.
- Typical mapping from `/api/policies`:
  - `score >= OW_min` -> `OW`.
  - `score <= UW_max` -> `UW`.
  - Otherwise -> `N`.
- Conviction is based on absolute signal score:
  - `abs(score) >= HIGH_abs_min` -> `HIGH`.
  - `abs(score) >= MEDIUM_abs_min` -> `MEDIUM`.
  - Below medium threshold -> `LOW`.
- Compare the active view with the prior-quarter view using policy `view_rank`:
  - Higher rank -> `UP`.
  - Lower rank -> `DOWN`.
  - Same rank -> `UNCHANGED`.
- Use the macro signal's `rationale_code` exactly. Do not invent a nearby enum when the signal already provides one.

## Committee And Action Conventions

- When linking correlation findings to allocation views, let the data drive actions:
  - High concentration plus an underweight view usually supports `trim` or `rotate`.
  - Positive high-conviction diversifiers usually support `add`.
  - A neutralized defensive currency sleeve may still support `hedge` when the committee packet highlights stale defensive positioning.
- If a rebalance is justified by a correlation breach but still needs oversight rather than unconditional implementation, prefer an approval-with-monitoring style next step over a plain approval.
- Use `correlation_cap_breach` when the correlation threshold is the binding reason for committee action. Use credit or duration triggers only when those portfolio constraints are the binding issue.

## Exclusion And Pitfall Checklist

- Do not use stale local quantities, stale local dates, or stale desk labels when current API records disagree.
- Do not buy watchlist issuers when the task asks for watchlist avoidance, even if the bond has high carry.
- Do not use candidate bonds outside the requested universe, sector, or energy-linked requirement.
- Do not compute correlations on levels, daily assumptions, or unmatched date windows.
- Do not sort rows by intuition when the template gives an order.
- Do not output enum synonyms such as `overweight`, `underweight`, `buy`, or `reduce` when the template requires `OW`, `UW`, `BUY`, `trim`, etc.
- Do not describe any training-time feedback or validation process in final task answers.
