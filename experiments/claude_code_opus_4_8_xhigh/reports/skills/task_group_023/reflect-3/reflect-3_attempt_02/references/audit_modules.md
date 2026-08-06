# Recurring audit-module families

Every PHO "registered algorithmic audit" `analysis_request.json` declares ~six
modules drawn from the families below, then a decision rule over per-module gates.
The module *names* and hyperparameters vary per task; the underlying algorithm
family and its reproducibility conventions are stable. Read the request's
`standard_method`, `feature_order`/`coefficient_order`, grids, seeds and
`required_evidence`/`required_audit_outputs` — they fully specify what to emit.

Implement each module from the request's declared spec; the notes below are the
conventions that make the numbers reproducible. Match them exactly — the graded
value is the *number*, so a wrong SE variant, standardization scope, PRNG or
tie-break makes the whole field wrong.

## 1. Delete-one-cluster jackknife on a fixed-effects / GMM model
- Fit the declared model (two-way state+year fixed effects OLS, or reliability-
  weighted linear model, or two-step linear GMM) on the declared cohort.
- Report the full-sample focal coefficient, then refit deleting each cluster
  (state / census division) once; the delete vector aligns positionally to the
  declared cluster order.
- Jackknife SE = sqrt((G-1)/G · Σ(θ_g − θ̄)²), θ̄ = mean of deletes, G = #clusters.
  Bias-corrected θ = G·θ_full − (G−1)·θ̄. t = θ_full / SE_jk, two-sided p on df=G−1.
- Also emit min/max delete cluster + coefficient and max |percent change|.
- Fixed effects can be dummies or within-transform (focal coef identical). The
  focal coefficient depends on the focal regressor's *units* — apply declared
  rescalings (e.g. `median_income_per_10000`, `log_income`) exactly.

## 2. Nested leave-group-out ridge / elastic-net (out-of-fold prediction)
- Outer folds = leave-one-group-out (census division, or state, or K blocked
  folds). Inner CV over the declared λ grid (and α / l1_ratio grid for elastic
  net), grouped the same way inside the training part.
- **Training-only standardization**: compute mean/sd on the training fold only,
  apply to held-out rows. Penalize all non-intercept terms; do not penalize the
  intercept (center y instead).
- Select λ (and α/l1) minimizing inner grouped RMSE (declared tie-break; usually
  first/smallest on ties). Refit on full training fold, predict held-out group.
- Pooled OOF metrics over all held-out predictions: RMSE, MAE,
  R²/Q² = 1 − SS_res/SS_tot (SS_tot about the global mean of y).
- Emit per-fold: held-out group, n, aligned inner-grid RMSEs, selected
  hyperparameters, (nonzero count / coordinate cycles for elastic net), outer RMSE.

## 3. Restricted-null wild cluster bootstrap-t
- Source model = the declared OLS. Observed statistic = focal coef / CR1 cluster-
  robust SE (CR1: c = (G/(G−1))·((n−1)/(n−k)); meat = Σ_g (X_gᵀû_g)(X_gᵀû_g)ᵀ).
- Impose the null (refit with focal coef = 0) to get restricted residuals, then
  resample cluster weights and recompute the t each replicate.
- **PRNG is specified exactly** — usually XORSHIFT32 or PCG32 with a declared seed
  (and stream). Reproduce the generator bit-for-bit, draw in the declared order,
  and report the requested checkpoints (PRNG state + t at replicate indices) and
  the terminal PRNG state. Weight family is named (e.g. Webb 6-point, Rademacher).
- p-value is usually the "plus-one" tail fraction (#|t*|≥|t_obs| + 1)/(R+1);
  emit exceedance count and requested bootstrap-t quantiles.

## 4. Grouped split-conformal calibration
- Split by group (division / state) or cross-fold. On each calibration set take
  nonconformity scores (|residual| from the declared predictor — often the ridge/
  elastic-net OOF predictions), threshold at the finite-sample rank
  ⌈(n_cal+1)(1−α)⌉ (nearest-rank quantile), form intervals on the held-out part.
- Emit per-group calibration/test counts, threshold/radius, coverage, mean width;
  pooled coverage and (weighted) mean width, worst group. Also RUCC-band and
  prediction-decile coverage/calibration when requested.

## 5. Trajectory PCA + deterministic k-means + leave-one-out ARI stability
- Build one row per unit (state/county) whose columns are the declared per-year
  feature blocks (e.g. `<measure>_<year>` in the declared order).
- **Covariance PCA** (center columns; eigit the covariance matrix) unless the
  request says correlation. Fix each component's sign by the declared rule (often
  largest-|loading| positive). Scores = centered data · loadings.
- Deterministic k-means (Lloyd) on the retained components with the *declared*
  initialization (registered/deterministic — e.g. specific seed states); report
  initial centroids, update/iteration count, final centroids, sizes, labels.
- Stability: redo the pipeline dropping each year's block; align clusters and
  report the adjusted Rand index vs the full clustering, plus min/median ARI.
  (ARI is invariant to label permutation; alignment matters for reported
  "assignment changes".)

## 6. Exhaustive source / feature-group perturbation (+ Shapley)
- Enumerate the declared scenario set: year-subsets of declared sizes, or
  direct-vs-rollup source swaps per eligible unit (2^M bitmask), or leave-one-
  feature-group-out. Refit the model per scenario; record focal coef and p.
- Stability = sign preserved / |percent shift| within the declared bound.
- Exact Shapley over the M swap "players": average marginal coefficient change
  over all orderings (use the 2^M coalition values). Emit per-replacement-count
  strata, worst scenario (max |shift|), Shapley vector and its sum.

## Decision block
For each gate, evaluate the declared threshold expression on your computed
statistics to a boolean, count passes, and apply the classification ladder /
precedence literally (e.g. all gates → strongest label; ≥k → intermediate;
else → null label / `NOT_ROBUST_AT_<first failed module in precedence>`).
