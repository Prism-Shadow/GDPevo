---
name: public-health-observatory-audit
description: Complete Public Health Observatory portal audit tasks that provide a prompt, analysis_request.json, answer_template.json, and environment_access.md. Use this for state, county, and country publication audits requiring exact release resolution, cohort construction, deterministic statistical modules, controlled decision gates, and a contract-conforming JSON-only answer.
---

# Public Health Observatory Audit

Use this skill when the task asks for a Public Health Observatory audit using a read-only Web portal and attached `analysis_request.json` / `answer_template.json` files.

## Non-Negotiable Contract

1. Read `prompt.txt`, every payload file, and `environment_access.md` before computing.
2. Use only the base URL and endpoints permitted by `environment_access.md`. Do not use outside web sources.
3. Treat `analysis_request.json` as the protocol and `answer_template.json` as the output contract. If they conflict, preserve every explicit field, type, enum, precision, and ordering rule required by the answer template while using the analysis request to define calculations.
4. Return exactly one JSON object and no surrounding narrative when solving the audit.
5. Compute with unrounded values. Round only at final serialization, using the requested decimal places. Keep integers, booleans, strings, arrays, and JSON `null` as their natural JSON types. Never emit `NaN`, `Infinity`, or stringified numbers.
6. Preserve declared orders exactly: years, measures, feature lists, coefficient orders, grids, folds, checkpoints, source groups, divisions, state codes, country ISO3 lists, and template-defined aligned arrays. Only sort lists when the template explicitly says they are set-like or sorted.

## Portal Workflow

1. Discover the portal:
   - Request `/`, `/catalog`, and `/methodology` first.
   - Prefer `/download` for complete reproducible extracts when available.
   - Use geography endpoints for authoritative state, county, country, region, division, RUCC, ISO3, and alias metadata.
   - Use health, socioeconomic, country indicator, and revision endpoints only as listed in `environment_access.md`.
2. Record enough metadata to reproduce release selection:
   - dataset or endpoint used
   - release status and value/source filters
   - revision and release priority
   - excluded or unresolved observations
   - row counts by requested year and cohort
3. Resolve publication records independently; do not assume the portal has already filtered them:
   - Apply requested geography, year, measure, value type, source type, release status, and revision rules.
   - For duplicate eligible records, use the priority specified by the request, commonly highest final revision, latest release timestamp, then stable observation or record id.
   - Apply revision events when requested and report applied versus nonapplied revision ids if the template asks.
   - Treat suppressed, blank, invalid quality-flagged, withdrawn, or unresolved scale-break values as unavailable. Never zero-fill missing values.

## Cohort Construction

Build all cohorts directly from selected publication records.

- Universe: derive requested states, counties, countries, regions, divisions, and aliases from geography metadata.
- Primary/reference cohort: units complete in the reference year for exactly the required outcome, exposure, adjustment, validity, weight, and metadata fields.
- Balanced panel cohort: intersection of units complete in every requested year.
- Machine-learning or broad cohort: reference-year complete cases for all ordered model features.
- Strict dual-source or perturbation cohort: units complete for both baseline and replacement/parallel sources plus all adjustments under the specified years.
- Country reconciliation: resolve requested labels to canonical ISO3 identifiers, count alias resolutions, and keep unresolved labels out of analytic cohorts.
- Report exclusion sets completely and in the template's requested order.

## Design Matrix Rules

Translate request terms literally.

- Include intercepts, fixed effects, references, indicators, interactions, lags, changes, squares, logs, and scaling exactly as specified.
- Common transforms include income per 10000, unscaled-income logs, RUCC indicators with RUCC1 reference, region indicators with the declared reference, and end-year indicators with the declared reference.
- Standardize only continuous predictors marked for standardization, and only with training data inside each fold. Reuse the fold's training means and standard deviations for validation/test rows.
- Leave intercepts and indicator reference semantics unpenalized unless the request says otherwise.
- For weighted models, use the declared reliability/sample-size weight consistently, including source perturbation fits if required.

## Statistical Modules

Implement the method named in the request and check `/methodology` for portal-specific conventions. When the methodology does not override them, use these defaults.

### Regression, Fixed Effects, and Jackknife

- Fit OLS, weighted least squares, fixed-effect OLS, or GMM on the declared cohort and design order.
- For two-way fixed effects, include unit and year effects or an equivalent within transformation.
- For cluster-robust inference, cluster on the declared state, division, or other group and use the request's CR1/HC3 convention.
- Delete-one-group jackknife:
  - Fit the full model once, then refit after removing each registered group in order.
  - Align every delete coefficient with the omitted group.
  - Use the standard delete-group jackknife unless the methodology says otherwise:
    - `mean_delete = mean(theta_delete)`
    - `bias_corrected = G * theta_full - (G - 1) * mean_delete`
    - `se = sqrt((G - 1) / G * sum((theta_delete - mean_delete)^2))`
  - Compute t statistics, p values, confidence intervals, percent changes, and influence summaries from unrounded values.

### GMM and Mediation

- Construct panel changes, lags, instruments, period indicators, and stacked equations exactly as declared.
- Use requested pseudoinverse cutoffs and cluster units.
- For mediation, report total, path-a, path-b, direct effects, first-stage diagnostics, indirect effect, cross-equation covariance/correction, and delete-state diagnostics when requested.
- Use cross-equation delta-method inference for indirect effects unless the methodology states another procedure.

### Nested Ridge and Elastic Net

- Outer folds are grouped exactly as requested, commonly by state or census division.
- Inner folds are created only within the current outer-training data.
- For each candidate lambda/alpha/l1-ratio in declared grid order:
  - Standardize using training-only statistics.
  - Fit the model with the declared penalty, weights, and unpenalized terms.
  - Compute inner grouped RMSEs aligned to the grid.
- Select hyperparameters by minimum inner RMSE, breaking ties by declared grid order unless the methodology says otherwise.
- Refit on all outer-training rows with selected hyperparameters, predict the held-out group, and preserve held-out fold order.
- Report all required fold sizes, selected hyperparameters, nonzero counts, coordinate cycle checkpoints, outer RMSEs, pooled RMSE/MAE/R2/Q2, and state-win counts as required.

### Wild Cluster Bootstrap

- Use the exact PRNG, seed, stream, weight family, replicate count, and checkpoint replicate list from the request.
- Fit the observed model and restricted-null model required by the protocol.
- Generate cluster-level wild weights in registered cluster order; apply the same weight to every row in a cluster.
- Refit each bootstrap replicate and compute the requested t statistic.
- Report complete checkpoint states/statistics, exceedance counts, plus-one p values when specified, coefficient summaries, and requested quantiles.
- Keep all randomization deterministic; never replace a specified PRNG with a library default.

### Grouped Conformal Calibration

- Use grouped split or cross-fold conformal exactly as declared.
- Use the specified source predictions, often outer out-of-fold predictions from a nested model.
- Calculate absolute residual calibration scores within the permitted training/calibration partition.
- Use the finite-sample nearest-rank threshold convention from `/methodology`; if absent, use `ceil((n_cal + 1) * nominal_coverage)` capped to the sorted calibration scores.
- Report all fold/cycle diagnostics, interval radii or thresholds, coverage, widths, MAE if requested, and aggregate coverage/width.
- Include subgroup calibration tables, such as state, RUCC-band, prediction decile, or division coverage, when the template requires them.

### PCA, Clustering, and Stability

- Build the feature matrix in the exact requested feature/year/block order.
- Use the request's PCA type, commonly covariance PCA. If the protocol calls for burden orientation, orient PC1 so higher values mean higher burden.
- Report eigenvalues, explained variance ratios, loadings, scores, and retained component counts exactly as requested.
- Run deterministic k-means with the requested cluster count or candidate grid. Preserve initialization order, iteration count, centroids, sizes, labels, silhouette values, and selected count.
- Stability audits must refit after omitting each requested year, state, or group; align labels back to the full clustering before computing adjusted Rand index or agreement/change counts.

### Source, Year, and Sensitivity Perturbations

- For exhaustive source/year perturbations, enumerate every registered subset or scenario in declared order. Fit each scenario without dropping unrelated eligible units unless the cohort definition requires it.
- For source-group deletion audits, reuse full-model selected hyperparameters when requested and do not retune.
- For exact Shapley attribution, enumerate all coalitions over the ordered replacement set and report effects aligned one-to-one with that order.
- For partial-R2 mediation sensitivity, use the declared baseline path quantities, R2 grids, and direction order. Emit the complete ordered surface and tipping point.

### Country Burden Audits

- Reconcile labels to canonical country metadata and uppercase ISO3 identifiers.
- Separate raw missing cells, anomaly/scale-break exclusions, and imputed cells.
- Impute only after quality exclusions using the portal or methodology rule; report imputation counts.
- For burden PCA, report requested loading ranks and burden-oriented components.
- Evaluate candidate cluster counts in the requested range using deterministic clustering and silhouette scores.
- Fit panel models with requested fixed effects and report the controlled advisory enum from the panel gate.

## Decision Gates

1. Translate every gate into a boolean using unrounded module results.
2. Count passing modules only after all required module fields are computed.
3. Apply precedence exactly:
   - all-pass rules before partial rules
   - first-failed-module rules in the declared module order
   - enum labels exactly as listed in the answer template
4. Do not infer a favorable conclusion from a single coefficient if other modules fail or are unavailable.

## Final Validation Checklist

Before responding, run a local validation script or explicit checks that confirm:

- top-level keys exactly match the template
- every required nested key is present
- no extra narrative or markdown is emitted
- arrays have required lengths and alignment
- enum values exactly match allowed values
- identifier case and ordering match the contract
- counts equal the actual arrays/cohorts they summarize
- all noninteger real values are finite and rounded to the requested precision
- JSON `null` appears only for mathematically unavailable statistics
- all controlled decision flags and classification values are derived from the declared gates

