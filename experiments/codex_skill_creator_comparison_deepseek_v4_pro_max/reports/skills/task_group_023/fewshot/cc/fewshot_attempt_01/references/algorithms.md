# PHO Algorithm Reference

Detailed specifications for statistical methods appearing across PHO audit protocols. Use these when a protocol profile does not fully describe a module's algorithm, or when implementing a module from a request's own description.

---

## Double-Demeaned Fixed Effects

Used in state-level panel models without an intercept.

**Transform.** For each modeled variable x, compute the entity mean xbar_i across its time periods, the time mean xbar_t across entities, and the grand mean xbar. The transformed value is x_it - xbar_i - xbar_t + xbar. Do this for the outcome and every predictor. Apply the same transformation when a cluster is deleted: recompute all means from the remaining observations and refit from scratch.

**Fit.** Regress the transformed outcome on the transformed predictors without an intercept. Coefficient order follows the declared predictor order in the request.

**Inference.** Use cluster-robust CR1 standard errors with the declared cluster variable and G-1 degrees of freedom, or the declared effective inference method.

---

## Ridge Regression

**Objective.** For centered outcome y and standardized features Z, minimize mean((y - Z*b)^2) + lambda * sum_j(b_j^2). The intercept is estimated separately as the training outcome mean after centering.

**Cyclic coordinate descent solver.** Initialize all coefficients to zero. For each feature j in declared order, compute partial residual r_i^(j) = y_i - sum_{l != j} Z_il * b_l, then b_j = sum_i Z_ij * r_i^(j) / (sum_i Z_ij^2 + n * lambda). Stop after a complete sweep when the maximum coefficient change falls below the declared tolerance, or at the declared sweep cap.

**Standardization.** Within each fold, compute training-only means and sample standard deviations (ddof=1) for every feature. Apply these moments to transform training, validation, and test rows. For a feature with zero sample variance, use divisor 1.0 instead of 0.0.

**Lambda selection.** For each penalty lambda, pool all inner validation squared errors across rows and compute RMSE = sqrt(sum of squared errors / total inner validation rows). Select the smallest unrounded RMSE, breaking ties toward the smaller lambda value. Refit on the entire outer-training set with that lambda and predict the outer holdout rows.

**Aggregation.** Pool exactly one out-of-fold prediction per eligible row (from the outer fold where that row was held out). Compute pooled RMSE, MAE, and R^2 (or Q^2) from these pooled predictions.

---

## Nested Cross-Validation

**Outer loop.** Hold out one declared group per outer fold, in the declared group order.

**Inner loop.** Within each outer training set, hold out each remaining group once in the same declared group order.

**Selection and prediction.** For each outer fold, select the best hyperparameter using inner validation, refit on all outer-training rows, and predict the held-out outer group.

**Pooling.** Pool exactly one out-of-fold prediction per eligible row and compute aggregate metrics.

---

## Delete-One-Cluster Jackknife

**Refits.** For each cluster g in the declared cluster order, delete all observations from that cluster, refit the full model from scratch, and record the target coefficient b^(-g).

**Bias-corrected estimate.** b_BC = G * b_full - (G-1) * bbar, where bbar = mean(b^(-g)).

**Jackknife standard error.** SE_JK = sqrt((G-1)/G * sum_{g=1}^G (b^(-g) - bbar)^2).

**Test statistic.** t = b_full / SE_JK, with two-sided Student-t p-value using G-1 degrees of freedom. For weighted models, use b_full or b_BC as declared.

**Influence.** Percent change per cluster = 100 * abs((b^(-g) - b_full) / b_full). Select the maximum change, breaking ties by earlier cluster order. Report the cluster with the most extreme coefficient value (minimum or maximum as declared).

---

## Wild Cluster Bootstrap

**Restricted null.** Fit the restricted model that excludes the target coefficient (set its coefficient to zero). Retain the restricted fitted values and residuals.

**Weight generation.** For each replicate, generate one weight per cluster from a declared weight distribution (Rademacher: +1/-1 with equal probability; Webb six-point: values [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)] mapped from a uniform PRNG draw). Draw in cluster order using a single continuous PRNG stream.

**Synthetic outcomes.** y* = restricted_fitted + restricted_residual * cluster_weight for each observation in cluster g.

**Bootstrap distribution.** For each replicate, refit the unrestricted model on y*, recompute CR1 standard errors, and studentize the target coefficient: t* = (b* - b_observed) / SE* (or |t*| for absolute tests).

**Test.** Count replicates where t* exceeds the observed statistic in the declared direction. p-value = (1 + count) / (1 + B).

**Checkpoints.** Record PRNG state and t-statistics at declared replicate checkpoints after completing that replicate without resetting the PRNG stream.

**Quantiles.** For B sorted bootstrap statistics and probability p, use the declared quantile method (nearest-rank or type-7). For nearest-rank: index = ceil(p * B), value = sorted[index - 1] (one-based rank). For type-7 linear interpolation: h = (B-1)*p, j = floor(h), gamma = h - j, value = (1-gamma)*sorted[j] + gamma*sorted[j+1] (zero-based index).

---

## PCG32 PRNG

Used in specific protocols that declare `PCG32` as the PRNG.

**State and increment.** 64-bit unsigned state. increment = 2 * stream + 1. Initialize state = 0, advance once, add seed mod 2^64, advance once.

**Advance.** old = state, state = old * 6364136223846793005 + increment (mod 2^64).

**Output.** xorshifted = ((old >> 18) ^ old) >> 27 (low 32 bits). rot = old >> 59. output = rotate_right_32(xorshifted, rot).

---

## Xorshift32 PRNG

Used in protocols that declare `XORSHIFT32` as the PRNG.

**State.** 32-bit unsigned integer.

**Next value.** x ^= x << 13, x ^= x >> 17, x ^= x << 5, all truncating to unsigned 32 bits after each xor. Return the final x.

**Weight mapping.** For Rademacher: map low bit 1 to +1, 0 to -1. For paired state assignment: odd state to +1, even to -1 using the state's ordinal position.

---

## Grouped Split Conformal

**Fold assignment.** For each declared outer group in order, use it as the test fold. Among the remaining groups, select the calibration group by the declared rule (e.g., greatest row count, then ascending group name). Remaining groups form the proper training set.

**Model fitting.** Fit the declared model (e.g., ridge with a fixed lambda) on the proper training rows. Predict all calibration rows and test rows.

**Calibration scores.** Compute absolute residuals on calibration rows: |y_i - yhat_i|. For state-grouped conformal, reduce to one maximum absolute residual per calibration state.

**Rank and interval.** Sort m calibration scores ascending. With nominal coverage c and miscoverage alpha = 1 - c, use rank r = min(m, ceil((m+1) * (1-alpha))). The threshold q = score[r] (one-based index). Prediction intervals are yhat +/- q, inclusive.

**Fold and aggregate metrics.** For each test fold, report the number of covered rows, coverage fraction, and mean interval width. Aggregate across folds by pooling covered counts and row counts, using weighted mean width by test-row counts.

**Worst group.** Select by smallest coverage fraction, then earlier group order.

---

## PCA (Covariance Method)

**Feature construction.** Build columns in the declared feature order. Standardize each column by subtracting its active-sample mean and dividing by its active-sample standard deviation (sample SD, ddof=1).

**Covariance matrix.** C = Z'Z / (n-1) where Z is the standardized matrix and n is the number of rows.

**Eigendecomposition (symmetric Jacobi).** While the maximum absolute off-diagonal element exceeds tolerance:
- Select the largest absolute upper-triangle off-diagonal element. Break ties by lower row index, then lower column index.
- Compute tau = (A_qq - A_pp) / (2 * A_pq)
- t = sign_nonnegative(tau) / (abs(tau) + sqrt(1 + tau^2))
- c = 1 / sqrt(1 + t^2), s = t * c
- Rotate rows and columns p and q of A, and columns of the eigenvector matrix.

**Component ordering.** Sort eigenpairs by descending eigenvalue, then by original column index for equal eigenvalues.

**Loading orientation.** For each retained eigenvector, flip its sign so the earliest (lowest index) element with the maximum absolute value is positive.

**Scores.** S = Z * L, where L contains the oriented eigenvectors.

**Explained variance.** explained_ratio[j] = eigenvalue[j] / sum of all eigenvalues.

---

## K-Means Clustering (Deterministic Lloyd)

**Initialization (farthest-first).** First centroid is the entity with the smallest declared identifier order (e.g., ASCII-first state code). Each subsequent centroid is the entity farthest from its nearest already-chosen centroid, breaking ties by entity code.

**Assignment.** Assign each entity to the nearest centroid by squared Euclidean distance. Break ties by lower centroid working id.

**Update.** Compute each centroid as the arithmetic mean of its member scores.

**Convergence.** Stop when assignments are unchanged from the previous iteration, or at the declared iteration cap. Canonicalize final cluster ids by centroid coordinates (e.g., ascending along PC1 centroids), then by working id.

**Empty clusters.** When a cluster becomes empty, move the entity farthest from its assigned centroid (among entities not alone in their cluster) to that cluster, recompute, and continue.

**Silhouette (Euclidean).** For each point i: a_i = mean distance to points in its own cluster; b_i = min mean distance to points in another cluster; s_i = (b_i - a_i)/max(a_i, b_i). For clusters of size 1, s_i = 0. The cluster count with the largest mean silhouette is selected, breaking ties toward the smaller count.

**Adjusted Rand Index (ARI).** For two labelings U and V with contingency table n_ij:
- sum_ij C(n_ij, 2) = sum_ij n_ij*(n_ij-1)/2
- expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)
- max_index = 0.5*(sum_i C(a_i,2) + sum_j C(b_j,2))
- ARI = (index - expected) / (max_index - expected)

For stability refits, align refit labels to full labels by relabeling through the permutation with maximum agreement, breaking ties by the lexicographically smallest mapped-id vector.

---

## Elastic Net (Weighted)

**Objective.** For standardized features Z and centered outcome y with observation weights w: minimize sum_i w_i*(y_i - Z_i*b)^2/(2*sum_i w_i) + lambda * (alpha*sum_j|b_j| + (1-alpha)*sum_j b_j^2/2).

**Weighted standardization.** Weighted mean: mu_j = sum_i w_i*x_ij / sum_i w_i. Weighted population SD: sigma_j = sqrt(sum_i w_i*(x_ij - mu_j)^2 / sum_i w_i). For zero weighted variance, use sigma_j = 1.0.

**Coordinate descent update.** rho_j = sum_i w_i*Z_ij*(y_i - sum_{l!=j} Z_il*b_l)/sum_i w_i. b_j = soft_threshold(rho_j, lambda*alpha) / (1 + lambda*(1-alpha)). soft_threshold(a,t) = sign(a)*max(abs(a)-t, 0). Update intercept as the weighted mean residual.

**Cold start.** All coefficients start at zero for every lambda and fold; the intercept starts at the training weighted outcome mean.

**Convergence.** Stop after a complete cycle when max coefficient change is below tolerance or at the declared cycle cap. Determine nonzero coefficients with the declared numerical cutoff.

**Lambda selection.** Pool unweighted inner validation squared errors across all inner rows and compute RMSE. Select smallest RMSE, then smallest lambda.

---

## Two-Step Linear GMM

**First step.** g(theta) = Z'(y - D theta)/n. Weight matrix = I. Solve for theta_1 and compute residuals u = y - D theta_1.

**Second step.** For each cluster g, s_g = Z_g' u_g. S = sum_g(s_g * s_g') / n. Use the Moore-Penrose pseudoinverse S^+ as the second-step weight matrix, applying the declared relative singular-value cutoff.

**Second-step estimation.** theta_2 = argmin g(theta)' S^+ g(theta). For linear moments, this is a weighted least-squares problem. Compute Hansen J = n * g(theta_2)' S^+ g(theta_2).

**Cluster-robust standard errors.** For the second-step estimator with cluster scores, use the declared cluster-robust sandwich formula.

**Jackknife bias correction.** For each state deletion, refit both steps from scratch. theta_bc = G*theta_full - (G-1)*mean(theta_delete). Select maximum absolute shift by coefficient, then earlier state.

---

## Mediation Sensitivity (Partial R^2)

**Baseline quantities.** a = path-a coefficient (exposure -> mediator). b = path-b coefficient (mediator -> outcome). SE_b = path-b standard error. df = residual degrees of freedom from the direct/outcome model.

**Sensitivity magnitude.** For each (r_M, r_Y) pair, compute magnitude = SE_b * sqrt(df * r_Y * r_M / (1 - r_M)).

**Adjusted coefficients.** For direction d (POSITIVE or NEGATIVE): adjusted_b = b - d*magnitude. adjusted_indirect = a * adjusted_b. adjusted_direct = c_total - adjusted_indirect. proportion = adjusted_indirect / c_total.

**Equal-strength tipping point.** Solve for the positive R^2 value where adjusted_b = 0, giving adjusted_indirect = 0. This is the point at which the mediation signal disappears under equal confounding strength.

**Surface enumeration.** Enumerate in declared R^2 mediator, R^2 outcome, and direction order.

---

## Exact Shapley Attribution

**Setting.** For m entities, each with a binary inclusion/exclusion decision, the value function v(S) is the model coefficient when entities in subset S use the alternate data source.

**Shapley value.** For entity j: phi_j = sum_{S subseteq M \\ {j}} |S|! * (m - |S| - 1)! / m! * (v(S union {j}) - v(S)).

**Verification.** sum_j phi_j = v(all entities) - v(no entities), within the declared numerical tolerance.

**Ordering.** Report phi_j in the declared entity order.

---

## Difference GMM

**Data transformation.** For each entity, create adjacent-period change rows in end-period order. Change variables: Delta x_t = x_t - x_{t-1} for t in declared end years.

**Excluded instruments.** For each time period, use lagged levels as instruments for the differenced equation. The effective instrument set is built from the declared instrument list.

**Estimation.** For each equation, use the 2SLS formula with the declared instrument weighting: beta = (X'Z(Z'Z)^-1 Z'X)^-1 X'Z(Z'Z)^-1 Z'y.

**Cluster-robust inference.** For clustered observations, compute cluster scores from the structural residuals and the instruments, then use the finite-sample cluster sandwich formula.

**Cross-equation covariance.** For the indirect effect theta = a*b (product of path-a and path-b coefficients), estimate a*b_cov from the structural covariance. Var(theta) = b^2*Var(a) + a^2*Var(b) + 2*a*b*Cov(a,b).

**First-stage partial F.** For each endogenous variable, compare the full first-stage model to the reduced model excluding the excluded instruments. F = ((SSE_reduced - SSE_full)/df1) / (SSE_full/df2).

---

## Conformal Calibration (General)

**Calibration residuals.** For each outer fold, use predictions from all other folds to compute absolute residuals on calibration rows.

**Rank and coverage.** For declared nominal coverage c, compute rank r = min(m, ceil((m+1)*c)) on sorted calibration scores. The radius q = score[r] (one-based). Prediction intervals are yhat +/- q, inclusive.

**Decile calibration.** Sort predictions ascending. Assign rows to decile bins by count after any declared identifier tie-breaking. For each decile, compute prediction mean, observation mean, and signed gap = prediction_mean - observation_mean.

**RUCC-band calibration.** Group rows by the declared rurality bands and compute coverage per band.

---

## Adjacent-Change Panel Construction

**Balanced panel.** Retain entities with valid observations in every declared balanced period.

**Adjacent changes.** For each entity, create rows for each adjacent year pair (t, t+1) where t+1 is in the declared end-year set. The change variable is value(t+1) - value(t). Lagged variables use the level at the earlier period.

**Change controls.** Create change versions of declared dynamic controls.

**Reference indicators.** Create binary indicators for the later period with the declared reference period omitted.

**Interactions.** Create products of change variables with end-period indicators as declared.

---

## Release Revision Priority (Standard)

For multiple records matching the same entity-time-measure key:
1. Select the greatest FINAL revision number.
2. Among those, select the latest `released_at` timestamp.
3. Among those, select the lowest observation_id or record_id.
4. PROVISIONAL records are never selected when a FINAL record exists for the same key.

---

## Completeness and Missing-Value Rules

- A health observation is complete when its `value` is non-null, `suppression_flag` is 0, and `quality_flag` is not in the declared invalid set.
- A socioeconomic record field is complete when non-null.
- Joins are inner joins on entity and time identifiers; rows missing any required field are excluded from the analytic cohort.
- Counts of selected publications are done before completeness filtering. Counts of analytic observations are done after completeness filtering.
