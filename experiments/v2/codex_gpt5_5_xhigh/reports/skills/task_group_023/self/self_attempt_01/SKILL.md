---
name: public-health-observatory-algorithmic-audit
description: Complete Public Health Observatory portal statistical audit tasks that require strict release resolution, cohort construction, reproducible modeling modules, controlled decision gates, and JSON-only answers.
---

# Public Health Observatory Algorithmic Audit

Use this skill when a task asks for a Public Health Observatory audit using `analysis_request.json`, `answer_template.json`, and the read-only Observatory portal. The deliverable is usually one JSON object with no surrounding narrative.

## Nonnegotiable Inputs

1. Read the prompt, `analysis_request.json`, and `answer_template.json` completely before doing calculations.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only those portal endpoints for network access.
3. Treat `analysis_request.json` as the statistical protocol and `answer_template.json` as the output contract. If they conflict, preserve the template shape but compute values from the protocol.
4. Do not import outside facts, external public-health data, or unstated defaults.

## Portal Data Workflow

1. Discover metadata first:
   - Use `/catalog` to identify datasets, fields, measure identifiers, release metadata, flags, and revision semantics.
   - Use the matching geography endpoint for the requested unit: `/geographies/states`, `/geographies/counties`, or `/geographies/countries`.
   - Use `/methodology` when an algorithm name, revision rule, PRNG, PCA orientation, clustering initialization, bootstrap weight scheme, or model-inference detail is not fully specified in the request.
2. Fetch only the data needed for the declared scope:
   - State tasks: `/data/state-health` and `/data/state-socioeconomic`.
   - County tasks: `/data/county-health` and `/data/county-socioeconomic`.
   - Country tasks: `/data/country-indicators`.
   - Revision audits: `/data/revisions`.
   - Bulk export is acceptable through `/download` when that is the clearest way to preserve complete release records.
3. Keep raw portal rows intact until release selection, quality filtering, and cohort audits are reproducible.

## Release And Quality Resolution

1. Apply the exact filters from the request:
   - `release_status` or publication state such as `FINAL`.
   - `value_type`, such as `AGE_ADJUSTED` or `CRUDE`.
   - `source_type`, such as `DIRECT_SURVEY`, `COUNTY_ROLLUP`, or another declared source.
   - Measure, indicator, year, region, state, county, country, and reference-year restrictions.
2. Resolve multiple eligible rows using the declared priority. Common priorities are highest final revision, latest `released_at`, then stable row identifiers such as `observation_id` or `record_id`.
3. Treat suppressed, invalid, withdrawn, invalid-scale, blank, and null numeric values as unavailable. Never zero-fill missing values.
4. Only impute when the request explicitly requires it, and count raw missing cells, anomaly exclusions, and imputed cells separately.
5. For country-label tasks, reconcile labels to canonical countries and ISO3 identifiers; report alias resolutions, unresolved labels, applied revision events, non-applied revision events, and unresolved anomaly keys exactly as requested.

## Cohort Construction

Build every cohort independently and report the requested counts.

1. Define the jurisdiction universe from the geography endpoint and the request scope.
2. Create selected release tables for every requested year and measure before complete-case filtering.
3. Apply complete-case rules exactly. Required values must be nonsuppressed and nonmissing; include sample sizes, RUCC, region, or other metadata when the request declares them as required.
4. Common cohorts:
   - `primary` or reference-year cohort: complete cases in the reference year.
   - `balanced panel`: units complete in every requested analysis year.
   - `machine-learning` or broad cohort: reference-year complete cases plus all declared feature values.
   - `strict dual source`: units complete for outcome, primary exposure, parallel exposure, and adjustments across all required years.
5. Exclusion lists must contain every omitted unit and no included unit. Sort only when the template says to sort; otherwise preserve registered order.

## Design Matrix Rules

1. Preserve declared term order in every coefficient vector, feature list, grid, fold, checkpoint, and diagnostic array.
2. Use declared reference categories:
   - Region indicators commonly use Northeast as reference when specified.
   - RUCC indicators commonly include RUCC2 through RUCC9 with RUCC1 as reference.
   - Period indicators use the declared base end year.
3. Apply declared transformations exactly:
   - `median_income_per_10000` or `income` means median income divided by 10000.
   - `log_income` means natural log of unscaled median income unless the request states otherwise.
   - Change models use end-year minus prior-year values and include declared lags and end-year indicators.
   - Interactions and polynomial terms follow the feature order in the request.
4. For predictive models, fit preprocessing on training data only. Standardize only the declared continuous terms; leave intercepts and indicators unstandardized unless methodology says otherwise.

## Reusable Module Patterns

### Regression, Fixed Effects, And GMM

1. Fit exactly the requested model: OLS, weighted least squares, two-way fixed effects, two-step linear GMM, or difference GMM.
2. Use reliability weights, instruments, fixed effects, clusters, and pseudoinverse cutoffs exactly as declared.
3. Cluster-robust or HC inference must match the requested estimator, such as HC3 or CR1.
4. Delete-unit jackknife modules must:
   - Fit the full model.
   - Refit after deleting each registered state, cluster, or division in order.
   - Report every delete coefficient and diagnostic.
   - Compute the delete mean, jackknife standard error, bias-corrected coefficient, t statistic, p value, and maximum percent shift requested by the template.

### Nested Ridge And Elastic Net

1. Use grouped outer folds exactly as declared, such as leave-one-state-out, leave-one-division-out, or fixed state-blocked folds.
2. Within each outer training split, run the declared inner grouped CV over the exact lambda, alpha, and l1-ratio grids in order.
3. Select hyperparameters by the registered metric, usually minimum inner RMSE. When exact ties occur and no rule is specified, choose the earliest candidate in declared grid order.
4. Refit on the full outer training split with the selected hyperparameters and evaluate only on the held-out outer group.
5. Report inner grids aligned to the grid order, selected hyperparameters, nonzero counts or coordinate-cycle checkpoints when requested, outer metrics, and pooled OOF metrics.

### Wild Cluster Bootstrap

1. Implement the named PRNG exactly, such as XORSHIFT32 or PCG32, including seed, stream, replicate count, terminal state, and checkpoint states.
2. Use the declared cluster unit and restricted-null construction. Weights are assigned at cluster level and reused across all rows in that cluster.
3. Preserve the requested statistic: signed t, absolute t, paired-equation t vector, or coefficient summary.
4. Report all requested checkpoints, exceedance counts, plus-one or ordinary p values as specified, and quantiles at the declared probabilities.

### Grouped Conformal Calibration

1. Use the requested prediction source, often nested outer OOF predictions or a fixed-lambda ridge model.
2. Split by the declared group, not by individual rows, when the method is grouped.
3. Calculate calibration residuals on calibration groups only. Use the finite-sample nearest-rank rule declared by the request or methodology.
4. Evaluate intervals on held-out groups and report fold, state, division, RUCC-band, decile, or aggregate diagnostics exactly as required.

### PCA, Clustering, And Stability

1. Build the matrix with rows and columns in the declared order. Center and scale only as required by the protocol or methodology.
2. Orient components deterministically:
   - For burden-oriented PCA, choose the sign so larger PC1 means greater burden.
   - Otherwise use the methodology rule, or make the loading with largest absolute value positive if no rule is given.
3. Report the requested spectrum, explained shares, loadings, scores, initial centroids, Lloyd update count, centroids, sizes, and assignments.
4. For deterministic k-means, use the registered initialization and candidate cluster counts. Preserve cluster labels as registered; align labels only for stability comparisons.
5. For leave-year-out or delete-state stability, rebuild the requested reduced matrix, rerun the registered clustering, align labels to the full solution, and report every adjusted Rand index and agreement/change diagnostic.

### Source Perturbation And Sensitivity

1. For source-year, direct-versus-rollup, or source-group perturbations, keep the registered source order, subset order, bitmask convention, and no-retune rule.
2. Exhaustive perturbations must enumerate every scenario, including the all-baseline and all-replacement cases.
3. Report coefficients, p values, shifts, stability flags, worst scenario, and exact Shapley effects when requested.
4. For partial-R2 mediation sensitivity surfaces, use the baseline path coefficients, standard error, degrees of freedom, R2 grids, and bias-direction order from the request. Emit the full ordered surface.

## Decision Gates

1. Evaluate every gate exactly as written, including strict versus non-strict inequalities.
2. Keep gate order and precedence from the request.
3. Compute boolean flags first, then the pass count, first failed module, classification, conclusion, or advisory enum.
4. Use only controlled enum values from the template. Do not invent labels.

## Output Validation

Before finalizing:

1. Construct the JSON object with exactly the top-level keys required by the template.
2. Include every required nested key and omit template descriptors.
3. Ensure arrays have the required lengths and order.
4. Round only final reported noninteger statistics to the declared precision. Keep counts, seeds, PRNG states, replicate numbers, fold numbers, ranks, booleans, and enums as natural JSON types.
5. Use JSON `null` only when a statistic is mathematically unavailable and the template permits it. Never emit `NaN`, `Infinity`, strings for numbers, or comments.
6. Validate with a JSON parser before submitting.
7. Return only the completed JSON object, with no markdown and no explanatory text.
