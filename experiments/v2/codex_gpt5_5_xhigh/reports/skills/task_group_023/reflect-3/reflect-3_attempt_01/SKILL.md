# Public Health Observatory Algorithmic Audit Skill

Use this skill when a task asks for a strict JSON audit using the Public Health Observatory portal and supplies a prompt, an `analysis_request.json`, and an `answer_template.json`.

## Core Approach

1. Read the prompt, request, and template before downloading data. Treat the request as the statistical protocol and the template as the output contract.
2. Use only the portal evidence source provided with the task. Do not use external data, inferred replacements, or unstated fallback values.
3. Build a local analysis script or notebook that can regenerate the complete answer from raw portal exports. Avoid manual copying of table values except for checking schema and methodology text.
4. Preserve every declared order exactly: years, states, counties, countries, divisions, feature orders, coefficient orders, lambda grids, fold orders, checkpoint replicates, source groups, and sensitivity grids.
5. Round only at final JSON emission. Keep all intermediate calculations in full floating-point precision.

## Release Resolution

Apply release filters exactly as declared.

- For health records, filter by requested `measure_id`, year, geography, `value_type`, `source_type` when present, and `release_status`.
- For socioeconomic records, filter by requested fields, year, geography, and `release_status`.
- When several eligible final records exist for the same entity-year-measure, select the highest final revision, then the latest release timestamp, then the stable row identifier named by the request.
- Treat suppressed, blank, null, invalid-scale, invalid, or withdrawn values as unavailable. Never replace unavailable observations with zero.
- Do not let a missing field invalidate unrelated fields unless the cohort rule says all fields must be present.
- For country labels, reconcile requested labels to stable ISO3 identifiers through canonical, portal, and alternate labels, then report sorted set-like identifier lists when required.
- For revision audits, include only revision notices applicable to the requested domain, entities, indicators, and years. Separate applied notices from pending, withdrawn, or otherwise non-applied notices.

## Cohort Construction

Create explicit data frames for each named cohort in the request.

- Jurisdiction universe: start from the requested states, counties, countries, regions, or labels, not from rows that happen to have data.
- Reference-year complete case: require the requested outcome, exposure, adjustments, weights, geography fields, and any declared ancillary fields in that year.
- Balanced panel: intersect complete-case entity sets across every requested year or panel end year.
- Broad machine-learning cohort: use the reference-year complete cases for the full declared feature map.
- Strict dual-source or perturbation cohort: require baseline and replacement sources plus all adjustment fields under the request's nonsuppression rules.
- Report exclusion lists as complete set differences in the requested sorted or registered order.
- Keep identifiers as strings when the portal treats them as strings, especially FIPS-style IDs with leading zeros.

## Feature Engineering

Implement feature maps directly from the request.

- Scale median income only when the request says so, such as per 10,000, unscaled log income, or raw change.
- Encode RUCC indicators with RUCC1 as the reference unless another reference is declared.
- Encode region indicators with the declared reference region and preserve the requested design order.
- Build year, period, or end-year indicators with the declared reference period omitted.
- Create squares, interactions, changes, lags, and source-specific series after release selection and cohort filtering.
- Standardize continuous machine-learning features using training-fold means and standard deviations only; apply those statistics to validation and held-out folds.

## Statistical Modules

Use standard numerical routines, but match the registered design exactly.

- OLS and WLS: construct the design matrix in the declared order, include intercepts only when requested, and use the declared weight semantics. For HC3 inference, use leverage-adjusted residual variance. For CR1 cluster inference, aggregate score contributions by cluster and apply the finite-sample correction when the protocol calls for clustered inference.
- Delete-cluster or delete-state jackknife: fit the full model once, then refit after deleting each registered cluster in order. Report the full coefficient, deletion vector, deletion mean, bias-corrected coefficient, jackknife standard error, t statistic, p value, and influence extrema.
- Difference GMM or instrumented change systems: construct changes over the declared end years, use the exact instrument order, compute two-step estimates when requested, and keep cross-equation covariance terms for mediation delta inference.
- Nested ridge or elastic net: perform outer grouped folds by the declared group, inner grouped validation inside each training set, training-only standardization, declared hyperparameter grids, deterministic tie-breaking, held-out predictions, fold RMSEs, selected parameters, and pooled OOF metrics.
- Wild cluster bootstrap: implement the named deterministic PRNG, seed, cluster order, replicate count, restricted-null refit, weight scheme, tail/exceedance rule, requested checkpoints, terminal state, and quantiles.
- Grouped split conformal: use out-of-fold or fixed-source predictions as declared, split by groups, compute finite-sample nearest-rank residual thresholds, intervals, coverage, widths, MAE when requested, and aggregate diagnostics.
- PCA and clustering: form the exact ordered feature matrix, center columns, use covariance PCA unless otherwise declared, orient component signs deterministically, cluster on the requested retained PCs with deterministic k-means initialization, and report spectra, loadings, scores, labels, centroids, sizes, and stability ARIs.
- Sensitivity surfaces: use the declared baseline coefficients, standard errors, degrees of freedom, R2 grids, and direction order. Emit every grid cell without reordering.
- Source or year perturbation: enumerate scenarios in the registered order, refit without retuning unless specified, compute coefficient/p-value/shift summaries, and for Shapley attribution average marginal effects over all subsets in the declared source order.

## Decision Logic

Compute module flags from the exact inequalities in the request.

- Respect strict versus non-strict thresholds such as `<`, `<=`, `>`, and `>=`.
- Count passed gates only after all module statistics are finalized.
- Apply classification precedence exactly as written.
- Use only enum values from the template, with JSON booleans for flags and JSON null only for mathematically unavailable statistics.

## Output Assembly

1. Populate exactly the required top-level keys and nested keys from `answer_template.json`.
2. Do not include prose outside the JSON object for answer tasks.
3. Emit integers as integers, booleans as booleans, strings with the requested casing, and noninteger statistics rounded to the declared decimal places.
4. Avoid `NaN`, `Infinity`, and stringified numbers.
5. Validate array lengths, positional alignment, sorted set lists, and registered orders before final output.
6. Re-run the script from clean raw portal exports and compare the regenerated JSON to the final output object.

## Common Failure Checks

- A final revision was missed because rows were sorted by release timestamp before revision.
- A suppressed or invalid value was treated as zero.
- A state, county, country, division, fold, or feature array was sorted independently from its aligned values.
- Median income was scaled inconsistently across modules.
- Test-fold information leaked into standardization, imputation, or hyperparameter selection.
- Cluster bootstrap checkpoints used observation order rather than cluster order.
- PCA signs changed between full and stability runs without deterministic alignment.
- Decision flags used rounded displayed values instead of full-precision computed values.
