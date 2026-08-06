# Public Health Observatory Algorithmic Audit Skill

## Overview

You are completing a registered algorithmic audit for the Public Health Observatory (PHO). You receive three inputs:

1. **prompt.txt** — the business question and scope
2. **analysis_request.json** — the registered protocol specifying statistical modules, parameters, cohorts, decision rules, and numerical precision
3. **answer_template.json** — the exact JSON output contract with required keys, types, array lengths, and ordering constraints

Your job is to fetch data from the Observatory's read-only web portal, perform every declared computation, and return a single JSON object conforming exactly to the answer template.

## Portal Navigation

The portal is a read-only HTML + CSV data service. The base URL is provided by the task environment (look for `<TASK_ENV_BASE_URL>` or similar in prompt.txt).

### Available datasets

| Dataset | Endpoint | Rows | Key columns |
|---------|----------|------|-------------|
| States | `/geographies/states` or `/download?dataset=states&format=csv` | 51 | state_fips, state_abbr, state_name, region, division, is_state |
| Counties | `/geographies/counties` or `/download?dataset=counties&format=csv` | ~1224 | county_fips, state_abbr, county_name, region, rucc, metro_class, population_base |
| Countries | `/geographies/countries` or `/download?dataset=countries&format=csv` | 72 | iso3, canonical_name, portal_label, alternate_labels, region, income_group |
| State health | `/data/state-health` or `/download?dataset=state_health&format=csv` | ~4861 | observation_id, state_fips, state_abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at |
| State socioeconomic | `/data/state-socioeconomic` or `/download?dataset=state_socioeconomic&format=csv` | ~323 | record_id, state_fips, state_abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population |
| County health | `/data/county-health` or `/download?dataset=county_health&format=csv` | ~47939 | observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag |
| County socioeconomic | `/data/county-socioeconomic` or `/download?dataset=county_socioeconomic&format=csv` | ~6772 | record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population |
| Country indicators | `/data/country-indicators` or `/download?dataset=country_indicators&format=csv` | ~9812 | observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag |
| Revisions | `/data/revisions` or `/download?dataset=revisions&format=csv` | ~130 | revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status, issued_at, reason_code |

### Download strategy

Always use the `/download` endpoint with `format=csv` to fetch entire datasets at once. You can filter by query parameters (e.g., `?state_abbr=CA&year=2023`). Parse the CSV with your language's standard CSV library. The HTML browse pages at `/data/*` and `/geographies/*` are for human navigation only — prefer CSV for programmatic use.

The `/catalog` page lists all columns, filter parameters, and row counts. Use it to understand schema before downloading.

The `/methodology` page documents domain conventions (release lifecycle, value types, quality flags, suppression rules, RUCC codes, country label reconciliation). Read relevant methodology docs when a task references a concept you haven't encountered.

## Data Resolution Rules

These rules apply to every task, regardless of the specific dataset:

### Release selection
1. Filter to `release_status = "FINAL"` only. Provisional, draft, pending, and withdrawn records are not authoritative.
2. For each unique combination of key columns (typically geography identifier + year + measure + type), select the row with the **highest `revision` number**.
3. If multiple rows share the same highest revision, break ties with the **latest `released_at` timestamp**, then the **highest `observation_id`** (or `record_id` for socioeconomic data).

### Missing, suppressed, and invalid values
- A value is **missing** if the cell is blank, empty, or the row doesn't exist for that key.
- A value is **suppressed** if `suppression_flag = "1"`.
- A value is **invalid** if `quality_flag` is `"INVALID_SCALE"`, `"INVALID"`, or `"WITHDRAWN"`.
- **Never substitute zero** for a missing, suppressed, or invalid value. Treat them as unavailable (null/None).
- A quality flag of `"REVIEWED"`, `"REVISED"`, `"PARALLEL_ESTIMATE"`, or `"CAUTION"` does **not** invalidate the value. Suppression and the three invalid flags above are the only exclusions.

### Geography conventions
- **State identifiers** are two-character uppercase USPS abbreviations (`state_abbr`). Include DC (`is_state = "0"`) when the scope says "50 states plus DC" or "51 jurisdictions."
- **County identifiers** are five-character FIPS strings (`county_fips`): two-digit state prefix + three-digit county suffix. Leading zeros are meaningful.
- **Country identifiers** are three-character uppercase `iso3` codes. Country `portal_label` may differ from `canonical_name`; use `alternate_labels` for reconciliation. The `/methodology?doc=aliases` page explains label resolution.
- **Division** and **region** names use the portal's exact spelling from the states geography.

### Revision notices
- Applied revisions (`status = "APPLIED"`) are already reflected in the latest FINAL release; they document what changed.
- Non-applied revisions (PENDING, WITHDRAWN) do not modify published values.
- When a task asks for `applied_revision_event_ids`, report the `revision_event_id` values with status `"APPLIED"` that target the relevant domain/entity.

## Reading analysis_request.json

Every analysis request follows a common structure. Identify these sections:

### Top-level metadata
- `request_id` or `briefing_id`: unique identifier for the audit
- `protocol_id`: registered protocol version
- `business_task` or `business_request`: the analytical question in plain language
- Geography scope, years, reference year, outcome/exposure/mediator variables

### Evidence specification / publication selection
Defines exactly how to filter data:
- `release_method`: usually `"REGISTERED_FINAL_RELEASE_RESOLUTION"` (the rule described above)
- Health filters: `value_type` (AGE_ADJUSTED, CRUDE), `source_type` (DIRECT_SURVEY, COUNTY_ROLLUP), `release_status` (FINAL)
- Socioeconomic filters: `release_status` (FINAL)
- `invalid_quality_flags`: the set of quality flags that invalidate a value
- `missing_rule`: confirms "never zero-fill"
- Cohort definitions: which variables must be non-null for inclusion in each cohort

### Cohort types (recurring pattern)
- **Primary/reference cohort**: complete cases for all required variables in the reference year
- **Balanced panel cohort**: complete cases in every analysis year
- **Core balanced cohort**: a stricter subset of balanced, often limited to specific variables
- **Broad cohort**: complete cases for an expanded feature set (used for ML/prediction modules)
- **Strict/dual-source cohort**: complete for outcome, primary exposure, parallel exposure, and adjustments
- **Machine-learning cohort**: broader features including interaction terms

### Common statistical module specifications

#### Delete-one jackknife
- `method`: identifies the jackknife variant (e.g., STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE)
- `cohort`: which data subset to use
- `outcome`: the dependent variable
- `ordered_predictors`: predictor variables in the exact order for the design matrix
- `cluster`: the unit to delete (STATE, CENSUS_DIVISION)
- `required_evidence`: what the module must output

Implementation: Fit the full model on the entire cohort. Then, for each cluster unit, refit the model with that unit excluded. The jackknife bias-corrected coefficient = `2 * coef_full - mean(delete_coefs)`. The jackknife standard error = `sqrt((G-1)/G * sum((coef_i - coef_bar)^2))` where G is the number of clusters. Report the full coefficient, all delete coefficients (ordered to match the cluster order), mean, SE, t-statistic, p-value (from t-distribution with G-1 df), bias-corrected coefficient, and min/max delete states with their coefficients.

#### Nested cross-validation (ridge or elastic net)
- `method`: identifies the CV variant
- `cohort`: which data subset
- `outcome` or `target`: the dependent variable
- `feature_order`: exactly ordered feature list for the design matrix
- `group`: outer fold grouping (CENSUS_DIVISION, STATE)
- `lambda_grid` or `alpha_grid` + `l1_ratio_grid`: hyperparameter grids in declared order
- `required_evidence`: what to output

Implementation: For each outer fold (leave-one-group-out), standardize features using only the outer training data. For each hyperparameter combination, run inner cross-validation (same leave-one-group-out pattern within the outer training set) and compute the inner RMSE. Select the hyperparameter that minimizes mean inner RMSE. Fit on the full outer training set with the selected hyperparameter, predict on the outer test set, and compute outer RMSE. After all outer folds, compute pooled metrics: RMSE, MAE, and Q² (R² on out-of-fold predictions = `1 - SSR/SST`). Report the complete inner grid, selected hyperparameters per fold, outer RMSEs, pooled metrics, and worst-performing fold.

#### Wild cluster bootstrap
- `method`: identifies the bootstrap variant and PRNG (PCG32_WEBB or XORSHIFT32)
- `cohort`: which data subset
- `cluster`: clustering unit
- `seed`, `stream`, `replicates`: PRNG parameters
- `checkpoint_replicates`: specific replication counts at which to record PRNG state
- `quantile_probabilities`: which quantiles to report
- `required_evidence`: what to output

Implementation:
1. Fit the restricted (null-imposed) model: set the target coefficient to 0 and fit the remaining terms. Store restricted residuals.
2. Initialize the specified PRNG with the given seed (and stream for PCG32).
3. For each bootstrap replicate:
   a. Generate Rademacher weights (+1/-1 with equal probability) for each cluster.
   b. Generate bootstrap y: `y* = y_fitted_restricted + residual * weight[cluster]`.
   c. Fit the full (unrestricted) model on the bootstrap sample.
   d. Compute the CR1 cluster-robust t-statistic for the target coefficient.
4. The bootstrap p-value = `(count of |t*| >= |t_obs| + 1) / (B + 1)`.
5. Record checkpoint PRNG states and t-statistics at the specified replicates.
6. Report the observed coefficient, CR1 SE, t-statistic, leading weight-index rows (aligned to cluster order), batch exceedance counts, and requested quantiles of the bootstrap t-distribution.

**CR1 cluster-robust variance**: `V_CR1 = (G/(G-1)) * ((n-1)/(n-k)) * (X'X)^(-1) * sum_g(X_g' u_g u_g' X_g) * (X'X)^(-1)` where G is number of clusters, n is observations, k is parameters.

**PRNG implementations**: Implement the exact algorithm specified. PCG32 uses a 64-bit state with multiplier 6364136223846793005, increment (stream|1). The output step: xor_shifted = ((old>>18)^old)>>27, rot = old>>59, result = (xor_shifted>>rot) | (xor_shifted<<((-rot)&31)) masked to 32 bits. XorShift32 uses three xorshift operations: x^=(x<<13), x^=(x>>17), x^=(x<<5), all masked to 32 bits.

#### Grouped split conformal
- `method`: identifies the calibration variant
- `cohort`: which data subset
- `group` or `state_groups`: how to partition the data
- `alpha` or `nominal_coverage`: desired coverage level (1 - alpha)
- `fixed_lambda` or model reference: prediction model

Implementation: For each outer fold (leave-one-group-out), split data into proper training (all groups except test and calibration groups), calibration group, and test group. Fit the prediction model on proper training. Compute absolute residuals on calibration set. The conformal threshold (q-hat) is the `ceil((1-alpha)*(n_cal+1))`th order statistic of calibration absolute residuals. Predict on the test set. Coverage = fraction of test observations where prediction error <= threshold. Mean width = 2 * threshold. Report per-fold and aggregate coverage and width.

#### Trajectory PCA clustering
- `method`: identifies PCA and clustering variant
- `cohort` or `aggregation_unit`: which data and at what level to aggregate
- `feature_years` and `within_year_feature_order`: how trajectory features are constructed
- `retained_component_count`: how many PCs to compute
- `cluster_count`: k for k-means
- `stability_omitted_years` or `leave_year_out`: years to omit for stability assessment

Implementation:
1. Build trajectory features: for each entity, concatenate all variables across all years in the declared order (e.g., `[le_2020, le_2021, ..., ao_2020, ao_2021, ...]`).
2. Standardize features (center and scale each column).
3. Compute PCA on the covariance matrix (use power iteration for the top components). Report eigenvalues, explained variance ratios, cumulative explained ratio, and signed loadings per component.
4. Project each entity onto the retained PCs to get scores.
5. Run deterministic k-means (k = cluster_count) on the PC scores. Initialize centroids from spread-selected entities (e.g., sort by PC1, take first, middle, last). Report cluster centroids, sizes, labels, iteration count, and per-entity assignments.
6. For each leave-year-out in the stability set: rebuild the trajectory without that year's features, re-run PCA, re-cluster, and compute the Adjusted Rand Index (ARI) against the reference clustering. Report ARI per omitted year and the minimum/mean ARI.

**Adjusted Rand Index**: `ARI = (sum_ij choose(n_ij, 2) - expected) / (0.5*(sum_i choose(a_i, 2) + sum_j choose(b_j, 2)) - expected)` where `expected = (sum_i choose(a_i, 2) * sum_j choose(b_j, 2)) / choose(n, 2)`.

#### Source perturbation / sensitivity
Common variants:
- **Source-year perturbation**: Exhaustively enumerate all year subsets of the declared sizes (e.g., 3, 4, 5 years from a 5-year window). For each subset, fit separate models with the primary (e.g., age-adjusted) and parallel (e.g., crude) exposure series. Compute coefficient vectors, absolute percent shifts between series, same-sign fraction, and median/max shift.
- **Exhaustive source perturbation**: For each jurisdiction that has both a baseline (direct) and replacement (rollup) record, enumerate all replacement-count strata (0 through M replacements). Within each stratum, enumerate all combinations (or enough to characterize stability). Report scenario counts, stable scenario count, maximum-shift metrics, and Shapley effects.
- **Mediation sensitivity surface**: Given baseline path coefficients and SE, grid over R² mediator-confounder and R² outcome-confounder values. For each cell, compute the adjusted path coefficients and indirect effect under the confounding scenario. Report the complete ordered surface and the tipping R².

### Decision rules
The decision section defines one or more gates, each with a pass/fail condition (e.g., `BOOTSTRAP_P_VALUE_IS_AT_MOST_0_05`). Gates are always evaluated against the reported statistics. The classification uses a precedence rule: check the strictest condition first, then fall back through the hierarchy.

## Reading answer_template.json

The template defines the exact output contract. Key patterns:

### Top-level structure
- `required_top_level_keys`: the JSON keys your answer must contain, in order
- `template` or `required_output`: the schema for each section

### Within each section
- `required_keys`: every key that must be present
- `array_lengths`: exact lengths for arrays (single number or nested structure like `[9, 5]`)
- `cardinality_rules`: semantic constraints (e.g., "must equal state_n", "must align positionally with state_order")
- `ordering`: how lists must be sorted (state ascending, year ascending, registered order, etc.)
- `gate_values` / `enum` / `allowed_values`: controlled vocabularies

### Global rules
- **Numeric precision**: round every non-integer to 4 decimal places (or the declared precision), encoded as a JSON number. Integer metadata and booleans keep their natural JSON type.
- **Identifiers**: use uppercase two-letter state codes, portal division names exactly as they appear, uppercase ISO3 codes.
- **Ordering**: preserve every formal order from the analysis request. Do not independently sort an aligned result array.
- **Missing**: use JSON `null` only when a statistic is mathematically unavailable (e.g., a delete coefficient for a state with insufficient data). Never use `NaN` or `Infinity`. A value of 0.0 is not the same as missing.

### Common template patterns
- **Cohort sections**: always include jurisdiction counts, yearly breakdowns, excluded codes, and complete observation counts.
- **Regression sections**: include coefficient order, full model results, and per-cluster diagnostics. Coefficients must be in the exact order declared.
- **CV sections**: include the hyperparameter grid, per-fold results in fold order, and pooled aggregate metrics.
- **Bootstrap sections**: include PRNG metadata, observed statistics, checkpoint arrays, and quantiles.
- **Conformal sections**: include fold-level diagnostics, per-group coverage/width, and aggregate calibration.
- **Clustering sections**: include component scores aligned to entity order, cluster assignments aligned to entity order, and stability diagnostics.
- **Decision sections**: include per-gate booleans, pass count, and classification enum.

## Implementation Approach

### Step 1: Understand the task
Read all three input files completely before writing any code. Map each audit module to:
- Which dataset(s) it needs
- What filters apply
- Which cohort definition governs inclusion
- What statistical computation is required
- What output shape is expected

### Step 2: Fetch and resolve data
Download all needed datasets as CSV. Apply the FINAL release resolution rule. Build lookup dictionaries keyed by geography + year + measure + type.

### Step 3: Build cohorts
Apply the cohort definitions in order. A panel is balanced only when an entity is complete in every analysis year. Exclusion codes are those missing from the cohort, not an arbitrary list.

### Step 4: Implement statistical modules
Work module by module. For each:
1. Build the design matrix using the declared predictor order
2. Apply the specified method exactly (not a similar method)
3. Verify numerical outputs are consistent (e.g., jackknife coefficients should vary slightly but not wildly from the full coefficient)
4. Format the output to match the template's required keys, array lengths, and ordering

### Step 5: Assemble and validate the answer
- Every required key is present
- Array lengths match the template's `array_lengths`
- Cardinality rules are satisfied (state_order length = state_n, etc.)
- Numeric values are rounded to the declared precision
- Booleans and integers are native JSON types
- Enums match the allowed values exactly
- No narrative text outside the JSON

### Implementation notes
- Use the portal's download endpoint for CSV; do not screen-scrape HTML tables
- Standardize features using ONLY the training subset for each fold (do not leak test information)
- When centering and scaling, use population standard deviation (ddof=0) or sample standard deviation (ddof=1) consistently; the portal methodology may clarify, but in practice either works if applied uniformly
- Deterministic k-means requires a reproducible initialization and no randomness in centroid updates — use k-means++ initialization with a fixed seed and iterate until convergence
- For PRNGs (PCG32, XorShift32), implement them exactly as specified; discarding the first draw after seeding is standard for PCG32
- When computing leave-one-out diagnostics, the deleted unit's observations must be completely excluded from both training and the design matrix
- Conformal prediction thresholds use the formula `q_idx = ceil((1-alpha) * (n_cal + 1)) - 1` (1-indexed to 0-indexed conversion)

## Supporting Files

This skill includes a pure-Python linear algebra module (`linalg.py`) that provides:
- Matrix operations (multiply, transpose, inverse via Cholesky)
- Least squares and ridge regression solvers
- PCA via power iteration
- k-means clustering with k-means++ initialization
- Adjusted Rand Index
- PRNG implementations (PCG32, XorShift32)
- Statistical utilities (mean, variance, quantile, t-distribution CDF)

Use it as a foundation when numpy/scipy are not available. The module has no external dependencies beyond the Python standard library.
