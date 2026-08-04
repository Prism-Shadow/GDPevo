## When to Use

Use this skill whenever a Public Health Observatory (PHO) algorithmic audit task instructs you to complete a registered multi-module analysis using the read-only evidence portal at `<TASK_ENV_BASE_URL>`. The task will supply an `analysis_request.json` defining the audit specification and an `answer_template.json` fixing the response contract. Return one JSON object conforming to the template, with no narrative outside it.

## Portal Access

Resolve `<TASK_ENV_BASE_URL>` from the prompt. The portal is a read-only REST API accessed via GET requests. No authentication is required.

Standard endpoints include:
- `GET /` – root listing
- `GET /catalog` – dataset and measure catalog
- `GET /geographies/states`, `/geographies/counties`, `/geographies/countries` – jurisdiction lookups
- `GET /data/state-health`, `/data/state-socioeconomic`, `/data/county-health`, `/data/county-socioeconomic`, `/data/country-indicators` – measurement records
- `GET /data/revisions` – revision-event history
- `GET /methodology` – measure definitions
- `GET /download?dataset=<name>&format=csv` – CSV export with supported filters

Data pages support `page` and `page_size` query parameters. Fetch all available pages for complete coverage before filtering.

## Data Resolution

### Release and Revision Selection

1. Retrieve the `/data/revisions` endpoint to discover all revision events.
2. For every measure, select records whose `release_status` equals the requested publication state (typically `"FINAL"`).
3. When `revision_selection` is specified, pick the record with the highest revision number; tie-break with the latest release timestamp. If a revision event is marked `"APPLIED"`, include it; non-applied revisions must be documented but excluded from analysis values.
4. When multiple `value_type` or `source_type` variants exist for the same measure, select only the exact combination requested (e.g. `AGE_ADJUSTED` + `DIRECT_SURVEY`).

### Quality and Missingness

- **Suppression**: Values that are suppressed, blank, `null`, or flagged with an invalid quality code (`INVALID_SCALE`, `INVALID`, `WITHDRAWN`) are unavailable. Never substitute zero or any other placeholder.
- **Never zero-fill**: Missing socioeconomic or health data means the observation is incomplete; do not impute unless the analysis request explicitly provides an imputation rule.
- When a cell is missing after applying all filters, the observation is excluded from the relevant cohort; document the exclusion.

## Cohort Construction

Construct cohorts in this order:

1. **Complete-case cohort for each year**: Filter to jurisdictions that have non-missing, non-suppressed values for all required outcome, exposure, and covariate variables for that year.
2. **Primary/reference-year cohort**: The set of jurisdictions complete in the single reference year.
3. **Balanced panel cohort**: The intersection of jurisdictions complete in every requested analysis year.
4. **ML/extended cohort**: The primary-year cohort further filtered for completeness on additional features.

Document cohort sizes at each stage. Track excluded jurisdictions in a sorted ascending list.

## Statistical Module Execution

### 1. Delete-One Cluster Jackknife (or Delete-State)

- Fit the full model on the complete cohort.
- Iterate over every cluster (state, census division), omitting all observations in that cluster and refitting the identical specification.
- Compute the bias-corrected coefficient: `2 * full_coefficient - mean(delete_one_coefficients)`.
- Compute jackknife standard error, t-statistic, and p-value.
- Report the full coefficient vector, every delete-one estimate, the bias-corrected estimate, and the most influential cluster.

### 2. Nested Cross-Validation (Ridge or Elastic Net)

- **Outer loop**: Group data by the `group` key (census division, state). For each outer fold, hold out one group as the test set; use all remaining groups for training.
- **Inner loop**: Within each training set, further partition into inner folds grouped by the same unit. For each candidate hyperparameter (lambda grid, or alpha×l1_ratio grid), compute inner CV RMSE. Select the hyperparameter that minimizes mean inner RMSE.
- **Standardization**: Apply training-only standardization (center and scale continuous predictors using training-set means and SDs; do not standardize indicator/dummy terms).
- **Evaluation**: Apply the selected model to the held-out outer fold. Pool all outer-fold predictions to compute pooled RMSE, MAE, and R².
- Report the full inner-RMSE grid, selected hyperparameters for each outer fold, and pooled metrics.

### 3. Wild Cluster Bootstrap

- Use the declared PRNG method (typically PCG32 or XORSHIFT32) with the given seed and stream.
- Fit the null (restricted) model and the unrestricted model on the observed data.
- Generate `replicates` bootstrap datasets by multiplying residuals by random weights drawn from the Rademacher distribution (Webb weights).
- For each bootstrap sample, compute the cluster-robust t-statistic under the null.
- Count bootstrap t-statistics whose absolute value exceeds the observed absolute t; compute the plus-one p-value: `(exceedance_count + 1) / (replicates + 1)`.
- Report observed statistics, all requested PRNG/t checkpoints at the declared replicate numbers, and bootstrap quantiles at the requested probabilities.

### 4. Grouped Split Conformal Calibration

- Split observations into training, calibration, and test folds grouped by the declared unit (census division, state).
- Train the prediction model on the training fold only.
- On the calibration fold, compute nonconformity scores (absolute residuals) and determine the conformal threshold (the `ceil((n+1)*(1-alpha))` order statistic of calibration residuals, sometimes a max-over-states quantile).
- Apply the threshold to test-fold predictions to produce prediction intervals.
- Report fold-level coverage, mean width, aggregate coverage, and worst-performing group.

### 5. Trajectory PCA Clustering

- Construct a feature matrix where each row is a jurisdiction and columns are variables measured across years (e.g. `life_expectancy_2020`, `life_expectancy_2021`, …).
- Standardize features to zero mean and unit variance.
- Compute PCA via covariance matrix eigendecomposition.
- Retain the declared number of principal components.
- Apply deterministic k-means clustering on the PC scores with a fixed initialization (e.g. first three observations in PC-sorted order).
- Run Lloyd's algorithm to convergence and report the update count.
- Evaluate stability via leave-one-year-out: omit each year's feature block, recompute PCA and clustering, and compute the Adjusted Rand Index against the full clustering.
- Report eigenvalues, explained-variance ratios, loadings, scores, cluster assignments, and all stability ARIs.

### 6. Source/Perturbation Robustness

- For source perturbation: Identify records where two measurement sources disagree (e.g. direct-survey vs county-rollup for the same measure). Iterate over all 2^M substitution scenarios, refit the model in each, and compute the coefficient and p-value stability. Compute exact Shapley effects via coalitional averaging.
- For source-year perturbation: Iterate over all subsets of analysis years for the exposure series. For each subset, fit the model and record the exposure coefficient and p-value. Compute the fraction of subsets with the same sign as the full model and the median absolute percent shift.
- For source-group perturbation: Define source groups (blocks of features with a common origin). Remove each group, refit the prediction model with nested CV, and compute RMSE deterioration. Rank groups by deterioration.

## Numerical Precision

- **Computed real-valued statistics**: Report to the declared precision (typically 4 or 6 decimal places) as JSON numbers.
- **Literal grid and threshold values**: Report to the declared precision (typically 4 decimal places).
- **Counts, ranks, fold numbers, seeds, PRNG states, replicate numbers**: Integers in natural JSON type.
- Trailing zeros need not be preserved in JSON numbers.

## Ordering Rules

- Preserve every declared input order exactly as it appears in `analysis_request.json`.
- Align arrays positionally: e.g. the coefficient vector aligns element-by-element with the ordered predictor list.
- Sort identifier lists (state codes, ISO3 codes, division names) ascending only when the template explicitly requires ascending order. Otherwise, follow the registered order.
- Never substitute a map/object for a list; order-sensitive data must use arrays.

## Decision Rules

- Evaluate each gate condition independently against the computed evidence.
- Count the number of passing gates.
- Apply the classification precedence table to determine the final classification.
- If a gate depends on a specific module's output, use only the values computed in that module.

## Response Formatting

- Return exactly one JSON object containing every required top-level key from `answer_template.json`.
- Do not include narrative, commentary, or explanatory text outside the JSON.
- Use JSON `null` only when a requested statistic is mathematically undefined (e.g. a p-value when degrees of freedom are zero). Never emit `NaN` or `Infinity`.
- Boolean fields use `true`/`false` (not strings).
- Enum fields must use exactly one of the allowed values, verbatim.

## Execution Workflow

1. Read `analysis_request.json` and `answer_template.json` fully.
2. Explore the portal starting from `GET /` and `GET /catalog` to understand available datasets.
3. Resolve releases and revisions systematically using `/data/revisions`.
4. Fetch all required data pages, merging results across pages.
5. Construct cohorts per the specification, documenting exclusions.
6. Execute each audit module in the declared order, computing all required diagnostics.
7. Apply the decision rule to produce the final classification.
8. Assemble the response object, verifying every required key is present.
9. Validate numeric precision, order preservation, and enum values before submitting.
