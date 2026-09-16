# PHO Algorithmic Audit Methods

This reference describes every reusable computational method used across
the PHO algorithmic audit families. Implement these exactly as written;
deviations will produce results that fail the registered audit gates.

Each section describes the algorithm; the effective request supplies all
task-local bindings (entities, measures, years, hyperparameter grids,
random seeds, business predicates).

---

## 1. Release Resolution and Cohorts

### 1.1 Publication Filtering and Selection

For each declared source (health or socioeconomic), apply the effective
filters: release_status, value_type, source_type, geography.

Within each entity-time-measure tuple, select one record using this
ordered precedence:
1. Greatest revision number
2. Latest released_at timestamp
3. Lowest observation_id (health) or record_id (socioeconomic)

An observation with suppressed, invalid, withdrawn, blank, or null
analytic value is selected as publication evidence but its analytic
value is unavailable for modelling.

### 1.2 Completeness Predicates

A row is complete-case when every required field is present,
nonsuppressed, and nonnull (except explicit nulls flagged as unavailable).
Never zero-fill or impute unavailable analytic values unless the module
explicitly requires imputation.

### 1.3 Country Reconciliation

When country labels are supplied as request identifiers, map each label
to its canonical ISO3 code by querying /catalog and /geographies/countries
endpoints. Labels that differ from the canonical name count toward the
alias resolution count. The resolved ISO3 set is all distinct codes
after reconciliation, sorted ascending.

### 1.4 Revision and Anomaly Audit

Query /data/revisions for applicable revision events. Classify each as
APPLIED or not based on whether its application_status is APPLIED.
List their revision_event_id values separately, sorted ascending.

For indicator data, detect scale-break anomalies (flagged as invalid
or containing special markers in their value or scale information).
Exclude these from modelling and report them as anomaly_observation_keys
in ISO3|YEAR|indicator_id format.

### 1.5 Imputation

When missing cross-section cells need imputation, use column-median
imputation computed from the usable rows. Count raw missing cells before
anomaly exclusion, anomaly cells in the target year, and total imputed
cells (missing plus anomaly) after quality exclusions.

---

## 2. Common Linear Algebra

### 2.1 Weighted Least Squares (WLS)

For design matrix X, outcome y, and positive weights w:
- Xw = diag(sqrt(w)) @ X
- yw = diag(sqrt(w)) @ y
- b = (Xw.T @ Xw)^-1 @ Xw.T @ yw

### 2.2 HC3 Heteroskedasticity-Robust Inference

- h_i = diag(Xw @ (Xw.T @ Xw)^-1 @ Xw.T) (leverage for row i)
- ew_i = sqrt(w_i) * (y_i - X_i @ b) (weighted residual)
- V_HC3 = (Xw.T @ Xw)^-1 @ Xw.T @ diag(ew_i^2 / (1 - h_i)^2) @ Xw @ (Xw.T @ Xw)^-1
- SE = sqrt(diag(V_HC3))
- Two-sided Student t with n - k df (k = number of coefficients)

### 2.3 CR1 Cluster-Robust Inference

For ordered clusters g = 1..G:
- s_g = Xw_g.T @ ew_g (cluster score vector)
- V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw.T @ Xw)^-1 * sum_g(s_g @ s_g.T) * (Xw.T @ Xw)^-1
- SE = sqrt(diag(V_CR1))
- Two-sided Student t with G - 1 df

### 2.4 Fixed-Effects Double-Demeaning

For each variable z observe over entities i and times t:
1. Entity-mean: zbar_i = mean_t(z_it)
2. Time-mean: zbar_t = mean_i(z_it)
3. Grand mean: zbar = mean_i,t(z_it)
4. Transformed: z_it_tilde = z_it - zbar_i - zbar_t + zbar

Fit OLS without an intercept on the transformed variables.
When deleting a cluster, recompute all means from scratch on the
retained observations and refit.

### 2.5 Cross-Equation Delta Method

For indirect effect theta = a * b:
- Var(theta) = b^2 * Var(a) + a^2 * Var(b) + 2 * a * b * Cov(a,b)
- Use the cluster-robust cross-equation covariance from the stacked
  moment conditions.
- Compute confidence intervals with two-sided Student t and cluster df.

---

## 3. Fixed-Effects / GMM Regression

### 3.1 Two-Way Fixed Effects OLS

1. Apply double-demeaning transformation to outcome and all regressors.
2. Solve OLS without intercept.
3. If cluster-robust SE is requested, compute CR1 on the transformed data.

### 3.2 Difference GMM

For panel data with adjacent changes, build equations in entity-then-end-period order.

For each equation:
- W = (Z.T @ Z)^-1 (first-step weight)
- beta = (X.T @ Z @ W @ Z.T @ X)^-1 @ X.T @ Z @ W @ Z.T @ y
- g = Z.T @ u / n (moments, where u = y - X @ beta)
- S = sum_g(s_g @ s_g.T) / n (cluster scores s_g = Z_g.T @ u_g)

Second-step weight is the Moore-Penrose pseudoinverse of S (with declared
relative singular-value cutoff):
- beta_2s = (X.T @ Z @ W2 @ Z.T @ X)^-1 @ X.T @ Z @ W2 @ Z.T @ y
- Hansen J = n * g(beta_2s).T @ W2 @ g(beta_2s)

First-stage partial F: for each endogenous regressor, compute
F = ((RSS_reduced - RSS_full) / r) / (RSS_full / (n - k_full))
where r is the number of excluded instruments.

For delete-state diagnostics, rebuild all rows without the deleted
states entities and refit all equations from scratch.

### 3.3 Two-Step Linear GMM

Residualize outcome, dynamic regressors, and instruments against intercept
plus baseline terms. First step uses identity weight matrix; second step
uses the Moore-Penrose inverse of the cluster-score covariance S.

Hansen J = n * g(theta_2).T @ W2 @ g(theta_2)

Apply the declared relative pseudoinverse cutoff to every pseudoinverse.

---

## 4. Delete-One-Cluster Jackknife

### 4.1 Procedure

1. Fit the full model on all clusters.
2. For each cluster g in registered order:
   - Delete all observations from that cluster
   - Refit the identical design from scratch
   - Record the target coefficient b_-g and optional percent change:
     percent = 100 * abs((b_-g - b) / b)
3. Select extrema by greatest unrounded coefficient (or percent change),
   tied by earlier cluster order.

### 4.2 Bias-Corrected Inference

For G delete estimates b_-g and mean bbar = (1/G) * sum_g(b_-g):
- b_BC = G * b - (G - 1) * bbar
- SE_JK = sqrt((G - 1)/G * sum_g((b_-g - bbar)^2))
- t = b_BC / SE_JK
- Two-sided Student t with G - 1 df

---

## 5. Nested Ridge with Training-Only Standardization

### 5.1 Folds

Outer folds: hold out one registered group at a time.
Inner folds: within each outer training set, hold out each remaining group
in the same order.

### 5.2 Standardization

For every fit, compute from training rows only:
- mu_j = training mean of feature j
- sigma_j = training sample std of feature j (ddof=1); use 1.0 if sigma_j == 0

Apply to training and prediction rows: x_ij_scaled = (x_ij - mu_j) / sigma_j
Center the training outcome by its training mean; do not scale the outcome.

### 5.3 Ridge Solver

Minimize: mean_i((y_i - a - X_i @ b)^2) + lambda * sum_j(b_j^2)

Intercept a is unpenalized; initialize b = 0.
Cyclic coordinate descent in declared feature order:
- r_ij = y_i - a - sum_{l != j} X_il * b_l
- b_j = sum_i(X_ij * r_ij) / (sum_i(X_ij^2) + n * lambda)

Stop after a full sweep when max abs(delta b) < tolerance or at the
effective sweep cap (default: 10,000).

### 5.4 Selection and Aggregation

For each penalty lambda in the grid (ascending):
1. Pool all inner validation squared errors at row level, compute RMSE.
2. Select the lambda with smallest unrounded RMSE; break ties by smaller lambda.
3. Cold-refit on all outer-training rows with the selected lambda.
4. Predict all outer-test rows.

Pool exactly one prediction per eligible row across outer folds.
Compute:
- RMSE = sqrt(SSE / n_pooled)
- MAE = mean_i(abs(y_i - yhat_i))
- R^2 (Q^2) = 1 - SSE / SST, where SST = sum_i(y_i - full_sample_mean)^2
  Use the full-sample unweighted outcome mean for SST.

---

## 6. Nested Elastic Net with Coordinate Descent

### 6.1 Preprocessing

Same training-only standardization as ridge (Section 5.1-5.2). Do not
standardize indicator/dummy columns. Keep the intercept unpenalized.

### 6.2 Objective and Solver

Minimize: sum_i(w_i * (y_i - a - X_i @ b)^2) / (2 * sum_i(w_i))
  + lambda * (alpha * sum_j|b_j| + (1 - alpha) * sum_j(b_j^2) / 2)

Cold-start all coefficients at zero and intercept at the training
weighted outcome mean. Never warm-start.

Cyclic coordinate descent in declared feature order:
- r_j = y - a - sum_{l != j} X_l * b_l
- rho_j = sum_i(w_i * X_ij * r_j) / sum_i(w_i)
- b_j = S(rho_j, lambda * alpha) / (1 + lambda * (1 - alpha))
  where S(a, t) = sign(a) * max(|a| - t, 0)

Stop after a full sweep when max abs(delta b) < tolerance or at the
effective sweep cap (default: 5,000 cycles).

### 6.3 Hyperparameter Selection

Traverse the declared grid in outer/inner order.
For each (alpha, l1_ratio) candidate:
1. Inner: pool squared errors across inner validation rows at row level,
   compute RMSE (not per-fold RMSE).
2. Select the candidate with smallest unrounded inner RMSE; break ties by
   smaller alpha, then smaller l1_ratio.
3. Cold-refit on all outer-training rows.
4. Predict all outer-test rows.

Pool OOF predictions across outer folds. Compute unweighted RMSE, MAE,
and R^2 (using full-sample unweighted outcome mean for SST).

Determine nonzero coefficients using the effective numerical cutoff
(e.g., abs(b_j) > 1e-8).

### 6.4 Outer-Fold State Allocation (County Panel)

Allocate states by descending retained-entity counts, assigning each to
the currently smallest fold and using lower fold id on equality. Sort
state codes within folds and repeat allocation inside each outer-training
set for inner folds.

---

## 7. Wild Cluster Bootstrap

### 7.1 Observed and Restricted Model

1. Fit the full model (WLS or OLS with double-demeaning), compute cluster
   CR1 standard errors, and studentize: t_obs = b_target / SE_CR1.
2. Fit the restricted model: same design but omit the target regressor.
   Retain restricted fitted values yhat_r and residuals e_r.

### 7.2 Bootstrap Draw and Refit

Maintain one continuous PRNG stream per module; never reset mid-simulation.

For each of B replicates:
1. Draw one value per cluster (not per observation) in registered cluster
   order. Use the effective PRNG implementation.
2. Form synthetic outcome:
   y*_i = yhat_r_i + e_r_i * weight_g (for observation i in cluster g)
3. Refit the unrestricted full model on y*.
4. Recompute CR1 and studentize: t* = b*_target / SE*_CR1.

### 7.3 Test and Aggregation

- For absolute-tail test: count t* where |t*| >= |t_obs| - delta.
- Plus-one p-value: p = (count + 1) / (B + 1)
- Confidence interval: b_obs +/- q_{1-alpha} * SE_obs, using bootstrap-t
  quantiles.

Record checkpoints only after their declared replicate is complete.
Never reset the stream for checkpoints.

### 7.4 Bootstrap Quantiles

Use the method declared in the protocol:

Nearest-rank: for sorted values x (length B) and probability p:
- rank = ceil(p * B) (one-based)
- index = min(B, rank) - 1 (zero-based)
- output = x[index]

Type-seven (R default): for sorted x:
- h = (B - 1) * p
- j = floor(h); gamma = h - j
- output = (1 - gamma) * x[j] + gamma * x[j+1] (zero-based)

---

## 8. Grouped Conformal Prediction

### 8.1 Partitioning

Division-grouped (state protocols): For each outer division as test,
select calibration as the remaining division with greatest row count,
then ascending division name. Use all other divisions for proper training.

State-blocked cyclic (county protocols): Index states in ascending order.
Assign cyclic partitions by index modulo partition_count.

Cross-fold (county panel): Use outer OOF predictions in original
analytic-row order. For each held-out fold, calibrate on absolute OOF
residuals from all other folds.

### 8.2 Calibration and Interval

For calibration set of size m:
1. Compute absolute residuals: r_i = |y_i - yhat_i|.
2. For nominal coverage c, rank = min(m, ceil((m + 1) * c)) (one-based).
3. Threshold q = sorted residuals[rank - 1].
4. For each test observation: interval = [yhat_i - q, yhat_i + q] (inclusive).

When state-level calibration is required, reduce residuals to one maximum
absolute residual per calibration state, then apply the same rank rule.

### 8.3 Aggregation

Report fold diagnostics: covered count, coverage fraction, mean interval
width. Aggregate coverage and mean width by outer-test row counts.
Choose worst coverage by smallest fraction then earlier fold/division order.

---

## 9. PCA with Jacobi Eigendecomposition

### 9.1 Data Preparation

Build columns in declared variable-major/time-major order. Standardize
each column by its active-sample standard deviation (sample SD, ddof=1).
Form covariance matrix C = Z.T @ Z / (n - 1).

### 9.2 Symmetric Jacobi

While the maximum absolute upper-triangle off-diagonal |C[p,q]| > tolerance:
1. Find (p, q) with largest |C[p,q]|, breaking ties by lower row p, then column q.
2. tau = (C[q,q] - C[p,p]) / (2 * C[p,q])
3. t = sign_nonnegative(tau) / (|tau| + sqrt(1 + tau^2))
4. c = 1 / sqrt(1 + t^2)
5. s = t * c
6. Apply rotation to C and accumulate eigenvectors V.

Stop at the effective off-diagonal tolerance or step cap.

### 9.3 Component Ordering and Orientation

- Sort eigenpairs by descending eigenvalue, then by original diagonal index.
- For each retained eigenvector, flip its sign so the earliest
  maximum-absolute loading is positive.
- Scores: scores = Z @ loadings (loadings columns are eigenvectors).
- Explained ratio for component j: eigenvalue_j / sum(all eigenvalues).

---

## 10. Deterministic K-Means Clustering

### 10.1 Farthest-First Initialization

1. First center: the ASCII-first entity among the active set.
2. Each subsequent center: the entity maximizing its minimum squared
   Euclidean distance to already-chosen centers. Break ties by ascending
   entity code.

### 10.2 Lloyd Iteration

On the effective leading principal component scores:
1. Assign each point to the nearest center by squared Euclidean distance.
   Break assignment ties by lower cluster id.
2. Update each center to the arithmetic mean of its assigned points.
3. Handle empty clusters: for each empty id, reassign the point farthest
   from its current center (ties by entity id).

Stop when assignments are unchanged or at the effective iteration cap.

### 10.3 Canonicalization

Order final cluster ids by centroid coordinates: sort by pc1 ascending,
then pc2 ascending, etc., then by the original working cluster id.
Remap labels so the smallest resulting label receives 1, next 2, etc.

### 10.4 Silhouette

For each entity i in cluster C_I:
- a_i = mean distance to other points in C_I (0 if singleton)
- b_i = min_{J != I} mean distance to points in C_J
- s_i = (b_i - a_i) / max(a_i, b_i)

Average silhouette = mean_i(s_i). For singleton clusters, use 0.
Select the cluster count k with the largest unrounded mean silhouette,
breaking ties by smaller k.

### 10.5 Adjusted Rand Index (ARI)

For two clusterings U and V with contingency table n_ij:
- sum_ij C(n_ij, 2) = sum_ij (n_ij * (n_ij - 1) / 2)
- a_i = sum_j n_ij, b_j = sum_i n_ij
- expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)
- max_index = 0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2))
- ARI = (sum_ij C(n_ij, 2) - expected) / (max_index - expected)

C(n, 2) = n * (n - 1) / 2.

When aligning two clusterings, find the permutation of refit labels that
maximizes matches. Break ties by lexicographically smallest mapped-id
vector.

---

## 11. Stability (Leave-One-Out)

### 11.1 Leave-Year-Out PCA Stability

For each omitted year/time block in ascending order:
1. Remove that complete variable block from the feature matrix.
2. Rebuild standardization, PCA, orientation, and clustering from scratch.
3. Compute ARI between full and leave-out labels. Align labels by maximum
   agreement permutation, breaking ties lexicographically.

### 11.2 Leave-State-Out Stability

For each state in state-code order:
1. Remove all entities from that state.
2. Rebuild the full trajectory pipeline at the selected cluster count.
3. Compute ARI against full-sample labels. Align by maximum agreement.

Report ordered refits and summary statistics: median ARI, minimum ARI.

---

## 12. Source Perturbation

### 12.1 Enumeration

For each ordered pair of baseline and alternate outcomes bound to the same
entities, compute the difference. Order entities by descending absolute
alternate-minus-baseline difference, tying by entity code.

For M eligible entities, enumerate masks from 0 through 2^M - 1. For mask
m, entity j uses the alternate source iff (m >> j) & 1 == 1. Fit the
entire design for each mask, keeping fixed weights and design unchanged.

### 12.2 Aggregation

- Relative shift: 100 * |b_mask - b_baseline| / |b_baseline|
- For each popcount stratum (number of replacements), report scenario
  count, coefficient range, p-value range, and mean shift.
- Find maximum unrounded relative shift; break ties by smaller mask.
- Same-sign stability: both coefficients nonzero with identical sign.
- Scenario stability: every scenarios result satisfies the effective
  predicate (e.g., all scenarios stable means every coefficient is
  nonzero and same-sign).

### 12.3 Exact Shapley Attribution

For ordered entity j:
phi_j = sum_{S subset of {1..M} not containing j}
  |S|! * (M - |S| - 1)! / M! * (b(S U {j}) - b(S))

Compute for each entity in the registered disagreement order. Verify:
sum_j phi_j = b(all replaced) - b(no replacements)

---

## 13. Partial-R2 Mediation Sensitivity

### 13.1 Baseline Quantities

From the primary OLS models, extract:
- a: path-a coefficient (exposure -> mediator)
- b: path-b coefficient (mediator -> outcome)
- SE_b: classical standard error of b
- df: residual degrees of freedom from the direct model

### 13.2 Sensitivity Surface

For each declared (rY, rM, direction) combination:
- magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
- adjusted_b = b - sign * magnitude
  (sign = -1 for NEGATIVE, +1 for POSITIVE)
- adjusted_indirect = a * adjusted_b
- adjusted_direct = total_effect - adjusted_indirect
- proportion = adjusted_indirect / total_effect

Enumerate in declared R2 order: r2_mediator ascending, r2_outcome
ascending, NEGATIVE then POSITIVE.

### 13.3 Tipping Point

The equal-strength tipping R2 is the r2 value (with rY = rM) where the
positive-bias adjusted indirect effect crosses zero.

---

## 14. Region-Adjusted Panel Model

For country-level protocols, filter by effective panel years and apply
fixed effects for declared regions. Regress the declared outcome on the
burden PC1 score with region dummies. Report coefficient, SE, p-value,
R^2, and whether region fixed effects were included.

---

## A. Country-Level Operations

### A.1 Quality Audit

Query the revision endpoint. Classify events as APPLIED (application_status
== APPLIED) or not. Report distinct revision_event_id lists sorted ascending.

For cross-section indicator data: detect scale-break anomalies. Count raw
missing cells per requested indicator in the reference year. Count anomaly
cells in the reference year. Total imputed = raw missing + anomaly cells
after quality exclusions.

### A.2 Burden PCA

Run PCA (Section 9) on the completed cross-section matrix. Retain the
number of components as requested or by Kaiser criterion. Report the PC1
variance fraction and the top 3 absolute loadings (descending absolute
loading, then ascending indicator_id on exact ties).

### A.3 Silhouette-Based Cluster Selection

For each candidate k in the declared set, run deterministic k-means
(Section 10) on the leading burden scores. Compute average silhouette
(Section 10.4). Select k with largest silhouette; break ties by smaller k.

### A.4 Burden Advisory

Based on the panel model result, classify:
- PRIORITIZE_HIGH_BURDEN_CLUSTER: when the panel coefficient is
  significant and the direction confirms worse outcomes with higher burden.
- MONITOR_GRADIENT: when the relationship does not meet the prioritization
  threshold but still warrants monitoring.
- NO_ADVERSE_GRADIENT: when no significant adverse relationship exists.
