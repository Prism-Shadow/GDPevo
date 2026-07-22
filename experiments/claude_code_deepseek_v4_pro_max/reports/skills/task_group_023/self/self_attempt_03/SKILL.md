# Public Health Observatory Algorithmic Audit

## Trigger

Use this skill when the user needs to complete a Public Health Observatory (PHO) registered algorithmic audit — a structured, multi-module statistical analysis that queries the PHO read-only data portal, applies registered methodologies, and returns a single JSON object conforming to a declared answer template.

Trigger signals: the task references a PHO portal at a configurable base URL, includes an `analysis_request.json` with audit modules and decision rules, and provides an `answer_template.json` that fixes the output contract.

## Portal Interaction

The PHO portal is an unauthenticated read-only HTTP API. Discover available endpoints from the accompanying environment description. All data is available via GET requests returning JSON arrays of records.

**Base workflow:**
1. Fetch `/` or `/catalog` to confirm available datasets.
2. Identify the relevant endpoint(s) from the analysis request's declared datasets, geographies, and measures.
3. Fetch all data pages. Check for paginated responses — iterate through pages if the portal paginates.
4. Cache raw responses in memory to avoid re-fetching; if the portal includes revision metadata, retain it alongside each record.

**Geography endpoints** return the canonical identifiers for states, counties, census divisions, and countries. Use them to map between label forms (full names, abbreviations, ISO3 codes) and to verify universe membership.

**Data endpoints** are organized by geography × domain (e.g., state-health, county-socioeconomic, country-indicators). Each record carries measure values plus metadata: release status, revision number, value type, source type, sample size, quality flags, and year.

**Revision endpoint** (`/data/revisions`) lists revision events with statuses (APPLIED, SUPERSEDED, WITHDRAWN). Track these to comply with registered-release methodology.

**Methodology endpoint** (`/methodology`) documents measure definitions, value-type semantics (AGE_ADJUSTED vs CRUDE), source-type provenance (DIRECT_SURVEY vs COUNTY_ROLLUP), and quality-flag meanings. Consult it before resolving any unfamiliar field.

## Data Selection and Cohort Construction

### Release Resolution

When the analysis request specifies `REGISTERED_FINAL_RELEASE_RESOLUTION`:
- Keep only records where `release_status` is `"FINAL"`.
- When multiple FINAL releases exist for the same jurisdiction×year×measure, select the one with the highest `revision` number.
- When revisions tie, prefer the most recent `released_at` timestamp, then the highest `observation_id` or `record_id`.
- Apply declared health filters (value_type, source_type) and socioeconomic filters (release_status) independently — health and socioeconomic records come from distinct endpoints and may have different selection rules.

### Missing-Data Rules

**Never zero-fill.** Suppressed, invalid, blank, or missing values mean the observation is unavailable. Mark them as absent — do not substitute zero.

**Quality flags:** The analysis request declares invalid flags (e.g., `INVALID_SCALE`, `INVALID`, `WITHDRAWN`). Treat any record carrying one of these flags as suppressed for that measure, even if a numeric value is present.

**Suppression cascade:** A record suppressed on one required measure makes the entire observation row incomplete for that year. Exclude it from complete-case cohorts.

### Cohort Definitions (recurring patterns)

Each analysis request defines cohorts with precise names. The common patterns are:

- **Complete-case (reference-year):** Jurisdiction has non-missing, non-suppressed values for the outcome, exposure, and all declared adjustment variables in the reference year.
- **Core balanced panel:** Jurisdiction has complete cases in every analysis year. This is stricter than reference-year complete — it requires longitudinal completeness.
- **Broad reference cohort:** Reference-year complete cases for the outcome and all ordered features (may include more variables than the core panel).
- **Strict dual-source cohort:** Complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.
- **Machine-learning cohort:** Complete-case reference-year plus additional fields (e.g., unemployment, net migration, uninsured).

Track excluded jurisdiction codes explicitly — they must be reported in the output and their absence must be justified.

### Identifier Conventions

- **U.S. states:** Uppercase two-letter postal codes (`AL` through `WY`, plus `DC`).
- **Census divisions:** The nine standard Census Bureau division names.
- **Countries:** Uppercase three-letter ISO3 codes.
- **Counties:** Portal-native county identifiers (typically FIPS or portal-specific codes); map to state abbreviations when reporting state-level aggregates.
- **Regions:** The four Census Bureau regions (Northeast, Midwest, South, West); Northeast is the default reference category unless the request overrides it.

## Statistical Methodology Patterns

The analysis request specifies each module with a `method` field naming a registered procedure. Below are the recurring method families and what they require.

### Fixed-Effects and Clustered Regression

Methods labeled `STANDARD_TWO_WAY_FIXED_EFFECTS_OLS` or `RELIABILITY_WEIGHTED_LINEAR_REGRESSION` fit a linear model with cluster-robust inference. When the module includes `cluster`, compute cluster-robust standard errors (CR1/ HC3 variants as declared). When reliability weights are declared (`sample_size`), apply them as observation weights throughout.

**Delete-one jackknife** variants (`DELETE_ONE_STATE_JACKKNIFE`, `DELETE_ONE_CENSUS_DIVISION_JACKKNIFE`): fit the model once on the full cohort, then re-fit once per deleted cluster. Report the full coefficient, every delete-one coefficient (aligned to the cluster order), the mean delete-one coefficient, jackknife standard error, t-statistic, p-value, bias-corrected coefficient, and the extreme-deletion cluster (minimum and maximum coefficient).

### Two-Step GMM (Dynamic Panels)

Methods labeled `DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM` or `STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION` fit instrumented panel models:
- First-stage: regress endogenous changes on declared instruments.
- Second-stage: use predicted values in the outcome equation.
- Compute Hansen's J statistic for overidentification.
- For delete-state variants: re-fit after dropping each state, report all coefficient vectors and J statistics.
- For mediation variants: compute the indirect effect as path-a × path-b with cross-equation delta-method inference (covariance across equations).

### Nested Cross-Validation (Ridge / Elastic Net)

Methods labeled `NESTED_LEAVE_*_OUT_RIDGE` or `*_NESTED_ELASTIC_NET` perform grouped cross-validation:

- **Outer loop:** Hold out one group at a time (census division, state, or random fold).
- **Inner loop:** Within the training set, perform further grouped or K-fold CV over a declared grid of hyperparameters (lambda for ridge; alpha × l1_ratio for elastic net).
- **Standardization:** Apply training-set-only standardization — compute mean and SD from the training fold, apply the same transform to both training and held-out observations.
- **Selection:** For each outer fold, select the hyperparameter(s) that minimize inner-grouped RMSE.
- **Reporting:** Return every outer fold's training and test sizes, selected hyperparameters, inner-grid RMSE matrix, outer RMSE, pooled RMSE, pooled MAE, and pooled R² or Q².

When comparing two feature sets (base vs augmented), run both pipelines through the same outer folds. Compare pooled RMSE and count outer folds where augmented wins.

### Wild Cluster Bootstrap

Methods labeled `*_WILD_CLUSTER_BOOTSTRAP_T` or `RESTRICTED_NULL_*_BOOTSTRAP_T`:

- Fit the source model (OLS or declared specification) on the original data to obtain the observed coefficient, cluster-robust standard error, and t-statistic.
- For each replicate (typically 1999 or 2047, per the request):
  - Generate Rademacher or Webb weights for each cluster.
  - Under the **restricted null**, impose the null hypothesis on the target coefficient before resampling.
  - Re-fit and record the bootstrap t-statistic.
- Track the PRNG state at declared checkpoint replicates.
- Compute the bootstrap p-value as (exceedance_count + 1) / (replicates + 1), where exceedance_count counts bootstrap t-statistics with absolute value ≥ the observed absolute t.
- Report the observed statistics, first few weight-index rows, batch exceedance counts, checkpoint PRNG states and t-statistics, tail quantiles, terminal PRNG state, and the p-value.

When the module specifies **paired equations** (mediation bootstrap), run each equation's restricted-null bootstrap and report all three t-statistic checkpoints per replicate.

### Grouped Split Conformal Prediction

Methods labeled `GROUPED_SPLIT_CONFORMAL` or `DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL`:

- Split data into calibration and test sets, typically by group (census division or state).
- For each fold: train on proper-training observations, compute nonconformity scores (absolute residuals) on calibration observations, determine the threshold (quantile-based rank with finite-sample correction), and evaluate coverage and interval width on test observations.
- The threshold for a fold is the ⌈(n_cal + 1) * (1 - alpha)⌉-th smallest calibration residual, divided by n_cal (with finite-sample correction as declared).
- Report every fold's calibration size, test size, threshold, coverage fraction, and mean interval width. Aggregate across folds for pooled coverage and mean width.
- When the module covers all groups in a leave-one-out scheme, every group serves as test once with all other groups pooled for calibration.

### Principal Component Analysis and Trajectory Clustering

Methods labeled `REGISTERED_COVARIANCE_PCA_DETERMINISTIC_*_MEANS_LEAVE_YEAR_OUT_STABILITY` or `*_TRAJECTORY_PCA_*`:

- Construct the feature matrix from jurisdiction-level trajectories. For multi-year features, flatten year × variable into columns (e.g., `life_expectancy_2020`, `life_expectancy_2021`, … or `diabetes_change_2022`, `diabetes_change_2023`, …).
- Center the feature matrix (no scaling unless declared). Compute the covariance matrix and its eigendecomposition.
- Report eigenvalues, explained-variance ratios, cumulative ratios, and signed loadings for the declared number of principal components.
- For clustering: initialize centroids with the declared method (e.g., first K states in the analysis-request's state order). Run Lloyd's algorithm to convergence. Report initial centroid states, update count, final centroids, cluster sizes, and per-state cluster labels aligned to the state order.
- For stability: repeat the full PCA + clustering workflow omitting one year at a time. Compute the Adjusted Rand Index between each leave-year-out labeling and the full-data labeling. Report every leave-year-out ARI, the aligned agreement flags, the minimum ARI, and the mean or median ARI as declared.

### Source / Year Perturbation and Sensitivity

Methods labeled `EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION` or `EXHAUSTIVE_DIRECT_VERSUS_ROLLUP_SOURCE_PERTURBATION`:

- Define all source or year subsets as declared (e.g., all 2^4 = 16 subsets of four eligible state codes, or combinations of year subset sizes).
- For each scenario, re-select data according to the perturbation rule and re-fit the declared model.
- Report the coefficient vector and p-value vector for every scenario, aligned to the declared subset order.
- Compute the absolute percent shift between scenario coefficients and the baseline.
- For source perturbation: also compute exact Shapley values — the average marginal contribution of each perturbable unit across all possible join orders.
- Report stability summaries (same-sign fraction, median and maximum absolute percent shift, worst subset).

### Mediation Sensitivity Surface

When the module is `PARTIAL_R2_MEDIATION_SENSITIVITY_SURFACE`:
- Extract the baseline path-a coefficient, path-b coefficient, path-b standard error, and residual degrees of freedom from the source models.
- For each combination of declared R² values (mediator confounder, outcome confounder) and bias direction:
  - Adjust the path-b coefficient using the Cinelli-Hazlett formula: `adjusted = baseline - bias_direction * (R2_outcome * baseline_se^2 * df / (1 - R2_outcome))^0.5`.
  - Recompute the indirect effect = path_a × adjusted_path_b.
  - Determine whether the sign of the indirect effect is preserved.
- Report the equal-strength tipping R² (the R² at which both confounder strengths cause the indirect effect to cross zero).
- Report the full surface grid in declared order.

### Source Group Deletion Audit

When the module is `NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT`:
- Train the full model (e.g., nested elastic net) and record its outer-fold OOF RMSE as the reference.
- For each declared source group, remove its terms from the design matrix, re-run the outer folds **without re-tuning hyperparameters** (reuse the full model's selected lambda/alpha/l1_ratio per fold), and compute each fold's RMSE.
- Compute the deterioration = group_rmse - reference_rmse for each fold and pooled.
- Count folds where deterioration is positive (worse). Rank groups by pooled deterioration descending.
- Report the reference RMSE, each group's removed terms, outer-fold RMSEs, pooled RMSE, deterioration, worse-fold count, and rank.

## Output Formatting Rules

### Precision

The analysis request declares a numeric decimal-place target (typically 4 or 6). Apply it to every computed non-integer statistic. Use standard rounding (half-up).

**Integer fields** — counts, ranks, fold numbers, replicate numbers, seeds, PRNG states — remain natural JSON integers (no decimal point).

**Boolean fields** — gate verdicts, support flags — use JSON `true` and `false`.

### Ordering

**Preserve every declared order.** When the analysis request lists states, features, divisions, lambda grids, quantile probabilities, checkpoint replicates, or any other sequence, that order is binding. Output arrays must follow it exactly. Do not alphabetically sort an array whose order is specified by the analysis request, even if the result would be deterministic.

**Positional alignment:** When one array's values are defined relative to another (e.g., delete-one coefficients aligned to a state order, PC scores aligned to a state order, inner-grid RMSE values aligned to a lambda grid), preserve the one-to-one correspondence. The i-th element of the dependent array corresponds to the i-th element of the reference array.

**Ascending sort** applies only when the template explicitly requires it: ascending ISO3, ascending state code, ascending year. When the template says "ordered by region then state" or "CENSUS_DIVISION order," use the portal's registered division order.

### Missing Values in Output

Use JSON `null` when a requested statistic is mathematically unavailable (e.g., a statistic that requires at least two observations but only one is available, or a division with zero test observations). Never emit `NaN`, `Infinity`, or `-Infinity` — these are not valid JSON.

### Enum and Controlled Vocabulary

Decision classifications, advisory values, and gate verdicts must use exactly the strings declared in the analysis request or answer template. Do not paraphrase, abbreviate, or invent variants.

## Decision Rule Application

Every audit concludes with a decision module that evaluates the results against declared gates:

1. Evaluate each gate independently against its declared threshold, using the evidence produced by the corresponding module.
2. Record each gate as `PASS` or `FAIL` (or `true`/`false` per the template's type declaration).
3. Count the number of passing gates.
4. Apply the precedence-ordered classification rule — the first matching condition wins.
5. Report the classification using the exact controlled-vocabulary string.

**Gate formulas** are stated in the analysis request and vary by task. Common forms:
- Coefficient sign + p-value threshold
- R² or Q² minimum
- Bootstrap p-value maximum
- Coverage minimum + width maximum
- Stability index minimum (ARI, same-sign fraction)
- Perturbation shift maximum

**Precedence is strict.** If the first classification condition matches, report it even if later conditions would also match. The conditions are ordered from strongest to weakest signal.

## Verification Checklist

Before submitting, confirm:

- [ ] Every required top-level key from the answer template is present.
- [ ] Every nested required key is present under its parent.
- [ ] All array lengths match the template's cardinality declarations.
- [ ] All numeric values respect the declared decimal-place precision.
- [ ] All arrays preserve the analysis request's declared order.
- [ ] Positionally aligned arrays have matching lengths and correspond element-by-element.
- [ ] No `NaN`, `Infinity`, or non-JSON values are present.
- [ ] No narrative text, commentary, or markdown appears outside the JSON.
- [ ] State codes are uppercase, ISO3 codes are uppercase, division names match the portal's canonical forms.
- [ ] Every gate verdict and decision classification uses the exact controlled-vocabulary strings.
- [ ] All cohort-excluded jurisdiction codes are explicitly listed and justified.
- [ ] Every integer field (count, rank, seed, replicate number) is a JSON integer type.
- [ ] Boolean fields are JSON `true`/`false`, not strings.
- [ ] The JSON parses without error.
