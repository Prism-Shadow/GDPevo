---
name: solve-asteria-investment-json
description: Solve Asteria Investment Office portfolio JSON tasks that require combining local request payloads and answer templates with the shared Asteria environment for credit trades, fixed-income risk rotations, equity correlation reviews, active allocation views, and committee decision files.
---

# Asteria Investment JSON Solver

Use this skill when an Asteria task asks for a JSON object from local `input/payloads/` files plus the shared Asteria environment.

## Required Workflow

1. Read the user prompt, every file in `input/payloads/`, and the answer template. Treat the template as the output contract for keys, enums, list ordering, and rounding.
2. Read `environment_access.md` if it is present in the workspace. Use only its read-only GET endpoints. Never call a judge endpoint.
3. Use the Asteria environment as the current book of record for portfolios, holdings, policies, security master data, issuers, market signals, index levels, opportunity sets, prior views, and macro signals.
4. Use local payloads to identify the requested portfolio, dates/windows, index universe, opportunity sets, trade counts/sizes, committee focus, and stale desk preferences. If local marks conflict with current environment records, prefer the environment unless the prompt explicitly says otherwise.
5. Build only the requested JSON. Do not include narrative outside JSON. Round numeric fields to the precision declared in the template and sort lists exactly as instructed there.

## Environment Endpoints

Default base URL is `http://task-env:9010/` when no local access note says otherwise.

Useful GET paths:

- `/api/catalog`
- `/api/policies`
- `/api/portfolios` and `/api/portfolios/{portfolio_id}`
- `/api/portfolios/{portfolio_id}/holdings`
- `/api/instruments/bonds`
- `/api/issuers`
- `/api/market/energy`
- `/api/indices`
- `/api/index-levels` and `/api/index-levels/{index_id}`
- `/api/allocation/opportunity-sets`
- `/api/allocation/prior-views`
- `/api/macro-signals`

## Helper Script

Use [scripts/asteria_helpers.py](scripts/asteria_helpers.py) for mechanical calculations:

```bash
python /work/skill/scripts/asteria_helpers.py correlations --index-ids IDX_A IDX_B IDX_C
python /work/skill/scripts/asteria_helpers.py allocation --quarter TARGET_QUARTER --sets "Opportunity Set A" "Opportunity Set B"
python /work/skill/scripts/asteria_helpers.py bond-candidates --candidate-only --avoid-watchlist --energy-linked
python /work/skill/scripts/asteria_helpers.py credit-metrics --portfolio-id PORTFOLIO_ID --trades-file /tmp/trades.json
```

The script returns JSON summaries. Adapt its output to the answer template; do not include extra fields that the template does not request.

## Correlation Reviews

Compute monthly simple returns from consecutive index levels:

```text
return[t] = level[t] / level[t-1] - 1
```

Use Pearson correlation over the requested level window. With 12 monthly levels there are 11 return observations. Filter levels by the local payload window when supplied; otherwise use the policy correlation window or the full environment level window. Pair ids must be alphabetically sorted inside each pair.

For extreme pairs, choose the highest correlation for concentration and the lowest correlation for diversification. Set concentration flags by comparing relevant pairs to the policy high-correlation threshold. When the prompt or memo names China/Asia/EM dependence, inspect pairs involving China, Asia Pacific ex Japan, EM, EM ex China, India, and broad global indices before assigning concentration codes or sleeve actions.

## Allocation Views

For active allocation rows:

1. Fetch policies, opportunity sets, prior views, and macro signals.
2. Use the local payload's target quarter and opportunity-set order.
3. Join each opportunity set to its macro signal for the target quarter and to the prior view row whose `quarter` is the target quarter.
4. Convert signal score to current view using policy thresholds: score at or above the OW threshold is `OW`, score at or below the UW threshold is `UW`, otherwise `N`.
5. Set conviction from absolute score using policy conviction thresholds.
6. Set change by comparing policy view ranks for current view versus prior view: higher is `UP`, lower is `DOWN`, equal is `UNCHANGED`.
7. Use the macro signal's `rationale_code` and the opportunity-set taxonomy's `asset_class`.

For risk overlays, choose the code/action that matches the strongest material risks after applying the views. Duration-support plus high-yield valuation risk points to a duration-quality tilt; high-yield or watchlist pressure points to credit-risk reduction; broad positive equity signals point to equity beta extension; currency defensive signals point to a hedge; otherwise use no overlay.

## Credit Trade And Risk Tasks

Join portfolio holdings to bonds by `instrument_id` and bonds to issuers by `issuer_id`.

Portfolio metrics are weighted by current or post-trade `quantity_usd_m`:

- total market value: sum quantities
- HY allocation percent: HY quantity divided by total quantity times 100
- weighted duration: sum quantity times `modified_duration_years` divided by total quantity
- weighted yield: sum quantity times `yield_to_maturity_pct` divided by total quantity
- watchlist exposure: quantity whose joined issuer has `watchlist: true`

For BUY packages, filter to current `candidate: true` instruments matching the requested domain, avoid watchlist issuers, satisfy policy HY and duration constraints after the trade, and respect issuer/subsector diversification. Maximize expected carry only after these constraints pass. Use energy market signals and bond theme tags to choose sales positioning.

For risk-reduction rotations, sell current watchlist holdings first, then additional HY pressure points only as needed to meet the requested HY reduction and policy cap. Fund sells with current non-watchlist candidates, generally IG or quality carry, sized to preserve the policy duration band. Verify post-trade HY, duration, HY reduction, watchlist exposure, watchlist sell ids, and buy watchlist avoidance.

## Final Checks

- Use the environment `as_of_date` for lineage fields tied to current records.
- Preserve template-specific list order: payload focus order, alphabetical ids, or action order as requested.
- Populate enum values exactly as declared.
- Use `current_environment_over_stale_payload` when the local payload contains stale dates, old quantities, or stale marks that the environment supersedes.
- Do not copy prior example answers or include task-specific answer records in the output.
