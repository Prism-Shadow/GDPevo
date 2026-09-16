Statistical Module Implementations
==================================

This reference contains reusable implementations for every statistical module
that appears across PHO audit protocols. Bind parameters from the effective
analysis request; bind entity identifiers, time coordinates, and outcome and
predictor selections from the resolved request.

Delete-One Cluster Fixed Effects
--------------------------------

Estimate a two-way fixed-effects model and assess cluster influence via
delete-one-cluster jackknife.

1. Build X (predictors in declared order) and y for the specified balanced
   cohort. Entity order: entity-code ascending. Time order: year ascending.
2. Double-demean: z_tilde_it = z_it - mean_i(z) - mean_t(z) + grand_mean(z).
3. OLS without intercept: solve (X'X)b = X'y on the demeaned matrices.
4. For each cluster g in entity-code order:
   a. Remove cluster g. Recompute entity/time/grand means on remaining data.
   b. Re-demean. Refit OLS. Record target coefficient b_-g.
5. Jackknife: bbar = mean(b_-g), SE_JK = sqrt((G-1)/G * sum((b_-g - bbar)^2)).
   t = b / SE_JK, p = two-sided Student-t with G-1 df.
   b_BC = G*b - (G-1)*bbar (bias-corrected).
6. Extremes: minimum and maximum b_-g. Tie: coefficient value then entity code.

Weighted variant (HC3): Multiply each observation by sqrt(weight). Hat matrix
diagonals h_ii from weighted projection. HC3: replace e_i with e_i/(1-h_ii)
in the variance estimator. Division-level clusters use the same logic.

Delete-State Two-Step GMM
--------------------------

Bias-corrected linear GMM with delete-one-state diagnostics.

1. Balanced panel: entity-code ascending then time ascending. First-difference
   the outcome and all right-hand-side variables.
2. First step: weighting = (Z'Z)^-1, b1 = (X'Z(Z'Z)^-1Z'X)^-1X'Z(Z'Z)^-1Z'y.
3. Second step: residuals e1, weighting = (Z'*diag(e1_i^2)*Z)^-1, recompute b2.
4. Hansen J: J = e'Z*(Z'diag(e^2)Z)^-1*Z'e, df = L - K.
   Pseudo-inverse with relative cutoff (declare in request, typically 1e-12).
5. State-clustered covariance. Report coefficients in declared coefficient
   order and Hansen J statistic.
6. Jackknife: omit each state, re-estimate full two-step GMM. Bias-corrected =
   G*b_full - (G-1)*bbar_mean. Maximum absolute shift across states.

Nested Ridge / Elastic Net Cross-Validation
-------------------------------------------

Leave-group-out nested CV selecting penalties by inner validation RMSE.

1. Outer: hold out one group in declared group order. Inner: hold out each
   remaining group in the same order.
2. Scaling: training-only means and SDs (ddof=1) for continuous features.
   Apply same moments to validation and test rows.
3. Ridge solver: center y, unpenalized intercept. Init b=0. Cycle in declared
   feature order. For feature j: b_j = sum_i(x_ij * r_ij) /
   (sum_i(x_ij^2) + n*lambda). r_ij excludes feature j. Stop at max sweep
   (default 1000) or when max|delta| < tol (default 1e-6).
4. Elastic-net: penalty = alpha*l1_ratio * sum|b_j| + alpha*(1-l1_ratio) *
   sum(b_j^2). Coordinate descent with soft-threshold: r_ij = y_i -
   sum_{k!=j}(x_ik*b_k), num = (1/n)*sum_i(x_ij*r_ij), denom = (1/n)*
   sum_i(x_ij^2) + alpha*(1-l1_ratio), b_j = sign(num)*max(0,|num|-
   alpha*l1_ratio) / denom. Indicator/dummy terms are NOT standardized.
5. Selection per outer fold: smallest inner-pooled RMSE. Tie: smaller penalty
   (ridge) or smaller alpha then smaller l1_ratio (elastic-net). Refit on all
   outer-training rows.
6. Pool one outer prediction per row. RMSE, MAE. R^2 = 1 - pooled_SSE/
   full_sample_SST. For ridge with Q^2 naming use identical formula.

Wild Cluster Bootstrap (PCG32)
-------------------------------

Restricted-null wild cluster bootstrap t-test.

1. Fit unrestricted double-demeaned OLS (same as FE module). Compute per-
   cluster scores: s_g = X_g' * e_g. CR1: V = [G/(G-1)]*[(n-1)/(n-k)]*
   (X'X)^-1 * sum_g(s_g*s_g') * (X'X)^-1. t_obs = b_target/sqrt(V_target).
2. Fit restricted model without target predictor. Retain fitted yhat_r and
   residuals e_r.
3. PCG32: 64-bit state, unsigned wraparound. increment=2*stream+1 (odd).
   Init state=0, advance, add seed mod 2^64, advance. Advance: old=state,
   state=old*6364136223846793005+increment (mod 2^64). xorshifted=low32(
   ((old>>18)^old)>>27), rot=old>>59, out=rotate_right_32(xorshifted,rot).
   Map out mod 6 to [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].
4. One continuous generator. Each replicate: draw one weight per cluster in
   entity-code order. y* = yhat_r + e_r * cluster_weight. Refit unrestricted,
   recompute CR1, studentize t*.
5. Checkpoints: record state after completed replicate, no stream reset.
   State reported as unsigned 32-bit (cast of 64-bit state).
6. p = (1 + count(|t*|>=|t_obs|)) / (1 + B).
7. Quantiles: sorted x, nearest-rank: x[min(B,ceil(p*B))-1] (one-based).

Wild Cluster Bootstrap (XORSHIFT32)
------------------------------------

Same framework as PCG32 with XORSHIFT32 PRNG.

XORSHIFT32: 32-bit state init with seed. Each step: state^=state<<13;
state^=state>>17; state^=state<<5. Output = state. Map mod 6 to same
six-element weight vector. Checkpoints: record 32-bit state after each
checkpoint replicate. For absolute t bootstrap (train 004 pattern): the
test statistic is |t_obs| and exceedance counts |t*| >= |t_obs|.
For paired multi-equation bootstrap (train 002 pattern): run three
separate restricted-null bootstraps sharing one continuous generator.
For single-equation bootstrap (train 005 pattern): run on the target
coefficient from unpenalized OLS with cluster-robust CR1 SE.

Difference GMM Mediation
------------------------

State-clustered difference GMM mediation with cross-equation delta-method
inference for the stacked indirect effect.

1. Balanced panel: entity then year. First-difference outcome and RHS vars.
2. Three equations: Total (outcome ~ exposure + controls), Path-A
   (mediator ~ exposure + instruments + controls), Direct/Path-B
   (outcome ~ exposure + mediator + controls). All estimated by GMM with
   state-clustered SEs.
3. Instruments: lagged levels of endogenous variables (exposure lagged two
   years, mediator lagged two years) plus period indicator.
4. First-stage partial F: F-test on excluded instruments. Report for both
   delta_exposure and delta_mediator.
5. Stacked indirect: path_a * path_b. Cross-equation covariance from joint
   moments. Delta-method SE: Var(indirect) = b_b^2*Var(b_a)+b_a^2*Var(b_b)
   +2*b_a*b_b*Cov(b_a,b_b).
6. Confidence intervals: estimate +/- t_crit * SE.
7. Delete-one-state: re-estimate all three equations, recalculate indirect
   and direct effects for each omitted state.

Partial-R2 Mediation Sensitivity Surface
----------------------------------------

Assess sensitivity of the indirect effect to unobserved confounding.

1. Baseline: path_a coefficient, path_b coefficient, path_b SE, residual df
   from direct model.
2. For each (r2_med, r2_out, bias_dir) triple:
   bias_a = dir_sign * b_a * sqrt(r2_med/(1-r2_med))
   bias_b = dir_sign * b_b * sqrt(r2_out/(1-r2_out))
   adjusted_b = b_b + bias_b
   adjusted_indirect = b_a * adjusted_b
   adjusted_direct = b_direct + bias_a
   proportion = adjusted_indirect / (b_a * b_b)
3. Equal-strength tipping R2: smallest r2 where both equal and adjusted
   indirect crosses zero (interpolate between grid points).
4. Surface ordered: r2_med ascending, r2_out ascending, NEGATIVE then
   POSITIVE within each pair.

Grouped Split Conformal
------------------------

Out-of-fold conformal prediction intervals.

1. For each ordered outer group g (test): designate g as test. From remaining
   groups, pick calibration by greatest row count then ascending group name.
   All other remaining groups = proper training.
2. Fit ridge on proper training with fixed penalty, training-only scaling,
   and solver rules from nested ridge module.
3. Calibration: sort m absolute residuals ascending. With miscoverage alpha,
   one-based r = min(m, ceil((m+1)*(1-alpha))), threshold q = score[r].
   Intervals: prediction +/- q, inclusive.
4. Per fold: coverage fraction, mean width (2*q), MAE. Aggregate coverage
   and width weighted by outer-test row counts.
5. State-level calibration variant: For each state, compute its coverage and
   mean width across all observations assigned to that state. Order state
   reports by state_abbr ascending.
6. Prediction-decile variant: sort all OOF predictions, bin into deciles,
   compute prediction_mean, observation_mean, and signed_gap per decile.

Trajectory PCA Clustering
--------------------------

PCA on entity trajectories, k-means clustering, leave-time-out stability.

1. Feature matrix: columns = variables * years, variable-major/time order.
   Rows = entities in entity-code order. Standardize each column: subtract
   mean, divide by SD (ddof=1).
2. Covariance: C = Z'Z/(n-1). Jacobi eigen-decomposition:
   - Largest |off-diag|, tie: lower row then column.
   - tau = (A_qq-A_pp)/(2*A_pq), sign_nonnegative(tau) = 1 if tau>=0 else -1,
     t = sign_nonnegative(tau)/(|tau|+sqrt(1+tau^2)).
   - c = 1/sqrt(1+t^2), s = t*c. Rotate A and eigenvectors.
   - Stop at max|off-diag| < tol (default 1e-12) or step cap.
3. Order PCs: descending eigenvalue, then original diag index. Flip each
   loading so earliest max-abs entry is positive. Scores = Z * loadings.
4. K-means (squared Euclidean):
   - First center: ASCII-first entity. Next: entity maximizing min dist to
     existing centers, tie by entity code.
   - Assign: nearest center, tie by lower working id. Update: member means.
   - Stop when assignments unchanged or at cap. Canonicalize: sort centers
     by coordinates then working id.
5. Leave-time-out stability: omit each time block, rebuild, re-standardize,
   re-PCA, re-orient, re-initialize, re-cluster. ARI between refit and full.
   Align refit labels: max agreement across permutations, tie: lexicographically
   smallest permutation.
   ARI: (sum_ij C(n_ij,2)-expected)/(0.5*(sum_i C(a_i,2)+sum_j C(b_j,2))-expected)
   where expected = sum_i C(a_i,2)*sum_j C(b_j,2)/C(n,2), C(x,2)=x*(x-1)/2.
6. Delete-state variant: omit all counties of one state, recompute PCA and
   clustering. Report ARI for each omitted state, median, and minimum.

Country Burden PCA and Clustering
----------------------------------

Burden-oriented PCA on cross-sectional country indicators, k-means by
requested k, silhouette-based best-k selection.

1. Cross-section matrix: rows = usable countries (post quality exclusions),
   columns = usable indicators. Impute missing cells with column median
   before scaling. Standardize columns (ddof=1).
2. PCA via Jacobi (same as trajectory PCA). Report leading components,
   top absolute loadings (descending |loading|, tie: indicator_id ascending).
3. K-means clustering on leading PC scores using the same algorithm.
   Report cluster sizes and member iso3 sets.
4. Silhouette selection: for k in [2,3,4,5], compute average silhouette.
   Select k with maximum silhouette. Tie: smaller k.

Panel Model with Region Fixed Effects
--------------------------------------

1. Balanced panel: entity then time. Outcome ~ PC1_burden_score +
   region indicators (one region reference excluded).
2. OLS estimation. Report coefficient, SE, two-sided p-value (t with
   n-k-1 df), R^2, observation count.

Source Perturbation
--------------------

Exhaustive source perturbation with Shapley (state-level):

1. Identify M entities where both baseline and replacement records resolve.
   Ordered by entity code ascending.
2. Enumerate all 2^M scenarios: by increasing replacement count, then
   lexicographic bitmask. For each, replace designated entities' source
   values and refit. Use reliability weighting if specified.
3. Per stratum (by replacement count): scenario count, min/max coefficient,
   min/max p-value, mean absolute percent shift.
4. Stability: scenario is stable if coefficient maintains same sign as
   baseline. Report stable count.
5. Maximum-shift scenario: greatest |percent shift|, then earlier bitmask.
   Report bitmask (integer), replaced codes, coefficient, p-value, shift.
6. Exact Shapley: for each entity i, marginal contributions averaged over
   all orderings. sum(Shapley) must equal all_replacement - all_baseline
   coefficient difference.

Source-group perturbation:

1. Full model OOF RMSE as reference (no retuning of hyperparameters).
2. For each source group in declared order, remove its terms, re-predict
   using the fixed outer-fold structure. Compute per-fold RMSE, pooled RMSE.
3. Deterioration = pooled_rmse - reference_rmse. worse_fold_count = folds
   where group RMSE > reference RMSE. Rank 1 = worst (largest deterioration),
   ascending for better. Tie: source-group order.

Year-subset perturbation:

1. Enumerate all time subsets of requested sizes: increasing size, then
   lexicographic tuple order.
2. For each subset, refit the double-demeaned model with primary and
   parallel series separately. Recompute CR1 inference.
3. Shift = |b_alt - b|/|b|*100. Same-sign: both nonzero, identical sign.
4. Median shift, same-sign fraction. Worst: greatest unrounded shift then
   earlier subset order.

Controlled Decision
--------------------

1. Complete every module in effective execution order.
2. Evaluate every gate predicate on unrounded internal values.
3. Count satisfied gates.
4. Apply the effective decision mapping with precedence rules.
5. For precedence-based decisions: scan gates in declared order. The first
   gate that fails determines the classification. If all pass, the terminal
   positive label applies.
6. For count-based decisions: apply the threshold rules (e.g., all-six-pass,
   at-least-four, at-least-two, otherwise).
7. Gate evaluation uses computation-time values; reporting rounds to the
   declared decimal places.

Country Quality Audit
----------------------

1. Revisions: scan /data/revisions for the matching domain. APPLIED events
   have status "APPLIED"; list their revision_event_ids sorted ascending.
   Non-APPLIED (PENDING, WITHDRAWN) similarly.
2. Anomaly cells: country indicator cells where quality_flag signals an
   unresolved scale break (quality_flag = "SCALE_BREAK"). Format each as
   "ISO3|YEAR|indicator_id". Sort ascending.
3. Missing 2022 cells: count requested indicator cells for 2022 that are
   null/suppressed before anomaly exclusions.
4. Anomaly 2022 cells: count of those missing cells that are annotated as
   scale breaks.
5. Imputation: impute remaining missing cells with column median across
   non-missing countries for that indicator.
