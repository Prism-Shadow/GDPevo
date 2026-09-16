# Statistical Primitives

Use unrounded floating point values internally. Report rounding is an output-format step, not a computation step.

## Linear Models

- OLS: solve in declared column order with a stable least-squares or pseudoinverse solver when the method allows it. Do not add an intercept unless the design calls for one.
- WLS: transform `Xw=sqrt(w)*X` and `yw=sqrt(w)*y`, then solve OLS on transformed data.
- HC3 covariance: use weighted leverage `h_i=diag(Xw (Xw'Xw)^-1 Xw')` and weighted residual `ew_i=sqrt(w_i)*(y_i-X_i b)`.
- CR1 covariance: for ordered clusters `g`, compute score `s_g=X_g' e_g` (or weighted score in WLS). Use finite sample factor `[G/(G-1)]*[(n-1)/(n-k)]`, and Student t with `G-1` degrees of freedom when requested.
- Jackknife: always refit from scratch after deleting a cluster/entity. Choose extrema or influence from unrounded diagnostics, using the declared tie rule.

## Cross-Validation And Penalized Models

- Scaling is training-only inside each fit. Apply the training moments to validation/test rows.
- Use sample SD only when the profile says sample SD; use population SD when it says population or weighted population SD. If a feature has zero variance, follow the active profile's unit-divisor or zero-feature rule.
- Pool validation squared errors at the row level before taking RMSE unless the request explicitly asks for fold-average RMSE.
- Tie-break hyperparameters only after comparing unrounded metrics.
- Cold-start coordinate descent when the profile says not to warm-start; do not reuse coefficients across folds or penalties in those profiles.

## Wild Bootstrap PRNGs

Unsigned xorshift32:

1. Start from the request seed as an unsigned 32-bit integer.
2. For each call: `x ^= x << 13`, mask to 32 bits; `x ^= x >> 17`, mask; `x ^= x << 5`, mask.
3. Use one continuous stream. Draw clusters in the active registered order inside each replicate.
4. Map signs exactly as the profile says, commonly odd to `+1` and even to `-1`.

PCG32 Webb bootstrap:

1. Use unsigned 64-bit state and increment `2*stream+1`.
2. Initialize by advancing from zero, adding the seed modulo `2^64`, then advancing again.
3. Each advance multiplies by `6364136223846793005`, adds increment modulo `2^64`, and emits the rotated xorshifted high bits.
4. Map output modulo six to the ordered Webb weights declared by the profile.

For bootstrap p-values, use the active comparison rule. Common forms are absolute exceedance with plus-one p `(count+1)/(B+1)` or direct `count/B`. Record checkpoints only after a listed replicate is fully complete.

## Conformal Calibration

- Build calibration scores only from the active calibration scheme. Some profiles use row residuals; others reduce residuals to one maximum per calibration state.
- Sort absolute residuals ascending. For nominal coverage `c`, common rank is `min(m, ceil((m+1)*c))`; for miscoverage `alpha`, common rank is `min(m, ceil((m+1)*(1-alpha)))`.
- Intervals are symmetric and inclusive unless the request says otherwise.
- Aggregate coverage by raw covered/test row counts and widths by the declared weighting.

## PCA, Clustering, And Stability

- Build feature matrices in declared variable/time order and entity order. Standardize before PCA using the profile's sample or population moments.
- Use covariance denominator from the profile: `n-1` for sample covariance, `n` for population covariance.
- Sort eigenpairs by descending eigenvalue. Orient each retained component so the earliest maximum-absolute loading is positive unless a burden-direction rule requires an additional sign choice.
- K-means profiles use deterministic farthest-first initialization. Start from the declared first entity rule, add the farthest point from existing centers, tie by entity code/id, assign ties to lower cluster ID, and update arithmetic centers until labels stop changing or the cap is reached.
- Adjusted Rand index must be computed on label partitions, not label names. For refit label reporting, align labels by maximum agreement and the declared tie rule.
- Silhouette uses Euclidean distances; singleton clusters have silhouette zero when the profile says so.

## Perturbation And Shapley

- Source or year perturbations keep the active analytic cohort fixed unless the request says replacement changes eligibility.
- Enumerate subsets/masks exactly in the declared order. For bitmask profiles, index entity `j` by the ordered disagreement list and replace when `mask & (1 << j)` is nonzero.
- Percent shift normally uses `100*abs((b_alt-b_base)/b_base)` from unrounded coefficients.
- Exact Shapley effect for ordered entity `j` is the weighted average over all subsets not containing `j` of `b(S union {j})-b(S)`, with weight `|S|!*(m-|S|-1)!/m!`.

## JSON Output Hygiene

- Convert all NumPy scalars and arrays to plain JSON types.
- Reject `NaN`, positive infinity, and negative infinity. Use `null` only when the requested statistic is mathematically unavailable.
- Rounding should produce JSON numbers, not strings.
- For fields declared with literal grids or thresholds, report the literal request values at the requested precision rather than recomputed binary floating variants.
