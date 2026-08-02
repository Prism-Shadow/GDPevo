# Numerical method library

Reusable primitives for the audit modules. Every capitalized "knob" is bound from the
effective request's method text — take the stated variant; do not default silently.
Compute everything **unrounded**; round only when writing an output field.

Naming: `X` design matrix in declared column order; `y` outcome; `b` coefficients; `n`
rows; `k` columns; `G` clusters; `w` weights. Two-sided Student-t p-values use the stated
degrees of freedom.

---

## A. Linear algebra & inference

**OLS.** Solve `b = (X'X)^-1 X'y` in declared column order. Include or omit the intercept
exactly as the design order states (fixed-effects designs are fit *without* an intercept
after demeaning; WLS/HC3 designs usually include an explicit `intercept` term).

**Two-way fixed effects (double demeaning).** On every (re)fit, transform each modeled
variable to `z_it - mean_i(z) - mean_t(z) + mean(z)` (entity mean, time mean, grand mean
over the active rows), then OLS **without intercept** in declared predictor order. A
cluster deletion removes the whole cluster, **recomputes all means**, and refits from
scratch in entity-code order.

**WLS.** For positive weights `w`, set `Xw = diag(sqrt(w))·X`, `yw = diag(sqrt(w))·y`,
solve `b = (Xw'Xw)^-1 Xw'yw`. Keep the same fixed weight vector across every refit
(including source-perturbation fits) unless the request says otherwise (typically the
selected outcome record's `sample_size` as a fixed reliability weight).

**HC3.** With `h_i = diag(Xw (Xw'Xw)^-1 Xw')` and `ew_i = sqrt(w_i)(y_i - X_i b)`,
`V_HC3 = (Xw'Xw)^-1 Xw' diag(ew_i^2/(1-h_i)^2) Xw (Xw'Xw)^-1`. Inference: two-sided
Student-t with `n-k` residual df.

**CR1 cluster-robust.** Order clusters as declared; `s_g = Xw_g' ew_g`;
`V_CR1 = [G/(G-1)]·[(n-1)/(n-k)]·(Xw'Xw)^-1 (Σ_g s_g s_g') (Xw'Xw)^-1`. Inference:
two-sided Student-t with `G-1` df. (For unweighted designs use `X`, `e` in place of
`Xw`, `ew`.)

**Delete-one-cluster jackknife.** Fit full `b`; delete each registered cluster in order and
refit the unchanged design from scratch, giving `b_-g`. With mean `bbar`:
`SE_JK = sqrt((G-1)/G · Σ_g (b_-g - bbar)^2)` and bias-corrected
`b_BC = G·b - (G-1)·bbar`. The **test statistic numerator is a knob**: some protocols test
`b/SE_JK`, others `b_BC/SE_JK` — two-sided Student-t, `G-1` df. Percent change for a
deletion is `100·|(b_-g - b)/b|`; select extrema by the unrounded value, ties broken by
earlier cluster/entity order.

---

## B. Penalized regression with nested CV (ridge / elastic-net)

**Features.** Build raw, transformed (e.g. log income), squared, interaction, and indicator
columns in the declared feature order. Preserve that order everywhere (inner grids, selected
coefficient vectors, etc.).

**Fold assignment.** Two schemes appear:
- *Leave-group-out*: each registered group (state / census division) is one outer fold;
  within an outer-training set each remaining group is one inner fold, in the same order.
- *Balanced state-blocked k folds*: allocate states by **descending retained-entity count**,
  each to the currently smallest fold (lower fold id on ties); sort state codes within
  folds; repeat the allocation inside each outer-training set for inner folds.

**Training-only standardization.** Inside every fit compute feature center `mu_j` and scale
`sigma_j` from the **training rows only** and apply them to validation/test rows. Knobs:
population SD (`ddof 0`, divide by `n`) vs sample SD (`ddof 1`); **weighted** moments
(`mu_j = Σ w_i x_ij/Σ w_i`, `sigma_j = sqrt(Σ w_i (x_ij-mu_j)^2/Σ w_i)`) vs unweighted; unit
divisor when variance is zero. Indicators are typically left unscaled. Center `y` by its
training (weighted) mean without scaling `y`; keep the intercept unpenalized.

**Ridge.** Minimize (weighted) training SSE `+ lambda·||b_nonintercept||^2`. Closed form or
coordinate updates are both fine if they match the objective; a coordinate sweep uses
`b_j = Σ_i x_ij r_ij/(Σ_i x_ij^2 + n·lambda)` with `r` excluding feature j.

**Elastic-net (coordinate descent).** Objective (weighted form):
`Σ_i w_i (y_i - Z_i b)^2/(2 Σ_i w_i) + lambda·[alpha·Σ_j|b_j| + (1-alpha)·Σ_j b_j^2/2]`
(some requests parameterize as `alpha·(rho·Σ|b| + 0.5(1-rho)Σb^2)` — bind the exact
parameterization). **Cold-start** `b=0` for every (penalty, fold); never warm-start.
Intercept starts at the training (weighted) outcome mean. In cyclic declared feature order:
`rho_j = Σ_i w_i Z_ij (y_i - Σ_{l≠j} Z_il b_l)/Σ_i w_i` (or the unweighted mean form),
`b_j = S(rho_j, lambda·alpha)/(1 + lambda·(1-alpha))` with soft-threshold
`S(a,t)=sign(a)·max(|a|-t,0)`. Update the intercept by the mean residual each sweep when the
recipe says so. Stop after a complete sweep when the max coefficient change is below the
effective tolerance, or at the sweep cap.

**Selection & aggregation.** For each penalty, **pool inner validation squared errors across
rows** then take RMSE (not a mean of fold RMSEs); choose smallest unrounded RMSE, ties toward
the smaller penalty (then smaller alpha, then smaller l1-ratio if a grid). Refit on all
outer-training rows and predict the outer holdout. Count nonzero coefficients with the
declared numerical cutoff. Pool exactly one outer (OOF) prediction per eligible row in entity
order; report RMSE, MAE, and `R2 = 1 - SSE / Σ_i (y_i - ȳ_full)^2` (weighted or unweighted
per the recipe; `ȳ_full` is the full-sample mean). "Q-squared" is this pooled OOF R².

---

## C. Wild cluster bootstrap-t (restricted null)

1. **Observed.** Studentize the full target coefficient with the registered cluster CR1
   (WLS/CR1 if weighted). Then fit the **restricted** model (target removed) and retain its
   fitted values and residuals in entity order. Reuse the same demeaned/weighted matrix as
   the base model.
2. **Draw & refit.** Using the pinned PRNG (`references/prng.md`), one continuous stream,
   draw one weight per cluster in declared order per replicate. Set
   `y* = restricted_fit + restricted_residual · cluster_weight`; refit the unrestricted
   model; recompute CR1 and the studentized target `t*`. (For paired-equation designs, reuse
   the same cluster sign across equations.)
3. **Test.** Two-sided absolute exceedance: `count = #{|t*| ≥ |t_obs| - delta}` (comparison
   tolerance `delta` defaults to 0 unless stated); report **plus-one** p-value
   `(1 + count) / (1 + B)`. Aggregate consecutive replicate **batches** exactly as bound.
4. **Quantiles (knob).** *Nearest-rank*: for sorted `x` and probability `p`,
   `x[min(B, ceil(p·B)) - 1]` (one-based rank). *Type-seven*: `h=(B-1)p`, `j=floor(h)`,
   `gamma=h-j`, `(1-gamma)x[j] + gamma·x[j+1]` (zero-based). Bootstrap-t interval inversion
   uses the observed standard error.
5. **Checkpoints.** Record each requested checkpoint/`final_prng_state` **after** its
   replicate's draws complete, using the current PRNG state and that replicate's statistics —
   never reset the stream.

---

## D. Split / grouped conformal

1. **Partition.** Either cyclic partitions (`index mod partition_count`) or leave-one-group
   -out. For each test partition/group, pick the calibration partition as declared (a
   registered preceding partition, or the remaining group with the greatest row count then
   ascending name), and use the rest for proper training. Or, when reusing OOF predictions,
   calibrate a held-out fold on absolute OOF residuals from all other folds.
2. **Scores.** Absolute residuals. Some protocols **reduce to one max absolute residual per
   calibration entity** before ranking; others use raw calibration rows — bind which.
3. **Rank/radius.** For `m` sorted scores and nominal coverage `c` (`= 1-alpha`), one-based
   `r = min(m, ceil((m+1)·c))`, radius `q = score[r]`. Intervals `prediction ± q` are
   **inclusive**.
4. **Aggregate.** Report per-fold/group coverage, mean interval width, and MAE; pool covered
   and row counts for aggregate coverage; weight mean width by held-out row count. Worst
   group = smallest coverage fraction, ties by earlier declared order. Report state / RUCC-
   band / prediction-decile diagnostics when the template asks (assign prediction bins after
   sorting by prediction then declared identifiers; signed gap = prediction mean − observation
   mean). Use unrounded group coverages for minima and decision predicates.

---

## E. Trajectory PCA + deterministic k-means + ARI

**PCA.** Build feature blocks in the declared variable-major / time order and entity ASCII
order. Standardize each column by its active-sample SD (population vs sample is a knob), then
form covariance `C = Z'Z / D` where the divisor `D` is `n` or `n-1` per the recipe.
Eigendecompose (symmetric Jacobi: rotate on the largest absolute upper-triangle off-diagonal,
ties by lower row then column; `tau=(Aqq-App)/(2Apq)`, `t=sign≥0(tau)/(|tau|+sqrt(1+tau^2))`,
`c=1/sqrt(1+t^2)`, `s=t·c`; stop at the off-diagonal tolerance or step cap). Order components
by descending eigenvalue then original diagonal index. **Orient** each eigenvector so its
earliest maximum-absolute loading is positive. Scores `= Z · oriented_loadings`. Explained
ratios divide each eigenvalue by the sum of all eigenvalues.

**Deterministic k-means (farthest-first / Lloyd).** On the declared leading scores, squared
Euclidean. First center = the ASCII-first entity; each next center = the entity maximizing
distance to its nearest current center, ties by entity code. Assign to nearest center, ties
to the lower working id; update centers by member means; stop when assignments are unchanged
(plus any center tolerance) or at the iteration cap. **Empty cluster**: move the ASCII-first
entity among those farthest from its assigned center, recompute, continue. Canonicalize final
cluster ids by centroid coordinates then working id.

**Choosing k (when a candidate list is given).** Compute Euclidean silhouette (singleton
silhouette = 0); select the largest unrounded mean silhouette, ties toward smaller k.

**Adjusted Rand index.** From the contingency table,
`ARI = (Σ_ij C(n_ij,2) - E) / (0.5(Σ_i C(a_i,2) + Σ_j C(b_j,2)) - E)`,
`E = Σ_i C(a_i,2)·Σ_j C(b_j,2) / C(n,2)`.

**Leave-block-out stability.** For each omitted time block (ascending), delete that whole
variable/time block and rebuild scaling → PCA → orientation → initialization → clustering
from scratch; compute ARI vs the full assignment. Align refit labels to the full labels by
the permutation with maximum agreement, ties to the lexicographically smallest mapped-id
vector; report aligned agreement / changes as the template asks.

---

## F. GMM

**Difference-GMM mediation.** Build adjacent-change rows in entity then end-period order with
the declared lag/instrument structure. Per equation: `W=(Z'Z)^-1`,
`beta = (X'ZWZ'X)^-1 X'ZWZ'y`. With residual `u` and cluster score `q_g = Z_g' u_g`, use the
registered finite-sample cluster sandwich; for two equations use the cross-cluster score
product for `Cov(a,b)`. Indirect `theta = a·b`,
`Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b)`, Student-t with cluster df. First-stage
partial F from full-vs-reduced residual sums of squares and effective instrument counts.
Every delete-state diagnostic rebuilds rows and refits all affected equations from scratch in
state order.

**Two-step linear GMM (with Hansen J).** Residualize outcome/regressors/instruments against
intercept + declared baseline terms. First step: moments `g(theta)=Z'(y-Dθ)/n` with identity
weight. Cluster scores `s_g=Z_g' u_g`, `S=Σ_g s_g s_g'/n`; second-step weight is the
Moore-Penrose pseudoinverse of `S` with the registered **relative singular-value cutoff**
applied to every pseudoinverse. Second-step `theta` from the weighted linear moments;
`Hansen J = n·g(theta)' W g(theta)`. Refit both steps after each state deletion in state
order; bias-corrected `theta_bc = G·theta_full - (G-1)·mean(theta_delete)`; retain maximum
absolute delete-state shifts.

---

## G. Exact-Shapley source perturbation

Resolve the alternate (replacement) source with its own effective release filters and the
greatest-revision/latest-release/id precedence. Order paired entities by **descending
|alternate − primary| difference**, ties by entity code. For `m` disagreeing entities and
every bitmask `0 … 2^m - 1`, replace entity j iff `mask & (1<<j)`; keep the fixed weights and
design; refit (WLS + HC3). Relative shift `= 100·|(b_mask - b_0)/b_0|`. Per popcount stratum
report scenario count, coefficient range, HC3 p-value range, and mean shift. Max shift = the
greatest unrounded shift, ties by smaller mask. Exact Shapley for entity j:
`phi_j = Σ_{S ∌ j} |S|!(m-|S|-1)!/m! · [b(S∪{j}) - b(S)]`; preserve signed order and verify
`Σ_j phi_j = b(all replacements) - b(no replacements)` within tolerance.

Simpler **source-group deletion** variant (no retune): for each declared source group and
outer fold, remove exactly the group's terms and **reuse that fold's full-model selected
hyperparameters** (no retuning); rerun the same preprocessing/solver; retain outer-fold
RMSEs, pool squared errors, subtract full-model OOF RMSE for deterioration; count folds worse
than the corresponding full-model fold; rank groups by decreasing deterioration then declared
order.

---

## H. Partial-R² mediation sensitivity

From unrounded baseline path-a `a`, path-b `b`, `SE_b`, residual df, and total effect
`total`: `magnitude = SE_b · sqrt(df · rY · rM / (1 - rM))`. For each declared bias direction
`s ∈ {+1 (POSITIVE), -1 (NEGATIVE)}` (follow the declared direction order):
`adjusted_b = b - s·magnitude`, `adjusted_indirect = a·adjusted_b`,
`adjusted_direct = total - adjusted_indirect`, `proportion = adjusted_indirect/total`.
Enumerate the full surface in declared `(rM, rY, direction)` order and compute the
equal-strength positive tipping `R²` root from the unrounded inputs.

---

## I. Cross-section PCA / clustering / panel (country-briefing shape)

Reuse §E's PCA, k-means, silhouette-k, and ARI on the completed cross-section matrix. Report
retained component count, PC1 variance fraction, and top absolute loadings (descending
|loading|, ties by indicator id). For clustering, label segments by burden level
(LOW/MIDDLE/HIGH) per the template and return the high-burden membership sorted ascending.
**Panel model**: region fixed-effects OLS of the outcome (e.g. life expectancy) on PC1 across
the requested country-year panel; report coefficient, standard error, two-sided p-value, R²,
and the `region_fixed_effects` flag. Map the final advisory enum from the panel result per the
template's allowed values.

---

## Controlled decision

After completing every evidence module:

1. Evaluate each business predicate/gate on **unrounded** values, using the exact thresholds
   and comparison directions the request states (e.g. "coefficient is negative and jackknife
   p ≤ 0.05", "pooled Q² ≥ 0.85", "minimum ARI ≥ 0.55").
2. Preserve the declared module order for gate reporting; count satisfied predicates.
3. Apply **only** this request's controlled decision mapping and tie/precedence rules — e.g.
   "all six gates pass → PRIMARY…", "at least four → ASSOCIATED…", else the fallback; or a
   precedence list that names the **first failed module** ("NOT_ROBUST_AT_<module>"). Use the
   exact enum strings from the template's allowed values.
4. Emit per-gate PASS/FAIL (or Boolean), the passed/supported count, the first-failed module
   where required, and the final classification.
