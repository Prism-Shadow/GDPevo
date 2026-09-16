# Statistical Module Implementation Patterns

Reusable implementation guidance for every recurring PHO audit module type.
Each module's exact parameters, grids, seeds, cohorts, and thresholds come
from the request --- the patterns below describe how to implement them
correctly.

## Fixed-effects and weighted linear regression

### Double-demeaned fixed effects

When the request specifies a two-way fixed-effects design with entity and
time dimensions:

1. For each variable `z_it`, compute the entity mean `zbar_i`, time mean
   `zbar_t`, and grand mean `zbar`.
2. Transform: `ztilde_it = z_it - zbar_i - zbar_t + zbar`.
3. Fit OLS on the transformed variables without an intercept, in the declared
   predictor order.
4. On deletion of a cluster, recompute every mean from scratch using only the
   retained observations, then refit.

### Reliability-weighted least squares (WLS)

When the request provides a positive reliability weight `w_i`:

1. Form weighted design: `Xw = diag(sqrt(w)) * X`, `yw = diag(sqrt(w)) * y`.
2. Solve `b = (Xw' Xw)^-1 Xw' yw` in declared column order.
3. Keep weights fixed even when replacing outcome sources in perturbation
   modules.

### HC3 robust standard errors

For weighted design with leverage `h_i = diag(Xw (Xw' Xw)^-1 Xw')` and
weighted residual `ew_i = sqrt(w_i) * (y_i - X_i b)`:

```
V_HC3 = (Xw' Xw)^-1 Xw' diag(ew_i^2 / (1 - h_i)^2) Xw (Xw' Xw)^-1
```

Use two-sided Student-t inference with `n - k` residual degrees of freedom.

### CR1 cluster-robust standard errors

For ordered clusters `g` with cluster score `s_g = Xw_g' ew_g`:

```
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw' Xw)^-1 * sum_g(s_g s_g') * (Xw' Xw)^-1
```

Use two-sided Student-t inference with `G - 1` degrees of freedom.

### Delete-one-cluster jackknife

1. Fit the full design to obtain coefficient `b`.
2. For each cluster in declared order, delete all its observations and refit
   the unchanged design from scratch, yielding `b_-g`.
3. Compute the absolute percent change: `100 * abs((b_-g - b) / b)`.
4. Report the mean of delete estimates `bbar`.
5. Jackknife standard error: `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))`.
6. Bias-corrected estimate: `b_BC = G * b - (G-1) * bbar`.
7. Test `b_BC / SE_JK` two-sided with `G - 1` Student-t degrees of freedom.
8. Select extrema by coefficient value, then by entity code on ties.

## Nested ridge regression CV

### Training-only standardization

For every fit, compute training-set means and sample standard deviations
(with ddof=1) for each feature. Apply these moments to both training and
held-out rows. Center the outcome by its training mean without scaling it.

If a feature has zero training variance, divide by 1.0 instead of 0.

### Ridge solver (cyclic coordinate descent)

- Keep the intercept unpenalized.
- Initialize coefficients to zero.
- In declared feature order, for each `j`:
  `b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n * lambda)`
  where `r_ij` is the partial residual excluding feature `j`.
- Stop when the maximum absolute coefficient change across one full sweep
  is below the solver tolerance, or at the sweep cap.

### Inner/outer selection

- Outer fold: hold out one group. Inner fold: within outer training, hold
  out each remaining group in order.
- For each penalty, pool all inner validation squared errors, compute RMSE
  at the row level (not the mean of fold RMSEs).
- Choose the penalty with smallest unrounded inner RMSE; break ties toward
  the smaller penalty value.
- Refit with the selected penalty on all outer-training rows and predict
  the outer test rows.
- Pool exactly one prediction per eligible row. Compute pooled RMSE, MAE,
  and Q-squared: `1 - SSE / SST` where SST uses the full-sample outcome mean.

## Nested elastic-net CV

### Feature construction

Build features in the exact declared order: raw terms, transformations
(e.g. log, squared), and interactions. Use only the declaration from the
request; do not add or remove features.

### Training-only standardization

Standardize declared continuous columns from training population moments
(weighted if reliability weights are in effect). Leave indicator/dummy
variables unchanged. Apply training moments to held-out rows. Keep the
intercept unpenalized.

### Elastic-net objective

Minimize: `sum_i w_i (y_i - Z_i b)^2 / (2 sum_i w_i) + lambda * [alpha * sum_j |b_j| + (1-alpha) * sum_j b_j^2 / 2]`

### Coordinate descent solver

- Cold-start: `b = 0` for every penalty and fold. Never warm-start.
- The intercept is updated as the weighted mean residual after each sweep.
- In declared feature order:
  `rho_j = sum_i w_i Z_ij (y_i - sum_{l != j} Z_il b_l) / sum_i w_i`
  `b_j = S(rho_j, lambda * alpha) / (1 + lambda * (1-alpha))`
  where `S(a, t) = sign(a) * max(abs(a) - t, 0)`.
- Stop after a complete cycle when max coefficient change is below the
  effective tolerance, or at the cycle cap.

### Inner/outer selection

- Pool unweighted inner squared errors across validation rows, take RMSE.
- Select smallest unrounded RMSE, then smaller alpha, then smaller l1_ratio.
- Cold-refit on all outer-training rows and predict the outer holdout.
- Determine nonzero coefficients with the effective numerical cutoff.
- Aggregate OOF metrics from the single prediction per row. Report unweighted
  RMSE, MAE, and `R^2 = 1 - SSE / sum_i(y_i - full_sample_mean)^2`.

## Wild cluster bootstrap

### Observed statistic

Fit the full model and compute the cluster-robust CR1 standard error.
Studentize the target coefficient: `t_obs = b_target / SE_CR1`.

### Restricted model

Fit the model **without** the target coefficient term. Retain restricted
fitted values and residuals in entity order.

### PRNG: PCG32

- Use unsigned 64-bit state, 32-bit output.
- Increment: `2 * stream + 1`.
- Initialize state to 0, advance, add the seed modulo 2^64, advance.
- Each advance: `old = state; state = old * 6364136223846793005 + increment mod 2^64`.
- Output: `xorshifted = low32(((old >> 18) ^ old) >> 27)`; `rot = old >> 59`;
  `output = rotate_right_32(xorshifted, rot)`.
- Map output to weights by modulo the weight-count and index into the ordered
  set.

### PRNG: xorshift32

- Use unsigned 32-bit state.
- Each call: `x ^= x << 13; x ^= x >> 17; x ^= x << 5`, masking to 32 bits after
  each XOR.
- Maintain one continuous stream across all replicates; never reset.
- Map the low bit to +1 (odd) or -1 (even) for wild bootstrap weights.
- For paired designs (e.g. mediation with three equations), draw once per
  cluster per replicate and reuse the same sign across all equations.

### Bootstrap loop

For each replicate in declared order:
1. Draw one weight per cluster in entity-code order.
2. Generate synthetic outcome: `y* = restricted_fit + restricted_residual * cluster_weight`.
3. Refit the full model and recompute CR1.
4. Record the absolute studentized target coefficient.

### Checkpoints

Record checkpoints only after the replicate is complete, without resetting
the PRNG stream. The checkpoint records the current PRNG state and the
replicate's t-statistic.

### Inference

- Count replicates where `|t*| >= |t_obs|` (with a declared comparison
  tolerance delta when specified).
- Plus-one p-value: `(count + 1) / (B + 1)`.
- For sorted values `x` and probability `p`:
  - Nearest-rank: `x[min(B, ceil(p * B)) - 1]` using one-based rank.
  - Type-7 quantile: `h = (B-1) * p; j = floor(h); gamma = h - j`;
    `(1-gamma) * x[j] + gamma * x[j+1]` with zero-based indexing.

## Grouped split conformal prediction

### Partitioning

For each outer group in declared order:
- Use that group as the test set.
- Among the remaining groups, choose the calibration group by greatest row
  count (then ascending group name on ties).
- All other groups form the proper training set.

### Model fitting

Fit the declared model (ridge or elastic-net) from scratch with the effective
fixed penalty and the identical training-only scaling and solver rules used
in the nested CV module. Predict the calibration and test rows.

### Calibration and intervals

- Collect absolute residuals from calibration rows.
- Sort ascending. With effective miscoverage `alpha` and `m` calibration rows:
  `r = min(m, ceil((m+1) * (1 - alpha)))` (one-based).
- `qhat = sorted_abs_residuals[r]`.
- For each test prediction: interval is `[pred - qhat, pred + qhat]`,
  inclusive.

### Aggregation

- Report coverage (fraction of test rows falling within the interval) and
  mean width per fold, per state, and overall.
- Pooled coverage: sum of covered rows across all folds divided by total
  rows.
- Weight mean width by held-out row counts.
- Select worst coverage division by smallest coverage fraction, then earlier
  division order on ties.

### State-grouped conformal variant

When calibration uses state-level reduction: take one maximum absolute
residual per calibration state. Use `k = min(m, ceil((m+1) * coverage))`
with one-based `k`-th state maximum. Build symmetric inclusive intervals and
aggregate county coverage and width by cycle and state.

## Trajectory PCA clustering

### PCA via covariance eigendecomposition

1. Build the data matrix `Z` with columns in declared variable-major/time
   order and rows in entity order (ascending entity code).
2. Standardize each column by its active-sample sample standard deviation.
3. Form the covariance matrix: `C = Z'Z / (n - 1)` or `Z'Z / n` as declared.
4. Eigendecompose using symmetric Jacobi rotations:
   - In each sweep, select the largest absolute upper-triangle off-diagonal.
   - Break ties by lower row index, then lower column index.
   - Compute rotation angle and apply to the matrix and eigenvector
     accumulator.
   - Stop when the maximum off-diagonal is below the tolerance or at the
     step cap.
5. Order eigenvalues descending; for equal eigenvalues, use the original
   diagonal index order.
6. For each retained eigenvector, flip its sign so the earliest
   maximum-absolute loading is positive.
7. Scores: `scores = Z * loadings`.
8. Explained ratio for component `j`: `lambda_j / sum of all eigenvalues`.

### Deterministic k-means clustering

1. First centroid: the entity with the smallest (ASCII-first) code.
2. Each subsequent centroid: the entity maximizing minimum distance to any
   existing centroid, breaking ties by ascending entity code.
3. Assignment: each point to the nearest centroid by squared Euclidean
   distance, breaking ties by lower working cluster id.
4. Update: arithmetic mean of members per cluster.
5. Stop when no assignments change, or at the iteration cap.
6. Canonicalize final cluster ids by centroid coordinates, then working id.

### Leave-one-out stability

For each omitted time block in ascending order:
1. Delete the corresponding variable block from the feature matrix.
2. Rebuild scaling, PCA, orientation, initialization, and clustering from
   scratch.
3. Compare the refit labels with the full-data labels using the adjusted
   Rand index (ARI).
4. Align refit cluster ids by the permutation maximizing agreement with full
   labels; break ties by lexicographically smallest mapped-id vector.
5. Report ordered ARIs and aligned agreement fractions.

### Adjusted Rand index

```
ARI = (sum_ij C(n_ij, 2) - expected) / (0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2)) - expected)
```
where `expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)`, `C(x, 2) = x * (x-1) / 2`,
`n_ij` is the contingency table, `a_i` are row sums, and `b_j` are column sums.

### Silhouette selection (when required)

For each candidate cluster count `k`:
- Compute the Euclidean silhouette score per point. Singleton clusters get
  silhouette value 0.
- Average silhouette across all points.
- Select the `k` with largest unrounded mean silhouette; break ties toward
  the smaller `k`.

## Source / year perturbation

### Subset enumeration

Generate all subsets of the declared dimension (years, source states) at
each requested size. Order by increasing size, then lexicographic tuple
order.

### Refit and comparison

For each subset:
1. Keep the analytic set unchanged (same cohort rows).
2. Refit the complete model using the subset's data configuration (e.g.
   subset of years, or replacement of direct-survey values with rollup
   values as declared).
3. Recompute inference (CR1, HC3, or cluster t-test as declared).

### Shift computation

For baseline coefficient `b` and alternate `b_alt`:
- `shift = 100 * abs(b_alt - b) / abs(b)`.
- Two coefficients are same-sign if both are nonzero and have identical sign.
- Median shift: ordinary median of ordered shift values.
- Select the worst subset by greatest unrounded shift, then earlier subset
  order on ties.

### Bitmask replacement

When replacing source values (e.g. direct-survey with county-rollup):
- Order entities by descending absolute alternate-minus-primary difference,
  then by entity code.
- For `m` entities, enumerate all `2^m` bitmasks.
- For bit `j`, replace entity `j` when the corresponding bit is set.
- Keep fixed reliability weights and design unchanged.

### Exact Shapley attribution

For ordered entity `j`:
```
phi_j = sum_{S not containing j} (|S|! * (m - |S| - 1)! / m!) * (b(S U {j}) - b(S))
```
Verify: `sum_j phi_j = b(all) - b(none)` within numerical tolerance.

## Difference GMM / panel mediation

### Data preparation

Create adjacent-change rows from the balanced panel, ordered by entity
identifier then end period. Derive lagged levels, dynamic changes, reference
indicators, and interactions in the declared order.

### First-step estimation

For each equation with instruments `Z`:
- `W = (Z'Z)^-1`.
- `beta = (X' Z W Z' X)^-1 X' Z W Z' y`.

### Second-step estimation

- With first-step residual `u` and cluster score `q_g = Z_g' u_g`:
  `S = sum_g(q_g q_g') / n`.
- Use the Moore-Penrose pseudoinverse of `S` as the weight matrix, applying
  the declared relative singular-value cutoff.
- Compute second-step `theta` from the weighted linear moments.
- Hansen J: `n * g(theta)' W g(theta)`.

### Cross-equation delta method

For indirect effect `theta = a * b`:
```
Var(theta) = b^2 * Var(a) + a^2 * Var(b) + 2 * a * b * Cov(a, b)
```
Use the cluster-robust cross-equation covariance. Student-t inference with
cluster degrees of freedom.

### First-stage partial F

For each endogenous regressor, compute the F-statistic from the full versus
reduced residual sums of squares using the effective instrument counts.

### Delete-state diagnostics

For each state in ascending order: rebuild rows, refit all affected equations
from scratch, and report the indirect effect and direct-exposure coefficient.

## Partial-R2 mediation sensitivity

### Baseline quantities

From the unrounded primary mediation models extract:
- `a`: path-a coefficient (exposure to mediator).
- `b`: path-b coefficient (mediator to outcome).
- `SE_b`: standard error of path-b.
- `df`: residual degrees of freedom from the direct/outcome model.

### Sensitivity surface

For each declared combination of R2_mediator_confounder and
R2_outcome_confounder, and for each bias direction (NEGATIVE, POSITIVE):
```
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
adjusted_b = b - sign * magnitude  (sign = +1 for NEGATIVE, -1 for POSITIVE)
adjusted_indirect = a * adjusted_b
adjusted_direct = total_effect - adjusted_indirect
proportion = adjusted_indirect / total_effect
```
Use the declared R2 values in the declared order for both mediator and
outcome confounding.

### Tipping point

Compute the equal-strength R2 value at which the adjusted indirect effect
crosses zero (for the POSITIVE direction). Solve from unrounded inputs using
the declared formula.

## Source-group perturbation

### Procedure

For each declared source group in order:
1. Remove exactly the group's declared terms from the design matrix.
2. Reuse the full model's selected hyperparameters without retuning.
3. Apply the same remaining-term preprocessing and solver.
4. Retain all outer-fold RMSEs and compute pooled RMSE from pooled squared
   errors.

### Deterioration

```
deterioration = pooled_rmse_group - full_model_pooled_rmse
```
For each fold, count it as worse if its RMSE exceeds the corresponding
full-model fold's RMSE.

### Ranking

Rank groups by decreasing unrounded deterioration, then by declared group
order on ties.

## Country-level modules

### Reconciliation

When a request supplies human-readable country labels:
1. Match each label to canonical country names and aliases from the
   `/geographies/countries` endpoint.
2. Count the total requested labels, resolved labels, and labels resolved
   through aliases (labels differing from the canonical name).
3. Report all uniquely resolved ISO3 codes sorted ascending.

### Quality audit

From the `/data/revisions` endpoint:
1. Collect revision event IDs. Classify as APPLIED or non-APPLIED based on
   their status.
2. Identify scale-break anomaly observation keys (e.g. ISO3|YEAR|indicator_id
   triples flagged in revision events).
3. Count raw missing 2022 cells, anomaly 2022 cells, and imputed 2022 cells.
4. Report the usable country and indicator counts after quality exclusions
   and imputation.

### PCA

- Standardize columns and use the covariance approach as described above.
- Retain components by the declared rule (e.g. cumulative explained variance
  threshold, or fixed count).
- Report eigenvalues, explained variance fractions, and top absolute loadings
  in declared order. Break ties on absolute loading by ascending indicator_id.

### Clustering

- Run k-means on the retained PC scores for each declared candidate `k`
  using the deterministic initialization described above.
- Compute silhouette scores for each `k`; select the best `k` by largest
  silhouette then smallest `k`.
- For the requested `k` (typically 3), report cluster memberships and sizes
  with meaningful labels (LOW_BURDEN, MIDDLE_BURDEN, HIGH_BURDEN) ordered by
  increasing PC1 centroid mean.

### Panel model

- Build a country-year panel for the declared years.
- Regress the panel outcome on PC1 burden score with declared fixed effects
  (e.g. region indicators).
- Report coefficient, standard error, p-value, R-squared, and whether region
  fixed effects were included.

### Advisory

Based on the panel model result, return the declared controlled advisory
value (e.g. PRIORITIZE_HIGH_BURDEN_CLUSTER if high-burden membership is
associated with worse outcomes).
