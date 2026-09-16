# Computation Reference

Use this file for PHO portal calculations. The request and answer template always control final field names, precision, order, and predicates.

## Portal Data Handling

- Fetch `/catalog` and `/methodology` first. Prefer `/download` when it gives a complete snapshot; otherwise query the specific `/data/...` and `/geographies/...` endpoints.
- Parse records with stable typed parsers. Normalize numbers only after checking suppression, validity, blank strings, and nulls.
- Resolve records independently per source family before joining. Use the request's release status, value type, source type, revision priority, release timestamp priority, record-id tie rule, geography scope, and measure/field list.
- Build complete-case, balanced-panel, broad reference, strict dual-source, machine-learning, or primary cohorts exactly from the effective predicates. Preserve requested entity order for aligned arrays and use set-like sorted order only when the template says so.
- Keep a reproducibility table for every ordered entity, fold, cluster, year subset, source group, and random checkpoint. Most PHO templates require complete diagnostic arrays.

## Numeric Discipline

- Keep full double precision internally. Round only when emitting JSON.
- Evaluate gates and tie-breaks on unrounded values.
- Use natural JSON integer and Boolean types. Use JSON `null` for unavailable mathematical results; never emit `NaN` or `Infinity`.
- For confidence intervals, use the effective Student-t degrees of freedom unless the request/methodology specifies normal inference.

## Linear Models

OLS:

- Use the declared column order.
- Include or omit intercept exactly as declared.
- Solve by numerically stable least squares or pseudoinverse only when the method permits it.

Two-way fixed effects:

- For each active refit, transform `z_it` to `z_it - entity_mean_i - time_mean_t + grand_mean`.
- Fit OLS without intercept on transformed variables.
- Deletions remove whole clusters and recompute all means from scratch.

WLS:

- For positive weights `w`, set `Xw = sqrt(w) * X` and `yw = sqrt(w) * y`.
- Fit `b = (Xw'Xw)^-1 Xw'yw` in declared order.
- Reuse fixed reliability weights during source perturbations when the protocol says so.

HC3:

- Compute leverage from the weighted design when WLS is active.
- With weighted residual `ew_i = sqrt(w_i) * (y_i - X_i b)`, use  
  `V = (Xw'Xw)^-1 Xw' diag(ew_i^2/(1-h_i)^2) Xw (Xw'Xw)^-1`.
- Use two-sided Student-t inference with `n-k` df unless overridden.

CR1 cluster covariance:

- For ordered clusters `g`, scores are `s_g = X_g' e_g` for OLS or `Xw_g' ew_g` for WLS.
- Use `V = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g(s_g s_g') * (X'X)^-1`, with weighted matrices for WLS.
- Use two-sided Student-t inference with `G-1` df unless overridden.

Delete-cluster jackknife:

- Refit from scratch for every cluster deletion in registered order.
- With full coefficient `b`, delete estimates `b_g`, `bbar=mean(b_g)`, and `G` clusters:  
  `se = sqrt((G-1)/G * sum((b_g-bbar)^2))` and `bias_corrected = G*b - (G-1)*bbar`.
- Percent shift is `100*abs((b_g-b)/b)` unless the request defines another denominator.

## GMM

Difference GMM mediation:

- Create adjacent-change rows in entity then end-period order.
- Bind instruments and equations from the request.
- Use `W=(Z'Z)^-1` when specified, and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- Build cluster scores from `Z_g'u_g`; use cross-cluster score products for cross-equation covariance.
- For indirect effect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`.

Two-step linear GMM:

- Residualize outcome, regressors, and instruments against declared baseline terms before fitting dynamic coefficients.
- First-step moments use identity weight unless overridden.
- For second step, build `S=sum_g(s_g s_g')/n`, apply the registered Moore-Penrose inverse and relative singular-value cutoff, then compute `theta` from weighted linear moments.
- Hansen `J = n * g(theta)' W g(theta)`.
- Refit both steps after each delete-state operation.

## Ridge And Elastic Net

Ridge:

- Use the exact feature order. Keep the intercept unpenalized.
- Standardize using training-only moments for every fold. Use sample SD or population SD according to the profile; if variance is zero, use a unit divisor.
- Center `y` only when the profile says to. Apply training moments to validation/test rows.
- Select the penalty by pooled row-level inner validation squared errors, not by averaging fold RMSEs. Tie to the smaller penalty.

Elastic net:

- Traverse candidates in declared grid order.
- Cold-start every fold/penalty unless the request explicitly allows warm-starting.
- Keep the intercept unpenalized.
- Use soft-threshold coordinate updates with the objective scaling stated in the profile.
- Count nonzero terms only after applying the effective numerical cutoff.
- Pool outer predictions so each eligible row contributes exactly one OOF prediction.

## PRNG And Wild Bootstrap

Unsigned xorshift32:

```text
x ^= (x << 13); x &= 0xffffffff
x ^= (x >> 17); x &= 0xffffffff
x ^= (x << 5);  x &= 0xffffffff
```

- Maintain one continuous stream.
- Draw clusters in the registered order for each replicate.
- Map odd state to `+1` and even state to `-1`.
- Record checkpoints only after the full replicate refit and statistic are complete.

PCG32/Webb:

- Use 64-bit unsigned wraparound. Set `increment = 2*stream + 1`; initialize `state = 0`, advance once, add the seed modulo `2^64`, and advance once more. Each advance sets `old = state`, `state = old*6364136223846793005 + increment mod 2^64`, `xorshifted = low32(((old >> 18) xor old) >> 27)`, `rot = old >> 59`, and output is `rotate_right_32(xorshifted, rot)`.
- Map output modulo six to Webb weights in order: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Maintain one continuous stream and draw once per cluster in entity-code order.

Bootstrap inference:

- Fit the restricted-null model without the target when specified.
- Generate `y* = restricted_fit + restricted_residual * cluster_weight`.
- Refit the full model and recompute the registered standard error each replicate.
- Use plus-one p-values: `(exceedance_count + 1) / (B + 1)`.
- For nearest-rank quantiles, sort values and use one-based rank `min(B, ceil(p*B))`, returning `x[rank-1]`.
- For type-seven quantiles, use `h=(B-1)*p`, `j=floor(h)`, `gamma=h-j`, and linear interpolation between zero-based `x[j]` and `x[j+1]`.

## Conformal Calibration

- Use the prediction source declared by the request, usually outer OOF predictions.
- Build absolute calibration residuals from rows or from group maxima according to the protocol.
- With miscoverage `alpha`, use rank `min(m, ceil((m+1)*(1-alpha)))` and select `score[rank-1]`.
- With nominal coverage `c`, use rank `min(m, ceil((m+1)*c))` and select `score[rank-1]`.
- Intervals are symmetric and inclusive: `[prediction - q, prediction + q]`.
- Aggregate coverage and width with the row or group weights declared by the template.
- Choose worst groups by unrounded coverage/error criteria and the registered tie order.

## PCA, K-Means, Silhouette, ARI

PCA:

- Build columns in the declared variable/time order.
- Standardize using the active sample and the profile's sample or population SD.
- Use covariance `Z'Z/(n-1)` or `Z'Z/n` as specified.
- Sort eigenpairs by descending eigenvalue. Orient each loading so the earliest maximum-absolute entry is positive, unless a burden-direction rule requires a different sign.
- Scores equal `Z` times oriented loadings.

Deterministic k-means:

- Use squared Euclidean distance for fitting.
- Initialize the first center from the profile's smallest/ASCII-first entity rule.
- Add each next center as the entity farthest from its nearest center; break ties by entity id.
- Assign ties to the lower cluster id.
- Update centroids by arithmetic means and stop when assignments are unchanged or the cap is reached.
- Canonicalize cluster labels only as the protocol requires; otherwise preserve working ids.

Silhouette:

- Use Euclidean distances.
- Singleton clusters have silhouette zero.
- Select the largest unrounded mean silhouette; tie to the smaller `k` unless overridden.

Adjusted Rand index:

- Build the contingency table between full and refit labels over retained entities.
- Use  
  `(sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2)+sum_j C(b_j,2)) - expected)`  
  with `expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)`.
- When reporting aligned changes or agreement, choose the label permutation with maximum matches, tied lexicographically.

## Perturbation And Shapley

Source-year subsets:

- Enumerate subset sizes in declared order, then lexicographic tuple order.
- Keep the strict cohort fixed unless the request explicitly says to rebuild it.
- Refit every subset from scratch and recompute inference.

Source replacement masks:

- Order replaceable entities by the protocol's disagreement order.
- Enumerate masks from `0` through `2^m - 1`.
- For entity index `j`, replace the source when `mask & (1 << j)` is nonzero.
- Summarize by replacement count/popcount in ascending order.
- Select maximum shifts using unrounded values and the protocol tie rule.

Exact Shapley:

- For ordered entity `j`, compute  
  `phi_j = sum_{S not containing j} |S|!*(m-|S|-1)!/m! * (b(S union {j}) - b(S))`.
- Preserve signed effects in ordered entity order.
- Verify the Shapley sum equals all-replacement minus no-replacement coefficient within numerical tolerance.

Source-group deletion:

- Remove exactly the declared terms for each group.
- Reuse selected full-model hyperparameters if the request says no retuning.
- Pool fold RMSEs from row-level squared errors, subtract the full-model OOF RMSE for deterioration, count worse folds, and rank by decreasing unrounded deterioration then declared group order.

## Controlled Decisions

- Complete every module first, even if an early gate appears to fail.
- Evaluate all predicates on unrounded values.
- Preserve gate order in any reported audit fields.
- Use only the controlled conclusion values supplied by the effective request/template.
