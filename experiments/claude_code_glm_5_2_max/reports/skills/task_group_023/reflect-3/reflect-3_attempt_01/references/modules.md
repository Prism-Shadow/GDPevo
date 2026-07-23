# Audit-module archetypes & exact conventions

Each task composes 3–6 of these modules. The spec names the method, cohort, ordered features, grids, seeds/streams/replicates, and checkpoint lists. Reproduce them literally. Below are the conventions a reference implementation uses; deviation silently breaks checkpoint fields.

## Shared numerics

- **Two-way FE OLS** (`STANDARD_TWO_WAY_FIXED_EFFECTS_OLS`, `*_FE`): design = [predictors, intercept, (n−1) entity dummies, (t−1) time dummies] (full rank). Solve by least squares. A predictor's partial coefficient is invariant to other predictors' scaling (FWL). For unbalanced panels follow the cohort's balanced subset. For one-way FE omit the time dummies.
- **Reliability-weighted cross-sectional regression** (`RELIABILITY_WEIGHTED_LINEAR_REGRESSION_WITH_HC3_INFERENCE`): a reference-year cross-section (not a panel), weighted least squares with the declared reliability weight (e.g. the focal outcome's direct-record `sample_size`), **region** fixed effects (region dummies, not state FE), and **HC3** heteroskedasticity-robust inference (`V = (X'WX)⁻¹ X'W diag(e²/(1−h_ii)²) WX (X'WX)⁻¹`, where `h_ii` are the leverages of the weighted design). The `primary_design_order` lists terms literally (intercept, exposure, mediator/adjustments, `median_income_per_10000`, region dummies) — include them in that order.
- **CR1 cluster-robust SE** (cluster = state/county/division): `V = (X'X)⁻¹ (Σ_g X_g' e_g e_g' X_g) (X'X)⁻¹ · G/(G−1) · (n−1)/(n−k)`; `t = β/se`; two-sided p with df = G−1. Use `pinv` (with a singular-value cutoff when the spec declares a `relative_pseudoinverse_cutoff`).
- **Ridge** (training-only standardization): `β = (X_s'X_s + λI)⁻¹ X_s'y` where `X_s = (X−μ_train)/σ_train` (σ=1 if 0); penalty excludes intercept; predict with the same μ,σ. No outcome standardization unless declared.
- **Elastic net** (coordinate descent): minimizes `(1/2n)||y−Xβ||² + λ[ (1−l1_ratio)/2 ||β||² + l1_ratio ||β||₁ ]` over the declared `alpha_grid` (here `alpha`=λ) and `l1_ratio_grid`; standardize the declared `continuous_terms_to_standardize`; do not penalize `indicator_terms`/intercept; penalize only `penalized_terms`. Select by inner CV.
- **PCA sign convention:** eigendecompose the covariance (same-unit trajectories) or correlation (mixed-unit cross-sections) matrix; sort eigenvalues descending; for each PC flip sign so the **largest-|loading|** entry is positive (deterministic). Scores = centered (and standardized, if correlation) data × loadings.
- **Deterministic k-means:** fixed initialization (declared seed or explicit `initial_centroid_states`/extreme-PC1 picks); iterate assignment+update to convergence; report iterations. For leave-unit/year-out stability: recompute PCA+clustering with the unit/year removed, then **ARI** vs the full clustering, and best-permutation aligned agreement.

## Module 1 — Cluster jackknife / delete-cluster fixed effects

Fit the primary model (two-way FE panel OR reliability-weighted cross-section — whichever the spec declares) of outcome on ordered predictors over the declared cohort. Report: full focal-exposure coefficient; delete-one-cluster (state/county/division) coefficient vector aligned to the cluster order; delete mean; jackknife SE = `√((n−1)/n · Σ(θ_i − θ̄)²)`; jackknife t = bias-corrected/SE where bias-corrected = `n·θ_full − (n−1)·θ̄`; two-sided p (df n−1); min/max delete cluster & coefficient; most-influential cluster (max |delete − full|/|full|). Gate: focal coefficient has the expected sign **and** jackknife p ≤ threshold (reliability-weighted variants may instead report the HC3 inference alongside).

## Module 2 — Nested ridge / elastic-net division- or state-grouped CV

Outer loop leaves one group (census division / state) out as test. Inner loop leaves one group out over the training set to select λ/alpha (inner RMSE grid = outer_folds × grid). Then evaluate outer test RMSE at the selected hyperparameter. Report outer train/test sizes, selected hyperparameters per fold, inner RMSE grid, outer RMSE, pooled RMSE/MAE/Q² (`Q² = 1 − SSE/SST` over pooled test residuals), worst outer group. For augmented-vs-base feature maps, report pooled base/augmented RMSE and augmented-win count. Gate typically on pooled Q² ≥ k and pooled RMSE ≤ k.

## Module 3 — Wild cluster bootstrap t

Fit the model; obtain focal coefficient, CR1 SE, observed t. Fit the **restricted** model (focal coefficient = 0) for residuals `e0` and fitted `ŷ0`. For each replicate: draw one Rademacher/Webb weight per cluster from the declared RNG, form `y* = ŷ0 + e0 · w_{g(i)}`, refit the full model, compute bootstrap coefficient and CR1 SE and `t* = β*/se*`. p = `(#{|t*| ≥ |t_obs|} + 1)/(B + 1)`. Report first-three weight-index rows (aligned to cluster order), batch exceedance counts (partition B into the declared number of batches), exceedance_n, coefficient mean/sd, t-quantiles at the declared probabilities, and any `checkpoint_replicates` (PRNG state + t-statistics at those replicate counts).

**RNGs (implement exactly):**
- **PCG32 (pcg_setseq 64):** `inc = (stream << 1) | 1`; `state = 0`; step; `state += seed`; step. `step`: `state = (state*6364136223846793005 + inc) mod 2⁶⁴`. `next_u32`: `xorshifted = ((old>>18)^old)>>27` (32-bit); `rot = old>>59`; `out = (xorshifted>>rot) | (xorshifted<<((-rot)&31))`. Draw a uniform as `next_u32()/2³²`.
- **xorshift32:** `state ^= state<<13; state ^= state>>17; state ^= state<<5` (all mod 2³²); seed from the spec.
- **Webb 6-point weights** (radix-2): `{−1, −√(2/3), −√(1/6), +√(1/6), +√(2/3), +1}`; pick index = `next_u32() mod 6` (or uniform·6 floored — match the spec's wording). Rademacher (2-point) = {−1,+1} when declared.
- "RESTRICTED_NULL_PAIRED" bootstraps draw a single weight per cluster shared across the paired equations; "PCG32_WEBB" / "XORSHIFT32" name the RNG.

## Module 4 — Grouped split conformal

For each test group (division/state fold): hold it out as test; from the rest, designate a calibration group (declared rule, e.g. cyclic next group) and train on the remainder. Fit ridge/elastic-net at the declared fixed λ. Conformity scores = |y_cal − ŷ_cal|; `threshold = ⌈(n_cal+1)(1−α)⌉`-th order statistic. Interval = ŷ_test ± threshold; fold coverage = fraction of test points inside; fold width = 2·threshold; fold test MAE. Aggregate coverage/width pooled across folds. Some variants partition into N calibration cycles and report per-state coverage/width and a state-threshold count. Gate: aggregate coverage ≥ k and aggregate mean width ≤ k.

## Module 5 — Trajectory PCA + deterministic k-means + stability

Build the trajectory feature matrix (e.g. outcome+exposure at each year, in declared order) over the balanced cohort. Covariance PCA (same units). Report first-two eigenvalues, explained ratios, cumulative ratio; PC1/PC2 loadings and per-unit scores; initial centroid states; centroids (in PC1–PC2 space); cluster sizes; labels aligned to `state_order`. Leave-year-out (or leave-unit-out) stability: drop that year's/unit's features, recompute PCA+clustering, report ARI and aligned agreement. Gate: min ARI ≥ k and first-two cumulative explained ≥ k. Country-burden variant: correlation PCA on the (imputed, complete) burden matrix; silhouette over k∈{2,3,4,5}, select argmax; k=requested_k labels LOW/MIDDLE/HIGH burden by PC1 centroid; report high-burden membership.

## Module 6 — Source/year (or source-group) perturbation

Exhaustive subsets of years (sizes per `year_subset_sizes`, e.g. C(5,3)+C(5,4)+C(5,5)=16) or ordered source groups. For each subset, fit two-way FE OLS with the focal exposure **twice** — once on the primary series, once on the parallel/alternate series — with the declared adjustments; collect coefficients and CR1 p-values (clustered). Compute absolute percent shift = `|β_primary − β_parallel|/|β_primary|·100` per subset. Report both coefficient and p-value vectors, the shift vector, same-sign subset count/fraction, median/maximum shift, worst subset. Gate: same-sign fraction ≥ k and median shift ≤ k.

## Module 7 — Difference-GMM mediation (county/state panels)

State-clustered difference-GMM with cross-equation delta inference. Path A: mediator ~ exposure (+ controls, instrumented by lagged exposure). Path B: outcome ~ exposure + mediator (+ controls, mediator instrumented by lagged mediator). Direct: outcome ~ exposure + mediator. First-stage partial F for each endogenous regressor. Stacked indirect effect = path_a × path_b with cross-equation delta-method SE (includes the a·b covariance). Leave-one-state-out diagnostics (omitted state ascending). Gate: stacked indirect 95% CI excludes zero.

## Module 8 — Partial-R² mediation sensitivity surface

Baseline quantities: path-a coefficient, path-b coefficient, path-b SE, direct-model residual df. For a grid of R²(mediator←confounder) × R²(outcome←confounder) and both bias directions, compute the adjusted path-b, adjusted indirect, adjusted direct, and proportion mediated. Equal-strength tipping R² = the value where the indirect-effect sign flips / CI crosses zero. Gate: every POSITIVE row with both R² ≤ small threshold preserves the nonzero baseline indirect sign.

## Decision / conclusion

Summarize each module's gate as PASS/FAIL (or boolean), count passes, and classify per the declared precedence (all-pass ⇒ primary/consistent; ≥k ⇒ partial/associated/fragile; else none). Use only the template's enum values. Country variant: `advisory` enum based on the panel-model p-value and sign (prioritize high-burden cluster if the region-adjusted life-expectancy ~ PC1 coefficient is significantly adverse).
