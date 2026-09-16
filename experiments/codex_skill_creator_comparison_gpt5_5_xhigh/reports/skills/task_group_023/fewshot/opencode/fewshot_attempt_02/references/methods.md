# Public Health Observatory Method Reference

This reference captures reusable method semantics inferred from the staged examples. It intentionally omits solved counts, coefficients, entity memberships, checkpoint states, classifications, and other task-specific answer values.

## Cross-Cutting Contract

Resolve one effective request first. Exact future request values override inherited method defaults: entities, years, measures, filters, random seeds, grids, folds, output names, precision, and business predicates are always task-local.

Release selection:
- Filter by declared release status, value type, source type, geography, measure, and year before analytic completeness checks.
- Prefer the request's explicit priority. Common priority is greatest final `revision`, latest `released_at`, then a record identifier tie-break. Some profiles tie by lowest observation id, others by greatest id; honor the active request/profile instead of assuming one global direction.
- Suppressed rows and rows with invalid quality flags are publication evidence but not analytic values. Missing, blank, suppressed, invalid, withdrawn, and unresolved scale-break values are unavailable and are never zero-filled.

Numerics:
- Use unrounded values for model selection, ties, gates, p-values, extrema, ranks, and Shapley checks.
- Use Student t degrees of freedom declared by the module: cluster tests usually use `G-1`; HC3 row-level tests use `n-k`.
- Choose ties by the request's declared order. If the request is silent, use the stable order implied by the examples: entity code ascending, group order as declared or portal division order, smaller penalty/grid value, then earlier candidate order.

## State Transport Audit

Use this profile when the request is a state longevity/transportability audit with two-way fixed effects, division ridge validation, Webb wild bootstrap, grouped conformal, trajectory PCA clustering, and source-year perturbation.

Release and cohorts:
- Resolve state health and socioeconomic records independently across requested years.
- Build core balanced, broad reference-year, and strict dual-source cohorts from the effective required fields.
- Preserve state-code order for all state-aligned arrays and declared feature order for model matrices.

Two-way fixed effects:
- For each active fit, transform every modeled variable as value minus entity mean minus time mean plus grand mean.
- Fit OLS without intercept in declared predictor order. Deletions remove a whole state/cluster, recompute all means, and refit from scratch.
- For delete estimates `b_g`, mean `bbar`, and `G` clusters: `SE=sqrt((G-1)/G*sum((b_g-bbar)^2))`, `b_bc=G*b_full-(G-1)*bbar`, and the registered t test uses the requested coefficient divided by `SE` with `G-1` degrees of freedom.

Nested ridge by census division:
- Outer folds leave one declared division out. Inner folds leave one remaining division out in the same order.
- Standardize features from training rows only. State transport uses sample standard deviations; county mediation uses population standard deviations. Keep the intercept unpenalized and center the training outcome.
- Select by pooled inner row-level RMSE, then smaller penalty. Refit on the full outer training set and pool one prediction per held-out row for RMSE, MAE, and `1-SSE/SST`.

PCG32 Webb wild bootstrap:
- Fit the unrestricted fixed-effects model and CR1 covariance. Fit a restricted model without the target coefficient.
- Initialize PCG32 with `state=0`, `increment=2*stream+1`, one advance, add seed modulo `2^64`, then advance again.
- Draw one value per cluster in state order for each replicate. Map output modulo six to Webb weights in this order: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Maintain one stream across all replicates. Record weight-index rows/checkpoints after completed replicates. Count two-sided absolute exceedances and use plus-one p-values when requested.

Grouped split conformal:
- For each test division, choose calibration from remaining divisions by greatest row count then ascending division name unless the request declares another partition.
- Fit ridge on proper training rows. Rank sorted absolute calibration residuals with `r=min(m, ceil((m+1)*(1-alpha)))` for miscoverage `alpha`, or `r=min(m, ceil((m+1)*coverage))` when the request declares nominal coverage directly.
- Intervals are inclusive and symmetric. Aggregate coverage and widths weighted by held-out row counts.

Trajectory PCA/k-means:
- Build columns in declared variable/time order and rows in entity order. Standardize active columns, form covariance with the requested divisor, sort eigenvalues descending, and orient each loading so the earliest maximum-absolute loading is positive.
- Initialize k-means with the first entity, then farthest-first centers, breaking ties by entity code. Assign ties to lower cluster id. Recompute until unchanged or cap.
- For leave-year/time stability, rebuild the whole PCA and clustering pipeline. Compute adjusted Rand index against the full labels and align labels by maximum agreement with lexicographic tie-breaking.

Source-year perturbation:
- Keep the strict analytic cohort fixed. Enumerate year subsets by increasing subset size, then lexicographic year tuple.
- Refit primary and parallel source models for every subset. Same sign requires both coefficients nonzero with identical sign. Relative shift is `100*abs((parallel-primary)/primary)` unless the request names a different baseline.

## Weighted State Robustness Audit

Use this profile for reliability-weighted state audits with WLS, HC3, division jackknife, weighted elastic-net, xorshift32 wild bootstrap, division conformal calibration, trajectory PCA, and exhaustive direct-versus-rollup source perturbation.

Weighted linear algebra:
- Set `Xw=sqrt(w)*X` and `yw=sqrt(w)*y`; solve WLS in declared column order.
- HC3 uses weighted residuals `ew=sqrt(w)*(y-Xb)` and leverage from `Xw`.
- CR1 cluster covariance uses ordered cluster scores `s_g=Xw_g' ew_g` and finite sample factor `[G/(G-1)]*[(n-1)/(n-k)]`.

Cluster jackknife:
- Delete each registered census division in order and refit WLS. Percent change is `100*abs((b_delete-b_full)/b_full)`.
- Bias-correct and test the target coefficient with the jackknife formula above, using the bias-corrected coefficient in the t statistic when the profile declares it.

Weighted elastic-net:
- Outer and inner folds are registered divisions. Build raw, squared, and interaction features in declared order.
- Standardize with training-only weighted population means and standard deviations. Center `y` by its training weighted mean.
- Minimize weighted SSE divided by `2*sum(w)` plus `lambda*(alpha*L1 + (1-alpha)*L2/2)`.
- Cold-start every fit. Cycle through features, applying soft-threshold updates. Pool inner validation squared errors at row level. Choose smallest RMSE, then smaller penalty.

Xorshift32 wild bootstrap:
- Use unsigned xorshift32 shifts `(13,17,5)` with 32-bit masking after each xor. Draw one sign per cluster in registered order; low bit one maps to `+1`, otherwise `-1`.
- Fit the weighted restricted model without the target, generate synthetic outcomes, refit full WLS, recompute CR1, and record absolute t statistics.
- Some templates request nearest-rank quantiles; weighted state robustness requests type-seven quantiles. Follow the active module text.

Exhaustive source perturbation:
- Resolve alternate outcome sources using the module's filters and release precedence.
- Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code.
- Enumerate every replacement mask from `0` to `2^m-1`. Keep direct reliability weights fixed. Refit WLS and HC3 for each mask.
- Summarize by replacement count, select maximum unrounded shift by greatest shift then smaller mask, and compute exact signed Shapley effects in the ordered entity list.

## County Mediation Transport Audit

Use this profile for Midwest/South county poverty, inactivity, and obesity mediation tasks with difference GMM, nested leave-state-out ridge, paired state bootstrap, state grouped conformal, partial-R2 sensitivity, and state trajectory clustering.

Publication/cohorts:
- Resolve county health and socioeconomic records independently with declared final filters and revision priority.
- Primary cohort is complete in the primary year. Balanced cohort is complete in every requested year. Machine-learning cohort adds declared extra fields.
- Convert median income to units of 10000 when requested. Encode RUCC indicators with RUCC1 as reference.

Difference GMM mediation:
- Build adjacent-change rows in entity then end-year order. Use lagged levels as instruments as declared.
- For each equation, `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- Cluster sandwich inference uses state scores. For indirect `theta=a*b`, use `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`.
- Compute first-stage partial F from full versus reduced residual sums of squares. Delete-state diagnostics rebuild rows and refit from scratch.

Nested state ridge:
- Fit base and augmented feature maps separately with training-only population standardization and unpenalized intercept.
- Outer folds leave one state out; inner folds leave each remaining state out. Select by pooled row-level RMSE, tie to smaller lambda.
- Report aligned inner grids, selected lambdas, outer RMSEs, pooled base/augmented RMSEs, and state win counts in state order.

Paired state bootstrap:
- For each target equation, fit the restricted model with only that target removed.
- Use one continuous xorshift32 stream. Draw one sign per state in ascending state order per replicate and reuse the same signs across paired equations.
- Count absolute exceedances with plus-one p-values. Record PRNG/t checkpoints after listed replicates.

State grouped conformal:
- Sort states ascending and assign cyclic partitions by index modulo partition count.
- For test fold `f`, use the preceding calibration fold `(f-1 mod K)` and all other folds for proper training.
- Reduce calibration residuals to one maximum absolute residual per calibration state before ranking.

Partial-R2 sensitivity:
- From unrounded baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`.
- For each declared direction, set adjusted `b` to `b +/- magnitude` according to the profile direction convention, then recompute indirect, direct, and proportion.
- Enumerate `r2_mediator`, `r2_outcome`, and direction in declared nested order. Derive tipping strength from unrounded inputs.

## County Panel Dynamics Audit

Use this profile for West/Northeast county diagnosed-diabetes dynamics with balanced panels, delete-state two-step GMM, state-blocked nested elastic-net, state wild bootstrap, cross-fold grouped conformal, county trajectory clustering, and source-group perturbation.

Balanced panel:
- Resolve final crude health and socioeconomic records, require valid RUCC, and retain counties complete across all balanced years.
- Create adjacent changes for declared panel end years ordered by county identifier then end year.
- Build baseline, dynamic, indicator, and interaction terms exactly in declared order.

Delete-state two-step GMM:
- Residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms.
- First step uses identity weighting. Build state scores, `S=sum(s_g s_g')/n`, and second-step weight as the Moore-Penrose inverse with the declared relative singular-value cutoff.
- Report full second-step coefficients, Hansen `J=n*g'Wg`, delete-state refits, bias-corrected coefficients, and maximum absolute shifts.

State-blocked nested elastic-net:
- Allocate states to outer folds by descending retained entity counts, assigning to the currently smallest fold and using lower fold id on equality. Sort state codes within folds. Repeat the allocation inside each outer training set for inner folds.
- Standardize declared continuous terms from training population moments; leave indicators unchanged. Keep intercept unpenalized.
- Traverse alpha then l1-ratio grids in declared order. Select by unrounded pooled inner RMSE, then smaller alpha, then smaller l1 ratio.

Cross-fold conformal:
- Use outer OOF predictions in original analytic-row order. For a held-out fold, calibrate on absolute OOF residuals from all other folds.
- Rank with `min(m, ceil((m+1)*coverage))`; intervals are symmetric and inclusive.
- Prediction deciles are assigned after sorting by prediction and declared identifiers. Signed gap is prediction mean minus observation mean.

County trajectory clustering:
- Build variable-major trajectories in declared variable and end-period order. Standardize by population moments and use covariance `Z'Z/n`.
- For each candidate k, run deterministic farthest-first k-means. Compute Euclidean silhouette with singleton silhouette zero.
- Select largest unrounded mean silhouette, then smaller k. For delete-state stability, rebuild the entire pipeline at the selected k.

Source-group perturbation:
- For each source group and outer fold, remove exactly the declared terms and reuse the full model's selected hyperparameters without retuning.
- Pool squared errors for RMSE, subtract full-model OOF RMSE for deterioration, count folds worse than full, and rank by decreasing unrounded deterioration then declared group order.

## Country Burden Audit

Use this branch when the request has country labels, burden indicator ids, a reference year, panel start/end years, and requested cluster count.

Reconciliation and quality:
- Resolve labels against canonical name, portal label, and alternate-label tokens. Unique ISO3 identifiers are sorted ascending for set-like lists.
- Use country indicator final releases and revision events. Applied scale corrections are valid; pending or withdrawn notices do not authorize replacement.
- Treat unresolved scale-review cells as anomalies. Exclude unresolved anomalies from the analytic matrix and count them separately from raw missing cells.

Completed burden matrix:
- Construct the reference-year country by requested-indicator matrix after quality exclusions.
- Impute excluded or missing cells only after the quality audit. Use a deterministic, documented rule based on available portal evidence; prefer same-region indicator medians and fall back to global indicator medians when a regional median is unavailable.
- Standardize indicators before PCA. Indicator directions in the requested burden set are higher-worse in the observed examples; verify direction from the catalog/methodology before combining any new indicator.

PCA, clusters, and panel:
- Use covariance PCA on standardized burden indicators. Orient PC1 so larger scores represent higher burden; if needed flip scores/loadings together.
- Report top absolute loadings by descending absolute loading and indicator id ascending for exact ties.
- Run deterministic k-means for requested k and candidate silhouette k values. Label the three requested groups by ordered PC1 burden: low, middle, high.
- For the panel model, score country-years with the reference PCA loadings using the same indicator standardization rules, include region fixed effects when requested, and regress the panel outcome on PC1 burden plus region indicators. Use the requested p-value and gradient rule for the advisory.
