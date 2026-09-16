---
name: pho-audit
description: >
  Public Health Observatory algorithmic audit execution using the PHO read-only
  web API. Provides the complete reusable method catalog, data-resolution
  protocol, statistical module specifications (fixed-effects, ridge/elastic-net
  CV, wild-cluster bootstrap, grouped conformal calibration, trajectory PCA,
  source perturbation, GMM mediation, sensitivity surfaces, and controlled
  decision gates), plus the protocol override and contract-resolution system.
  Use when a future request references a registered PHO protocol_id, an
  answer_template.json contract, or an analysis_request.json with a
  geography_scope, study years, audit modules, and robustness gates; or when
  the task involves accessing the PHO portal endpoint catalog, resolving
  publication records by revision precedence, constructing balanced-cohort
  panels, or running any combination of the registered statistical audit
  modules against PHO evidence.
---

# PHO Algorithmic Audit Skill

Execute registered Public Health Observatory algorithmic audits from an
`analysis_request.json` contract through the PHO read-only web portal.

## Quick start

1. Read the analysis request and answer template.
2. Resolve every `TASK_ENV_BASE_URL` or explicit URL to the PHO portal root.
3. Fetch `/catalog` and relevant geography listings.
4. For each requested dataset and measure, fetch data using the request's
   filter, value-type, and release-status specifications.
5. Select the single best record per entity-time-measure key using **revision,
   then release timestamp, then record-id** precedence (descending).
6. Construct the requested cohorts from completeness predicates.
7. Execute each audit module in the declared order, following its exact
   reusable method profile (see [references/statistical_modules.md](references/statistical_modules.md)).
8. Apply the protocol override system when a protocol registry record is
   present (see [references/protocol_system.md](references/protocol_system.md)).
9. Evaluate every robustness gate on unrounded values and apply the
   controlled decision rule.
10. Return one JSON object matching the answer template exactly.

## Portal API

See [references/api_endpoints.md](references/api_endpoints.md) for the full
endpoint catalog, query-parameter conventions, and response shapes.

The PHO portal is a read-only HTTP REST API. No credentials are required.
All data endpoints return JSON arrays. Key endpoints:

- `GET /` - Portal root
- `GET /catalog` - Full dataset, measure, and geography catalog
- `GET /geographies/states` - U.S. state code listing
- `GET /geographies/counties` - U.S. county listing
- `GET /geographies/countries` - Country listing
- `GET /data/state-health` - State-level health indicators
- `GET /data/state-socioeconomic` - State-level socioeconomic data
- `GET /data/county-health` - County-level health indicators
- `GET /data/county-socioeconomic` - County-level socioeconomic data
- `GET /data/country-indicators` - Country-level burden and outcome indicators
- `GET /data/revisions` - Revision event log
- `GET /methodology` - Methodology documentation
- `GET /download` - Bulk data download

## Data resolution

See [references/data_resolution.md](references/data_resolution.md) for the
complete record-selection, filtering, revision-precedence, and cohort-
construction rules.

### Record selection precedence

For every entity-time-measure key, choose exactly one publication record
using this ordered comparison, preferring the greater value at each step:

1. Highest `revision`
2. Latest `released_at` timestamp
3. Lowest `observation_id` (health) or `record_id` (socioeconomic)

### Filtering

Filter records by the effective request's declared fields:
- `release_status` (typically `FINAL`)
- `value_type` (e.g., `AGE_ADJUSTED`, `CRUDE`)
- `source_type` (e.g., `DIRECT_SURVEY`, `COUNTY_ROLLUP`)
- Geographic constraints (state codes, county FIPS, ISO3 codes)

### Validity rules

- Suppressed, invalid (`INVALID_SCALE`, `INVALID`), withdrawn, blank, or
  null analytic values count as publication evidence but are **unavailable**
  for analysis.
- Never zero-fill missing values.
- Quality-flag exclusions apply after record selection.

### Cohort construction

Construct every requested cohort by intersecting complete-case entities
over the effective time periods using the effective completeness predicates.
Preserve declared entity order (typically ASCII-ordered state codes or FIPS).

## Protocol resolution

See [references/protocol_system.md](references/protocol_system.md) for the
full override-resolution and contract-merging specification.

When the analysis request carries a `protocol_id`, match its case-sensitive
value against the protocol registry record's portable protocol profile.
Apply the override system:

- Direct keys bind identically to canonical keys.
- `<section>_overrides` keys target canonical `<section>` after stripping the
  `_overrides` suffix.
- `module_overrides.<module_name>` targets the canonical module of that exact name.
- `reporting_overrides` targets reporting.
- Objects deep-merge by exact key; arrays and scalars replace in full.
- Reject unknown targets, implicit renames, type coercion, and positional
  array patching before any computation.
- Freeze one effective contract and use it consistently across every module.

The protocol profile is **REUSABLE_METHOD_ONLY**: entities, measures, time
coordinates, random seeds, hyperparameter grids, business cutoffs, and output
vocabulary bind exclusively from the effective future request.

## Statistical modules

See [references/statistical_modules.md](references/statistical_modules.md)
for the complete reusable method catalog. Every module specification is a
deterministic, reproducible, fully-specified algorithm. Key families:

### State-level modules (protocol: `PHO_STATE_*`)

1. **Release resolution and cohorts** - Filter, select, count, and construct
   balanced/broad/strict cohorts.
2. **Delete-cluster fixed effects** - Double-demeaned FE OLS with delete-one
   jackknife, bias correction, and cluster-robust inference.
3. **Nested ridge/elastic-net division CV** - Leave-one-division-out nested
   cross-validation with training-only standardization and coordinate-
   descent solvers.
4. **Wild cluster bootstrap** - PCG32/xorshift32 restricted-null wild
   cluster bootstrap-t with CR1 studentization.
5. **Grouped split conformal** - Leave-one-group-out split conformal
   prediction with absolute-residual calibration.
6. **Trajectory PCA clustering** - Covariance PCA with Jacobi eigendecomposition,
   deterministic k-means, and leave-period-out adjusted Rand stability.
7. **Source year/group perturbation** - Exhaustive time-subset or source-group
   deletion with Shapley attribution.
8. **Controlled decision** - Ordered gate evaluation with precedence.

### County-level modules (protocol: `PHO_COUNTY_*`)

1. **Publication and linked cohorts** - County-level resolution with RUCC
   indicators.
2. **Primary mediation models / Difference GMM** - Two-step linear GMM
   with state-cluster sandwich, stacked indirect effects, and delete-state
   diagnostics.
3. **Nested state/block ridge/elastic-net** - State-blocked nested
   cross-validation with training-only moments.
4. **Wild cluster bootstrap (paired equations)** - Restricted-null state-
   clustered bootstrap-t with coordinated PRNG draws.
5. **Grouped split / cross-fold conformal** - State-grouped conformal
   calibration with RUCC-band and decile diagnostics.
6. **Partial-R2 sensitivity surface** - Mediation confounding sensitivity
   with equal-strength tipping point.
7. **County/state trajectory PCA** - Variable-major county trajectory PCA
   with deterministic k-means and leave-state/leave-year stability.
8. **Source group perturbation** - No-retune source-group deletion with
   deterioration ranking.

### Country-level modules (protocol: `PHO_CBR_*`)

1. **Reconciliation** - Label-to-ISO3 resolution with alias counting.
2. **Quality audit** - Revision event classification, scale-break anomaly
   detection, missing/imputed cell counting.
3. **PCA** - Burden-indicator covariance PCA with top-loading extraction.
4. **Clustering** - Silhouette selection across candidate k, burden-segment
   labeling.
5. **Panel model** - Region-fixed-effects panel regression of outcome on
   PC1 burden.
6. **Advisory** - Controlled policy advisory from panel evidence.

## Decision rules

Every audit concludes with a controlled decision. Complete all modules first,
evaluate every business predicate on **unrounded** computed values, and
apply the effective request's decision mapping in the declared precedence
order. Gate predicates are boolean conditions on specific module outputs
(e.g., "p-value <= 0.05", "coverage >= 0.80", "ARI >= 0.55"). The first
unsatisfied gate determines the conclusion string from the request's
enumerated mapping.

## Precision and reporting

- Compute everything in double precision; report non-integer values to the
  declared number of decimal places (typically 4 or 6).
- Integers, counts, seeds, PRNG states, ranks, fold indices, and booleans
  use natural JSON types.
- Preserve every declared array order; never independently sort an aligned
  result vector.
- Never emit `NaN` or `Infinity`; use `null` only when a statistic is
  mathematically undefined.
- Use uppercase state codes and ISO3 values.
- Return exactly one JSON object matching the answer template's top-level
  keys, with no narrative outside it.

## General execution discipline

- Resolve the whole effective contract before any data access, random draw,
  fit, aggregation, or decision.
- Read all evidence from the portal; do not fabricate or carry forward
  task-specific values from other invocations.
- When a protocol registry record exists in the answer, place it in the
  output as an optional solved-answer provenance record but bind all
  instance-specific content only from the effective future request.
- Implement every algorithm from its reusable specification; do not import
  black-box library routines that violate the declared steps.
- For PRNG sequences, implement the exact generator (PCG32 or xorshift32)
  as specified, maintain a single continuous stream, and record checkpoints
  after the specified replicate completes without resetting the stream.
