# Numeric Methods Reference

Use this file for implementation details that recur across PHO audit protocols. Request-specific protocol profiles can override scaling, quantile type, fold definitions, and tie rules.

## Rounding And Ties

- Keep internal values as full precision floats or exact integers.
- Evaluate gates, maxima, minima, medians, and ties on unrounded values.
- Round only the JSON fields requested by the template. JSON numbers do not need trailing zeros.
- For extrema, use the request/profile tie rule. If unspecified, tie by earlier declared order for aligned arrays and ascending stable identifier for set-like outputs.
- Use JSON `null` only when a requested statistic is mathematically unavailable. Never emit NaN or Infinity.

## Linear Models

OLS:

- Fit columns in declared order. Include an intercept only when the design order includes one.
- Solve `(X'X)b = X'y`. If the request calls for a pseudoinverse cutoff, use that cutoff rather than silently dropping columns.
- Residuals are `e = y - Xb`.

WLS:

- For positive weights `w`, use `Xw_i = sqrt(w_i) X_i` and `yw_i = sqrt(w_i) y_i`.
- Fit OLS on weighted rows, but keep predictions on the original outcome scale.

HC3 covariance:

- Let `H_ii = Xw_i (Xw'Xw)^-1 Xw_i'` and `ew_i = sqrt(w_i)(y_i - X_i b)`.
- `V = A^-1 Xw' diag(ew_i^2 / (1-H_ii)^2) Xw A^-1`, where `A=Xw'Xw`.
- Use residual degrees of freedom `n-k` for two-sided Student-t inference.

Cluster CR1 covariance:

- For ordered clusters `g`, score `s_g = Xw_g' ew_g`.
- `V = [G/(G-1)] * [(n-1)/(n-k)] * A^-1 (sum_g s_g s_g') A^-1`.
- Use `G-1` degrees of freedom for two-sided t tests unless the request states otherwise.

Two-way fixed effects:

- For each modeled variable, transform `z_it` to `z_it - entity_mean_i - time_mean_t + grand_mean` on the active sample.
- Fit the transformed design without an intercept.
- Recompute all means inside every delete-cluster or subset refit.

## GMM And Mediation

One-step IV/GMM:

- With regressors `X`, instruments `Z`, and outcome `y`, use `W=(Z'Z)^-1` unless the protocol says identity.
- `b=(X'Z W Z'X)^-1 X'Z W Z'y`.

Two-step linear GMM:

- Residualize against required baseline terms first when the profile says so.
- First-step residuals build cluster scores `s_g=Z_g'u_g` and moment covariance `S`.
- Use the registered inverse or pseudoinverse of `S` as the second-step weight.
- Hansen `J = n * g(b)' W g(b)`, with `g(b)=Z'(y-Xb)/n`.

Indirect effects:

- For `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`.
- For delete-state diagnostics, rebuild the analytic rows and refit affected equations from scratch.

Partial-R2 sensitivity:

- With baseline `a`, `b`, path-b SE, and residual df, magnitude is `SE_b * sqrt(df*rY*rM/(1-rM))`.
- Direction controls whether that magnitude is added to or subtracted from `b`; then recompute indirect, direct, and proportion from unrounded values.

## Penalized Prediction

Training-only scaling:

- Compute means and standard deviations on the training rows only.
- Use the profile's denominator: sample SD (`ddof=1`), population SD (`ddof=0`), weighted population SD, or a unit divisor for zero variance.
- Apply training moments to validation/test rows.

Ridge:

- Keep intercept unpenalized.
- Select penalties from row-pooled validation squared errors, not the mean of fold RMSE values, unless the request says otherwise.
- Break equal RMSE by the smaller penalty.

Elastic net coordinate descent:

- Minimize the profile's objective exactly. Common forms are `SSE/(2n)+alpha*(rho*|b|_1 + 0.5*(1-rho)*||b||^2)` or the weighted analogue.
- Cold-start every fold/penalty unless the profile explicitly permits warm starts.
- Update coefficients in declared feature order. Stop only after a full sweep satisfies the max-change tolerance or after the cap.
- Count nonzero coefficients with the request/profile numerical cutoff.

Out-of-fold metrics:

- Each eligible row gets exactly one outer prediction.
- RMSE is `sqrt(mean(error^2))`, MAE is `mean(abs(error))`, and OOF R-squared is `1 - SSE / sum((y - full_sample_mean)^2)` unless overridden.

## Bootstrap PRNGs

Xorshift32:

1. Keep an unsigned 32-bit state.
2. `x ^= x << 13`, mask to 32 bits.
3. `x ^= x >> 17`, mask.
4. `x ^= x << 5`, mask.
5. Map odd output to `+1` and even output to `-1` for sign bootstraps.

Draw order:

- Maintain one continuous stream across all replicates.
- Draw clusters in the registered order inside each replicate.
- Record checkpoint state only after the replicate's full draw/refit/statistic is complete.

PCG32 Webb:

- Increment is `2*stream+1`.
- Initialize with the standard two-advance PCG seeding sequence using the request seed.
- Each output maps `value mod 6` to Webb weights in this order: `-sqrt(3/2)`, `-1`, `-sqrt(1/2)`, `sqrt(1/2)`, `1`, `sqrt(3/2)`.

Bootstrap tests:

- Restricted-null modules fit the restricted model without the target, generate `y* = restricted_fit + restricted_residual * cluster_weight`, refit the unrestricted model, recompute the requested covariance, and studentize.
- Plus-one p-value is `(1 + exceedance_count) / (1 + B)`.
- Nearest-rank quantile at probability `p` is sorted value `min(B, ceil(p*B))-1` using zero-based indexing.
- Type-seven quantile uses `h=(B-1)*p`, `j=floor(h)`, `gamma=h-j`, and linear interpolation between `x[j]` and `x[j+1]`.

## Conformal Calibration

- Use only calibration residuals allowed by the fold design.
- Sort absolute residuals ascending.
- For nominal coverage `c`, a common finite-sample rank is `min(m, ceil((m+1)*c))`.
- For miscoverage `alpha`, use `c=1-alpha` unless the profile states a different expression.
- Intervals are symmetric and inclusive: `[prediction - q, prediction + q]`.
- Aggregate pooled coverage by row counts. Aggregate widths by the weights declared in the template/profile.

## PCA, K-Means, ARI, Silhouette

PCA:

- Build columns in the declared variable/year order.
- Standardize each column using the profile's sample or population denominator.
- Use covariance `Z'Z/(n-1)` for sample profiles and `Z'Z/n` for population profiles.
- Sort eigenpairs descending by eigenvalue. Flip each loading vector so the earliest maximum-absolute loading is positive.
- Scores equal standardized rows times oriented loadings.

K-means:

- Use squared Euclidean distance unless the profile says otherwise.
- Farthest-first initialization starts from the smallest entity id or ASCII-first entity, then repeatedly chooses the point farthest from its nearest center, tied by entity id.
- Assign ties to the lower cluster id.
- Update by arithmetic centroid means until labels stop changing or the cap is reached.
- If segment labels are semantic, order final clusters by the requested burden or centroid coordinate rule before naming them.

Adjusted Rand index:

- Build the contingency table between two labelings on the common retained entities.
- `ARI = (sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2)+sum_j C(b_j,2)) - expected)`.
- `expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)`.
- If the denominator is zero, return `1` only for identical trivial labelings, otherwise `0`.

Silhouette:

- Use Euclidean distance on the retained score vectors.
- Singleton clusters have silhouette `0`.
- Select the largest unrounded mean silhouette, tied by smaller cluster count unless overridden.

## Source Perturbation

- Resolve alternate source records with the module's effective filters and release priority.
- Keep the analytic design, weights, and cohort fixed unless the module says to rebuild them.
- Exhaustive replacement masks use the registered entity order. Bit `j` replaces entity `j`.
- Percent shift is `100*abs((b_alt-b_base)/b_base)` unless overridden.
- Exact Shapley effect for ordered entity `j` is the factorial-weighted average marginal coefficient change across all subsets not containing `j`; preserve signed effects and verify their sum equals all-replacement minus no-replacement.
