# Reusable Module Methods

The reusable algorithms for every PHO audit module family, synthesized across
protocols. Each module's **method is reusable**; its **parameters are task-local**
(seed, stream, replicate schedule, grids, cutoffs, feature order, cohort,
thresholds) — bind them from the effective request and never copy solved values.

Run modules in the request's declared order. Within a module, follow the
deterministic rules exactly: ordering, tie-breaks, and PRNG state are part of the
answer.

Common notation: `n` rows, `k` parameters, `G` clusters, entity-code then time
order throughout.

---

## A. Regression cores

### A1. Two-way fixed effects (double-demean OLS)
For entity `i`, time `t`, active entity mean `μ_i`, active time mean `ν_t`, active
grand mean `μ`:

    z*_it = z_it − μ_i − ν_t + μ

Apply to every modeled variable (outcome and predictors), then solve OLS **without
an intercept** in declared predictor order. A cluster deletion removes the whole
cluster, **recomputes every mean**, and refits from scratch in entity-code order.
Used by delete-cluster FE and as the shared matrix for wild bootstrap.

### A2. Reliability-weighted least squares (WLS)
For design `X`, outcome `y`, positive weights `w`: set `Xw = diag(sqrt(w))·X`,
`yw = diag(sqrt(w))·y`, then

    b = (Xw'Xw)^−1 · Xw'yw

in declared column order. Keep the selected direct outcome-record `sample_size` as
the fixed positive weight through every refit (including perturbation) unless
overridden.

### A3. Heteroskedasticity HC3
With leverage `h_i = diag(Xw·(Xw'Xw)^−1·Xw')` and weighted residual
`ew_i = sqrt(w_i)·(y_i − X_i·b)`:

    V_HC3 = (Xw'Xw)^−1 · Xw' · diag(ew_i² / (1 − h_i)²) · Xw · (Xw'Xw)^−1

Two-sided Student-t with `n − k` residual degrees of freedom.

### A4. Cluster-robust CR1
For ordered clusters `g`, cluster score `s_g = X_g'·e_g` (weighted: `Xw_g'·ew_g`):

    V_CR1 = [G/(G−1)] · [(n−1)/(n−k)] · (X'X)^−1 · Σ_g (s_g·s_g') · (X'X)^−1

Two-sided Student-t with `G − 1` degrees of freedom. CR1 is the default
clustered inference for FE, WLS, GMM, bootstrap, and perturbation modules.

---

## B. Delete-one-cluster jackknife

Fit the full model (FE/WLS), then delete every registered cluster in order and
refit the **unchanged** design from scratch. For target coefficient `b`, delete
estimates `b_-g`, and mean `b̄`:

- Bias-corrected coefficient: `b_BC = G·b − (G−1)·b̄`.
- Jackknife SE: `SE_JK = sqrt((G−1)/G · Σ_g (b_-g − b̄)²)`.
- Test: Student-t with `G − 1` df. The tested statistic is protocol-specific —
  some test `b_BC / SE_JK`, others test `b / SE_JK`. Read the request.
- Influence / percent change: `100 · |(b_-g − b) / b|`; choose greatest unrounded
  change, tied by earlier cluster order. Report min/max delete cluster by
  coefficient then entity code.

A deletion removes the whole cluster and recomputes all dependent means/moments;
do not approximate.

---

## C. GMM / difference-GMM / two-step linear GMM

### C1. Two-step linear GMM (panel/dynamic)
Within every full or delete-cluster fit, residualize outcome, dynamic regressors,
and instruments against intercept plus effective baseline terms.

- First-step moments: `g(θ) = Z'(y − D·θ)/n` with identity weight.
- Cluster scores `s_g = Z_g'·u_g`, `S = Σ_g (s_g·s_g')/n`; second-step weight `W`
  is the registered Moore-Penrose inverse of `S` (apply the declared relative
  singular-value cutoff to every pseudoinverse).
- Second-step `θ` from the weighted linear moments; **Hansen J** = `n·g(θ)'·W·g(θ)`.
- Delete-cluster bias correction: `θ_bc = G·θ_full − (G−1)·mean(θ_delete)`. Retain
  maximum absolute delete-cluster shifts.

### C2. Difference-GMM mediation
Create adjacent-change rows in entity then end-period order using the effective
lag structure and equation bindings. Per equation: `W = (Z'Z)^−1`,
`β = (X'ZWZ'X)^−1 · X'ZWZ'y`. With residual `u` and cluster score `q_g = Z_g'·u_g`,
use the registered finite-sample cluster sandwich; for two equations use the
cross-cluster score product for the covariance.

- **Indirect effect** `θ = a·b` with
  `Var(θ) = b²·Var(a) + a²·Var(b) + 2ab·Cov(a,b)`; Student-t inference with
  cluster df.
- **Stacked indirect**: cross-equation correction, `a·b` covariance, estimate,
  cluster SE, 95% interval.
- **First-stage partial F**: from full-vs-reduced residual sums of squares using
  effective instrument counts.
- Delete-state diagnostics: rebuild rows and refit all affected equations from
  scratch in state order.

---

## D. Nested leave-one-group-out ridge / elastic-net CV

### D1. Folds
Outer: hold out one ordered group (state/division) per outer fold. Inner: within
each outer training set, hold out every remaining group once **in the same order**.
(For blocked state folds, allocate states by descending retained-entity counts to
the currently smallest fold, lower fold id on equality; sort codes within folds.)

### D2. Training-only standardization
Within every fit: subtract **training** feature means and divide by **training**
sample SD. The SD degree-of-freedom convention (sample `ddof=1` vs population) is
**task-local** — read it. Use a unit divisor for zero variance. Apply those
training moments to validation/test rows. Center the outcome by its training mean
(do not scale `y`). Indicators/Reference-category columns are left unchanged when
the request says so.

### D3. Ridge solver (coordinate descent)
Center training outcome, keep the intercept **unpenalized**, initialize
coefficients to zero, cycle in declared feature order. Objective
`mean((y − a − Xb)²) + λ·Σ_j b_j²`. Update:

    b_j = Σ_i x_ij·r_ij / (Σ_i x_ij² + n·λ)

where `r` excludes feature `j`. Stop after a full sweep when the max coefficient
change is below the effective tolerance or at the sweep cap.

### D4. Elastic-net solver (weighted)
Cold-start `b = 0` (and intercept at training outcome mean) for every penalty and
fold — **never warm-start**. Objective
`Σ_i w_i(y_i − Z_i·b)²/(2·Σw) + λ·[α·Σ_j |b_j| + (1−α)·Σ_j b_j²/2]`. In cyclic
feature order:

    ρ_j = Σ_i w_i·Z_ij·(y_i − Σ_{l≠j} Z_il·b_l) / Σ_i w_i
    b_j = S(ρ_j, λ·α) / (1 + λ·(1−α))
    S(a, t) = sign(a)·max(|a| − t, 0)

Stop at the effective max-change tolerance or cycle cap. Update the intercept by
mean residual when included. Determine nonzero coefficients with the effective
numerical cutoff.

### D5. Selection and aggregation
For each penalty, **pool inner validation squared errors at row level**, take RMSE
(not the mean of fold RMSEs), choose the **smallest unrounded RMSE** then the
smaller penalty (then smaller `α`, then smaller `l1_ratio` for elastic net). Refit
on all outer-training rows, predict all outer rows. Pool exactly **one outer
prediction per eligible row**; compute RMSE, MAE, and
`Q²/R² = 1 − SSE / SST` where SST uses the full-sample (unweighted) outcome mean.
Report every outer fold's aligned inner grid, selected penalty, nonzero count,
and outer RMSE; report the worst outer group.

---

## E. Wild cluster bootstrap

### E1. Observed and restricted model
Use the same double-demeaned/weighted matrix as the regression core. Studentize
the full target coefficient with CR1. Fit the **restricted** model **without the
target** and retain restricted fitted values and residuals (untransformed, in
entity order).

### E2. PRNG (task-local — use exactly what the request declares)
- **PCG32 (Webb 6-point).** Unsigned wraparound, 64-bit state, 32-bit output.
  `increment = 2·stream + 1`; initialize state to zero, advance, add the effective
  seed modulo 2⁶⁴, advance. Each advance: `old = state`;
  `state = old·6364136223846793005 + increment (mod 2⁶⁴)`;
  `xorshifted = low32(((old>>18) xor old)>>27)`; `rot = old>>59`;
  `output = rotate_right_32(xorshifted, rot)`. Map `output mod 6` in order to the
  Webb weights `[−sqrt(3/2), −1, −sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- **xorshift32 (Rademacher).** Unsigned 32-bit. Each call:
  `x ^= x<<13; x ^= x>>17; x ^= x<<5`, masking to unsigned 32 bits **after every
  xor**. Map low bit 1 → `+1`, 0 → `−1`.

Maintain **one continuous stream**; never reset between replicates or checkpoints.

### E3. Draw, refit, test
For every replicate, draw once per cluster **in entity-code order**; set
`y* = restricted_fit + restricted_residual · cluster_weight` (reuse the same
cluster sign across paired equations when paired); refit the unrestricted model;
recompute CR1; record the absolute studentized target. Checkpoints are recorded
**only after** the listed replicate completes, using the current PRNG state and
that replicate's statistic.

- **p-value**: count `|t*| ≥ |t_obs|` (some protocols use a comparison tolerance
  `δ`: count `t* ≥ t_obs − δ`); report `(1 + count)/(1 + B)`.
- **Quantiles**: nearest-rank `x[min(B, ceil(p·B)) − 1]` (one-based rank) **or**
  type-7 linear `h=(B−1)·p, j=floor(h), γ=h−j,
  (1−γ)·x[j] + γ·x[j+1]` (zero-based) — protocol-specific; read it.
- Report observed coefficient, CR1 SE, observed t, bootstrap p, coefficient
  mean/SD, requested quantiles, every checkpoint, and the **terminal generator
  state**.

---

## F. Grouped split conformal

### F1. Partition and fit
For each ordered outer group as **test**, choose **calibration** per the request:
- greatest row count then ascending group name (among remaining), with the rest as
  proper training; **or**
- a registered preceding cyclic partition, with the rest as proper training; **or**
- hold out each other training cluster once and pool.

Fit ridge/elastic-net **from scratch** with the effective fixed penalty and the
**identical training-only scaling and solver rules** (D2–D4). Some variants reuse
nested-CV outer predictions instead of refitting.

### F2. Rank interval
Sort `m` absolute calibration residuals. With miscoverage `α` (coverage
`c = 1 − α`): one-based `r = min(m, ceil((m+1)·c))`, radius `q = score[r]`.
Intervals `prediction ± q` are **inclusive**. (Some variants reduce calibration to
one max-abs residual per calibration entity, then take the one-based kth entity
maximum.) Report fold coverage, width, and absolute error; aggregate coverage and
width by outer-test row counts (weight mean width by held-out count). Choose worst
by smallest coverage fraction then earlier cluster order.

---

## G. Covariance PCA (Jacobi)

### G1. Build and standardize
Columns in **variable-major / time-major** order (declared), entities in ASCII
order. Standardize each column by active-column sample SD (convention
`ddof=1` giving `C = Z'Z/(n−1)`, or population `Z'Z/n` — task-local). Form `C`.

### G2. Symmetric Jacobi eigensolver
Select the largest absolute upper-triangle off-diagonal, tying by **lower row then
column**. `τ = (A_qq − A_pp)/(2·A_pq)`;
`t = sign_nonneg(τ) / (|τ| + sqrt(1 + τ²))`; `c = 1/sqrt(1 + t²)`; `s = t·c`.
Rotate `A` and the eigenvectors. Stop at the effective off-diagonal tolerance or
step cap.

### G3. Order, orient, score
Order components by **descending eigenvalue then original diagonal index**. Flip
each loading so its **earliest maximum-absolute entry is positive**. Scores = `Z`
times oriented loadings. Explained ratio = eigenvalue / sum of all eigenvalues.
Report the leading spectrum, explained ratios, cumulative ratio, signed loadings,
and all entity scores.

---

## H. Deterministic k-means + silhouette

### H1. Initialization (farthest-first)
Run squared-Euclidean k-means on the effective leading scores. First center =
**ASCII-first entity**; each next center = the entity **maximizing distance to its
nearest center**, tied by entity code. (Some protocols initialize at the smallest
entity id then add the farthest point.)

### H2. Assignment and update
Assign to nearest center, **tied by lower working id**; update centers by member
means. Stop when assignments are unchanged or at the effective cap (some add a
registered center-tolerance). **Empty-id handling**: for empty ids in order, move
the ASCII-first entity among those farthest from their assigned center, recompute,
continue. Canonicalize final ids by centroid coordinates then working id.

### H3. Silhouette (k selection)
Euclidean silhouette with **singleton value 0**. Select the candidate `k` with the
largest **unrounded mean silhouette**, tied by smaller `k`. Report sizes and the
high-burden (or designated) membership sorted ascending.

### H4. Stability (leave-one-out / delete-cluster ARI)
For each omitted time block (ascending) **or** deleted cluster, rebuild scaling,
PCA orientation, initialization, and clustering from scratch. Compute the
**adjusted Rand index** from the contingency table:

    ARI = (Σ_ij C(n_ij,2) − expected) / (0.5·(Σ_i C(a_i,2) + Σ_j C(b_j,2)) − expected)
    expected = Σ_i C(a_i,2) · Σ_j C(b_j,2) / C(n,2)

Align refit labels by the permutation with **maximum agreement**, tied by the
lexicographically smallest mapped-id vector; report aligned agreement. Report
mean/minimum ARI over the refits.

---

## I. Source / year / group perturbation

### I1. Year-subset perturbation
Enumerate time subsets by **increasing requested subset size then lexicographic
tuple order**. Keep the strict dual-source cohort unchanged. For each subset, refit
the complete double-demeaned (or weighted) model **separately** with primary and
parallel series, recomputing CR1 and `G − 1` df inference. For baseline `b` and
alternate `b_alt`: `shift = |b_alt − b| / |b| · 100`; **same-sign** requires both
nonzero with identical sign. Compute the ordinary **median of ordered shifts**.
Choose worst by greatest **unrounded** shift, then earlier subset order.

### I2. Exhaustive direct-vs-rollup source perturbation (with exact Shapley)
Resolve alternate outcomes with the module's release filters and
greatest-revision/latest-release record-id precedence. Order paired entities by
**descending absolute (alternate − primary) difference**, tied by entity code. For
index `j` and every mask `0 .. 2^m−1`, replace entity `j` iff `mask & (1<<j)`; retain
fixed reliability weights and design; refit WLS + HC3. Relative shift
`100·|((b_mask − b_zero)/b_zero)|`. For each popcount stratum report scenario
count, coefficient range, HC3 p-value range, mean shift. Select maximum unrounded
shift, tied by smaller mask. **Exact Shapley**:

    φ_j = Σ_{S ⊆ {1..m}\{j}} |S|!·(m−|S|−1)!/m! · [b(S∪{j}) − b(S)]

Preserve signed `φ` order; verify `Σ_j φ_j = b(all replaced) − b(none replaced)`
within numerical tolerance.

### I3. No-retune outer-fold source-group deletion
For every source group and outer fold in declared order, **remove exactly the
group's terms** and reuse that fold's full-model selected hyperparameters **without
retuning**. Apply the same remaining-term preprocessing and solver; retain all
outer-fold RMSEs; pool their squared errors; deterioration = full-model OOF RMSE −
removed RMSE. Count folds worse than the corresponding full-model fold. Rank groups
by decreasing unrounded deterioration, then declared group order.

---

## J. Partial-R² mediation sensitivity surface

From unrounded baseline `a`, `b`, `SE_b`, and residual df:

    magnitude = SE_b · sqrt(df · rY · rM / (1 − rM))

For each declared direction `s ∈ {−1, +1}`:
`adjusted_b = b − s·magnitude`; `adjusted_indirect = a·adjusted_b`;
`adjusted_direct = total − adjusted_indirect`;
`proportion = adjusted_indirect / total`.

Enumerate the complete surface in declared R² (mediator) × R² (outcome) ×
direction order. Compute the equal-strength positive **tipping R²** root from
unrounded inputs.

---

## K. Country reconciliation / quality audit (cross-section + panel variant)

A distinct audit shape (no `protocol_registry_record`); still portal-only and
deterministic.

1. **Reconciliation.** Reconcile requested country labels to stable `iso3` via
   `portal_label` / `alternate_labels` / `canonical_name`. Report requested count,
   uniquely resolved count, alias-resolution count (resolved labels differing from
   the canonical name), and all resolved `iso3` sorted ascending.
2. **Quality audit.** Apply revision events: `APPLIED` authorize use; report
   applied vs non-applied `revision_event_id`s sorted ascending. Detect unresolved
   scale-break anomalies (cells where an `APPLIED` SCALE_CORRECTION's `old` vs
   `new` differ by a large factor and remain unresolved) as `ISO3|YEAR|indicator`
   keys sorted ascending. Count raw-missing 2022 cells, anomaly 2022 cells, and
   imputed 2022 cells after quality exclusions. Report usable country/indicator
   counts (completed PCA matrix dimensions).
3. **PCA.** Covariance PCA (G) on the completed matrix; report retained component
   count, PC1 variance fraction, and the top absolute loadings (descending
   absolute loading, indicator ascending breaks ties).
4. **Clusters.** Three-segment grouping (LOW/MIDDLE/HIGH burden); select best `k`
   among the declared candidates by silhouette (H3); report sizes and high-burden
   membership sorted ascending.
5. **Panel model.** Region-fixed-effects OLS of `life_expectancy` on PC1 burden
   across country-years; report `n`, coefficient, SE, two-sided p, R², and whether
   region FE were applied.
6. **Advisory.** Apply the request's mapping (e.g. prioritize high-burden cluster
   vs monitor gradient vs no adverse gradient) based on the panel result.
