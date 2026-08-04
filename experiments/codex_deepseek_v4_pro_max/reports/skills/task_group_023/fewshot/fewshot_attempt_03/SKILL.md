---
name: pho-algorithmic-audit
description: Execute registered algorithmic transportability audits for the Public Health Observatory. Use when a request requires reproducible statistical evidence from the PHO portal using controlled publication gates, cohort resolution, and decision rules. Covers state-level, county-level, and country-level audit protocols.
---

# Public Health Observatory — Algorithmic Transportability Audit

Complete six-to-nine-module registered audits against the read-only PHO Web portal. Resolve publication releases, construct evidence cohorts, execute every declared statistical module with exact reproducibility, and apply controlled decision gates.

## Portal Access

Set `PHO_BASE_URL` from the task environment (do not hardcode). Allowed endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Portal metadata and version |
| GET | `/catalog` | Available datasets, measures, and fields |
| GET | `/geographies/states` | State codes, names, divisions, regions |
| GET | `/geographies/counties` | County FIPS, names, states, RUCC codes |
| GET | `/geographies/countries` | Country codes (ISO3), names, regions |
| GET | `/data/state-health` | State-level health measures by year |
| GET | `/data/state-socioeconomic` | State-level socioeconomic indicators |
| GET | `/data/county-health` | County-level health measures by year |
| GET | `/data/county-socioeconomic` | County-level socioeconomic indicators |
| GET | `/data/country-indicators` | Country-level burden and health indicators |
| GET | `/data/revisions` | Revision history for publication records |
| GET | `/methodology` | Methodological notes |
| GET | `/download` | CSV export with `?dataset=<name>&format=csv` |

Dataset endpoints support `?page=N&page_size=M` pagination. Use the exact query strings accepted by the portal; all query parameters are documented in the catalog response.

## General Workflow

1. **Resolve the effective request**: Deep-merge the analysis request with any inherited protocol defaults using the override rules below. Freeze one effective contract before any data access.
2. **Fetch and resolve evidence**: Query portal endpoints for all declared measures, fields, geographies, and years. Select the correct publication record per entity-time-measure using the declared revision priority.
3. **Construct cohorts**: Apply completeness filters to build primary, balanced, broad, and strict analytic sets.
4. **Execute modules in registered order**: Every module uses only data from its declared cohort and applies exact method specifications.
5. **Apply decision rules**: Evaluate every gate predicate on unrounded values, count passes, and select the controlled classification.
6. **Format output**: Conform exactly to the declared answer template, preserving list order, numeric precision, identifier codes, and enum values.

## Request Override Resolution

When a portable protocol profile is activated (exact `protocol_id` match), resolve overrides before computation:

- **Direct keys**: A root key in the request binds to the identically named canonical key.
- **Suffix aliases**: `section_overrides` binds to canonical `section`; `module_overrides.<name>` binds to `modules.<name>`; `reporting_overrides` binds to `reporting`.
- **Objects**: Deep-merge recursively by exact key.
- **Arrays**: Replace the entire array; never concatenate, union, or merge by position.
- **Scalars/strings/booleans/null**: Replace only at the exact path.
- **Absent paths**: Inherit from protocol defaults unchanged.
- **Reject**: Unknown targets, implicit renames, type coercion, and positional array patches.
- **Task-local bindings and resolved overrides** take precedence over inherited values at the same path.

## Instance Boundary

All protocols are classified `REUSABLE_METHOD_ONLY`. Never carry task-local or solved analytical values across invocations. Recompute everything from the future request and authorized portal evidence. Task-local fields include: entities, measures, calendar scope, geography, source filters, random seeds, hyperparameter grids, business cutoffs, and output vocabulary.

## Protocol Family: PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1

Covers state-level audits of whether an exposure is a transportable signal for an outcome across U.S. states (plus DC). Protocols in this family: `PHO_STATE_TRANSPORT_AUDIT_V1`, `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

### Module: Release Resolution and Cohorts

**Publication selection**: For each declared health or socioeconomic measure, filter portal records by effective status, source type, value type, validity, and geography bindings. From matching records select one per entity-time-measure key using the declared ordered priority: greatest revision number, then latest release timestamp, then lowest record/observation identifier.

**Completeness**: Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and never zero-filled. Count selected publications before completeness exclusions when requested.

**Cohort construction**: Join independently resolved series by stable entity and time keys. Build each cohort from its effective required fields:
- **Primary/reference-year cohort**: Complete cases for the reference year on outcome, exposure, and required adjustments.
- **Core balanced cohort**: Complete cases in every analysis year for core panel variables.
- **Broad reference cohort**: Reference-year complete cases for outcome and all ordered ridge features.
- **Strict dual-source cohort**: Complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.

Preserve entity-code then time order, and preserve every declared feature, group, and cluster order.

### Module: Delete-Cluster Fixed Effects (Two-Way FE with Jackknife)

**Transform**: For every active refit, transform each modeled variable as `z_it - entity_mean - time_mean + grand_mean` (double-demeaning). A deletion removes the whole cluster, recomputes every mean, and refits from scratch in entity-code order.

**Fit**: Solve OLS without an intercept in declared predictor order using the double-demeaned matrix.

**Jackknife inference**: For `G` delete estimates `b_-g` and mean `b_bar`:
```
SE_JK = sqrt((G-1)/G * sum_g (b_-g - b_bar)^2)
b_BC  = G*b - (G-1)*b_bar
t     = b_BC / SE_JK
```
Test two-sided with Student-t and `G-1` degrees of freedom. Select extrema by coefficient value, then entity code.

### Module: Nested Ridge with Grouped Cross-Validation

**Folds**: Hold out one ordered group per outer fold. Within each outer training set, hold out each remaining group once as inner validation in the same order.

**Scaling**: For every fit, subtract training-only feature means and divide by training sample standard deviation (ddof=1). For zero variance, use unit divisor. Apply training moments to validation/test rows.

**Solver**: Center the training outcome. Keep the intercept unpenalized. Initialize coefficients to zero. Cycle in declared feature order minimizing:
```
mean((y - alpha - X*beta)^2) + lambda * sum_j beta_j^2
```
Update `beta_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n*lambda)` where `r` excludes feature `j`. Stop after a full sweep when max coefficient change is below the effective solver tolerance or at the effective sweep cap.

**Selection**: For each lambda, pool all inner validation squared errors at row level and take RMSE (not the mean of fold RMSEs). Choose the smallest RMSE, breaking ties toward the smaller penalty. Refit on all outer-training rows and predict every outer row.

**Aggregation**: Pool exactly one outer prediction per eligible row. Report:
```
pooled_RMSE = sqrt(sum_i (y_i - y_hat_i)^2 / n)
pooled_MAE  = sum_i |y_i - y_hat_i| / n
pooled_Q2   = 1 - SSE / SST  (where SST uses full-sample outcome mean)
```

### Module: Wild Cluster Bootstrap-t (PCG32/Webb Weights)

**Observed fit**: Use the same double-demeaned matrix as the FE module. For cluster scores `s_g = X_g' e_g`:
```
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^(-1) * sum_g (s_g s_g') * (X'X)^(-1)
```
Studentize the full target coefficient: `t_obs = beta_target / SE_CR1`.

**Restricted model**: Fit without the target variable. Retain restricted fitted values and residuals.

**PRNG - PCG32**: Use unsigned wraparound with 64-bit state and 32-bit output. Let increment = `2*stream + 1`. Initialize state to zero, advance, add effective initialization value modulo 2^64, and advance. Each advance: `old = state; state = old * 6364136223846793005 + increment (mod 2^64); xorshifted = low32(((old >> 18) ^ old) >> 27); rot = old >> 59; output = rotate_right_32(xorshifted, rot)`. Map output modulo six to weights: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.

**Draw and refit**: Maintain one continuous generator. For every replicate draw once per cluster in entity-code order. Set `y* = restricted_fit + restricted_residual * cluster_weight`. Refit the unrestricted model, recompute CR1, and studentize.

**Test**: Count `abs(t*) >= abs(t_obs)` and report `p = (1 + count) / (1 + B)`. Aggregate consecutive replicate batches exactly as bound. For sorted values `x` and probability `p`, nearest-rank output is `x[min(B, ceil(p*B)) - 1]` (one-based rank).

### Alternative PRNG - XorShift32

Initialize one unsigned 32-bit state from the effective random binding. Each next call: `x ^= x << 13; x ^= x >> 17; x ^= x << 5`, truncating to unsigned 32 bits after every xor. Map the low bit: odd gives +1, even gives -1. Maintain one continuous stream across all replicates.

### Module: Grouped Split Conformal (Ridge)

**Partition**: For each ordered outer group, use it as test. Among remaining groups, choose calibration by greatest row count then ascending group name; all others form proper training.

**Fit**: Fit ridge from scratch with the effective fixed penalty and the identical training-only scaling and solver rules. Predict calibration and test rows. Pool absolute calibration residuals.

**Interval construction**: Sort `m` absolute calibration scores. With miscoverage `alpha`, use `r = min(m, ceil((m+1) * (1-alpha)))` and radius `q = score[r]` (one-based). Intervals `prediction +/- q` are inclusive.

**Aggregation**: Report fold coverage, width, and MAE. Aggregate coverage and width by outer-test row counts. Choose worst coverage by smallest fraction, then earlier cluster order.

### Module: Trajectory PCA Clustering

**PCA**: Build columns in effective variable-major/time order. Standardize each column by active-sample sample standard deviation. Form `C = Z'Z / (n-1)`.

**Eigendecomposition - symmetric Jacobi**: Select the largest absolute upper-triangle off-diagonal, tying by lower row then column. Compute `tau = (Aqq - App) / (2*Apq)`, `t = sign_nonnegative(tau) / (|tau| + sqrt(1+tau^2))`, `c = 1/sqrt(1+t^2)`, `s = t*c`. Rotate A and eigenvectors. Stop at the effective off-diagonal tolerance or step cap.

**Component ordering**: Sort by descending eigenvalue, then original diagonal index. Flip each loading so the earliest maximum-absolute entry is positive. Scores = `Z * loadings`.

**Clustering - farthest-first k-means**: Use squared Euclidean distance on effective leading scores. First center is the ASCII-first entity. Each next center is the entity maximizing distance to its nearest center, tying by entity code. Assign to nearest center, tying by lower working id. Update by member means. Stop when assignments are unchanged or at the effective cap. Canonicalize final ids by centroid coordinates then working id.

**Stability - leave-time-out**: For each omitted time block in ascending order, rebuild scaling, PCA, orientation, initialization, and clustering. Compute adjusted Rand index:
```
ARI = (sum_ij C(n_ij,2) - expected) / (0.5 * (sum_i C(a_i,2) + sum_j C(b_j,2)) - expected)
expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)
```
Align refit labels by maximum agreement, tying to the lexicographically smallest permutation.

### Module: Source/Year Perturbation

**Enumeration**: Enumerate effective time subsets by increasing subset size and lexicographic tuple order. Keep the analytic set unchanged.

**Refit**: For each subset, refit the complete model separately with primary and parallel series, recomputing CR1 and two-sided `G-1`-df inference for each fit.

**Aggregation**: For baseline `b` and alternate `b_alt`, shift = `|b_alt - b| / |b| * 100`. Same-sign requires both nonzero with identical sign. Compute ordinary median of ordered shifts. Choose worst by greatest unrounded shift, then earlier subset order.

### Alternative: Exhaustive Source Perturbation (State-level)

**Scenario enumeration**: Resolve alternate outcomes with effective release filters and revision precedence. Order entities by descending absolute alternate-minus-primary difference, tying by entity code. For index `j` and mask from `0` to `2^m - 1`, replace entity `j` iff `mask & (1 << j)` is nonzero. Retain fixed reliability weights and design; refit WLS and HC3.

**Aggregation**: Relative shift = `100 * |b_mask - b_zero| / |b_zero|`. For each popcount stratum, report scenario count, coefficient range, p-value range, and mean shift. Select maximum unrounded shift, tying by smaller mask.

**Shapley effects**: For ordered entity `j`, `phi_j = sum_{S not containing j} |S|! * (m - |S| - 1)! / m! * [b(S U {j}) - b(S)]`. Preserve signed phi order. Verify `sum_j phi_j = b(all) - b(none)` within tolerance.

### Module: Weighted Linear Algebra (for WLS protocols)

**WLS**: For design `X`, outcome `y`, and positive weights `w`:
```
X_w = diag(sqrt(w)) * X
y_w = diag(sqrt(w)) * y
beta = (X_w' X_w)^(-1) X_w' y_w
```

**HC3**: `h_i = diag(X_w (X_w' X_w)^(-1) X_w')`, `ew_i = sqrt(w_i) * (y_i - X_i beta)`:
```
V_HC3 = (X_w' X_w)^(-1) X_w' diag(ew_i^2 / (1-h_i)^2) X_w (X_w' X_w)^(-1)
```
Test two-sided with `n-k` Student-t df.

**CR1 (cluster-robust)**: For ordered clusters `g` and `s_g = X_wg' ew_g`:
```
V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X_w' X_w)^(-1) * sum_g (s_g s_g') * (X_w' X_w)^(-1)
```
Test two-sided with `G-1` Student-t df.

### Module: Nested Elastic Net

**Folds**: Hold out each registered cluster as an outer fold; each remaining cluster as an ordered inner fold. Build effective raw, transformed, squared, and interaction features in declared order.

**Scaling**: Inside every fit compute training-only weighted mean `mu_j` and weighted population SD `sigma_j = sqrt(sum_i w_i*(x_ij-mu_j)^2 / sum_i w_i)`. Standardize training and prediction rows with these moments. Center `y` by its training weighted mean without scaling.

**Objective**: Minimize:
```
sum_i w_i*(y_i - Z_i beta)^2 / (2*sum_i w_i) + lambda * [alpha * sum_j |beta_j| + (1-alpha) * sum_j beta_j^2 / 2]
```

**Solver - coordinate descent**: Cold-start `beta = 0` for every penalty and fold. In cyclic feature order:
```
rho_j = sum_i w_i * Z_ij * (y_i - sum_{l != j} Z_il beta_l) / sum_i w_i
beta_j = S(rho_j, lambda*alpha) / (1 + lambda*(1-alpha))
S(a, t) = sign(a) * max(|a| - t, 0)
```
Stop after a complete cycle when max coefficient change is below effective tolerance or at the effective cycle cap.

**Selection**: Pool unweighted inner validation squared errors across rows and take RMSE (not mean of fold RMSEs). Choose smallest RMSE, then smaller penalty. Cold-refit on all outer-training rows and predict the outer holdout.

**Aggregation**: Pool outer predictions in entity order. Report unweighted RMSE, MAE, and `R2 = 1 - SSE / sum_i (y_i - y_bar)^2` where `y_bar` is the full-sample unweighted mean.

### Module: Grouped Split Conformal (Weighted Elastic Net)

Reuse each outer center prediction and its selected penalty. For outer cluster `d`, hold out each other training cluster once, cold-refit the identical weighted elastic-net algorithm on remaining clusters, predict held-out rows, and pool absolute residuals. Rank construction and aggregation follow the same rank-interval rules as the ridge conformal module.

### Controlled Decision Module

Complete every evidence module first. Evaluate every effective business predicate on unrounded values in the declared precedence order. Count satisfied predicates, and apply the effective request's controlled classification mapping. Select the first applicable class in the effective precedence order.

## Protocol Family: PHO_COUNTY_ALGORITHMIC_TRANSPORT_FAMILY_V1

Covers county-level audits across U.S. counties. Protocols: `PHO_COUNTY_MEDIATION_TRANSPORT_V1`, `PHO_COUNTY_PANEL_TRANSPORT_V1`.

### Module: Publication and Balanced Panel

Filter effective county health and socioeconomic sources independently. Resolve one final record per declared key using effective release priority (highest revision, latest release, lowest record id). Treat suppressed, invalid, or missing values as incomplete, never zero.

For panel designs, create adjacent-change rows ordered by entity identifier then end period. Derive lagged levels, dynamic changes, reference indicators, and interactions in declared order. Retain only entities complete across every effective balanced period with valid geography attributes (RUCC 1-9).

### Module: Difference GMM Mediation

Create adjacent-change rows in entity then end-period order using the effective lag structure. For each equation:
```
W = (Z'Z)^(-1)
beta = (X'Z W Z'X)^(-1) X'Z W Z'y
```
With residual `u` and cluster score `q_g = Z_g' u_g`, use the registered finite-sample cluster sandwich. For two equations, use cross-cluster score products.

**Indirect effect**: `theta = a * b`. Variance: `Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b)`. Student-t inference with cluster degrees of freedom (`G-1`).

**First-stage partial F**: Compute from full-versus-reduced residual sums of squares using effective instrument counts.

**Delete-state diagnostics**: For each state deletion, rebuild rows and refit all affected equations from scratch in state order.

### Module: Delete-State Two-Step GMM (County Panel)

Within every full or delete-state fit, residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms.

**First step**: Moments `g(theta) = Z'(y - D*theta)/n` with identity weight. Build state scores `s_g = Z_g' u_g` and `S = sum_g(s_g s_g')/n`.

**Second step**: Weight `W` is the registered Moore-Penrose inverse of `S`. Compute `theta` from weighted linear moments and Hansen `J = n*g(theta)'W g(theta)`. Apply the registered relative singular-value cutoff to every pseudoinverse.

**Jackknife**: Refit both steps after each state deletion in state order. With `G` clusters: `theta_bc = G*theta_full - (G-1)*mean(theta_delete)`. Retain maximum absolute delete-state shifts.

### Module: Nested State Ridge (County)

Use effective feature arrays in exact order. Within every fit, standardize from training arithmetic means and population standard deviations (unit divisor for zero variance). Apply moments to held-out rows. Fit ridge with unpenalized intercept.

Outer validation leaves one state out; each inner validation leaves one remaining state out. Pool county squared errors before RMSE. Select smallest unrounded inner RMSE, breaking equality toward smaller penalty. Refit on all outer-training rows and retain complete aligned grids and outer diagnostics. Aggregate OOF metrics from the single prediction assigned to every eligible row.

### Module: State-Blocked Nested Elastic Net (County Panel)

Allocate states by descending retained-entity counts, assigning each to the currently smallest fold (lower fold id on equality). Sort state codes within folds; repeat allocation inside each outer-training set.

Within each fit, standardize declared continuous columns from training population moments; leave indicators unchanged. Apply training moments to held-out rows. Keep the intercept unpenalized.

**Objective**: `SSE/(2n) + alpha * (rho * sum|beta_j| + 0.5*(1-rho) * sum beta_j^2)`. Cold-start coefficients at zero and intercept at training outcome mean.

**Solver**: In each cyclic sweep update intercept by mean residual, then `beta_j = S(mean(x_j * r_partial), alpha*rho) / (mean(x_j^2) + alpha*(1-rho))` in declared coefficient order. `S(a,t) = sign(a) * max(|a|-t, 0)`. Stop at registered tolerance or sweep cap.

Traverse the effective (alpha, rho) grid in declared order. Pool inner squared errors before RMSE. Select by smallest unrounded RMSE, then smaller alpha, then smaller rho. Refit outer models and pool OOF metrics.

### Module: Mediation Sensitivity Surface (Partial R2)

From unrounded baseline `a`, `b`, `SE_b`, and residual df:
```
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
adjusted_b = b - s * magnitude          (s = +1 or -1 per declared direction)
adjusted_indirect = a * adjusted_b
adjusted_direct = total - adjusted_indirect
proportion = adjusted_indirect / total
```
Enumerate the complete effective surface in declared R2 and direction order. Compute the equal-strength positive tipping root from unrounded inputs.

### Module: Cross-Fold Grouped Conformal (County)

Use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. With `m` calibration rows, use rank `min(m, ceil((m+1)*coverage))`. Build symmetric inclusive intervals.

Report fold, state, effective rurality-band, and rank-defined prediction-bin diagnostics. Assign prediction bins after sorting by prediction and declared identifiers. Compute signed gap as prediction mean minus observation mean. Use unrounded group coverages for minima and decision predicates; round only reported fields.

### Module: County Trajectory PCA Clustering

Build variable-major entity trajectories in declared variable and end-period order. Standardize each feature by population moments; use covariance `Z'Z/n`.

Sort eigenpairs descending and orient each loading so its earliest maximum-absolute element is positive. Use effective retained scores.

For each effective candidate `k`, initialize at the smallest entity id, then add the point farthest from its nearest center (breaking equality by entity id). Assign equality to lower cluster id. Update arithmetic centers until unchanged labels and registered center tolerance, or the iteration cap.

Compute Euclidean silhouette with singleton value zero. Select largest unrounded mean silhouette, then smaller `k`.

For each state deletion, rebuild the full trajectory pipeline at selected `k` and compare retained labels with adjusted Rand index.

### Module: Source Group Perturbation (County Panel)

For every source group and outer fold in declared order, remove exactly the group terms and reuse that fold's full-model selected hyperparameters without retuning. Apply the same remaining-term preprocessing and solver. Retain all outer-fold RMSEs; pool their squared errors; subtract full-model OOF RMSE for deterioration.

Count folds worse than corresponding full-model folds. Rank groups by decreasing unrounded deterioration, then declared group order.

## Protocol: Country Burden Revision Audit

Covers international country-level burden stratification.

### Module: Label Reconciliation

Resolve every requested country label against the portal's country catalog. Count requested labels, uniquely resolved labels, and labels differing from the canonical country name. Report resolved ISO3 identifiers sorted ascending.

### Module: Quality Audit

Query the revisions endpoint for the declared reference year. Identify APPLIED and non-APPLIED revision events. Cross-reference requested indicators against available data. Flag unresolved scale-break cells as `ISO3|YEAR|indicator_id`. Count raw missing cells, anomaly cells, and imputed cells. Report usable country and indicator counts.

### Module: Burden PCA

Build a country by indicator matrix for the reference year using imputed complete data. Standardize columns. Eigendecompose the covariance matrix. Retain components per Kaiser criterion (eigenvalue > 1) or declared count. Report retained count, PC1 variance fraction, and top absolute loadings.

### Module: Country Clustering

Cluster countries on retained PC scores using k-means at declared `k`. Compute silhouette scores for a range of `k` values (2 through declared `k+2`). Report the silhouette-selected `k`, cluster sizes, and high-burden ISO3 list.

### Module: Panel Model

Build a panel from panel start to end years. Compute PC1 scores for each country-year using the same loadings. Fit a region fixed-effects panel model: `life_expectancy ~ PC1 + region_dummies`. Report coefficient, standard error, p-value, R-squared, and fixed-effects flag.

### Advisory Decision

If the panel model's PC1 coefficient is negative and significant, advise `PRIORITIZE_HIGH_BURDEN_CLUSTER`.

## Output Formatting Rules

- **Numeric precision**: Round computed real-valued fields to the effective declared decimal places. Encode as JSON numbers (do not pad trailing zeros). Counts, ranks, seeds, and PRNG states are integers.
- **Identifiers**: Use the portal's canonical codes exactly (uppercase two-letter state codes, ISO3, division/region names).
- **Ordering**: Preserve every declared order. Do not sort an aligned result array independently. List lengths must match their declared cardinalities.
- **Missing values**: Use JSON `null` only when a requested statistic is mathematically unavailable. Never use `NaN` or `Infinity`.
- **Enum values**: Use only the declared controlled values. Do not invent or infer new categories.
- **Single JSON object**: Return exactly one JSON object with all required top-level keys and no narrative outside it.
