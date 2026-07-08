---
name: task-group-010-fewshot-attempt-01
description: Solve PanofyBench task_group_010 Asteria Investment Office input-output tasks that require reading local request/template JSON, using the public Asteria API at http://127.0.0.1:8036 as the current book of record, computing portfolio credit metrics, index correlations, active allocation views, and returning only schema-conforming JSON.
---

# Task Group 010 Input-Output SOP

Use this skill for Asteria Investment Office JSON tasks in `task_group_010`. Produce only the requested JSON object.

## Source Order

1. Read the local `input/prompt.txt`, request payload, and `input/payloads/answer_template.json`.
2. Treat the public API at `http://127.0.0.1:8036` as authoritative for current portfolio, policy, instrument, issuer, index, and signal records.
3. Use local payloads for request scope, portfolio id, requested universe, ordering, stale-context clues, and output-contract details. Override stale local snapshots or notes with API data.
4. Never use environment files, test files, notes, evaluator files, or hidden answers.

## API Checklist

Use `GET /` if endpoint discovery is needed. Common endpoints:

- `/api/catalog`: ids for portfolios, policies, indices, issuers, bonds, and opportunity sets.
- `/api/policies`: policy ids, credit limits, correlation thresholds, and allocation mapping thresholds.
- `/api/portfolios` and `/api/portfolios/<portfolio_id>`: current as-of date, constraints, market value, and holdings.
- `/api/instruments/bonds`: bond security master, candidate flag, rating bucket, duration, yield, sector/subsector, and issuer id.
- `/api/issuers`: issuer watchlist and research status.
- `/api/market/energy`: current energy pitch themes and commodity signals.
- `/api/indices`, `/api/index-levels`, `/api/index-levels/<index_id>`: monthly index metadata and levels.
- `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, `/api/macro-signals`: allocation taxonomy, prior views, signal scores, and rationale codes.

## Template Discipline

- Follow the answer template exactly: required keys, required values, enum spellings, precisions, and item ordering.
- Preserve request-specific ordering unless the template says otherwise. Common patterns: allocation rows in request `focus_opportunity_sets` order; pair ids sorted alphabetically within each pair; trade packages sorted by the template rule.
- Return JSON numbers and booleans as native JSON values, not strings.
- Round only final values to the template precision. JSON may omit trailing zeroes.

## Credit And Bond Tasks

Join portfolio holdings to bonds by `instrument_id`, and bonds to issuers by `issuer_id`.

For BUY selection:

- Start from `candidate: true` instruments unless the prompt explicitly permits otherwise.
- Honor requested action count, total notional, split rules, and allowed actions.
- Avoid issuer watchlist buys when requested or when client-facing suitability matters.
- Use `energy_linked`, `recommended_theme_tags`, issuer research tags, and `/api/market/energy` signals to choose theme-fit candidates.
- Prefer current, eligible, non-watchlist carry that keeps HY allocation and duration inside policy limits; do not chase watchlisted high yield.
- For diversification checks, avoid duplicate selected issuers and use at least the policy minimum distinct selected subsectors when required.

For SELL or rotation selection:

- Sell current holdings that create HY pressure, watchlist exposure, or explicit risk exceptions.
- Fund buys with current eligible candidates that restore duration and reduce HY/watchlist pressure.
- Keep total buy/sell quantities balanced when the prompt asks for a rotation rather than a net allocation.

Metric formulas:

- Post market value = current market value + buys - sells.
- HY allocation pct = `100 * sum(post quantities whose bond rating_bucket == "HY") / post market value`.
- HY reduction pct points = pre-trade HY allocation pct - post-trade HY allocation pct.
- Weighted duration = `sum(post quantity_usd_m * modified_duration_years) / post market value`.
- Weighted yield = `sum(post quantity_usd_m * yield_to_maturity_pct) / post market value`.
- Post watchlist exposure = sum post quantities whose issuer has `watchlist: true`.
- Duration pass uses the portfolio/policy `duration_band_years`; HY pass uses `max_hy_allocation_pct`; target HY reduction uses the applicable policy or local requested minimum.

## Correlation Tasks

Use the requested index universe and review window.

1. Fetch levels from `/api/index-levels` or `/api/index-levels/<index_id>`.
2. Keep levels from `level_start_date` through `level_end_date`, inclusive.
3. Convert to monthly simple returns: `return_t = level_t / level_(t-1) - 1`.
4. `return_observations` is the number of returns, normally one less than the number of monthly levels.
5. Compute standard Pearson correlation on aligned monthly returns.
6. Round correlations to three decimals.

Interpretation patterns:

- `highest_positive` or `highest_concentration` is the largest positive correlation in the requested universe.
- `lowest` or `best_diversifier` is the smallest correlation, often negative.
- Set pair ids in alphabetical index-id order even when the pair role is not alphabetical.
- Use `/api/policies` correlation thresholds. A concentration flag is true when a relevant concentration pair exceeds the high threshold.
- Use `CHINA_ASIA_DEPENDENCE` when China, EM, or Asia beta sleeves show high dependence; use diversifier actions for structurally lower-correlation sleeves such as ex-China or Latin America only when supported by the computed correlations and template allowed values.

## Allocation View Tasks

Build each allocation row from current API records:

1. Get asset class from `/api/allocation/opportunity-sets`.
2. Get the prior view from `/api/allocation/prior-views` for the target quarter; its `view` is the prior-quarter view for comparison.
3. Get current score and `rationale_code` from `/api/macro-signals` for the target quarter.
4. Apply `/api/policies.allocation_mapping.view_score_thresholds`:
   - `score >= OW_min` -> `OW`
   - `score <= UW_max` -> `UW`
   - otherwise -> `N`
5. Apply conviction thresholds to `abs(score)`:
   - `>= HIGH_abs_min` -> `HIGH`
   - `>= MEDIUM_abs_min` -> `MEDIUM`
   - otherwise -> `LOW`
6. Compute `change` with `view_rank`: current rank greater than prior -> `UP`, lower -> `DOWN`, equal -> `UNCHANGED`.

Risk overlay conventions:

- Prefer `DURATION_QUALITY_TILT` / `tilt_to_duration_quality` when duration support combines with credit or China-dependence risk.
- Use `CREDIT_RISK_REDUCTION` / `trim_credit_beta` for dominant HY or spread-risk pressure.
- Use `CURRENCY_DEFENSIVE_HEDGE` / `add_currency_hedge` for dominant currency-defensive needs.
- Use `NO_OVERLAY` / `hold_policy_weights` only when no material risk theme is present.
- Order overlay rationale codes by business priority, not alphabetically.

## Enum And Output Pitfalls

- Use enum strings exactly as the template lists them, including case: `UW`, `N`, `OW`, `UP`, `DOWN`, `UNCHANGED`, `LOW`, `MEDIUM`, `HIGH`.
- Do not invent rationale codes, sleeve actions, target segments, pitch themes, trigger codes, or next-step values.
- Use `current_environment_over_stale_payload` when a template asks for data precedence and the local payload conflicts with API records.
- For trade sorting, obey the template even if it differs from alphabetical action order.
- Include no prose, Markdown, explanations, or extra keys outside the final JSON.
