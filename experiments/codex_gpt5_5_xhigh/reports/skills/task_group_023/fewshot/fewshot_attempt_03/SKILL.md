---
name: pho-observatory-algorithmic-audits
description: Solve Public Health Observatory portal audit tasks that provide an analysis_request.json and answer_template.json, including state, county, and country statistical audits with strict JSON output contracts.
---

# Public Health Observatory Algorithmic Audits

## When To Use

Use this skill when the task asks for a Public Health Observatory audit using the portal at `<TASK_ENV_BASE_URL>` and staged payloads such as `analysis_request.json` and `answer_template.json`. It covers:

- State algorithmic transport audits with `protocol_id` `PHO_STATE_TRANSPORT_AUDIT_V1`.
- County mediation transport audits with `protocol_id` `PHO_COUNTY_MEDIATION_TRANSPORT_V1`.
- State reliability-weighted robustness audits with `protocol_id` `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.
- County panel dynamics audits with `protocol_id` `PHO_COUNTY_PANEL_TRANSPORT_V1`.
- Country burden/revision audits whose request has country labels, burden indicators, a life-expectancy panel outcome, PCA/clustering, and a country-burden answer template.

Do not reuse solved numeric values, cohort memberships, classifications, seeds, thresholds, grids, or labels from previous tasks. Bind all entities, variables, years, filters, orders, randomization settings, decision cutoffs, and output names from the active request and template.

## Required Workflow

1. Read the prompt, every file under the task `input/` directory, and the matching `analysis_request.json` and `answer_template.json`.
2. Read `/work/environment_access.md` and use only its `GDPEVO_ENV_BASE_URL` for portal access.
3. Freeze one effective request before fetching data or fitting models. Apply overrides only when the active request declares them:
   - Direct root keys replace the same canonical root key.
   - `<section>_overrides` targets `<section>`.
   - `module_overrides.<module>` targets that exact module.
   - Objects deep-merge; arrays replace whole arrays; scalars replace only their exact path.
   - Reject unknown override targets, key renames, type coercions, array concatenation, or positional patches.
4. Fetch portal evidence through `/download?dataset=<name>&format=csv`. Available datasets are `states`, `counties`, `countries`, `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, and `revisions`.
5. Resolve publications independently for each declared data source and key. The usual precedence is final release status, highest revision, latest `released_at`, then the request/profile's identifier tie-break. Do not invent a tie-break when the request specifies one.
6. Treat suppressed, invalid, blank, null, and withdrawn analytic values as unavailable. Never zero-fill missing evidence.
7. Preserve every declared order: entity order, state/division/fold order, feature order, coefficient order, grid order, checkpoint order, source-group order, and output-array order.
8. Compute all predicates on unrounded values. Round only the reported JSON fields to the precision declared by the active template.
9. Return exactly one JSON object matching the active `answer_template.json`. Emit no narrative outside the JSON.

The companion file `pho_audit_tools.py` provides reusable portal fetchers and numerical primitives. A typical scratch script can start with:

```python
from pho_audit_tools import *

base = read_env_base_url("/work/environment_access.md")
tables = fetch_all_portal_tables(base)
```

## Portal And Release Rules

- Geography identifiers are text. Preserve leading zeroes in FIPS-like columns.
- State geography supplies region/division; county geography supplies state, region, RUCC, population, and coordinates; country geography supplies canonical labels, portal labels, alternate labels, region, and income group.
- Health rows use `observation_id`; socioeconomic rows use `record_id`.
- For state health, filter by `measure_id`, `year`, `value_type`, `source_type`, `release_status`, and any source filter in the request.
- For county health, filter by `measure_id`, `year`, `value_type`, and `release_status`.
- For socioeconomic tables, filter by geography, year, `release_status`, and requested field completeness.
- Count selected publication rows before analytic completeness exclusions when the template asks for release counts.
- Cohorts are built after release selection:
  - Primary/reference cohorts require complete selected records in the reference year.
  - Balanced cohorts are intersections complete in every requested year.
  - Broad ML cohorts add requested feature completeness in the reference year.
  - Strict dual-source cohorts require both primary and alternate source values plus adjustments.

## Common Numerical Conventions

- Use natural JSON integers and booleans for counts, seeds, flags, fold numbers, PRNG states, and enum decisions.
- Convert income as requested, commonly `median_income / 10000`; use natural log only when explicitly requested.
- Use RUCC indicators with the declared reference, usually RUCC1.
- Use two-sided Student-t inference with the registered degrees of freedom unless a module explicitly says otherwise.
- For CR1 cluster covariance, use ordered cluster scores and finite-sample factor `(G/(G-1))*((n-1)/(n-k))`.
- For HC3, compute leverage in the weighted design when fitting WLS.
- For finite-sample conformal ranks, sort absolute residual scores and use one-based `min(m, ceil((m+1)*coverage))`, or equivalently `ceil((m+1)*(1-alpha))` when miscoverage is supplied.
- Nearest-rank bootstrap quantiles use `ceil(p*B)` one-based unless the profile explicitly requests type-seven interpolation.

## State Transport Audit Profile

Activation: exact `protocol_id` `PHO_STATE_TRANSPORT_AUDIT_V1`.

Release and cohorts:

- Resolve state health and socioeconomic final releases by declared source/value filters.
- Keep suppressed, invalid-scale, withdrawn, blank, and null values unavailable.
- Build the core balanced panel from the variables named by the request and all analysis years.
- Build the broad reference cohort from complete reference-year outcome and ordered ridge features.
- Build the strict dual-source cohort from primary exposure, parallel exposure, outcome, and adjustments in every analysis year.

Modules:

- `delete_cluster_fixed_effects`: double-demean outcome and predictors by entity and year. Fit OLS without intercept in declared predictor order. For each delete-state refit, remove the whole state, recompute means, and refit. Jackknife with `SE=sqrt((G-1)/G*sum((b_g-bbar)^2))` and `b_bc=G*b-(G-1)*bbar`; select extrema by unrounded coefficient, then state code.
- `nested_ridge_division_cv`: leave one Census division out. Within each outer train set, leave each remaining division out. Standardize features using training-only means and sample SDs. Center outcome, keep intercept unpenalized, select lambda by pooled inner validation RMSE with smaller lambda tie-break, then pool one outer prediction per row.
- `wild_cluster_bootstrap`: use the fixed-effect design. Fit restricted model without target, generate synthetic outcomes from restricted fitted values plus cluster-weighted restricted residuals, and refit full models. For the Webb variant, use PCG32 and map output modulo six to the ordered Webb weights in `pho_audit_tools.PCG32.webb_weight()`. Keep one continuous stream and record checkpoints after completed replicates.
- `grouped_split_conformal`: for each ordered division, hold it out as test. Pick calibration from remaining divisions by greatest row count then ascending division name unless overridden; fit ridge on proper training and form inclusive symmetric intervals from calibration residuals.
- `trajectory_pca_clustering`: build variable-major/time-major trajectories in declared feature order. Standardize with sample SD, eigendecompose covariance, orient each PC by earliest maximum absolute loading positive, score states, run deterministic farthest-first k-means, and recompute the whole pipeline for leave-year-out stability with adjusted Rand index.
- `source_year_perturbation`: enumerate year subsets by increasing requested subset size and lexicographic tuple order. Refit primary and parallel double-demeaned models on the unchanged strict cohort. Compute coefficient shifts, same-sign fraction, median absolute percent shift, and worst subset using unrounded shifts.
- Decision: complete every module, evaluate the six gate predicates on unrounded values, count passes, and map through the active request's decision rule.

## County Mediation Transport Profile

Activation: exact `protocol_id` `PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Release and cohorts:

- Resolve county health and socioeconomic rows by the request's revision priority.
- Build primary-year, balanced-panel, and machine-learning cohorts after health, socioeconomic, and geography validity checks.
- Use county identifiers as analytic entities and state abbreviations as cluster/groups unless the request says otherwise.

Modules:

- Primary mediation models: build total, path-a, and direct/path-b OLS designs from the declared exposure, mediator, outcome, controls, transformations, and RUCC references. Retain unrounded baseline coefficients for bootstrap and sensitivity.
- `difference_gmm_mediation`: create adjacent-change rows in entity/end-year order. Use lagged levels as instruments exactly as declared. For each equation fit linear GMM with `W=(Z'Z)^-1`; use cluster sandwich scores for inference. For indirect effect `a*b`, use delta variance `b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`. Refit all equations for each delete-state diagnostic.
- `nested_state_ridge`: use exact base and augmented feature order. Standardize from training arithmetic means and population SDs; use divisor 1 for zero variance. Outer folds leave one state out; inner folds leave one remaining state out. Pool row-level squared errors for inner RMSE and choose the smaller penalty on ties.
- `wild_cluster_bootstrap_t`: for each target equation, fit restricted null without that target; use one continuous xorshift32 stream, drawing once per state in ascending order per replicate, and reuse paired state signs across equations. Use plus-one two-sided p-values and requested checkpoints.
- `state_grouped_conformal`: assign states in ascending order to cyclic partitions by index modulo the declared partition count. For each test partition, use the preceding/registered calibration partition and remaining proper training. Reduce calibration residuals to the maximum absolute residual per calibration state before computing the state-level rank.
- `mediation_sensitivity_surface`: from baseline path-a `a`, path-b `b`, path-b SE, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`. For each direction, adjust `b`, indirect, direct, and proportion in declared R2 order. Compute equal-strength tipping from unrounded inputs.
- `trajectory_pca_clustering`: aggregate balanced county data to state-period means in declared feature order; standardize, PCA, deterministic k-means, and leave-year-out ARI as in the state profile.
- Decision: evaluate every declared support flag on unrounded values, count supported modules, and return the first matching class in the active precedence.

## Country Burden Revision Profile

Activation: country-label request with burden indicators, country-indicator panel, PCA/clustering, and country burden answer template.

Reconciliation and quality:

- Resolve each requested label against `countries.canonical_name`, `portal_label`, and pipe-separated `alternate_labels`.
- `resolved_iso3` is the unique resolved ISO3 list sorted ascending unless the template requests positional order.
- Count alias resolutions by comparing the requested label to the canonical country name.
- Use `revisions` rows for the requested country domain, indicators, and years. Report applicable applied and nonapplied event ids sorted ascending.
- Applied scale corrections should already appear in later final country indicator records. Pending or withdrawn notices do not authorize manual replacement.
- Treat unresolved scale-review cells as anomalies. In portal data these can appear as `quality_flag` values such as `SCALE_REVIEW`; include them in anomaly keys as `ISO3|YEAR|indicator_id`, sorted ascending.

Country cross-section:

- Resolve one final record per ISO3/year/indicator using highest revision and latest release.
- For the reference-year burden matrix, raw missing cells are cells with no selected value before anomaly exclusions.
- Exclude anomaly cells from the usable value set. Impute missing plus anomaly cells with the indicator-specific median among nonmissing, nonanomalous reference-year values.
- Standardize indicators across countries and run covariance PCA. Orient PC1 so the earliest maximum-absolute loading is positive. Because burden indicators are higher-worse, PC1 should represent higher burden; if the whole PC sign is contrary to the burden direction, flip scores and loadings consistently.
- Report top absolute PC1 loadings by descending absolute loading, breaking exact ties by indicator id ascending.

Country clustering and panel:

- Run deterministic k-means on retained burden PC scores for the requested cluster count. Order burden labels by cluster mean PC1: lowest mean is low burden, highest mean is high burden.
- For silhouette selection, evaluate candidate k values requested by the template/request, use Euclidean distances, singleton silhouette zero, choose largest unrounded average silhouette, then smaller k on ties.
- For panel modeling, build year-specific PC1 burden scores from the same requested burden indicators for each panel year, using the same anomaly and median-imputation rule within each year. Join life expectancy for the same ISO3/year records.
- Fit life expectancy on PC1 and region fixed effects with an intercept. Report coefficient, standard error, p-value, R-squared, observation count, and whether region fixed effects were used.
- Advisory is controlled by the active template/request. Typically, an adverse and statistically supported life-expectancy gradient for the high-burden segment triggers the high-priority advisory; otherwise select the monitor/no-gradient enum according to the request language.

## State Weighted Robustness Profile

Activation: exact `protocol_id` `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Release and cohorts:

- Resolve final state health records by effective status, value type, source type, revision, latest release, and profile tie-break.
- Join selected outcome, exposure, adjustments, region, and reliability weights. The fixed weight is the selected direct outcome sample size unless the active request overrides it.
- The primary cohort is reference-year complete; the balanced cohort is complete across all requested study years.

Modules:

- `cluster_jackknife`: fit reliability-weighted linear regression in declared design order. Use HC3 for full-model inference as needed and delete one Census division at a time for jackknife. Percent change is `100*abs((b_delete-b_full)/b_full)`. Test the bias-corrected coefficient with jackknife SE and `G-1` df.
- `nested_elastic_net`: build raw, squared, and interaction features in exact order. For each weighted fit, compute training-only weighted means and weighted population SDs, center y by weighted mean, cold-start coefficients, and solve cyclic elastic net. Outer and inner folds are ordered Census divisions. Inner selection uses pooled unweighted validation RMSE; ties choose smaller lambda. Report cycles, nonzero counts, inner grids, and pooled OOF metrics.
- `wild_cluster_bootstrap`: studentize the weighted target coefficient with division CR1. Fit the restricted model without the target. Use xorshift32, one continuous stream, one sign per division per replicate in registered order, plus-one exceedance p-value, and the requested quantile method.
- `grouped_conformal`: reuse nested outer predictions and selected penalties. For each held-out division, create calibration predictions by leaving out each other division from its training set, then use pooled absolute residuals for the finite-sample radius. Aggregate pooled coverage, mean width, and worst division by unrounded coverage.
- `trajectory_pca_clustering`: build state trajectories in declared variable/year block order, including transformed sample-size blocks when requested. Standardize, PCA, deterministic three-means on retained PCs, handle empty clusters by moving the farthest ASCII-first entity if specified, and recompute leave-year stability.
- `exhaustive_source_perturbation`: resolve alternate rollup/direct source pairs. Order replacement-eligible states by descending absolute alternate-minus-primary value difference, tied by state code. Enumerate every bitmask scenario, retain fixed direct reliability weights, refit WLS+HC3, summarize popcount strata, max shift, stability count, and exact signed Shapley effects.
- Decision: evaluate module flags in declared precedence. If any fail, return the controlled `NOT_ROBUST_AT_<FIRST_FAILED_MODULE>` value; otherwise return the active all-pass value.

## County Panel Dynamics Profile

Activation: exact `protocol_id` `PHO_COUNTY_PANEL_TRANSPORT_V1`.

Release and panel construction:

- Resolve final county health and socioeconomic records independently using the declared final revision/latest release rule.
- Retain counties complete across every balanced-panel year with valid RUCC.
- Create adjacent end-year rows ordered by county identifier then end year. Derive lagged levels, changes, end-year indicators, RUCC indicators, and dynamic terms exactly in declared order.

Modules:

- `delete_state_two_step_gmm`: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. First step uses identity moments; second step uses state-cluster score covariance and the registered pseudoinverse cutoff. Refit both steps after each state deletion. Bias-correct coefficients with delete-state jackknife and retain maximum absolute shifts.
- `nested_elastic_net`: allocate states to outer folds by descending retained-row counts, assigning to the currently smallest fold and lower fold id on ties. Reallocate inner folds inside each outer train set. Standardize only declared continuous terms from training population moments, leave indicators unchanged, keep intercept unpenalized, traverse the declared alpha/l1-ratio grid, and tie-break by smaller alpha then smaller l1 ratio.
- `wild_cluster_bootstrap_t`: fit full unpenalized OLS over common-design terms, then restricted OLS without the target. Use xorshift32 in ascending state order, plus-one absolute-tail p-value, nearest-rank quantiles, and declared checkpoints.
- `grouped_conformal_calibration`: use nested elastic-net OOF predictions in original analytic-row order. For each held-out outer fold, calibrate on absolute OOF residuals from all other folds. Report fold, state, RUCC-band, prediction-decile, overall, and minimum-state coverage. Prediction deciles are assigned after sorting by prediction and declared identifiers.
- `trajectory_pca_clustering`: build county trajectories in variable-major/end-year order. Standardize with population moments, use covariance `Z'Z/n`, evaluate declared candidate cluster counts by deterministic k-means and Euclidean silhouette, choose largest unrounded silhouette then smaller k, and compute delete-state ARIs by rebuilding the full pipeline.
- `source_group_perturbation`: for each declared source group and outer fold, remove exactly those terms and reuse that fold's full-model selected hyperparameters without retuning. Pool squared errors for RMSE, compute deterioration from full-model OOF RMSE, count worse folds, and rank by decreasing unrounded deterioration then declared group order.
- Decision: evaluate the six gates in order on unrounded values and select the active controlled decision by pass count/precedence.

## Validation Checklist

Before returning:

- Confirm every requested top-level key exists and no prohibited narrative is present.
- Confirm every list length and order matches `answer_template.json`.
- Confirm aligned arrays have the same entity/fold/order basis.
- Confirm numeric precision, null handling, booleans, integer fields, and enum values match the template.
- Confirm checkpoint PRNG state is recorded after completing the checkpoint replicate, never before.
- Confirm decisions were made from unrounded values.
- Confirm no training answer constants, solved cohort lists, solved coefficients, or solved classifications were copied into the output.
