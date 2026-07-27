# Public Health Observatory Audit Skill

Use this skill when a task asks for a strict JSON audit using Public Health Observatory portal data. The goal is to turn `analysis_request.json` plus `answer_template.json` into one validated answer object while preserving every declared cohort rule, ordering rule, numerical rule, and decision rule.

## Operating Principles

- Treat the portal as authoritative. Do not infer values from prompt prose when they can be resolved from portal records.
- Keep all identifiers as stable strings. Read FIPS, ISO-like codes, state abbreviations, county codes, observation ids, and record ids without numeric coercion.
- Compute with unrounded floating point values until final serialization. Round only the reported real-valued fields to the precision declared in the request or template.
- Preserve declared order exactly. Never sort aligned arrays independently. Sort only when the template explicitly calls a field a set-like list or says ascending.
- Treat suppressed, blank, null, invalid, withdrawn, and unresolved anomaly values as unavailable. Never zero-fill missing evidence.
- Return exactly one JSON object that matches the template. Do not include narrative around the JSON.

## Parse The Contract First

1. Read the prompt, `analysis_request.json`, and `answer_template.json`.
2. Extract these registries before touching data:
   - geography scope, regions, countries, states, counties, and reference years
   - all health, socioeconomic, and country indicator ids
   - release filters, value types, source types, revision priorities, and validity flags
   - cohort definitions, including primary, balanced, broad, machine-learning, and strict source cohorts
   - formal feature, coefficient, cluster, fold, source-group, subset, checkpoint, lambda, alpha, and grid orders
   - required output keys, array lengths, enum values, precision, and decision precedence
3. Build a validation checklist directly from the template. Use it before final output.

## Resolve Publication Records

For each requested domain, create a selected-release table before modeling.

- Filter to the requested release status, usually `FINAL`.
- Apply value-type and source-type filters exactly. Direct survey, county rollup, crude, and age-adjusted series are distinct sources unless the request explicitly asks for a perturbation between them.
- Select one record per entity-year-measure or entity-year-release group by the declared priority. When no special priority is declared, use highest final revision, then latest release timestamp, then the stable observation or record id as a deterministic tie-breaker.
- For state and county health, exclude records with suppressed values, missing values, or invalid quality flags when the cohort rule requires usable values.
- For socioeconomic releases, select the final release independently from health releases. Sparse null fields invalidate only the requested field set for that cohort rule.
- For country labels, reconcile requested labels through canonical name, portal label, and alternate labels to stable ISO identifiers. Count aliases as resolved requested labels whose submitted label differs from the canonical country name.
- For country scale-break anomalies, prefer later corrected final revisions when they exist. Pending or withdrawn notices do not authorize replacement. Unresolved scale-review cells should be listed as anomalies and excluded from analytic values, then imputed only when the requested method asks for a completed matrix.

## Build Cohorts

Construct wide analytic rows after release resolution.

- Use the geography reference table for region, division, RUCC, state membership, and stable ordering.
- A complete case must satisfy every requested health, socioeconomic, geography, sample-size, source, and quality condition for that specific cohort.
- Primary cohorts are usually reference-year complete cases.
- Balanced cohorts are intersections of complete-case entities across all requested years.
- Broad reference cohorts are reference-year complete cases for the outcome and every ordered feature in that module.
- Machine-learning cohorts add all requested prediction features to the primary cohort.
- Strict source cohorts require simultaneous completeness for baseline and parallel source series plus adjustments across every requested year.
- Report complete counts and exclusion lists from these constructed cohorts, not from raw row counts.

## Design Matrices

Build every model matrix from the declared order.

- Add intercepts only when the method or template includes them.
- Use declared reference categories for region, RUCC, year, and other indicators.
- Encode RUCC indicators as `RUCC2` through `RUCC9` with `RUCC1` omitted unless the request says otherwise.
- Convert income exactly as declared, for example median income per 10000 or natural log of unscaled median income.
- Create polynomial and interaction features after any declared semantic transformation, and keep the requested feature order.
- Standardize only within the training split for predictive models. Apply the training mean and scale to validation, calibration, and test rows.

## Common Audit Algorithms

### Linear Models And Jackknife

- Use OLS, WLS, fixed effects, or GMM exactly as named by the module.
- For reliability-weighted state models, use the selected outcome sample size as the fixed weight.
- For cluster-robust inference, cluster on the requested grouping and report the declared CR1, HC3, or other covariance estimator.
- For delete-one-cluster diagnostics, refit after removing each cluster in the registered cluster order.
- Bias-correct a scalar coefficient as `cluster_count * full_coefficient - (cluster_count - 1) * mean_delete_coefficient`.
- Jackknife standard error is `sqrt((m - 1) / m * sum((delete_i - mean_delete)^2))`, where `m` is the cluster count. Use the requested degrees of freedom for p-values.
- Percent shifts are relative to the full coefficient unless the request declares a different denominator.

### Fixed Effects And Panel Changes

- For two-way fixed effects, include entity and year effects or use an equivalent within transformation. Do not include duplicate reference columns.
- For change models, join each end year to its lagged baseline year before differencing. Keep panel-end-year indicators in the declared order.
- For GMM or IV mediation, construct instruments exactly from declared lag levels or interactions. Report first-stage diagnostics, equation coefficients, and cross-equation delta-method indirect effects from the same analytic cohort.

### Nested Ridge And Elastic Net

- Outer folds are grouped exactly as declared, commonly by state, census division, or fixed fold number.
- Inner folds must use training data only and preserve the same group-blocking logic.
- For each outer fold, evaluate every hyperparameter option in the declared grid order.
- Select the hyperparameter with minimum inner RMSE. Break exact ties by the earliest option in the declared grid unless the request states another rule.
- Fit the selected model on the full outer-training set and evaluate on the held-out group.
- Pool predictions across all outer test rows before computing overall RMSE, MAE, R-squared, or Q-squared.
- For no-retune perturbation modules, reuse the selected full-model hyperparameters and fold splits.

### Wild Cluster Bootstrap

- Implement the requested deterministic generator and weight distribution exactly from the method name and request metadata.
- Fit the restricted null model when the method says restricted null; do not bootstrap unrestricted residuals as a shortcut.
- Keep cluster order fixed and record every requested checkpoint after the corresponding replicate.
- Count exceedances using the requested absolute or signed tail rule.
- Use plus-one p-values when requested: `(exceedance_count + 1) / (replicate_count + 1)`.
- Report quantiles from the generated bootstrap statistics at the requested probabilities.

### Grouped Conformal Calibration

- Use the requested grouped split, out-of-fold predictions, or fixed source model.
- Compute nonconformity scores as absolute residuals unless the request defines another score.
- For split conformal radius, use the finite-sample nearest-rank rule declared by the task, commonly `ceil((n_calibration + 1) * nominal_coverage)`.
- Report fold, group, RUCC-band, division, state, and decile diagnostics from the actual held-out rows.
- Overall coverage is covered rows divided by held-out rows pooled across all groups. Mean width is the row-weighted interval width unless the template says otherwise.

### PCA, Clustering, And Stability

- Build trajectory or burden matrices in the exact feature order.
- Standardize columns before covariance PCA unless the request explicitly says to use raw covariance.
- Orient component signs deterministically. For burden components, make higher-worse indicators load in the burden direction. For repeated stability fits, align signs to the full fit by positive dot product.
- Use deterministic k-means initialization from the request when specified. Otherwise use a reproducible deterministic rule and document only the requested outputs.
- For requested cluster-count options, compute every silhouette or inertia value and select by the declared criterion.
- For leave-year-out, delete-state, or delete-cluster stability, refit the complete pipeline on the reduced matrix, align cluster labels to the full solution by maximum overlap, and report adjusted Rand index plus any requested agreement counts.

### Source, Year, And Group Perturbations

- Enumerate subsets, years, source replacements, or source-group deletions in the exact registered order.
- For exhaustive source replacement, evaluate every scenario from zero replacements through all replacements.
- Stability flags must be calculated per scenario before summarizing stable counts and maximum shifts.
- Exact Shapley attribution requires averaging marginal coefficient changes over all coalitions in which each source is absent, with combinatorial weights implied by the full source count.

### Sensitivity Surfaces

- Use the baseline coefficients, residual degrees of freedom, and standard errors from the primary fitted models.
- Evaluate the full Cartesian product of mediator-R2 values, outcome-R2 values, and bias directions in the declared order.
- Compute adjusted path, indirect, direct, and proportion values before rounding. Tipping-point summaries must be derived from the same baseline scale.

## Decisions

- Evaluate every gate from computed rounded-independent statistics, using unrounded values when comparing thresholds unless the request states otherwise.
- Preserve decision precedence. For "first failed module" outputs, scan the requested gate order and stop at the first false gate.
- Use only enum strings allowed by the template.
- Count supported or passed modules from the gate booleans, not from narrative interpretation.

## Final Validation

Before returning the answer:

- Confirm every required top-level key and nested key is present.
- Confirm all arrays have required lengths and aligned ordering.
- Confirm set-like lists are unique and sorted only when the template says so.
- Confirm integers, booleans, strings, numbers, and JSON nulls use the declared JSON types.
- Confirm there are no `NaN`, `Infinity`, comments, extra keys that conflict with the template, or prose outside the JSON.
- Confirm all numeric output precision matches the request and template.
