---
name: pho-algorithmic-audit
description: Solve Public Health Observatory algorithmic audit tasks by constructing cohorts from the portal, executing registered statistical modules (fixed-effects OLS, nested ridge/elastic-net CV, wild cluster bootstrap, grouped conformal, trajectory PCA clustering, sensitivity/perturbation), and applying controlled decision rules. Supports state, county, and country protocols.
---

# PHO Algorithmic Audit Solver

Activate this skill when a Public Health Observatory task arrives with a
`protocol_id` from one of the supported families and a structured
`analysis_request.json` or similar contract. The skill provides reusable
algorithmic methods only; every entity, measure, time coordinate, source
binding, random seed, parameter grid, cutoff, and output label must come from
the effective future request.

## Supported Protocol Families

- `PHO_STATE_TRANSPORT_AUDIT_V1` -- state-level multi-module transport audit
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1` -- county mediation transport audit
- `PHO_COUNTY_PANEL_TRANSPORT_V1` -- county panel dynamics audit
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` -- state weighted robustness audit
- Country burden audits (request-driven, no fixed protocol ID) -- label
  reconciliation, PCA, clustering, panel regression

## Portal

Base URL from the task prompt (typically `http://task-env:9023/`). Endpoints:

| Endpoint | Returns |
|---|---|
| `GET /` | Portal root |
| `GET /catalog` | Available datasets |
| `GET /geographies/states` | State codes, names, divisions |
| `GET /geographies/counties` | County codes, names, states, RUCC |
| `GET /geographies/countries` | Country names, ISO3, regions, aliases |
| `GET /data/state-health` | State health measures |
| `GET /data/state-socioeconomic` | State socioeconomic measures |
| `GET /data/county-health` | County health measures |
| `GET /data/county-socioeconomic` | County socioeconomic measures |
| `GET /data/country-indicators` | Country indicators |
| `GET /data/revisions` | Revision events |
| `GET /methodology` | Methodology notes |
| `GET /download` | Bulk downloads |
| `GET /health` | Service health |

Fetch endpoints as JSON arrays with query parameters for filtering.
Every response field name, value format, and semantic is discovered at
access time; do not assume field names beyond the standard structural
conventions documented here.

---

## 1. Publication Resolution and Cohort Construction

### 1.1 Record Selection

For each effective measure and geography scope, query the appropriate data
endpoint. Filter records by the effective release status, value type, source
type (when applicable), geography membership, and time scope.

For each unique entity-time-measure key, select one record by this precedence:

1. Greatest `revision` (numeric)
2. Latest `released_at` (ISO-8601 timestamp)
3. Lowest `observation_id` or `record_id` (numeric)

Count **selected publications** before analytic completeness exclusions.
Suppressed, invalid (`INVALID_SCALE`, `INVALID`, `WITHDRAWN`), blank, or null
analytic values are selected publication evidence but are **unavailable** for
analysis -- never zero-fill them.

### 1.2 Revision Events

When the task requests revision-event reporting, enumerate all applicable
revision events from `GET /data/revisions`. Distinguish `APPLIED` vs
non-`APPLIED` events. An `observation_key` in a revision event typically
follows the pattern `ISO3|YEAR|indicator_id` or similar.

### 1.3 Cohort Construction

Construct analytic cohorts from the effective completeness predicate:

**Primary / reference-year cohort**: All entities complete (non-suppressed,
non-null, valid) for the reference year on every required measure and field.

**Balanced panel cohort**: Intersection of entities complete in every requested
study year. Preserve entity-code order (ASCII ascending by state abbreviation
or ISO3).

**Broad / machine-learning cohort**: Reference-year entities additionally
complete for any extra specified fields.

**Strict dual-source cohort**: Entities complete for outcome, primary
exposure, parallel exposure, and all adjustments in every analysis year.

Report cohort sizes, excluded entity codes (sorted ascending), and yearly
complete counts in the requested format.

### 1.4 Geography Attributes

Augment resolved records with geography attributes from the geography
endpoints: state abbreviation, census division, census region, RUCC codes
(for counties), region labels (for countries). Use two-letter uppercase state
codes and portal division/region names exactly.

---

## 2. Linear Algebra Building Blocks

### 2.1 OLS and WLS

**Standard OLS**: For design matrix X (n x k, including intercept if specified)
and outcome vector y (n x 1), compute `b = (X'X)^-1 X'y` in declared column
order. Residual df = n - k.

**Weighted Least Squares**: For positive weights w (n x 1), form
`Xw = diag(sqrt(w)) * X` and `yw = diag(sqrt(w)) * y`, then solve
`b = (Xw'Xw)^-1 Xw'yw`.

### 2.2 Double-Demeaned Fixed Effects

For entity-cluster g and time t, transform each variable x as:

```
x_double_demeaned = x_gt - mean_g(x) - mean_t(x) + grand_mean(x)
```

where `mean_g` averages over all time periods for entity g, `mean_t` averages
over all entities for time t, and `grand_mean` averages over all observations.
Run OLS on transformed variables without an intercept.

When a cluster is deleted, recompute all means from the remaining observations
and refit from scratch.

### 2.3 Cluster-Robust Standard Errors

**HC3**: With leverage `h_i = diag(Xw*(Xw'Xw)^-1*Xw')` and weighted residual
`ew_i = sqrt(w_i)(y_i - X_i b)`, compute:

```
V_HC3 = (Xw'Xw)^-1 * Xw' * diag(ew_i^2/(1-h_i)^2) * Xw * (Xw'Xw)^-1
```

**CR1 (one-way cluster)**: For G clusters with cluster-g scores
`s_g = X_g' e_g` (or weighted equivalents), compute:

```
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g(s_g s_g') * (X'X)^-1
```

Use two-sided Student t with G-1 df for CR1, n-k df for HC3.

### 2.4 Cross-Equation Cluster Covariance (GMM)

For two equations a and b with cluster-g scores `s_ag = Z_ag' u_ag` and
`s_bg = Z_bg' u_bg`, the cross-equation cluster covariance uses the
corresponding cross-product of cluster scores. For indirect effect
`theta = a * b`: `Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b)`.

---

## 3. Fixed-Effects Delete-Cluster Jackknife

**Applicable to**: delete-one-cluster fixed effects OLS, delete-one-division
weighted LS.

### Procedure

1. Fit the full model on the effective cohort and design, yielding target
   coefficient `b_full`.

2. For each cluster g in the declared cluster order:
   a. Delete all observations belonging to cluster g.
   b. Recompute every mean (if double-demeaning) or rebuild the design.
   c. Refit the identical model specification, yielding `b_-g`.
   d. Compute absolute percent change:
      `100 * abs((b_-g - b_full) / b_full)`.

3. Compute jackknife statistics:
   ```
   bbar = (1/G) * sum_g(b_-g)
   SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))
   b_BC = G * b_full - (G-1) * bbar
   t_JK = b_BC / SE_JK
   ```
   Two-sided p-value from Student t with G-1 df.

### Reporting

Report the full coefficient, all G delete-coefficients aligned with cluster
order, jackknife SE, t-statistic, p-value, bias-corrected coefficient,
minimum and maximum delete coefficients with their clusters, and the
most influential cluster (greatest absolute percent change).

---

## 4. Nested Grouped Ridge / Elastic-Net Cross-Validation

**Applicable to**: leave-one-division-out ridge, leave-one-state-out ridge,
division-grouped weighted elastic net, state-blocked nested elastic net.

### 4.1 Fold Structure

**Outer folds**: Hold out one group (division, state) at a time in declared
group order.

**Inner folds**: For each outer fold, hold out every remaining group once in
declared order.

For state-based folds where counts vary, assign states to folds by descending
entity count: each state joins the currently smallest fold; use lower fold
index on equality.

### 4.2 Standardization

Within every fit (every fold x penalty combination):

1. Compute training-only **weighted mean** `mu_j` and **weighted population
   standard deviation**:
   ```
   sigma_j = sqrt(sum_i w_i (x_ij - mu_j)^2 / sum_i w_i)
   ```
   With unit weights when unweighted. For zero variance, set sigma_j = 1.

2. Standardize training rows: `z_ij = (x_ij - mu_j) / sigma_j`.

3. Apply the same `mu_j`, `sigma_j` to held-out rows.

4. Center the training outcome by its training (weighted) mean; do not scale y.

5. For ridge/elastic-net, the intercept is unpenalized (do not standardize or
   penalize it).

### 4.3 Ridge (L2) Objective and Solver

Minimize: `(1/(2n)) * sum_i w_i (y_i - a - Z_i b)^2 + (lambda/2) * sum_j b_j^2`

Where a is the unpenalized intercept. Initialize b = 0, a = mean(y_train).

**Coordinate descent** in declared feature order until convergence or sweep cap:

```
For feature j (non-intercept):
  r_j = sum_i w_i * z_ij * (y_i - a - sum_{l != j} z_il * b_l) / sum_i w_i
  b_j = r_j / (sum_i w_i * z_ij^2 / sum_i w_i + lambda)
```

After each full sweep, update intercept a to the weighted mean residual.
Stop when `max |b_j_new - b_j_old| < tol` or at the sweep cap.

### 4.4 Elastic Net (L1+L2) Objective and Solver

Minimize: `SSE/(2n) + lambda * (alpha * sum_j|b_j| + 0.5*(1-alpha) * sum_j b_j^2)`

Initialize all b_j = 0, a = mean(y_train). In declared coefficient order:

```
rho_j = sum_i w_i * z_ij * (y_i - a - sum_{l != j} z_il b_l) / sum_i w_i
b_j = S(rho_j, lambda*alpha) / (sum_i w_i z_ij^2 / sum_i w_i + lambda*(1-alpha))

where S(a, t) = sign(a) * max(|a| - t, 0)
```

Same convergence check. An unpenalized intercept is maintained.

### 4.5 Lambda/Penalty Selection

For each penalty in the declared grid:

1. Pool inner validation squared errors across all inner folds at the **row
   level** (not the mean of fold RMSEs).
2. Compute `inner_RMSE = sqrt(pooled SSE / total inner rows)`.
3. Select the penalty with the smallest unrounded inner RMSE.
4. Break ties toward the smaller penalty (or smaller alpha then smaller l1_ratio
   for elastic net).
5. Refit on all outer-training rows with the selected penalty.
6. Predict the held-out outer fold rows.

### 4.6 Pooled Metrics

After all outer folds, each eligible row has exactly one out-of-fold
prediction. Compute:

```
pooled_RMSE = sqrt(sum_i (y_i - yhat_i)^2 / n)
pooled_MAE  = sum_i |y_i - yhat_i| / n
pooled_Q2   = 1 - sum_i (y_i - yhat_i)^2 / sum_i (y_i - ybar_full)^2
pooled_R2   = 1 - sum_i (y_i - yhat_i)^2 / sum_i (y_i - ybar_full)^2
```

### Reporting

Report every outer fold: held-out group, count, complete inner grid (all
penalty x RMSE pairs in declared order), selected penalty, and outer RMSE.
Also report the pooled RMSE, MAE, and R2/Q2. When requested, report nonzero
coefficient count and coordinate cycles for each outer fold.

---

## 5. Wild Cluster Bootstrap

### 5.1 Restricted-Null Procedure

1. Fit the **full** model, compute the target coefficient `b_obs`, CR1
   cluster-robust standard error, and studentized t-statistic
   `t_obs = b_obs / SE_CR1`.

2. Fit the **restricted** model with the target variable removed. Retain
   restricted fitted values `yhat_rest` and residuals `e_rest` in entity order.

3. For each of B bootstrap replicates:
   a. Draw one weight per cluster in declared cluster order.
   b. Form `y* = yhat_rest + e_rest * weight_g` for all observations in
      cluster g.
   c. Refit the **full** model on `y*`.
   d. Recompute CR1 SE and studentized t-statistic `t*`.

4. Count exceedances: `|t*| >= |t_obs|` (with a small delta tolerance to avoid
   floating-point ties when specified).

5. Report `p = (exceedance_count + 1) / (B + 1)`.

### 5.2 PRNG: PCG32 (for state-level protocols)

64-bit state, 32-bit output. `increment = 2 * stream + 1`.

Initialize state to 0, advance once, add init_value modulo 2^64, advance.

Each advance:
```
old = state
state = old * 6364136223846793005 + increment  (mod 2^64)
xorshifted = low32(((old >> 18) xor old) >> 27)
rot = old >> 59
output = rotate_right_32(xorshifted, rot)
```

Map output modulo 6 to weights: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.

### 5.3 PRNG: xorshift32 (for county-level protocols)

Unsigned 32-bit state, initialized from the effective seed.

Each call:
```
x = x xor (x << 13)   (mask to 32 bits)
x = x xor (x >> 17)   (mask to 32 bits)
x = x xor (x << 5)    (mask to 32 bits)
```

Map the low bit: 1 -> +1, 0 -> -1 (or odd -> +1, even -> -1).

Maintain one continuous stream. Draw once per cluster per replicate in
declared cluster order. For paired-equation designs, reuse the same
cluster weight across all equations within a replicate.

### 5.4 Checkpoints

Record checkpoints **after** the listed replicate is complete, storing the
current PRNG state and the replicate's t-statistic(s). Do not reset the
stream between checkpoints.

### 5.5 Quantiles

For sorted values x[0..B-1] and probability p:

**Nearest-rank**: `x[min(B, ceil(p * B)) - 1]` (one-based rank).

**Type-7**: `h = (B-1) * p, j = floor(h), gamma = h - j`.
Then `(1-gamma) * x[j] + gamma * x[j+1]` (zero-based).

Bootstrap-t confidence interval for coefficient:
`[b_obs - t_q_upper * SE_obs, b_obs - t_q_lower * SE_obs]`
(where q_upper = bootstrap_t_q975, q_lower = bootstrap_t_q025 for 95% CI).

---

## 6. Grouped Split Conformal Prediction

### 6.1 Procedure

For each group g in declared group order (outer fold):

1. **Test set**: All observations in group g.
2. **Calibration set**: For leave-one-out designs, use the remaining groups
   directly. For partition-based designs, assign each group to a calibration
   fold by index modulo partition_count (use `(idx+1) % partition_count` or
   similar cycling); the test fold's calibration fold is the registered
   preceding partition.
3. **Training set**: All remaining groups not in test or calibration.

4. Fit the source model on training rows, predict calibration rows, and
   compute absolute residuals. For state-grouped conformal, reduce to one
   maximum absolute residual per calibration state.

5. Sort m calibration scores. With nominal coverage c:
   ```
   rank = min(m, ceil((m+1) * c))
   radius = scores[rank - 1]  (one-based)
   ```

6. Build symmetric inclusive intervals: `[yhat - radius, yhat + radius]`.

7. Report fold coverage, mean width, and test MAE.

### 6.2 Aggregation

Pool all outer-fold test-row results. Weight aggregate mean width by test-row
counts. Select worst-coverage group by smallest unrounded coverage fraction,
then earlier group order.

### 6.3 Subgroup Diagnostics (When Requested)

For each effective subgroup (state, RUCC band, prediction decile), compute
coverage and width from the pooled outer-fold results. Assign prediction
deciles after sorting all predictions by value then stable identifier;
compute signed gap = prediction mean - observation mean per decile.

---

## 7. Trajectory PCA Clustering

### 7.1 Feature Construction

Build the data matrix with rows = entities (states/counties), columns =
trajectory features in variable-major/time-major order as declared. Each row
is one entity's complete trajectory across all time periods and variables.

Standardize each column by sample standard deviation (ddof=1 for covariance,
ddof=0 for population variance as specified). Form the covariance matrix
`C = Z'Z / (n-1)`.

### 7.2 Eigendecomposition: Symmetric Jacobi

For a symmetric matrix A (p x p), iterate while max absolute off-diagonal
element > tolerance:

1. Find element (p, q) with largest absolute upper-triangle value.
   Tie-breaking: lower row, then column.

2. Compute rotation:
   ```
   tau = (Aqq - App) / (2 * Apq)
   t = sign_nonnegative(tau) / (|tau| + sqrt(1 + tau^2))
   c = 1 / sqrt(1 + t^2)
   s = t * c
   ```

3. Apply rotation to A and accumulate eigenvectors.
   Stop at tolerance or iteration cap.

### 7.3 Post-Processing

Order eigenvalues descending; for equal eigenvalues, order by original
diagonal index ascending.

For each retained eigenvector, flip sign so the earliest (lowest-index)
maximum-absolute loading is positive.

Compute scores: `S = Z * V_retained` where V columns are oriented loadings.

Explained ratio for component q: `lambda_q / sum_all_lambda`.
Cumulative sum in declared component order.

### 7.4 Deterministic K-Means Clustering

**Initialization (farthest-first)**:
1. First centroid = entity with smallest ASCII code (or lowest index).
2. Each next centroid = entity maximizing minimum squared Euclidean distance
   to already-selected centroids, tied by ASCII code.

**Lloyd iteration**:
1. Assign each entity to nearest centroid (squared Euclidean on retained PC
   scores). Tie to lower cluster ID.
2. Update centroids to arithmetic means of member scores.
3. Stop when no assignment changes and centroid movement < tolerance, or at
   the iteration cap.
4. Canonicalize final cluster IDs by centroid coordinates (sort by first
   component, then second, etc.) and assign new IDs from 1 upward.

For empty clusters: assign the entity farthest from its current centroid
(by ASCII code) among those not alone in their cluster, recompute, continue.

### 7.5 Silhouette (When Requested)

For each entity i in cluster C_I:
```
a_i = mean distance to other members of C_I (or 0 if |C_I| = 1)
b_i = min over J != I of mean distance to members of C_J
s_i = (b_i - a_i) / max(a_i, b_i)  (or 0 for singletons)
```
Average silhouette = mean of s_i. Select k with largest mean silhouette,
tie to smaller k.

### 7.6 Adjusted Rand Index

For two labelings with contingency table n_ij:
```
ARI = (sum_ij C(n_ij, 2) - expected) /
      (0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2)) - expected)

where expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)
and C(x, 2) = x(x-1)/2
```

### 7.7 Leave-One-Out Stability

For each omitted time block in declared order:
1. Delete all features belonging to that block.
2. Rebuild standardization, PCA, orientation, initialization, and clustering
   from scratch (at the selected k).
3. Compute ARI against the full-data clustering.
4. Align refit labels to full labels by maximum agreement (test all
   permutations; tie to lexicographically smallest mapped-ID vector).

Report all leave-out ARIs, the median ARI, and the minimum ARI.

---

## 8. Exhaustive Source / Perturbation Sensitivity

### 8.1 Source-Year Perturbation

Enumerate time subsets by increasing subset size, then lexicographic tuple
order. For each subset:

1. Filter the analytic dataset to those years.
2. Refit the complete model specification (double-demeaned OLS with CR1).
3. Report the target coefficient and CR1 p-value for both primary and
   parallel series.

Compute shift: `100 * |b_alt - b_baseline| / |b_baseline|`.
Same-sign: both baseline and alternate coefficients nonzero with identical sign.

**Aggregation**: Same-sign fraction, median absolute percent shift (ordinary
median of ordered shifts), maximum shift with its subset identifier. Select
worst by greatest unrounded shift, then earlier subset order.

### 8.2 Source-Group Deletion Perturbation

For each declared source group in order:
1. Remove the group's terms from the model design.
2. Reuse the full model's selected hyperparameters without retuning.
3. For every outer fold, refit with the original outer/inner fold structure
   and report outer-fold RMSE.
4. Pool row-level squared errors for pooled RMSE.

Compute deterioration: `pooled_RMSE_group - pooled_RMSE_full` (positive means
worse). Count folds where the group RMSE > corresponding full-model RMSE.
Rank groups by decreasing unrounded deterioration, then declared order.

### 8.3 Exhaustive Source Replacement with Shapley

When the task replaces a source variant for a subset of entities:

1. Resolve the alternate source records using the same publication precedence.
2. Order replaceable entities by descending absolute alternate-minus-primary
   difference, tied by entity code.
3. For m replaceable entities, enumerate all 2^m replacement masks.
4. For each mask, replace the entity's source if `mask & (1 << j)` is nonzero;
   retain fixed reliability weights and design.
5. Refit WLS with HC3 for each mask.

**Aggregation**: Report scenario counts by popcount stratum, coefficient
ranges, p-value ranges, and mean shift per stratum. Maximum shift by greatest
unrounded value then smaller mask.

**Exact Shapley values**: For entity j in ordered position:
```
phi_j = sum_{S subseteq M excluding j}  |S|! * (m-|S|-1)! / m! * [b(S U {j}) - b(S)]
```
Verify `sum_j phi_j = b(all) - b(none)` within numerical tolerance.

---

## 9. Difference / System GMM Mediation

### 9.1 First-Differenced Design

For each entity and consecutive time pair (t-1, t), create an
adjacent-change row:
- `delta_y = y_t - y_{t-1}` (outcome change)
- `delta_x = x_t - x_{t-1}` (regressor changes)
- `delta_controls` = changes in control variables
- Period indicators as specified

Order rows by entity then end period.

### 9.2 Instrument Construction

Build instruments from declared lag structures and instrument list. For
level instruments (lagged levels), use the appropriate lagged variable
values. Include period indicators and interaction instruments when declared.

### 9.3 Two-Step GMM Estimation

**First step**: With identity weight, residualize outcome and regressors
against baseline terms. Compute moments `g(theta) = Z'(y - D*theta)/n`. Solve
for theta that minimizes `g(theta)' * g(theta)`.

Form state-cluster scores `s_g = Z_g' u_g` and `S = sum_g(s_g s_g') / n`.

**Second step**: Use weight matrix W = Moore-Penrose pseudoinverse of S
with effective relative singular-value cutoff. Solve
`theta = (D'Z W Z'D)^-1 D'Z W Z'y`.

Hansen J statistic: `n * g(theta)' W g(theta)`.

### 9.4 Mediation Equations

For a 3-equation mediation system:
- **Total effect**: delta_outcome on delta_exposure + controls
- **Path A**: delta_mediator on delta_exposure + controls
- **Direct + Path B**: delta_outcome on delta_exposure + delta_mediator + controls

Indirect effect = path_a * path_b. Cross-equation covariance from shared
cluster scores. Delta method for SE as described in section 2.4.

### 9.5 First-Stage Diagnostics

Partial F for each endogenous regressor: compare full first-stage model RSS
to reduced model RSS (excluding the regressor's instruments). Compute F with
numerator df = excluded instrument count, denominator df = residual df.

### 9.6 Delete-State Diagnostics

For each state in state-code order, delete all rows belonging to that state,
recompute both GMM steps from scratch, and report the indirect effect and
direct-effect coefficient.

---

## 10. Partial R2 Mediation Sensitivity

Given unrounded baseline path-a coefficient **a**, path-b coefficient **b**,
path-b standard error **SE_b**, and residual degrees of freedom **df**:

```
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
```

where `rY` is the outcome-confounder partial R2 and `rM` is the
mediator-confounder partial R2.

For each direction in declared order:
```
adjusted_b = b - s * magnitude   (s = -1 for NEGATIVE, s = +1 for POSITIVE)
adjusted_indirect = a * adjusted_b
adjusted_direct = total - adjusted_indirect
proportion = adjusted_indirect / total  (when total != 0)
```

Enumerate the complete surface in declared R2 row-major order (rM ascending,
then rY ascending, then direction order).

**Tipping point**: The R2 value (assuming equal strength rM = rY = r2) at
which `b - s * SE_b * sqrt(df * r2 / (1 - r2)) = 0` for s = +1.
Solve: `r2 = t^2 / (df + t^2)` where `t = b / SE_b`.

---

## 11. Country Label Reconciliation

When the task provides a list of country labels:

1. Query `GET /geographies/countries` for the complete country registry.
2. For each requested label, match against `name`, `aliases` (resolve
   aliases: labels that differ from the canonical `name`).
3. Uniquely resolve ISO3 identifiers (map all labels to their canonical
   ISO3). Report resolved ISO3 sorted ascending.
4. Report the count of requested, resolved, and alias-resolution labels.

---

## 12. Panel Regression with Region Fixed Effects

Build a country-year panel from the effective year range and usable
countries. For region fixed effects, include indicator columns for each
region minus one reference (drop the first-alphabetical region, or as
specified).

Report: n (observations), coefficient, standard error, p-value (two-sided
Student t, residual df), and R2.

---

## 13. Controlled Decision

### Procedure

1. Complete every evidence module before evaluating any gate.
2. Evaluate each effective business predicate on **unrounded** values.
3. Count satisfied predicates (or gates passed).
4. Apply the effective request's decision mapping using the declared
   precedence order.

Reporting: produce one entry per gate in declared module order (PASS/FAIL),
the count of passed gates, and the final classification exactly matching one
of the effective request's controlled decision values.

### Common Gate Patterns

- Coefficient direction + p-value threshold
- Pooled Q2/R2 >= threshold and/or pooled RMSE <= threshold
- Bootstrap p-value <= threshold
- Aggregate coverage >= threshold and/or mean width <= threshold
- Minimum leave-out ARI >= threshold and/or cumulative explained variance >= threshold
- Same-sign fraction >= threshold and/or median shift <= threshold

---

## 14. Numerical Precision and Output Rules

- Compute with floating-point; round only **reported** values.
- Non-integer statistics: 4 decimal places (standard), 6 decimal places
  (county panel protocol). Encode as JSON numbers.
- Integer fields (counts, seeds, PRNG states, replicate numbers, ranks):
  natural JSON integer type.
- Boolean fields: JSON `true`/`false`.
- Use JSON `null` only when a statistic is mathematically unavailable; never
  use NaN or Infinity.
- Preserve every declared array order; do not sort independently.
- Use the declared entity codes, division names, region labels, and enum
  values exactly as specified.

---

## 15. Execution Order

Follow the effective request's declared module order exactly. Typically:

1. **Release resolution and cohort construction** -- always first.
2. **Common model fitting** (if shared across modules).
3. **Audit modules** in declared order, each computing its full required
   evidence.
4. **Controlled decision** -- always last, after all evidence modules.

Within each module, follow its registered internal order: data preparation,
fitting, inference, diagnostics, and reporting.

---

## References

- [pseudoinverse_helpers.py](pseudoinverse_helpers.py) -- Moore-Penrose
  pseudoinverse with relative singular-value cutoff.
- [pcg32.py](pcg32.py) -- PCG32 PRNG implementation (64-bit state, 32-bit
  output, unsigned wraparound).
- [xorshift32.py](xorshift32.py) -- xorshift32 PRNG implementation with
  32-bit masking.
- [jacobi_eigen.py](jacobi_eigen.py) -- Symmetric Jacobi eigendecomposition.
- [coordinate_descent.py](coordinate_descent.py) -- Ridge and elastic-net
  coordinate-descent solvers with standardization.
- [conformal.py](conformal.py) -- Grouped split conformal calibration and
  interval construction.
- [adjusted_rand_index.py](adjusted_rand_index.py) -- Adjusted Rand Index
  computation.
- [shapley.py](shapley.py) -- Exact Shapley value enumeration for source
  perturbation.
