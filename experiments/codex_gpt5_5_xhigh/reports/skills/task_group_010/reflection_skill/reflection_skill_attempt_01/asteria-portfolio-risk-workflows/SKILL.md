---
name: asteria-portfolio-risk-workflows
description: Solve Asteria Investment Office portfolio-risk, credit-rotation, correlation-review, and active-allocation JSON tasks using the public Asteria API. Use when prompts mention Asteria portfolios, current shared environment records, bond or issuer constraints, monthly index-level correlations, macro-signal allocation views, committee decisions, or stale local payloads that must be reconciled to current API data.
---

# Asteria Portfolio Risk Workflows

## Source Discipline

Use the public API at `http://127.0.0.1:8036` as the book of record. Treat local payloads as request context, stale preferences, and output schemas unless the prompt explicitly says otherwise.

Never read environment implementation folders, notes, eval artifacts, or test answer files. Fetch only the task input payloads plus public API records needed for the calculation.

Start with:

```text
GET /
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

Raw JSON clients receive arrays directly for many endpoints. PowerShell may display those arrays under a synthetic `value` wrapper; do not assume the wrapper exists in other clients.

## Credit Metrics

Use current portfolio holdings and current bond master fields:

```text
post_market_value = current_market_value + buys - sells
hy_allocation_pct = 100 * sum(quantity for rating_bucket == "HY") / post_market_value
weighted_duration = sum(quantity * modified_duration_years) / post_market_value
weighted_ytm = sum(quantity * yield_to_maturity_pct) / post_market_value
watchlist_exposure = sum(quantity where issuer.watchlist == true)
hy_reduction_pct_points = pre_trade_hy_allocation_pct - post_trade_hy_allocation_pct
```

Round only at output precision. Use current quantities from `/api/portfolios/<id>`, not quantities in stale desk packets.

Join bonds to issuers by `issuer_id` for watchlist checks. A watchlist issuer makes all its bonds watchlist-sensitive, even if the bond payload only has attractive carry tags.

## Energy Credit Trades

For energy-credit BUY packages:

- Filter candidate bonds with `candidate: true`, `energy_linked: true`, and non-watchlist issuers.
- Obey exact ticket count and explicit split rules. If the prompt says two tickets totaling USD 8.0 million split evenly, use two USD 4.0 million BUYs.
- Keep HY allocation under the credit policy cap and duration inside the policy band after the trade.
- Make selected issuers and selected subsectors distinct when the schema asks for issuer/subsector diversification.
- Prefer a client-facing LNG/gas anchor plus a distinct non-watchlist carry diversifier over simply maximizing HY yield. Positive LNG signals favor BlueGas-style IG LNG exposure for `lng_export_tailwind`; avoid adding extra HY LNG if it pushes the package close to the HY cap or duplicates an existing HY LNG issuer.
- Use `target_segment` from the request context, commonly `multi_asset_income`, and set `data_precedence` to `current_environment_over_stale_payload` when API records override old worksheets.

Common pitfall: chasing the highest non-watchlist HY carry can pass numeric caps but miss the investment-office preference for a cleaner client-facing LNG/gas income pitch.

## Fixed-Income Risk Rotations

For credit-risk reduction rotations:

- Sell current watchlist HY exposure first.
- Sell only enough additional HY pressure to pass the HY cap and target HY reduction while preserving carry. Do not zero all HY exposure unless the prompt requires it.
- Exclude watchlist issuers from buys, even if a shortlisted bond has high carry.
- Buy eligible IG candidates that preserve duration; size the buys according to risk purpose and desk ranking when no equal split is specified. Do not force equal-funded buys unless the prompt explicitly asks for equal tickets.
- Favor longer-duration IG ballast for larger buy sizes when the memo warns about duration shortfall. Use smaller allocations to overlapping thematic credits when diversification or cross-sleeve exposure matters.
- Sort rotation trades as the schema requires, often SELL before BUY, then `instrument_id` ascending within each action.

For Lumen-style packets, the transferable pattern is: sell the watchlist bond plus the smallest additional HY pressure point needed to bring HY below the cap; retain better non-watchlist carry when possible; fund all current non-watchlist IG shortlist candidates with larger weight to the duration-ballast candidate.

Use `risk_note_code: "watchlist_concentration"` when the rotation is primarily justified by clearing watchlist exposure while also meeting HY and duration constraints.

## Correlation Reviews

Use monthly simple returns from consecutive API levels:

```text
return_t = level_t / level_(t-1) - 1
return_observations = number_of_levels - 1
correlation = Pearson(return_series_a, return_series_b)
```

Compute pairwise correlations over the exact requested level window. Round correlations to three decimals. Pair ids must be sorted by index id within each pair.

Use policy thresholds from `/api/policies.correlation`:

- `high_threshold_breached` is true if any relevant concentration pair exceeds `correlation_high_threshold`.
- `china_asia_dependence_flag` is true when China, EM, or Asia Pacific ex Japan relationships breach the high threshold.
- Use `primary_code: "CHINA_ASIA_DEPENDENCE"` when China/EM/Asia dependence is the main issue.
- Use the most positive pair for `highest_positive` or `highest_concentration`; use the lowest correlation, including negative correlations, for `lowest` or `best_diversifier`.

Diversification candidates should reflect both structure and correlation: include EM ex China when the issue is China dependence, and include Latin America when it is the strongest low-correlation diversifier. India can be an offset in allocation work, but its correlations may still be high.

For sleeve actions under a China-dependence review, prefer a compact action set such as trimming China and adding Latin America when only two actions are requested.

## Allocation Views

Build active views from `/api/macro-signals`, `/api/allocation/prior-views`, `/api/allocation/opportunity-sets`, and `/api/policies`.

Use the top-level policy set id from `/api/policies.policy_id` for lineage fields unless the schema explicitly asks for a nested policy id.

Map signal scores using `/api/policies.allocation_mapping`:

```text
view = "OW" if score >= OW_min
view = "UW" if score <= UW_max
view = "N" otherwise

conviction = "HIGH" if abs(score) >= HIGH_abs_min
conviction = "MEDIUM" if abs(score) >= MEDIUM_abs_min
conviction = "LOW" otherwise

change = compare rank(current_view) to rank(prior_view)
```

Take `asset_class` from opportunity-set taxonomy. Take `rationale_code` directly from the macro signal. Preserve the request's opportunity-set order when the schema requires it.

For Q2-style risk overlays, prefer:

```json
{
  "overlay_code": "DURATION_QUALITY_TILT",
  "primary_action": "tilt_to_duration_quality",
  "rationale_codes": [
    "DURATION_SUPPORT",
    "HY_VALUATION_RISK",
    "CHINA_DEPENDENCE"
  ]
}
```

Use that priority order when duration support, HY valuation risk, and China dependence all appear in the focused views. Do not drop China dependence from the overlay when EM is underweight because of China drag.

## Multi-Asset Committee Decisions

Combine correlation findings with allocation views:

- Use the same correlation calculation rules as equity reviews.
- Map target sleeve actions from current views: `UW -> trim`, `OW -> add`.
- For USD or currency sleeves, a prior OW that moves to neutral with stale local notes about defensive USD should generally become `action: "hedge"`, not `hold`.
- Use `rebalance_trigger: "correlation_cap_breach"` when a concentration pair is above the high threshold.
- Set `portfolio_risk_concentration_flag: true` when the concentration pair breaches threshold.
- Prefer `next_step: "approve_with_monitoring"` when actions are valid but the decision remains a committee-monitored correlation breach.

## Output Hygiene

Return only the JSON object requested by the task. Match schema key names exactly. Preserve required ordering rules for lists. Use numeric precision exactly as declared in the input template.

Before finalizing, recheck these high-risk fields:

- Current API `as_of_date`, not stale payload dates.
- Top-level `POLICY_SET_...` id for allocation lineage.
- Non-watchlist status through issuer records, not bond labels alone.
- Equal ticket splits only when the prompt explicitly says equal.
- Correlation observations equal levels minus one.
- USD neutral-from-OW committee action usually `hedge`.
