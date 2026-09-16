# Protocol Method Profiles

These profiles are reusable method semantics only. Activate a profile only when the future `analysis_request.json` has the exact case-sensitive `protocol_id`. Bind all entities, measures, years, sources, grids, seeds, cutoffs, output names, and decision labels from the active request.

## Common Override Resolution

For known PHO protocol tasks, resolve one effective request before computation:

- Direct root key `k` targets canonical root `k`.
- A root key named `<section>_overrides` targets canonical `<section>`.
- `module_overrides.<module>` targets the exact top-level module of the same name.
- `reporting_overrides` targets reporting.
- Recursively merge object keys by exact name.
- Replace arrays whole; do not concatenate, union, or position-patch them.
- Replace scalars, strings, booleans, and nulls only at the exact resolved path.
- Reject unknown targets, implicit aliases, type coercion, and incompatible overrides.

## PHO_STATE_TRANSPORT_AUDIT_V1

Module order: release/cohorts, delete-cluster fixed effects, nested ridge division CV, wild cluster bootstrap, grouped split conformal, trajectory PCA clustering, source-year perturbation, controlled decision.

- Release resolution: filter by effective status, source, value type, geography, validity, and measure. Select greatest revision, latest release timestamp, then the profile's stable identifier tie direction. Suppressed, invalid, withdrawn, blank, and null values are unavailable.
- Fixed effects: double-demean each modeled variable by active entity and time means plus grand mean. Fit OLS without an intercept in declared predictor order. Delete one state/cluster by recomputing all means and refitting.
- Jackknife: for delete estimates `b_g` and mean `bbar`, use `SE=sqrt((G-1)/G*sum((b_g-bbar)^2))`, bias-corrected `G*b_full-(G-1)*bbar`, and two-sided Student t with `G-1` df.
- Nested ridge: outer folds leave one ordered census division out; inner folds leave one remaining division out. Use training-only means and sample SD (`ddof=1`) for features, center y, and keep intercept unpenalized. Pool inner validation squared errors by row, choose smallest RMSE then smaller lambda, refit on all outer-training rows, and pool one prediction per row.
- PCG32 Webb bootstrap: use the request seed and stream to initialize PCG32. Draw one index per cluster in entity order for every replicate, mapping modulo six to Webb weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`. Fit the restricted model without the target, generate `y*`, refit unrestricted FE, recompute CR1, count two-sided exceedances, and use nearest-rank quantiles.
- Grouped conformal: for each outer division, use it as test. Choose calibration among remaining divisions by greatest row count then ascending name; use the rest for proper training. Use fixed-lambda ridge and inclusive symmetric intervals with rank `min(m, ceil((m+1)*(1-alpha)))`.
- Trajectory PCA: build variable/year features in declared order, standardize with sample SD, covariance `Z'Z/(n-1)`, deterministic oriented eigenvectors, farthest-first three-means, canonical labels, and leave-year-out ARI/agreement.
- Source-year perturbation: enumerate requested year subsets by increasing size then lexicographic tuple order. Keep the strict cohort fixed, refit primary and parallel double-demeaned models for each subset, compute same-sign counts and percent shifts from unrounded coefficients, and choose worst subset by greatest unrounded shift then earlier subset order.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Module order: publication/cohorts, primary mediation models, difference GMM mediation, nested state ridge, paired state wild bootstrap, state-grouped conformal, partial-R2 sensitivity, state trajectory PCA clustering, controlled precedence.

- Publication/cohorts: filter health and socioeconomic sources by effective request fields and ordered release priority. Selected suppressed or null health records count as publication evidence when requested but are incomplete analytically. Build primary, balanced-panel, and machine-learning cohorts from the active completeness predicates.
- Primary models: build total-effect, path-a, and direct/path-b OLS designs from the active exposure, mediator, outcome, transformations, covariates, and reference indicators. Keep unrounded fit objects for bootstrap and sensitivity.
- Difference GMM: create adjacent-change rows in entity then end-period order. For each equation use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`. Cluster by state; for indirect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student t inference with cluster df. Refit from scratch for delete-state diagnostics.
- Nested state ridge: feature arrays follow request order. Standardize with training arithmetic means and population SD, using divisor one for zero variance. Leave one state out for outer folds and one remaining state out for inner folds. Pool row squared errors, choose smallest RMSE then smaller penalty, and report aligned grids.
- Paired state wild bootstrap: use restricted models, unsigned xorshift32, one continuous stream, state order ascending, odd PRNG state maps to +1 and even to -1, reuse the paired state signs across target equations, plus-one p-values, nearest-rank order statistics, and bootstrap-t inversion.
- State-grouped conformal: assign states in ascending order to cyclic partitions by index modulo partition count. For test partition j, use the registered preceding calibration partition and the others for training. Reduce calibration residuals to one maximum absolute residual per calibration state before the finite-sample rank.
- Partial-R2 sensitivity: from unrounded baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`. For each direction, adjust `b`, then recompute indirect, direct, and proportion in declared R2/direction order. Compute equal-strength tipping from unrounded inputs.
- State trajectory PCA: aggregate balanced-panel county measures to state-period means in declared order, standardize with sample SD, use covariance `Z'Z/(G-1)`, orient eigenvectors by earliest max-absolute loading, run deterministic farthest-first k-means, and recompute full pipeline for leave-period ARI.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Module order: release/cohort, common weighted linear algebra, cluster jackknife, nested elastic net, wild cluster bootstrap, grouped conformal, trajectory PCA clustering, exhaustive source perturbation, controlled decision.

- Release/cohort: select greatest revision, latest release timestamp, then greatest stable record ID unless the active request overrides. Fixed reliability weights come from the selected direct outcome sample size and remain fixed in source perturbation fits.
- WLS and inference: use `sqrt(w)` transformed design and outcome. HC3 uses weighted leverage and weighted residuals with `n-k` df. CR1 uses ordered cluster scores and `G-1` df.
- Cluster jackknife: delete each registered census division in order, refit weighted design, compute percent change from the unrounded full coefficient, bias-corrected coefficient, jackknife SE, and most influential division by greatest unrounded change then earlier order.
- Nested elastic net: outer and inner folds follow registered cluster order. Build declared raw/transformed/squared/interaction features. Use training-only weighted means and weighted population SD. Center y by training weighted mean. Cold-start every penalty; cyclic coordinate descent uses the elastic-net soft-threshold update. Pool unweighted inner validation squared errors, choose smallest RMSE then smaller lambda, refit cold, and pool unweighted outer metrics.
- Wild cluster bootstrap: fit weighted restricted model without target, draw xorshift32 signs by cluster order, generate untransformed `y*`, refit WLS, recompute CR1, record absolute t checkpoints, count with the active comparison tolerance, and use type-seven quantiles.
- Grouped conformal: reuse each outer prediction and selected penalty. For held-out cluster d, calibrate by leaving each other training cluster out once, pooling absolute residuals. Rank by nominal coverage, report ordered cluster diagnostics, and choose worst coverage by smallest fraction then earlier cluster order.
- Trajectory PCA/clustering: build variable-major/time-major blocks, standardize by sample SD, orient retained components, run farthest-first k-means with empty-cluster repair if needed, and report leave-year stability with aligned assignment changes.
- Exhaustive source perturbation: order paired alternate-source entities by descending absolute alternate-minus-primary difference then entity code. Enumerate masks from `0` to `2^m-1`, keep fixed direct weights, refit WLS and HC3, summarize by popcount, choose maximum shift by unrounded shift then smaller mask, and compute signed exact Shapley effects whose sum equals all-replacement minus no-replacement coefficient.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Module order: publication balanced panel, delete-state two-step GMM, state-blocked nested elastic net, state wild cluster bootstrap, cross-fold grouped conformal, county trajectory PCA clustering, source-group perturbation, controlled precedence.

- Balanced panel: resolve county health and socioeconomic sources independently by active final-release priority. Require nonsuppressed/nonmissing health, requested socioeconomic fields, and valid RUCC. Create adjacent-change rows ordered by entity ID then end period; derive lagged levels, changes, reference indicators, and interactions in declared order.
- Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus active baseline terms. First-step uses identity moment weight. Build state-score covariance, use the registered Moore-Penrose inverse with relative singular cutoff for second-step weight, compute Hansen J, and refit both steps for every state deletion. Bias-correct coefficients with `G*full-(G-1)*mean(delete)`.
- State-blocked nested elastic net: allocate states to folds by descending retained-entity counts, assigning to the currently smallest fold with lower fold ID on ties; sort state codes inside folds. Standardize continuous columns from training population moments, leave indicators unchanged, and keep intercept unpenalized. Traverse alpha/l1 grid in declared order; select by inner RMSE, then smaller alpha, then smaller l1 ratio.
- State wild bootstrap: use full unpenalized OLS with state CR1, restricted model without target, unsigned xorshift32 signs by ascending state, absolute-tail plus-one p-value, nearest-rank quantiles, and requested checkpoints.
- Cross-fold grouped conformal: use outer OOF predictions in analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds with rank `min(m, ceil((m+1)*coverage))`. Report fold, state, RUCC-band, prediction-decile, overall, and minimum-state coverage.
- County trajectory PCA/clustering: build variable-major trajectories by declared variable and end-period order, standardize by population moments, covariance `Z'Z/n`, oriented eigenvectors, farthest-first k-means for every candidate k, Euclidean silhouette with singleton value zero, select largest unrounded mean silhouette then smaller k, and recompute pipeline for each delete-state ARI.
- Source-group perturbation: remove exactly one declared source group at a time, reuse each outer fold's full-model selected hyperparameters without retuning, preprocess remaining terms identically, pool outer RMSEs, subtract full-model OOF RMSE, count worse folds, and rank by decreasing unrounded deterioration then declared group order.
