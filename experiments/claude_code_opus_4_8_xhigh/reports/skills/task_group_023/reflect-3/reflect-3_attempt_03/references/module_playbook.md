# Audit-module playbook

Requests bundle ~6 modules, each with a `standard_method`/`method` name, a `cohort`, a
feature/coefficient order, and (for stochastic ones) seeds/grids/checkpoints. The names
vary but map to the recurring estimators below. Always: use the named cohort, preserve
the declared order, and emit every field the template lists for that module.

## A. Delete-one-cluster fixed-effects / jackknife

- **Estimator**: OLS with the declared design. "Two-way fixed effects" ⇒ absorb entity
  and year (dummies with a dropped reference, or within-transform). "Reliability-
  weighted" ⇒ WLS with the declared weight (e.g. a measure's `sample_size`), and
  classical inference via **HC3** when asked.
- **Design order**: exactly as declared, e.g.
  `[intercept, exposure, adjustments..., region dummies (ref = declared)]`, income as
  `median_income/10000` when the request says "per 10000".
- **Jackknife**: delete each cluster (state, or **census division** ⇒ 9 deletions),
  refit, collect the target coefficient. Then
  `mean = mean(θ_delete)`;
  `SE = sqrt((n-1)/n · Σ(θ_i − mean)²)`;
  `bias_corrected = n·θ_full − (n-1)·mean`;
  `t = estimate/SE`, `p` two-sided from `t_{n-1}`.
- **Report**: full coefficient, per-deletion coefficient (+ deleted count, absolute %
  change vs full), mean, bias-corrected, SE, t, p, min/max deletions and the
  most-influential cluster. Percent change = `100·|θ_i − θ_full| / |θ_full|`.

## B. Nested cross-validated ridge / elastic-net

- **Outer**: leave-one-group-out over the declared grouping (division or state) ⇒ folds
  = #groups. **Inner**: CV over the hyperparameter grid (ridge: `lambda_grid`;
  elastic-net: `alpha` fixed or gridded × `l1_ratio` grid × `lambda_grid`).
- **Standardisation**: **training-fold only** (fit scaler on the inner/outer training
  rows, apply to held-out). Penalise all non-intercept terms (or exactly as stated).
  Elastic-net uses coordinate descent; report `coordinate_cycles`/`nonzero_feature_count`
  when asked.
- **Features**: build engineered terms exactly — squares, pairwise interactions,
  `log(median_income)` (natural log of *unscaled* income when specified), RUCC dummies
  (RUCC1 reference), end-year dummies (declared reference year). Keep `feature_order`.
- **Report**: per outer fold — held-out group & size, inner RMSE grid aligned to grid
  order, selected hyperparameters, standardised coefficients, outer RMSE. Pooled
  out-of-fold RMSE / MAE / R² (and `Q² = 1 − SSE/SST` when a "q_squared" is asked).

## C. Wild cluster bootstrap-t (restricted null)

- **Setup**: cluster = state or census division; impose the null on the target
  coefficient (restricted-null residuals), then resample cluster-level sign weights.
- **PRNG**: use the **named generator exactly** — `XORSHIFT32` or `PCG32` — with the
  declared `seed` (and `stream` for PCG32). Draw weights in the declared order
  (Rademacher ±1, or **Webb** 6-point when "Webb" is named). The reproducibility fields
  (PRNG state and t at each `checkpoint_replicate`, the first weight-index rows) only
  match if you replicate the generator's stream and the weight-assignment order
  precisely. See `scripts/audit_toolkit.py` for reference generators.
- **Inference**: bootstrap t = coefficient/CR1-cluster-SE per replicate under the null;
  `exceedance = #{|t*| ≥ |t_obs|}`; **plus-one p-value** `= (1 + exceedance)/(B + 1)`;
  report requested t-quantiles and the final PRNG state. CR1 = clustered
  finite-sample-corrected variance.

## D. Grouped split / out-of-fold conformal

- **Groups**: division or state (or K partitions of states). Split into proper-train and
  calibration; compute absolute residuals on calibration.
- **Threshold**: finite-sample nearest-rank quantile at nominal coverage `1−α`:
  `rank = ceil((n_cal + 1)·(1−α))`, interval radius = that order statistic of
  calibration residuals (report `finite_sample_rank`/`nearest_rank`).
- **Report**: per group — calibration/test sizes, threshold/radius, coverage, mean
  width, MAE, worst member. Pooled coverage & mean width; worst group. When predictions
  come from module B, reuse its out-of-fold predictions as the conformal score source.

## E. Trajectory PCA + deterministic k-means + leave-one-out ARI

- **Feature matrix**: one row per entity; columns = trajectory variables × years in the
  declared block order (e.g. `var_2020…var_2024` then next var). Include engineered
  blocks exactly (e.g. `log(sample_size)`).
- **PCA**: "covariance PCA" ⇒ **center** columns and eigendecompose the covariance
  matrix (mind ddof); "correlation" ⇒ also standardise. Retain the declared #components.
  Fix a **sign convention** (e.g. largest-magnitude loading positive) and apply it to
  loadings and scores consistently. Report eigenvalues, explained shares
  (eig/Σeig), loadings, scores.
- **k-means**: "deterministic k-means" means a *fixed* initialisation (commonly
  farthest-first traversal from the point farthest from the mean, or a declared
  seeding), then Lloyd updates to convergence; report initial centroids, update count,
  centroids, sizes, and labels aligned to the entity order. Order/label clusters by a
  stable rule (e.g. ascending PC1 centroid) when the template implies named tiers
  (LOW/MIDDLE/HIGH burden).
- **Stability**: leave-one-year-out (or leave-one-state-out): rebuild the trajectory,
  re-cluster, and compute the **adjusted Rand index** vs the full clustering; "aligned
  agreement" = fraction of entities keeping the same label under the best label
  permutation. Report per-fold ARI and min/median.
- **Silhouette model selection** (when asked): compute average silhouette for each
  candidate k and pick the best.

## F. Source / year perturbation and exact Shapley

- **Scenarios**: enumerate the declared perturbation set — e.g. all `2^M` subsets of M
  swappable states (direct ↔ county-rollup outcome source), or all year-subsets of the
  declared sizes. Refit the target coefficient (same weight/design) per scenario.
- **Diagnostics**: percent shift vs baseline `100·(θ_scn − θ_base)/θ_base`;
  same-sign fraction; median/max absolute % shift; the worst scenario (report its
  bitmask / replaced codes). Stratify by replacement_count 0…M.
- **Exact Shapley** (when asked): the average marginal contribution of each swap over all
  orderings; `Σ Shapley = θ_all-swapped − θ_baseline`. Enumerate exactly (M is small).

## G. Difference / two-step linear GMM (mediation & dynamics variants)

- **Difference-GMM mediation**: state-clustered, multi-period change equations with
  lagged-level instruments; report clustered coefficient summaries, first-stage partial
  F per instrument, the stacked indirect effect with cross-equation covariance
  correction, and leave-one-state-out diagnostics.
- **Two-step linear GMM dynamics**: declared instrument & coefficient orders,
  relative-pseudoinverse cutoff for the weight matrix, bias-corrected (jackknife)
  coefficients, Hansen J per fit, and delete-state diagnostics.
- These are the least forgiving modules; follow the declared instrument order,
  weighting, and cutoff literally.

---

**General**: the request's gate definitions tell you which single statistic each module
must ultimately deliver (a sign, a p-value, an RMSE/R², a coverage, an ARI, a % shift).
Make sure that headline statistic is computed even if some ancillary evidence field is
hard — but the template requires the full ordered evidence, so populate every field.
