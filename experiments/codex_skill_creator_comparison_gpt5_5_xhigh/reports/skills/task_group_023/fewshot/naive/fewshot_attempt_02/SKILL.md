---
name: solve-pho-audits
description: Solve Public Health Observatory portal audit tasks from prompt.txt, analysis_request.json, and answer_template.json. Use for PHO JSON-only analytical audits that require portal release resolution, cohorts, regression/GMM, nested ridge or elastic-net validation, wild cluster bootstrap, conformal calibration, PCA/k-means clustering, source perturbation, mediation sensitivity, country burden revision reconciliation, and controlled decisions; especially exact protocol_id values PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, and PHO_COUNTY_PANEL_TRANSPORT_V1.
---

# Public Health Observatory Audits

## Core Contract

Use the task's `prompt.txt`, `analysis_request.json`, and `answer_template.json` as the only output contract. Replace `<TASK_ENV_BASE_URL>` with the task-provided portal base URL. Submit exactly one JSON object, no narrative.

Do not reuse solved values from any prior task. This skill contains method semantics only: bind entities, measures, years, sources, random seeds, grids, thresholds, field names, enum values, and output keys from the active request and template, then recompute all evidence from the portal.

Do not include a `protocol_registry_record` in the answer unless the active `answer_template.json` explicitly requires it. In training examples it was provenance, not solver-visible evidence.

## Portal Access

Prefer CSV exports over scraping HTML:

`GET /download?dataset=<dataset>&format=csv`

Available datasets observed in the portal:

- `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`
- `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, `latitude`, `longitude`
- `countries`: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`
- `state_health`: `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`
- `state_socioeconomic`: `record_id`, `state_fips`, `state_abbr`, `year`, `release_status`, `revision`, `released_at`, socioeconomic fields, `population`, `quality_flag`
- `county_health`: `observation_id`, `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, `low_ci`, `high_ci`, `population`, `suppression_flag`, `quality_flag`
- `county_socioeconomic`: `record_id`, `county_fips`, `state_abbr`, `region`, `year`, `release_status`, `revision`, `released_at`, socioeconomic fields, `population`, `quality_flag`
- `country_indicators`: `observation_id`, `country_label`, `iso3`, `year`, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`
- `revisions`: `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, `old_value`, `new_value`, `status`, `issued_at`, `reason_code`, `note`

Filter locally unless the task is small enough for endpoint filters. Use `/catalog` and `/methodology` only to confirm schema or policy. Do not call judge endpoints.

## One Effective Request

Before data access or random draws, resolve the complete effective request:

1. Verify exact `protocol_id` when a profile below applies.
2. Start from that protocol's method semantics only.
3. Apply direct task keys to the identical canonical path.
4. Treat `<section>_overrides` as targeting `<section>` and `module_overrides.<module>` as targeting that exact module.
5. Recursively merge objects, replace arrays whole, and replace scalar/string/Boolean/null values only at the exact path.
6. Reject unknown targets, inferred aliases, array concatenation, positional patches, and type coercion.

Evaluate gates on unrounded values after all modules are complete. Round only final reported numbers, using the precision requested by `answer_template.json` or `analysis_request.json`. Preserve declared list orders; when no order is declared, use stable identifier ASCII order for entities and group-name ASCII order for groups.

## Release Resolution And Cohorts

Resolve each requested publication series independently by entity, time, measure/field, status, source, and value type.

- Keep selected publication records for release counts before analytic exclusions when requested.
- Treat suppressed rows, invalid quality flags, blank values, and null values as unavailable for analytic completeness. Never zero-fill.
- Use the request/profile tie rule. Common default: greatest final `revision`, latest `released_at`, then the specified record id direction. `PHO_STATE_TRANSPORT_AUDIT_V1` uses lowest record id for the final tie; `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` uses greatest record id. If the request names priority fields without a direction, use highest revision, latest timestamp, then ascending stable id unless explicit text says greatest.
- Join resolved series by stable entity-time keys. Construct complete, balanced, broad, machine-learning, strict dual-source, or primary cohorts exactly from the effective completeness predicates.
- Preserve aligned orders: entity order, year/end-period order, feature order, coefficient order, source-group order, checkpoint order, and grid order.

## Common Numerical Rules

Use task-local scripts for computation. Avoid library defaults for HC3, CR1, GMM, CV aggregation, or PRNGs unless you verify they match the formulas here.

OLS: solve in declared column order. Weighted least squares uses `sqrt(w)X` and `sqrt(w)y`.

HC3 for WLS: `h_i=diag(Xw (Xw'Xw)^-1 Xw')`, `ew_i=sqrt(w_i)(y_i-X_i b)`, and
`V=(Xw'Xw)^-1 Xw' diag(ew_i^2/(1-h_i)^2) Xw (Xw'Xw)^-1`. Use two-sided Student t with `n-k` df unless the request says otherwise.

Cluster CR1: for ordered clusters `g`, `s_g=X_g'e_g` or `Xw_g'ew_g`,
`V=[G/(G-1)] [(n-1)/(n-k)] (X'X)^-1 sum_g(s_g s_g') (X'X)^-1`. Use `G-1` df for two-sided cluster t tests.

Jackknife: for `G` delete estimates `b_-g`, `bbar=mean(b_-g)`, `SE=sqrt((G-1)/G sum((b_-g-bbar)^2))`, and `b_BC=G*b_full-(G-1)*bbar`. Select extrema/influence by unrounded statistic, then declared order.

Ridge/elastic net validation: standardize features using training-only moments for every fold. Pool validation squared errors at row level before taking RMSE. Select the smallest unrounded inner RMSE, then the smaller penalty values in declared grid order. Refit on all outer-training rows and assign exactly one out-of-fold prediction per eligible row.

Conformal ranks: sort absolute calibration residuals. With coverage `c`, use one-based rank `min(m, ceil((m+1)c))`; with miscoverage `alpha`, use `c=1-alpha`. Intervals are inclusive and symmetric about the registered prediction source.

PCA: build columns in declared variable/time order, standardize each active column with the profile's sample or population divisor, eigendecompose the covariance/cross-product matrix, sort eigenvalues descending, and orient each loading vector so the earliest maximum-absolute loading is positive unless a burden-oriented task requires the high-burden direction to be positive. Scores are standardized data times oriented loadings.

K-means: use deterministic farthest-first initialization unless the request states another initialization. First center is the smallest entity id; each next center is the entity farthest from its nearest center, tied by entity id. Assign ties to lower cluster id, update by arithmetic centroid means, and stop on unchanged labels or the registered cap. Canonicalize labels only as the profile says; do not reorder aligned score arrays.

Adjusted Rand index: compute from the contingency table with
`(sum_ij C(n_ij,2)-expected)/(0.5*(sum_i C(a_i,2)+sum_j C(b_j,2))-expected)`, where `expected=sum_i C(a_i,2)*sum_j C(b_j,2)/C(n,2)`. Align refit labels by maximum agreement, tied by lexicographically smallest permutation.

Nearest-rank quantile: sorted `x[min(B, ceil(pB))-1]`. Type-seven quantile: `h=(B-1)p`, `j=floor(h)`, `gamma=h-j`, `(1-gamma)x[j]+gamma x[j+1]`.

## Protocol PHO_STATE_TRANSPORT_AUDIT_V1

Execute modules in this order: release/cohorts, delete-cluster fixed effects, nested ridge division CV, PCG32 Webb wild bootstrap, grouped split conformal ridge, trajectory PCA clustering, source-year perturbation, controlled decision.

Fixed effects: double-demean every modeled variable as `z_it - entity_mean - time_mean + grand_mean`; fit OLS without intercept in declared predictor order. For each delete-state refit, remove the whole state, recompute means, and refit from scratch.

Nested ridge: leave one census division out. Inside each outer training set, leave each remaining division out for inner validation in ordered division order. Use training sample SD with `ddof=1`, center outcome, keep intercept unpenalized, and minimize `mean((y-a-Xb)^2)+lambda*sum(b_j^2)`. Coordinate update:
`b_j=sum_i x_ij*r_ij/(sum_i x_ij^2+n*lambda)`, where `r` excludes feature `j`.

Wild bootstrap: fit the restricted fixed-effects model without the target. Use PCG32 with unsigned 64-bit state, `increment=2*stream+1`, multiplier `6364136223846793005`, rotate-right 32-bit output, and map output modulo six to `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`. Maintain one continuous stream, drawing once per state in entity-code order per replicate. If the template asks for weight-index rows, report the raw modulo-six indices aligned to state order for the requested replicates. Count `abs(t*) >= abs(t_observed)` and use plus-one p. If batch exceedance counts are requested without explicit cutpoints, aggregate consecutive 100-replicate batches plus the final remainder.

Grouped conformal: each ordered division is test; choose calibration among remaining divisions by greatest row count then ascending division name; train on the rest. Fit fixed-lambda ridge with the same scaling and solver rules.

Trajectory: use variable-major/year order from the request, sample-SD covariance, deterministic three-means, and leave-year-out stability. Rebuild scaling, PCA, orientation, initialization, and clustering for every omitted year.

Source-year perturbation: keep the strict dual-source cohort fixed. Enumerate year subsets by increasing requested subset size and lexicographic tuple order. Refit primary and parallel fixed-effects models with CR1 inference; shift is `100*abs(b_alt-b)/abs(b)`. Same sign requires both coefficients nonzero with identical sign.

## Protocol PHO_COUNTY_MEDIATION_TRANSPORT_V1

Execute modules in order: publication/linked cohorts, primary mediation models, difference GMM mediation, nested state ridge, paired state wild bootstrap, state grouped conformal, partial-R2 sensitivity, state trajectory PCA clustering, controlled precedence.

Publication/cohorts: resolve county health and socioeconomic releases independently by request filters and release priority. Suppressed selected health rows count as selected publication evidence but fail analytic completeness. Build primary-year, balanced-panel, and machine-learning cohorts from the effective nonmissing predicates.

Primary mediation: build total-effect, path-a, and direct/path-b OLS designs from the effective exposure, mediator, outcome, transformations, references, and column order. Keep unrounded fits for bootstrap and sensitivity.

Difference GMM: create adjacent-change rows in entity then end-period order. For each equation use `W=(Z'Z)^-1` and `beta=(X'Z W Z'X)^-1 X'Z W Z'y`. Use clustered sandwich over state scores; for indirect `theta=a*b`, `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`. Compute first-stage partial F from full-vs-reduced RSS. Delete-state diagnostics rebuild rows and refit from scratch.

Nested state ridge: use the effective base and augmented feature arrays. Standardize with training arithmetic means and population SD, using divisor one for zero variance. Leave one state out for outer and inner folds. Minimize training SSE plus `lambda` times squared non-intercept norm. Select by pooled row-level inner RMSE, then smaller lambda.

Paired state wild bootstrap: restricted model removes each target in turn. Use unsigned xorshift32 with shifts 13, 17, 5 and 32-bit masking after each xor; odd state maps to `+1`, even to `-1`. Maintain one stream, draw states ascending once per replicate, and reuse the same state sign across paired equations. Use absolute exceedances and plus-one p.

State grouped conformal: sort states ascending, assign cyclic partitions by index modulo partition count, use the preceding partition as calibration, and train on the rest. Reduce residuals to one maximum absolute residual per calibration state before rank selection.

Partial-R2 sensitivity: from baseline `a`, `b`, `SE_b`, and residual df, compute `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`; for each direction use `adjusted_b=b-s*magnitude`, `adjusted_indirect=a*adjusted_b`, `adjusted_direct=total-adjusted_indirect`, and `proportion=adjusted_indirect/total`. Enumerate the full surface in declared R2 and direction order.

Trajectory: aggregate balanced-panel measures to state-period means in declared feature order, standardize with sample SD across states, orient PCA, run deterministic k-means, and compare leave-year-out refits with ARI.

## Protocol PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Execute modules in order: release/cohort, common weighted linear algebra, cluster jackknife, nested elastic net, wild cluster bootstrap, grouped conformal, trajectory PCA clustering, exhaustive source perturbation, controlled decision.

Release/cohort: select greatest revision, latest release timestamp, then greatest record id. Keep the selected direct outcome sample size as the fixed positive reliability weight, including source-perturbation fits, unless the effective request overrides it.

Weighted regression: use WLS, HC3, and CR1 formulas above. Region indicators use the request's reference category and design order.

Cluster jackknife: delete each registered census division in order, refit unchanged weighted design from scratch, compute percent change `100*abs((b_-g-b)/b)`, and choose most influential by greatest unrounded change then earlier division order. Test `b_BC/SE_JK`.

Nested weighted elastic net: outer and inner folds leave one registered cluster out. Build raw, transformed, squared, and interaction features in declared order. Compute training-only weighted means and weighted population SDs. Center `y` by weighted training mean. Minimize
`sum w_i(y_i-Z_i b)^2/(2 sum w_i) + lambda*(alpha*sum|b_j| + (1-alpha)sum b_j^2/2)`.
Cold-start for every fold and penalty. Coordinate update:
`rho_j=sum w_i Z_ij(y_i-sum_{l!=j}Z_il b_l)/sum w_i`,
`b_j=S(rho_j,lambda*alpha)/(1+lambda*(1-alpha))`.
Pool unweighted validation errors for selection and OOF metrics.

Wild bootstrap: use weighted restricted model without the target. Xorshift32 draws one sign per cluster in registered order, low bit one to `+1`, otherwise `-1`. Refit WLS, recompute CR1, record absolute studentized target, checkpoints, final state, and type-seven requested quantiles.

Grouped conformal: reuse nested elastic-net outer center predictions. For each outer cluster, calibrate by holding out each other training cluster once, cold-refitting the same weighted elastic-net algorithm, and pooling absolute residuals. Rank by nominal coverage.

Trajectory: build variable-major/time-major blocks in entity ASCII order, standardize with sample SD, eigendecompose `Z'Z/(n-1)`, orient loadings, run deterministic k-means with empty-cluster repair by moving the ASCII-first farthest assigned entity, and report leave-year aligned changes.

Exhaustive source perturbation: resolve alternate outcomes by module filters. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. For every mask `0..2^m-1`, replace entity `j` iff `mask & (1<<j)`, keep direct weights and design, refit WLS+HC3, summarize popcount strata, choose maximum shift by unrounded shift then smaller mask, and compute signed exact Shapley effects in ordered entity order.

## Protocol PHO_COUNTY_PANEL_TRANSPORT_V1

Execute modules in order: publication balanced panel, delete-state two-step GMM, state-blocked nested elastic net, state wild cluster bootstrap t, cross-fold grouped conformal, county trajectory PCA clustering, source-group perturbation, controlled precedence.

Balanced panel: resolve county health and socioeconomic final records independently. Retain entities complete across every effective balanced period with valid RUCC. Create adjacent-change rows ordered by county identifier then end period, deriving lagged levels, dynamic changes, reference indicators, and interactions in declared order.

Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. First step uses identity weighting; second step builds state scores `s_g=Z_g'u_g`, `S=sum(s_g s_g')/n`, and the registered Moore-Penrose inverse of `S`. Compute Hansen `J=n*g(theta)'Wg(theta)`. Refit both steps after each state deletion and compute bias-corrected coefficients.

State-blocked nested elastic net: allocate states by descending retained-entity counts to the smallest fold, lower fold id on equality; sort state codes within folds and repeat inside outer training for inner folds. Standardize continuous terms by training population moments, leave indicators unchanged, and keep intercept unpenalized. Objective:
`SSE/(2n)+alpha*(rho*sum|beta_j|+0.5*(1-rho)sum beta_j^2)`.
Cold-start intercept at training outcome mean; update intercept by mean residual, then coefficients by soft threshold in declared order. Select by pooled inner RMSE, then smaller alpha, then smaller l1 ratio.

Wild cluster bootstrap: fit full unpenalized OLS and state-cluster CR1 for the target. Fit restricted model without the target, generate state-weighted synthetic outcomes with xorshift32 signs, refit full model, recompute CR1, use absolute-tail plus-one p, and nearest-rank quantiles.

Cross-fold conformal: use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. Report fold, state, RUCC-band, and prediction-bin diagnostics. Assign prediction bins after sorting by prediction and declared identifiers; signed gap is prediction mean minus observation mean.

County trajectory: build variable-major county trajectories over declared end years, standardize by population moments, use covariance `Z'Z/n`, orient loadings, run deterministic k-means for each candidate k, compute Euclidean silhouette with singleton value zero, choose highest unrounded mean silhouette then smaller k, and rebuild the pipeline for each delete-state ARI.

Source-group perturbation: for each declared source group and outer fold, remove exactly that group's terms and reuse the full-model selected hyperparameters without retuning. Apply the same preprocessing/solver on remaining terms, pool RMSE, subtract full-model OOF RMSE for deterioration, count worse folds, and rank by decreasing unrounded deterioration then declared group order.

## Country Burden Revision Audits

Use this section when the request asks for a country burden/revision audit and no exact protocol profile is present.

Reconcile each requested country label against `countries.canonical_name`, `portal_label`, and pipe-delimited `alternate_labels`. Require one unique match per requested label. Report sorted unique ISO3 values when the template asks for set-like lists. Count alias resolutions as requested labels whose text is not the canonical country name.

For country indicator releases, filter to requested ISO3, years, indicators, and final status. Select greatest revision, latest `released_at`, then stable observation id. Applied revision notices document corrected final revisions; non-applied notices do not authorize replacement. Treat `SCALE_REVIEW` cells with non-applied scale-correction notices as unresolved anomalies: report their `ISO3|YEAR|indicator_id` keys, exclude them from analytic values, and do not substitute the notice's proposed value. Count raw missing cells before anomaly exclusions when requested.

For a completed 2022 burden PCA matrix, impute missing or anomaly-excluded requested burden cells after quality exclusions using a deterministic column-level rule; prefer the request/methodology rule if stated, otherwise use the reference-year mean of that indicator among resolved usable countries. Count every imputed cell. Standardize burden indicators, orient PC1 so higher requested burden corresponds to larger PC1, and report top absolute loadings by descending absolute loading, tied by indicator id.

For country clusters, run deterministic k-means on retained burden scores for requested `k`; label the ordered segments by mean PC1 burden as `LOW_BURDEN`, `MIDDLE_BURDEN`, and `HIGH_BURDEN`. For silhouette-selected k, evaluate candidate counts requested by the template, compute Euclidean silhouette, and choose highest unrounded silhouette then smaller k. Sort high-burden ISO3 output ascending if the template says set-like.

For the region-adjusted panel model, build a country-year panel over the requested years where life expectancy and the same completed burden-score construction are available. For a request that defines a reference-year burden PCA and a multi-year panel, score panel rows with the reference-year burden orientation, loadings, and scaling unless the request explicitly asks to refit PCA over the panel. Include region fixed effects when requested, using stable region labels and one reference category. Fit OLS of life expectancy on PC1 plus region indicators; report coefficient, standard error, p-value, R-squared, and advisory strictly from the template's decision wording.

## Final Checks

Before answering:

- Confirm all required top-level keys and nested keys from `answer_template.json` are present.
- Confirm no unexpected keys are present unless the template allows them.
- Confirm every aligned array has the requested length and order.
- Confirm JSON has no `NaN`, `Infinity`, comments, or narrative.
- Confirm booleans, integers, strings, enums, and `null` match the template.
- Recompute controlled decisions from unrounded module values and only then round reported statistics.
