# Audit-module catalog & reproducibility contract

Every task registers a fixed set of "modules" (usually six) in
`analysis_request.json`, and `answer_template.json` fixes the exact keys/lengths
each must emit. The module *names* vary per task, but they are drawn from a small
recurring family. Recognise the family, then implement **exactly what the current
task's request declares** — its own seeds, grids, orders, and thresholds. Never
carry a constant over from a previous task; read it from the payload every time.

## The golden rule
For every module, the request supplies the reproducibility knobs and the template
supplies the output shape. Reproduce them bit-for-bit:
- **orders** (feature_order, coefficient_order, division/state order, subset order,
  checkpoint order) are load-bearing — emitted arrays must align **positionally**;
- **seeds / streams / replicate counts / checkpoint replicates** are exact;
- **grids** (lambda / alpha / l1_ratio) are used in the declared order;
- **cohorts** named by a module (e.g. `CORE_BALANCED_COHORT`) refer to the cohort
  definitions elsewhere in the same request.

## Recurring module types (map the declared method onto one of these)

1. **Delete-one / jackknife fixed-effects (or GMM) estimator.**
   Fit the declared model on the cohort; refit deleting one cluster (state / census
   division) at a time; report the full coefficient, the aligned delete-one vector,
   jackknife SE / t / p, bias-corrected coefficient, and the extreme deletions.
   Two-way fixed effects, reliability-weighted regression, and two-step linear GMM
   (with Hansen J) all appear. Cluster unit and target coefficient are declared.

2. **Nested leave-group-out ridge / elastic net CV.**
   Outer folds = leave-one-group-out (census division / state); inner CV selects the
   penalty from the declared `lambda_grid` (and `alpha` / `l1_ratio` grids for elastic
   net). **Training-only standardization** when stated. Emit outer train/test sizes,
   inner RMSE grid (aligned to the penalty grid), selected penalties, outer RMSE
   vector, and pooled RMSE / MAE / R² (or Q²). Feature maps may include polynomial /
   interaction / RUCC-indicator terms in a declared order.

3. **Wild cluster bootstrap-t (restricted null).**
   Deterministic PRNG — the request names it (**PCG32** or **xorshift32**) with a
   `seed` (and sometimes `stream`) and `replicates`. Impose the null, draw cluster
   weights (Webb / Rademacher as declared), recompute the cluster-robust (CR1) t each
   replicate. Emit observed coefficient/SE/t, the requested t-quantiles, the
   exceedance count and (plus-one) p-value, the final PRNG state, and the exact
   `checkpoint_replicates` rows (PRNG state + t at each checkpoint). The generator
   must be implemented to match the portal's methodology bit-for-bit.

4. **Grouped split / cross-fold conformal calibration.**
   Group folds by census division / state; use the declared `alpha` /
   `nominal_coverage` and (often) a fixed lambda or the ridge/elastic-net OOF
   predictions as the score source. Emit per-fold calibration/test sizes, thresholds
   (finite-sample / nearest-rank quantile), per-fold and per-group coverage & width,
   and pooled coverage / mean width / worst group.

5. **Trajectory PCA + deterministic k-means with leave-out ARI stability.**
   Build per-unit trajectory feature vectors in the declared year×feature order;
   covariance PCA; retain the declared components; deterministic k-means (declared
   `cluster_count`, deterministic init) → centroids, sizes, per-unit scores & labels
   (aligned to the unit order). Stability = re-run leaving each year (or each state)
   out and report the Adjusted Rand Index vs the full labels, plus min/median ARI.

6. **Exhaustive source / year / group perturbation (± Shapley).**
   Enumerate the declared perturbation set (all source×year subsets; all
   direct-vs-rollup replacement combinations; leave-one-source-group-out). Refit,
   collect the target coefficient / p-value per scenario, and summarise: same-sign
   fraction, median/maximum absolute percent shift, the worst scenario, and (when
   asked) an **exact Shapley** attribution whose components sum to the all-vs-none gap.

## Determinism checklist per run
- Same cohort rows, same row order → same fit. Fix row order deterministically
  (e.g. by identifier) before any algorithm that depends on it.
- PRNG output must be exactly reproducible: verify your generator against any
  checkpoint the template requests before trusting the rest.
- Do not sort an aligned result array independently of the order it must align to.
