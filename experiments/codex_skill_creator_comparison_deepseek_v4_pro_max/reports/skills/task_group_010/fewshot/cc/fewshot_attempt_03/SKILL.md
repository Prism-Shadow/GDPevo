---
name: asteria-portfolio
description: Perform institutional portfolio work for the Asteria Investment Office API environment. Use this skill whenever the user mentions Asteria portfolios, fixed-income credit strategy, equity index correlation reviews, active allocation views, risk rebalancing rotations, or multi-asset committee decisions. Also trigger when the task involves querying portfolio holdings, bond universes, issuer watchlists, index levels, macro signals, or allocation policies through a REST API.
---

# Asteria Portfolio Work

Work with the Asteria Investment Office shared environment to produce structured
JSON outputs for institutional portfolio decisions. Every task follows the same
core pattern: query current API records, reconcile stale local payloads against
them, compute standard metrics, apply policy thresholds, and produce a
template-compliant answer.

## Quickstart

1. **Find the base URL** from the task prompt or environment-access notes.
   `GET /` returns a catalogue page confirming available endpoints.
2. **Read every endpoint relevant to the task** before designing an answer.
   Partial data leads to policy breaches that the template constraint checks will
   flag.
3. **Reconcile input payloads**: local desk requests or meeting memos may carry
   stale marks. The API is the current book of record. When the API contains
   fresher or more complete data, mark `data_precedence` as
   `current_environment_over_stale_payload` (or the analogous field in the
   template).
4. **Produce JSON** that matches every required key, enumerated value, sort
   order, and numeric precision declared in the answer template.

## The Asteria Environment

A REST API at `http://task-env:9010/` provides the shared book of record. Every
task in this domain depends on combinations of these endpoints; read the full
surface description in [references/api_surface.md](references/api_surface.md)
before starting work.

The API is read-only (GET only). No credentials or headers are needed. All
endpoints return JSON.

Key resources:
- **Portfolios**: summaries + per-portfolio holdings at
  `/api/portfolios/{portfolio_id}/holdings`
- **Bonds**: current and candidate bond universe at `/api/instruments/bonds`
- **Issuers**: credit outlooks, watchlist flags, research tags at
  `/api/issuers`
- **Indices**: metadata at `/api/indices`, monthly levels at
  `/api/index-levels/{index_id}`
- **Allocation**: opportunity-set taxonomy at `/api/allocation/opportunity-sets`,
  prior-quarter views at `/api/allocation/prior-views`, macro signal scores at
  `/api/macro-signals`
- **Policies**: constraint thresholds at `/api/policies` (single composite
  object keyed by policy_id; the top-level `policy_id` is the current set
  identifier)
- **Market**: energy commodity signals at `/api/market/energy`
- **Catalog**: all known ids at `/api/catalog`

## Workflow for Every Task

### Step 1: Gather the current state

Read the answer template first. It declares every required field, allowed enum
value, precision, sort order, and required value constant. Let the template
drive what you fetch.

Then fetch from the API:
- Current portfolio holdings (if the task names a portfolio id)
- The full bond universe and issuer records (if the task involves credit
  selection)
- Monthly index levels for every index in the review universe (if correlations
  are needed)
- Prior-quarter views and macro signals (if allocation views are needed)
- The policy object whose policy_id matches the portfolio or task type

### Step 2: Reconcile stale input

Local payloads (desk requests, meeting memos, committee requests) are intake
context. They may contain stale snapshots, outdated worksheet marks, or
preferences from an earlier quarter. The environment API is always the current
source of truth.

Check for conflicts:
- Portfolio market values or holding quantities in a local payload vs holdings
  from `/api/portfolios/{id}/holdings`
- Stale exception-board labels on bonds vs current issuer watchlist and rating
  data from `/api/issuers` and `/api/instruments/bonds`
- Outdated allocation views or signal scores in local notes vs current
  `/api/macro-signals` and `/api/allocation/prior-views`

When the API record contradicts a local mark, prefer the API. Record that
decision in the output's data-precedence or lineage fields.

### Step 3: Compute standard metrics

Use the computation patterns described below. Do not guess; compute exactly.

### Step 4: Apply policy thresholds

Every constraint check (HY cap, duration band, correlation thresholds,
view-score thresholds, conviction thresholds) comes from a policy object fetched
from `/api/policies`. Never hardcode a threshold. Read the policy for the
portfolio's `constraint_policy_id` (shown in `/api/portfolios`).

### Step 5: Produce the answer JSON

The answer template is the contract. Verify:
- Every required top-level key is present
- Every enum field uses an allowed value
- Lists are in the declared sort order
- Numeric fields use the declared precision
- Required constant values (e.g., `portfolio_id`, `task_id`) match the template

## Computation Patterns

### Portfolio Metrics (Credit Portfolios)

Given a set of holdings (each with instrument_id, quantity_usd_m) plus proposed
trades:

**Market value after trades**: sum of all holding quantities (after adding buys
and removing sells).

**HY allocation percent**: total market value of holdings whose rating_bucket
(from the bond universe) is `"HY"`, divided by total market value, times 100.

**Weighted modified duration**: sum over each holding of (quantity x
modified_duration_years from bond data), divided by total market value.

**Weighted yield to maturity**: sum over each holding of (quantity x
yield_to_maturity_pct from bond data), divided by total market value.

**HY reduction (percentage points)**: pre-trade HY% minus post-trade HY%.

**Issuer concentration**: for each issuer, sum quantities across all holdings
from that issuer, divide by total market value, times 100. Compare against the
`issuer_concentration_limit_pct` from the policy.

**Subsector diversification**: count distinct subsectors across selected/holding
bonds. Compare against `subsector_min_count_for_diversified` from the policy.

**Watchlist exposure**: sum quantities for holdings whose issuer has
`watchlist: true` in `/api/issuers`.

Always use the bond universe endpoint (not the holdings record) for rating,
duration, YTM, sector, subsector, and energy_linked data because holdings
records may not carry the full security master fields.

### Pearson Correlation from Monthly Index Levels

When computing correlations between equity indices:

1. Fetch level data from `/api/index-levels/{index_id}` for the window specified
   in the task or policy.
2. Sort levels by date ascending.
3. Compute monthly simple returns: `r_t = (level_t / level_{t-1}) - 1.0`
4. The number of return observations is one fewer than the number of level
   observations.
5. For each pair of indices, compute the Pearson correlation on the aligned
   return series using the standard formula (covariance divided by product of
   standard deviations).
6. Round to three decimal places.
7. Pair ids must be sorted alphabetically within each pair.

Use the policy's `correlation_high_threshold` and `correlation_low_threshold`
to classify concentration risk (pairs above the high threshold) and
diversification candidates (pairs below the low threshold).

### Allocation View Determination

For each opportunity set in the task's focus list:

1. Fetch the target-quarter macro signal from `/api/macro-signals`. Filter by
   `opportunity_set` and `quarter`.
2. Fetch the prior-quarter view from `/api/allocation/prior-views`. Filter by
   `opportunity_set` and `previous_quarter` matching the prior quarter.
3. Map the signal `score` to a view using the policy in `/api/policies`:
   - `score >= OW_min` maps to `"OW"`
   - `score <= UW_max` maps to `"UW"`
   - Between `neutral_between[0]` and `neutral_between[1]` maps to `"N"`
4. Determine change: compare the new view to the prior view. If different,
   `"UP"` or `"DOWN"` depending on direction; if same, `"UNCHANGED"`.
5. Determine conviction from the absolute signal score using
   `conviction_thresholds`:
   - `abs(score) >= HIGH_abs_min` maps to `"HIGH"`
   - `abs(score) < LOW_abs_below` maps to `"LOW"`
   - Otherwise maps to `"MEDIUM"`
6. Use the `rationale_code` from the macro signal record directly.
7. Use the top-level `policy_id` from `/api/policies` as the policy identifier.

### Risk Overlay Selection

When the task requires a single portfolio-level risk overlay:

- If duration-oriented views (U.S. Treasuries, German Bunds) are OW and credit
  views (Corporate HY) are UW, prefer `DURATION_QUALITY_TILT`.
- If HY is UW with negative score and EM/China signals point to dependence risk,
  lift those rationale codes into the overlay.
- If HY is OW with positive score and no concentration flags, `NO_OVERLAY` may
  apply.
- The overlay's `primary_action` field must match the chosen `overlay_code`
  logically.

### Credit Candidate Screening

When selecting bonds for a buy trade or rotation:

1. Filter the bond universe to `candidate: true`.
2. For energy-linked tasks, further filter to `energy_linked: true`.
3. Cross-reference each candidate's `issuer_id` with `/api/issuers`:
   - Exclude `watchlist: true` issuers.
   - Prefer issuers with positive or stable credit outlook.
4. Check the bond's `rating_bucket` against the portfolio's HY constraint:
   - IG bonds are always safe buys.
   - HY bonds are acceptable only when post-trade HY% remains within the policy
     cap.
5. Prefer bonds whose `recommended_theme_tags` align with the task's preferred
   exposures or the current market signals from `/api/market/energy` (or macro
   signals).
6. Ensure issuer and subsector diversification constraints are met after adding
   the selected bonds.

### Sleeve Actions (Equity Correlation + Allocation Tasks)

When linking correlation findings with allocation views to produce sleeve
actions:

- **trim**: apply to sleeves with high concentration correlation, China/Asia
  dependence flag, or a UW allocation view with negative signal score.
- **add**: apply to diversification candidates that also carry an OW allocation
  view with positive signal score.
- **hedge**: apply to USD when the signal score is negative and the prior view
  was OW, suggesting a move to neutral.
- **hold**: apply when the view is N and no concentration or diversification
  signal exists.
- **monitor**: apply when a sleeve has borderline metrics but no clear action.

## Template Compliance Rules

These rules apply to every task's JSON output:

1. **Required string constants**: fields like `portfolio_id` or `task_id` that
   the template declares with a `required_value` must carry that exact string.
2. **Enum fields**: use only values listed in the template's `allowed_values`.
3. **List sort order**: sort as declared (ascending alphabetical, ascending by
   instrument_id, SELL before BUY then ascending, etc.).
4. **Numeric precision**: round to the number of decimals declared (e.g., 2 for
   percentage points, 3 for correlations, 1 for quantities in USD millions).
5. **Required keys**: every key listed in `required_top_level_keys` must be
   present. Every key in `required_keys` within a nested object must be present.
6. **List lengths**: when a template declares a `length` or `required_length`,
   the output list must have exactly that many items.
7. **Return only JSON**: unless the prompt explicitly asks for commentary, the
   output is the JSON object and nothing else.
