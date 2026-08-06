# Audit module catalog — the six registered families

Every PHO audit declares six modules drawn from these families. The domain and exact method
name vary, but the inputs, deterministic execution, and required evidence are stable. Execute
each module's `method`, `cohort`, ordered features, grids, seeds, replicates, and checkpoints
**exactly as declared** in `analysis_request.json`, and produce the `required_evidence` plus
every key the template lists for that module.

All numerics are computed in full precision and rounded only at output. RNG state is recorded
at the declared checkpoint replicates and at termination.

---

## 1. Delete-one-cluster inference (jackknife / two-step GMM)

**Variants seen:** `STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE`,
`RELIABILITY_WEIGHTED_DELETE_ONE_CENSUS_DIVISION_JACKKNIFE`,
`STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION_WITH_CROSS_EQUATION_DELTA_INFERENCE`,
`DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM`.

**Inputs:** a cohort (CORE_BALANCED / PRIMARY / BALANCED_PANEL), an outcome, ordered
predictors (or instrument order + coefficient order for GMM), a cluster unit
(STATE or CENSUS_DIVISION), and (for GMM) a relative-pseudoinverse cutoff.

**Execution:**
- Fit the full model on the whole cohort; record the target coefficient (and, for GMM, the
  full coefficient vector + Hansen J).
- Delete one cluster at a time, refit, and record the target coefficient per deletion
  **aligned to the cluster order** (state ascending, or registered division order).
- Jackknife inference: `delete_mean = mean(delete_coefs)`;
  `bias_corrected = N*full − (N−1)*delete_mean`;
  `jackknife_se = sqrt(((N−1)/N) * sum((delete_coefs − delete_mean)^2))`;
  `t = bias_corrected / jackknife_se`; `p = 2*(1 − CDF_t(|t|, df))` (df per the request).
  For GMM, delete-state coefficients and Hansen J per deletion, plus maximum absolute shifts.
- Influence: min/max deletion cluster + coefficient, most-influential cluster, maximum
  absolute percent change vs full.

**Required evidence (typical):** cluster/state order, cluster_n, observation_n, full target
coefficient, per-deletion coefficient vector (aligned), delete mean, bias-corrected
coefficient, jackknife SE / t / p, min/max delete cluster + coefficient, most-influential
cluster, max percent change. For mediation/GMM: panel dimensions, coefficient summaries per
equation, first-stage partial F, stacked indirect effect + interval, all delete-state
diagnostics, Hansen J, maximum shifts.

---

## 2. Nested leave-group-out ridge / elastic-net CV

**Variants seen:** `NESTED_LEAVE_ONE_CENSUS_DIVISION_OUT_RIDGE`,
`NESTED_LEAVE_STATE_OUT_RIDGE_WITH_TRAINING_ONLY_STANDARDIZATION`,
`DIVISION_GROUPED_NESTED_WEIGHTED_ELASTIC_NET`,
`STATE_BLOCKED_NESTED_ELASTIC_NET_WITH_TRAINING_ONLY_STANDARDIZATION`.

**Inputs:** a cohort (BROAD_REFERENCE / ML), outcome, `feature_order` (possibly base +
augmented), `lambda_grid` (and `alpha` / `l1_ratio_grid` for elastic-net), outer grouping
(STATE or CENSUS_DIVISION), inner grouping.

**Execution:**
- Outer loop: leave one group out. Inner loop: leave one (inner) group out of the training
  fold to select the hyperparameter. **Standardize continuous terms on training folds only**
  (fit scaler on training, apply to held-out); indicators/intercept are not standardized.
- Select hyperparameter(s) by minimum inner RMSE (ties → smallest grid index, per declared
  grid order). Refit on the full outer-training fold with the selected hyperparameter; score
  on the held-out outer group → outer RMSE.
- Pooled: `pooled_rmse = sqrt(mean(outer_rmse^2))` (or pooled over held-out rows per the
  request), `pooled_mae`, `pooled_q_squared = 1 − SS_res/SS_tot`,
  `pooled_oof_r_squared`. Worst group = max outer RMSE (or declared criterion). For augmented
  vs base: count states where augmented outer RMSE < base.

**Required evidence (typical):** cohort/fold counts, `feature_order`, `division_order` /
outer state order, `lambda_grid` (and `alpha`/`l1_ratio` grids), per-outer-fold inner RMSE
grid (aligned to the lambda/alpha grid), selected lambda/alpha per fold, nonzero feature
count, coordinate-cycle count (elastic-net), outer RMSE per fold, pooled RMSE/MAE/Q²/R²,
worst division, augmented-better state count.

---

## 3. Restricted-null wild cluster bootstrap-t

**Variants seen:** `PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T`,
`RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T`,
`RESTRICTED_NULL_XORSHIFT32_WILD_CENSUS_DIVISION_BOOTSTRAP_T`,
`RESTRICTED_NULL_STATE_WILD_CLUSTER_BOOTSTRAP_T_WITH_XORSHIFT32`.

**Inputs:** a cohort, cluster unit, target coefficient/term, `seed`, `stream` (if declared),
`replicates` / `replicate_count`, `checkpoint_replicates`, `quantile_probabilities`, the
declared RNG family, and (for mediation) the source models/equations in `target_order`.

**Execution:**
- Fit under the **restricted null** (impose the null on the target coefficient), obtain
  cluster-robust CR1 SE and the observed t-statistic. (For mediation: one bootstrap engine
  drives all equations in `target_order` together.)
- For each replicate: draw wild weights per cluster from the declared scheme (Webb 6-point or
  Rademacher) using the declared seeded RNG; impose on residuals; refit under the null;
  record the replicate t-statistic (or absolute t). Record the PRNG state and t at every
  declared checkpoint replicate. Continue for the full replicate count; record the **terminal
  PRNG state**.
- p-value: **plus-one** `p = (1 + #{|t_b| >= |t_obs|}) / (1 + B)`. Tail/exceedance count =
  `#{|t_b| >= |t_obs|}` (also report batch counts if declared, e.g., 20 batches). Quantiles of
  the bootstrap-t distribution at the requested probabilities.

**Required evidence (typical):** method/RNG metadata, `seed`, `stream`, replicate count,
cluster definition, `state_order` (must match module 1's state order where the template says
so), observed coefficient / CR1 SE / t, first-three weight-index rows (aligned to state
order) where requested, batch exceedance counts / exceedance_n, plus-one p-value, bootstrap
coefficient mean/SD, `t_quantile_probabilities` + `bootstrap_t_quantiles`, all checkpoint
replicates (replicate, prng_state, t), final PRNG state.

**RNG note:** PCG32 and XORSHIFT32 are specific bit-level generators. Implement the exact
algorithm (state, output function, advance). The seed initializes state once; `stream`
selects the PCG stream when declared. Do not substitute `Math.random` or a library default —
checkpoint states will not match.

---

## 4. Grouped split conformal calibration

**Variants seen:** `GROUPED_SPLIT_CONFORMAL_RIDGE`,
`STATE_GROUPED_SPLIT_CONFORMAL`,
`DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL_CALIBRATION`,
`CROSS_FOLD_GROUPED_SPLIT_CONFORMAL`.

**Inputs:** a cohort, group (CENSUS_DIVISION / STATE / RUCC_band / prediction decile),
`fixed_lambda` (or predictions from module 2's outer OOF), `alpha` / `nominal_coverage`,
`partition_count` where declared.

**Execution:**
- For each held-out group: fit on the rest (or reuse module-2 OOF predictions), compute
  nonconformity scores on the calibration set, take the finite-sample rank quantile at
  `1 − alpha` (ceil) as the threshold/radius, form intervals on the held-out test set, measure
  coverage and mean width. MAE per fold where declared.
- Aggregate: pooled coverage fraction and (weighted) mean interval width over all held-out
  units; worst-coverage group; count of states ≥ a declared coverage floor (e.g., 0.80).
- For RUCC bands and prediction deciles: stratify the held-out units and report per-stratum
  coverage + counts.

**Required evidence (typical):** `nominal_coverage`, `fixed_lambda`, `division_order` /
`calibration_division`, per-group `proper_train_n`/`calibration_n`/`test_n`, `threshold`/
`nearest_rank`/`radius`, `fold_coverage`, `fold_mean_width`, `fold_test_mae`, calibration
count, covered count, coverage fraction, mean width, maximum excess, `aggregate_coverage`,
`aggregate_mean_width`/`held_out_weighted_mean_interval_width`, worst-coverage division,
state coverage list, RUCC-band coverage, decile calibration rows, minimum-state coverage.

---

## 5. Trajectory PCA + deterministic k-means clustering

**Variants seen:** `REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_STABILITY`,
`STATE_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_LEAVE_YEAR_OUT_ARI`,
`REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_STABILITY` (county),
`COUNTY_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_DELETE_STATE_ARI`.

**Inputs:** a cohort (BALANCED), `feature_order` (jurisdiction × year × variable trajectory
matrix, or within-year feature blocks), `cluster_count` (fixed or selected from a candidate
grid by silhouette), `leave_year_out` / `stability_omitted_years` / `stability_deletion_unit`
(STATE), `principal_components_for_clustering` / `retained_component_count`.

**Execution:**
- **Covariance PCA** (not correlation; center, do not standardize unless declared) on the
  trajectory matrix. Record the leading eigenvalues, explained-variance ratios, cumulative
  ratio, signed loadings (PC1/PC2/PC3), and per-jurisdiction scores (aligned to state order).
- **Deterministic k-means:** initialize centroids from declared centroid states (or a
  deterministic rule tied to the data order — never random). Run Lloyd updates to convergence;
  record the update count, centroids (in PC space), cluster sizes, and labels (aligned to
  state order).
- **Stability:** leave one year out (or delete one state), recompute PCA + clustering, and
  report the **adjusted Rand index** vs the full-sample clustering for each omitted unit
  (aligned to the declared omission order). Report mean/median and minimum ARI.
- **Candidate-k selection (where declared):** compute k-means + silhouette for each candidate
  k; select the best by average silhouette; report the full cluster grid (k, inertia,
  silhouette, sizes).

**Required evidence (typical):** `feature_order`, `state_order` (match module 1 where
required), `county_count`/`state_count`, retained component count, first-N eigenvalues +
explained ratios + cumulative ratio, PC1/PC2(/PC3) loadings, per-state PC1/PC2(/PC3) scores,
`initial_centroid_states`, `lloyd_update_count`/`kmeans_iterations`, cluster centroids, sizes,
labels (aligned), `leave_year_out_order`/`stability_deletion_unit`, per-omission ARI +
aligned-agreement/assignment-changes, mean/median + minimum ARI, cluster grid + selected k.

---

## 6. Exhaustive source / year / group perturbation

**Variants seen:** `EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION`,
`EXHAUSTIVE_DIRECT_VERSUS_ROLLUP_SOURCE_PERTURBATION_WITH_EXACT_SHAPLEY`,
`NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT`.

**Inputs:** a cohort (STRICT_DUAL_SOURCE / PRIMARY), target coefficient, a primary series and
a parallel/replacement series (or ordered source groups), declared `year_subset_sizes` /
replacement-count strata / ordered groups, and (for Shapley) the registered disagreement order.

**Execution:**
- **Source-year perturbation:** enumerate all declared source/year subsets (e.g., 16 subsets
  = combinations of {primary,parallel} × {3,4,5}-year windows per the request). Refit per
  subset; record the target coefficient and CR1 p-value for both primary and parallel series
  (aligned to `subset_order`). Compute the percent shift vs the baseline; same-sign summary;
  worst subset.
- **Direct-vs-rollup Shapley:** for each primary-cohort state where both the baseline direct
  record and the replacement rollup record resolve eligible, enumerate all 2^M replacement
  scenarios (M = disagreeing states). Refit HC3-weighted model per scenario; record
  coefficient + p-value. Stratify by replacement_count (0..M). Compute **exact Shapley**
  attribution per state (average marginal contribution over all orderings) — `shapley_sum`
  must equal `all_rollup − all_direct`. Maximum-shift bitmask + replaced states + coefficient
  + p-value + percent shift. Stable-scenario count.
- **Source-group deletion (no-retune):** reuse the full-model selected hyperparameters. For
  each ordered source group, remove its terms, refit per outer fold, record per-fold RMSE +
  pooled RMSE + deterioration vs the full-model OOF reference + worse-fold count + rank.

**Required evidence (typical):** strict cohort audit (n, observations, excluded codes),
`subset_order`/`ordered_rollup_state_codes`/`ordered_source_groups`, per-subset primary +
parallel coefficients and p-values (aligned), percent shifts, `same_sign_subset_n`/
fraction, median + maximum absolute percent shift, worst subset, scenario_count,
by-replacement-count strata, stable_scenario_count, maximum-shift bitmask + states +
coefficient + p-value + percent shift, ordered Shapley effects + sum, all-replacement-minus-
all-direct coefficient, group deletion per-fold RMSE + pooled RMSE + deterioration +
worse-fold count + rank, reference full-model OOF RMSE.
