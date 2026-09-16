# Public Health Observatory Protocol Reference

This reference is reusable method guidance only. It must not be treated as a source of task-local entities, measures, years, seeds, grids, thresholds, output field names, or solved values.

## Shared Resolution Rules

- Activate an exact protocol profile only when the active request's `protocol_id` exactly matches. For the country burden audit, use the template name or prompt structure when no `protocol_id` is present.
- Apply overrides before evidence resolution. Direct keys target identical canonical paths. A root `<section>_overrides` key targets `<section>`; `module_overrides.<module>` targets that exact module. Recursively merge objects, replace arrays whole, replace scalars exactly, and reject unknown paths or incompatible types.
- Resolve one frozen request contract before fetching, folding, drawing random weights, fitting models, imputing values, clustering, or evaluating gates.
- Select publications per active request: filter by entity, year, measure or indicator, release status, source, value type, and quality; then apply declared revision, release timestamp, and record-id priority. Suppressed, invalid, withdrawn, blank, and null analytic values are unavailable and never zero-filled.
- Build complete-case, balanced, broad, strict, primary, machine-learning, or panel cohorts from the active nonmissing predicates after source resolution. Preserve declared orders.
- Compute with unrounded numbers. Round reported real numbers only at final JSON serialization.

## State Transport Audit

Protocol: `PHO_STATE_TRANSPORT_AUDIT_V1`.

Module order:

1. Release resolution and cohorts.
2. Delete-cluster fixed effects.
3. Nested leave-group-out ridge.
4. Wild cluster bootstrap.
5. Grouped split conformal.
6. Trajectory PCA and clustering.
7. Source-year perturbation.
8. Controlled decision.

Fixed-effects OLS:

- For each active fit, double-demean outcome and predictors by entity and time: `z_it - entity_mean - time_mean + grand_mean`.
- Solve OLS without intercept in the declared predictor order.
- For delete-cluster diagnostics, remove the full cluster, recompute all means, and refit from scratch in entity-code order.
- For delete estimates `b_-g`, `bbar=mean(b_-g)`, and cluster count `G`, use `SE_JK=sqrt((G-1)/G * sum((b_-g-bbar)^2))` and `b_BC=G*b-(G-1)*bbar`. Test the registered coefficient with two-sided Student t and `G-1` degrees of freedom.
- Select extrema by unrounded coefficient, then entity code.

Nested ridge and conformal:

- In each outer fold, hold out one ordered group. In each inner fold, hold out one remaining group in the same order.
- Standardize features using training-only arithmetic means and sample standard deviations with `ddof=1`; apply those moments to validation and test rows.
- Center training outcome, keep intercept unpenalized, solve ridge by coordinate descent for objective `mean((y-a-Xb)^2)+lambda*sum(b_j^2)`.
- Pool inner validation squared errors at row level before RMSE. Choose smallest unrounded RMSE, then smaller penalty. Pool one outer prediction per eligible row for RMSE, MAE, and `1-SSE/SST`.
- For split conformal, choose the calibration group among non-test groups by greatest row count then ascending group name unless the request specifies another rule. Sort absolute calibration residuals and use one-based rank `min(m, ceil((m+1)*(1-alpha)))`.

PCG32 Webb bootstrap:

- Use the declared seed and stream. Initialize PCG32 with unsigned 64-bit wraparound, increment `2*stream+1`, and one continuous generator.
- Draw once per cluster in entity-code order for each replicate. Map output modulo six to Webb weights in order `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Fit the restricted model without the target. Generate `y* = restricted_fit + restricted_residual * cluster_weight`, refit unrestricted OLS, recompute CR1, and studentize.
- Count absolute exceedances, report plus-one p-value, batch checkpoints, coefficient summaries, and nearest-rank quantiles.

Trajectory PCA:

- Build feature columns in the active variable-major and time order. Standardize columns with sample standard deviations and form covariance `Z'Z/(n-1)`.
- Use deterministic eigendecomposition. Order components by descending eigenvalue, break ties by original index, and flip each loading so the earliest maximum-absolute entry is positive.
- Cluster leading scores with deterministic farthest-first k-means: first center is ASCII-first entity, each next center maximizes distance to the nearest center with entity-code tie break. Assign ties to lower id, update by arithmetic means, and canonicalize final ids as requested.
- For leave-time stability, rebuild the full PCA and clustering pipeline after omitting each time block. Compute adjusted Rand index and aligned agreement using the best label permutation, tied lexicographically.

Source-year perturbation:

- Keep the strict analytic cohort fixed. Enumerate requested time subsets by increasing size and lexicographic order.
- Refit the complete double-demeaned model separately for primary and parallel sources. Recompute CR1 and two-sided inference for every subset.
- Report same-sign counts, absolute percent shifts relative to the baseline coefficient, ordinary median shift, and the worst subset by greatest unrounded shift then earlier subset order.

## County Mediation Transport Audit

Protocol: `PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Module order:

1. Publication and linked cohorts.
2. Primary mediation models.
3. Difference GMM mediation.
4. Nested state ridge.
5. Paired state wild bootstrap.
6. State grouped conformal.
7. Partial-R2 sensitivity.
8. State trajectory PCA.
9. Controlled conclusion.

Publication and designs:

- Resolve health and socioeconomic records independently, count selected publications before analytic exclusions when requested, and construct primary, balanced-panel, and machine-learning cohorts from active completeness predicates.
- Build total-effect, path-a, and direct/path-b OLS designs from active exposure, mediator, outcome, covariates, transformations, references, and column order. Reuse unrounded fitted models for bootstrap and sensitivity.
- Apply declared income and categorical-reference semantics from the active request.

Difference GMM mediation:

- Create adjacent-change rows in entity then end-period order.
- Use instruments and controls from the active request. For each equation, use `W=(Z'Z)^-1` and `beta=(X' Z W Z' X)^-1 X' Z W Z' y`.
- With residual `u`, build cluster scores `q_g=Z_g' u` and the registered finite-sample sandwich. For cross-equation covariance, use the corresponding cross-cluster score product.
- For indirect effect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t inference with cluster degrees of freedom.
- Compute first-stage partial F from full-versus-reduced residual sums of squares. Rebuild all rows and refit affected equations for each delete-state diagnostic.

Nested state ridge:

- Use effective feature maps in exact order. Standardize with training arithmetic means and population standard deviations, using a unit divisor for zero variance.
- Fit ridge with unpenalized intercept by minimizing training SSE plus penalty times non-intercept squared norm.
- Outer validation leaves one state out; inner validation leaves one remaining state out. Pool county squared errors before RMSE. Choose smallest unrounded inner RMSE, then smaller penalty.
- For base versus augmented models, keep aligned inner grids and compare each state's held-out RMSE.

Paired xorshift32 bootstrap:

- For each target equation, fit the restricted model with only that target removed.
- Use unsigned xorshift32 with shifts 13, 17, and 5, masking to 32 bits after each xor. Draw once per state in ascending order per replicate and reuse the same sign across paired equations; odd maps to `+1`, even to `-1`.
- Refit unrestricted equations, recompute CR1 t statistics, use two-sided absolute exceedances with plus-one p-values, and record declared checkpoints after completed replicates.

State grouped conformal:

- Sort states ascending, assign cyclic partitions by index modulo partition count, and use the registered preceding partition as calibration for each test partition.
- Reduce calibration residuals to one maximum absolute residual per calibration state. Use rank `min(m, ceil((m+1)*coverage))`.
- Aggregate county coverage and interval width by cycle and by state. Choose worst states using declared tie rules.

Partial-R2 sensitivity:

- From unrounded baseline `a`, `b`, `SE_b`, and residual degrees of freedom `df`, compute `magnitude = SE_b * sqrt(df*rY*rM/(1-rM))`.
- For each declared direction, use `adjusted_b=b-s*magnitude`, `adjusted_indirect=a*adjusted_b`, `adjusted_direct=total-adjusted_indirect`, and `proportion=adjusted_indirect/total`.
- Enumerate the complete surface in declared R2 and direction order. Compute the equal-strength tipping point from unrounded inputs.

State trajectory PCA:

- Aggregate balanced-panel county measures to state-period means in declared order.
- Standardize across states with sample standard deviations and covariance `Z'Z/(G-1)`.
- Orient eigenvectors by earliest maximum-absolute loading, score states, run deterministic farthest-first k-means, and rebuild the entire pipeline for leave-period ARIs.

## Country Burden Revision Audit

Template family: `country_burden_revision_audit_v1`.

- Reconcile every requested country label against portal country records and aliases. Count requested labels, unique resolved labels, alias resolutions, and return ISO3 identifiers in sorted ascending order when the template asks for a set-like list.
- Use the revisions endpoint to identify applicable revision events for requested countries, years, and indicators. Separate applied from non-applied events by status and sort event identifiers ascending.
- Treat unresolved scale breaks or anomaly flags as unusable cells. Report anomaly observation keys as `ISO3|YEAR|indicator_id` sorted ascending.
- For the reference-year burden matrix, count raw missing requested cells before anomaly exclusions. Impute remaining usable cells only by the method indicated by portal methodology or request; keep imputation counts separate from anomaly counts.
- For burden PCA, standardize usable indicators, compute covariance PCA, orient PC1 so burden-increasing indicators have positive loadings when the data support that direction, and report top absolute PC1 loadings by descending absolute value with identifier tie break.
- Run deterministic k-means for requested segmentation. For silhouette selection, evaluate candidate `k` values required by the template, compute mean Euclidean silhouette with singleton clusters scored zero, choose highest unrounded silhouette, and break ties toward smaller `k`.
- Label burden clusters by PC1 burden ordering as low, middle, and high. Return high-burden membership sorted when requested.
- For panel association, join country-year PC1 burden scores to the active outcome, include region fixed effects when requested, and report coefficient, standard error, p-value, R-squared, observation count, and advisory using the active decision rule.

## State Reliability-Weighted Robustness Audit

Protocol: `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Module order:

1. Release and cohort.
2. Weighted linear algebra.
3. Cluster jackknife.
4. Nested elastic net.
5. Wild cluster bootstrap.
6. Grouped conformal.
7. Trajectory PCA.
8. Exhaustive source perturbation.
9. Controlled decision.

Weighted regression and inference:

- Use the active positive reliability weight. For design `X`, outcome `y`, and weights `w`, set `Xw=sqrt(w)*X`, `yw=sqrt(w)*y`, then solve WLS in declared column order.
- HC3 uses weighted leverages from `Xw (Xw'Xw)^-1 Xw'` and weighted residuals `sqrt(w_i)*(y_i-X_i b)`.
- CR1 uses ordered cluster scores `s_g=Xw_g' ew_g` and finite-sample factor `[G/(G-1)]*[(n-1)/(n-k)]`, with two-sided Student t and `G-1` degrees of freedom.

Cluster jackknife:

- Fit full WLS, then delete every registered cluster in order and refit unchanged design from scratch.
- Percent change is `100*abs((b_delete-b_full)/b_full)`. Pick greatest unrounded percent change, tied by earlier cluster order.
- Use bias-corrected coefficient and jackknife SE formulas; test `b_BC/SE_JK`.

Weighted elastic net:

- Hold out each registered cluster as outer fold and each remaining cluster as ordered inner fold.
- Build declared raw, transformed, squared, and interaction features. Standardize with training-only weighted means and weighted population standard deviations.
- Center `y` by its training weighted mean. Minimize weighted SSE divided by `2*sum(w)` plus elastic-net penalty. Cold-start each fit; never warm-start across penalties.
- Coordinate update: `rho_j=sum(w_i*z_ij*r_ij)/sum(w_i)` and `b_j=S(rho_j, lambda*alpha)/(1+lambda*(1-alpha))`.
- Pool unweighted inner validation squared errors, choose smallest unrounded RMSE then smaller penalty, refit, and pool OOF metrics in entity order.

Xorshift division bootstrap:

- Fit the restricted weighted model without the target, generate synthetic outcomes using cluster signs from one continuous xorshift32 stream, refit full WLS, recompute CR1, and record absolute target t statistics.
- Count `t* >= t_observed - delta` when a comparison tolerance is specified. Use plus-one p-value.
- Type-seven quantile uses `h=(B-1)*p`, `j=floor(h)`, and linear interpolation between sorted zero-based positions.

Grouped conformal:

- Reuse each outer prediction and selected penalty. For each held-out cluster, hold out each other training cluster once as calibration, cold-refit on remaining clusters, and pool absolute residuals.
- Use rank `min(m, ceil((m+1)*nominal_coverage))`. Report pooled covered count, row count, coverage, held-out-count-weighted mean interval width, and worst division by smallest coverage then earlier cluster order.

Exhaustive source perturbation:

- Resolve alternate outcomes with effective filters. Pair entities that have eligible baseline and replacement records. Order pairs by descending absolute alternate-minus-primary difference, tied by entity code.
- For each bitmask from zero to `2^m-1`, replace entity `j` iff the bit is set. Keep direct reliability weights and design fixed, refit WLS, and compute HC3.
- Stratum summaries are by replacement count. Select maximum unrounded percent shift, tied by smaller mask.
- Exact Shapley contribution for entity `j` is the factorial-weighted average of `b(S union j)-b(S)` over all subsets not containing `j`. Preserve signed effects in ordered entity order and verify their sum equals all-replacement minus all-direct.

## County Panel Dynamics Audit

Protocol: `PHO_COUNTY_PANEL_TRANSPORT_V1`.

Module order:

1. Publication balanced panel.
2. Delete-state two-step GMM.
3. State-blocked nested elastic net.
4. State wild cluster bootstrap-t.
5. Cross-fold grouped conformal.
6. County trajectory PCA and clustering.
7. Source-group perturbation.
8. Controlled decision.

Publication panel:

- Resolve county health and socioeconomic records independently by active final-release rules.
- Retain counties complete for every balanced period, with valid geography attributes. Create adjacent-change rows ordered by entity id then end period.
- Derive lagged levels, dynamic changes, reference indicators, interactions, and source groups in declared order.

Delete-state two-step GMM:

- Residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms in every full or delete-state fit.
- First-step moments use identity weight. Build state scores from residuals; second-step weight is the Moore-Penrose inverse of the cluster score covariance using the active relative singular-value cutoff.
- Estimate second-step coefficients, Hansen J, delete-state coefficients, bias-corrected coefficients, and maximum absolute shifts. Refit both steps after each state deletion.

State-blocked nested elastic net:

- Allocate states by descending retained-entity counts to the currently smallest fold, tying to lower fold id; sort state codes within folds. Repeat allocation inside each outer-training set for inner folds.
- Standardize declared continuous terms by training population moments, leave indicators unchanged, keep intercept unpenalized, and penalize all non-intercept terms.
- Traverse the full declared alpha and l1-ratio grid in order. Pool inner squared errors before RMSE. Select by smallest unrounded RMSE, then smaller alpha, then smaller l1 ratio.
- Refit each outer model with selected hyperparameters, retain selected standardized coefficients, outer RMSEs, and pooled OOF metrics.

State wild bootstrap:

- Fit full unpenalized OLS with state-cluster CR1 for the target term.
- Fit restricted model without the target. Generate synthetic outcomes with one continuous xorshift32 stream, drawing states in ascending order. Odd maps to `+1`, even to `-1`.
- Refit full model and recompute CR1 each replicate. Use absolute-tail exceedances, plus-one p-value, nearest-rank quantiles, and requested checkpoints.

Cross-fold conformal:

- Use nested elastic-net OOF predictions in original analytic-row order.
- For each held-out fold, calibrate on absolute OOF residuals from all other folds. Rank is `min(m, ceil((m+1)*coverage))`.
- Report fold diagnostics, state coverages, rurality-band coverages, prediction-bin diagnostics, overall coverage, and minimum state coverage. Assign prediction bins after sorting by prediction and declared identifiers.

County trajectory PCA:

- Build variable-major county trajectories in declared variable and end-period order. Standardize by population moments and use covariance `Z'Z/n`.
- Evaluate every candidate cluster count with deterministic farthest-first k-means. Compute Euclidean silhouette, singleton score zero, choose highest unrounded silhouette then smaller `k`.
- For each state deletion, rebuild the complete trajectory pipeline at selected `k` and compute adjusted Rand index on retained counties.

Source-group perturbation:

- For each source group and each outer fold in declared order, remove exactly the group's terms and reuse that fold's full-model selected hyperparameters without retuning.
- Apply the same preprocessing and solver to remaining terms, report outer-fold RMSEs, pooled RMSE, deterioration from full-model OOF RMSE, worse-fold count, and rank by decreasing unrounded deterioration with declared-order tie break.

## Final Decision

- Evaluate every module-specific predicate on unrounded values after all modules are complete.
- Count supported flags or select the first failed module exactly as the active request specifies.
- Return only controlled enum values from the active template.
