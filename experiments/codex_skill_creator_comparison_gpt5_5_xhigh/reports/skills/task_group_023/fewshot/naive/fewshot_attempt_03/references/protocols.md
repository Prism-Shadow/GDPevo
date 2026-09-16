# Protocol Profiles

Read this file after parsing `analysis_request.json` when a request has a `protocol_id`, or when the prompt matches the country burden revision audit pattern. Activate a registered protocol profile only on exact case-sensitive `protocol_id` equality.

Do not carry solved values across invocations. Bind entities, measures, years, source filters, random seeds, grids, cutoffs, field names, and controlled output vocabulary from the future request. Apply overrides before touching evidence.

## Override Resolution

Use these merge rules for registered PHO protocol requests unless the effective request gives stricter rules:

- Direct root key `k` targets the canonical root key `k`.
- Inside a named section or module, child key `k` targets only the identical child path.
- Root `<section>_overrides` targets canonical `<section>` after stripping the terminal suffix.
- `module_overrides.<module>` targets the exact canonical top-level module.
- `reporting_overrides` targets canonical `reporting`.
- Recursively merge objects by exact key.
- Replace arrays whole; never concatenate, union, or patch by position.
- Replace explicit scalar, string, Boolean, and null values only at their exact path.
- Reject unknown targets, implicit aliases, key renames, incompatible types, and type coercion.
- Freeze one effective contract and use it consistently across every module.

## PHO_STATE_TRANSPORT_AUDIT_V1

Use for state-level adult-obesity/longevity transportability audits under `PHO_STATE_TRANSPORT_AUDIT_V1`.

Module order:

1. Release resolution and cohorts.
2. Delete-cluster fixed effects.
3. Nested ridge division cross-validation.
4. Wild cluster bootstrap.
5. Grouped split conformal.
6. Trajectory PCA clustering.
7. Source-year perturbation.
8. Controlled decision.

Reusable method:

- Resolve final health and socioeconomic publications by effective status, source, value type, validity, geography, and requested measure. Select greatest revision, latest release timestamp, then the profile's record-id tie rule. Treat suppressed, invalid, withdrawn, blank, and null analytical values as unavailable.
- Join resolved series by stable jurisdiction and year. Build complete, balanced, broad reference-year, and strict dual-source cohorts from the effective required fields. Preserve jurisdiction code, year, feature, division, and subset orders.
- Fixed effects: double-demean each active modeled variable by entity and time, then solve OLS without an intercept in declared predictor order. For each deleted state, remove the whole state, recompute all means, and refit from scratch.
- Jackknife: for `G` delete estimates, use the delete mean, `sqrt((G-1)/G * sum((b_delete-bbar)^2))`, bias correction `G*b_full-(G-1)*bbar`, and two-sided Student-t inference with `G-1` df. Pick extrema by unrounded coefficient, then state code.
- Nested ridge: hold out one ordered census division per outer fold; inside each outer training set hold out each remaining division in the same order. Standardize features using outer/inner training-only means and sample SD with ddof 1. Center the training outcome, keep intercept unpenalized, fit ridge by cyclic coordinate descent over the declared feature order, pool inner row-level squared errors by lambda, choose minimum RMSE then smaller lambda, refit, and pool one outer prediction per row.
- Wild bootstrap: use the fixed-effects design and CR1 cluster covariance. Fit the restricted model without the target, generate `y*` from restricted fitted values plus cluster-weighted restricted residuals, then refit unrestricted and recompute CR1 each replicate. Use the profile's PCG32/Webb weights, one continuous stream, cluster draws in state-code order, plus-one two-sided exceedance p-values, requested batch counts, and nearest-rank quantiles.
- Grouped conformal: for each ordered outer division, use it as test. Choose calibration among remaining divisions by greatest row count then ascending division name; train on the rest. Fit fixed-lambda ridge with the same scaling and solver rules. Use finite-sample rank `min(m, ceil((m+1)*(1-alpha)))`; intervals are inclusive.
- Trajectory PCA: build variable-major/time feature blocks, standardize by sample SD, covariance `Z'Z/(n-1)`, deterministic symmetric eigen/PCA orientation by earliest maximum-absolute loading, score all states, then run farthest-first deterministic k-means on leading scores. For leave-year stability, rebuild scaling/PCA/k-means from scratch and report ARI plus aligned agreement.
- Source-year perturbation: keep the strict dual-source cohort fixed. Enumerate requested year subsets by increasing size and lexicographic tuple order. Refit complete double-demeaned models separately for primary and parallel exposure series, recompute CR1 p-values, calculate absolute percent shifts against the baseline, count same-sign subsets, and choose the worst by unrounded shift then earlier subset order.
- Controlled decision: compute every module before applying gates. Evaluate predicates on unrounded values, preserve gate order, count passes, and apply only the request's classification mapping.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Use for county poverty-to-obesity mediation transportability audits under `PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Module order:

1. Publication and linked cohorts.
2. Primary mediation OLS models.
3. Difference GMM mediation.
4. Nested state ridge.
5. Paired state wild bootstrap.
6. State grouped conformal.
7. Partial-R2 sensitivity.
8. State trajectory PCA clustering.
9. Controlled precedence.

Reusable method:

- Select one record per entity-time-measure/source key with the effective ordered release priority. Count selected publication rows before analytical completeness exclusions when requested.
- Build total-effect, path-a, and direct/path-b primary-year OLS designs from the effective exposure, mediator, outcome, transformations, covariates, reference levels, and column order. Retain unrounded fitted objects for bootstrap and sensitivity.
- Difference GMM: create adjacent changes in entity then end-period order using the effective lag/instrument bindings. For each equation use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`. With cluster scores `Z_g'u_g`, use the registered finite-sample cluster sandwich. For two-equation indirect effect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t inference with cluster df. Compute first-stage partial F from full-vs-reduced RSS. Rebuild rows and refit for every delete-state diagnostic.
- Nested state ridge: use exact effective base and augmented feature orders. Within every fit standardize with training arithmetic means and population SD, using divisor 1 for zero variance; apply moments to held-out rows. Use an unpenalized intercept, pool county squared errors before RMSE, tie to smaller penalty, and report complete aligned inner grids and outer diagnostics for both feature maps.
- Paired state bootstrap: for each target equation, fit the restricted model with only that target removed, synthesize outcomes with state signs, refit unrestricted models, and recompute CR1 t statistics. Use unsigned xorshift32, one continuous stream, ascending state draw order, odd `+1` and even `-1`, paired signs reused across equations, plus-one two-sided p-values, nearest-rank order statistics, and checkpoint records after completed replicates.
- State grouped conformal: assign states in ascending order to cyclic partitions by index modulo the effective partition count. For each test partition, use the preceding partition for calibration and remaining partitions for proper training. Reduce calibration residuals to one maximum absolute residual per calibration state, rank by nominal coverage, build inclusive symmetric intervals, and aggregate by county rows.
- Partial-R2 sensitivity: from unrounded baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude = SE_b*sqrt(df*rY*rM/(1-rM))`. For each declared direction, compute adjusted path-b, indirect, direct, and proportion in the declared R2/direction order. Compute equal-strength positive tipping from unrounded inputs.
- State trajectory PCA: aggregate balanced-panel measures to state-period means in declared feature order. Standardize across states with sample SD, covariance `Z'Z/(G-1)`, orient PCA loadings, run deterministic farthest-first Lloyd k-means, and rebuild the whole pipeline for leave-period ARI.
- Controlled precedence: evaluate all predicates on unrounded values and return the first applicable controlled class.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Use for reliability-weighted state robustness/transportability audits under `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Module order:

1. Release and cohort.
2. Common weighted linear algebra.
3. Cluster jackknife.
4. Nested elastic net.
5. Wild cluster bootstrap.
6. Grouped conformal.
7. Trajectory PCA clustering.
8. Exhaustive source perturbation.
9. Controlled decision.

Reusable method:

- Resolve one eligible publication per effective key using filters and profile precedence; unavailable selected values are never zero-filled. Join by stable entity/time keys and preserve entity, time, feature, and cluster order.
- Weighted least squares: solve on `sqrt(w)*X` and `sqrt(w)*y` in declared column order. Use HC3 with weighted leverage and residuals, and CR1 with ordered cluster scores; inference uses residual df for HC3 and `G-1` df for CR1.
- Cluster jackknife: delete every registered cluster in order, refit unchanged weighted design, compute target percent changes against the full coefficient, bias-correct from delete estimates, and choose most influential by greatest unrounded percent change then earlier cluster order.
- Nested weighted elastic net: hold out each registered cluster externally and internally. Build transformed/squared/interaction features in exact order. In every fit compute weighted training means and weighted population SDs, center `y` by weighted mean, cold-start coefficients, and use cyclic coordinate descent with soft-thresholding. Pool unweighted validation squared errors before RMSE, tie to smaller lambda, count nonzero coefficients by the effective cutoff, and pool outer OOF metrics unweighted.
- Wild bootstrap: studentize full weighted target with CR1, fit the weighted restricted model without target, then use unsigned xorshift32 signs by cluster in registered order. Maintain one stream, record requested checkpoints, count with the effective tolerance if any, report plus-one p-value, and use type-seven quantiles when this profile requests them.
- Grouped conformal: reuse each outer center prediction and selected penalty. For an outer cluster, hold out each other cluster as calibration, cold-refit on the remaining clusters, pool absolute residuals, rank by nominal coverage, report ordered diagnostics, and choose worst coverage by smallest fraction then earlier order.
- Trajectory PCA: build declared variable/time blocks, standardize by sample SD, use covariance `Z'Z/(n-1)`, orient by earliest maximum-absolute loading, score retained components, run deterministic k-means with empty-cluster repair, and rebuild for every omitted time block. Align refit labels by best agreement before reporting changes.
- Exhaustive source perturbation: resolve alternate outcomes, order replaceable entities by descending absolute alternate-minus-primary difference then code, enumerate masks in increasing integer order, keep fixed reliability weights and design, refit WLS/HC3 for every scenario, summarize popcount strata, select maximum shift by unrounded shift then smaller mask, and compute exact signed Shapley contributions whose sum equals all-replacement minus all-direct coefficient.
- Controlled decision: complete all modules, evaluate unrounded predicates, and select the first failed module by the effective precedence.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Use for county dynamic panel transportability audits under `PHO_COUNTY_PANEL_TRANSPORT_V1`.

Module order:

1. Publication balanced panel.
2. Delete-state two-step GMM.
3. State-blocked nested elastic net.
4. State wild cluster bootstrap-t.
5. Cross-fold grouped conformal.
6. County trajectory PCA clustering.
7. Source-group perturbation.
8. Controlled precedence.

Reusable method:

- Filter county health and socioeconomic sources independently, resolve final records by effective release priority, require valid geography/RUCC attributes, retain counties complete across every balanced period, and create adjacent-change rows ordered by entity identifier then end period.
- Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. First-step uses identity moment weight. Build state scores from residuals, form `S`, apply the registered relative-cutoff Moore-Penrose inverse for second-step weight, compute second-step coefficients and Hansen J, and refit both steps for each deleted state. Bias-correct coefficients from delete estimates and report maximum absolute shifts in coefficient order.
- State-blocked nested elastic net: allocate states to folds by descending retained-entity counts, assigning to the currently smallest fold and lower fold id on equality; sort state codes within folds. Standardize continuous columns by training population moments, leave indicators unchanged, keep intercept unpenalized, traverse alpha/l1 grids in declared nested order, cold-start each fit, pool inner squared errors before RMSE, and tie to smaller alpha then smaller l1 ratio.
- Wild bootstrap-t: fit full unpenalized OLS and state-cluster CR1 for the target, fit restricted model without target, use xorshift32 signs over states in ascending order, use plus-one absolute-tail p-values, nearest-rank quantiles, and checkpoint records after completed replicates.
- Cross-fold grouped conformal: use nested-model OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds, use rank `min(m,ceil((m+1)*coverage))`, build inclusive symmetric intervals, and report fold, state, RUCC-band, prediction-decile, overall, and minimum-state diagnostics.
- County trajectory PCA clustering: build variable-major trajectories by declared variable and end-period order, standardize by population moments, use covariance `Z'Z/n`, orient PCA loadings, run farthest-first k-means for each candidate `k`, compute Euclidean silhouettes with singleton silhouette zero, select largest mean silhouette then smaller `k`, and rebuild the pipeline for every delete-state ARI.
- Source-group perturbation: for each declared source group and outer fold, remove exactly those terms, reuse the full-model selected hyperparameters without retuning, pool fold RMSEs, subtract full-model OOF RMSE for deterioration, count worse folds, and rank groups by decreasing unrounded deterioration then declared order.
- Controlled precedence: evaluate all six gates on unrounded values and choose the first applicable controlled decision from the request.

## Country Burden Revision Audit

Use this non-protocol workflow when the request asks for an international country burden revision/PCA/clustering/panel audit and the template resembles `country_burden_revision_audit_v1`.

Reusable method:

- Reconcile requested country labels against portal country metadata, including aliases, and report only uniquely resolved identifiers in the template's requested order or sorted set order.
- Resolve applicable revision events from `/data/revisions`; separate applied from non-applied event ids according to event status and request scope. Apply only applicable `APPLIED` revisions before modeling.
- Treat unresolved scale breaks/anomalies as unavailable cells. Count raw missing reference-year cells before anomaly exclusions, count anomaly cells separately, then impute only as required by the methodology or request. Do not impute by guessing.
- Build the reference-year burden matrix using the requested indicator order. Standardize indicators, orient PC1 so higher burden indicators load positively when the methodology implies a burden direction, and report requested top absolute loadings by absolute value with identifier tie-breaks.
- For clustering, evaluate the requested candidate `k` values with deterministic k-means and silhouette. Build requested burden labels from cluster PC1/order semantics, not from arbitrary cluster ids.
- For the panel model, rebuild country-year PC1 burden scores across the requested panel years, include region fixed effects when requested, and report the life-expectancy association, standard error, p-value, R-squared, and advisory from unrounded values.
