# Reusable Audit Methods

Each audit module's `method` string names the exact algorithm. The formulas below are the
reusable, protocol-independent numerics. **Bind every parameter** (cohort, feature/coefficient
order, grid, seed/stream, replicate count, quantile probabilities, checkpoint schedule,
tolerances, caps) from the effective request. Nothing here is a task-specific answer value.

Conventions: entities are ordered by ascending entity code; clusters are the registered
grouping (STATE, CENSUS_DIVISION, etc.); `G` is the cluster count, `n` the row count, `k` the
parameter count. "Training-only" moments are computed on the rows of the current fit and
applied to held-out rows. Gates and decisions are evaluated on **unrounded** values.

---

## A. Common weighted linear algebra

Used by weighted-OLS modules (reliability-weighted audits).

- **WLS.** For design `X`, outcome `y`, positive weights `w`: set `Xw = diag(sqrt(w)) X`,
  `yw = diag(sqrt(w)) y`, solve `b = (Xw'Xw)^-1 Xw'yw` in declared column order.
- **HC3.** With `h_i = diag(Xw (Xw'Xw)^-1 Xw')` and `ew_i = sqrt(w_i)(y_i - X_i b)`,
  `V_HC3 = (Xw'Xw)^-1 Xw' diag(ew_i^2 / (1-h_i)^2) Xw (Xw'Xw)^-1`. Two-sided Student-t with
  `n-k` residual df.
- **CR1 (cluster).** For ordered clusters `g` with scores `s_g = Xw_g' ew_g`,
  `V_CR1 = [G/(G-1)] [(n-1)/(n-k)] (Xw'Xw)^-1 [sum_g s_g s_g'] (Xw'Xw)^-1`. Two-sided Student-t
  with `G-1` df.
- For **two equations** sharing clusters (mediation), the cross-equation covariance uses the
  corresponding cross-cluster score product.

---

## B. Delete-cluster fixed effects / cluster jackknife

**Two-way fixed-effects OLS (delete-one-cluster jackknife).**

- **Transform & fit.** On every active refit, transform each modeled variable as
  `z_it - entity_mean - time_mean + grand_mean`, then solve OLS **without an intercept** in
  declared predictor order. A deletion removes the whole cluster, recomputes every mean, and
  refits from scratch in entity-code order.
- **Jackknife.** For `G` delete estimates `b_-g` and mean `bbar`:
  `SE_JK = sqrt((G-1)/G * sum_g (b_-g - bbar)^2)` and `b_BC = G*b - (G-1)*bbar`. The
  registered test uses `b / SE_JK` (or `b_BC / SE_JK` per the request) with two-sided
  Student-t, `G-1` df. Select extrema by coefficient, then entity code.
- **Weighted variant (cluster jackknife).** Fit the full weighted design, then delete every
  registered cluster in order and refit the unchanged design from scratch. For target `b` and
  delete value `b_-g`, percent change is `100*abs((b_-g - b)/b)`; choose greatest unrounded
  change, tied by earlier cluster order. Inference: `b_BC = G*b - (G-1)*bbar`,
  `SE_JK = sqrt((G-1)/G * sum_g (b_-g - bbar)^2)`, test `b_BC/SE_JK` two-sided with `G-1` df.

---

## C. Nested ridge cross-validation (leave-one-group-out)

- **Folds & scaling.** Hold out one ordered group per outer fold; within each outer training
  set, hold out every remaining group once in the same order. For every fit, subtract
  training-only feature means and divide by training sample SD (ddof=1); apply those moments
  to validation/test rows. Center the training outcome by its training mean; keep the
  intercept unpenalized.
- **Solver (cyclic coordinate descent).** Initialize coefficients to zero. Cycle in declared
  feature order for objective `mean((y - a - Xb)^2) + lambda * sum_j b_j^2`. Update
  `b_j = sum_i x_ij r_ij / (sum_i x_ij^2 + n*lambda)`, where `r` excludes feature `j`. Stop
  after a full sweep when max coefficient change < effective tolerance or at the sweep cap.
- **Selection & aggregation.** For each penalty, pool all inner validation squared errors at
  row level, take RMSE, choose the smallest RMSE and then the smaller penalty; refit on all
  outer-training rows and predict all outer rows. Pool exactly one outer prediction per
  eligible row; compute RMSE, MAE, and `Q^2 = 1 - pooled_SSE / full_sample_outcome_SST`.
  Report the worst outer group (largest outer RMSE, then group order).

---

## D. Nested elastic-net cross-validation (state/division blocked)

- **Folds & features.** Hold out each registered cluster as an outer fold and each remaining
  cluster as an ordered inner fold. (For fixed-count folds, allocate states by descending
  retained-entity counts to the currently smallest fold, lower fold id on equality; sort state
  codes within folds.) Build effective raw, transformed, squared, and interaction features in
  declared order.
- **Scaling & objective.** Inside every fit, compute training-only weighted mean `mu_j` and
  weighted population SD `sigma_j = sqrt(sum_i w_i (x_ij - mu_j)^2 / sum_i w_i)`
  (unit divisor for zero variance); standardize training and prediction rows; center `y` by
  its training weighted mean without scaling `y`. Leave indicator terms unchanged. Minimize
  `sum_i w_i (y_i - Z_i b)^2 / (2 sum_i w_i) + lambda [alpha sum_j |b_j| + (1-alpha) sum_j b_j^2 / 2]`.
  Intercept unpenalized.
- **Solver.** Cold-start `b = 0` for every penalty and fold; never warm-start. In cyclic
  feature order set
  `rho_j = sum_i w_i Z_ij (y_i - sum_{l!=j} Z_il b_l) / sum_i w_i` and
  `b_j = S(rho_j, lambda*alpha) / (1 + lambda*(1-alpha))`, with
  `S(a,t) = sign(a)*max(abs(a)-t,0)`. Update the intercept by the mean residual. Stop after a
  complete cycle when max coefficient change < effective tolerance or at the cycle cap.
- **Selection & aggregation.** For each penalty pool **unweighted** inner validation squared
  errors across rows and take RMSE (not the mean of fold RMSEs). Choose smallest RMSE, then
  smaller penalty (ridge) / smaller alpha then smaller l1_ratio (elastic-net). Cold-refit on
  all outer-training rows and predict the outer holdout. Determine nonzero coefficients with
  the effective numerical cutoff. Pool outer predictions in entity order; report unweighted
  RMSE, MAE, and `R^2 = 1 - SSE / sum_i (y_i - full_sample_unweighted_mean)^2`.

---

## E. Wild cluster bootstrap (restricted-null)

The `method` string selects the PRNG: `PCG32_*` or `*XORSHIFT32*`.

- **Observed & restricted.** Use the same (double-demeaned for FE, or weighted for WLS) model
  as the fixed-effects/primary module. Studentize the full target coefficient with CR1. Fit the
  **restricted** model (without the target) and retain restricted fitted values and residuals
  in entity order.
- **PRNG.**
  - **pcg32** (64-bit state, 32-bit output): `increment = 2*stream + 1`; initialize state to
    zero, advance, add the effective initialization value mod 2^64, advance. Each advance:
    `old = state`; `state = old*6364136223846793005 + increment (mod 2^64)`;
    `xorshifted = low32(((old>>18) xor old) >> 27)`; `rot = old>>59`;
    `output = rotate_right_32(xorshifted, rot)`. Map `output mod 6` (in order) to the six
    weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
  - **xorshift32** (unsigned 32-bit): `x ^= x<<13; x ^= x>>17; x ^= x<<5`, masking to
    unsigned 32 bits after every xor. Map odd state to `+1`, even to `-1`.
- **Draw & refit order.** Maintain **one continuous stream**. For every replicate, draw once
  per cluster in registered (entity-code) order; set
  `y* = restricted_fit + restricted_residual * cluster_weight`; refit the unrestricted model;
  recompute CR1; studentize the target. For **paired** bootstrap across equations, reuse the
  same cluster sign across the paired equations. Checkpoints are recorded **after** their
  completed replicate, using the current PRNG state and that replicate's statistics, **without
  resetting** the stream.
- **Test & aggregation.** Count `abs(t*) >= abs(t_obs)` (or `t* >= t_obs - delta` per the
  request's comparison tolerance) and report plus-one `p = (1 + count)/(1 + B)`. For sorted
  values `x` and probability `p`:
  - **nearest-rank:** `x[min(B, ceil(p*B)) - 1]` (one-based rank).
  - **type-7:** `h = (B-1)*p`, `j = floor(h)`, `gamma = h - j`,
    `(1-gamma)*x[j] + gamma*x[j+1]` (zero-based).
  Use whichever the module declares. Report the requested quantiles and the terminal generator
  state.

---

## F. Grouped split conformal

- **Partition & fit (split conformal).** For each ordered outer group, use it as test; among
  remaining groups choose calibration by greatest row count then ascending group name; use all
  others for proper training. Fit ridge (or the nested-elastic-net outer predictions, when the
  module reuses them) from scratch with the effective fixed penalty and the identical
  training-only scaling/solver rules.
- **Calibration (cross-fold / grouped).** Reuse each outer center prediction and its selected
  penalty. For outer cluster `d`, hold out each other training cluster once, cold-refit the
  identical algorithm on the remaining clusters, predict the held-out calibration rows, and
  pool absolute residuals. Where states are partitioned cyclically, index states in ascending
  order and assign by index modulo the effective partition count; use the registered
  preceding calibration partition.
- **Rank interval.** Sort `m` absolute calibration residuals (or per-state maxima for
  state-grouped). With effective miscoverage `alpha` / nominal coverage `c`, use one-based
  `r = min(m, ceil((m+1)*(1-alpha)))` (or `ceil((m+1)*c)`) and `q = score[r]`. Intervals
  `prediction ± q` are **inclusive**. Report fold coverage, width, and absolute error.
- **Aggregation.** Aggregate coverage and width by outer-test row counts (weight mean width by
  held-out count). Choose worst division/coverage by smallest fraction, then earlier cluster
  order. For decile calibration, assign prediction bins after sorting by prediction and
  declared identifiers; signed gap = prediction mean − observation mean.

---

## G. Trajectory PCA + deterministic k-means + ARI stability

- **PCA.** Build columns in effective variable-major/time order (entity ASCII order).
  Standardize each column by active-sample sample SD (or population moments per the method);
  form `C = Z'Z/(n-1)` (or `Z'Z/n`). Eigendecompose with **symmetric Jacobi**: select the
  largest absolute upper-triangle off-diagonal (tie → lower row then column);
  `tau = (A_qq - A_pp)/(2 A_pq)`; `t = sign_nonnegative(tau)/(abs(tau)+sqrt(1+tau^2))`;
  `c = 1/sqrt(1+t^2)`; `s = t*c`; rotate `A` and eigenvectors; stop at the off-diagonal
  tolerance or step cap. Order components by **descending eigenvalue then original diagonal
  index**; flip each retained eigenvector so its **earliest maximum-absolute loading is
  positive**; scores are `Z` times oriented loadings; explained ratios divide by the sum of all
  eigenvalues.
- **k-means (deterministic).** Run squared-Euclidean k-means on the effective leading scores.
  First center is the **ASCII-first entity**; each next is the entity maximizing distance to
  its nearest center (tie → entity code). Assign to nearest center (tie → lower working id);
  update by member means; stop when assignments are unchanged or at the cap. For empty ids in
  order, move the ASCII-first entity among those farthest from its assigned center, recompute,
  continue. Canonicalize final ids by centroid coordinates then working id.
- **Cluster-count selection (when declared).** For each candidate `k`, run k-means and compute
  Euclidean silhouette (singleton value zero); select the largest unrounded mean silhouette,
  then smaller `k`.
- **Stability (ARI).** For each omitted time block (ascending) / deleted state (registered
  order), rebuild scaling, PCA orientation, initialization, and clustering from scratch.
  Compute the **adjusted Rand index** from the contingency table:
  `ARI = (sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2) + sum_j C(b_j,2)) - expected)`,
  with `expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)`. Align refit labels by the
  permutation with maximum agreement (tie → lexicographically smallest mapped-id vector), then
  report aligned agreement / changes. Summaries: mean and minimum ARI (and median where
  declared).

---

## H. Source perturbation

Three variants appear in the family; bind from the `method` string.

### H1. Exhaustive source-year perturbation (dual-source)
- **Enumeration.** Enumerate effective time subsets by increasing requested subset size, then
  lexicographic tuple order. Keep the effective strict analytic set unchanged. For each subset,
  refit the complete double-demeaned model separately with the **primary** and **parallel**
  series, recomputing CR1 and two-sided `G-1`-df inference for each fit.
- **Aggregation.** For baseline coefficient `b` and alternate `b_alt`,
  `shift = abs(b_alt - b)/abs(b) * 100`; same-sign requires both nonzero with identical sign.
  Compute the ordinary median of ordered shifts. Choose worst by greatest unrounded shift,
  then earlier subset order.

### H2. Source-group deletion (no-retune)
- For every source group and outer fold in declared order, remove exactly the group's terms
  and **reuse that fold's full-model selected hyperparameters without retuning**. Apply the
  same remaining-term preprocessing and solver, retain all outer-fold RMSEs, pool their squared
  errors, and subtract the full-model OOF RMSE for **deterioration**. Count folds worse than
  the corresponding full-model fold. Rank groups by decreasing unrounded deterioration, then
  declared group order.

### H3. Exhaustive direct-vs-rollup source perturbation (exact Shapley)
- **Selection order.** Resolve alternate (rollup) outcomes with the module's effective release
  filters and greatest-revision/latest-release/greatest-id precedence. Order paired entities by
  **descending absolute (alternate − primary) difference**, tie → entity code. Let `M` be the
  count of eligible disagreement entities.
- **Scenarios.** For index `j` and every mask `0 .. 2^M - 1`, replace entity `j` iff
  `mask & (1<<j)` is nonzero; retain fixed direct reliability weights and design, then refit
  WLS and HC3. Relative shift `= 100*abs((b_mask - b_zero)/b_zero)`. For each popcount stratum
  `0..M`, report scenario count, coefficient range, HC3 p-value range, and mean shift. Select
  maximum unrounded shift, tie → smaller mask.
- **Exact Shapley.** For ordered entity `j`,
  `phi_j = sum_{S not containing j} |S|! (M-|S|-1)! / M! * [b(S ∪ {j}) - b(S)]`. Preserve
  signed `phi` order and verify `sum_j phi_j = b(all replacements) - b(no replacements)` within
  numerical tolerance.

---

## I. Difference-GMM mediation (protocol-specific)

- **Change rows.** Create adjacent-change rows in entity then end-period order using the
  effective lag structure and equation bindings (total / path-a / path-b / direct).
- **GMM.** For each equation use `W = (Z'Z)^-1` and `beta = (X'ZWZ'X)^-1 X'ZWZ'y`. With
  residual `u` and cluster score `q_g = Z_g' u_g`, use the registered finite-sample cluster
  sandwich; for two equations use the cross-cluster score product.
- **Indirect effect.** `theta = a*b` with
  `Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b)`, Student-t inference with cluster df.
- **First-stage partial F** from full-vs-reduced residual sums of squares using effective
  instrument counts.
- **Delete-state.** For every delete-state diagnostic, rebuild rows and refit all affected
  equations from scratch in state order.

---

## J. Partial-R² mediation sensitivity surface (protocol-specific)

- From unrounded baseline `a`, `b`, `SE_b`, and residual df, compute
  `magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))`.
- For each declared direction: `adjusted_b = b - s*magnitude`;
  `adjusted_indirect = a * adjusted_b`; `adjusted_direct = total - adjusted_indirect`;
  `proportion = adjusted_indirect / total`.
- Enumerate the complete effective surface in declared R2-mediator × R2-outcome × direction
  order. Compute the equal-strength positive tipping root from unrounded inputs.

---

## K. Two-step linear GMM (delete-state, protocol-specific)

- **Residualize** outcome, dynamic regressors, and instruments against intercept plus
  effective baseline terms, within every full or delete-state fit.
- **First step:** moments `g(theta) = Z'(y - D theta)/n` with identity weight. Build state
  scores `s_g = Z_g' u_g` and `S = sum_g (s_g s_g')/n`; second-step weight is the registered
  Moore-Penrose inverse of `S`. Apply the registered relative singular-value cutoff to every
  pseudoinverse.
- **Second step:** compute `theta` from the weighted linear moments; `Hansen J = n * g(theta)' W g(theta)`.
- **Delete-state:** refit both steps after each state deletion in state order. With `G`
  clusters, `theta_bc = G*theta_full - (G-1)*mean(theta_delete)`; retain maximum absolute
  delete-state shifts.

---

## L. Country burden reconciliation, PCA, clustering, panel model (protocol-specific)

- **Label reconciliation.** Map requested labels to stable ISO3 via the `countries` reference
  (`canonical_name`, `portal_label`, `alternate_labels`). Count requested labels, uniquely
  resolved labels, and alias resolutions (resolved labels differing from the canonical name).
  Resolved ISO3 sorted ascending.
- **Quality audit.** Partition applicable revision events into APPLIED / non-APPLIED by
  `revision_event_id` (ascending). Detect unresolved scale-break anomaly cells; report keys as
  `ISO3|YEAR|indicator_id` (ascending). Count raw-missing, anomaly, and imputed cells; report
  usable country/indicator counts for the completed PCA matrix.
- **PCA.** Retain the declared component count; report PC1 variance fraction and the top
  absolute loadings (descending absolute loading; indicator_id ascending breaks ties).
- **Clusters.** For candidate `k in {2,3,4,5}`, compute silhouette; select the best, then
  report three-cluster sizes (LOW/MIDDLE/HIGH burden) and high-burden ISO3 (ascending).
- **Panel model.** Region-adjusted panel regression of the panel outcome on PC1 burden:
  `n_observations`, coefficient, SE, two-sided p, `R^2`, region fixed effects (boolean).
- **Advisory.** Controlled enum from the template, chosen from the panel result and cluster
  gradient per the request's rule.

---

## M. Controlled decision

- **Order.** Complete every evidence module first, in the order the request lists them.
- **Evaluate.** Evaluate every effective business predicate / gate on **unrounded** values.
- **Count & map.** Count satisfied predicates and apply the request's controlled-decision
  mapping:
  - "all gates pass" → top class;
  - "at least N gates pass" → intermediate class(es);
  - otherwise → bottom class.
  For precedence-style rules, return the **first** unsatisfied module in the listed precedence
  (or `NONE`), and the corresponding `NOT_ROBUST_AT_<MODULE>` / equivalent conclusion.
- **Report.** Each gate as the request's controlled value (e.g. `PASS`/`FAIL`, or booleans),
  the passed/supported count, and the classification/conclusion enum exactly as the template
  allows. Use only the controlled values the template declares.
