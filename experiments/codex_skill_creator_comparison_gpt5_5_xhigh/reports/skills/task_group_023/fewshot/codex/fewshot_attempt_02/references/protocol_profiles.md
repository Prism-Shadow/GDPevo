# PHO Reusable Protocol Profiles

These profiles contain method semantics only. They intentionally omit solved example values. Bind entities, measures, years, sources, seeds, grids, cutoffs, labels, and output vocabulary from the current request, then recompute every value from the current portal evidence.

## Shared Override Contract

Activate a profile only when the future request's `protocol_id` exactly equals the profile ID. For active profiles:

- Direct root key `k` targets canonical root `k`.
- A root key named `<section>_overrides` targets canonical `<section>` after removing only the terminal suffix.
- `module_overrides.<module>` targets that exact top-level module.
- `reporting_overrides` targets `reporting`.
- Objects recursively merge by exact key.
- Arrays replace whole arrays; never concatenate, union, or patch by position.
- Scalars, strings, Booleans, and null replace only their exact paths.
- Reject unknown targets, renamed keys, inferred aliases, coercions, and incompatible types before any data access.

## PHO_STATE_TRANSPORT_AUDIT_V1

Execution order: release resolution and cohorts, delete-cluster fixed effects, nested ridge division CV, wild cluster bootstrap, grouped split conformal, trajectory PCA clustering, source-year perturbation, controlled decision.

Release and cohorts:

- Filter each requested publication by effective status, source, value type, validity, and geography bindings.
- Select greatest revision, latest release timestamp, then lowest record identifier.
- Count selected publications before analytic completeness exclusions when requested.
- Treat suppressed, invalid, withdrawn, blank, or null analytic values as unavailable.
- Join resolved series by stable entity and time keys; preserve entity-code, time, feature, and group order.

Delete-cluster fixed effects:

- For every active refit, double-demean each modeled variable as `z_it - entity_mean - time_mean + grand_mean`.
- Solve OLS without intercept in declared predictor order.
- A deletion removes the whole cluster, recomputes all means, and refits from scratch in entity-code order.
- With `G` delete estimates `b_-g` and mean `bbar`, compute `SE_JK=sqrt((G-1)/G*sum((b_-g-bbar)^2))` and `b_BC=G*b-(G-1)*bbar`.
- Test `b/SE_JK` two-sided with Student t `G-1` degrees of freedom. Choose extrema by coefficient, then entity code.

Nested ridge division CV:

- Hold out one ordered group per outer fold; within each outer training set hold out every remaining group once in the same order.
- Standardize features from training-only means and sample SD with `ddof=1`.
- Center the training outcome, keep intercept unpenalized, initialize coefficients to zero, and cycle in declared feature order.
- Minimize `mean((y-a-Xb)^2)+lambda*sum(b_j^2)`.
- Update `b_j=sum(x_j*r_j)/(sum(x_j^2)+n*lambda)`, where `r_j` excludes feature `j`.
- Pool inner validation squared errors at row level; select smallest RMSE, then smaller penalty. Pool one outer prediction per eligible row.

Wild cluster bootstrap:

- Use the same double-demeaned matrix as fixed effects.
- For cluster scores `s_g=X_g'e_g`, use CR1 covariance `[G/(G-1)]*[(n-1)/(n-k)]*(X'X)^-1*sum(s_g s_g')*(X'X)^-1`.
- Fit the restricted model without the target and retain restricted fitted values and residuals.
- Use PCG32 with stream binding; map output modulo six to Webb weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Maintain one continuous generator, draw once per cluster in entity-code order for every replicate, refit unrestricted, recompute CR1, and studentize.
- Count `abs(t*)>=abs(t_observed)` and report plus-one `p=(1+count)/(1+B)`. Use nearest-rank quantiles.

Grouped split conformal:

- For each ordered outer group, use it as test.
- Among remaining groups choose calibration by greatest row count then ascending group name; all others are proper training.
- Fit ridge from scratch with the fixed penalty and training-only scaling.
- Sort absolute calibration residuals. With miscoverage `alpha`, use one-based `r=min(m,ceil((m+1)*(1-alpha)))`.
- Intervals are inclusive. Aggregate coverage and width by outer-test row counts.

Trajectory PCA clustering:

- Build columns in variable-major/time order and standardize by active-column sample SD.
- Form `C=Z'Z/(n-1)`. Order components by descending eigenvalue and orient each loading so its earliest maximum-absolute entry is positive.
- Scores are `Z` times oriented loadings.
- Run squared-Euclidean k-means on leading scores: first center is ASCII-first entity; each next center is farthest from nearest center, tied by entity code.
- Assign to nearest center, tied by lower working id; update by member means until unchanged or capped.
- Canonicalize final ids by centroid coordinates then working id.
- For leave-year stability, rebuild scaling, PCA, orientation, initialization, and clustering from scratch; compute adjusted Rand index and align labels by maximum agreement.

Source-year perturbation:

- Enumerate time subsets by increasing requested subset size and lexicographic tuple order.
- Keep the strict analytic set unchanged.
- For each subset, refit double-demeaned primary and parallel models, recomputing CR1 and two-sided `G-1` inference.
- Shift is `abs(b_alt-b)/abs(b)*100`; same-sign requires nonzero identical sign.
- Median is the ordinary median of ordered shifts. Worst subset is greatest unrounded shift, then earlier subset order.

Controlled decision: complete all modules, evaluate predicates on unrounded values in request order, count satisfied gates, and apply only the current request's decision mapping.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Execution order: publication and linked cohorts, primary mediation models, difference GMM mediation, nested state ridge, paired state wild bootstrap, state grouped conformal, partial-R2 sensitivity, state trajectory PCA, controlled precedence.

- Filter each source by effective request fields; select one record per entity-time-measure key using the declared ordered release priority.
- Count selected publications before analytic completeness exclusions when requested.
- Construct primary, balanced-panel, and machine-learning cohorts from effective nonmissing and validity predicates; preserve declared entity and state order.
- Build total-effect, path-a, and direct/path-b OLS designs from effective exposure, mediator, outcome, covariates, transformations, references, and column order. Keep unrounded fitted objects.
- Difference GMM creates adjacent-change rows in entity then end-period order. For each equation use `W=(Z'Z)^-1` and `beta=(X'ZWZ'X)^-1 X'ZWZ'y`.
- With residual `u` and cluster score `q_g=Z_g'u_g`, use the registered finite-sample cluster sandwich. For two equations use the corresponding cross-cluster score product.
- For indirect `theta=a*b`, compute `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t inference with cluster degrees of freedom.
- Compute first-stage partial F from full-versus-reduced residual sums of squares using effective instrument counts.
- Delete-state diagnostics rebuild rows and refit affected equations from scratch in state order.
- Nested ridge uses exact feature order, training arithmetic means, population SD with unit divisor for zero variance, unpenalized intercept, and SSE plus `lambda` times squared non-intercept norm. Outer leaves one state out; inner leaves one remaining state out; pool row squared errors before RMSE.
- Paired wild bootstrap removes each target in turn, forms synthetic outcomes from restricted fitted values plus cluster-weighted residuals, and reuses one xorshift32 state-sign stream across paired equations. Odd state maps to `+1`, even to `-1`; checkpoints record after completed replicate.
- State-grouped conformal indexes states in ascending order, assigns cyclic partitions by index modulo partition count, uses the preceding partition for calibration, reduces calibration residuals to one maximum absolute residual per state, and uses one-based `min(m,ceil((m+1)*coverage))`.
- Partial-R2 sensitivity uses `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`; by direction set `adjusted_b=b-s*magnitude`, `adjusted_indirect=a*adjusted_b`, `adjusted_direct=total-adjusted_indirect`, and `proportion=adjusted_indirect/total`.
- State trajectory PCA aggregates balanced-panel measures to state-period means, standardizes across states with sample SD, uses covariance `Z'Z/(G-1)`, orients loadings, runs deterministic farthest-first Lloyd k-means, and rebuilds the full pipeline for leave-period ARI.
- Controlled precedence evaluates every predicate on unrounded values and returns the first applicable class in the current request's order.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Execution order: release and cohort, common weighted linear algebra, cluster jackknife, nested elastic-net, wild cluster bootstrap, grouped conformal, trajectory PCA clustering, exhaustive source perturbation, controlled decision.

Release, weights, and linear algebra:

- Filter each publication key by status, source, value type, validity, and entity bindings.
- Select greatest revision, latest release timestamp, then greatest record id.
- Join series by stable entity-time keys and apply effective completeness fields.
- Unless overridden, keep the selected direct outcome-record sample size as the fixed positive reliability weight, including source-perturbation fits.
- For WLS, set `Xw=diag(sqrt(w))*X`, `yw=diag(sqrt(w))*y`, and solve `(Xw'Xw)^-1 Xw'yw`.
- HC3 uses leverage `h_i=diag(Xw*(Xw'Xw)^-1*Xw')` and weighted residual `ew_i`; use two-sided Student t with `n-k` degrees of freedom.
- CR1 uses ordered cluster scores and Student t with `G-1` degrees of freedom.

Cluster jackknife:

- Fit full weighted design, delete each registered cluster in order, and refit unchanged design from scratch.
- Percent change is `100*abs((b_delete-b_full)/b_full)`.
- Bias correction and SE use standard delete-cluster jackknife formulas; test `b_BC/SE_JK`.
- Select most influential cluster by greatest unrounded percent change, tied by earlier cluster order.

Nested elastic-net:

- Hold out each registered cluster outer; hold out each remaining cluster as ordered inner fold.
- Build raw, transformed, squared, and interaction features in declared order.
- Compute training-only weighted means and weighted population SD; center `y` by training weighted mean.
- Minimize weighted squared error plus `lambda*(alpha*L1+(1-alpha)*L2/2)`.
- Cold-start every penalty and fold. Cyclic update uses soft threshold `S(rho,lambda*alpha)/(1+lambda*(1-alpha))`.
- Pool unweighted inner validation squared errors; select smallest RMSE then smaller penalty. Pool outer predictions in entity order for RMSE, MAE, and R2.

Wild cluster bootstrap:

- Studentize the full weighted target with cluster CR1.
- Fit restricted weighted model without target, keep untransformed fitted values and residuals in entity order.
- Use continuous xorshift32 stream; draw once per cluster in registered order and map low bit one to `+1`, otherwise `-1`.
- Refit full WLS and recompute cluster CR1 each replicate.
- Count `t*>=t_observed-delta`, report plus-one p, and use type-seven quantiles.

Grouped conformal:

- Reuse each outer center prediction and its selected penalty.
- For outer cluster `d`, hold out each other training cluster once, cold-refit the same weighted elastic-net on remaining clusters, predict held-out calibration rows, and pool absolute residuals.
- Use one-based `min(m,ceil((m+1)*coverage))`. Choose worst coverage by smallest fraction, then earlier cluster order.

Trajectory PCA:

- Build variable-major/time-major blocks in declared order and entity ASCII order.
- Standardize with sample SD; use `C=Z'Z/(n-1)`.
- Order eigenvalues descending, orient earliest maximum-absolute loading positive, score with oriented loadings, and divide explained ratios by the sum of all eigenvalues.
- K-means uses ASCII-first, farthest-first centers, nearest-center ties to lower id, empty-id repair by moving ASCII-first farthest entity, and full rebuild for leave-time stability.

Exhaustive source perturbation:

- Resolve alternate outcomes with module release filters and greatest-revision/latest-release/greatest-id precedence.
- Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code.
- For each mask, replace entity `j` iff `mask & (1<<j)` is nonzero; retain fixed direct reliability weights and design.
- Refit WLS and HC3. Summarize each replacement-count stratum.
- Select maximum shift by greatest unrounded shift, tied by smaller mask.
- Exact Shapley effect for entity `j` is the factorial-weighted average marginal coefficient change; preserve signed order and verify the sum equals all-replacements minus no-replacements.

Controlled decision: complete every module, evaluate gates on unrounded values, and select the first unsatisfied module by the request's precedence.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Execution order: publication balanced panel, delete-state two-step GMM, state-blocked nested elastic-net, state wild cluster bootstrap, cross-fold grouped conformal, county trajectory PCA clustering, source-group perturbation, controlled precedence.

- Resolve county health and socioeconomic sources independently using effective final release priority.
- Treat selected suppressed, invalid, or missing values as incomplete, never zero.
- Retain entities complete across every balanced period with valid geography attributes.
- Create adjacent-change rows ordered by entity identifier then end period. Derive lagged levels, dynamic changes, reference indicators, and interactions in declared order.
- In every GMM fit, residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms.
- First-step moments use identity weight. Build state scores `s_g=Z_g'u_g`, `S=sum(s_g s_g')/n`, and second-step weight as the registered Moore-Penrose inverse of `S`.
- Compute second-step coefficients from weighted linear moments and Hansen `J=n*g(theta)'Wg(theta)`. Apply the relative singular-value cutoff to every pseudoinverse.
- Refit both steps after each state deletion. Bias-correct coefficients with delete-state jackknife and retain maximum absolute delete-state shifts.
- State-blocked nested elastic-net allocates states by descending retained-entity counts to the currently smallest fold, lower fold id on equality; sort state codes within folds and repeat inside each outer-training set.
- Standardize only declared continuous columns from training population moments, leave indicators unchanged, keep intercept unpenalized, and cold-start coefficients at zero with intercept at the training outcome mean.
- Traverse candidate grid in declared order. Pool inner squared errors before RMSE; select smallest unrounded RMSE, then smaller alpha, then smaller l1 ratio.
- Wild bootstrap fits full unpenalized OLS and state CR1, fits restricted model without target, uses continuous xorshift32 in ascending state order, records requested checkpoints, and uses nearest-rank quantiles.
- Cross-fold conformal uses outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on residuals from all other folds; use rank `min(m,ceil((m+1)*coverage))`. Report fold, state, RUCC-band, and prediction-bin diagnostics.
- County trajectory PCA builds variable-major entity trajectories in declared variable and end-period order, standardizes by population moments, uses covariance `Z'Z/n`, orients loadings, runs farthest-first k-means for each candidate k, selects largest unrounded mean silhouette then smaller k, and rebuilds for each state deletion ARI.
- Source-group perturbation removes exactly one declared group at a time, reuses each fold's full-model selected hyperparameters without retuning, applies the same preprocessing and solver, pools fold RMSEs, and ranks by decreasing unrounded deterioration then declared group order.
- Controlled precedence completes all modules, evaluates gates on unrounded values, and returns the first applicable controlled decision.

## Country Burden Revision Audit

Use this section when the request asks for country label reconciliation, revision history, missing coverage, scale-break anomalies, burden PCA, silhouette-selected clustering, region-adjusted panel association, and an advisory, but no exact protocol profile is supplied.

Workflow:

1. Reconcile every requested country label to one stable `iso3` using `countries.portal_label`, `canonical_name`, and `alternate_labels`. Count aliases when the requested label differs from the canonical country name.
2. Pull requested country indicators for the reference cross-section and panel years. Select final records by highest revision then latest release unless the request says otherwise.
3. Pull relevant `revisions` rows. Separate APPLIED scale-correction events from non-applied events. Apply only APPLIED corrections embodied in final revised observations; do not apply pending or withdrawn events manually.
4. Mark unresolved scale-break anomaly cells from non-applied revision events that match requested countries, years, and indicators.
5. Count raw missing reference-year cells before anomaly exclusions. Treat anomaly cells as unavailable. Impute missing/anomaly reference cells using a deterministic, request-defensible rule such as indicator median within region, falling back to global indicator median; report the number imputed.
6. Build the completed PCA matrix in requested indicator order. Orient PC1 as a burden score so higher-worse indicators load positive; if signs are ambiguous, orient so the sum of higher-worse loadings is positive.
7. Report top absolute PC1 loadings by descending absolute loading, breaking exact ties by indicator id.
8. Run deterministic k-means for requested k and candidate k values. Label the requested three clusters by mean PC1 burden as LOW, MIDDLE, and HIGH. Report high-burden ISO3 values sorted only because the template treats the list as set-like.
9. Compute silhouette for candidate k values on the PCA score space. Select largest unrounded silhouette, breaking ties by smaller k unless the request overrides.
10. For panel modeling, build country-year PC1 burden scores from the active indicator set using training/cross-section-consistent orientation, join the outcome indicator, include region fixed effects if requested, and fit the specified panel association.
11. Choose the advisory only from the template vocabulary and only by the current request's controlled rule.
