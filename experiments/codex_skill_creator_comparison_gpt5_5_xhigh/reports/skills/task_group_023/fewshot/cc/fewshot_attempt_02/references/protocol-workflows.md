# PHO Protocol Workflows

This file contains reusable method semantics inferred from the staged examples. It intentionally excludes solved numeric outputs, entity membership lists, fitted coefficients, and final classifications from the training answers. Bind all entities, measures, years, random seeds, grids, cutoffs, labels, and output vocabulary from the current request and template.

## Common Protocol Activation

Use an exact, case-sensitive `protocol_id` match. Do not activate a profile because the family, subject matter, or module names look similar. If the request has overrides, resolve them first into a frozen effective request and run every module against that same request.

Recognized protocols:

- `PHO_STATE_TRANSPORT_AUDIT_V1`
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`
- `PHO_COUNTY_PANEL_TRANSPORT_V1`

Also use the country workflow for `country_burden_revision_audit_v1` style templates and prompts asking for country burden, revision reconciliation, PCA segmentation, and region-adjusted panel association.

## `PHO_STATE_TRANSPORT_AUDIT_V1`

Purpose: audit whether a state-level health exposure is a transportable longevity signal over a multi-year state panel.

Module order:

1. Release resolution and cohorts.
2. Delete-cluster fixed effects.
3. Nested leave-one-census-division-out ridge.
4. PCG32 Webb wild cluster bootstrap.
5. Grouped split conformal ridge.
6. Trajectory PCA clustering with leave-year-out stability.
7. Source-year perturbation.
8. Controlled decision.

Reusable semantics:

- Resolve state health and socioeconomic records by the effective filters. For this protocol's default final-release rule, select greatest revision, latest release timestamp, then lowest record identifier. Keep invalid, withdrawn, suppressed, blank, or null analytic values unavailable.
- Build the core balanced cohort from entities complete for the effective outcome, primary exposure, and required socioeconomic fields in every analysis year. Build the broad reference cohort from complete reference-year outcome and ordered ridge features. Build strict dual-source cohorts from complete outcome, primary exposure, parallel exposure, and adjustments in every requested year.
- Fixed-effects module: double-demean each modeled variable by entity and year, fit OLS without intercept in declared predictor order, delete one state at a time, recompute all means, and refit from scratch.
- Jackknife: for `G` delete estimates, compute `bbar`, `SE=sqrt((G-1)/G*sum((b_g-bbar)^2))`, bias-corrected `G*b_full-(G-1)*bbar`, and two-sided Student-t inference with `G-1` degrees of freedom. Choose coefficient extrema by unrounded coefficient, then entity code.
- Nested ridge: outer folds follow the declared census division order; inner folds leave out each remaining division. Standardize features from training sample means and sample standard deviations. Use an unpenalized intercept and ridge objective `mean((y-a-Xb)^2)+lambda*sum(b_j^2)`. Pool inner validation squared errors at row level; choose smallest unrounded RMSE, then smaller lambda.
- Wild bootstrap: use the fixed-effects design and CR1 state-cluster variance. Fit the restricted model without the target, then generate synthetic outcomes from restricted fitted values plus state-weighted restricted residuals. Use the PCG32 Webb generator described in `statistical-methods.md`; keep one continuous stream; draw weights in entity-code order; record requested checkpoints and batch counts only after completed replicates.
- Grouped conformal: for each outer division, choose the calibration division among the remaining groups by greatest row count, then ascending name. Fit ridge using the same scaling rules. With sorted calibration residuals, use one-based `min(m, ceil((m+1)*(1-alpha)))`; aggregate coverage and width by outer-test row counts.
- Trajectory PCA: build variable-major/time-major feature blocks as declared, standardize by sample SD, use covariance `Z'Z/(n-1)`, orient eigenvectors so the earliest maximum-absolute loading is positive, score all states, and run deterministic farthest-first k-means. For each omitted year, rebuild the whole PCA and clustering pipeline, then compute adjusted Rand index and aligned agreement.
- Source-year perturbation: enumerate requested time subsets by increasing size and lexicographic tuple order. Keep the strict cohort fixed. For each subset refit primary and parallel double-demeaned models, recompute CR1 p-values, absolute percent shifts, same-sign counts, medians, and worst subset by unrounded shift then subset order.
- Decision: evaluate all six gates on unrounded values in the request's named gate order. Count passes and apply only the controlled mapping in the effective request.

## `PHO_COUNTY_MEDIATION_TRANSPORT_V1`

Purpose: audit county poverty-to-obesity mediation through physical inactivity across reproducibility, prediction, bootstrap, calibration, confounding sensitivity, trajectory stability, and controlled conclusion modules.

Module order:

1. Publication and linked cohorts.
2. Primary mediation OLS models.
3. Difference GMM mediation.
4. Nested leave-state-out ridge.
5. Paired state wild bootstrap.
6. State-grouped conformal.
7. Partial-R2 mediation sensitivity.
8. State trajectory PCA clustering.
9. Controlled precedence.

Reusable semantics:

- Filter each county source by effective region, year, measure, value type, release status, and declared revision priority. Selected suppressed or null health rows count as publication evidence but fail analytic completeness.
- A basic-complete year requires selected health values, poverty, median income, bachelors, and valid RUCC. Build primary, balanced-panel, and machine-learning cohorts from the effective completeness predicates.
- Primary mediation models use the effective total-effect, path-a, and direct/path-b OLS designs. Use transformed income and RUCC reference indicators exactly as declared. Retain unrounded fitted objects for bootstrap and sensitivity.
- Difference GMM: create adjacent-change rows ordered by entity then end period. Use `W=(Z'Z)^-1` and `beta=(X'ZWZ'X)^-1 X'ZWZ'y`. Compute cluster sandwich variances by state, including cross-equation score products for the indirect effect. Delta method for `theta=a*b`: `b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`. Use Student-t inference with state-cluster degrees of freedom. Delete-state diagnostics rebuild rows and refit from scratch in state order.
- Nested ridge: use exact base and augmented feature orders. Standardize from training arithmetic means and population standard deviations, with unit divisor for zero variance. Outer folds leave one state out; inner folds leave one remaining state out. Pool county squared errors before RMSE and break lambda ties toward the smaller penalty.
- Paired wild bootstrap: for each target equation, fit the restricted model with only that target removed. Use one continuous xorshift32 stream, drawing one sign per state in ascending state order per replicate and reusing the paired signs across equations. Map odd state to `+1`, even to `-1`. Use plus-one two-sided p-values and nearest-rank quantiles.
- State-grouped conformal: sort states ascending, assign cyclic partitions by index modulo the partition count, use the preceding partition for calibration, and reduce calibration residuals to one maximum absolute residual per state. Use finite-sample one-based ranks and aggregate county coverage plus widths by cycle and state.
- Partial-R2 surface: from unrounded baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`. For each requested direction and R2 pair, adjust path-b, indirect, direct, and proportion in the declared order. Compute the equal-strength positive tipping root from unrounded inputs.
- State trajectory PCA: aggregate balanced-panel measures to state-period means in declared feature order, use covariance `Z'Z/(G-1)`, orient loadings, deterministic farthest-first k-means, and leave-period ARI stability.
- Decision: finish all modules, evaluate predicates on unrounded values, count supported modules, and return the first applicable class in the request's precedence order.

## `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`

Purpose: audit a reliability-weighted state association under weighted linear modeling, grouped prediction, bootstrap, calibration, trajectory, source perturbation, and controlled failure precedence.

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

Reusable semantics:

- Resolve state publications by effective filters; for this protocol's default final-release rule, select greatest revision, latest release timestamp, then greatest record identifier. The selected direct outcome sample size is the fixed positive reliability weight unless the request says otherwise; keep it fixed even when replacing outcome source in perturbation.
- Weighted linear algebra: with design `X`, outcome `y`, and positive weights `w`, solve WLS on `sqrt(w)`-weighted rows. HC3 uses weighted hat diagonals and weighted residuals with two-sided `n-k` Student-t inference. CR1 uses ordered cluster scores with finite-sample factor `[G/(G-1)]*[(n-1)/(n-k)]` and `G-1` degrees of freedom.
- Cluster jackknife: fit the full weighted design, delete each registered cluster in order, refit unchanged design, compute percent changes from the unrounded full target coefficient, bias-corrected coefficient, jackknife SE, and t test.
- Nested elastic net: outer and inner folds hold out registered clusters. Build raw, transformed, squared, and interaction features in declared order. Standardize by training-only weighted population moments, center `y` by training weighted mean, keep intercept unpenalized, cold-start every fit, and use cyclic coordinate descent with soft-thresholding. Pool unweighted inner validation squared errors before RMSE; choose smallest RMSE then smaller penalty.
- Wild bootstrap: studentize the weighted full target coefficient with cluster CR1. Fit weighted restricted model without target; synthesize outcomes with xorshift32 cluster signs in registered cluster order; recompute full WLS and CR1 each replicate. Count `t* >= observed - delta` if a tolerance is declared; use type-seven quantiles for this protocol.
- Grouped conformal: reuse nested elastic-net outer predictions and selected penalties. For each outer cluster, hold out each other training cluster once for calibration, pool absolute residuals, use one-based rank `ceil((m+1)*coverage)`, and report ordered diagnostics plus pooled coverage and weighted mean width.
- Trajectory PCA: build declared variable/time blocks in entity ASCII order, standardize with sample SD, use covariance `Z'Z/(n-1)`, orient loadings, run deterministic k-means, handle empty clusters by moving the ASCII-first farthest entity, and compute leave-year ARI plus aligned changes.
- Exhaustive source perturbation: resolve alternate outcome source with module filters. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. Enumerate masks from `0` to `2^m-1`; replace entity `j` when `mask & (1<<j)` is nonzero; retain fixed direct weights and design. Report popcount strata, stable scenario counts, max shift tied by smaller mask, and exact signed Shapley effects whose sum equals all-replacement minus no-replacement coefficient.
- Decision: evaluate flags in the request's precedence order and return the first unsatisfied module's controlled conclusion, or the all-robust value.

## `PHO_COUNTY_PANEL_TRANSPORT_V1`

Purpose: audit a county panel dynamics model across two-step GMM, blocked nested elastic net, wild bootstrap, grouped conformal calibration, county trajectory clustering, source-group perturbation, and controlled deployment decision.

Module order:

1. Publication balanced panel.
2. Delete-state two-step GMM.
3. State-blocked nested elastic net.
4. State wild cluster bootstrap t.
5. Cross-fold grouped conformal.
6. County trajectory PCA clustering.
7. Source-group perturbation.
8. Controlled precedence.

Reusable semantics:

- Resolve county health and socioeconomic records independently by effective scope, final status, value type, revision priority, nonsuppression, nonmissing values, valid RUCC, and complete balanced periods.
- Create adjacent-change panel rows ordered by entity identifier then end period. Derive lagged levels, dynamic changes, period indicators, RUCC reference indicators, and declared interactions in exact order.
- Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms. First step uses identity moments. Build state score covariance and second-step weight from the Moore-Penrose inverse with the declared relative singular cutoff. Compute Hansen J and refit both steps for each state deletion. Bias-correct dynamic coefficients with `G*theta_full-(G-1)*mean(theta_delete)`.
- State-blocked nested elastic net: allocate states by descending retained-entity counts to the currently smallest fold, lower fold id on equality, and sorted states within folds. Repeat allocation inside each outer-training set. Standardize continuous terms by training population moments; leave indicators unchanged. Cold-start intercept at training outcome mean and coefficients at zero. Traverse the alpha/l1 grid in declared order, pool inner squared errors, and break ties by smaller alpha then smaller l1 ratio.
- Wild bootstrap: fit full unpenalized OLS over the common design and state-cluster CR1 for the target, fit restricted model without target, draw xorshift32 state signs in ascending state order, and use plus-one absolute-tail p-values plus nearest-rank quantiles.
- Cross-fold conformal: use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. Use rank `min(m, ceil((m+1)*coverage))`. Report fold, state, RUCC-band, and prediction-bin diagnostics. Sort prediction bins by prediction then declared identifiers; signed gap is prediction mean minus observation mean.
- County trajectory PCA: build variable-major county trajectories by declared variable and end-period order, standardize by population moments, use covariance `Z'Z/n`, orient eigenvectors, run deterministic farthest-first k-means for each candidate cluster count, compute Euclidean silhouette with singleton value zero, and select largest mean silhouette then smaller k. Delete-state stability rebuilds the full trajectory pipeline at the selected k.
- Source-group perturbation: for every source group and outer fold, remove exactly that group's terms, reuse that fold's full-model selected hyperparameters without retuning, solve with the same preprocessing, and compare pooled RMSE to the full OOF reference. Rank groups by decreasing unrounded deterioration, tied by declared source-group order.
- Decision: evaluate all six gates on unrounded values and apply the request's precedence mapping.

## Country Burden Revision Audit

Use this workflow when the request asks for a 2022-style country burden cross-section plus a panel audit and the template resembles `country_burden_revision_audit_v1`.

Reusable semantics:

- Reconcile every requested country label against the `countries` dataset using exact matches to `portal_label`, `canonical_name`, and pipe-delimited `alternate_labels`. Count alias resolutions when the requested label differs from the canonical name. Output unique ISO3 identifiers sorted ascending when the template asks for a set-like list.
- Resolve country indicator rows for the requested burden indicators and panel outcome from `country_indicators`, using final releases and revision precedence unless the request states otherwise. Applied revision notices can explain later final values; pending, withdrawn, or otherwise non-applied notices do not authorize replacement.
- Build the quality audit from `revisions` and indicator quality flags over the requested entities, indicators, and years. Treat unresolved anomaly or scale-break cells as unavailable analytic values. Count raw missing cells before anomaly exclusions; count imputed cells after applying quality exclusions.
- For the reference-year burden PCA, create one row per resolved country and one column per requested burden indicator. Impute unavailable reference-year burden cells by the indicator mean over available resolved countries for that same year. Standardize columns, run PCA, and orient PC1 so higher adverse burden indicators have a positive net loading. Report top absolute PC1 loadings by descending absolute loading, with indicator id as the exact tie-break.
- For requested three-segment grouping, cluster on the retained burden scores and label the three clusters by mean PC1 burden as `LOW_BURDEN`, `MIDDLE_BURDEN`, and `HIGH_BURDEN`. Separately evaluate candidate k values requested by the template, usually 2 through 5, with deterministic k-means and average silhouette.
- For the panel model, score country-year burden consistently with the reference burden direction, join to the panel outcome, omit rows with unavailable outcome or burden score, and run OLS with region fixed effects when requested. Report coefficient, standard error, p-value, R-squared, and whether region effects were included.
- Advisory: use the controlled template values. A statistically supported adverse gradient for life expectancy versus burden supports the priority value; an adverse but weak gradient supports monitoring; otherwise use the no-adverse-gradient value.
