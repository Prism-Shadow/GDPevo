# Statistical Module Reference

Detailed specifications for every registered statistical module. Implement these exactly — the portal audit expects bitwise-reproducible results.

## Table of Contents

1. [Delete-Cluster Fixed Effects](#delete-cluster-fixed-effects)
2. [Nested Ridge Division CV](#nested-ridge-division-cv)
3. [Nested Elastic Net](#nested-elastic-net)
4. [Wild Cluster Bootstrap](#wild-cluster-bootstrap)
5. [Grouped Split Conformal](#grouped-split-conformal)
6. [Trajectory PCA Clustering](#trajectory-pca-clustering)
7. [Source Year/Group Perturbation](#source-yeargroup-perturbation)
8. [Difference GMM Mediation](#difference-gmm-mediation)
9. [Mediation Sensitivity Surface](#mediation-sensitivity-surface)

---

## Delete-Cluster Fixed Effects

### Within transformation

For each modeled variable `z_it` (outcome and each predictor):

```
z_transformed = z_it - entity_mean(z) - time_mean(z) + grand_mean(z)
```

Where entity mean is the mean of z for entity i across all its observations, time mean is the mean of z for period t across all entities, and grand mean is the overall mean.

### OLS without intercept

Fit the transformed outcome on transformed predictors using OLS with no intercept. Solve in declared predictor order.

### Delete-one jackknife

For G clusters (states/divisions):

1. For each cluster g, remove all observations belonging to that cluster.
2. Recompute all means from the remaining observations (not from the original full sample).
3. Re-fit OLS without intercept.
4. Record the coefficient `b_-g`.

Compute:

```
bbar = mean(b_-g over all g)
SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))
b_BC = G * b_full - (G-1) * bbar
t = b_BC / SE_JK
p = 2 * (1 - cdf_t(|t|, G-1))
```

Use the two-sided Student t distribution with G-1 degrees of freedom.

For state-level audits, the coefficient of interest is the primary exposure. For division-level audits, the coefficient of interest is the target predictor from the weighted model (see Weighted Fixed Effects below).

### Weighted Fixed Effects

When the request specifies reliability or population weighting:
- Weight each observation by sqrt(weight) before the within transformation
- Follow the same double-demeaning, OLS, and jackknife procedures on the weighted data

### Extreme deletions

Report the entity code with the smallest delete-one coefficient (most negative effect from removing it) and the largest (least negative / most positive effect).

---

## Nested Ridge Division CV

### Outer/inner structure

- Outer folds: hold out one group (e.g., census division) at a time, in declared group order.
- Inner folds: within each outer training set, hold out each remaining group once, in the same order.
- For each inner fold, fit ridge with each lambda from the grid.

### Standardization

For every fit (inner and final outer refit):

1. Subtract training-only feature means from all training rows.
2. Divide by training sample standard deviation (ddof=1).
3. Apply the same training moments to validation/test rows.
4. Do not standardize the outcome (only center it).

### Coordinate descent solver

Center the training outcome `y`. Keep the intercept unpenalized: `a = mean(y - X @ b)`. Initialize all `b_j = 0`.

For each cycle, update coefficients in declared feature order:

```
r_ij = y_i - a - sum_{k != j} X_ik * b_k    (residual excluding feature j)
b_j = sum_i(X_ij * r_ij) / (sum_i(X_ij^2) + n * lambda)
```

After each sweep, recompute `a`. Stop when `max(|b_new - b_old|) < tolerance` or at the sweep cap (default 10000). Default tolerance is 1e-6.

### Lambda selection

For each outer fold, pool all inner validation squared errors at row level. Take RMSE for each lambda. Select the lambda with smallest inner RMSE; tie-break by smaller lambda value. Refit on all outer-training rows with the selected lambda. Predict the held-out outer test rows.

### Pooled metrics

Pool exactly one prediction per eligible row across all outer folds. Compute:

```
pooled_rmse = sqrt(mean((y_true - y_pred)^2))
pooled_mae = mean(|y_true - y_pred|)
pooled_q_squared = 1 - SSE_pooled / SST_full_sample
```

Where SST is computed on the full sample outcome (centered).

### Worst outer division

The division with the largest outer-fold RMSE.

---

## Nested Elastic Net

### Standardization

Same training-only standardization as ridge. Continuous terms are standardized; indicator terms (RUCC dummies, year dummies) are not standardized but are included in the design matrix.

### Coordinate descent with elastic net penalty

For objective: `(1/(2n)) * sum((y - a - Xb)^2) + lambda * (alpha * L1 + 0.5 * (1-alpha) * L2)`

Update for continuous/indicator feature j:

```
r_ij = y_i - a - sum_{k != j} X_ik * b_k
z_j = (1/n) * sum_i(X_ij^2) + lambda * (1 - alpha)
b_j_ols = (1/n) * sum_i(X_ij * r_ij) / z_j
b_j = soft_threshold(b_j_ols, lambda * alpha / z_j)
```

Where `soft_threshold(x, t) = sign(x) * max(0, |x| - t)`.

Update for intercept: `a = mean(y - X @ b)` after each sweep.

### Grid search

For each (alpha, l1_ratio) pair in the declared grid, run nested CV. The inner grouping mirrors the outer grouping: within each outer training set, hold out each remaining group once. Select the hyperparameters minimizing inner RMSE; tie-break by smaller alpha, then smaller l1_ratio.

### OOF metrics

Pool predictions as in ridge CV. Report RMSE, MAE, and R-squared.

---

## Wild Cluster Bootstrap

### PCG32 PRNG

A 64-bit state, 32-bit output generator.

```
increment = 2 * stream + 1  (odd)
state = 0
advance once
state = (state + seed) mod 2^64
advance
```

Each advance:
```
old = state
state = (old * 6364136223846793005 + increment) mod 2^64
xorshifted = low32( ((old >> 18) xor old) >> 27 )
rot = old >> 59
output = rotate_right_32(xorshifted, rot)
```

Where `low32(x)` returns the lower 32 bits of x, and `rotate_right_32(x, n)` rotates a 32-bit value right by n bits.

Map output modulo 6 to weights: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.

### XORSHIFT32 PRNG

Standard xorshift32: 32-bit state, 32-bit output.

```
state = seed
xorshift32():
    state ^= state << 13
    state ^= state >> 17
    state ^= state << 5
    return state
```

Map each 32-bit output: take the lower 4 bits (modulo 16) and assign to {-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8} if value < 11, else discard and draw again.

### Bootstrap procedure

1. Fit the unrestricted model on the double-demeaned data. Compute CR1 standard error:

```
s_g = X_g' @ e_g  (cluster score vectors, G clusters)
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^{-1} * sum_g(s_g @ s_g') * (X'X)^{-1}
t_obs = b_target / sqrt(V_CR1[target, target])
```

2. Fit the restricted model (without the target predictor), keeping it nested in the unrestricted specification. Retain restricted fitted values and residuals.

3. For B replicates:
   - Draw one weight per cluster in entity-code order (single continuous PRNG stream)
   - Construct `y* = restricted_fitted + restricted_residual * cluster_weight`
   - Refit the unrestricted model on y*
   - Recompute CR1 for the target coefficient
   - Studentize: `t* = (b*_target - 0) / se*(b*_target)`

   The null hypothesis is that the target coefficient equals zero.

4. Record checkpoints at specified replicate numbers (PRNG state and t* value) without resetting the stream.

5. Compute p-value: `(1 + count(|t*| >= |t_obs|)) / (1 + B)`.

6. For quantiles, sort the t* values and use nearest-rank: `x[min(B, ceil(p * B)) - 1]` (one-based rank).

### PCG32 vs XORSHIFT32

PCG32 is used for state-level audits. XORSHIFT32 is used for county-level audits. The request specifies which PRNG to use. PCG32 uses a stream parameter; XORSHIFT32 does not.

---

## Grouped Split Conformal

### Partition

For each outer group g (in declared order):

1. Test set = group g.
2. Among remaining groups, choose the calibration set as the one with greatest row count; tie-break by ascending group name.
3. All other groups form the proper training set.

### Model fitting

Fit the model (ridge or elastic net) with the effective fixed penalty/hyperparameters on the proper training set only. Use the same standardization and solver rules as the corresponding CV module. Predict test and calibration rows.

### Conformal intervals

For calibration set of size m, compute absolute residuals. Sort them ascending. With miscoverage rate alpha:

```
r = min(m, ceil((m+1) * (1 - alpha)))    (one-based rank)
q = sorted_residuals[r - 1]               (zero-based index)
```

Intervals are `prediction ± q` (inclusive).

### Aggregation

Compute fold-level coverage (fraction of test points where true value falls in interval), mean width (2q), and MAE. Aggregate overall coverage and mean width by weighting each outer fold by its test row count.

---

## Trajectory PCA Clustering

### Feature construction

Build trajectory features by concatenating variables across time in the declared variable-major/time order. For example, with variables [A, B] and years [2022, 2023]: columns are `A_2022, A_2023, B_2022, B_2023`.

### PCA via covariance matrix

1. Standardize each column to mean 0, variance 1 (sample SD, ddof=1).
2. Compute `C = Z' @ Z / (n-1)`.
3. Eigendecomposition via symmetric Jacobi:

Repeat until max absolute off-diagonal < tolerance or step cap:
- Find the largest absolute off-diagonal element `A[p][q]` (p < q). Tie-break by lower p (row), then lower q (column).
- Compute rotation:
  ```
  tau = (A[q][q] - A[p][p]) / (2 * A[p][q])
  t = sign_nonnegative(tau) / (|tau| + sqrt(1 + tau^2))
  c = 1 / sqrt(1 + t^2)
  s = t * c
  ```
  Where `sign_nonnegative(x)` returns 1 if x >= 0, -1 otherwise.
- Apply rotation to A and accumulate eigenvectors.

4. Order components by descending eigenvalue. For ties, order by the original diagonal index of the eigenvalue before rotation.

5. Flip each loading vector so the element with the earliest maximum absolute value is positive.

6. Compute scores: `scores = Z @ loadings`.

### K-means clustering

On the effective leading scores (e.g., first k principal components):

1. **Initialization**: First centroid = entity whose state code is ASCII-first among all entities. Each subsequent centroid = entity maximizing minimum Euclidean distance to all existing centroids. Tie-break by ASCII-first entity code.

2. **Assignment**: Assign each entity to the nearest centroid by squared Euclidean distance. Tie-break by lower working cluster id.

3. **Update**: Recompute each centroid as the mean of its assigned members.

4. Stop when assignments are unchanged or at the iteration cap (default 100).

5. **Canonicalize labels**: Order clusters by centroid coordinates (e.g., PC1, then PC2, then PC3), then by working id. Remap assignments to canonical labels 0, 1, 2, ...

### Silhouette score

For each point i in cluster C_I:
- `a(i)` = mean distance to other points in C_I
- `b(i)` = min over other clusters C_J of mean distance to points in C_J
- `s(i) = (b(i) - a(i)) / max(a(i), b(i))`
- Average over all points for the overall silhouette.

### Leave-one-out stability

For each omitted time block or entity in declared order:

1. Rebuild the trajectory features without the omitted block/entity.
2. Re-standardize, re-run PCA, re-orient loadings, re-initialize k-means, re-cluster.
3. Compute Adjusted Rand Index between full and refit cluster assignments.

**Adjusted Rand Index**:

```
n_ij = contingency table cell (i,j) = count of entities in cluster i in partition A and cluster j in partition B
a_i = row sums, b_j = column sums
n = total entities

expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)
numerator = sum_ij C(n_ij,2) - expected
denominator = 0.5 * (sum_i C(a_i,2) + sum_j C(b_j,2)) - expected
ARI = numerator / denominator
```

Align refit labels to original labels by maximizing agreement (overlap count). For ties, choose the lexicographically smallest permutation of label mappings.

For entity-deletion stability: remove the entity, re-run, align the remaining labels, compute ARI on the intersection of entities.

---

## Source Year/Group Perturbation

### Year subset perturbation

For state-level audits: enumerate all subsets of analysis years of declared sizes. For each subset size S, enumerate all combinations of S years in lexicographic tuple order.

For each subset:
1. Keep the strict dual-source cohort unchanged (entities must be complete in all analysis years).
2. Subset observations to only those in the included years.
3. Refit the full double-demeaned model separately for the primary and parallel exposure series.
4. Compute CR1 standard errors and two-sided p-values.
5. Compute shift: `shift = |b_alt - b_baseline| / |b_baseline| * 100`.

For the baseline, use all analysis years. For aggregation: compute same-sign fraction (both baseline and alternate nonzero with same sign), median absolute percent shift, maximum shift, and worst subset (greatest unrounded shift, then earlier in subset order).

### Source group perturbation

For county-level audits: enumerate declared source groups. For each group:

1. Remove all terms belonging to that group from the model specification.
2. Reuse the outer fold structure and selected hyperparameters from the full model (no re-tuning).
3. Re-fit the model on each outer training set and predict the test set.
4. Compute outer-fold RMSEs, pooled RMSE, deterioration (= pooled_rmse_sans_group - full_pooled_rmse), worse-fold count, and rank (greatest positive deterioration gets rank 1).

### Shapley effects (optional, when requested)

For state-level rollup/direct disagreement Shapley decomposition: enumerate all 2^M subsets of the M states with disagreement. For each subset, replace direct records with rollup records for those states and refit. Compute Shapley value for each state as the average marginal effect of including that state across all subsets.

---

## Difference GMM Mediation

For county mediation audits with panel data:

### First-difference transformation

For each entity, compute changes: `Δy_i = y_{i,t} - y_{i,t-1}` for all variables.

### Two-equation system

Path A: `Δmediator = b_a * Δexposure + controls + error_a`
Path B: `Δoutcome = b_b * Δmediator + b_direct * Δexposure + controls + error_b`

### Instrumentation

Use lagged levels as instruments: exposure level at t-2 instruments Δexposure, mediator level at t-2 instruments Δmediator.

### Stacked system

Stack both equations. Estimate by GMM with the declared cluster-robust variance.

### Delta method indirect effect

Indirect effect = `b_a * b_b`. Standard error via delta method using the full coefficient covariance matrix.

---

## Mediation Sensitivity Surface

For assessing robustness of the mediation indirect effect to unobserved confounding:

### Baseline quantities

From the fitted mediation model: path-a coefficient, direct-effect coefficient, path-b standard error, direct-model residual degrees of freedom.

### Partial R² parameterization

For each combination of `R²_mediator_confounder` and `R²_outcome_confounder` from the declared grids:

Compute the bias-adjusted indirect effect under the assumption that an unobserved confounder explains the given R² of the residual variance in the mediator and outcome equations respectively. Apply the bias in the declared direction (negative = attenuates, positive = amplifies).

### Tipping point

The smallest equal-strength R² value where the indirect effect sign flips (crosses zero). Scan both directions.

---

## Controlled Decision

### Gate evaluation

Evaluate each business predicate from the request's decision rule on **unrounded** module results. Each gate produces `PASS` or `FAIL` as a string.

Examples of business predicates:
- `FULL_EXPOSURE_COEFFICIENT_IS_NEGATIVE_AND_JACKKNIFE_P_VALUE_IS_AT_MOST_0_05`
- `POOLED_Q_SQUARED_IS_AT_LEAST_0_85_AND_POOLED_RMSE_IS_AT_MOST_0_75`
- `BOOTSTRAP_P_VALUE_IS_AT_MOST_0_05`
- `AGGREGATE_COVERAGE_IS_AT_LEAST_0_80_AND_AGGREGATE_MEAN_WIDTH_IS_AT_MOST_3_25`
- `MINIMUM_LEAVE_YEAR_OUT_ADJUSTED_RAND_INDEX_IS_AT_LEAST_0_75`

### Classification

Apply the decision mapping from the request. Classifications follow a precedence order: evaluate the most stringent rule first, then fall through.
The decision is reported as a single string from the controlled vocabulary (e.g., `PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL`, `DEPLOY_DIABETES_DYNAMICS`).

For module-by-module decisions: report each gate result individually along with the first failed module and overall conclusion.
