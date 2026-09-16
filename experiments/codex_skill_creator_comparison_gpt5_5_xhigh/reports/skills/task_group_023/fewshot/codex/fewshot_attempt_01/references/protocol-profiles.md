# PHO Protocol Profiles

This reference contains reusable method semantics inferred from the staged examples. It must not be treated as a source of task-local values. The active request and portal data supply all entities, years, measures, source filters, grids, seeds, replicate counts, cutoffs, labels, and output field names.

## Shared Effective-Request Rules

Activate protocol-specific instructions only for an exact case-sensitive `protocol_id` match. For country burden tasks without a `protocol_id`, activate only when the template or prompt clearly names the country burden revision audit.

Resolve one effective request before evidence resolution or computation:

- A direct root key targets the canonical root key with the identical name.
- Inside a named section or module, a direct child key targets only the identical child path.
- A root key named `<section>_overrides` targets canonical `<section>` after removing only the terminal suffix.
- `module_overrides.<module_name>` targets the canonical top-level module of the exact same name.
- Objects deep-merge by exact key; arrays replace arrays in full; scalars, strings, booleans, and null replace only their exact paths.
- Reject unknown targets, inferred aliases, key renames, array concatenation, positional patches, and type coercion.

General release and cohort rules:

- Select only records satisfying the active status, source, value type, geography, measure, and validity predicates.
- Apply the active release priority exactly. Common priorities are highest final revision, then latest `released_at`, then a record-id tie rule from the request or profile.
- Count selected publication rows before analytic completeness exclusions when requested.
- Treat suppressed, invalid, withdrawn, blank, null, and unresolved scale-break values as unavailable.
- Join independently resolved series by stable entity and time keys. Preserve declared orders; do not sort aligned arrays independently.

## Common Numerical Rules

Use unrounded computations throughout. Round only while serializing the final JSON.

For OLS or WLS, keep the intercept unpenalized. For weighted models, transform by `sqrt(w)` for fitting and robust covariance while reporting coefficients on the original design scale.

For CR1 covariance with clusters `g`, let `s_g=X_g' e_g` on the model's transformed design and residual scale. Use
`V=[G/(G-1)]*[(n-1)/(n-k)]*(X'X)^-1*sum_g(s_g s_g')*(X'X)^-1`
unless the active request specifies a different finite-sample correction. Use Student-t inference with `G-1` degrees of freedom. For HC3, use leverage-adjusted squared residuals divided by `(1-h_i)^2` and Student-t inference with `n-k` degrees of freedom.

For jackknife over `G` clusters, compute all delete-cluster refits from scratch. With full coefficient `b`, delete estimates `b_-g`, and mean `bbar`, use
`SE=sqrt((G-1)/G * sum((b_-g-bbar)^2))` and `b_bc=G*b-(G-1)*bbar`. Select extrema and influence summaries by unrounded value, then by the requested order.

For nested validation, standardize from training rows only and apply those moments to validation/test rows. Pool row-level squared errors before RMSE; do not average fold RMSEs. Break ties by the request's declared order, usually smaller penalty first.

For split conformal intervals, sort absolute calibration residuals and use the finite-sample one-based rank declared by the profile. Intervals are symmetric and inclusive.

For PCA and clustering, build features in declared order, standardize columns using the profile's population or sample convention, orient each loading so the earliest maximum-absolute loading is positive unless a burden orientation is declared, and rerun the full pipeline for every stability deletion. K-means uses deterministic farthest-first centers, lower cluster id on assignment ties, arithmetic centroid updates, and declared convergence limits.

## PHO_STATE_TRANSPORT_AUDIT_V1

Use this profile only for `protocol_id: PHO_STATE_TRANSPORT_AUDIT_V1`.

Release/cohort:

- Resolve state health and socioeconomic final releases independently.
- For this profile, select greatest revision, then latest release timestamp, then lowest record identifier unless the active request overrides the priority.
- Build the core balanced cohort from states complete for the requested outcome, primary exposure, and adjustments in every analysis year. Build the broad reference cohort from reference-year complete cases for the outcome and every ordered ridge feature. Build the strict dual-source cohort from states complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.

Delete-cluster fixed effects:

- For every full and delete-state refit, double-demean each modeled variable as `z_it - state_mean - year_mean + grand_mean`.
- Fit OLS without intercept in declared predictor order.
- Delete one whole state at a time, recompute all means, and refit in state-code order.
- Test the full target coefficient with the jackknife SE and `G-1` Student-t degrees of freedom; bias-correct with the standard jackknife formula.

Nested leave-division-out ridge:

- Hold out one ordered Census division per outer fold. Within each outer training set, hold out each remaining division once in the same order.
- Use training-only feature means and sample standard deviations with `ddof=1`.
- Center the training outcome. Minimize `mean((y-a-Xb)^2)+lambda*sum(b_j^2)` with cyclic coordinate descent in declared feature order:
  `b_j=sum(x_j*r_j)/(sum(x_j^2)+n*lambda)`.
- Select the smallest pooled inner RMSE, breaking ties toward the smaller lambda. Refit on the full outer-training set and pool one outer prediction per eligible row.

PCG32 Webb wild cluster bootstrap:

- Use the fixed-effects double-demeaned design. Studentize the full target coefficient with CR1.
- Fit the restricted model without the target. Generate `y* = restricted_fit + restricted_residual * cluster_weight`.
- Initialize PCG32 with unsigned wraparound: increment `2*stream+1`, state zero, one advance, add seed modulo `2^64`, one advance. Each output advances with multiplier `6364136223846793005`, xorshift/rotate as PCG32, then maps output modulo six to Webb weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Maintain one continuous stream; draw once per state in state-code order for every replicate. Record checkpoint rows only after a replicate completes.
- Count `abs(t*) >= abs(t_observed)` and use plus-one p-value `(1+count)/(1+B)`. Use nearest-rank quantiles for requested probabilities.

Grouped split conformal ridge:

- For each ordered outer division, use it as test. Among remaining divisions choose calibration by greatest row count then ascending division name; all other divisions are proper training.
- Fit ridge with the fixed lambda and the same training-only scaling as nested ridge.
- With `m` calibration residuals and miscoverage `alpha`, use rank `min(m, ceil((m+1)*(1-alpha)))`.

Trajectory PCA and source-year perturbation:

- Build variable-major/time feature blocks exactly as requested, standardize with sample SD, form covariance `Z'Z/(n-1)`, and run deterministic three-means on leading scores.
- For each omitted year, delete that time block and rebuild scaling, PCA, orientation, initialization, and clustering before computing ARI and aligned agreement.
- Enumerate source-year subsets by increasing subset size and lexicographic year tuple. Keep the strict dual-source cohort fixed. Refit primary and parallel double-demeaned models with CR1 inference for every subset. Compute absolute percent shift relative to the primary baseline, same-sign counts, ordinary median shift, and worst subset by greatest unrounded shift then earlier subset order.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Use this profile only for `protocol_id: PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Publication and models:

- Resolve county health and socioeconomic records by the active source filters and ordered revision priority.
- Build primary, balanced-panel, and machine-learning cohorts from the active nonmissing predicates. Preserve county and state order.
- Build total-effect, path-a, and direct/path-b OLS designs from the active exposure, mediator, outcome, covariates, transformations, references, and column order. Use unrounded fitted objects for bootstrap and sensitivity modules.

Difference GMM mediation:

- Create adjacent-change rows in entity then end-period order using the active lag instruments.
- For each equation use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- With residual `u` and cluster score `q_g=Z_g'u_g`, use the registered finite-sample cluster sandwich. For cross-equation covariance, use the corresponding cross-cluster score products.
- For indirect effect `theta=a*b`, compute `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t inference with cluster degrees of freedom.
- Compute first-stage partial F from full-versus-reduced residual sums of squares using the active instrument counts.
- For each delete-state diagnostic, rebuild rows and refit every affected equation from scratch.

Nested state ridge:

- Build base and augmented feature maps in exact active order.
- Standardize with training arithmetic means and population standard deviations; use a unit divisor for zero variance.
- Fit ridge with an unpenalized intercept by minimizing training SSE plus lambda times the squared non-intercept norm.
- Outer validation leaves one state out; inner validation leaves one remaining state out. Pool county squared errors before RMSE.
- Select the smallest unrounded inner RMSE, then smaller penalty; refit on all outer-training rows and report aligned grids and outer diagnostics.

Paired state wild bootstrap:

- For each target equation, fit the restricted model with only that target removed.
- Use unsigned xorshift32 with shifts `13,17,5`, masking to 32 bits after each xor. Maintain one continuous stream; draw states in ascending order and reuse each state sign across paired equations in that replicate. Odd output maps to `+1`, even to `-1`.
- Refit unrestricted models, recompute CR1 t statistics, use absolute exceedances with plus-one p-values, nearest-rank quantiles, and checkpoint states after completed replicates.

Grouped conformal, sensitivity, trajectory:

- Assign states in ascending order to cyclic partitions by index modulo the active partition count. For each test partition, use the preceding partition as calibration and the rest as proper training.
- Reduce calibration residuals to one maximum absolute residual per calibration state. With nominal coverage `c`, use rank `min(m, ceil((m+1)*c))`.
- For partial-R2 sensitivity, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`; apply the declared direction to adjust `b`, then compute adjusted indirect, direct, and proportion. Enumerate all R2 pairs and directions in request order.
- Aggregate balanced-panel measures to state-period means in declared order. Standardize with sample SD and covariance `Z'Z/(G-1)`. Run deterministic k-means and rebuild the full pipeline for leave-year-out ARI.

## country_burden_revision_audit_v1

Use this profile when the active template name is `country_burden_revision_audit_v1` or the prompt asks for the PHO country burden revision audit.

Reconciliation and quality:

- Resolve each requested label against `countries.canonical_name`, `portal_label`, and every pipe-separated alternate label. Require a unique match. Count alias resolutions when the requested label differs from the canonical name.
- Keep ISO3 identifiers stable and sort set-like ISO3 lists ascending when the template asks for a set.
- For requested countries, years, and indicators, select final country indicator records by highest revision, latest `released_at`, then deterministic observation-id tie break.
- Query `revisions` for domain `COUNTRY`, requested ISO3 values, requested burden indicators, panel outcome indicator when applicable, and requested years. Applied scale corrections should be reflected through later final revisions. Pending, withdrawn, or otherwise non-applied scale corrections do not authorize replacement; mark the affected cell as an unresolved scale-break anomaly.
- Count raw missing reference-year burden cells before excluding anomalies. Count anomaly cells separately. Complete the reference-year PCA matrix by deterministic column-mean imputation after quality exclusions unless the active request or methodology states a different imputation rule.

Burden PCA and clusters:

- Verify indicator directions from the catalog. Convert any higher-better burden input to adverse-burden orientation before PCA; leave higher-worse indicators as-is.
- Standardize each burden indicator column across usable countries with sample SD. Use covariance PCA and orient PC1 so higher burden indicators have positive aggregate loading; if orientation is ambiguous, use earliest maximum-absolute loading positive.
- Report top absolute loadings by descending absolute loading, tied by indicator id.
- For the requested three-segment grouping, run deterministic k-means on retained burden scores. Label clusters by PC1 centroid order as low, middle, and high burden. Sort high-burden membership when requested as a set.
- Evaluate silhouette for candidate k values in request/template order. Use Euclidean distances, singleton silhouette zero, largest unrounded mean silhouette, and smaller k on a tie.

Panel model and advisory:

- For each panel year, rebuild the burden score using the same indicator ordering, revision/anomaly handling, imputation convention, standardization convention, and PC1 orientation.
- Fit life expectancy on PC1 burden and region fixed effects. Report region fixed effects as true when region dummies are included.
- Use the controlled advisory vocabulary only. A statistically significant adverse gradient means a negative life-expectancy coefficient on the higher-burden PC1; choose the priority advisory. If the adverse gradient is present but not decisive, choose the monitoring advisory. If the coefficient is not adverse, choose the no-adverse-gradient advisory.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Use this profile only for `protocol_id: PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Release, WLS, and cluster jackknife:

- Resolve state direct health, socioeconomic, and alternate source records by active filters. For this profile, final release priority is greatest revision, latest release timestamp, then greatest record id unless overridden.
- Use the selected direct outcome-record sample size as the fixed positive reliability weight, including source-perturbation fits, unless the active request changes the weight rule.
- Fit weighted linear regression by multiplying rows by `sqrt(weight)`. Use HC3 for primary weighted inference and CR1 for cluster bootstrap statistics.
- Delete each registered Census division in order, refit from scratch, compute percent change relative to the full coefficient, then compute bias-corrected jackknife inference. Choose the most influential division by greatest unrounded absolute percent change, tied by earlier division order.

Weighted nested elastic net:

- Hold out each registered division as an outer fold and each remaining division as an inner fold.
- Build raw, transformed, squared, and interaction features in declared order.
- Compute training-only weighted feature means and weighted population SDs. Center `y` by weighted training mean without scaling it.
- Minimize `sum(w_i*(y_i-Z_i*b)^2)/(2*sum(w_i)) + lambda*(alpha*sum(abs(b_j)) + (1-alpha)*sum(b_j^2)/2)`.
- Cold-start every fold and penalty. Update in cyclic feature order with `S(rho_j, lambda*alpha)/(1+lambda*(1-alpha))`, where `rho_j` is the weighted mean partial residual product. Stop on the active tolerance or cycle cap.
- Pool unweighted validation squared errors for RMSE. Select by smallest unrounded RMSE then smaller penalty. Report nonzero counts using the active numerical cutoff.

Weighted wild bootstrap and conformal:

- Studentize the full weighted target coefficient with cluster CR1. Fit the weighted restricted model without the target and generate synthetic outcomes from restricted fitted values plus cluster-signed restricted residuals.
- Use one continuous unsigned xorshift32 stream with registered cluster order. Low bit one maps to `+1`, otherwise `-1`.
- Count `t* >= t_observed - delta` for the effective comparison tolerance and report plus-one p-value. Use type-seven quantiles for requested absolute-t probabilities.
- For conformal calibration, reuse each outer prediction and its selected penalty. For each held-out division, hold out every other training division once, cold-refit the same weighted elastic-net algorithm on remaining divisions, pool absolute residuals, and use rank `min(m, ceil((m+1)*coverage))`.

Trajectory and exhaustive source perturbation:

- Build variable-major/time-major blocks in declared order and state ASCII order. Standardize with sample SD; use covariance `Z'Z/(n-1)` and explained ratios relative to all eigenvalues.
- Run deterministic k-means on leading scores, handling empty clusters by moving the ASCII-first farthest assigned entity for the empty id.
- For every omitted year, rebuild the full PCA and clustering pipeline, align labels by maximum matches with lexicographic tie break, and report ARI and aligned changes.
- For source perturbation, order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. Enumerate masks from zero to `2^m-1`, replacing entity `j` when bit `j` is set. Refit WLS and HC3 for every scenario with fixed weights.
- Summarize by replacement-count strata. Select maximum unrounded shift, tied by smaller mask. Compute exact signed Shapley effects in paired-entity order and verify their sum equals all-alternate minus all-primary coefficient within tolerance.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Use this profile only for `protocol_id: PHO_COUNTY_PANEL_TRANSPORT_V1`.

Publication and panel construction:

- Resolve county health and socioeconomic final records independently under the active revision rule. Treat suppressed, invalid, or missing values as incomplete. Require valid RUCC and active regional/geography filters.
- Retain counties complete across every balanced year. Create adjacent-change panel rows ordered by county identifier then end period.
- Derive lagged levels, dynamic changes, reference indicators, and interactions exactly in declared term order.

Delete-state two-step GMM:

- In every full or delete-state fit, residualize the outcome, dynamic regressors, and instruments against intercept plus active baseline terms.
- First-step moments use identity weight. Build state scores from first-step residuals, compute the cluster moment covariance, and use the registered Moore-Penrose inverse with the active relative singular-value cutoff for the second step.
- Compute second-step coefficients from weighted linear moments and Hansen `J=n*g(theta)'Wg(theta)`.
- Refit both steps for each deleted state in state order. Bias-correct coefficients with the jackknife formula and retain maximum absolute delete-state shifts by coefficient.

State-blocked nested elastic net:

- Allocate states to outer folds by descending retained-entity counts, assigning each to the currently smallest fold and using lower fold id on equality. Sort state codes within folds. Repeat the same allocation rule inside each outer-training set for inner folds.
- Standardize declared continuous columns from training population moments, leave indicators unchanged, and keep the intercept unpenalized.
- Minimize `SSE/(2n)+alpha*(rho*sum(abs(beta_j))+0.5*(1-rho)*sum(beta_j^2))`. Cold-start coefficients at zero and intercept at the training outcome mean.
- Cycle intercept first, then coefficients in declared order using soft-threshold updates. Pool inner squared errors; select smallest unrounded RMSE, then smaller alpha, then smaller l1 ratio. Refit outer models and pool OOF metrics.

Bootstrap, conformal, trajectory, and source groups:

- For the state wild bootstrap, fit full unpenalized OLS and state-cluster CR1 for the target. Fit the restricted model without the target, generate state-signed residual outcomes using one continuous xorshift32 stream in ascending state order, recompute CR1 t, use absolute-tail plus-one p-values, nearest-rank quantiles, and record completed-replicate checkpoints.
- For grouped conformal, use outer OOF predictions in original analytic-row order. Each held-out fold calibrates on absolute OOF residuals from all other folds. Use rank `min(m, ceil((m+1)*coverage))`, then report fold, state, RUCC-band, prediction-bin, overall, and minimum-state diagnostics.
- For county trajectory PCA, build variable-major trajectories in declared variable and end-period order. Standardize with population moments and covariance `Z'Z/n`. For each candidate k, run deterministic farthest-first k-means, compute Euclidean silhouette with singleton zero, select largest unrounded mean silhouette then smaller k, and compute delete-state ARI after rebuilding the full pipeline.
- For source-group perturbation, remove exactly one declared group at a time. Reuse that fold's full-model selected hyperparameters without retuning. Apply identical preprocessing to remaining terms, retain all outer-fold RMSEs, pool squared errors, subtract full-model OOF RMSE, count worse folds, and rank by decreasing unrounded deterioration then declared group order.

Controlled decision:

- Complete all modules before evaluating gates.
- Evaluate gates using unrounded values in the exact order declared by the active request.
- Return only the active template's controlled decision value.
