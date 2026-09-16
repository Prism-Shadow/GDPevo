# Statistical Algorithm Specifications

This reference catalogs the statistical methods in PHO registered audit protocols.
Implement each from scratch using only portal data and the specifications below.
Do not substitute external packages that would change the algorithmic contract.

## Release Resolution

**Method:** REGISTERED_FINAL_RELEASE_RESOLUTION

See [data-rules.md](data-rules.md) for the full selection, suppression, and cohort rules.
Always resolve releases independently per dataset, then join by entity key and year.
Construct each analytic cohort from its effective required variable set.

## Fixed Effects (Delete-One Cluster Jackknife)

**Registered names:**
- STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE
- RELIABILITY_WEIGHTED_DELETE_ONE_CENSUS_DIVISION_JACKKNIFE

### Two-Way Fixed Effects Transformation

For panel data with entity i and time t, transform each variable x:
  x_tilde = x_it - entity_mean(x_i) - time_mean(x_t) + grand_mean(x)

This removes entity and time fixed effects. Fit OLS without an intercept on the
transformed data. Predictors must be used in the declared order.

### Reliability Weights

When a weight variable is specified (e.g., sample_size), use weighted least squares.
Weight each observation by its reliability weight. All centering and regression use
weighted means and weighted OLS.

### Delete-One Jackknife

For G clusters:
1. Drop cluster g entirely
2. Recompute all means from the remaining data
3. Refit the model from scratch in entity-code order
4. Record coefficient b_-g

Jackknife inference:
- b_bar = (1/G) * sum(b_-g)
- SE_JK = sqrt((G-1)/G * sum((b_-g - b_bar)^2))
- bias-corrected b_BC = G*b_full - (G-1)*b_bar
- t = b_BC / SE_JK (or b_full / SE_JK, per protocol specification)
- Two-sided Student t p-value with G-1 degrees of freedom

Extrema: select by coefficient value, then entity code for ties.
Percent change for delete g: |b_-g - b_full| / |b_full| * 100

### Cluster-Robust Standard Errors (CR1)

For OLS with n observations, k parameters, G clusters:
- s_g = X_g^T * e_g  (cluster score vector, length k)
- V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X^T X)^-1 * sum_g(s_g * s_g^T) * (X^T X)^-1
- SE_j = sqrt(V_CR1[j,j])

### HC3 Standard Errors

HC3 applies leverage correction: e_i_hc3 = e_i / (1 - h_ii) where h_ii is the
i-th diagonal of the hat matrix H = X (X^T X)^-1 X^T.

## Nested Ridge / Elastic Net Regression

**Registered names:**
- NESTED_LEAVE_ONE_CENSUS_DIVISION_OUT_RIDGE
- NESTED_LEAVE_STATE_OUT_RIDGE_WITH_TRAINING_ONLY_STANDARDIZATION
- DIVISION_GROUPED_NESTED_WEIGHTED_ELASTIC_NET
- STATE_BLOCKED_NESTED_ELASTIC_NET_WITH_TRAINING_ONLY_STANDARDIZATION

### Training-Only Standardization

For each training fold:
1. Compute feature means and sample std (ddof=1) from training rows only
2. Apply those moments to standardize training rows
3. Apply the same training moments to validation and test rows
4. Center the outcome by its training mean

### Ridge Coordinate Descent Solver

Objective: mean((y - a - Xb)^2) + lambda * sum_j(b_j^2)

Initialize coefficients to zero. For each feature j in declared order:
- Partial residual: r_ij = y_i - a - sum_{k != j} x_ik * b_k
- b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n * lambda)

Intercept: a = mean(y) - mean(Xb), updated after each full cycle.
Cycle through all features. Stop when max|coeff change| < tolerance (default 1e-8)
or at sweep cap (default 5000).

### Elastic Net Variant

Objective: mean((y - a - Xb)^2) + lambda * (alpha*sum|b_j| + (1-alpha)/2*sum(b_j^2))

For each feature j:
- b_ols = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n * lambda * (1-alpha))
- b_j = sign(b_ols) * max(0, |b_ols| - lambda*alpha / (sum_i(x_ij^2)/n + lambda*(1-alpha)))

Intercept is not penalized. Indicator terms may be excluded from standardization
but included in the penalty. Terms flagged as unpenalized skip the penalty.

### Nested Cross-Validation

Outer loop: hold out each group (division, state, fold partition) in declared order.
Inner loop: within each outer training set, hold out each remaining group as validation.

For each (outer_fold, lambda):
- Pool inner validation squared errors at row level; compute RMSE
- Select lambda with minimum inner RMSE; tiebreak by smaller lambda (or alpha then l1_ratio)
- Refit on all outer-training rows with selected lambda
- Predict all outer-test rows

Pool exactly one prediction per row across outer folds:
- RMSE = sqrt(mean((y - y_hat)^2))
- MAE = mean(|y - y_hat|)
- R-squared = 1 - SSE_pooled / SST_full_sample

## Wild Cluster Bootstrap

**Registered names:**
- PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T
- RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T
- RESTRICTED_NULL_XORSHIFT32_WILD_CENSUS_DIVISION_BOOTSTRAP_T
- RESTRICTED_NULL_STATE_WILD_CLUSTER_BOOTSTRAP_T_WITH_XORSHIFT32

### Observed Fit

Fit the unrestricted model. Compute:
- Target coefficient b
- CR1 cluster-robust standard error SE
- t_observed = b / SE  (or |t_observed| for absolute-value tests)

### Restricted Model

Fit the model WITHOUT the target variable (null hypothesis). Retain restricted
fitted values y_hat_0 and residuals e_0 = y - y_hat_0.

### PRNG: PCG32

64-bit unsigned integer state.
increment = 2 * stream + 1 (odd).
Initialize state to 0, advance once, then add seed (mod 2^64).

Advance operation:
  old = state
  state = old * 6364136223846793005 + increment  (mod 2^64)
  xorshifted = ((old >> 18) xor old) >> 27  (low 32 bits after XOR and shift)
  rot = old >> 59  (6 bits, 0-31)
  out = rotate_right_32(xorshifted, rot)  (circular right shift)

Map output modulo 6 sequentially to:
  [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]

These are the Webb 6-point wild bootstrap weights.

### PRNG: Xorshift32

Standard xorshift32 algorithm with a 32-bit unsigned state.

### Weight Distributions

Webb 6-point (used with PCG32): map output mod 6 to the six weights above.
Rademacher (used with Xorshift32): map output to +1 or -1 with equal probability.

### Bootstrap Replicate Generation

Maintain one continuous PRNG stream across all replicates.

For each replicate:
1. Draw one weight per cluster in entity-code order
2. Construct y* = y_hat_0 + e_0 * cluster_weight (same weight for all obs in cluster)
3. Refit the unrestricted model on (X, y*)
4. Recompute CR1 cluster-robust SE from the refit
5. t* = b* / SE*  (studentized bootstrap statistic)

### Checkpoints

Record (replicate_number, prng_state, t*) after the completed replicate,
without resetting the stream. Checkpoint at the declared replicate indices
(typically 1, 2, 4, 8, ... or 1, 10, 100, ...).

### Batch Exceedance Counts

Group consecutive replicates into declared batch sizes (e.g., batches of 100).
Count per batch how many |t*| >= |t_observed|. Report each batch count.

### Inference

exceedance_n = total count of |t*| >= |t_observed| (or per specification).
plus_one_p_value = (1 + exceedance_n) / (1 + B)

For sorted bootstrap t* values and probability p:
  nearest_rank_index = min(B, ceil(p * B)) - 1  (one-based)
  quantile = sorted_values[nearest_rank_index]

### Bootstrap Coefficient Summary

bootstrap_mean = mean of bootstrap b* values
bootstrap_sample_sd = sample std of bootstrap b* values (ddof=1, or per spec)

## Grouped Split Conformal Prediction

**Registered names:**
- GROUPED_SPLIT_CONFORMAL_RIDGE
- STATE_GROUPED_SPLIT_CONFORMAL
- DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL_CALIBRATION
- CROSS_FOLD_GROUPED_SPLIT_CONFORMAL

### Partition Strategy

For each outer group as test:
- Among remaining groups, select calibration group with largest row count
- Tiebreak: ascending group name (alphabetical, case-sensitive)
- All other groups = proper training set

### Ridge Fit and Calibration

1. Fit ridge on proper training set with the effective fixed lambda
   (Use training-only standardization and coordinate descent as above)
2. Predict calibration rows using fitted model
3. Compute absolute residuals: r_i = |y_i - y_hat_i|
4. Sort residuals ascending
5. With miscoverage rate alpha:
     rank = min(m, ceil((m+1) * (1-alpha)))
   where m = number of calibration residuals
6. Threshold q = sorted_residuals[rank - 1]  (1-based index into sorted list)

### Prediction Intervals

For each test observation:
  interval = [y_hat - q, y_hat + q]  (inclusive endpoints)
  covered = 1 if y is in [y_hat - q, y_hat + q], else 0

### Aggregation

Fold-level:
- fold_coverage = covered_count / test_count
- fold_mean_width = 2 * q  (or mean of (y_hat + q) - (y_hat - q) = 2q)
- fold_test_mae = mean(|y - y_hat|) on test rows

Aggregate:
- aggregate_coverage = sum(covered) / total_test_rows  (pooled across folds)
- aggregate_mean_width: weighted by test row counts across folds

## Trajectory PCA Clustering

**Registered names:**
- REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_STABILITY
- STATE_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_LEAVE_YEAR_OUT_ARI
- COUNTY_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_DELETE_STATE_ARI

### PCA via Covariance Matrix

1. Build feature matrix Z: columns in declared variable-major/time order
2. Standardize each column: subtract column mean, divide by column sample std (ddof=1)
3. Form covariance matrix: C = Z^T * Z / (n-1)
4. Symmetric Jacobi eigenvalue decomposition:
   a. Find largest |upper-triangle off-diagonal| in C
      Tiebreak: lower row index, then lower column index
   b. tau = (C_qq - C_pp) / (2 * C_pq)
   c. t = sign(tau) / (|tau| + sqrt(1 + tau^2))
      (sign_nonnegative: t >= 0 if tau >= 0, t < 0 if tau < 0)
   d. c = 1 / sqrt(1 + t^2),  s = t * c
   e. Apply Givens rotation to matrix C and eigenvector accumulator
   f. Stop when max|off-diagonal| < tolerance (default 1e-10) or step cap reached
5. Order components by descending eigenvalue
   Tiebreak: original column index (ascending)
6. Flip loadings: for each component, find earliest index with maximum |loading|;
   if that loading is negative, multiply entire loading vector by -1
7. Scores = Z * loadings  (n x k matrix)

### Cumulative Ratio and Spectrum

first_two_cumulative_explained_ratio = (eig1 + eig2) / sum(all eigenvalues)
report eigenvalues, explained ratios, and cumulative ratios at requested precision

### K-Means Clustering (Deterministic)

1. First centroid: ASCII-first entity code from the cohort (e.g., lexicographically first state_abbr)
2. Each subsequent centroid: entity maximizing minimum squared Euclidean distance
   to already-selected centroids; tiebreak by entity code (ascending)
3. Assignment step: assign each entity to nearest centroid by squared Euclidean distance
   on the effective PCA scores; tiebreak by lower cluster working id (0, 1, 2, ...)
4. Update step: centroids = arithmetic mean of member vectors
5. Convergence: stop when assignments are unchanged from the previous iteration
   or at iteration cap (default 300)
6. Canonicalize final cluster ids: sort by PC1 centroid coordinate, then PC2, then
   PC3, ..., then by original working id; reassign labels 0, 1, 2, ... accordingly
7. Cluster sizes: count members in each canonical cluster

### Initialization for 3-Means

When cluster_count=3 with scores_3d:
- First: ASCII-first entity in cohort
- Second: entity with max distance to first centroid
- Third: entity with max min-distance to {first, second}

### Stability: Leave-Year-Out / Delete-State ARI

For each omitted time block (year) or deleted state, in ascending order:

1. Remove all rows belonging to the omitted year or state
2. Rebuild: scaling, covariance PCA, loading orientation, k-means initialization,
   and clustering from scratch on the retained rows
3. Compute Adjusted Rand Index between the full-model assignments (on retained rows
   only) and the refit assignments:

   Form contingency table C with n_ij = count of entities assigned to cluster i
   in full model and cluster j in refit.

   sum_comb = sum_{ij} binom(n_ij, 2)
   a_sums = [row sums of C]; b_sums = [col sums of C]
   expected = sum_i binom(a_i,2) * sum_j binom(b_j,2) / binom(n,2)
   ARI = (sum_comb - expected) / (0.5*(sum_i binom(a_i,2) + sum_j binom(b_j,2)) - expected)

   If refit produces a different number of clusters, extend with zero columns/rows.

4. Align refit labels to full-model labels by maximum agreement (Hungarian-like
   assignment maximizing sum of matched cell counts). Tiebreak: lexicographically
   smallest permutation of refit labels.

5. Report aligned_assignment_changes: number of entities whose cluster assignment
   changed, after alignment.

### Mean and Minimum ARI

Report arithmetic mean and minimum across all leave-out/delete-state runs.

### Silhouette Score

For each entity i in cluster C_I:
  a_i = mean distance to other entities in C_I
  b_i = min over J != I of mean distance to entities in C_J
  s_i = (b_i - a_i) / max(a_i, b_i)

Average s_i over all entities. Cluster-by-cluster silhouette is the mean within each cluster.

### K-Means Inertia

Sum of squared Euclidean distances from each entity to its assigned centroid.

### Selecting Best K by Silhouette

For each candidate cluster_count k in {2, 3, 4, 5} (or as declared):
  Run full deterministic PCA + k-means pipeline
  Compute average silhouette score
Select the k with maximum average silhouette; tiebreak by larger k.

## Source / Year Perturbation

**Registered names:**
- EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION
- EXHAUSTIVE_DIRECT_VERSUS_ROLLUP_SOURCE_PERTURBATION_WITH_EXACT_SHAPLEY

### Time Subset Enumeration

Enumerate all subsets of analysis years at requested sizes, in increasing subset size
then lexicographic tuple order.

For each subset:
1. Keep the strict analytic set unchanged
2. Refit the complete double-demeaned model using only the subset years
3. Record coefficient, CR1 standard error, and two-sided G-1 df p-value for both
   primary and parallel exposure series

### Aggregation for Time Perturbation

For baseline coefficient b and alternate coefficient b_alt:
- absolute_percent_shift = abs(b_alt - b) / abs(b) * 100
- same-sign: both nonzero and identical sign (both positive or both negative)

Compute median of ordered shifts. Select worst subset by greatest unrounded shift,
then earlier subset order for ties.

same_sign_subset_n: count of subsets where primary and parallel each have same sign
as their respective baselines.

### Source Perturbation (Direct vs Rollup)

For M states where both baseline (direct) and replacement (rollup) source records
resolve as eligible, nonsuppressed, and nonmissing:

ordered_rollup_state_codes: the M state codes in the order where disagreement
between sources is resolved.

Enumerate all 2^M replacement scenarios:
- Each scenario is a bitmask where bit j = 1 means state j uses rollup, 0 uses direct
- scenario_count = 2^M

Group scenarios by replacement_count k = 0, 1, ..., M:
- by_replacement_count[k]: count of scenarios, min/max coefficient, min/max HC3 p-value,
  mean absolute percent shift

Stable scenario: coefficient sign matches the all-direct baseline sign AND
HC3 p-value does not cross the declared threshold (typically 0.05).

maximum_shift_bitmask: the bitmask of the scenario with largest absolute percent shift.
maximum_shift_replaced_state_codes: states with bit=1 in that bitmask, in disagreement order.

### Shapley Attribution

For each state j among the M:
- shapley_j = average marginal coefficient change from replacing state j,
  averaged over all M! coalition orders
- Compute exactly via the factorial formula or exhaustive enumeration

shapley_sum = sum of all signed_shapley_coefficient_change values.
This must equal all_rollup_coefficient - all_direct_coefficient.

ordered_shapley_effects: one per state in disagreement order, with signed
coefficient change.

## Difference GMM Mediation

**Registered name:**
- STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION_WITH_CROSS_EQUATION_DELTA_INFERENCE

### Model Equations

Three equations, all in first differences:

1. TOTAL: delta_outcome ~ delta_exposure + delta_controls + period_indicator
2. PATH_A: delta_mediator ~ delta_exposure + delta_controls + period_indicator
3. DIRECT+PATH_B: delta_outcome ~ delta_exposure + delta_mediator + delta_controls + period_indicator

Instruments: lagged levels (typically lag 2) of the endogenous change variables.

### Two-Step GMM Estimation

Step 1: Identity weight matrix. Compute residuals.
Step 2: Optimal weight matrix from step-1 residuals.
Final: cluster-robust (state-clustered) standard errors.

### Cross-Equation Delta Method

Indirect effect = path_a_coefficient * path_b_coefficient.
cross_equation_correction: accounts for covariance between equations.
a_b_covariance = estimated covariance between path_a and path_b coefficients.

Var(indirect) = b^2 * Var(a) + a^2 * Var(b) + 2*a*b * Cov(a,b)
95% CI: indirect +/- 1.96 * sqrt(Var(indirect))

### First-Stage Partial F

For each endogenous variable, compute the partial F-statistic from the first-stage
regression of the differenced variable on all instruments (including exogenous controls).
Report for delta_poverty and delta_inactivity (or as named in the protocol).

### Hansen J Overidentification Test

J = T * gbar^T * W * gbar where gbar are sample moments.
Null: overidentifying restrictions are valid.
Chi-squared with (num_instruments - num_parameters) degrees of freedom.

### Leave-One-State-Out Diagnostics

For each state:
1. Drop all observations from that state
2. Refit the complete three-equation system
3. Report indirect effect and direct poverty coefficient (or as specified)

## Delete-State Two-Step GMM (Panel)

**Registered name:** DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM

Single-equation two-step GMM with state-clustered standard errors. Instruments are declared
in the protocol. First step uses identity weighting; second step uses optimal weighting from
first-step residuals.

For S states:
- Full model fit on all states: coefficients beta_full, Hansen J_full
- For each state s: delete all panel rows, refit: coefficients beta_-s, Hansen J_-s
- beta_bar = (1/S) * sum(beta_-s)
- bias_corrected beta_BC = S*beta_full - (S-1)*beta_bar
- maximum_absolute_delete_state_shifts per coefficient

Report full coefficients, bias-corrected coefficients, and per-state diagnostics.

## Sensitivity Analysis

**Registered name:** PARTIAL_R2_MEDIATION_SENSITIVITY_SURFACE

### Baseline Quantities

- baseline_path_a: coefficient from path-a model (exposure -> mediator)
- baseline_path_b: coefficient from direct model (mediator -> outcome, with exposure controlled)
- baseline_path_b_se: standard error of path-b coefficient
- residual_df: residual degrees of freedom from direct model
- baseline_indirect = baseline_path_a * baseline_path_b

### Surface Computation

For each (r2_mediator, r2_outcome, bias_direction) in the declared grids:

- The bias factor adjusts path_b for unobserved confounding strength
- Adjusted path_b and adjusted indirect are computed from the bias factor
- Proportion = adjusted_indirect / baseline_indirect

### Tipping Point

Equal-strength tipping R2: the smallest R2 where r2_mediator = r2_outcome = R2 and
the indirect effect changes sign. Found by scanning declared R2 values.

## Source Group Perturbation

**Registered name:** NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT

### Procedure

1. Establish reference: full-model pooled OOF RMSE from nested CV
2. For each declared source_group in order:
   a. Remove the specified terms from the model
   b. For each outer fold, refit WITHOUT re-tuning hyperparameters (use full-model selected values)
   c. Compute outer-fold RMSE for each fold
   d. pooled_rmse = sqrt(mean of squared errors pooled across all folds)
   e. rmse_deterioration = grouped_pooled_rmse - reference_pooled_rmse
   f. worse_fold_count = number of outer folds where group RMSE exceeds reference fold RMSE
   g. deterioration_rank: 1 = largest deterioration; ties broken by declared group order

## Controlled Decision Logic

1. Complete every module before evaluating any gate
2. Evaluate each gate predicate on UNROUNDED computed values
3. Preserve the declared module precedence order for gate reporting
4. Count satisfied gates
5. Apply the effective decision rule mapping from the request

If a module fails before producing outputs, treat its gate as FAIL and record that
module as the first_failed_module.
