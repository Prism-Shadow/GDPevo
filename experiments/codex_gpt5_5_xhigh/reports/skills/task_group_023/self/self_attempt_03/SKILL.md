# Public Health Observatory Algorithmic Audit

Use this skill for Public Health Observatory tasks that provide a prompt, an
`analysis_request.json`, and an `answer_template.json`, and require one strict
JSON answer computed from the read-only Observatory portal.

## Core Rule

Treat the request and answer template as the contract. Do not infer final answer
values from examples. Fetch the portal data, resolve publication records,
compute every requested audit module, and emit exactly one JSON object with no
surrounding prose.

## Inputs And Portal Access

1. Read the full prompt, `analysis_request.json`, and `answer_template.json`
   before coding. Extract:
   - geography scope, years, regions, measures, value types, source types, and
     release statuses;
   - revision priorities and invalid/suppression rules;
   - cohort definitions;
   - model formulas, feature orders, grids, seeds, checkpoints, and decision
     thresholds;
   - required key names, array lengths, enum values, numeric precision, and
     ordering rules.
2. Read `environment_access.md` for the portal base URL and allowed endpoints.
   Use only those endpoints. The reusable datasets are available through:
   - `/download?dataset=states&format=csv`
   - `/download?dataset=counties&format=csv`
   - `/download?dataset=countries&format=csv`
   - `/download?dataset=state_health&format=csv`
   - `/download?dataset=state_socioeconomic&format=csv`
   - `/download?dataset=county_health&format=csv`
   - `/download?dataset=county_socioeconomic&format=csv`
   - `/download?dataset=country_indicators&format=csv`
   - `/download?dataset=revisions&format=csv`
   Also inspect `/catalog` and `/methodology` when column definitions,
   identifier semantics, release policy, quality flags, RUCC, country aliases,
   or revision handling are relevant.
3. Load CSVs with stable identifier columns as strings. FIPS codes, state
   abbreviations, ISO3 values, observation IDs, and record IDs must not be
   converted to numbers.

## Publication Record Resolution

1. Filter records exactly as declared: measure or indicator IDs, years,
   geography, `release_status`, `value_type`, `source_type`, and any source
   family constraints.
2. Select one publication record for each logical key. The usual final-release
   precedence is:
   - keep requested `release_status`, usually `FINAL`;
   - choose the highest final `revision`;
   - break ties by latest `released_at`;
   - if the request declares an ID tie-breaker, use the declared ID order;
   - otherwise keep a deterministic stable order and audit any duplicate.
3. Applied revision notices are evidence; pending or withdrawn notices do not
   replace published values unless the request explicitly says so. For country
   tasks, report relevant applied and non-applied revision event IDs as the
   template requires.
4. Treat suppressed, blank, null, and request-declared invalid quality flags as
   unavailable. Never zero-fill unavailable values. Preserve quality and
   suppression metadata for audit counts.
5. Country labels must be reconciled through `countries.canonical_name`,
   `portal_label`, and pipe-delimited `alternate_labels`. Require unique ISO3
   resolution. Sort set-like ISO3 and event-ID lists ascending when the template
   says they are set-like; otherwise preserve the declared label order.

## Cohort Construction

1. Build selected health or indicator records and socioeconomic records first,
   then pivot to one row per entity-year.
2. Join geography attributes from the reference tables:
   - states: state code, region, Census division, and `is_state`;
   - counties: county FIPS, state, region, RUCC, metro class, population base;
   - countries: ISO3, canonical and portal labels, region, income group.
3. Complete-case rules are request-specific. Common patterns:
   - reference-year primary cohort: complete for all required reference-year
     outcome, exposure, adjustment, weight, and geography fields;
   - balanced panel cohort: entity is complete in every requested analysis year;
   - machine-learning or broad cohorts: primary/reference cohort plus all
     ordered prediction features;
   - strict dual-source cohorts: complete for outcome, primary source, parallel
     source, and adjustments in all required years.
4. Report selected-row counts, complete counts, cohort sizes, panel row counts,
   state or country counts, and exclusions exactly as requested. Exclusions are
   the full universe minus the reported cohort, in the requested order.
5. Preserve all registered orders. Derive implicit state order from the state
   geography table after applying the request universe. Derive implicit division
   order from first occurrence in that state order. County state lists usually
   follow ascending state abbreviation unless the request declares fold order.

## Feature Engineering

1. Apply unit transformations exactly:
   - `median_income_per_10000` or `income` means median income divided by
     10000;
   - `log_income` means natural log of unscaled median income;
   - RUCC indicators `RUCC2` through `RUCC9` use RUCC1 as reference;
   - region indicators use the request's reference region;
   - powers and interactions are built after the named base transformation.
2. For panel dynamics, define changes as end-year value minus prior-year value.
   Lagged terms are prior-year values for the same entity. End-year indicators
   use the request's reference period.
3. Standardize only where the method says to do so. In cross-validation, fit
   means and scales on the training portion only, then apply them to inner,
   validation, calibration, and held-out rows. Do not standardize indicators
   unless the request says so.
4. Keep feature and coefficient arrays in the exact declared order. Do not sort
   an aligned array independently.

## Statistical Implementation Rules

Implement calculations in a reproducible script, usually Python with
`pandas`, `numpy`, `scipy`, `statsmodels`, and `sklearn` if available. Keep
unrounded values internally and round only while serializing the final object.

General model conventions:
1. Include an intercept when requested or when fitting ordinary regression
   designs, unless the request explicitly excludes it.
2. Do not penalize intercept terms in ridge or elastic-net models.
3. For weighted regressions, use the declared reliability weight directly and
   keep it fixed in perturbation fits if requested.
4. Clustered CR1 standard errors, HC3 standard errors, fixed effects, and GMM
   weighting must match the method named in the request. If a denominator or
   degrees-of-freedom correction is not explicit, use the standard small-sample
   correction for the named estimator and record enough diagnostics to verify it.
5. For unavailable mathematical statistics, use JSON `null`; never emit `NaN`,
   `Infinity`, or stringified numbers.

Delete-cluster and jackknife modules:
1. Fit the full model, then refit after deleting each registered state,
   division, or cluster.
2. Let `G` be the number of delete groups, `theta_full` the full estimate, and
   `theta_g` each leave-one estimate. Use:
   - `theta_bar = mean(theta_g)`;
   - `se = sqrt((G - 1) / G * sum((theta_g - theta_bar)^2))`;
   - `theta_bias_corrected = G * theta_full - (G - 1) * theta_bar`.
3. Compute percent shifts against the full estimate when requested and identify
   minimum, maximum, or most influential deletions from the aligned delete
   vector.

Nested prediction modules:
1. Use the declared outer grouping, inner grouping, candidate grid, and fold
   order. Leave-one-group-out means the entire group is held out.
2. For each outer fold, tune only on the outer-training rows. Compute inner
   grouped RMSE for every candidate in declared grid order.
3. Select the candidate with minimum mean inner RMSE; break exact ties by the
   earliest declared grid position.
4. Refit on the full outer-training rows using the selected candidate and score
   the held-out rows. Store fold sizes, selected hyperparameters, coefficient
   checkpoints, inner grids, outer RMSEs, and out-of-fold predictions.
5. Pooled RMSE, MAE, Q-squared, and R-squared are computed from all held-out
   predictions together, not by averaging fold metrics unless the template asks
   for fold averages.

Wild cluster bootstrap modules:
1. Use the request's PRNG, seed, stream, replicate count, cluster order,
   bootstrap weight family, and checkpoint replicate list.
2. Restricted-null bootstrap means generate bootstrap outcomes under the null
   hypothesis for the target coefficient or equation, refit the full target
   model, and compute the requested bootstrap t-statistic.
3. Preserve reproducibility evidence: terminal PRNG state, requested checkpoint
   states and t-statistics, first weight-index rows, batch exceedance counts, or
   quantiles as named by the template.
4. Use the requested p-value convention. If the template says plus-one p-value,
   compute `(exceedance_count + 1) / (replicate_count + 1)`.

Grouped conformal modules:
1. Use the declared source predictions, fixed model, or nested out-of-fold
   predictions. Do not retrain unless the method requires it.
2. For split conformal, compute absolute residuals on the calibration group and
   use the finite-sample nearest-rank threshold:
   `rank = ceil((n_calibration + 1) * nominal_coverage)`, capped at
   `n_calibration`.
3. Intervals are prediction plus or minus the threshold. Width is
   `2 * threshold`. Report fold, group, state, RUCC-band, decile, and aggregate
   coverage and widths exactly as requested.

PCA, clustering, and stability modules:
1. Build the complete matrix in the declared feature order. For trajectory
   features, order by requested year blocks and within-year variable order.
2. Use the PCA variant named in the request. For covariance PCA, center columns
   and use the covariance matrix. Only scale columns when the request or
   methodology calls for standardized/correlation PCA.
3. Orient component signs deterministically. For burden PCA, orient PC1 so
   higher burden indicators load positively overall. Otherwise orient each
   component so its largest absolute loading is positive unless the request
   declares another sign rule.
4. Run deterministic k-means with the registered initialization and cluster
   count or candidate counts. Do not use random restarts unless specified.
5. For silhouette selection, evaluate every requested candidate count and choose
   the highest silhouette, breaking exact ties by the earliest candidate order.
6. For leave-year-out or delete-state stability, rebuild the reduced feature
   matrix, recluster deterministically, align cluster labels to the full labels
   with a maximum-overlap assignment, and report adjusted Rand indices plus any
   aligned agreements or change counts required.

Mediation, GMM, sensitivity, and perturbation modules:
1. Difference-GMM mediation uses requested changes, lagged-level instruments,
   state-clustered inference, first-stage partial F diagnostics, and delta-method
   inference for the indirect effect `a * b`, including the cross-equation
   covariance term when requested.
2. Two-step linear GMM uses the declared design, instrument order, coefficient
   order, and pseudoinverse cutoff. Report full coefficients, Hansen J, and
   delete-state diagnostics in the registered order.
3. Mediation sensitivity surfaces use the declared R2 grids and direction order.
   Start from the baseline path-a coefficient, path-b coefficient, path-b
   standard error, and residual degrees of freedom, then report every ordered
   grid cell and the tipping point requested by the template.
4. Source-year, direct-versus-rollup, and source-group perturbations must
   enumerate every registered subset, bitmask, replacement count, or ordered
   group. Reuse selected hyperparameters when the request says no retuning.
5. Exact Shapley attribution for source replacement means average each source's
   marginal coefficient contribution over all subsets that exclude it. The
   Shapley effects must align one-to-one with the registered source order, and
   their sum must equal the all-replacement coefficient minus the all-direct
   coefficient within rounding tolerance.

## Decision And JSON Output

1. Apply gate thresholds exactly, including strict versus non-strict
   inequalities. Preserve the request's gate precedence.
2. Boolean flags must be real JSON booleans. Enums must exactly match the
   allowed values in the template.
3. Round computed non-integer statistics to the declared precision as JSON
   numbers. Literal grids and thresholds use the template's declared precision
   if it differs from computed-stat precision. Counts, ranks, fold numbers,
   seeds, PRNG states, and replicate numbers remain integers.
4. Construct the final object from the template, not from memory. Validate:
   - required top-level keys and nested keys are present;
   - no accidental extra narrative is printed;
   - list lengths match the template;
   - aligned arrays have matching lengths and order;
   - no `NaN`, `Infinity`, or stringified numbers appear;
   - set-like lists are unique and sorted only when the template says so.
5. Print exactly one JSON object as the final answer.

## Recommended Work Pattern

1. Write a solver script that downloads or caches portal CSVs, performs release
   resolution, builds cohorts, computes modules, validates the answer object,
   and writes or prints JSON.
2. Add assertions after each cohort and module for the template's cardinality
   and ordering requirements.
3. Keep a small audit table in the script for each model's input rows and
   groups. Most mistakes in these tasks come from an incorrect selected release,
   leaked cross-validation standardization, a silently sorted aligned array, or
   rounding before downstream calculations.
