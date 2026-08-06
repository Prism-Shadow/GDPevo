# PHO audit method library

Canonical, reusable implementations of the primitives these audits recombine.
**Nothing here is a task answer.** Every entity list, measure, year, seed,
grid, threshold, PRNG choice, model form, and decision mapping is *bound from
the effective request* at runtime — the text below only fixes *how* each named
method behaves once its parameters are bound. When a request's `method` string,
`required_evidence`, or a methodology doc specifies a formula, order, or
tie-break, that specification wins over any default here.

Guiding invariant: **resolve one effective request first** (data bindings +
overrides), then compute every module from it consistently. Carry full precision
end to end; round only at the moment of reporting; evaluate every decision
predicate on **unrounded** values.

---

## 1. Release resolution (one record per cell)

For each requested publication cell (entity × time × measure/field, with the
requested `value_type`/`source_type`), filter candidate rows by the effective
bindings: `release_status` (usually `FINAL`), `value_type`, `source_type`,
validity (drop suppressed / invalid quality flags / withdrawn / blank / null),
and geography scope. Among survivors select **one** record by the declared
priority, canonically:

1. greatest `revision`,
2. then latest `released_at` timestamp,
3. then the tie-break on the record id (`observation_id`/`record_id`) exactly as
   the request states — *lowest* id in some protocols, *greatest* in others.
   **Read which; do not assume.**

Missing rule (universal): suppressed, invalid, withdrawn, blank, or null values
are **unavailable**, never zero-filled. When a task asks for "selected release
counts", count *selected publications* before analytic-completeness exclusions.

Apply `revisions` events only as the methodology doc dictates (`APPLIED` already
folded into later finals; `WITHDRAWN`/pending do not overwrite; unresolved
scale-breaks may render a cell an anomaly to exclude/impute per the request).

## 2. Cohort construction

Join independently resolved series by stable entity+time keys, then build each
named cohort from its effective required-field predicates. Typical cohorts:

- **complete-case (reference year):** all required outcome/exposure/adjustment
  fields present and valid in the reference year.
- **balanced panel:** entities complete-and-valid in *every* requested year
  (intersection across years).
- **broad reference:** reference-year complete cases for the outcome and *all*
  ordered model features.
- **strict dual-source:** complete for outcome + primary series + parallel
  series + adjustments in every analysis year.

Preserve declared order everywhere: entity code, then time; and every declared
feature / group / cluster order. Report cohort sizes/exclusions exactly as the
template names them (e.g. excluded = universe minus cohort, ASCII-sorted).

## 3. Two-way fixed-effects OLS (double demeaning)

On each active fit, transform every modeled variable to
`z_it − entity_mean_i − time_mean_t + grand_mean` over the *active* rows, then
solve OLS **without intercept** in declared predictor order. A cluster deletion
removes the whole cluster, recomputes all means, and refits from scratch in
entity-code order.

## 4. Delete-one-cluster jackknife

For G delete estimates `b_(-g)` with mean `bbar`:
`SE_JK = sqrt((G-1)/G · Σ_g (b_(-g) − bbar)²)`,
`b_BC = G·b − (G-1)·bbar`. Registered test statistic is `b/SE_JK` (or
`b_BC/SE_JK` when the request says bias-corrected), two-sided Student-t with
`G−1` df. Percent change per deletion = `100·|(b_(-g) − b)/b|`; pick extrema by
unrounded value, tie-broken by entity/cluster order.

## 5. Weighted least squares, HC3, CR1 (shared linear algebra)

- **WLS:** with weights `w`, set `Xw = diag(√w)·X`, `yw = diag(√w)·y`, solve
  `b = (Xw'Xw)⁻¹ Xw'yw` in declared column order. (Unweighted = all `w=1`.)
- **HC3:** with hat `h_i = diag(Xw (Xw'Xw)⁻¹ Xw')` and `ew_i = √w_i·(y_i − X_i b)`,
  `V_HC3 = (Xw'Xw)⁻¹ Xw' diag(ew_i²/(1−h_i)²) Xw (Xw'Xw)⁻¹`; two-sided Student-t,
  `n−k` df.
- **CR1 (cluster-robust):** cluster scores `s_g = Xw_g' ew_g`,
  `V_CR1 = [G/(G−1)]·[(n−1)/(n−k)]·(Xw'Xw)⁻¹ (Σ_g s_g s_g') (Xw'Xw)⁻¹`;
  two-sided Student-t, `G−1` df.

## 6. Ridge / elastic-net with nested leave-group-out CV

Folds: outer = hold out one declared group; inner = within each outer-training
set, hold out each remaining group once, same order.

Scaling (inside **every** fit, training-only): subtract training feature mean,
divide by training SD. Read whether the request wants **sample SD (ddof=1)** or
**population SD (ddof=0)**, and whether SD is **weighted**
(`σ_j = √(Σ w_i (x_ij−μ_j)² / Σ w_i)`); zero-variance divisor → 1. Apply the same
moments to validation/test rows. Center `y` (by its training mean, weighted if
requested) with an **unpenalized** intercept.

Solvers:
- **Ridge (coordinate descent):** init `b=0`, cycle in declared feature order,
  `b_j = Σ_i x_ij r_ij / (Σ_i x_ij² + n·λ)` where `r` excludes feature `j`.
- **Elastic-net (coordinate descent):** objective
  `Σ w_i (y_i − Z_i b)² / (2 Σ w_i) + λ[α Σ|b_j| + (1−α) Σ b_j²/2]` (some
  requests parameterize as `α·(ρ Σ|b| + ½(1−ρ) Σ b²)`; use the request's form).
  Cold-start `b=0` for every (λ, fold) — **never warm-start**. Update
  `b_j = S(ρ_j, λα)/(1 + λ(1−α))`, `ρ_j = Σ w_i Z_ij (y_i − Σ_{l≠j} Z_il b_l)/Σ w_i`,
  soft-threshold `S(a,t)=sign(a)·max(|a|−t,0)`. Update the intercept by (weighted)
  mean residual each sweep when the request keeps an explicit intercept.
- Stop after a full sweep when max coefficient change < the effective tolerance,
  or at the sweep/cycle cap.

Selection & aggregation: for each penalty **pool row-level (validation) squared
errors** then take RMSE (not a mean of fold RMSEs). Choose smallest unrounded
RMSE, then the smaller penalty (then smaller α, then smaller `l1_ratio` when a 2-D
grid). Refit on all outer-training rows, predict the outer holdout, pool exactly
**one** OOF prediction per eligible row. Report pooled RMSE, MAE, and
`R²/Q² = 1 − pooled_SSE / SST`, with SST about the full-sample outcome mean
(weighting only if the request says so). Determine nonzero coefficients with the
declared numerical cutoff.

## 7. Wild cluster bootstrap-t (restricted null)

Observed leg: studentize the full target coefficient with cluster CR1 (§5).
Fit the **restricted** model without the target; keep restricted fitted values
and residuals in entity order.

PRNG — **bind the one the request names**; keep a single continuous stream for
the whole run:

- **PCG32** (64-bit state, 32-bit output; unsigned wraparound mod 2⁶⁴):
  `increment = 2·stream + 1`; seed by `state=0 → advance → state += seed →
  advance`. Each advance: `old = state`;
  `state = old·6364136223846793005 + increment`;
  `xorshifted = low32(((old>>18) XOR old) >> 27)`; `rot = old>>59`;
  `output = rotate_right_32(xorshifted, rot)`. Map `output mod 6`, in order, to
  the Webb 6-point weights `[−√(3/2), −1, −√(1/2), √(1/2), 1, √(3/2)]`.
- **xorshift32** (unsigned, 32-bit mask after **each** xor):
  `x ^= x<<13; x ^= x>>17; x ^= x<<5`. Rademacher map: odd/low-bit-1 → +1,
  else −1.

Draw once per cluster in the declared (entity-code) order per replicate; reuse
the same draw across paired equations when the request pairs them. Form
`y* = restricted_fit + restricted_resid · weight`, refit the unrestricted model,
recompute CR1, studentize. Record a checkpoint **only after** its replicate
completes, using the then-current PRNG state — never reset the stream.

Test: `p = (1 + count)/(1 + B)` where `count` is exceedances of the observed
statistic (`|t*| ≥ |t_obs|`, or one-sided/absolute per the request, allowing the
declared comparison tolerance `δ`: `t* ≥ t_obs − δ`). Report requested quantiles
using the declared estimator — **nearest-rank** (`x[min(B,⌈p·B⌉)−1]`, one-based)
or **type-7** (`h=(B−1)p`, interpolate) — read which.

## 8. Split / grouped conformal calibration

For each ordered test group: choose the calibration group as the request states
(e.g. greatest row count then ascending name, or a fixed cyclic/preceding
partition); train "proper" on the rest with the same scaling/solver rules
(reuse the outer model + selected penalty when the request says so). Compute
absolute calibration residuals (reduce to one max-abs per calibration entity when
requested). Nearest-rank radius: one-based `r = min(m, ⌈(m+1)·coverage⌉)`,
`q = sorted_score[r]`. Intervals `ŷ ± q` are **inclusive**. Report per-fold
coverage/width/MAE, then aggregate coverage and (row-count-weighted) mean width;
pick worst group by smallest unrounded coverage then declared order. Use
unrounded group coverages for minima and decision predicates.

## 9. Trajectory PCA + deterministic k-means + stability

**PCA:** build feature columns in the declared variable-major/time order and
entity ASCII order; standardize each column by its (active-sample) SD — read
sample vs population; form covariance `C = Z'Z/(n−1)` (or `/n` if the request
says population). Eigensolve with symmetric Jacobi: pivot on the largest
absolute upper-triangle off-diagonal (tie: lower row then column);
`τ=(A_qq−A_pp)/(2A_pq)`, `t=sign⁺(τ)/(|τ|+√(1+τ²))`, `c=1/√(1+t²)`, `s=tc`;
rotate `A` and eigenvectors; stop at the off-diagonal tolerance or step cap.
Order components by **descending eigenvalue**, tie by original diagonal index.
Orient each loading so its **earliest maximum-absolute entry is positive**.
Scores = `Z · oriented_loadings`. Explained ratios divide by the sum of all
eigenvalues.

**Deterministic k-means (squared Euclidean, farthest-first init):** first center
= ASCII-first entity; each next center = the entity maximizing distance to its
nearest existing center, tie by entity code. Assign to nearest center, tie by
lower working id; update centers by member means; stop when assignments are
unchanged or at the cap. Empty cluster: move the ASCII-first entity among those
farthest from its assigned center, recompute, continue. Canonicalize final ids
by centroid coordinates then working id.

**Cluster-count selection (when a candidate grid is given):** Euclidean
silhouette with singleton silhouette = 0; select **largest unrounded mean
silhouette**, tie by smaller k.

**Stability:** for each omitted time block (or deleted entity) in the declared
order, rebuild scaling → PCA → orientation → init → clustering from scratch and
compare to the full assignment via the **Adjusted Rand Index**:
`ARI = (Σ_ij C(n_ij,2) − E) / (½(Σ_i C(a_i,2) + Σ_j C(b_j,2)) − E)`,
`E = Σ_i C(a_i,2)·Σ_j C(b_j,2)/C(n,2)`. Align refit labels to the full labels by
the permutation with maximum agreement, tie to the lexicographically smallest
mapped-id vector; report aligned agreement/changes and the ARI array + summaries.

## 10. Two-step linear GMM (when requested)

Residualize outcome, dynamic regressors, and instruments against
`intercept + baseline terms`. First step: moments `g(θ)=Z'(y−Dθ)/n` with
identity weight. Cluster scores `s_g=Z_g'u_g`, `S=Σ_g s_g s_g'/n`; second-step
weight = Moore–Penrose pseudoinverse of `S` (apply the declared relative
singular-value cutoff). Second-step `θ` from the weighted linear moments;
`Hansen J = n·g(θ)'W g(θ)`. Delete-cluster: refit both steps in cluster order;
`θ_bc = G·θ_full − (G−1)·mean(θ_delete)`; retain max abs delete shifts.
First-stage partial F from full-vs-reduced residual sums of squares with the
effective instrument counts. For an indirect effect `θ=a·b`,
`Var(θ)=b²Var(a)+a²Var(b)+2ab·Cov(a,b)`.

## 11. Source / source-year perturbation

Enumerate the declared subsets — by increasing subset size then lexicographic
tuple order, or every mask `0..2^m−1` over an ordered entity list (ordered by
descending |alternate − primary|, tie by entity code). Keep the strict analytic
set and (when weighted) the fixed reliability weights unchanged. Refit per
subset/mask, recomputing the declared inference (CR1 or HC3). Percent shift =
`100·|(b_alt − b_base)/b_base|`; same-sign requires both nonzero with identical
sign. Median = ordinary median of ordered shifts. Worst = greatest unrounded
shift, tie by earlier subset order / smaller mask. Per popcount stratum report
scenario count, coefficient range, p-value range, mean shift.

**Exact Shapley (when requested):** for ordered entity `j`,
`φ_j = Σ_{S∌j} |S|!(m−|S|−1)!/m! · [b(S∪{j}) − b(S)]`; preserve signed order and
check `Σ_j φ_j = b(all) − b(none)` within tolerance.

## 12. Partial-R² mediation sensitivity surface (when requested)

From unrounded baseline `a`, `b`, `SE_b`, residual df:
`magnitude = SE_b·√(df·rY·rM/(1−rM))`. For each direction `s∈{−,+}`:
`b_adj = b − s·magnitude`, `indirect_adj = a·b_adj`,
`direct_adj = total − indirect_adj`, `proportion = indirect_adj/total`.
Enumerate the full surface in declared `r2_mediator × r2_outcome × direction`
order; compute the equal-strength positive tipping-point R² from unrounded
inputs.

## 13. Controlled decision

Complete **every** evidence module first. Evaluate each business predicate/gate
on **unrounded** values, in the declared reporting order. Then apply *only the
effective request's* mapping — either count satisfied gates against thresholds
(e.g. all-pass / at-least-N / else) or select the **first unsatisfied module by
the declared precedence** (e.g. `NOT_ROBUST_AT_<first failed>`). Honor the
request's exact enum spellings and tie/precedence rules.

---

## Override / binding resolution (protocol tasks)

When the request carries a `protocol_id`, treat the profile as method-only.
Bind entities, measures, fields, time coordinates, sources, seeds, grids,
tolerances, reporting cutoffs, output names, and decision predicates from the
**effective request**. Resolve overrides in request document order: a root key
`<section>_overrides` targets canonical `<section>`; `module_overrides.<name>`
targets that module; strip only the terminal `_overrides` suffix. Objects merge
recursively by exact key; arrays replace whole arrays; scalars/strings/booleans/
null replace their exact path; absent paths inherit. No array concatenation,
positional patching, alias inference, key renaming, or type coercion; reject
unknown targets and type mismatches before touching data. Resolve the single
effective request **before** any data access, fold, draw, fit, or decision.
