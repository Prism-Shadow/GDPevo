# PHO Protocol Methods

This reference captures reusable method semantics inferred from the training evidence. It intentionally omits solved counts, coefficients, entity memberships, PRNG states, classifications, and other task-local final answer values.

## Universal Release Rules

Bind all entities, years, measures, sources, grids, seeds, thresholds, and output names from the active request. If the request supplies an override structure, freeze the effective request once before querying data.

Publication resolution pattern:

1. Filter by effective release status, source type, value type, measure or indicator, year, geography, and any explicit quality predicates.
2. Within each entity-time-measure key, select one row by the effective priority. Unless a profile says otherwise, use highest revision, latest `released_at`, then the deterministic record-id direction required by the active request/profile.
3. Treat `suppression_flag=1`, blank values, null values, explicitly invalid quality flags, withdrawn records, and unresolved scale-review anomaly cells as analytically unavailable. Do not substitute zero.
4. Count release rows before analytic exclusions only when the template asks for publication/release counts.

Current-methodology portal cues:

- `SCALE_REVIEW` in `country_indicators` marks unresolved scale-review cells unless an applied revision supersedes the issue.
- `SUPPRESSED` health quality flags and suppression flags make values unavailable.
- `PARALLEL_ESTIMATE`, `REVISED`, `CORRECTED`, `STALE`, and `REVIEWED` can remain eligible unless the active request excludes them.
- `FINAL` releases supersede provisional records for publication tasks.

## Shared Numerical Conventions

Keep full precision internally. Round only output fields. For ties, use the unrounded values and then the earliest declared order unless a profile gives a different tie-break.

Common formulas:

- OLS: solve in declared column order, retaining an intercept only when the design includes one.
- WLS: with positive weights `w`, solve OLS on `sqrt(w_i) * X_i` and `sqrt(w_i) * y_i`.
- HC3 for WLS: compute leverage on the weighted design and use `e_w_i^2 / (1 - h_i)^2`.
- CR1: for `G` clusters and `k` parameters, use `[G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g s_g s_g' * (X'X)^-1`, where `s_g=X_g' e_g` on the active transformed/weighted design.
- Jackknife: for delete estimates `b_-g`, `bbar=mean(b_-g)`, `SE=sqrt((G-1)/G * sum((b_-g-bbar)^2))`, and `b_BC=G*b_full-(G-1)*bbar`.
- Two-sided p-values use the Student t degrees of freedom declared by the profile, commonly `G-1` for cluster inference or `n-k` for HC3.
- Pooled RMSE and R2 always pool row-level held-out predictions, not fold means.

Random generators:

- Xorshift32: unsigned 32-bit state; `x ^= x << 13`, `x ^= x >> 17`, `x ^= x << 5`, masking to 32 bits after each xor. Maintain one continuous stream. Odd low bit maps to `+1`; even maps to `-1`.
- PCG32 Webb: initialize a 64-bit PCG stream with `increment=2*stream+1`; advance once from zero, add seed modulo `2^64`, advance again. Each output uses multiplier `6364136223846793005`, rotates the xorshifted value, and maps `output % 6` to Webb weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Record checkpoints only after the requested replicate has been fully drawn and refit.

PCA and clustering:

- Build feature columns in declared order. Standardize columns using the active sample moments and the profile's divisor (`n-1` sample SD or `n` population SD).
- Order eigenpairs by descending eigenvalue. Flip each loading vector so the earliest maximum-absolute loading is positive, unless the active request gives a burden-direction orientation.
- Deterministic k-means uses farthest-first centers starting from the smallest stable entity id unless the profile specifies fold allocation instead. Assign equality to the lower cluster id. Update by arithmetic centroids until labels stop changing or the cap is hit.
- Adjusted Rand index is computed from the contingency table against the full labels. When labels must be aligned, choose the permutation with maximum matches, tied lexicographically.

Conformal calibration:

- Intervals are inclusive and symmetric around the specified predictions.
- For coverage `c`, use one-based rank `min(m, ceil((m+1)*c))`. For miscoverage `alpha`, use `c=1-alpha`.
- Sort absolute calibration scores ascending. Report pooled coverage by row counts unless a template asks for state-maximum scores or weighted widths.

## PHO_STATE_TRANSPORT_AUDIT_V1

Activate this profile only for exact `protocol_id: PHO_STATE_TRANSPORT_AUDIT_V1`.

Modules in order:

1. Release resolution and cohorts
2. Delete-cluster two-way fixed effects
3. Nested leave-one-Census-division-out ridge
4. PCG32 Webb wild cluster bootstrap
5. Grouped split conformal ridge
6. Trajectory PCA clustering
7. Source/year perturbation
8. Controlled decision

Release/cohort:

- Resolve requested state health and state socioeconomic series separately.
- The state transport profile selects final records by greatest revision, latest release timestamp, then lowest record identifier when an id tie remains.
- Core balanced cohorts must be complete for the effective outcome, primary exposure, and adjustment fields in every analysis year.
- Broad reference cohorts are reference-year complete cases for the outcome and ordered ridge features.
- Strict dual-source cohorts are complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.

Delete-cluster fixed effects:

- For each active fit, double-demean outcome and predictors as `z_it - entity_mean - time_mean + grand_mean`.
- Fit OLS without intercept in declared predictor order.
- A deletion removes one state/cluster, recomputes all means, and refits.
- Test the full target coefficient divided by the jackknife SE with `G-1` degrees of freedom. Extrema are by coefficient, then entity code.

Nested ridge:

- Outer folds hold out each declared Census division. Inner folds hold out each remaining division in the same order.
- Standardize features with training-only arithmetic means and sample SD (`ddof=1`); apply those moments to validation/test rows.
- Center the training outcome; keep the intercept unpenalized.
- Optimize `mean((y-a-Xb)^2) + lambda * sum(b_j^2)`.
- Coordinate update for feature `j`: `b_j = sum(x_ij*r_ij) / (sum(x_ij^2) + n*lambda)`, where `r` excludes feature `j`.
- Choose the smallest pooled inner RMSE, tied toward the smaller penalty. Refit on all outer-training rows.

Wild bootstrap:

- Use the same double-demeaned design as fixed effects.
- Fit the restricted model with the target removed. Generate `y* = restricted_fit + restricted_residual * cluster_weight`.
- Draw one Webb weight index per state per replicate in state-code order from the continuous PCG32 stream.
- Refit unrestricted, recompute CR1, studentize, count `abs(t*) >= abs(t_observed)`, and report plus-one p-value if requested by the active template.
- Batch exceedance counts are consecutive replicate batches in bound order. Nearest-rank quantiles use one-based `ceil(p*B)`.

Grouped split conformal:

- For each outer division, use it as test.
- Among remaining divisions, choose calibration by greatest row count then ascending division name; train on the rest.
- Fit ridge with the fixed lambda and the same scaling/solver as nested ridge.
- Rank absolute calibration residuals with the declared coverage/miscoverage rule and aggregate coverage/width over held-out rows.

Trajectory PCA:

- Build variables in the request's feature order, usually all years for one measure before the next measure.
- Use sample SD and covariance `Z'Z/(n-1)`.
- Use the deterministic PCA orientation and farthest-first k-means rules above.
- Leave-year-out stability rebuilds the entire PCA and clustering pipeline after deleting the year block.

Source/year perturbation:

- Enumerate source/year subsets by increasing requested subset size, then lexicographic tuple order.
- Keep the strict cohort fixed.
- For each subset, refit the double-demeaned model with primary and parallel exposure series separately, recomputing CR1 and p-values.
- Percent shift is `100 * abs(b_alt - b) / abs(b)`. Same sign requires both coefficients nonzero and identical sign.
- Worst subset is greatest unrounded shift, then earlier subset order.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Activate only for exact `protocol_id: PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Release/cohort:

- Resolve state health/socioeconomic final records. This profile uses greatest revision, latest release timestamp, then greatest record id for remaining ties.
- Use the selected direct outcome sample size as the fixed reliability weight, including source-perturbation fits, unless explicitly overridden.

Weighted regression:

- Build the declared design with intercept and regional references from the request.
- Use WLS for coefficients, HC3 for primary inference, and CR1 for clustered bootstrap statistics.

Cluster jackknife:

- Delete each registered Census division in order and refit the unchanged weighted design.
- Percent change is `100 * abs((b_delete - b_full) / b_full)`.
- Test `b_BC / SE_JK` with `G-1` degrees of freedom. Most influential division is greatest unrounded percent change, tied by earlier division order.

Nested weighted elastic net:

- Outer folds and inner folds leave one registered division out.
- Build raw, log, squared, and interaction features exactly in declared order.
- Compute weighted training means and weighted population SDs for scaling. Center `y` by its training weighted mean.
- Minimize `sum(w_i*(y_i-Z_i b)^2)/(2*sum w_i) + lambda * [alpha*sum|b_j| + (1-alpha)*sum(b_j^2)/2]`.
- Cold-start every fold/penalty. Cyclic update: `rho_j=sum(w_i*Z_ij*r_ij)/sum(w_i)` and `b_j=S(rho_j, lambda*alpha)/(1+lambda*(1-alpha))`.
- Pool unweighted validation errors for RMSE. Choose smallest unrounded RMSE, tied toward the smaller penalty.

Wild bootstrap:

- Fit the weighted restricted model without the target coefficient.
- Use continuous xorshift32 signs in registered division order.
- Record absolute studentized target values. Count exceedances with the active tolerance, report plus-one p-value, and use type-seven quantiles for requested absolute t probabilities.

Grouped conformal:

- Reuse each outer prediction and selected penalty.
- For held-out division `d`, hold out each other training division once as a calibration fold, cold-refit on the remaining divisions, and pool absolute residuals.
- Use coverage rank, inclusive intervals, pooled covered/state counts, held-out-count weighted mean width, and worst coverage by smallest fraction then earlier division order.

Trajectory:

- Build variable-major/time-major blocks in declared order for balanced states.
- Use sample SD, covariance `Z'Z/(n-1)`, oriented PCA scores, and deterministic k-means on the retained components.
- If a k-means cluster is empty, move the ASCII-first point among those farthest from its assigned center, then continue.

Exhaustive source perturbation:

- Resolve alternate outcome records with the module filters.
- Order paired entities by descending absolute alternate-minus-primary difference, tied by state code.
- Enumerate masks from `0` through `2^m - 1`; replace entity `j` when bit `j` is set. Retain fixed direct reliability weights.
- For each stratum by replacement count, report scenario counts, coefficient and HC3 p-value ranges, and mean absolute shift.
- Exact Shapley effect for entity `j`: sum over subsets not containing `j` of `|S|!*(m-|S|-1)!/m! * (b(S union j)-b(S))`.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Activate only for exact `protocol_id: PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Release/cohort:

- Resolve county health and county socioeconomic records independently with the request's release priority.
- Primary cohort is the requested primary-year basic-complete counties. Balanced cohort is complete across all requested years. Machine-learning cohort adds requested ML covariates.
- Income terms use median income per 10000. RUCC indicators are `RUCC2` through `RUCC9` with `RUCC1` as reference.

Primary and difference-GMM mediation:

- Build total-effect, path-a, and direct/path-b designs from the effective exposure, mediator, outcome, covariates, transformations, and column order.
- Create adjacent-change rows in entity then end-period order using the requested lag structure.
- For each GMM equation use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- Cluster sandwich uses state scores. Cross-equation covariance uses cross-products of corresponding cluster scores.
- For indirect effect `theta=a*b`, `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`.
- First-stage partial F compares full and reduced first stages with the effective instrument count.
- Delete-state diagnostics rebuild rows and refit all affected equations from scratch in state order.

Nested state ridge:

- Construct base and augmented feature maps exactly in request order.
- Leave one state out for outer folds; leave one remaining state out for each inner fold.
- Standardize with training arithmetic means and population SDs, using a unit divisor for zero variance.
- Fit ridge with unpenalized intercept; choose smallest pooled inner RMSE, tied to smaller penalty; aggregate one OOF prediction per eligible county.

Paired state wild bootstrap:

- For each target equation, fit the restricted model without that target.
- Use one continuous xorshift32 stream. Draw one sign per state in ascending state order and reuse the same state signs across paired equations.
- Use absolute exceedances, plus-one p-values, nearest-rank bootstrap-t quantiles, and checkpoint PRNG states after completed replicates.

State grouped conformal:

- Sort states ascending and assign cyclic partitions by index modulo the requested partition count.
- For test partition `p`, use the registered preceding partition as calibration and all others for training.
- Reduce calibration residuals to one maximum absolute residual per calibration state. Use coverage rank on those state maxima.
- Aggregate county coverage and interval width by cycle and state.

Partial R2 sensitivity:

- From baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`.
- For each direction sign `s`, use `adjusted_b=b-s*magnitude`, `adjusted_indirect=a*adjusted_b`, `adjusted_direct=total-adjusted_indirect`, and `proportion=adjusted_indirect/total`.
- Enumerate R2 values and directions exactly as declared.

State trajectory:

- Aggregate balanced county measures to state-period means in declared feature order.
- Use sample SD and covariance `Z'Z/(G-1)`, oriented PCA, deterministic k-means, and leave-period ARI refits.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Activate only for exact `protocol_id: PHO_COUNTY_PANEL_TRANSPORT_V1`.

Balanced panel:

- Filter county health and socioeconomic sources independently.
- Retain counties complete across every balanced period with valid geography and RUCC attributes.
- Create adjacent-change rows ordered by county identifier then end period. Derive lagged levels, dynamic changes, indicators, and interactions in declared order.

Delete-state two-step GMM:

- Within each full/delete fit, residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms.
- First-step moments use identity weight.
- Build state scores `s_g=Z_g'u_g`, `S=sum(s_g s_g')/n`, and the second-step weight as the Moore-Penrose inverse of `S` using the effective relative singular-value cutoff.
- Compute second-step coefficients and Hansen `J=n*g(theta)'Wg(theta)`.
- Refit after every state deletion and bias-correct coefficients with the jackknife formula.

State-blocked nested elastic net:

- Allocate states by descending retained-entity counts, assigning each to the currently smallest fold and using lower fold id on equality; sort state codes within folds. Repeat inside each outer-training set for inner folds.
- Standardize continuous terms by training population moments. Leave indicators unchanged. Keep intercept unpenalized.
- Minimize `SSE/(2n)+alpha*(rho*sum|beta|+0.5*(1-rho)*sum beta^2)`.
- Cold-start coefficients at zero and intercept at the training outcome mean.
- In each sweep update intercept by mean residual, then update features in coefficient order with soft thresholding. Stop by max coefficient change or cap.
- Traverse candidate grid in declared order. Select smallest unrounded inner RMSE, then smaller alpha, then smaller l1 ratio.

Wild state bootstrap:

- Fit full unpenalized OLS and state-cluster CR1 for the target.
- Fit restricted model without the target, then generate synthetic outcomes with xorshift32 state signs in ascending state order.
- Refit full model each replicate, recompute CR1, record absolute-tail exceedances, plus-one p-value, nearest-rank quantiles, and checkpoints.

Cross-fold grouped conformal:

- Use outer OOF predictions in original analytic-row order.
- For held-out fold `f`, calibrate on absolute OOF residuals from all other folds.
- Report fold diagnostics, state coverage, RUCC-band coverage, prediction-decile calibration, overall coverage, and minimum state coverage.
- Prediction bins are assigned after sorting by prediction and declared identifiers; signed gap is prediction mean minus observation mean.

County trajectory:

- Build variable-major entity trajectories in declared variable and end-period order.
- Standardize with population moments and covariance `Z'Z/n`.
- For each candidate k, use farthest-first k-means, compute Euclidean silhouette with singleton value zero, and select largest unrounded mean silhouette, tied to smaller k.
- Delete-state stability rebuilds the entire pipeline at the selected k and compares retained labels with ARI.

Source-group perturbation:

- For each source group and outer fold in declared order, remove exactly the group terms and reuse that fold's full-model selected hyperparameters without retuning.
- Apply the same preprocessing and solver to the remaining terms.
- Pool squared errors for group RMSE, subtract full-model OOF RMSE for deterioration, count folds worse than the corresponding full-model fold, and rank groups by decreasing unrounded deterioration then declared group order.

## Country Burden Revision Audits

Use this profile when the active request asks for country-label reconciliation, country indicator revisions/anomalies, burden PCA, cluster segmentation, and a region-adjusted panel association.

Reconciliation:

- Resolve each requested label against `countries.canonical_name`, `portal_label`, and pipe-separated `alternate_labels`.
- Use stable `iso3` identifiers. Count alias resolutions when the requested label is not the canonical country name.
- Report set-like ISO3 lists sorted ascending unless the template declares another order.

Quality and revisions:

- Work from `country_indicators` and `revisions`.
- Resolve final country indicator rows by country, year, and indicator using highest revision and latest release.
- Audit applicable revision events by requested countries, indicators, and panel/reference years. Report APPLIED and non-APPLIED event ids in sorted order when requested.
- Treat unresolved `SCALE_REVIEW` country-indicator cells as anomaly observation keys formatted `ISO3|YEAR|indicator_id`.
- For the reference-year PCA matrix, count raw missing requested indicator cells before anomaly exclusions; count anomaly cells separately; impute all missing/anomaly matrix cells after exclusion.

Burden PCA:

- Build a country by requested burden-indicator matrix for the reference year.
- Impute missing/anomaly cells deterministically from the available same-indicator distribution among resolved countries unless the active request or portal method says otherwise.
- Standardize each indicator column. Orient PC1 so higher burden indicators have positive loadings.
- Report top absolute loadings by descending absolute loading, tied by indicator id.

Clusters:

- Cluster on retained burden scores. For the requested three-segment output, assign burden labels by increasing cluster mean PC1: low, middle, high.
- Evaluate silhouette for candidate k values from the active request/template. Select largest unrounded silhouette, tied by smaller k.
- Report high-burden membership sorted ascending when requested as a set.

Panel model:

- Build a country-year panel over the requested years for resolved countries with life expectancy and PC1 burden score.
- Include region fixed effects when requested. Recompute burden scores for panel years using the same indicator order and orientation convention.
- Fit the region-adjusted association and report coefficient, standard error, p-value, R-squared, and the controlled advisory from active predicates.
