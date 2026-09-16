# Statistical Modules

Complete reusable method catalog for PHO algorithmic audits. Every
specification is deterministic, reproducible, and fully self-contained.
These are method semantics only; instance-specific bindings (entities,
measures, time ranges, random seeds, hyperparameter grids, business cutoffs,
output names) come from the effective future analysis request.

## Table of Contents

1. [Data Publication and Cohorts](#1-data-publication-and-cohorts)
2. [Linear Algebra Primitives](#2-linear-algebra-primitives)
3. [Fixed Effects and Delete-Cluster Jackknife](#3-fixed-effects-and-delete-cluster-jackknife)
4. [Nested Ridge / Elastic-Net Cross-Validation](#4-nested-ridge--elastic-net-cross-validation)
5. [Wild Cluster Bootstrap](#5-wild-cluster-bootstrap)
6. [Grouped Split Conformal Calibration](#6-grouped-split-conformal-calibration)
7. [Trajectory PCA and Clustering](#7-trajectory-pca-and-clustering)
8. [Source Perturbation](#8-source-perturbation)
9. [Difference GMM Mediation](#9-difference-gmm-mediation)
10. [Partial-R2 Sensitivity Surface](#10-partial-r2-sensitivity-surface)
11. [Controlled Decision](#11-controlled-decision)

---

## 1. Data Publication and Cohorts

### 1.1 Release Resolution

For each publication source independently:

1. Filter records by effective `release_status`, `value_type`, `source_type`,
   `measure_id`, geographic code, and year constraints.
2. Group remaining records by `(entity_code, year, measure_id)` for health or
   `(entity_code, year, measure_id)` for socioeconomic.
3. Within each group, select the single record with:
   - Greatest `revision` number,
   - Then latest `released_at` timestamp,
   - Then lowest `observation_id` or `record_id`.
4. Count selected publications **before** analytic completeness exclusions
   when the request requires publication counts.
5. Suppressed, invalid, withdrawn, blank, or null analytic values remain
   **publication evidence** but are **unavailable** for analysis.

### 1.2 Cohort Construction

From the resolved records, build each cohort:

- **Primary/reference-year cohort**: Entities complete for all required
  fields in the reference year only.
- **Balanced panel cohort**: Intersection of entities complete for all
  required fields in every analysis year.
- **Broad cohort**: Entities complete for outcome plus all ordered features
  in the reference year.
- **Strict dual-source cohort**: Entities complete for outcome, primary
  exposure, parallel exposure, and all adjustments in every analysis year.
- **Machine-learning cohort**: Primary cohort members also complete for
  additional socioeconomic fields.

Preserve entity order (state codes ascending ASCII, county FIPS ascending,
ISO3 ascending). Entity-order arrays produced by a cohort must align exactly
with that cohort's entity order.

### 1.3 Country-Specific Resolution

For country-level audits:

1. Fetch `/geographies/countries` for canonical label-to-ISO3 mapping.
2. Resolve requested labels against canonical names: match case-insensitively,
   recognize common patterns ("Republic of X", "X Republic", "X Federation",
   "X Isles"), and infer aliases.
3. Every resolved label maps to exactly one ISO3.
4. Count `alias_resolution_count` as resolved labels whose resolved canonical
   name differs from the requested label string.

### 1.4 Revision Event Audit

For country-level audits:

1. Fetch `/data/revisions` to obtain all revision events.
2. Classify each event: `APPLIED` events are applicable; others are
   `nonapplied`.
3. Sort event IDs ascending.
4. For scale-break anomaly detection: records with `scale_break` flags that
   remain unresolved are anomalies, identified as `ISO3|YEAR|indicator_id`.
5. Count missing and imputed cells per the request's methodology.

---

## 2. Linear Algebra Primitives

### 2.1 OLS via Normal Equations

For design matrix X (n x k) and outcome y (n x 1):

```
b = (X'X)^-1 X'y
```

In declared column order. The intercept, if included, is the first column or
as declared. Use numerically stable matrix inversion.

### 2.2 Weighted Least Squares

For design X, outcome y, and positive weights w:

```
Xw = diag(sqrt(w)) * X
yw = diag(sqrt(w)) * y
b = (Xw'Xw)^-1 Xw'yw
```

### 2.3 HC3 Heteroskedasticity-Robust Inference

```
h_i = diag(Xw (Xw'Xw)^-1 Xw')_i
ew_i = sqrt(w_i) * (y_i - X_i b)
V_HC3 = (Xw'Xw)^-1 Xw' diag(ew_i^2 / max(1-h_i, epsilon)^2) Xw (Xw'Xw)^-1
```

Use `n - k` residual degrees of freedom for two-sided Student-t inference.
Set epsilon to a small positive value (e.g., 1e-12) to avoid division by
zero from leverage values near 1.

### 2.4 CR1 Cluster-Robust Inference

For ordered cluster groups g (G clusters):

```
s_g = Xw_g' ew_g
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw'Xw)^-1 * sum_g(s_g s_g') * (Xw'Xw)^-1
```

Use `G - 1` degrees of freedom for two-sided Student-t. For single-cluster
cases (G = 1), the correction factors reduce to standard sandwich.

### 2.5 Double-Demeaned Transform

For entity-clustered panel data with entity index i and time index t:

```
z_dd_it = z_it - mean_t(z_i*) - mean_i(z_*t) + mean(z_**)
```

where `mean_t(z_i*)` is the entity-specific mean across time, `mean_i(z_*t)`
is the time-specific mean across entities, and `mean(z_**)` is the grand mean.
Apply independently to each variable (outcome and every predictor). Fit OLS
without an intercept on the transformed variables.

### 2.6 Moore-Penrose Pseudoinverse

For matrix S with eigendecomposition or SVD, use singular values and
retain components where the singular value exceeds `cutoff * max_singular_value`.
The effective cutoff is typically `1e-12` relative.

---

## 3. Fixed Effects and Delete-Cluster Jackknife

### 3.1 Two-Way Fixed Effects OLS

1. Apply the double-demeaned transform (Section 2.5) to the outcome and every
   predictor using cluster (entity) and time dimensions.
2. Fit OLS without intercept on the transformed variables in declared
   predictor order.
3. For CR1 inference (Section 2.4), form cluster scores from the original
   weighted residuals.

### 3.2 Delete-One-Cluster Jackknife

For each cluster g in entity-code order:

1. Delete cluster g entirely from the balanced panel.
2. Recompute every entity mean, time mean, and grand mean from the remaining
   observations.
3. Transform variables using only the remaining data's moments.
4. Fit OLS from scratch.
5. Record the target coefficient `b_-g`.

After all G deletions:

```
bbar = mean(b_-g)
SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))
t_JK = b / SE_JK
```

Two-sided Student-t with `G - 1` degrees of freedom.

```
b_BC = G * b - (G - 1) * bbar
```

Select extrema: the minimum coefficient (most negative) and its state, and
the maximum coefficient (least negative / most positive) and its state.

### 3.3 Weighted Delete-Cluster Jackknife

Same as 3.2 but with reliability weights preserved through deletion:

```
percent_change_g = 100 * abs((b_-g - b) / b)
```

Select the maximum `percent_change_g`, breaking ties with earlier cluster
order. Use `b_BC` for the jackknife test statistic:

```
t_JK = b_BC / SE_JK
```

---

## 4. Nested Ridge / Elastic-Net Cross-Validation

### 4.1 Group Structure

The effective request declares outer groups (e.g., census divisions or
states in declared order). Each outer fold holds out exactly one group.

For inner folds, hold out each remaining group once in the same order.

### 4.2 Training-Only Standardization

Inside every fit:

1. Compute training-only weighted/unweighted feature means `mu_j` and
   standard deviations `sigma_j`:
   - For ridge: unweighted sample mean and sample SD with `ddof = 1`.
   - For weighted elastic-net: weighted mean `mu_j = sum(w_i * x_ij) / sum(w_i)`
     and weighted population SD `sigma_j = sqrt(sum(w_i * (x_ij - mu_j)^2) / sum(w_i))`.
2. If `sigma_j == 0`, set `sigma_j = 1` (unit divisor for zero variance).
3. Standardize training and prediction rows with these moments.
4. For ridge: center the training outcome (subtract training mean), do not
   scale y.
5. For elastic-net: center y by its weighted training mean.
6. Keep the intercept unpenalized; do not standardize indicator variables.

### 4.3 Ridge Solver

For centered outcome y and standardized design Z (excluding intercept),
penalty `lambda`, and unpenalized intercept a:

Objective:
```
minimize mean((y - a - Z b)^2) + lambda * sum_j(b_j^2)
```

Coordinate descent:
1. Initialize all `b_j = 0` and `a = mean(y)`.
2. Cycle in declared feature order. For feature j:
   - `r_ij = y_i - a - sum_{l != j} Z_il * b_l`
   - `b_j = sum_i(Z_ij * r_ij) / (sum_i(Z_ij^2) + n * lambda)`
3. Update `a = mean(y - Z b)` after each sweep if intercept is present.
4. Stop after a complete sweep when `max(|b_j_new - b_j_old|) < tolerance`,
   or at the effective sweep cap (typically 1000-2000 sweeps).
5. The effective tolerance is typically `1e-6` relative to coefficient scale.

### 4.4 Elastic-Net Solver

Objective with penalty `alpha`, L1 ratio `rho`:
```
minimize sum_i w_i * (y_i - a - Z_i b)^2 / (2 * sum_i w_i)
         + alpha * (rho * sum_j |b_j| + (1 - rho) * sum_j b_j^2 / 2)
```

Coordinate descent with soft thresholding:
1. Cold-start `b = 0` and `a = weighted_mean(y)` for every penalty.
2. Cycle in declared coefficient order. For feature j:
   - `r_partial_i = y_i - a - sum_{l != j} Z_il * b_l`
   - `rho_j = sum_i w_i * Z_ij * r_partial_i / sum_i w_i`
   - `b_j = S(rho_j, alpha * rho) / (sum_i w_i * Z_ij^2 / sum_i w_i + alpha * (1 - rho))`
   - where `S(a, t) = sign(a) * max(abs(a) - t, 0)`
3. After each sweep, update intercept: `a = weighted_mean(y - Z b)`.
4. Stop at tolerance or sweep cap.
5. For unpenalized intercept, the intercept update is applied each cycle.

### 4.5 Selection and Pooling (Ridge)

1. For each lambda in the grid, pool inner validation squared errors at the
   **row level** (not fold-mean of RMSE) and compute RMSE.
2. Select the lambda with smallest unrounded inner RMSE; if tied, choose the
   **smaller** lambda.
3. Refit on all outer-training rows with the selected lambda.
4. Predict all outer-test rows.
5. After all folds, pool exactly one prediction per eligible row.
6. Compute:
   - `pooled_RMSE = sqrt(sum((y_i - yhat_i)^2) / n)`
   - `pooled_MAE = sum(|y_i - yhat_i|) / n`
   - `pooled_R2 = 1 - SSE / SST` where SST uses the full-sample unweighted mean.

### 4.6 Selection and Pooling (Elastic-Net)

1. For each penalty in the grid (declared outer alpha then l1_ratio order),
   pool inner validation squared errors at row level and compute RMSE.
2. Select smallest RMSE; if tied, choose smaller alpha, then smaller l1_ratio.
3. Cold-refit on all outer-training rows.
4. Predict outer-test rows.
5. Pool OOF predictions and compute RMSE, MAE, R2.
6. Record which features have non-zero coefficients (using numerical cutoff,
   typically `1e-8`).

### 4.7 State-Block Fold Allocation

When groups are states, allocate by descending county count:
1. Assign each state to the currently smallest fold (by total panel rows).
2. Break ties with lower fold index.
3. Sort state codes within each fold ascending.
4. For inner folds within each outer-training set, repeat allocation of the
   remaining states.

---

## 5. Wild Cluster Bootstrap

### 5.1 Observed Fit

1. Fit the full model (weighted or unweighted, as declared) to the cohort.
2. Compute the CR1 cluster-robust standard error (Section 2.4) for the target
   coefficient.
3. Studentize: `t_obs = b_target / SE_CR1_target`.

### 5.2 Restricted Null Model

1. Fit the model **without** the target variable (all other covariates remain).
2. Retain restricted fitted values `y_restricted_i` and residuals `e_restricted_i`
   in entity order.

### 5.3 PRNG Specification

Two generators appear in the protocol catalog.

#### PCG32 (used with 64-bit state and 32-bit output)

```
increment = 2 * stream + 1    // stream is odd
state = 0
advance: state = old + init  // init is the seed
advance: old = state; state = old * 6364136223846793005 + increment (mod 2^64)

output:
  xorshifted = ((old >> 18) xor old) >> 27
  rot = old >> 59
  output = rotate_right_32(xorshifted, rot)   // 32-bit rotation
```

Map output to wild weights by modulo 6, giving values in order:
`[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`

#### xorshift32 (unsigned 32-bit)

```
Initialize state from seed.
Each call:
  x ^= x << 13; x &= 0xFFFFFFFF
  x ^= x >> 17; x &= 0xFFFFFFFF
  x ^= x << 5;  x &= 0xFFFFFFFF
  return x
```

Map to wild weights: low bit 1 -> +1, low bit 0 -> -1.
Alternatively: odd state -> +1, even state -> -1.

### 5.4 Bootstrap Draw and Refit

Maintain one continuous PRNG stream across all replicates.

For each of B replicates (B from the request):

1. Draw once per cluster in declared cluster order.
2. Map the PRNG output to a wild weight `w_g`.
3. Form synthetic outcomes:
   ```
   y*_i = y_restricted_i + e_restricted_i * w_g(i)
   ```
4. Refit the unrestricted model (same specification as observed).
5. Recompute CR1 standard error.
6. Studentize: `t* = b*_target / SE*_CR1_target`.
7. Record checkpoints after the specified replicate is complete, without
   resetting the stream.

### 5.5 Test and Aggregation

```
exceedance_count = sum(abs(t*_r) >= abs(t_obs) - delta)
```
where `delta` is a small tolerance (typically 0 or 1e-12).

```
p_value = (exceedance_count + 1) / (B + 1)
```

Use two-sided absolute exceedances.

### 5.6 Quantile Computation

**Nearest-rank method**: For sorted values `x` and probability `p`:

```
one-based index = min(B, ceil(p * B))
value = x[index - 1]   // zero-based access
```

**Type-7 (default) method** (used in some protocol variants):
```
h = (B - 1) * p
j = floor(h)
gamma = h - j
value = (1 - gamma) * x[j] + gamma * x[j + 1]   // zero-based indexing
```

The effective request declares which quantile method to use.

### 5.7 Bootstrap-t Confidence Intervals

If constructing confidence intervals by bootstrap-t inversion:
```
CI = b_obs +/- q * SE_obs
```
where `q` is the appropriate bootstrap-t quantile.

### 5.8 Paired Equation Bootstrap

When multiple equations share the same cluster structure and PRNG stream:

1. Draw cluster weights once per replicate.
2. Use the **same weights** for all equations in that replicate.
3. Refit and studentize each equation independently.
4. Report checkpoints for all equations at each checkpoint replicate.

---

## 6. Grouped Split Conformal Calibration

### 6.1 Split Conformal (Single Group)

For each outer group `g` in declared group order:

1. **Test set**: Group `g`.
2. **Calibration set**: Among remaining groups, choose the one with the
   greatest row count; if tied, choose the one with the earlier group name
   (ASCII order).
3. **Proper training**: All other groups.

Fit the declared model on the proper training set with training-only
standardization. Predict calibration and test rows.

### 6.2 Calibration and Intervals

1. Collect absolute calibration residuals: `r_i = |y_i - yhat_i|`.
2. Sort ascending.
3. With effective miscoverage `alpha` (e.g., 0.20) and `m` calibration rows:
   ```
   r = min(m, ceil((m + 1) * (1 - alpha)))
   q = score[r]   // one-based index
   ```
4. For each test row, interval is `[yhat_i - q, yhat_i + q]` (inclusive).
5. Aggregate:
   - **Fold coverage**: fraction of test rows where `y_i` falls in the interval.
   - **Fold mean width**: `2 * q` (constant within the fold).
   - **Fold test MAE**: mean absolute error of center predictions.
   - **Aggregate coverage**: total covered test rows / total test rows.
   - **Aggregate mean width**: weighted by test row counts.

### 6.3 State-Max Calibration

For state-grouped designs:

1. Reduce calibration residuals to one **maximum** absolute residual per
   calibration state (not per row).
2. With `m` state maxima: use one-based `k = min(m, ceil((m + 1) * coverage))`
   and radius = the `k`-th sorted state maximum.
3. Build symmetric inclusive intervals for all test rows.

### 6.4 Cross-Fold Grouped Conformal

When outer predictions come from a nested CV procedure:

1. For each outer fold, calibrate on absolute OOF residuals from **all other
   folds** (not using any in-fold data).
2. With `m` calibration rows, use rank `min(m, ceil((m + 1) * nominal_coverage))`.
3. Build intervals for the held-out fold's rows.
4. Report fold diagnostics plus state-level, RUCC-band, and prediction-decile
   coverages.

### 6.5 Out-of-Fold Conformal (Elastic-Net Source)

When source predictions come from nested elastic-net:

1. For each outer division, hold out each other training division once,
   cold-refit the identical weighted elastic-net on the remaining divisions,
   and predict the held-out division.
2. Collect absolute calibration residuals.
3. With m calibration rows, use one-based `r = min(m, ceil((m+1) * c))` and
   radius = `score[r]`.

---

## 7. Trajectory PCA and Clustering

### 7.1 Feature Construction

Build trajectory columns in the effective variable-major/time order. Each
feature is a variable-year pair (e.g., `life_expectancy_2020`,
`adult_obesity_2020`, `life_expectancy_2021`, ...). Entity rows use the
balanced-panel entity order.

For county trajectories, features are variable-end_year pairs.

### 7.2 PCA via Covariance Matrix

1. Standardize each column by its active-column sample standard deviation
   (population SD: divide by n, or sample SD: divide by n-1 as declared).
2. Form `C = Z'Z / (n - 1)` for the covariance matrix of standardized data.
3. Eigendecompose C.

### 7.3 Jacobi Eigendecomposition

For symmetric matrix A:

1. Find the largest absolute off-diagonal element (upper triangle). Tiebreak
   by lower row index, then lower column index.
2. Compute rotation:
   ```
   tau = (A_qq - A_pp) / (2 * A_pq)
   t = sign_nonnegative(tau) / (abs(tau) + sqrt(1 + tau^2))
   c = 1 / sqrt(1 + t^2)
   s = t * c
   ```
3. Apply Givens rotation to A and to eigenvector matrix V.
4. Stop when the maximum absolute off-diagonal is below the effective
   tolerance (typically `1e-10`) or at the effective step cap (e.g., 100).

### 7.4 Component Ordering and Orientation

1. Sort components by descending eigenvalue; break ties by original diagonal
   index (the component's position before sorting).
2. For each retained eigenvector, flip sign so the **earliest** (lowest
   index) maximum-absolute loading is positive.
3. Scores = `Z * V_retained` (standardized data times oriented loadings).
4. Explained variance ratio = eigenvalue / sum(all eigenvalues).

### 7.5 Deterministic k-means

**Initialization**:
1. First centroid: the ASCII-first entity point.
2. Each subsequent centroid: the entity maximizing minimum squared Euclidean
   distance to its nearest existing centroid. Tiebreak by entity code
   (ascending ASCII).

**Lloyd iteration**:
1. Assign each point to the nearest centroid by squared Euclidean distance.
   Tiebreak: assign to the lower working cluster id.
2. Update centroids as the arithmetic mean of assigned points.
3. Handle empty clusters: assign the ASCII-first entity among those farthest
   from their assigned centroid, recompute.
4. Stop when no assignment changes (or at the effective cap, typically 100
   iterations).

**Canonicalization**: After convergence, relabel clusters by sorting on
centroid coordinates (e.g., PC1 then PC2), then by working id for ties.

### 7.6 Adjusted Rand Index

For two clusterings with contingency table `n_ij`:

```
sum_comb = sum_ij C(n_ij, 2)
sum_a = sum_i C(a_i, 2)   // row sums
sum_b = sum_j C(b_j, 2)   // column sums
expected = sum_a * sum_b / C(n, 2)
ARI = (sum_comb - expected) / (0.5 * (sum_a + sum_b) - expected)
```

where `C(x, 2) = x * (x - 1) / 2`.

### 7.7 Leave-Period/State-Out Stability

For each omitted time block (or omitted state) in ascending order:

1. Delete all features belonging to that time block (or all rows from that
   state).
2. Rebuild scaling, PCA, orientation, initialization, and clustering from
   scratch.
3. Compute ARI against the full-data assignment.
4. Align refit labels to maximize agreement with full-data labels.
   Iterate over all k! label permutations and choose the one with maximum
   matched assignments; tiebreak by lexicographically smallest mapped id
   vector.

### 7.8 Silhouette Selection (Country Clustering)

For candidate cluster counts (typically 2-5):

1. For each point i in cluster a:
   - `a_i` = mean distance to other points in cluster a.
   - `b_i` = min over clusters c != a of mean distance to points in c.
   - `s_i = (b_i - a_i) / max(a_i, b_i)`.
2. For singleton clusters (size 1), set `s_i = 0`.
3. Mean silhouette = mean of `s_i` across all points.
4. Select k with largest mean silhouette; tiebreak by smaller k.

---

## 8. Source Perturbation

### 8.1 Exhaustive Time-Subset Perturbation

For the strict dual-source cohort:

1. Enumerate time subsets by increasing subset size, then lexicographic tuple
   order of years.
2. For each subset, refit the complete double-demeaned model separately with
   the primary and parallel exposure series.
3. For each fit, recompute CR1 standard errors and two-sided G-1 df inference.

**Aggregation**:
```
shift = 100 * abs(b_alt - b_baseline) / abs(b_baseline)
```
- `same_sign`: both coefficients are nonzero with identical sign.
- `median_shift`: ordinary median of the ordered shift values.
- `worst_subset`: greatest unrounded shift, tiebreak by earlier subset order.

### 8.2 Exhaustive Source Replacement Perturbation

When an alternate outcome source is available (e.g., DIRECT_SURVEY vs.
COUNTY_ROLLUP):

1. Resolve alternate outcome records with identical filtering but alternate
   `value_type` and `source_type`.
2. Identify entity codes where both baseline and alternate records resolve
   as eligible (non-suppressed, non-missing).
3. Order these entities by descending `|alternate_value - baseline_value|`,
   tiebreak by entity code.
4. For every bitmask from 0 through `2^M - 1` (M = eligible entity count),
   replace entity j if `mask & (1 << j)` is nonzero. Retain fixed reliability
   weights and design.
5. Refit the declared WLS model and compute HC3 inference for each scenario.

**Aggregation by popcount**:
For each replacement count stratum (0 through M), report:
- `scenario_count`, `minimum_coefficient`, `maximum_coefficient`,
  `minimum_hc3_p_value`, `maximum_hc3_p_value`, `mean_absolute_percent_shift`.

**Worst shift**:
```
percent_shift = 100 * abs((b_mask - b_zero) / b_zero)
```
Select maximum unrounded shift; tiebreak by smaller mask.

### 8.3 Exact Shapley Attribution

For ordered entity j:

```
phi_j = sum_{S subset of {1..M} without j}
        |S|! * (M - |S| - 1)! / M! * (b(S union {j}) - b(S))
```

where `b(S)` is the coefficient when entities in S are replaced.

Verify: `sum_j phi_j = b(all_replaced) - b(no_replacements)` within
numerical tolerance.

### 8.4 Source Group Deletion (No-Retune)

For each declared source group in order:

1. Remove exactly the group's terms from the design.
2. Reuse the full model's selected hyperparameters without retuning.
3. For each outer fold, apply the same remaining-term preprocessing and
   solver; retain each outer-fold RMSE.
4. Pool squared errors across folds; compute pooled RMSE.
5. `deterioration = pooled_group_rmse - full_model_pooled_rmse`.
6. Count folds where group RMSE exceeds the corresponding full-model fold
   RMSE (within small tolerance).
7. Rank groups by decreasing unrounded deterioration; tiebreak by declared
   group order.

---

## 9. Difference GMM Mediation

### 9.1 Panel Construction

1. Create adjacent-change rows from the balanced panel: each row is an entity
   observed in two consecutive periods (end years as declared).
2. Differenced outcome `delta_y`, differenced exposure `delta_X`, differenced
   mediator `delta_M`, and differenced controls.
3. Add period indicators for the later period.
4. Order rows by entity identifier, then end period.

### 9.2 Two-Step Linear GMM

**Residualization**: Residualize outcome, dynamic regressors, and instruments
against the intercept plus baseline terms (period indicators).

For each equation:

1. **First step**: moments `g(theta) = Z'(y - D theta) / n` with identity weight.
   ```
   W1 = (Z'Z / n)^-1
   theta1 = (D'Z W1 Z'D)^-1 D'Z W1 Z'y
   ```
2. **State-cluster scores**: `s_g = Z_g' u_g` for each cluster g.
   ```
   S = sum_g(s_g s_g') / n
   ```
3. **Second step**: weight `W2 = pinv(S)` using the declared relative
   pseudoinverse cutoff.
   ```
   theta2 = (D'Z W2 Z'D)^-1 D'Z W2 Z'y
   ```
4. **Hansen J statistic**: `J = n * g(theta2)' W2 g(theta2)`.

### 9.3 Clustered Inference

With cluster scores `q_g = Z_g' u_g` and the second-step projection matrix:
```
Var(theta) = [G/(G-1)] * correction * (D'Z W Z'D)^-1 *
             sum_g(D'Z W q_g q_g' W Z'D) * (D'Z W Z'D)^-1
```
Use `G - 1` degrees of freedom for Student-t.

Cross-equation covariance for indirect effects uses the corresponding
cross-equation cluster score products.

### 9.4 Stacked Indirect Effect

For path-a coefficient `a` and path-b coefficient `b`:
```
indirect = a * b
Var(indirect) = b^2 * Var(a) + a^2 * Var(b) + 2 * a * b * Cov(a, b)
SE_indirect = sqrt(Var(indirect))
```
Confidence intervals use cluster degrees of freedom.

### 9.5 First-Stage Partial F

For each endogenous variable separately:
```
F = ((RSS_reduced - RSS_full) / excluded_instruments) /
    (RSS_full / residual_df)
```
where `excluded_instruments` count only those excluded from the structural
equation.

### 9.6 Delete-State Diagnostics

For each state in state-code order:

1. Remove all rows belonging to that state.
2. Rebuild the change panel, residualization, both GMM steps, and all
   equation fits from scratch.
3. Report `omitted_state`, `n`, `indirect_effect`, and `direct_poverty`
   (or other declared focal coefficients).

---

## 10. Partial-R2 Sensitivity Surface

### 10.1 Baseline Quantities

From the primary OLS mediation models:

- `a` = path-a exposure coefficient (exposure -> mediator).
- `b` = path-b mediator coefficient (mediator -> outcome, from the model
  containing both exposure, mediator, and covariates).
- `SE_b` = standard error of `b`.
- `df` = residual degrees of freedom from the direct model.

### 10.2 Sensitivity Magnitude

```
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
```
where `rM` is the R2 confounder-mediator value and `rY` is the R2
confounder-outcome value.

### 10.3 Adjusted Coefficients

For each `(rM, rY, direction)` combination in declared order:

```
adjusted_b = b - sign * magnitude      // sign is +1 for NEGATIVE, -1 for POSITIVE
adjusted_indirect = a * adjusted_b
adjusted_direct = total_effect - adjusted_indirect
proportion = adjusted_indirect / total_effect
```

### 10.4 Equal-Strength Tipping Point

Find the smallest `r2` value where both confounder-mediator and
confounder-outcome R2 equal `r2` and the adjusted indirect effect crosses
zero. This is the **equal-strength tipping R2**.

---

## 11. Controlled Decision

### 11.1 Gate Evaluation

Compute every module first. Then evaluate each business predicate on
**unrounded** computed values.

Gate predicates are boolean expressions on module outputs from the effective
request, for example:
- "coefficient is positive and p-value <= 0.05"
- "pooled R2 >= 0.85 and pooled RMSE <= 0.75"
- "bootstrap p-value <= 0.05"
- "aggregate coverage >= 0.80"
- "minimum ARI >= 0.55"

### 11.2 Decision Mapping

Apply the effective request's decision rule in declared precedence order:

1. Count how many gates pass.
2. If the "all pass" condition is met, return the top classification.
3. Else if the "at least N pass" condition is met, return the intermediate
   classification.
4. Else return the fallback classification.

Or for sequential precedence:

1. Check gates in declared order.
2. The first failed gate determines the classification.
3. If all pass, return the success classification.

### 11.3 Precedence Values

The controlled conclusion always uses the **exact** string values declared
in the effective request's `decision_rule` or `controlled_conclusion` section.
Never invent or alias decision strings.
