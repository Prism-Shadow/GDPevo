# Methods reference — deterministic module specifications

These are the recurring, reusable algorithms across PHO audits. **All names,
orders, grids, seeds, tolerances, cutoffs, and cohorts are bound from the task's
`analysis_request.json`** — the specs here fix only the deterministic *how*.
When the request states a rule that differs from a default below, the request
wins. Compute everything unrounded; round only reported fields.

General conventions used below: `w` = reliability weights (all-ones when
unweighted); `k` = number of design columns; `n` = rows; `G` = number of
clusters. "entity-code order" / "ASCII order" means ascending string sort of the
entity identifier. Two-sided Student-t is used with the stated degrees of
freedom.

## Release resolution & cohorts

1. Pull each requested measure/field dataset; apply request filters
   (status, value_type, source_type, geography, year).
2. For each declared key `(entity, year, measure[, value_type, source_type])`
   keep one record: **max `revision` → latest `released_at` → record-id tiebreak
   the request names**. Drop records failing validity (suppressed, invalid/
   withdrawn quality flag, blank/null value).
3. Count selected publications **before** analytic-completeness exclusions when a
   release count is requested.
4. Join independently resolved series on stable entity+time keys. Build each
   named cohort from exactly its declared required fields + validity predicates:
   - *complete-case / primary*: all required fields present in the reference year.
   - *balanced*: entities complete in **every** requested year (intersection).
   - *broad / reference*: reference-year complete cases over all ordered features.
   - *dual-source / strict*: complete for outcome + primary + parallel series +
     adjustments in every year.
   - *machine-learning*: a base cohort further complete on the ML feature set.
   Preserve entity-code then time order; report sizes, per-year counts, and the
   complete excluded-entity set the template asks for.

## Linear algebra core

- **OLS (no intercept, double-demeaned FE):** for two-way fixed effects, transform
  each modeled variable `z_it → z_it − mean_entity − mean_time + grand_mean`, then
  solve OLS in declared predictor order. Deletions remove the whole cluster,
  recompute all means, and refit from scratch.
- **WLS with weights `w`:** `Xw = diag(sqrt(w))·X`, `yw = diag(sqrt(w))·y`, solve
  `b = (Xw'Xw)^-1 Xw'yw` in declared column order.
- **HC3:** with hat `h_i = diag(Xw (Xw'Xw)^-1 Xw')` and weighted residual
  `ew_i = sqrt(w_i)(y_i − X_i b)`,
  `V_HC3 = (Xw'Xw)^-1 Xw' diag(ew_i^2/(1−h_i)^2) Xw (Xw'Xw)^-1`; t uses `n−k` df.
- **CR1 cluster-robust:** for ordered clusters `g`, score `s_g = Xw_g' ew_g`,
  `V_CR1 = [G/(G−1)]·[(n−1)/(n−k)]·(Xw'Xw)^-1 (Σ_g s_g s_g') (Xw'Xw)^-1`;
  t uses `G−1` df.

## Delete-one-cluster jackknife

Fit full design, then delete each cluster in declared order and refit from
scratch. For target `b` and delete estimate `b_-g`: percent change
`= 100·|(b_-g − b)/b|` (pick the greatest unrounded, tie → earlier cluster).
With mean `bbar = mean_g b_-g`:
- bias-corrected `b_BC = G·b − (G−1)·bbar`,
- `SE_JK = sqrt((G−1)/G · Σ_g (b_-g − bbar)^2)`,
- test `b/SE_JK` (or `b_BC/SE_JK` when the request says so) with `G−1` df.
Select extrema by coefficient then entity code.

## Nested leave-group-out ridge / elastic-net CV

- **Folds:** outer = hold out one declared group per fold; inner = within each
  outer-training set hold out every remaining group once, same order.
- **Standardization (training-only):** subtract training feature means and divide
  by training SD; for ridge default SD uses `ddof=1`, for weighted elastic-net use
  weighted population SD `sqrt(Σ w_i(x_ij−mu_j)^2 / Σ w_i)`; unit divisor when
  variance is 0. Apply training moments to validation/test rows. Center `y` by its
  training (weighted) mean; do not scale `y`. Keep the intercept unpenalized.
- **Ridge objective / update:** minimize `mean((y−a−Xb)^2) + λ Σ b_j^2`; cyclic
  coordinate update `b_j = Σ_i x_ij r_ij / (Σ_i x_ij^2 + n·λ)` with `r` excluding
  feature `j`.
- **Elastic-net objective / update:** minimize
  `Σ w_i (y_i−Z_i b)^2 / (2 Σ w_i) + λ[α Σ|b_j| + (1−α) Σ b_j^2/2]`; coordinate
  update `ρ_j = Σ w_i Z_ij (y_i − Σ_{l≠j} Z_il b_l)/Σ w_i`,
  `b_j = S(ρ_j, λα)/(1 + λ(1−α))`, soft-threshold `S(a,t)=sign(a)·max(|a|−t,0)`.
- **Convergence:** cold-start `b=0` for every `λ`/fold (never warm-start); stop
  after a full sweep when max coefficient change < tolerance, or at the sweep cap.
- **Selection:** for each penalty pool **row-level** validation squared errors
  and take RMSE; choose smallest RMSE then smaller penalty; refit on all
  outer-training rows; predict the held-out fold.
- **Aggregation:** one OOF prediction per eligible row → pooled RMSE, MAE, and
  `R²/Q² = 1 − SSE / Σ(y − full-sample mean)^2` (weighted/unweighted per request).

## Wild cluster bootstrap-t (restricted null)

1. Studentize the full-model target coefficient with CR1. Fit the **restricted**
   model without the target; keep its fitted values and residuals in entity order.
2. Per replicate: draw one weight per cluster in entity-code order from one
   continuous PRNG stream; `y* = restricted_fit + restricted_resid · weight`;
   refit the unrestricted model; recompute CR1; studentize.
3. Reuse the same cluster draw across paired equations when the request pairs
   them. Record each checkpoint **after** its replicate completes, without
   resetting the stream.
4. p-value: count `|t*| ≥ |t_obs|` (or a one-sided/tolerance variant the request
   names) → **plus-one** `p = (1+count)/(1+B)`.
5. Quantiles: use the request's convention — either **nearest-rank** (sorted `x`,
   one-based rank `min(B, ceil(p·B))`) or **type-7** (`h=(B−1)p`, `j=floor(h)`,
   `γ=h−j`, `(1−γ)x[j]+γ x[j+1]`, zero-based).

### PRNGs (pick the one the request names)

**PCG32** (64-bit state, 32-bit output; unsigned wraparound mod 2^64):
- `increment = 2·stream + 1`; init `state=0`, advance once, add the seed/init
  value mod 2^64, advance once.
- Each advance: `old = state`; `state = old·6364136223846793005 + increment`;
  `xorshifted = low32( ((old>>18) xor old) >> 27 )`; `rot = old>>59`;
  `output = rotate_right_32(xorshifted, rot)`.
- Map `output mod 6` in order to the Webb six-point weights
  `[−sqrt(3/2), −1, −sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]` (or the mapping the
  request states, e.g. Rademacher ±1).

**xorshift32** (unsigned 32-bit state; mask to 32 bits after every step):
- next: `x ^= x<<13; x ^= x>>17; x ^= x<<5;` (truncate to 32 bits after each).
- Rademacher map: low bit 1 → `+1`, else `−1` (odd → +1, even → −1), unless the
  request maps differently.
- Seed from the request's random binding; report the terminal PRNG state if the
  template asks.

## Split / grouped / cross-fold conformal

- **Partitioning:** per the request — cyclic index-mod-k folds, or one held-out
  group per cycle with a declared/selected calibration group (e.g. greatest row
  count then ascending name; or the preceding fold), remaining groups train.
- **Fit:** ridge/elastic-net from scratch with the fixed penalty and identical
  training-only scaling/solver; or reuse the nested-CV OOF predictions when the
  request sources them.
- **Interval:** sort `m` absolute calibration residuals; one-based
  `r = min(m, ceil((m+1)·coverage))`; radius `q = score[r]`; interval is
  `prediction ± q`, **inclusive**. When calibration is reduced per group, take one
  max-abs residual per group first if the request says so.
- **Aggregate:** report per-fold/-group coverage, mean width, MAE; pool coverage
  and width by held-out row counts; pick worst group by smallest coverage then
  earlier declared order.

## Trajectory PCA + deterministic k-means + ARI stability

- **Matrix:** build columns in the declared variable-major / time order over the
  cohort in entity ASCII order; standardize each column by its active-sample SD.
- **PCA:** form `C = Z'Z/(n−1)` (or `/n` if the request specifies population).
  Symmetric **Jacobi**: rotate on the largest absolute off-diagonal (tie → lower
  row then column); `τ=(A_qq−A_pp)/(2A_pq)`, `t=sign⁺(τ)/(|τ|+sqrt(1+τ^2))`,
  `c=1/sqrt(1+t^2)`, `s=t·c`; stop at the off-diagonal tolerance or step cap.
  Order components by descending eigenvalue then original diagonal index; **orient**
  each loading so its earliest maximum-absolute entry is positive; `scores = Z·loadings`.
  Explained ratios divide by the sum of all eigenvalues.
- **k-means (farthest-first Lloyd, squared Euclidean):** first center = ASCII-first
  entity; each next center = entity maximizing distance to its nearest current
  center (tie → entity code). Assign to nearest center (tie → lower cluster id);
  update centers by member means; stop when labels are unchanged (and any center
  tolerance) or at the cap. Handle empty clusters by the request's rule (e.g. move
  the ASCII-first farthest point). Canonicalize final ids by centroid coordinates
  then working id if requested.
- **Cluster-count selection (when requested):** Euclidean **silhouette** (singleton
  = 0); pick largest mean silhouette then smaller k.
- **Adjusted Rand index:** from the contingency table,
  `ARI = (Σ_ij C(n_ij,2) − E) / (½(Σ_i C(a_i,2)+Σ_j C(b_j,2)) − E)`,
  `E = Σ_i C(a_i,2)·Σ_j C(b_j,2) / C(n,2)`. For stability, rebuild the whole
  pipeline (scaling, PCA orientation, init, clustering) leaving out each declared
  time block / entity; align refit labels by the permutation with maximum matches
  (tie → lexicographically smallest mapping) before reporting aligned changes.

## GMM (difference / two-step)

- **Difference GMM:** create adjacent-change rows in entity then end-period order
  with the declared lag/instrument structure. Per equation `W=(Z'Z)^-1`,
  `β=(X'ZWZ'X)^-1 X'ZWZ'y`; cluster sandwich with scores `q_g=Z_g'u_g`. First-stage
  partial F from full-vs-reduced residual sums of squares using the instrument
  counts. Delete-state diagnostics rebuild rows and refit affected equations from
  scratch in state order.
- **Two-step linear GMM:** residualize outcome/regressors/instruments against
  intercept + baseline terms. Step-1 moments `g(θ)=Z'(y−Dθ)/n` with identity
  weight; `S=Σ_g s_g s_g'/n`, step-2 weight `= Moore-Penrose pseudoinverse of S`
  with the declared relative singular-value cutoff; `Hansen J = n·g(θ)'W g(θ)`.
  Delete-state bias correction `θ_bc = G·θ_full − (G−1)·mean(θ_delete)`; keep max
  absolute delete-state shifts.

## Mediation delta method

For indirect `θ=a·b`: `Var(θ)=b²Var(a)+a²Var(b)+2ab·Cov(a,b)`; Student-t with the
cluster df. Stacked/cross-equation corrections use the cross-cluster score product
when two equations share clusters. Shift `= |b_alt − b|/|b|·100`; same-sign
requires both nonzero with identical sign; ordinary median over ordered shifts.

## Partial-R² mediation sensitivity surface

From unrounded baseline `a`, `b`, `SE_b`, residual df:
`magnitude = SE_b · sqrt(df · rY · rM / (1 − rM))`. For each declared direction
`s∈{+1(POSITIVE), −1(NEGATIVE)}`: `adjusted_b = b − s·magnitude`,
`adjusted_indirect = a·adjusted_b`, `adjusted_direct = total − adjusted_indirect`,
`proportion = adjusted_indirect/total`. Enumerate the full surface in declared
`r²` and direction order; solve the equal-strength positive tipping root from
unrounded inputs.

## Exact Shapley source attribution

Order paired entities by descending `|alternate − primary|` (tie → entity code).
For mask `0..2^m−1`, replace entity `j` iff `mask & (1<<j)`; refit (keeping fixed
weights/design) and recompute the target + HC3. Relative shift
`= 100·|(b_mask − b_zero)/b_zero|` (max unrounded, tie → smaller mask). Per popcount
stratum report counts, coefficient range, p-value range, mean shift. Shapley
`φ_j = Σ_{S ∌ j} |S|!(m−|S|−1)!/m! · [b(S∪{j}) − b(S)]`; verify
`Σ_j φ_j = b(all) − b(none)` within tolerance.

## Controlled decision

Complete every module first. Evaluate each gate/flag predicate on **unrounded**
values in the declared reporting order, count satisfied gates, then apply only
this request's mapping — count thresholds (all-pass / at-least-N), first-failed
module by precedence, and any tie rules — to emit the controlled classification
enum exactly as the template allows.
