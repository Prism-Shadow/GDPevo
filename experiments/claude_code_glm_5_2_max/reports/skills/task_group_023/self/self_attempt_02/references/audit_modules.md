# Audit Module Families

Requests declare a set of audit modules (commonly six). The exact module set, method names, and parameters are read from each task's `analysis_request.json`; this file describes the **recurring families** and the evidence each must produce, plus the algorithmic specifics that make results reproducible. Nothing here is a task-specific final value — all seeds, grids, thresholds, and counts come from the request.

## Cross-cutting module rules

- **Positional alignment.** Whenever a module emits a vector aligned to an order the request declares (state/county order, coefficient order, feature order, division order, lambda/alpha grid, checkpoint replicate list, source-group order, cluster order), the array positions must correspond one-to-one to that order. Never re-sort an aligned array.
- **Full ordered evidence.** Report complete vectors/matrices (e.g. the full delete-one-cluster coefficient vector, the entire inner-RMSE grid, every checkpoint), not just summaries.
- **Cohort fidelity.** Each module runs on the cohort the request assigns it. Do not swap cohorts between modules.
- **Determinism.** Anything random uses the request's declared PRNG, seed, stream, replicate count, and checkpoint list, exactly. Inference (SE, t, p) follows the declared estimator (OLS/HC3, cluster-robust CR1, jackknife, bootstrap, GMM two-step).
- **Reference categories and indicators.** Categorical terms (RUCC bands, region/division indicators, period/end-year dummies) enter as indicators with one reference category omitted; indicators are not penalized/standardized where the request says so.
- **Training-only standardization.** When a predictive module declares training-only standardization, fit the scaler on the training fold only and apply it to the held-out fold — never standardize on the full dataset or the test fold.

## Family 1 — Delete-one-cluster fixed effects / jackknife / GMM

**Shape.** A panel/panel-change regression (two-way fixed-effects OLS, difference/dynamic GMM, or mediation GMM) fit on the declared cohort, with delete-one-cluster (state or census division) influence diagnostics.

**Params read from request.** Outcome, ordered predictors, cluster unit, cohort, change end-years/panel-end-years, instrument order (for GMM), coefficient order, pseudoinverse cutoff (for GMM).

**Must produce.** Full-sample dimensions and coefficient(s); the complete delete-one-cluster coefficient vector aligned to cluster order; jackknife SE, t-statistic, and p-value; bias-corrected coefficient; min/max (or most-influential) deletion and its coefficient/percent-change. For GMM: full two-step coefficients, Hansen J, delete-state coefficient + Hansen-J vectors, bias-corrected coefficients, and maximum absolute delete-state shifts. For mediation: path coefficients, first-stage partial F, stacked indirect effect with cross-equation-corrected SE and CI.

**Specifics.** Bias correction subtracts the delete-one jackknife bias. Cluster-robust SE uses CR1. GMM uses two-step linear GMM with the declared instrument set and a relative-pseudoinverse cutoff for the weighting matrix.

## Family 2 — Nested ridge / elastic-net cross-validation

**Shape.** Leave-one-group-out (census division or state) outer CV; within each outer fold, an inner CV over a declared grid selects the hyperparameter(s). Ridge or elastic-net (alpha + l1_ratio) penalty, training-only standardization.

**Params read from request.** Cohort, target, feature map (base + augmented terms, including polynomial/interaction terms), lambda grid (and alpha grid / l1_ratio grid for elastic-net), outer/inner grouping, fold counts.

**Must produce.** Cohort and fold counts; the candidate grid; every outer fold's held-out group, row count, aligned inner-grid RMSE, selected hyperparameter(s), standardized coefficients (where requested), and outer RMSE; pooled RMSE/MAE/R² (or Q²); worst outer fold/division; for augmented designs, the augmented-vs-base win count.

**Specifics.** Penalize all non-intercept terms unless told otherwise. Standardize continuous terms on training data only; leave indicator terms unstandardized. Selected hyperparameter = inner-grid argmin of grouped inner RMSE. Pooled OOF metrics aggregate held-out predictions across all outer folds. Coordinate-cycle / Lloyd-update counts, where requested, are reported as integers.

## Family 3 — Wild cluster bootstrap-t

**Shape.** A wild cluster bootstrap of the t-statistic for a target coefficient, clustering on the declared unit (state or division), often under the **restricted null** (the null is imposed when resampling). A declared integer PRNG (e.g. PCG32 or XORSHIFT32) with a seed (and stream, where declared) drives the replicate weights.

**Params read from request.** Target coefficient, cluster unit, seed, stream (if any), PRNG algorithm, replicate count, checkpoint replicate list, quantile probabilities.

**Must produce.** Method + randomization metadata (PRNG, seed, replicate count); observed coefficient, CR1 SE, and t-statistic; exceedance/tail count and **plus-one p-value** = `(exceedance_count + 1) / (replicate_count + 1)`; bootstrap-t quantiles at the requested probabilities; the declared checkpoint rows (replicate, PRNG state, and the t-statistic at that replicate); the first-three weight-index rows where requested; the terminal PRNG state.

**Specifics.** Restricted null means refitting under H0 before resampling so the resampled distribution is centered at the null. The plus-one p-value avoids zero p-values. PRNG state at each checkpoint must match the declared generator advanced to that replicate. Honor the exact seed and stream; do not reseed per replicate.

## Family 4 — Grouped split conformal

**Shape.** Split conformal prediction with grouping by the declared unit (division or state) and a fixed penalty (fixed lambda / fixed source model). Calibration set determines a conformity threshold; test points are covered if their absolute residual falls within the threshold.

**Params read from request.** Cohort, source predictions (often a nested-CV outer-fold OOF prediction), fixed lambda, nominal coverage, partition/fold count, group definition (and RUCC bands / prediction deciles where requested).

**Must produce.** Per-fold/per-group calibration and test counts, conformity threshold (finite-sample rank / nearest-rank quantile), interval radius/width, coverage fraction, mean interval width, and worst test group; per-state/per-band coverage and width where requested; aggregate (pooled) coverage and mean width; worst-coverage group/division.

**Specifics.** Threshold = the finite-sample quantile of calibration absolute residuals at `ceil((n_cal + 1) * nominal_coverage) / n_cal` (nearest-rank). Coverage = fraction of test points whose absolute residual ≤ threshold; width = 2 × threshold (or the declared interval-radius convention). Aggregate coverage pools covered/total across folds.

## Family 5 — Trajectory PCA + clustering

**Shape.** Covariance PCA on year/feature-blocked trajectory features (e.g. a measure's values across analysis years, or change variables across panel end-years), followed by deterministic k-means / three-means clustering on the leading PC scores, with leave-year-out or delete-state stability via adjusted Rand index (ARI).

**Params read from request.** Cohort, trajectory feature order (year blocks and within-year variables), retained component count, cluster count (or candidate cluster-count grid), initialization (declared initial centroid geographies), stability deletion unit and omitted years.

**Must produce.** Feature order and cohort size; leading eigenvalues, explained-variance ratios, and cumulative ratio; signed PC loading vectors and per-geography PC scores; declared initialization (initial centroid states/counties); Lloyd/k-means update count; cluster centroids, sizes, and labels aligned to geography order; leave-year-out or delete-state ARI vector plus median and minimum ARI; aligned-agreement / aligned-assignment-changes counts where requested.

**Specifics.** Use covariance PCA (center, do not standardize, unless the request says standardized). Scores = centered data projected onto loadings. k-means is deterministic with the declared initial centroids (specific geographies as seeds) and a fixed iteration/assignment rule. **ARI stability** compares each leave-one-out clustering to the full clustering; "aligned agreement" re-labels the leave-one-out clusters by the optimal permutation that maximizes agreement with the full labels, then counts assignment changes. For a candidate cluster-count grid, select the count by best average silhouette (or the declared criterion).

## Family 6 — Source / source-year perturbation

**Shape.** A sensitivity audit that perturbs the data source and refits the target coefficient. Three variants appear: (a) exhaustive source-year subsets (all year-subsets of the declared sizes), (b) direct-vs-rollup source replacement with **exact Shapley** attribution over the disagreeing geographies, (c) source-group term deletion (no-retune) over declared term groups.

**Params read from request.** Cohort, target coefficient, primary vs parallel/replacement source specs, year-subset sizes (variant a) or ordered replacement geographies (variant b) or ordered source groups with their terms (variant c), stability threshold.

**Must produce.** Strict-cohort audit (eligible count, excluded codes); the ordered subset/group/replacement list; both coefficient and p-value vectors aligned to that order; percent-shift vector; same-sign subset count and fraction; median and maximum absolute percent shift; worst subset/group. For variant (b): scenario count (2^M over M eligible replacements), by-replacement-count strata (0..M), stable-scenario count, maximum-shift bitmask and replaced codes, and the full exact Shapley effect vector (one per replacement) whose sum equals all-replaced minus all-direct.

**Specifics.** Same-sign = coefficient retains the full-sample sign across the subset. Percent shift = `|coef_subset − coef_full| / |coef_full| × 100`. Exact Shapley averages each replacement's marginal contribution over all inclusion orderings; the effects sum exactly to the difference between all-replacements-applied and the baseline. Variant (c) reuses the full model's selected hyperparameters (no retune) and reports per-group outer-fold RMSE, pooled RMSE, deterioration vs the full-model OOF reference, worse-fold count, and rank.

## Gate evaluation and decision

Each module has a declared gate — a threshold on one of its outputs (e.g. a jackknife/plus-one p-value ceiling, a pooled Q²/R² floor, an aggregate-coverage floor, a minimum-ARI floor, a same-sign-fraction floor, or a maximum-percent-shift ceiling — each read from the request's `robustness_gates`/`decision_rule` block). Evaluate each gate to a PASS/FAIL (or boolean). Then apply the request's **decision precedence**:

- Typically: all gates pass → strongest tier; a declared partial count (e.g. ≥ 4 of 6, or "four or five") → middle tier; otherwise → weakest tier.
- For "first failed module" styles: report the first failing gate in the declared precedence order (`NONE` if all pass) and the matching `NOT_ROBUST_AT_<MODULE>` conclusion.
- Emit **only** the controlled enum values the template declares for classification/conclusion. Do not invent tiers.
