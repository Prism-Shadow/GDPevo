# Module playbook

A PHO audit is a fixed roster of **6 audit modules** plus a **cohort/census** block and a
**gated decision**. The wording changes per task, but the modules are drawn from a small,
recurring family. For each module the `analysis_request.json` registers the method name,
cohort, ordered feature/coefficient list, grids, seeds, and required evidence; the
`answer_template.json` fixes the output keys, array lengths, ordering and precision.
**Read both, build the exact declared design matrix, and preserve every declared order.**

General rules that apply to every module:

- **Design order is law.** Build columns in the exact `*_order` the request lists
  (intercept first only if named). Category indicators use the named reference level
  (e.g. RUCC1 reference → `rucc_2..rucc_9`; region reference `Northeast`). Interaction and
  polynomial terms (`x^2`, `x*y`) are appended in the exact append order given.
- **Transforms** happen at design time: `median_income_per_10000`, `log(median_income)`
  of the *unscaled* value, `log(sample_size)`, first differences / lags for "change" and
  "lagged" panel terms, and `end_year_*` period indicators.
- **Standardization**, when a module says "training-only," is fit on the outer-train fold
  and applied to the held-out fold; never leak test statistics.
- **Inference conventions:** `HC3` = MacKinnon–White heteroskedastic-consistent SEs;
  `CR1` = cluster-robust SE with the finite-sample factor `G/(G-1)·(N-1)/(N-k)` over the
  named cluster unit. Weighted fits use the declared reliability weight (e.g. a
  `sample_size`) in every refit, including perturbations.
- **Precision:** compute unrounded, round only the reported statistic to the declared
  decimals (usually 4; sometimes 6 for computed reals with 4 for literal grids/thresholds).
  Emit JSON numbers; use JSON `null` only when a statistic is mathematically undefined.

---

## 1. Delete-one-cluster jackknife on a base regression

Base model is a two-way (entity+year) fixed-effects OLS, or a reliability-weighted linear
model, or a two-step linear GMM — as named. Fit on the named cohort; the target is one
coefficient (the focal exposure).

Steps: (a) full-sample coefficient; (b) for each cluster `g` (state or census division),
refit deleting `g`, record its coefficient and diagnostics *in the registered cluster
order*; (c) jackknife SE = sqrt((G-1)/G · Σ(θ₋g − mean)²); t = bias-corrected θ / SE;
two-sided p from the t (or normal) reference; (d) bias-corrected θ = G·θ_full −
(G-1)·mean(θ₋g); (e) influence = max |percent change| and the argmax cluster. The
delete-coefficient array must align positionally with the state/division order.

## 2. Nested grouped cross-validation of a penalized regressor

Ridge, or elastic-net (declared `alpha`, `lambda_grid`, and for EN a `l1_ratio` grid).
**Leave-group-out** outer folds (leave-one-division-out, leave-one-state-out, or K
state-blocked folds). For each outer fold: standardize on train only, run an **inner**
grouped CV over the grid, pick the hyperparameter minimising inner grouped RMSE (ties →
smaller/earlier grid value unless stated), refit on the full outer-train, predict the
held-out group. Report per-fold: held-out group, n, inner grid RMSE matrix (aligned to
the grid), selected hyperparameters, standardized coefficients, outer RMSE. Pool the
out-of-fold predictions to compute pooled RMSE / MAE / R² (or Q² = 1 − SSE/SST against the
outcome mean). Elastic-net uses coordinate descent; report `nonzero_feature_count` and
`coordinate_cycles` if asked. Reuse the *same selected hyperparameters* for downstream
conformal / source-deletion modules when the task says so.

## 3. Wild cluster bootstrap-t (restricted null)

Impose the null (drop the target term, refit to get restricted residuals), then for each
replicate draw one **cluster-level** weight per cluster and form the bootstrap t of the
target coefficient's cluster-robust (CR1) statistic. Conventions that must match exactly:

- **PRNG**: implement the *named* generator bit-exactly — `PCG32` (with the given `stream`)
  or `XORSHIFT32` — seeded with the given `seed`. Advance the stream in the registered
  order (typically cluster-major within each replicate). Report requested PRNG-state
  checkpoints and terminal state as integers.
- **Weights**: Webb 6-point or Rademacher ±1 as named ("Webb wild"); one weight per
  cluster per replicate, applied to restricted residuals.
- **Statistic**: bootstrap t = (θ*b) / CR1_se*b (restricted-null centering). Count
  exceedances |t*| ≥ |t_obs| (two-sided) or one-sided as declared.
- **p-value**: use the **plus-one** estimator (exceedances+1)/(replicates+1).
- Report requested bootstrap-t quantiles, first weight-index rows, and batch/checkpoint
  exceedance counts, all in registered order.

## 4. Grouped split conformal

Leave-group-out (or cross-fold) split conformal on a fixed model (fixed lambda, or the
ridge/EN OOF predictions). For each held-out group: fit/predict, compute calibration
absolute residuals on the complementary calibration fold, take the finite-sample
conformal quantile — rank `ceil((n_cal+1)·(1−alpha))` of sorted calibration scores — as
the interval radius/threshold, then measure held-out coverage and mean interval width.
Report per-group threshold, coverage, width, MAE, and the pooled aggregate coverage &
mean width (and worst group). `nominal_coverage = 1 − alpha`.

## 5. Trajectory PCA + deterministic k-means + leave-one-out ARI stability

Build one row per unit (state/county) whose columns are the **stacked trajectory features**
in the declared within-year × variable order (e.g. `var_2020..var_2024` blocks). Then:

- **PCA** on the *covariance* matrix (registered convention — mean-center, do **not**
  scale to unit variance unless told). Report eigenvalues, explained-variance ratios, and
  signed loadings; fix loading **sign** deterministically (e.g. force the largest-magnitude
  loading, or the sum of loadings, positive) so signs are reproducible.
- **k-means** on the retained PCs with a *deterministic* initialization (the request names
  it — e.g. specific initial centroid units, or a deterministic farthest-point / seeded
  rule). Run Lloyd iterations to convergence; report initialization, iteration/update
  count, centroids (PC space), sizes, and per-unit labels aligned to the unit order.
  Cluster ids/labels may need a canonical relabeling (by size, or by a burden ordering
  LOW/MIDDLE/HIGH) — follow the template.
- **Stability**: refit dropping one year (or one state) at a time, recompute clusters, and
  score agreement with the full clustering by **Adjusted Rand Index** (and any
  aligned-agreement count). Report every leave-one-out ARI and the min/median.
- **Model selection** (when asked): pick k by maximum average **silhouette** over the
  candidate k list.

## 6. Source / year perturbation (and exact Shapley)

Enumerate the declared perturbation set — e.g. all `2^k` source-swap subsets, or all
year-subsets of sizes {3,4,5} (→ 16 for years 2020–24), or leave-one-source-group-out.
Refit the model under each scenario (keeping the reliability weight fixed), record the
target coefficient and its p-value per scenario in registered order. Summaries:
**same-sign fraction**, **absolute percent shift** vs. the baseline (median / max), the
worst scenario, and per-stratum aggregates by replacement count. When **exact Shapley**
attribution is requested, average each element's marginal coefficient change over all
orderings (`Σ_{S⊆N\{i}} |S|!(n−|S|−1)!/n! · (v(S∪i)−v(S)))`); the Shapley effects sum to
`v(all) − v(none)` (all-rollup minus all-direct). Emit a `maximum_shift_bitmask` if asked.

---

## Other recurring pieces

- **Difference / two-step GMM mediation** (county tasks): stacked total / path-a / path-b /
  direct equations, state-clustered SEs, cross-equation delta (Sobel-type) inference for
  the indirect effect, lagged-level instruments, first-stage partial F, Hansen J
  overidentification, leave-one-state-out diagnostics.
- **Partial-R² mediation sensitivity surface**: from baseline path-a, path-b, its SE and
  residual dof, sweep `(R²_mediator, R²_outcome)` grids in each bias direction to adjust
  path-b, recompute indirect/direct/proportion, and find the equal-strength tipping R².
- **Silhouette candidate-k selection**: standard silhouette coefficient over candidate k.

Whenever a convention is under-specified by the prose, prefer the **most standard textbook
definition** and make it deterministic; the answer template's array lengths and ordering
rules are the ground truth for shape.
