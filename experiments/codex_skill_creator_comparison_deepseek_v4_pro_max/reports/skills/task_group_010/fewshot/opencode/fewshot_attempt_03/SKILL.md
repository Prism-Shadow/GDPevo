---
name: asteria-portfolio-analyst
description: Complete Asteria Investment Office portfolio-analysis tasks using the shared API environment at task-env:9010. Use when the assignment mentions Asteria, any PF-* portfolio identifier, energy-credit trades, fixed-income rotation, international equity correlation, active allocation views, investment committee memos, or any institutional portfolio risk work. Do not attempt these tasks with local-only reasoning — the environment holds the current book of record and policy thresholds.
---

# Asteria Investment Office Portfolio Analyst

Use this skill for every Asteria Investment Office portfolio task. These
assignments follow a repeatable pattern: query the shared environment for the
current book of record, derive an answer from that data, and produce a strictly
structured JSON response. The skill is organized around three analytical
families, a universal data-precedence rule, and a common template-compliance
discipline.

---

## Data Precedence (Universal Rule)

**Always prefer the current environment over stale local payloads.**

The shared Asteria environment at `http://task-env:9010/` is the book of
record. Local payload files (JSON objects included with the task prompt) serve
only as **intake context**: they provide the request parameters, the task
identity (portfolio id, target quarter, review window dates, desk preferences),
and sometimes stale snapshots or worksheet notes. Those local records may be
outdated. Whenever the prompt or payload references a data point that the
environment can source (holdings, bond attributes, issuer status,
index levels, macro signals, prior views, policy thresholds), reach for the
environment and use its current values.

When stale data and current environment data disagree, log the conflict by
setting the `data_precedence` field (or equivalent lineage field) to
`current_environment_over_stale_payload`. The one exception is when the
template itself enumerates the allowed values and `data_precedence` is not
among them — in that case just document the choice in a comment-style field if
available, or let the current data silently win.

---

## Environment Entry Points

Every endpoint is a GET under `http://task-env:9010/`. No authentication is
required. The environment exposes ten endpoints covering five data domains.
See [references/api_catalog.md](references/api_catalog.md) for the complete
listing with field shapes.

The five domains:

1. **Portfolios** — `/api/portfolios` and `/api/portfolios/{id}/holdings`
2. **Bonds & Issuers** — `/api/instruments/bonds` and `/api/issuers`
3. **Equity Indices** — `/api/indices`, `/api/index-levels`, and `/api/index-levels/{id}`
4. **Allocation Framework** — `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`, and `/api/macro-signals`
5. **Energy Market** — `/api/market/energy`

Policies are served at `/api/policies` as a single JSON object keyed by
policy_id. The same object also holds sub-policy fragments nested under
`allocation_mapping`, `correlation`, `credit_default`, `credit_risk_reduction`,
and `multi_asset*` keys.

---

## Three Analytical Families

Every Asteria task fits one of these families, or a composition of them.

### Family A — Credit & Fixed-Income Rotation

**Relevant tasks**: energy-credit trade proposals, HY reduction rotations,
watchlist cleanup.

**Process**:

1. Read the local payload for task identity (portfolio_id, request parameters,
   stale hints, desk preferences).
2. Fetch `/api/portfolios/{id}/holdings` for current positions.
3. Fetch `/api/instruments/bonds` for the full bond universe — this gives
   rating_bucket (IG/HY), issuer_id, modified_duration_years,
   yield_to_maturity_pct, candidate flag, recommended_theme_tags, sector, subsector.
4. Fetch `/api/issuers` for watchlist status and credit_outlook on every issuer.
5. If the task is energy-linked, fetch `/api/market/energy` for signal
   direction and scores.
6. Fetch `/api/policies` for constraint thresholds (HY cap, duration band,
   issuer concentration limit, subsector diversification minimum).
7. Select instruments that satisfy the task's constraints. Compute post-trade
   metrics using the scripts in [scripts/](scripts/).
8. Produce the JSON answer using the task's answer_template.json.

**Constraint checks common to this family**:
- `hy_cap_pass`: post-trade HY% ≤ max_hy_allocation_pct from the relevant policy
- `duration_band_pass`: post-trade weighted modified duration inside
  [duration_band_years[0], duration_band_years[1]]
- `selected_issuer_diversification_pass`: no single issuer exceeds
  issuer_concentration_limit_pct of post-trade market value
- `selected_subsector_diversification_pass`: selected instruments span at least
  subsector_min_count_for_diversified distinct subsectors
- `watchlist_avoidance_pass`: no BUY ticket hits a watchlisted issuer

The policy to use is the one referenced by the portfolio's
`constraint_policy_id` field from the `/api/portfolios` summary.

### Family B — International Equity Correlation

**Relevant tasks**: correlation reviews, concentration checks, diversification
candidate identification.

**Process**:

1. Read the local payload for the index universe, review window dates, and
   committee focus.
2. Fetch `/api/index-levels/{id}` for every index in the universe. Each
   response contains a `levels` array of `{date, level}` objects.
3. Compute Pearson correlations from monthly simple returns across the
   requested window. Use the script at
   [scripts/pearson_corr.py](scripts/pearson_corr.py) for deterministic
   output. Call it once per index pair needed. If you prefer to compute
   inline, follow the same formula documented in the script header.
4. Identify extreme pairs: highest positive correlation (concentration risk)
   and lowest correlation (best diversifier, which may be negative).
5. Derive concentration flags, diversification candidates, and sleeve actions
   from the correlation matrix and any committee guidance in the payload.
6. Produce the JSON answer using the answer_template.json.

**Correlation computation**:
- Use consecutive monthly index levels from the review window.
- Monthly simple return = (level_current - level_prior) / level_prior.
- Use the Pearson product-moment formula on the paired return series.
- Round to three decimals.
- Pair ids must be sorted alphabetically within each pair.
- The number of return observations is one fewer than the number of levels.

### Family C — Active Allocation Views

**Relevant tasks**: CIO allocation view refresh, committee decision linking.

**Process**:

1. Read the local payload for the focus opportunity sets, target quarter,
   prior quarter, and requested output shape.
2. Fetch `/api/allocation/opportunity-sets` for the taxonomy (asset_class
   mapping).
3. Fetch `/api/allocation/prior-views` for the prior quarter views. Filter to
   rows where `quarter` equals the requested target quarter AND
   `previous_quarter` equals the requested prior quarter — these are the
   current published views that the task is revising.
4. Fetch `/api/macro-signals` for signal scores and rationale codes. Filter to
   the same target quarter.
5. Fetch `/api/policies` for the policy id (the top-level `policy_id` field)
   and the `allocation_mapping` sub-object for threshold logic.
6. For each focus opportunity set, derive the active view, change, conviction,
   and rationale code:

   - **View**: Map the macro-signal score through the allocation_mapping
     thresholds: score ≥ OW_min → `OW`, score ≤ UW_max → `UW`, else → `N`.
   - **Change**: Compare the derived view to the prior view from prior-views.
     If the rank (OW=1, N=0, UW=-1) increased → `UP`, decreased → `DOWN`,
     same → `UNCHANGED`.
   - **Conviction**: |score| ≥ HIGH_abs_min → `HIGH`, |score| ≥ MEDIUM_abs_min
     → `MEDIUM`, else → `LOW`.
   - **Rationale code**: Use the `rationale_code` field from the macro-signal
     record for that opportunity set and quarter.
7. For the risk overlay, select an overlay_code and primary_action that align
   with the dominant signal themes. The rationale_codes field should list the
   highest-priority rationale codes in business-priority order.
8. Produce the JSON answer using the answer_template.json.

---

## Template Compliance

Every Asteria task ships with an `answer_template.json` in the payload
directory. Treat it as the authoritative output contract.

- **Required keys**: Every key listed under `required`, `required_top_level_keys`,
  or `required_keys` must be present with a non-null value.
- **Enum values**: Fields with `allowed_values` must use exactly one of
  those values. Do not invent new codes.
- **Precision**: Numeric fields declare a precision (e.g. `precision: 2` for
  2 decimal places). Round aggressively to that precision with Python's
  `round()` — do not add trailing zeros beyond the declared precision unless
  the template explicitly calls for string formatting.
- **Ordering**: Lists that declare an ordering rule (e.g. "Sort ascending by
  instrument_id") must follow it. Use `sorted()` or equivalent.
- **Required values**: Fields with `required_value` must output exactly that
  string or number. The `as_of_date` field should always use the date from
  the current portfolio/holding records (typically visible as the `as_of_date`
  field on `/api/portfolios` or `/api/portfolios/{id}/holdings`).
- **Length constraints**: Lists with a declared `length` must contain exactly
  that many items.

If a field appears in the template but the answer is truly unknown, use a
null or default value that respects the field's type — never omit a required
key.

---

## Scripts

Two deterministic Python scripts are bundled to avoid floating-point drift
and to make the computation logic transparent to reviewers:

- **[scripts/pearson_corr.py](scripts/pearson_corr.py)** — Pearson
  correlation from two arrays of index levels. Accepts two JSON index-level
  files (the raw API responses) and a window start/end date, outputs the
  correlation to three decimals.
- **[scripts/portfolio_metrics.py](scripts/portfolio_metrics.py)** —
  Post-trade weighted metrics. Accepts JSON arrays of holdings (with
  quantity_usd_m and instrument_id) and bond attributes, outputs market
  value, HY%, duration, YTM.

Use these scripts when the task involves correlation or trade-rotation
metrics. They remove ambiguity about rounding and formula choice.

---

## Reference Files

- **[references/api_catalog.md](references/api_catalog.md)** — Every endpoint
  with example response shapes, so you know what fields to pull without
  guessing.
- **[references/policy_thresholds.md](references/policy_thresholds.md)** —
  Policy structure, constraint thresholds, and how to select the right policy
  for a portfolio.
- **[references/computation_rules.md](references/computation_rules.md)** —
  Detailed formulas for post-trade metrics, view derivation, and correlation.

Read these when you need the exact field name, threshold value, or formula.

---

## Cross-Family Composition

Some tasks (e.g. a committee decision file) combine two families. The most
common composition is Family B (correlation) + Family C (allocation views).
When a task spans families:

1. Execute each family's data-fetch step independently, using the same
   environment as-of date.
2. Cross-reference findings: correlation extremes should inform allocation
   views, and vice versa. For instance, a `CHINA_DEPENDENCE` finding from
   correlation should drive an UW Emerging Markets allocation view.
3. Produce a single unified JSON response that follows the task's
   answer_template.json.

---

## Error Handling

- If an endpoint returns 404 or an unexpected shape, note it and fall back
  to the next-best source (another endpoint, or a local payload if the
  payload explicitly marks that data as current).
- If a bond or issuer referenced in a holding is absent from `/api/bonds` or
  `/api/issuers`, exclude it from the recommendation and flag the gap.
- If the correlation window dates in the local payload differ from the index
  `level_start_date`/`level_end_date` in the API response, use the payload's
  dates for filtering but verify the API covers them. If the API data is
  incomplete for the requested window, report the actual observation count.
- If the answer template requires a field value that cannot be determined,
  use the most reasonable default: `false` for booleans, `0` or `0.0` for
  numbers, empty arrays for lists — but never omit a required key.

---

## Quick Start

When you see an Asteria task:

1. Identify the family (A, B, C, or composite) from the prompt and payload.
2. Read the answer_template.json.
3. Fetch the environment data needed for that family.
4. Run the computation scripts if relevant.
5. Assemble the JSON answer, checking every template constraint.
6. Return only the JSON object (unless the prompt says otherwise).
