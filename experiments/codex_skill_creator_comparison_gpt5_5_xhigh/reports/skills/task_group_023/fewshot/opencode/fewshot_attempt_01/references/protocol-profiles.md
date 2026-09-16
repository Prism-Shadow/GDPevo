# PHO Protocol Profiles

These profiles carry reusable method semantics only. Bind all variables, entities, years, sources, random seeds, grids, cutoffs, output names, enum values, and list orders from the active request/template.

## Effective Request Resolution

For PHO protocol tasks, resolve one effective contract before fetching evidence, folding, fitting, random draws, aggregation, or decisions.

- Exact `protocol_id` matching controls profile activation. Similar names or family membership are not enough.
- Direct root key `k` targets canonical root `k`; inside a named section or module, direct child `k` targets the identical child path.
- A root `<section>_overrides` targets canonical `<section>` after stripping only the terminal suffix. `module_overrides.<module>` targets that exact top-level module.
- Objects deep-merge recursively. Arrays replace whole arrays. Scalars, strings, booleans, and null replace only their exact path. Absent paths inherit unchanged.
- Reject unresolved targets, inferred aliases, positional array patches, array concatenation, key renames, and incompatible type coercions.

## Common Numerical Rules

- OLS/WLS designs keep columns in declared order. Include an intercept only when the request/template declares one.
- HC3 for WLS: with `Xw=sqrt(w)X`, `ew=sqrt(w)(y-Xb)`, and leverage `h_i=diag(Xw (Xw'Xw)^-1 Xw')`, use `(Xw'Xw)^-1 Xw' diag(ew_i^2/(1-h_i)^2) Xw (Xw'Xw)^-1`.
- CR1 by cluster: with ordered cluster scores `s_g=X_g'e_g`, use `[G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g(s_g s_g') * (X'X)^-1`; use the weighted `Xw, ew` analog for WLS.
- Jackknife: for `G` delete estimates `b_-g` and mean `bbar`, `SE=sqrt((G-1)/G * sum((b_-g-bbar)^2))` and `b_BC=G*b_full-(G-1)*bbar`.
- Two-sided t tests use the active cluster or residual degrees of freedom.
- Conformal intervals are inclusive.
- For all random modules, maintain one continuous generator and record checkpoints after the completed replicate requested.

## `PHO_STATE_TRANSPORT_AUDIT_V1`

Typical modules: release/cohort audit, two-way fixed effects delete-cluster jackknife, nested leave-one-division ridge, PCG32/Webb wild cluster bootstrap, grouped split conformal ridge, trajectory PCA clustering, source-year perturbation, controlled decision.

### Release And Cohorts

Resolve health and socioeconomic series independently from active filters. Construct complete, balanced, broad reference, or strict dual-source cohorts from the exact fields in the request. Preserve entity-code then year order and every declared feature/group order.

### Two-Way Fixed Effects Jackknife

For every full or delete-cluster refit, double-demean each modeled variable:

```text
z_it - entity_mean(z)_i - time_mean(z)_t + grand_mean(z)
```

Fit OLS without intercept in declared predictor order. A deletion removes the whole cluster/entity, recomputes all means, and refits from scratch. Select minimum/maximum delete coefficients by unrounded coefficient, then entity code if needed.

### Nested Ridge By Division

Hold out one ordered division per outer fold. Within each outer training set, hold out each remaining division once in the same order. Standardize features with training arithmetic means and sample standard deviations (`ddof=1`) and center the training outcome; keep the intercept unpenalized. Minimize:

```text
mean((y - a - Xb)^2) + lambda * sum(b_j^2)
```

Coordinate update:

```text
b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n * lambda)
```

Pool all row-level inner validation squared errors before RMSE. Select smallest unrounded RMSE, then smaller penalty. Refit on all outer-training rows and pool exactly one outer prediction per eligible row.

### PCG32 Webb Wild Cluster Bootstrap

Use the fixed-effects double-demeaned matrix. Fit full and restricted models, studentize the full target coefficient with CR1, then generate `y* = restricted_fit + restricted_residual * cluster_weight`.

PCG32 uses a 64-bit state, `increment=2*stream+1`, multiplier `6364136223846793005`, rotate-right 32-bit output, and maps output modulo six to Webb weights in this order:

```text
[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]
```

Draw one weight per cluster in entity-code order per replicate. Count `abs(t*) >= abs(t_observed)`, use plus-one p-value, and nearest-rank quantiles.

### Grouped Split Conformal Ridge

For each ordered outer group, use it as test. Among remaining groups, choose calibration by greatest row count then ascending group name; all others are proper training. Fit ridge from scratch with the fixed penalty and training-only scaling. Sort absolute calibration residuals and use one-based rank:

```text
r = min(m, ceil((m + 1) * (1 - alpha)))
```

Aggregate coverage and width by outer-test row counts.

### Trajectory PCA And Clustering

Build columns in declared variable-major/time order. Standardize columns by active sample standard deviation and form `C=Z'Z/(n-1)`. Use deterministic eigendecomposition, sort descending, and orient each loading so the earliest maximum-absolute entry is positive. Scores are `Z` times oriented loadings.

Run squared-Euclidean farthest-first k-means on leading scores: first center is ASCII-first entity, later centers maximize distance to nearest center with entity-code tie-breaks. Assign ties to lower working id, update by means, stop on unchanged labels or cap, then canonicalize final IDs as the protocol declares. Rebuild the entire PCA/clustering pipeline for each leave-year stability fit and compute ARI.

### Source-Year Perturbation

Enumerate time subsets by increasing requested subset size and lexicographic tuple order. Keep the strict analytic set unchanged. For each subset, refit the complete double-demeaned model separately for primary and parallel series, recomputing CR1 and inference. Relative shift is `abs(b_alt-b)/abs(b)*100`; same sign requires both nonzero with identical sign. Median is the ordinary median of ordered shifts. Worst subset is greatest unrounded shift, then earlier subset order.

## `PHO_COUNTY_MEDIATION_TRANSPORT_V1`

Typical modules: publication/cohort audit, primary mediation OLS models, difference GMM mediation, nested state ridge, paired state wild bootstrap, state-grouped conformal, partial-R2 sensitivity, state trajectory PCA, controlled precedence.

### Publication And Cohorts

Filter each source by the active request. Select one record per entity-time-measure key using declared release priority. Construct primary, balanced-panel, and machine-learning cohorts from effective nonmissing predicates. Suppressed/null selected health records count as selected publications but fail analytic completeness.

### Mediation And Difference GMM

Build total-effect, path-a, direct/path-b OLS designs from active exposure, mediator, outcome, controls, transformations, references, and column order. Use unrounded fitted objects downstream.

For difference GMM, create adjacent-change rows in entity then end-period order. For each equation use:

```text
W = (Z'Z)^-1
beta = (X'Z W Z'X)^-1 X'Z W Z'y
```

With residual `u`, cluster score `q_g=Z_g'u_g`, and cross-equation score products, compute finite-sample cluster sandwich covariance. For indirect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`. Compute first-stage partial F from full-vs-reduced RSS. Delete-state diagnostics rebuild rows and refit from scratch.

### Nested State Ridge

Use active feature arrays in exact order. Standardize from training arithmetic means and population standard deviations, using divisor one for zero variance. Fit ridge with unpenalized intercept by minimizing training SSE plus `lambda * ||beta||^2`. Outer validation leaves one state out; inner validation leaves one remaining state out. Pool county squared errors before RMSE. Select smallest unrounded RMSE, then smaller penalty.

### Paired State Wild Bootstrap

For each target equation, fit the restricted model with only that target removed. Synthetic outcomes use restricted fitted values plus state-weighted restricted residuals. Use unsigned xorshift32 with shifts 13, 17, 5 and 32-bit masking. Draw once per state in ascending order per replicate; odd maps to `+1`, even to `-1`. Reuse the same state signs across paired equations. Use absolute exceedances, plus-one p-values, nearest-rank order statistics, and bootstrap-t inversion with observed standard error.

### State-Grouped Conformal

Index states in ascending order and assign cyclic partitions by index modulo the active partition count. For each test partition, use the registered preceding calibration partition and remaining partitions for proper training. Reduce calibration residuals to one maximum absolute residual per calibration state; use `k=min(m,ceil((m+1)*coverage))`. Aggregate county coverage/width by cycle and state.

### Partial-R2 Sensitivity

From unrounded baseline `a`, `b`, `SE_b`, and residual `df`, compute:

```text
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
adjusted_b = b - sign * magnitude
adjusted_indirect = a * adjusted_b
adjusted_direct = total - adjusted_indirect
proportion = adjusted_indirect / total
```

Enumerate the full active R2 surface in declared R2 and direction order. Compute tipping roots from unrounded inputs.

## Country Burden Revision Audits

This family uses requested country labels, burden indicators, revisions, PCA/clustering, and a region-adjusted life-expectancy panel model.

1. Reconcile labels to unique `iso3` values using canonical names, portal labels, and alternate labels.
2. Select final country indicator records by active release/revision policy. Use revision notices to distinguish applied from non-applied events; pending, withdrawn, or non-applied notices do not authorize value replacement.
3. Track raw missing cells before quality/anomaly exclusions. Track unresolved scale-break/anomaly observation keys as `ISO3|YEAR|indicator_id` in sorted order when requested; count reference-year anomalies separately if the template asks.
4. Build the reference-year burden matrix over requested indicators. Exclude or impute exactly as required by the active template; when imputation is requested, compute it from active evidence only and report imputed cell counts.
5. Standardize indicators before PCA. Orient PC1 so higher PC1 means greater burden when the requested burden indicators are unfavorable. Report top absolute loadings by descending absolute value, breaking exact ties by indicator id.
6. Cluster countries using deterministic k-means on retained burden scores. For candidate k values, compute Euclidean silhouette with singleton silhouette zero; choose the highest unrounded silhouette, then smaller k.
7. Fit the panel model using active country-year observations, life expectancy as outcome, PC1 burden as predictor, and requested region fixed effects. Decide the advisory from the active business rule using unrounded coefficient and p-value.

## `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`

Typical modules: weighted release/cohort, cluster jackknife, nested weighted elastic-net, xorshift32 wild cluster bootstrap, grouped conformal, trajectory PCA clustering, exhaustive direct-vs-rollup source perturbation, controlled decision.

### Weighted Linear Algebra

For WLS, form `Xw=sqrt(w)X` and `yw=sqrt(w)y`, then solve in declared column order. HC3 and CR1 use the weighted formulas in the common numerical rules. Unless overridden, keep the selected direct outcome sample size as the fixed positive reliability weight even when replacing the outcome source.

### Cluster Jackknife

Fit the full weighted design. Delete every registered cluster in order and refit the unchanged design from scratch. Percent change is `100*abs((b_delete-b_full)/b_full)`. Maximum influence ties use earlier cluster order. The jackknife test uses `b_BC/SE_JK`.

### Nested Weighted Elastic-Net

Hold out each registered cluster as outer fold and each remaining cluster as ordered inner fold. Build raw, transformed, squared, and interaction features in declared order.

Inside every fit, compute training-only weighted means and weighted population SDs for features, center `y` by its weighted training mean, and minimize:

```text
sum_i w_i*(y_i - Z_i b)^2/(2*sum_i w_i)
  + lambda * (alpha * sum_j |b_j| + (1-alpha) * sum_j b_j^2 / 2)
```

Cold-start every penalty/fold. Cyclic update:

```text
rho_j = sum_i w_i * Z_ij * residual_without_j / sum_i w_i
b_j = soft_threshold(rho_j, lambda*alpha) / (1 + lambda*(1-alpha))
```

Pool unweighted inner validation squared errors by row before RMSE. Select by smallest unrounded RMSE, then smaller penalty. Pool outer predictions in entity order.

### Xorshift32 Wild Bootstrap

Studentize the full weighted target coefficient with cluster CR1. Fit the weighted restricted model without target; use untransformed fitted values/residuals in entity order. Initialize unsigned xorshift32 from the active seed. Each call applies shifts 13, 17, 5 with 32-bit masking. Draw clusters in registered order; low bit one maps to `+1`, otherwise `-1`. Type-seven quantiles may be required; bind quantile type from the protocol text.

### Grouped Conformal

Reuse each outer center prediction and selected penalty. For each held-out cluster, calibrate by holding out each other training cluster once, cold-refitting the identical weighted elastic-net on remaining clusters, and pooling absolute residuals. Rank is `ceil((m+1)*coverage)` capped at `m`. Choose worst coverage by smallest fraction then earlier cluster order.

### Exhaustive Source Perturbation

Resolve alternate outcome source records using the active replacement filters and release precedence. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. For every mask from zero through `2^m-1`, replace entity `j` iff bit `j` is set; retain fixed direct reliability weights and design. Refit WLS and HC3 for every scenario.

Aggregate by replacement count. Relative shift is `100*abs((b_mask-b_zero)/b_zero)`. Maximum shift ties use smaller mask. Exact Shapley effect for ordered entity `j`:

```text
phi_j = sum_{S not containing j} |S|!*(m-|S|-1)!/m! * (b(S union {j}) - b(S))
```

Verify `sum(phi) = b(all replacements) - b(no replacements)` within numerical tolerance.

## `PHO_COUNTY_PANEL_TRANSPORT_V1`

Typical modules: publication balanced panel, delete-state two-step GMM, state-blocked nested elastic-net, state wild bootstrap, cross-fold grouped conformal, county trajectory PCA clustering, source-group perturbation, controlled decision.

### Publication Balanced Panel

Filter county health and socioeconomic sources independently. Resolve final records by active release priority. Treat suppressed, invalid, or missing selected values as incomplete. Retain only counties complete across all active balanced years with valid geography attributes. Create adjacent-change rows ordered by entity identifier then end period. Derive lagged levels, changes, indicators, and interactions in declared order.

### Delete-State Two-Step GMM

Within every full or delete-state fit, residualize outcome, dynamic regressors, and instruments against intercept plus active baseline terms. First-step moments use identity weight. Build state scores `s_g=Z_g'u_g`, `S=sum_g(s_g s_g')/n`, and second-step weight as the Moore-Penrose inverse of `S` with the active relative singular-value cutoff. Compute second-step coefficients and `Hansen J=n*g(theta)'Wg(theta)`. Refit both steps after each state deletion; bias-correct with the jackknife formula and retain maximum absolute delete-state shifts.

### State-Blocked Nested Elastic-Net

Allocate states by descending retained-entity counts, assigning each to the currently smallest fold and using lower fold id on equality; sort state codes within folds. Repeat allocation inside each outer-training set. Standardize declared continuous columns from training population moments, leave indicators unchanged, and keep intercept unpenalized.

Minimize:

```text
SSE/(2n) + alpha * (rho * sum|beta_j| + 0.5*(1-rho)*sum beta_j^2)
```

Cold-start coefficients at zero and intercept at training outcome mean. In each sweep update intercept by mean residual, then:

```text
beta_j = soft_threshold(mean(x_j*r_partial), alpha*rho) /
         (mean(x_j^2) + alpha*(1-rho))
```

Traverse candidate grid in declared order. Pool inner squared errors before RMSE. Select by smallest unrounded RMSE, then smaller alpha, then smaller l1 ratio.

### State Wild Bootstrap

Fit full unpenalized OLS and state-cluster CR1 for the target. Fit the restricted model without target. Use unsigned xorshift32, drawing states in ascending order; odd maps to `+1`, even to `-1`. Use absolute-tail exceedances, plus-one p-values, and nearest-rank order statistics at active probabilities. Checkpoints are after completed replicates.

### Cross-Fold Grouped Conformal

Use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. Rank is `min(m, ceil((m+1)*coverage))`. Report fold, state, RUCC-band, and prediction-bin diagnostics. Prediction bins are assigned after sorting by prediction and declared identifiers; signed gap is prediction mean minus observation mean.

### County Trajectory PCA And Clustering

Build variable-major entity trajectories in declared variable and end-period order. Standardize each feature by population moments and use covariance `Z'Z/n`. Sort eigenpairs descending and orient each loading so its earliest maximum-absolute element is positive. For each candidate k, initialize with smallest entity id, then farthest-first with entity-id tie-breaks; equality assigns to lower cluster id. Compute Euclidean silhouette with singleton zero; select largest unrounded mean silhouette, then smaller k. For each state deletion, rebuild the full trajectory pipeline at selected k and compare retained labels with ARI.

### Source-Group Perturbation

For each source group and outer fold in declared order, remove exactly the group terms and reuse that fold's full-model selected hyperparameters without retuning. Apply the same remaining-term preprocessing/solver, retain all outer-fold RMSEs, pool squared errors, and subtract full-model OOF RMSE for deterioration. Count worse folds. Rank groups by decreasing unrounded deterioration, then declared group order.
