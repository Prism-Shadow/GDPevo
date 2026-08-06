# The six audit-module families

Every task registers ~6 ordered modules drawn from the families below. The *names, cohorts, orders,
grids, seeds, and thresholds are per-task* — read them from `analysis_request`. What is reusable is the
shape of each family, the evidence it must emit, and the determinism traps. For each module, the
`required_evidence` / `required_audit_outputs` string plus the template's `required_keys`,
`array_lengths`, and `cardinality_rules` are an exact checklist — produce every listed quantity.

General determinism rules (apply to all modules):
- Use the declared **feature / coefficient / division / state / grid / checkpoint order** everywhere;
  aligned arrays are positional. Never re-sort an aligned array.
- **Standardize using training-fold statistics only** when a module says so; never leak test/holdout
  moments into scaling.
- Compute unrounded; round only reported values to the declared precision at the very end.
- Reproduce the *named* PRNG exactly (see the bootstrap family). Library RNGs will not match.

---

## Family A — Cluster jackknife / fixed-effects / GMM regression

Examples: `STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE`,
`RELIABILITY_WEIGHTED_DELETE_ONE_CENSUS_DIVISION_JACKKNIFE`,
`STATE_CLUSTERED_DIFFERENCE_GMM_MEDIATION_...`, `DELETE_STATE_BIAS_CORRECTED_TWO_STEP_LINEAR_GMM`.

Purpose: is the focal coefficient the right sign, significant, and not driven by one cluster?

Recipe:
1. Fit the declared model on the declared cohort with the declared design order (intercept + predictors,
   fixed effects, weights). Honor `reliability_weight` (a fixed per-row weight, e.g. a sample_size) if
   specified — including in every re-fit.
2. Delete one cluster at a time (state or census division), refit, and record each deletion coefficient
   (aligned to the cluster order), deleted-unit counts, and per-deletion percent change.
3. Jackknife inference: mean of delete-one coefficients, jackknife SE, t, p; **bias-corrected**
   coefficient = n·full − (n−1)·mean(delete-one) (or the declared correction). Report min/max deletion
   coefficient and the most influential cluster / maximum absolute percent change.
4. GMM variants additionally require: instrument/coefficient orders, Hansen J per fit, two-step
   weighting, and a relative pseudoinverse cutoff — follow them exactly.

Common gate: focal (bias-corrected) coefficient has the expected sign, jackknife p ≤ threshold, and max
delete-one percent change ≤ threshold.

---

## Family B — Nested leave-group-out penalized cross-validation

Examples: `NESTED_LEAVE_ONE_CENSUS_DIVISION_OUT_RIDGE`, `NESTED_LEAVE_STATE_OUT_RIDGE...`,
`DIVISION_GROUPED_NESTED_WEIGHTED_ELASTIC_NET`, `STATE_BLOCKED_NESTED_ELASTIC_NET...`.

Purpose: genuine out-of-group predictive value (not in-sample fit).

Recipe:
1. Outer split = leave-one-group-out (each Census division or state is one outer fold). Inner split =
   grouped CV within the training groups.
2. Build the feature map in the **exact declared order** (base terms, squares, interactions, indicator
   dummies, optional augmented block appended). Standardize continuous terms with **training-fold
   statistics only**; usually penalize all non-intercept terms.
3. Inner CV selects the hyperparameter(s) from the declared grid(s) — ridge `lambda_grid`, elastic-net
   `alpha` + `lambda_grid` or `alpha_grid` × `l1_ratio_grid`. Record the inner RMSE grid **aligned
   positionally to the grid order**, the selected value(s), nonzero-feature counts, coordinate-cycle
   counts (elastic net), and each outer fold's held-out RMSE and size.
4. Pool the out-of-fold predictions and report pooled RMSE / MAE / R² (a.k.a. Q²) and the worst fold.
   For an "augmented vs base" comparison, report both pooled RMSEs and the augmented-wins state count.

Common gate: pooled OOF R²/Q² ≥ threshold (and RMSE ≤ threshold), or augmented beats base by a margin.

---

## Family C — Restricted-null wild cluster bootstrap-t

Examples: `PCG32_WEBB_WILD_CLUSTER_BOOTSTRAP_T`,
`RESTRICTED_NULL_..._XORSHIFT32_..._BOOTSTRAP_T`, `RESTRICTED_NULL_PAIRED_STATE_XORSHIFT32_BOOTSTRAP_T`.

Purpose: cluster-robust significance of the focal coefficient via a bootstrap-t under the null.

Recipe:
1. Fit the source model; compute the observed CR1 (cluster-robust) t for the target term.
2. Impose the restricted null (refit with the target coefficient constrained to 0) to get null
   residuals. Resample **cluster-level** weights (Webb 6-point or Rademacher/paired, as named) for
   `replicates` draws, recompute the bootstrap-t each draw.
3. **Implement the named PRNG exactly** — PCG32 (with the declared `stream`) or XORSHIFT32, seeded with
   the declared `seed`. Advance it in the declared order. You must report **PRNG-state checkpoints** at
   the declared `checkpoint_replicates` and often the first few weight-index rows and the terminal PRNG
   state — these only match if your generator is bit-exact.
4. Report: observed coefficient/SE/t, per-batch or cumulative exceedance counts, exceedance total,
   the **plus-one p-value** = (1 + #{|t*| ≥ |t_obs|}) / (1 + replicates), and the requested bootstrap-t
   quantiles at the declared probabilities.

Common gate: bootstrap (plus-one) p-value ≤ threshold.

Determinism trap: the whole module is worthless if the PRNG is not the exact named algorithm — the
checkpoint states are the grader's proof you reproduced it. Verify the generator against its spec before
running the full replicate loop.

---

## Family D — Grouped split-conformal calibration

Examples: `GROUPED_SPLIT_CONFORMAL_RIDGE`, `STATE_GROUPED_SPLIT_CONFORMAL`,
`DIVISION_GROUPED_OUT_OF_FOLD_CONFORMAL_CALIBRATION`, `CROSS_FOLD_GROUPED_SPLIT_CONFORMAL`.

Purpose: are prediction intervals calibrated at the nominal coverage across and within groups?

Recipe:
1. Use the declared prediction source (a fixed-lambda ridge, or the nested model's OOF predictions) and
   `alpha` / `nominal_coverage`.
2. Group by division or state. For each held-out group, form absolute-residual nonconformity scores on
   the calibration set, take the **finite-sample rank** quantile threshold (⌈(n+1)(1−α)⌉/n style — use
   the declared rank rule), build intervals on the test group.
3. Report per-group: calibration/test counts, threshold/interval radius, coverage, mean width, MAE,
   worst group; and pooled coverage + mean width. Cross-fold variants cycle which fold calibrates.

Common gate: pooled/overall coverage ≥ threshold (and mean width ≤ threshold, and/or a minimum count of
groups above a per-group coverage floor).

---

## Family E — Trajectory PCA + deterministic k-means + leave-one-out ARI

Examples: `REGISTERED_COVARIANCE_PCA_DETERMINISTIC_THREE_MEANS_LEAVE_YEAR_OUT_STABILITY`,
`STATE_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_LEAVE_YEAR_OUT_ARI`,
`COUNTY_TRAJECTORY_PCA_WITH_DETERMINISTIC_KMEANS_AND_DELETE_STATE_ARI`.

Purpose: is there a stable multi-year trajectory structure?

Recipe:
1. Build each unit's trajectory feature vector in the **exact declared order** (usually value×year
   blocks, e.g. `measure_2020..measure_2024` per measure). Use the balanced/panel cohort.
2. **Covariance PCA** (declared centering; typically mean-centered, covariance not correlation unless
   stated). Report the leading eigenvalue spectrum, explained-variance ratios, cumulative ratio, and
   signed loading vectors for the retained components. Fix loading sign conventions deterministically.
3. **Deterministic k-means** on the retained PC scores: the declared `cluster_count` (often 3), a
   **fixed, reproducible initialization** (the task names it — e.g. specific seed states / farthest-point
   / declared initial centroid units), Lloyd updates counted. Report centroids, sizes, and per-unit
   labels aligned to the unit order. Some tasks pick k by silhouette over a candidate set — report
   silhouette by k and the selected k.
4. Stability: refit leaving out one year (or deleting one state) at a time, align clusters, and compute
   the **adjusted Rand index** vs the full clustering. Report per-omission ARI (in declared order),
   plus mean/median and minimum ARI.

Common gate: minimum (or mean) leave-one-out ARI ≥ threshold, and/or cumulative explained ratio of the
first components ≥ threshold.

Determinism traps: label permutations are irrelevant to ARI but matter for reported labels/centroids —
align to the declared initialization. Covariance-vs-correlation PCA and centering choice change every
number; follow the registered spec.

---

## Family F — Source / year / sensitivity perturbation

Examples: `EXHAUSTIVE_SOURCE_YEAR_FIXED_EFFECTS_PERTURBATION`,
`EXHAUSTIVE_DIRECT_VERSUS_ROLLUP_SOURCE_PERTURBATION_WITH_EXACT_SHAPLEY`,
`PARTIAL_R2_MEDIATION_SENSITIVITY_SURFACE`, `NO_RETUNE_OUTER_FOLD_SOURCE_GROUP_DELETION_AUDIT`.

Purpose: does the signal survive swapping data sources/years, deleting term groups, or plausible
confounding?

Recipe (varies most by task — follow the declared enumeration exactly):
- **Source/year subset perturbation**: enumerate every declared combination (e.g. all 16 source×year
  subsets, or every 0..M subset of states switched from direct to rollup source), refit the focal
  coefficient (keeping the fixed reliability weight if any), and report each scenario's coefficient and
  p-value, the same-sign fraction, median/maximum absolute percent shift, and the worst subset.
- **Exact Shapley** variants: attribute the all-rollup-minus-all-direct coefficient change to each
  switched unit via exact Shapley over all 2^M coalitions; report per-unit signed contributions and
  their sum (which must equal the all-vs-all difference), plus by-replacement-count strata.
- **Partial-R² mediation surface**: over the declared R²_mediator × R²_outcome grid and both bias
  directions, adjust the path-b/indirect effects and report the surface plus the equal-strength tipping
  R². Report the baseline quantities first.
- **No-retune group deletion**: reuse the full model's selected hyperparameters, delete each declared
  source-group's terms, recompute OOF RMSE, and report deterioration, worse-fold count, and rank.

Common gate: every scenario stays same-sign / stable and maximum absolute percent shift ≤ threshold; or a
specific group's deletion deterioration ≥ threshold.
