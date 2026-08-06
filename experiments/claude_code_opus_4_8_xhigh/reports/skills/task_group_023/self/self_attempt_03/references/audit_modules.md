# Audit module families

A request registers a fixed set of modules (usually six) under `audit_modules` /
named sections. Their surface names vary, but they fall into the six families below.
For each, the request supplies the exact method name, cohort, term/feature order,
seeds, grids, and required evidence; the template fixes the output keys and array
shapes. **Implement the declared spec, not a library default**, compute unrounded,
and preserve every declared order. The recurring failure mode is a statistic that is
"right" under some library convention but wrong under the registered one.

## Family A — Delete-one cluster / fixed-effects / GMM (influence & bias)

Names seen: `STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE`,
`RELIABILITY_WEIGHTED_DELETE_ONE_CENSUS_DIVISION_JACKKNIFE`,
`STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION...`,
`DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM`.

Core: fit the declared full model, then refit deleting one cluster at a time
(state / census division), in the registered cluster order. Report the full
coefficient, the aligned delete-one coefficient vector, delete mean, jackknife SE
`sqrt((G-1)/G · Σ(θ_(g) − θ̄)²)`, jackknife t and p (t against the declared df /
normal), a **bias-corrected** coefficient `Gθ̂ − (G−1)θ̄`, min/max delete cluster and
their coefficients, and max absolute percent change. GMM variants add the two-step
weight matrix, Hansen J, instrument order, and a relative-pseudoinverse cutoff — use
exactly those. Weighted variants use the fixed reliability weight (a selected
`sample_size`) in every fit, including deletions.

## Family B — Nested cross-validated penalized regression (predictive stability)

Names: `NESTED_LEAVE_ONE_CENSUS_DIVISION_OUT_RIDGE`, `NESTED_LEAVE_STATE_OUT_RIDGE_
WITH_TRAINING_ONLY_STANDARDIZATION`, `DIVISION_GROUPED_NESTED_WEIGHTED_ELASTIC_NET`,
`STATE_BLOCKED_NESTED_ELASTIC_NET...`.

Core: leave-one-group-out **outer** folds (group = state or census division);
within each outer training set, an **inner** CV selects the hyperparameter(s) from
the declared grid (`lambda_grid`, plus `alpha`/`l1_ratio` grids for elastic net) by
inner grouped RMSE; refit on the full outer-train with the selected value; predict
the held-out group. Critical details:

- **Standardize using training-fold statistics only** (never the whole sample);
  apply the same transform to the held-out fold.
- Match the **penalty parameterization** and the **exact feature order** (including
  polynomial/interaction terms and RUCC indicator dummies with the declared
  reference level). Penalize the declared term set (usually all non-intercept).
- Report per-outer-fold: held-out group, n, aligned inner-grid RMSE (aligned to the
  grid order), selected hyperparameters, nonzero/coefficient info, coordinate-cycle
  checkpoints where asked, and outer RMSE. Then pooled out-of-fold RMSE / MAE / R²
  (some call it Q²). Augmented-vs-base variants report both and the per-group win
  count.

## Family C — Wild cluster bootstrap-t (restricted null) — EXACT PRNG

Names: `PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T`, `RESTRICTED_NULL_PAIRED_STATE_
XORSHIFT32_BOOTSTRAP_T`, `RESTRICTED_NULL_XORSHIFT32_WILD_CENSUS_DIVISION_
BOOTSTRAP_T`, `RESTRICTED_NULL_STATE_WILD_CLUSTER_BOOTSTRAP_T_WITH_XORSHIFT32`.

Core: impose the null on the target coefficient, resample cluster-level weights, and
build a bootstrap-t reference distribution for the CR1 cluster-robust t. This module
is graded on **bit-exact reproducibility**:

- Implement the **named generator yourself** (PCG32 or xorshift32) with the declared
  `seed`, and `stream` if given. The request lists **checkpoint replicates** at which
  you must report the intermediate PRNG state and t-statistics — these only match if
  your generator, draw order, and weight mapping are identical to the spec.
- Weights: Webb 6-point vs Rademacher ±1 per the method name. Cluster unit and
  cluster order are declared; "first three weight-index rows" must align columns to
  the state/cluster order.
- Report observed coefficient, CR1 SE, observed t, per-batch/checkpoint exceedance
  counts, exceedance total, the **plus-one p-value** `(1+#exceed)/(1+R)`, requested
  bootstrap-t quantiles, and (when asked) the final PRNG state.

## Family D — Grouped split / cross-fold conformal calibration

Names: `GROUPED_SPLIT_CONFORMAL_RIDGE`, `STATE_GROUPED_SPLIT_CONFORMAL`,
`DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL_CALIBRATION`,
`CROSS_FOLD_GROUPED_SPLIT_CONFORMAL`.

Core: split by group (state / census division / K partitions); on a calibration set
compute nonconformity scores (usually `|residual|`) and take the finite-sample
quantile at nominal coverage `1−α` via the **ceiling rank** `⌈(n+1)(1−α)⌉/n`; form
`ŷ ± qhat` intervals on held-out data. Report per-fold/per-group: calibration n,
finite-sample rank, threshold/radius, held-out n, covered count, coverage, mean
width, worst group; then pooled coverage and (often weighted) mean width. Predictions
may come from a fixed-λ ridge or from Family B's outer OOF predictions — use the
declared source.

## Family E — Trajectory PCA + deterministic k-means + leave-out ARI stability

Names: `REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_
STABILITY`, `STATE_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_LEAVE_YEAR_OUT_ARI`,
`COUNTY_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_DELETE_STATE_ARI`.

Core: build one row per entity by stacking the declared variables across the declared
years in the declared within-year/feature order; PCA via **covariance-matrix
eigendecomposition** (fix a deterministic sign convention, e.g. largest-magnitude
loading positive — follow the spec); retain the declared component count; run
**deterministic** k-means with the declared initialization (e.g. specific seed states
as initial centroids) and Lloyd iterations to convergence; report eigenvalues,
explained ratios (and cumulative), signed loadings, per-entity PC scores (aligned to
the entity order), initial centroids, final centroids, cluster sizes, labels, and
Lloyd update count. Stability: re-run leaving out one year (or one state) at a time,
align labels, and report each **adjusted Rand index** plus min/median. Some variants
also select the best k by silhouette over a candidate list.

## Family F — Source / year / group perturbation (exhaustive robustness)

Names: `EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION`, `EXHAUSTIVE_DIRECT_
VERSUS_ROLLUP_SOURCE_PERTURBATION_WITH_EXACT_SHAPLEY`, `PARTIAL_R2_MEDIATION_
SENSITIVITY_SURFACE`, `NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT`.

Core: systematically perturb the design and measure how the target coefficient/p-value
moves. Variants: enumerate all year-subset × source combinations (e.g. 16 = source×
subset); swap the outcome source direct↔rollup across all subsets of the disagreeing
entities (2^M scenarios) and compute **exact Shapley** attributions per entity; sweep
a partial-R² confounding surface; or delete one predictor group at a time reusing the
full model's selected hyperparameters (no retune). Report the registered subset/group
order, coefficient and p-value vectors, absolute percent shifts, same-sign fraction,
median/max absolute percent shift, worst subset, and (Shapley variant) the ordered
per-entity effects and their sum equal to `all-swapped − all-baseline`.

## Gates and classification

Each request states gate predicates over the module outputs and a precedence rule.
Evaluate each gate to a boolean, count passes, and map to the classification enum
exactly:
- "all N pass → PRIMARY/ROBUST/CONSISTENT/DEPLOY; ≥k pass → intermediate; else →
  none/NOT ROBUST/RETAIN", or
- ordered "NOT_ROBUST_AT_<first failed module>" with a `first_failed_module` field.
Emit only the enum vocabulary the template allows, and only those gate booleans.
