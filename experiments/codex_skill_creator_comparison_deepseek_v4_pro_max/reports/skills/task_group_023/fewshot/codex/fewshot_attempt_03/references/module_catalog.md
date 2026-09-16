# PHO Audit Module Catalog

This reference catalogues every reusable computational module across registered PHO protocols. Each module is defined by a method name and a fixed algorithmic contract. The analysis_request.json specifies which modules run, their parameters, and cohorts.

## Release Resolution and Cohorts

Appears in: all protocols.

1. For each requested series (measure x filter), select highest revision, then latest release timestamp, then lowest record identifier among eligible rows.
2. Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and never zero-filled.
3. Join independently resolved series by stable entity key and time key.
4. Construct each analytic cohort from its effective required fields.
5. Preserve entity-code then time order for all output arrays; preserve declared feature and group orders.

No single script; implement in analysis orchestration. Key ops: csv filtering, grouping, merge-on-keys.

## Delete-Cluster Fixed Effects / Jackknife

Method names: STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE, RELIABILITY_WEIGHTED_DELETE_ONE_CENSUS_DIVISION_JACKKNIFE, DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM.

### Two-way FE jackknife

1. Double-demean each variable: z - entity_mean(z) - time_mean(z) + grand_mean(z).
2. Fit OLS without intercept on transformed data.
3. For each cluster deletion: drop all rows, recompute all means, refit from scratch in entity-code order.
4. b_BC = G * b_full - (G-1) * bbar.
5. SE_JK = sqrt((G-1)/G * sum_g (b_-g - bbar)^2).
6. t = b_full / SE_JK, df = G-1, two-sided.

Script: scripts/ols.py - two_way_fixed_effects(), delete_one_cluster_jackknife()

### Two-step GMM (train_005 variant)

Method: DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM. First step: identity weighting. Second step: optimal weighting from clustered first-step residuals. Hansen J test. Implement from scratch following request instrument and coefficient orders.

## Nested Ridge / Elastic Net CV

Method names: NESTED_LEAVE_ONE_CENSUS_DIVISION_OUT_RIDGE, NESTED_LEAVE_STATE_OUT_RIDGE_WITH_TRAINING_ONLY_STANDARDIZATION, DIVISION_GROUPED_NESTED_WEIGHTED_ELASTIC_NET, STATE_BLOCKED_NESTED_ELASTIC_NET_WITH_TRAINING_ONLY_STANDARDIZATION.

### Ridge coordinate descent

1. For each outer group: hold out. Within training: hold out each inner group once.
2. Standardize features using training-only means and SD (ddof=1); apply to validation/test.
3. Coordinate descent: center outcome, intercept unpenalized, coefs start at 0.
   Cycle in declared feature order: b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n * lambda).
   Stop when max change < tol or at sweep cap.
4. For each lambda: pool all inner validation SSE, compute RMSE.
   Select lambda with smallest RMSE (ties: smaller lambda). Refit on all training, predict test.
5. Pool exactly one OOF prediction per row; compute RMSE, MAE, and Q^2.

Script: scripts/ridge.py - ridge_coordinate_descent(), standardize_training(), apply_standardization(), nested_group_cv_ridge()

### Elastic net variant (train_004, train_005)

Uses alpha-l1_ratio grid. Coordinate descent with elastic net penalty:
b_j = soft_threshold(num) / (denom + n * alpha * (1 - l1_ratio))
where soft_threshold(z,g) = sign(z) * max(0, |z|-g).
Indicator terms (RUCC, time dummies) are NOT standardized. Implement from scratch.

### Weighted variant (train_004)

Reliability weights (sample_size) multiply residuals. Use weighted normal equations.

## Wild Cluster Bootstrap

Method names: PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T, RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T, RESTRICTED_NULL_XORSHIFT32_WILD_CENSUS_DIVISION_BOOTSTRAP_T, RESTRICTED_NULL_STATE_WILD_CLUSTER_BOOTSTRAP_T_WITH_XORSHIFT32.

1. Fit unrestricted model; compute observed t = b / SE_CR1.
2. Fit restricted model (null: target coefficient = 0); retain fitted values and residuals.
3. For each replicate: draw one Webb six-point weight per cluster in entity-code order.
   y* = restricted_fit + restricted_residual * cluster_weight.
   Refit unrestricted model, recompute CR1 SE, studentize.
4. One continuous PRNG stream; record checkpoints after completed replicates without resetting.
5. Count abs(t*) >= abs(t_observed); p = (1 + count) / (1 + B).
6. Quantiles: nearest-rank: x[min(B, ceil(p*B)) - 1] (one-based rank).

PRNGs:
- PCG32: 64-bit state, increment = 2*stream+1. multiplier = 6364136223846793005.
- XORSHIFT32: 32-bit state. x ^= x<<13; x ^= x>>17; x ^= x<<5.
- Webb weights: PRNG output % 6 -> [-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5)].

Script: scripts/prng.py - PCG32, XORSHIFT32

## Grouped Split / Cross-Fold Conformal

Method names: GROUPED_SPLIT_CONFORMAL_RIDGE, STATE_GROUPED_SPLIT_CONFORMAL, DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL_CALIBRATION, CROSS_FOLD_GROUPED_SPLIT_CONFORMAL.

### Grouped split conformal

1. For each ordered outer group (test): among remaining, pick calibration by greatest row count then ascending group name; others = proper training.
2. Fit ridge from scratch with effective fixed lambda and training-only scaling.
3. Sort m abs calibration residuals. r = min(m, ceil((m+1)*(1-alpha))) one-based.
   Threshold = score[r]. Intervals = pred +/- threshold (inclusive).
4. Report fold coverage, mean width, MAE. Aggregate by outer-test row counts.

### Cross-fold variant (train_005)

Use pre-computed OOF predictions. Each fold calibrates on all other folds.

Script: scripts/conformal.py - grouped_split_conformal_fold(), cross_fold_conformal(), state_grouped_coverage()

## Trajectory PCA and Clustering

Method names: REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_STABILITY, STATE_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_LEAVE_YEAR_OUT_ARI, COUNTY_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_DELETE_STATE_ARI.

1. Build columns in declared variable-major/time order. Standardize by active-column sample SD.
2. Covariance: C = Z'Z / (n-1). Symmetric Jacobi.
3. Jacobi: largest |A_pq| in upper triangle (ties: lower row, then column).
   tau = (A_qq - A_pp) / (2 * A_pq).
   t = sign_nonnegative(tau) / (|tau| + sqrt(1 + tau^2)).
   c = 1/sqrt(1 + t^2); s = t * c. Rotate A and eigenvectors.
   Stop at off-diagonal tolerance or step cap.
4. Order by descending eigenvalue, then original diagonal index.
5. Flip each loading: earliest max-absolute entry positive.
6. Scores = Z * loadings.
7. Deterministic k-means on retained PCs. First center = ASCII-first entity.
   Each subsequent = entity maximizing distance to nearest center (ties: entity code).
   Canonicalize final ids by centroid coordinates then working id.
8. Stability: for each omitted time block or deleted state, rebuild pipeline.
   Adjusted Rand Index: (sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2)+sum_j C(b_j,2)) - expected).

Script: scripts/pca.py - symmetric_jacobi_pca(), pca_summary()
Script: scripts/cluster.py - kmeans_deterministic(), silhouette_score(), adjusted_rand_index()

## Source / Year Perturbation

Method names: EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION, EXHAUSTIVE_DIRECT_VERSUS_ROLLUP_SOURCE_PERTURBATION_WITH_EXACT_SHAPLEY, NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT.

### Source-year perturbation

1. Enumerate time subsets by increasing size then lexicographic tuple order.
2. For each subset, refit complete model separately with primary and parallel series.
3. Shift = |b_alt - b| / |b| * 100. Same-sign: both nonzero with identical sign.
4. Ordinary median of ordered shifts. Worst by greatest unrounded shift, then earlier subset.

### Source group deletion (train_005)

1. For each ordered source group, remove its terms from the design.
2. Reuse full model selected hyperparameters without retuning.
3. OOF RMSE on same outer folds. Deterioration = reduced_RMSE - full_RMSE.

### Source perturbation with Shapley (train_004)

1. For eligible states with both direct and rollup values: enumerate 2^M scenarios.
2. Fit primary model per scenario. Stability: all scenarios same-sign, shift within threshold.
3. Exact Shapley: average marginal contribution across all orderings.

## Mediation Sensitivity (train_002)

Method: PARTIAL_R2_MEDIATION_SENSITIVITY_SURFACE. From path-a and direct model coefficients, SEs, and residual df: for each (R2_mediator_confounder, R2_outcome_confounder) in both bias directions, compute adjusted indirect effect via partial-R2 sensitivity formulas. Tipping R2: value where adjusted effect crosses zero.

## Difference GMM Mediation (train_002)

Method: STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION_WITH_CROSS_EQUATION_DELTA_INFERENCE. Panel in changes with level lags as instruments. Three equations. Delta method for indirect effect. State-clustered throughout.

## Country Cross-Section and Panel (train_003)

1. Reconcile country labels via portal_label + alternate_labels -> iso3.
2. Apply APPLIED revision events; note non-applied.
3. Flag anomaly cells; exclude from PCA.
4. Impute missing 2022 cells via column-median after anomaly exclusion.
5. PCA on 2022 burden indicators; retain first PC if dominant.
6. K-means k=3 on PC1; compute silhouettes for k=2,3,4,5; select best.
7. Panel 2017-2022: life_expectancy ~ PC1 + region FE.

## Controlled Decision

Every protocol concludes with a controlled decision module evaluating business predicates across all preceding modules, counting passed gates, and applying the request decision mapping and precedence rules. Gate order is fixed by the request precedence list.
