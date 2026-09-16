# Statistical Module Specifications

This document defines the computational methods for each module type
encountered across PHO algorithmic audit protocols. Implement each module
exactly as specified; do not substitute variants or approximations unless
the task's analysis_request explicitly permits it.

---

## Table of Contents

- [Module 1](#module-1:-release-resolution-and-cohorts)
- [Module 2](#module-2:-delete-cluster-fixed-effects-two-way-fe-ols-jackknife)
- [Module 3](#module-3:-nested-grouped-ridge--elastic-net-cross-validation)
- [Module 4](#module-4:-wild-cluster-bootstrap-restricted-null)
- [Module 5](#module-5:-grouped-split-conformal-prediction)
- [Module 6](#module-6:-trajectory-pca-and-clustering)
- [Module 7](#module-7:-source-perturbation-stability-audit)
- [Module 8](#module-8:-difference-gmm-mediation)
- [Module 9](#module-9:-mediation-sensitivity-surface)
- [Module 10](#module-10:-controlled-decision)

---


## Module 1: Release Resolution and Cohorts

**Purpose**: Apply publication filtering, revision resolution, and cohort
construction rules to produce the analytic datasets for all downstream modules.

**Method**: The release resolution rules in
[data_resolution.md](data_resolution.md) and cohort construction rules in
[cohort_construction.md](cohort_construction.md) are the canonical
specification for this module.

**When requested by the audit**, report:
- Total resolved observation/record counts by dataset
- Yearly complete-case counts
- Balanced panel dimensions and excluded entity lists
- Broad/reference cohort sizes

---

## Module 2: Delete-Cluster Fixed Effects (Two-Way FE OLS Jackknife)

**Purpose**: Estimate a fixed-effects model and assess coefficient stability
through delete-one-cluster jackknife inference.

**Appears in**: State-level transport audits, reliability-weighted audits,
county panel audits (as delete-state GMM or WLS variants).

### Data Preparation

For the specified cohort, construct the design matrix X and outcome vector y.
Sort rows by entity code then time.

**Two-way fixed effects transformation (standard double-demeaning)**:
For each modeled variable z (both outcome and predictors), compute:

```
z_dd[it] = z[it] - zbar_entity[i] - zbar_time[t] + zbar_grand
```

where `zbar_entity[i]` is the mean over all time periods for entity i,
`zbar_time[t]` is the mean over all entities for time t, and `zbar_grand`
is the overall mean.

### Full-Model Fit

Fit OLS *without an intercept* on the double-demeaned data. The predictors
are in the exact order declared by the request. Use standard OLS: solve
the normal equations `b = inv(X'X) * X'y`.

### Delete-One-Cluster Jackknife

For each cluster g (state, division, or other declared grouping):

1. Remove all rows belonging to cluster g.
2. Recompute every entity mean, time mean, and grand mean on the reduced
   dataset (this shifts all remaining observations).
3. Refit OLS from scratch on the reduced, re-demeaned data.
4. Record the coefficient vector `b_-g` for the target predictor.

After all G clusters are processed:

- **Mean of delete estimates**: `bbar = (1/G) * sum_g(b_-g)`
- **Jackknife standard error**: `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))`
- **Bias-corrected coefficient**: `b_BC = G*b - (G-1)*bbar`
- **Jackknife t-statistic**: `t_JK = b / SE_JK` (using the full-model
  coefficient, not the bias-corrected one)
- **Jackknife p-value**: two-sided from Student's t distribution with
  `G-1` degrees of freedom
- **Minimum delete coefficient**: the smallest `b_-g` value
- **Maximum delete coefficient**: the largest `b_-g` value
- **Extreme deletions**: report the state/division name matching the
  minimum and maximum coefficients

**Weighted variant**: When the request specifies reliability weighting
(e.g., sample_size weights), apply the declared weights in the OLS
normal equations: `b = inv(X'WX) * X'Wy` where W is a diagonal matrix of
the declared weights. The jackknife formulas use the weighted coefficients.

### GMM Variant (County Panel, Delete-State)

When the module specifies two-step GMM with instruments:

1. First step: compute the optimal weighting matrix from a consistent
   initial estimate (e.g., 2SLS).
2. Second step: GMM using that weighting matrix.
3. Report Hansen J statistic for overidentification test.
4. Jackknife: delete one state at a time, recompute full two-step GMM,
   and apply the same bias-correction formulas to each dynamic-term
   coefficient.

---

## Module 3: Nested Grouped Ridge / Elastic Net Cross-Validation

**Purpose**: Assess out-of-sample predictive performance using nested
leave-one-group-out cross-validation with regularized regression.

**Appears in**: All protocol families, as ridge or elastic net variants.

### Nested Ridge CV (Leave-One-Division-Out)

**Folds and data splits**:

For a declared grouping (e.g., census division):

1. **Outer loop**: Hold out one group as test; the remaining groups form
   the outer-training set.
2. **Inner loop (within outer-training)**: For each remaining group, hold
   it out as validation; all other remaining groups form inner-training.
   Process inner groups in the same sorted order.

**Standardization** (training-only):

For every fit (both inner and outer):
1. Compute the mean and sample standard deviation (ddof=1) of each feature
   using ONLY the training rows.
2. Subtract training mean from each training, validation, and test row.
3. Divide by training sample SD for each training, validation, and test row.
4. Center the outcome by subtracting the training outcome mean.

**Coordinate-descent ridge solver**:

Parameters: `lambda >= 0` (penalty), `tol` (convergence tolerance),
`max_sweeps` (iteration cap).

1. Initialize all coefficients `b_j = 0`.
2. Keep the intercept unpenalized.
3. For each sweep, cycle through features in declared order. For feature j:
   - Compute partial residuals: `r_ij = y_i - a - sum_{k != j} x_ik * b_k`
   - Update: `b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n * lambda)`
   where n is the number of training rows.
4. After a full sweep, if the maximum absolute coefficient change is below
   `tol`, stop. Otherwise continue to the next sweep, up to `max_sweeps`.
5. After convergence, recompute the intercept: `a = mean(y) - mean(X*b)`.

**Lambda selection**:

1. For each lambda in the grid, run inner CV: fit on each inner-training
   set, predict the inner-validation set, and pool all inner-validation
   squared errors.
2. Compute RMSE = sqrt(mean of pooled squared errors).
3. Choose the lambda with the smallest RMSE. If tied, choose the smaller
   lambda value.
4. Refit on ALL outer-training rows using the selected lambda, then
   predict the held-out outer-test rows.

**Aggregation**:

- Each row receives exactly one outer prediction (when its group was
  the held-out test group).
- **Pooled RMSE**: sqrt(mean of all outer squared errors)
- **Pooled MAE**: mean of all outer absolute errors
- **Pooled Q-squared (R-squared)**: `1 - SSE_pooled / SST_full`
  where SSE_pooled = sum of all outer squared errors and SST_full =
  sum of squared deviations of the full-sample outcome from its mean.
- **Worst division**: the outer fold with the highest outer RMSE.

### Nested Elastic Net CV

Similar structure but with an alpha/l1_ratio grid instead of a single
lambda grid.

**Standardization**: Training-only, same as ridge. Continuous terms are
standardized; indicator (dummy) terms are not.

**Parameters**: `alpha` (overall penalty strength), `l1_ratio` (0 = ridge,
1 = lasso, values in between = elastic net).

**Grid**: Cartesian product of alpha values and l1_ratio values.

**Selection**: For each outer fold, evaluate every (alpha, l1_ratio)
combination via inner CV. Select the combination with the smallest
inner RMSE; tiebreak by smallest alpha, then smallest l1_ratio.

**Coordinate cycle**: The elastic net coordinate update combines L1 and L2
penalties. For feature j with penalty alpha and l1_ratio rho:

```
b_j = S(sum_i(x_ij * r_ij), n * alpha * rho) / (sum_i(x_ij^2) + n * alpha * (1-rho))
```

where S(z, gamma) is the soft-thresholding operator:
`S(z, gamma) = sign(z) * max(0, abs(z) - gamma)`

The intercept remains unpenalized.

**Reporting**: For each outer fold, report the selected alpha, l1_ratio,
standardized coefficients (with zeros for unselected features), and outer
RMSE. Pool predictions as in ridge to compute OOF RMSE and R-squared.

---

## Module 4: Wild Cluster Bootstrap (Restricted Null)

**Purpose**: Test a target coefficient under a restricted null using
cluster-robust wild bootstrap with parametric null imposition.

**Appears in**: All protocol families. PRNG variants include PCG32 and
XORSHIFT32.

### Observed Fit and CR1 Variance

Using the same double-demeaned design matrix as the fixed-effects module
(or the specified model matrix):

1. Fit the full unrestricted model by OLS. Record the target coefficient
   `b` and the residual vector `e`.
2. Compute cluster scores: for each cluster g, `s_g = X_g' * e_g`
   where `X_g` are the rows of cluster g and `e_g` are the corresponding
   residuals.
3. Compute CR1 variance:
   ```
   V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * inv(X'X) * sum_g(s_g * s_g') * inv(X'X)
   ```
   where G = number of clusters, n = total observations, k = number of
   predictors (including intercept if applicable).
4. Extract the standard error for the target coefficient from the diagonal
   of V_CR1.
5. Studentize: `t_obs = b / SE_CR1`.

### Restricted Model Fit

Fit the model *without* the target predictor. Retain:
- Restricted fitted values `y_hat_r`
- Restricted residuals `e_r`

### PCG32 PRNG (used with PCG32_WEBB variant)

The generator uses unsigned 64-bit wraparound arithmetic with 32-bit output.

**Initialization**:
```
state = 0
increment = 2 * stream + 1
// Advance once
state = state * 6364136223846793005 + increment (mod 2^64)
// Add seed
state = (state + seed) mod 2^64
// Advance once more
state = state * 6364136223846793005 + increment (mod 2^64)
```

**Each advance**:
```
old = state
state = old * 6364136223846793005 + increment (mod 2^64)
xorshifted = low32(((old >> 18) XOR old) >> 27)
rot = old >> 59
output = rotate_right_32(xorshifted, rot)
```

The `low32` function takes the lower 32 bits. `rotate_right_32` rotates a
32-bit value right by `rot` bits (rot is in 0..63, use rot mod 32).

**Weight mapping (Webb six-point)**:
Map the 32-bit output modulo 6. Assign weights in order:
`0 -> -sqrt(3/2)`, `1 -> -1`, `2 -> -sqrt(1/2)`,
`3 -> sqrt(1/2)`, `4 -> 1`, `5 -> sqrt(3/2)`.

### Xorshift32 PRNG (used with XORSHIFT32 variant)

The generator maintains a single 32-bit state. Initialize the state with
the declared seed value (if the seed is 0, use a non-zero convention to
avoid the zero trap).

Standard xorshift32 core:
1. `state ^= state << 13`
2. `state ^= state >> 17`
3. `state ^= state << 5`
4. Output is the resulting state.

**Weight mapping**: Map the 32-bit output to weights. Typically this uses
the Rademacher distribution: if the highest bit is 1, use weight +1;
otherwise use weight -1. Always consult the request for the exact
mapping (some variants use different distributions).

### Bootstrap Procedure

Maintain one continuous PRNG throughout. Do not reset between replicates.

For each replicate b = 1 through B:

1. Draw one weight per cluster in entity-code order (stable order).
2. Construct the bootstrap outcome:
   `y*_it = y_hat_r[it] + e_r[it] * w_g`
   where `w_g` is the single weight for cluster g (same for all
   observations within the cluster).
3. Refit the full unrestricted model on (X, y*).
4. Recompute CR1 variance on the bootstrap fit.
5. Studentize: `t*_b = b*_target / SE*_CR1`.
6. If the request requires checkpoints at specific replicate numbers,
   record the PRNG state and the t-statistic immediately after completing
   that replicate (do not reset the PRNG stream for checkpoints).

### Test Summary

Count the number of replicates where `abs(t*_b) >= abs(t_obs)`:
`exceedance_n = count(abs(t*_b) >= abs(t_obs))`

Bootstrap p-value (plus-one convention):
`p_boot = (exceedance_n + 1) / (B + 1)`

**Batch exceedance counts**: When the request asks for batch counts,
divide the B replicates into consecutive batches of equal size (or as
close as possible). Report the exceedance count within each batch in order.

### Bootstrap Coefficient Distribution

- **Bootstrap coefficient mean**: mean of all `b*_target` across replicates
- **Bootstrap coefficient sample SD**: sample SD (ddof=1) of `b*_target`

### Bootstrap t Quantiles

For sorted values x[0..B-1] and probability p:
nearest-rank = x[min(B, ceil(p * B)) - 1] (one-based rank)

---

## Module 5: Grouped Split Conformal Prediction

**Purpose**: Construct prediction intervals with finite-sample coverage
guarantees using split conformal inference with grouped cross-validation.

**Appears in**: State and county transport audits.

### Data and Model

Use the same cohort and feature matrix as the nested ridge module. Fit
ridge with the declared fixed penalty (lambda) parameter.

### Partition Scheme

For each ordered outer group (e.g., census division) as the test set:

1. From the *remaining* groups, select the calibration group as the one
   with the greatest row count. If tied, use ascending group name order.
2. All other remaining groups form the proper training set.

### Fit and Calibration

1. Fit ridge on the proper training set using the fixed lambda and the
   training-only standardization rules from Module 3.
2. Predict on the calibration set and compute absolute residuals:
   `r_i = abs(y_i - yhat_i)`.
3. Sort the m calibration absolute residuals ascending.

### Interval Construction

For nominal coverage `1 - alpha`:
```
r = min(m, ceil((m + 1) * (1 - alpha)))
q = sorted_residuals[r - 1]  // 0-based indexing
```

Prediction interval for a test point with prediction `yhat`:
`[yhat - q, yhat + q]` (inclusive bounds)

### Coverage and Width

- **Fold coverage**: fraction of test points whose observed value falls
  within the interval.
- **Fold mean width**: mean interval width = `2 * q` for that fold.
- **Fold test MAE**: mean absolute error on the test set.
- **Aggregate coverage**: weighted by test row counts across folds.
- **Aggregate mean width**: weighted by test row counts across folds.

**State-grouped conformal** (for county panels):
When the grouping is by state and the model uses OOF predictions from a
prior nested module, the calibration data comes from cross-fold residuals.

---

## Module 6: Trajectory PCA and Clustering

**Purpose**: Reduce multi-year, multi-variable trajectories to principal
components and cluster entities using k-means, with leave-one-out stability
assessment.

**Appears in**: All protocol families (state, county, country levels).

### PCA via Symmetric Jacobi

**Data matrix construction**:

Build the data matrix Z where columns are ordered variable-major then
time. For example, with features (A, B) and years (2020, 2021, 2022),
columns are: A_2020, A_2021, A_2022, B_2020, B_2021, B_2022.

Standardize each column to mean 0, sample SD 1 (ddof=1).

Form the covariance matrix: `C = Z'Z / (n - 1)` where n is the number of
entities.

**Jacobi eigenvalue decomposition**:

Initialize eigenvectors V = identity matrix.

Repeat until convergence or step cap:

1. Find the largest absolute value in the upper triangle of C (off-diagonal
   only). Track the position (p, q) with p < q. Break ties by lower row
   index p, then lower column index q.
2. Compute Jacobi rotation for element C[p,q]:
   ```
   tau = (C[q,q] - C[p,p]) / (2 * C[p,q])
   t = sign_nonnegative(tau) / (abs(tau) + sqrt(1 + tau^2))
   c = 1 / sqrt(1 + t^2)
   s = t * c
   ```
3. Apply rotation: update C and V using the standard Jacobi rotation
   formulas. Only rows/columns p and q are affected.
4. Stop when the maximum absolute off-diagonal is below the convergence
   tolerance, or when the step cap is reached.

**Post-processing**:

1. Extract eigenvalues from the diagonal of C. Sort components by
   descending eigenvalue; tiebreak by original diagonal index (ascending).
2. For each loading (eigenvector), flip its sign so the element with the
   earliest maximum absolute value is positive.
3. Scores: `S = Z * V` (using the sorted, sign-flipped loadings).

### K-Means Clustering

On the leading k principal component scores:

**Initialization**:
1. First centroid: the entity that comes first in ASCII order.
2. For each subsequent centroid: pick the entity that maximizes the
   minimum squared Euclidean distance to all previously chosen centroids.
   Tiebreak by entity code (ascending).

**Lloyd iteration**:
1. Assign each entity to the nearest centroid (minimum squared Euclidean
   distance). Tiebreak by lower working cluster id.
2. Update each centroid to the mean of its assigned members.
3. Repeat until assignments are unchanged or the iteration cap is reached.

**Canonicalization**: After convergence, assign stable cluster ids by
sorting centroids lexicographically (PC1, then PC2, ...) and mapping
old working ids to the new sorted order.

### Leave-One-Out Stability

For each omitted time block (year) in ascending order:

1. Rebuild the data matrix without columns belonging to the omitted time
   block (remove the corresponding features from all variables).
2. Repeat standardization, PCA, loading sign-flip, centroid initialization,
   and k-means clustering from scratch.
3. Compute the Adjusted Rand Index between the full-data clustering and
   the leave-one-out clustering.

**Adjusted Rand Index**:

Build the contingency table `n_ij` where rows are full-data clusters and
columns are leave-one-out clusters.

```
sum_comb = sum_i sum_j C(n_ij, 2)
expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)
max_index = 0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2))
ARI = (sum_comb - expected) / (max_index - expected)
```

where `C(x, 2) = x*(x-1)/2`, `a_i` = row sums, `b_j` = column sums, `n`
= total entities.

**Label alignment**: Align refit cluster labels to the full-data labels by
maximum agreement (largest number of matching assignments). Tiebreak by the
lexicographically smallest permutation.

### County-Level Trajectory Variant

For county-level trajectories:
- Variables are changes (deltas) rather than levels
- Column ordering: variable-major, then end-year within each variable
- Stability is assessed by deleting one state at a time (all counties in
  that state), not by omitting years
- The cluster grid evaluates candidate cluster counts (e.g., 2 through 6)
  and selects the one with the highest average silhouette score

**Silhouette score** for cluster count k:
For each entity i in cluster C_I:
- `a_i` = mean distance to other entities in C_I
- `b_i` = minimum mean distance to entities in any other cluster
- `s_i = (b_i - a_i) / max(a_i, b_i)`
- Average silhouette = mean of all `s_i`.

---

## Module 7: Source Perturbation (Stability Audit)

**Purpose**: Assess whether the primary finding is stable when the data
source, time window, or predictor set is perturbed.

**Appears in**: All protocol families with protocol-specific variants.

### Source Year Perturbation (State)

For primary and parallel (alternate-source) exposure series:

1. Enumerate all time subsets of the specified sizes. For example, with
   years {2020,2021,2022,2023,2024} and sizes {3,4,5}, enumerate all
   subsets in increasing size order, then lexicographic tuple order within
   each size.
2. For each subset, keep the strict dual-source cohort fixed (entities
   complete for both series in all years of the FULL set, not just the
   subset). Subset only the time dimension of the refit.
3. Refit the full double-demeaned model using the primary series, compute
   CR1 variance, and record the coefficient and two-sided p-value.
4. Repeat with the parallel series.
5. For each subset, compute the absolute percent shift:
   `shift = abs(b_alt - b_primary) / abs(b_primary) * 100`
6. A shift is "same-sign" if both coefficients are nonzero with the same
   sign.
7. Report the median of ordered shifts. Choose the worst subset by
   greatest unrounded shift, then by earlier subset order.

### Source Group Perturbation (County Panel)

For ordered groups of predictor terms:

1. Establish the reference OOF RMSE from the full model.
2. Remove each source group's terms entirely from the design matrix (no
   retuning of hyperparameters — reuse the full model's selected values).
3. For each group deletion, run the nested outer-fold procedure and
   compute per-fold RMSEs, pooled RMSE, and deterioration:
   `deterioration = pooled_rmse - reference_rmse`.
4. Count how many outer folds got worse (higher RMSE).
5. Rank groups by descending deterioration; tiebreak by worse-fold count
   (descending), then by declared group order.

### Exhaustive Direct/Rollup Source Perturbation (State)

For a baseline (direct-survey) and replacement (rollup) outcome source:

1. Identify states where BOTH the direct and rollup records resolve as
   eligible (nonsuppressed, nonmissing) for the reference year.
2. Enumerate all 2^M scenarios (where M = count of dual-eligible states),
   each defined by which states use the rollup source.
3. For each scenario, refit the full model and record the target
   coefficient and HC3 p-value.
4. A scenario is "stable" if the coefficient's sign matches the baseline
   and the HC3 p-value remains below 0.05.
5. Group results by replacement count. Report the scenario with the
   maximum absolute percent shift in the target coefficient.
6. Compute exact Shapley effects: for each state, the Shapley value is
   the average marginal change in the target coefficient when that
   state switches from direct to rollup, averaged over all possible
   orderings of the M states. Validate that the Shapley sum equals
   `coeff(all_rollup) - coeff(all_direct)`.

---

## Module 8: Difference-GMM Mediation

**Purpose**: Estimate a mediation model using first-differenced GMM with
state-clustered standard errors and cross-equation delta-method inference
for the indirect effect.

**Appears in**: County mediation audits.

### Model Structure

Three equations estimated simultaneously:

1. **Total effect**: outcome (first-differenced) on exposure (first-
   differenced), controls (first-differenced), and period indicator.
2. **Path a**: mediator (first-differenced) on exposure (first-differenced),
   controls, period indicator, and lagged-level instruments.
3. **Path b / Direct**: outcome (first-differenced) on mediator (first-
   differenced), exposure (first-differenced), controls, period indicator,
   and lagged-level instruments for the mediator.

### First-Stage Diagnostics

Report partial F-statistics for the excluded instruments in each
first-differenced equation. These test whether the lagged-level instruments
have sufficient predictive power.

### Stacked Indirect Effect

Indirect effect = (path-a coefficient) * (path-b coefficient).

Cross-equation correction: the sampling covariance between the path-a and
path-b coefficient estimates, accounting for the GMM moment structure.

Delta-method standard error:
```
SE_indirect = sqrt(a^2 * var(b) + b^2 * var(a) + 2*a*b*cov(a,b))
```

Confidence interval: `estimate +/- t_critical * SE_indirect` using
state-clustered degrees of freedom.

### Leave-One-State-Out Diagnostics

For each state in the cohort:
1. Delete all county observations belonging to that state.
2. Re-estimate the full difference-GMM system from scratch.
3. Report the re-estimated indirect effect and direct poverty coefficient.

---

## Module 9: Mediation Sensitivity Surface

**Purpose**: Assess how sensitive the mediation finding is to unobserved
confounding using the partial-R2 parameterization.

**Appears in**: County mediation audits.

### Baseline Quantities

From the primary OLS models:
- `a` = path-a coefficient (exposure -> mediator, controlling for shared terms)
- `b` = path-b coefficient (mediator -> outcome, controlling for exposure
  and shared terms)
- `SE_b` = classical standard error of path-b
- `df` = residual degrees of freedom from the direct (path-b) model

### Sensitivity Surface

For each combination of `(R2_mediator, R2_outcome, bias_direction)` in
the declared grid:

The confounder is parameterized by:
- R2_M: how much of the mediator's residual variance the confounder
  explains (after accounting for observed covariates)
- R2_Y: how much of the outcome's residual variance the confounder
  explains

For bias direction NEGATIVE:
```
adjusted_a = a * (1 - sqrt(R2_M))
adjusted_b = b * (1 - sqrt(R2_Y))
```

For bias direction POSITIVE:
```
adjusted_a = a * (1 + sqrt(R2_M))
adjusted_b = b * (1 + sqrt(R2_Y))
```

Adjusted indirect = adjusted_a * adjusted_b.
Adjusted direct = unchanged (the direct path is assessed under the
confounding of the path-b equation).

Proportion mediated = adjusted_indirect / (adjusted_indirect + adjusted_direct).

### Equal-Strength Tipping Point

Find the smallest R2 value (same for mediator and outcome, with bias
direction NEGATIVE) at which the adjusted indirect effect sign flips
from the baseline sign (i.e., crosses zero). This is reported as the
"tipping R2."

---

## Module 10: Controlled Decision

**Purpose**: Apply the gated decision rules to produce the final audit
classification.

**Appears in**: Every protocol.

### Decision Procedure

1. Complete every declared audit module.
2. Evaluate each business predicate (gate) on *unrounded* computed values.
3. Record each gate as PASS or FAIL.
4. Count the number of satisfied gates.
5. Apply the precedence-based decision mapping from the analysis request.

**Gate evaluation examples** (the exact predicates come from the request):

- `FULL_EXPOSURE_COEFFICIENT_IS_NEGATIVE_AND_JACKKNIFE_P_VALUE_IS_AT_MOST_0_05`
  -> PASS if full coefficient < 0 AND jackknife p-value <= 0.05
- `POOLED_Q_SQUARED_IS_AT_LEAST_0_85_AND_POOLED_RMSE_IS_AT_MOST_0_75`
  -> PASS if q_squared >= 0.85 AND pooled_rmse <= 0.75
- `BOOTSTRAP_P_VALUE_IS_AT_MOST_0_05`
  -> PASS if plus-one bootstrap p-value <= 0.05
- Source / trajectory / sensitivity stability gates follow similar
  pattern.

**Decision mapping**: Apply the declared classification rules in precedence
order. The first matching rule determines the output classification.
If no specific rule matches, the catch-all rule applies.

---

## General Implementation Notes

### Numerical Stability

- Use double-precision floating point throughout.
- For matrix inversion, use a numerically stable method (e.g., solve
  linear system rather than explicit inverse when possible).
- For the coordinate-descent solvers, scale features to comparable ranges
  through the standardization step rather than through ad-hoc scaling.

### Sorting and Ordering

- **State codes**: two-letter uppercase, sorted ASCII ascending.
- **County FIPS**: five-digit text, sorted ASCII ascending.
- **ISO3**: three-letter uppercase, sorted ASCII ascending.
- **Years**: integer ascending.
- **Division names**: exactly as they appear in `/geographies/states`.
- **Feature order**: exactly as declared in the analysis request.

### PRNG Consistency

- Never reset a PRNG stream mid-module unless the request explicitly
  declares a reset point.
- For checkpointing, record the state *after* completing the replicate,
  not before.
- Different modules use independent PRNG instances with their own seeds.
