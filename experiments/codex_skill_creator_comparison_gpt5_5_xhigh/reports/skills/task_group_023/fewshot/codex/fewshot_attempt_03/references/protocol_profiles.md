# PHO Protocol Profiles

These are reusable method profiles inferred from the five training examples. They are not solved answers. Bind all entities, variables, years, grids, seeds, thresholds, labels, and output names from the future request/template.

## Override And Instance Rules

- Activate an exact protocol profile only when `analysis_request.json.protocol_id` equals the listed id exactly.
- Resolve one effective request before data access or computation.
- Apply direct keys to identical canonical keys. Apply `<section>_overrides` to the same section with only the terminal suffix removed. Apply `module_overrides.<module>` only to that exact module.
- Deep-merge objects by exact keys. Replace arrays whole. Replace scalars, strings, booleans, and nulls only at their exact path. Reject inferred aliases, position patches, unknown targets, and type coercion.
- Never reuse train output values, train cohorts, train classifications, or task-local constants. Recompute every invocation.

## PHO_STATE_TRANSPORT_AUDIT_V1

Purpose: state-level transportability audit of an exposure-outcome longevity signal across release resolution, fixed effects, ridge prediction, bootstrap, conformal calibration, trajectory clustering, source/year perturbation, and controlled gates.

Module order:

1. Resolve final health and socioeconomic releases, then build core balanced, broad reference, and strict dual-source cohorts from effective completeness rules.
2. Delete-cluster fixed effects: double-demean outcome and predictors by entity and time, fit OLS without intercept, delete each state cluster in entity-code order, recompute demeaning and refit. Jackknife uses delete-estimate mean, finite-cluster SE, bias correction, and a two-sided Student-t test with cluster minus one degrees of freedom.
3. Nested ridge by census division: outer leave-one-division-out; inner leave-one-remaining-division-out; training-only feature scaling; unpenalized intercept; row-pooled inner RMSE; tie to smaller penalty.
4. Wild cluster bootstrap: use the same fixed-effect design, CR1 studentization, restricted model without the target, PCG32 with the requested seed/stream, Webb six-point weights in entity-code order, plus-one p-value, batch exceedance counts, and requested nearest-rank quantiles.
5. Grouped split conformal: for each outer division, choose the calibration division from remaining groups by greatest row count then ascending group name unless overridden; fit ridge with the fixed penalty; use finite-sample absolute-residual rank; aggregate coverage and width by test rows.
6. Trajectory PCA clustering: build variable-major/time-major state trajectories, sample-standardize columns, covariance PCA, deterministic farthest-first three-means on retained scores, and leave-year-out stability with ARI plus aligned agreement.
7. Source-year perturbation: keep the strict cohort fixed, enumerate requested year subsets by size then lexicographic tuple order, refit primary and parallel exposure fixed-effect models, compute percent shifts, same-sign summaries, and worst subset by unrounded shift then earlier order.
8. Controlled decision: evaluate every request gate on unrounded values in declared module order.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Purpose: county-level poverty, mediator, and outcome mediation audit with linked cohorts, IV/GMM changes, prediction transport, paired bootstrap, grouped conformal calibration, partial-R2 sensitivity, state trajectory clustering, and controlled conclusion.

Module order:

1. Resolve county health and socioeconomic publications independently; count selected rows by year; build primary year, balanced panel, and machine-learning complete cohorts.
2. Fit primary-year OLS total, path-a, and direct/path-b models from the effective terms, transformations, RUCC references, and column order. Preserve unrounded fitted objects for bootstrap and sensitivity.
3. Difference GMM mediation: create adjacent-change rows in entity then period order; use lagged levels as instruments as requested; compute IV/GMM coefficients, finite-sample state-cluster sandwich, cross-equation covariance for indirect effect, first-stage partial F, confidence intervals, and delete-state diagnostics.
4. Nested state ridge: compare base and augmented feature maps with training-only standardization, leave-one-state-out outer folds, leave-one-state-out inner folds, row-pooled inner RMSE, smaller-penalty ties, and pooled out-of-fold RMSE plus state-win count.
5. Restricted-null paired state bootstrap: for each target equation remove only the target term in the restricted model; draw one xorshift32 sign per state per replicate and reuse signs across paired equations; record checkpoints after completed replicates.
6. State grouped conformal: assign states in ascending order cyclically to partitions, use the preceding partition for calibration, reduce calibration residuals to one maximum per calibration state, and aggregate cycle and state coverage.
7. Partial-R2 sensitivity: enumerate declared mediator and outcome R2 grids and direction order. Use baseline path-a, path-b, path-b SE, residual df, total effect, and the request's sign preservation predicates.
8. State trajectory PCA: aggregate balanced counties to state-period means in declared year/feature order; sample-standardize across states; deterministic PCA and k-means; leave-year-out ARI.
9. Controlled conclusion: count supported predicates and choose the first class in the request's precedence.

## Country Burden Revision Audit

Trigger when the template resembles `country_burden_revision_audit_v1` or the request asks for country label reconciliation, burden-indicator PCA, silhouette cluster selection, and a region-adjusted panel association.

Reusable recipe:

1. Reconcile every requested country label to one ISO3 through canonical name, portal label, or alternate labels. Count aliases where the requested label is not the canonical country name.
2. Pull final country indicator records for the requested reference cross-section and panel years. Resolve revisions by effective release precedence. Audit applied versus non-applied revision events that match requested entities, fields, and years.
3. Mark unresolved anomaly or scale-break cells from quality flags/revision evidence. Count raw missing cells before anomaly exclusions, then impute remaining required PCA cells by a deterministic indicator-level rule chosen from the request/methodology. Keep an audit count of imputed cells.
4. Orient burden indicators so higher PC1 means higher burden. For the training pattern, the requested burden indicators are already unfavorable except life expectancy, which is panel outcome rather than PCA burden input.
5. Standardize completed cross-section columns, run covariance PCA, orient PC1 so the earliest maximum-absolute burden loading is positive, and report top absolute loadings using indicator-id tie breaks.
6. For requested three-segment reporting, run deterministic k-means on retained burden scores and label segments by mean PC1 burden: low, middle, high. Separately compute candidate-k silhouettes for the requested candidate range and tie to smaller k.
7. Build the requested country-year panel, recomputing PC1 burden scores for each year with the same indicator ordering and imputation policy. Fit life expectancy on PC1 plus region fixed effects when requested; report coefficient, SE, p-value, R-squared, and advisory from the template predicates.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Purpose: reliability-weighted state association audit with WLS/HC3, delete-division jackknife, nested weighted elastic net, restricted-null division bootstrap, division conformal calibration, trajectory PCA, exhaustive source perturbation, Shapley attribution, and first-failed decision.

Module order:

1. Resolve releases and cohorts. Keep the selected direct outcome sample size as the fixed positive reliability weight, including source-perturbation fits, unless overridden.
2. Common weighted linear algebra: fit WLS by multiplying rows by square-root weights. HC3 uses weighted leverages and weighted residuals. CR1 uses ordered cluster scores with finite-sample factors and cluster minus one degrees of freedom.
3. Cluster jackknife: delete each census division in registered order, refit WLS, compute percent changes against the full target coefficient, bias-correct with delete means, and test the bias-corrected coefficient.
4. Nested weighted elastic net: leave one division out; inner folds over remaining divisions; build transformed features in declared order; weighted training means and weighted population SDs; cold-start coordinate descent for every penalty and fold; row-pooled unweighted validation RMSE; report nonzero counts and cycles.
5. Wild cluster bootstrap: restricted WLS without target; xorshift32 signs in registered division order; refit WLS and CR1 per replicate; count exceedances with the request tolerance; use type-seven quantiles when specified.
6. Grouped conformal: reuse outer predictions and selected penalties; for each held-out division, calibrate from all other training divisions by cold refits; use finite-sample rank and aggregate by held-out counts.
7. Trajectory PCA: build declared feature blocks by variable and year, sample-standardize, orient eigenvectors, farthest-first k-means, handle empty clusters by moving the farthest eligible entity, and compute leave-year aligned ARI/change counts.
8. Exhaustive source perturbation: order entities eligible for direct/rollup disagreement by descending absolute alternate-minus-primary difference then code; enumerate all masks; retain fixed direct weights and design; refit WLS/HC3; summarize by replacement count; compute exact signed Shapley contributions.
9. Decision: report booleans for every module, then choose the first failed module in request precedence or the robust conclusion if none fail.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Purpose: West/Northeast-style county dynamics audit with balanced county panel, delete-state two-step GMM, state-blocked nested elastic net, state wild bootstrap, cross-fold conformal calibration, county trajectory clustering, source-group deletion, and controlled decision.

Module order:

1. Resolve county health and socioeconomic releases, enforce valid RUCC and requested regions, retain counties complete across every balanced year, and create adjacent-change rows ordered by county id then end year.
2. Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. First step uses identity weight. Build state-cluster moment covariance, use the registered Moore-Penrose pseudoinverse cutoff for the second-step weight, compute Hansen J, refit after every state deletion, and jackknife-bias-correct coefficient arrays.
3. State-blocked nested elastic net: allocate states to folds by descending retained-row counts into the currently smallest fold, lower fold id on equality; repeat inside outer training. Standardize continuous terms by training population moments, leave indicators unchanged, cold-start intercept at training outcome mean, traverse grid in declared alpha/l1 order, pool inner squared errors, tie by smaller alpha then smaller l1 ratio.
4. State wild bootstrap: fit unpenalized full OLS and state CR1 for the target, restricted model without target, xorshift32 signs in ascending state order, absolute-tail plus-one p-value, nearest-rank t quantiles, and requested checkpoints.
5. Cross-fold grouped conformal: use outer OOF predictions in analytic-row order. For each fold, calibrate from absolute OOF residuals of all other folds, use rank `min(m, ceil((m+1)*coverage))`, then report fold, state, RUCC-band, prediction-decile, overall, and minimum-state diagnostics.
6. County trajectory PCA clustering: build variable-major trajectories by declared variables and end years, population-standardize, covariance `Z'Z/n`, deterministic farthest-first k-means for each candidate k, Euclidean silhouette with singleton zero, select largest silhouette then smaller k, and compute delete-state ARI.
7. Source-group perturbation: remove exactly the declared group terms one group at a time, reuse each outer fold's full-model selected hyperparameters without retuning, pool RMSE, count worse folds, and rank by decreasing deterioration then declared group order.
8. Decision: evaluate the six gates on unrounded values and return the first applicable controlled enum.
