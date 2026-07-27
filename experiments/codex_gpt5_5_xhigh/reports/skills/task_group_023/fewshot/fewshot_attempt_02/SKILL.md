---
name: pho-algorithmic-audits
description: Solve Public Health Observatory portal audit tasks by ingesting portal evidence, resolving publication releases and cohorts, and executing the registered statistical modules for the supported audit families.
---

# Public Health Observatory Algorithmic Audits

## When To Use

Use this skill for Public Health Observatory tasks that provide a prompt, `analysis_request.json`, and `answer_template.json`, and require evidence from the Web portal declared in `environment_access.md`.

Activate exact registered profiles only when the active request has one of these exact `protocol_id` values:

- `PHO_STATE_TRANSPORT_AUDIT_V1`
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`
- `PHO_COUNTY_PANEL_TRANSPORT_V1`

Also use this skill for the country burden revision audit whose request/template asks for country label reconciliation, revision/anomaly accounting, reference-year burden PCA, burden clusters, a region-adjusted life-expectancy panel model, and an advisory.

Do not reuse solved values from previous tasks. Bind all entities, measures, fields, years, release filters, grids, seeds, thresholds, output names, enum values, and business predicates from the active request and answer template, then recompute every output.

## Evidence Access

1. Read the active prompt, `analysis_request.json`, and `answer_template.json` completely before fetching data.
2. Read `environment_access.md` for `GDPEVO_ENV_BASE_URL`. Use only that base URL and only the allowed portal endpoints.
3. Prefer full CSV downloads through `/download?dataset=<dataset>&format=csv`; parse identifiers such as FIPS, ISO3, and state codes as strings.
4. Fetch only the datasets required by the active request:
   - `states`: state FIPS, abbreviation, name, region, division, state/DC flag.
   - `counties`: county FIPS, state, region, RUCC, metro class, population, coordinates.
   - `countries`: ISO3, canonical and portal labels, alternate labels, region, income group.
   - `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`, and `revisions`.
5. Use `/catalog` and `/methodology` only to confirm schema, release policy, identifier semantics, quality flags, suppression, country aliases, and indicator directions.

## Global Rules

- Resolve one effective request contract before computation. Apply exact-key overrides by deep-merging objects, replacing arrays in full, replacing scalars at the exact path, and rejecting unknown targets, implicit aliases, positional patches, array concatenation, or type coercion.
- Select publication records independently for each requested entity-time-measure key. Filter by the effective release status, value type, source type, geography, validity, and measure bindings. Use the priority order declared by the request/profile; when the profile specifies a final tie rule, follow it exactly.
- Suppressed records, invalid quality flags, withdrawn records, blank strings, and null analytic values are unavailable. They may count as selected publication evidence when the template asks for selected release counts, but they are incomplete for analytic cohorts. Never zero-fill unavailable values.
- Preserve every declared order: years, measures, features, coefficients, grid values, divisions, states, source groups, checkpoint replicates, quantile probabilities, and output arrays. When no order is declared for set-like identifiers, sort by stable ASCII identifier.
- Use unrounded values for fitting, selection, ranking, gates, and controlled decisions. Round only final reported noninteger statistics to the precision declared by the request/template. Use JSON integers and booleans naturally; use JSON `null` only for mathematically unavailable values, never NaN or Infinity.
- Refit from scratch for every deletion, bootstrap replicate, inner fold, outer fold, source perturbation, and stability run unless the protocol explicitly says to reuse predictions or selected hyperparameters.

## Shared Statistical Primitives

- OLS solves `(X'X)^-1 X'y` in declared column order. WLS uses `sqrt(w) * X` and `sqrt(w) * y`.
- HC3 for WLS uses weighted leverage `h_i` from `Xw`, weighted residual `ew_i`, and sandwich diagonal `ew_i^2/(1-h_i)^2`; use two-sided Student t with `n-k` degrees of freedom.
- CR1 cluster covariance uses ordered cluster scores `s_g = X_g' e_g` and multiplier `[G/(G-1)] * [(n-1)/(n-k)]`; use two-sided Student t with `G-1` degrees of freedom unless the active profile states otherwise.
- Fixed effects in the state transport profile are two-way double demeaned: transform each modeled variable as `z_it - entity_mean - time_mean + grand_mean`, then fit without an intercept. Recompute all means for each deletion.
- Ridge models center training outcomes, keep the intercept unpenalized, standardize features using training-only moments, and choose penalties by pooled validation squared errors, not by averaging fold RMSEs.
- Elastic-net models cold-start every fit, standardize only the declared continuous/raw feature columns using training-only moments, keep the intercept unpenalized, and select by smallest unrounded pooled validation RMSE with declared tie-breakers.
- Conformal intervals are symmetric and inclusive. Sort absolute calibration residuals, use the finite-sample rank declared by the profile, and aggregate coverage/width by held-out row counts unless the template asks for group-level summaries.
- PCA builds features in declared order, standardizes columns by the profile's requested population or sample standard deviation, eigendecomposes the covariance matrix, sorts eigenpairs descending, orients loadings deterministically, and scores as `Z * loadings`.
- K-means uses deterministic initialization, squared Euclidean distance, lower-id assignment ties, arithmetic centroid updates, and the profile's convergence/tie rules. Compute adjusted Rand index from the contingency table for stability modules.
- Wild bootstrap generators are continuous streams. Draw clusters in the registered order for each replicate and record checkpoints only after the completed replicate. Use the profile-specific PRNG and quantile rule.

## Profile: PHO_STATE_TRANSPORT_AUDIT_V1

Module order: release/cohort resolution, delete-cluster fixed effects, nested leave-division-out ridge, PCG32 Webb wild cluster bootstrap, grouped split conformal ridge, trajectory PCA clustering, source/year perturbation, controlled decision.

Implementation details:

- Resolve `state_health` and `state_socioeconomic` series for the effective 51-jurisdiction universe. For state health, apply the requested value type/source/status filters and invalid quality flags. Select greatest revision, latest release timestamp, then the profile's record-id tie rule.
- Build the core balanced cohort from states complete for the core variables in every analysis year. Build the broad reference cohort from complete cases for the reference-year outcome and all ordered ridge features. Build the strict dual-source cohort from states complete for outcome, primary exposure, parallel exposure, and adjustments in every analysis year.
- Delete-cluster FE: fit the double-demeaned OLS over the ordered predictors, delete each state cluster in state-code order, compute jackknife mean, standard error, bias correction, t statistic, p-value, and min/max deletion diagnostics.
- Nested ridge: outer folds hold out census divisions in registered order; inner folds leave one remaining division out. Standardize with training-only sample SD. Coordinate-descent ridge uses the declared feature and lambda order; select smallest pooled inner RMSE, breaking ties to the smaller lambda.
- Wild bootstrap: use the restricted model without the target exposure, PCG32 with the effective seed and stream, Webb six-point weights, plus-one two-sided p-value, batch exceedance counts, and nearest-rank quantiles.
- Grouped split conformal: for each outer division, choose calibration among remaining divisions by greatest row count then ascending division name; train ridge on the rest with the fixed lambda and report fold and aggregate calibration.
- Trajectory PCA: build variable-major/year columns for effective outcome and exposure trajectories, use covariance PCA, deterministic three-means, full scores/loadings/labels, and leave-year-out ARI/agreement.
- Source/year perturbation: enumerate year subsets by increasing size and lexicographic tuple order; fit primary and parallel double-demeaned models with CR1 inference and report sign/shift stability.
- Evaluate every robustness gate on unrounded values and use only the active request's decision mapping.

## Profile: PHO_COUNTY_MEDIATION_TRANSPORT_V1

Module order: publication/cohort audit, primary mediation models, difference-GMM mediation, nested leave-state-out ridge, paired restricted-null state bootstrap, state-grouped conformal, partial-R2 sensitivity, state trajectory PCA clustering, controlled conclusion.

Implementation details:

- Resolve county health and socioeconomic publications by active filters and declared release priority. Join to county geography for region, state, and RUCC. Count selected releases before completeness exclusions when requested.
- Primary cohort is active primary-year basic completeness. Balanced panel cohort is complete for every requested year. Machine-learning cohort is primary cohort plus all requested ML fields.
- Build total-effect, path-a, and direct/path-b primary-year OLS designs using the active exposure, mediator, outcome, transformations, RUCC reference dummies, and covariate order. Keep unrounded fitted objects for bootstrap and sensitivity.
- Difference GMM: create adjacent-change rows in entity then end-period order. Use the declared lagged instruments and controls; fit `beta=(X' Z W Z' X)^-1 X' Z W Z' y` with `W=(Z'Z)^-1`. Use clustered sandwich and cross-equation covariance for the indirect effect. Compute first-stage partial F from full vs reduced RSS. Refit all equations for every delete-state diagnostic.
- Nested state ridge: build base and augmented feature maps in exact order. Standardize with training arithmetic means and population SD, using divisor one for zero-variance features. Outer and inner folds leave states out. Select lambda by pooled county-row RMSE and report all aligned inner grids.
- Paired bootstrap: for each target equation fit its restricted-null model, generate synthetic outcomes with one xorshift32 state sign reused across paired equations, refit unrestricted OLS, recompute CR1 t statistics, record all checkpoints, use plus-one p-values and nearest-rank/bootstrap-t intervals.
- State-grouped conformal: assign states cyclically in ascending order to the requested number of partitions. For each test partition use the preceding registered partition for calibration and remaining partitions for proper training. Reduce calibration to one maximum absolute residual per calibration state before ranking.
- Partial-R2 sensitivity: enumerate the complete requested surface. For each row compute the adjusted path-b, adjusted indirect, adjusted direct, and proportion from unrounded baseline quantities; solve the equal-strength positive tipping R2 from the same quantities.
- State trajectory PCA: aggregate balanced county measures to state-period means in declared feature order, perform covariance PCA, deterministic k-means, and leave-year-out ARI.
- Finish all modules before evaluating controlled flags and classification precedence.

## Profile: Country Burden Revision Audit

Use this for the country burden template even though it may not declare a registered `protocol_id`.

Implementation details:

- Reconcile every requested label to a unique ISO3 by matching `countries.portal_label`, `canonical_name`, and pipe-separated `alternate_labels`. Count aliases when the requested label differs from the canonical name. Report ISO3 sets sorted ascending.
- Select final `country_indicators` records for requested burden indicators and life expectancy by ISO3, year, and indicator using highest revision, latest release timestamp, then stable observation-id tie-breaking.
- Revision audit: filter `revisions` to requested countries, requested indicators, and the active panel years. Report applicable APPLIED scale-correction event ids separately from applicable non-APPLIED event ids. Treat non-APPLIED scale-correction cells as unresolved anomalies, keyed as `ISO3|YEAR|indicator_id`.
- For the reference-year PCA matrix, count raw missing cells before anomaly exclusion. Then set raw missing and unresolved anomaly cells to missing and impute with the reference-year median of that indicator over available requested countries. The imputed cell count is raw missing plus reference-year anomaly cells after quality exclusion.
- Standardize the completed reference-year matrix with sample SD, compute covariance PCA, and orient PC1 so larger scores mean greater burden. If an input indicator is favorable by dictionary direction, reverse its standardized sign before PCA unless the request already defines it as a gap or burden measure.
- Report the PC1 variance fraction and the top absolute PC1 loadings sorted by descending absolute loading, then indicator id for exact ties. The retained component count for this audit is the number of burden score components used downstream, normally PC1 unless the active request overrides it.
- Cluster on the reference-year PC1 scores with optimal one-dimensional contiguous k-means: sort scores ascending, choose breakpoints minimizing within-cluster SSE, and label requested three-cluster segments by ascending cluster mean as low, middle, high burden. Compute average silhouette on PC1 distances for candidate k values requested by the template and select the largest unrounded silhouette, breaking exact ties to smaller k.
- For the panel model, use the reference-year median imputers, means, SDs, and oriented PC1 loading vector to score every active panel country-year. Drop rows lacking the selected life-expectancy outcome. Fit OLS `life_expectancy ~ PC1 + region fixed effects` with the first sorted region as reference, report classical SE, two-sided Student t p-value, R-squared, and the fixed-effects boolean.
- Apply the advisory rule from the active prompt/template using unrounded panel evidence and the high-burden segment.

## Profile: PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Module order: release/cohort, common weighted linear algebra, reliability-weighted cluster jackknife, nested weighted elastic net, restricted-null xorshift32 wild bootstrap, grouped conformal, trajectory PCA clustering, exhaustive source perturbation, controlled decision.

Implementation details:

- Resolve the state primary and balanced cohorts from `state_health`, `state_socioeconomic`, and `states` using the active direct/parallel source definitions. Keep the selected direct outcome sample size as the fixed positive reliability weight even in source-perturbation fits.
- WLS/HC3/CR1 follow the shared formulas. The primary design uses the active intercept, exposure, adjustments, income scaling, region dummies, and reference category.
- Cluster jackknife deletes each census division in registered order, refits WLS from scratch, reports percent changes against the full coefficient, computes bias-corrected coefficient and jackknife inference, and selects the most influential division by greatest unrounded absolute percent change then earlier division order.
- Nested elastic net holds out each division as an outer fold and each remaining division as ordered inner folds. Build raw, squared, interaction, and transformed features in declared order. Use weighted training means and weighted population SDs; objective is weighted SSE plus the declared elastic-net penalty. Cold-start every fit and report cycles, nonzero counts, inner grids, outer diagnostics, and pooled unweighted OOF metrics.
- Wild bootstrap fits the weighted restricted model without the target, uses continuous xorshift32 signs over ordered divisions, refits full WLS, recomputes CR1 absolute t, records checkpoints and terminal state, counts exceedances with any declared tolerance, and uses the profile's type-seven quantile rule.
- Grouped conformal reuses nested outer center predictions and each fold's selected penalty. For each outer division, calibrate by leave-one-other-division refits, rank pooled absolute residuals, and report division diagnostics plus pooled coverage, width, and worst division.
- Trajectory PCA uses balanced state trajectories, declared variable/year blocks, covariance PCA, deterministic three-means over leading scores, empty-cluster handling from the profile, leave-year-out ARI, and aligned assignment changes.
- Exhaustive source perturbation orders alternate-eligible states by descending absolute alternate-minus-primary outcome difference, enumerates every replacement bitmask, retains direct weights/design, refits WLS/HC3, summarizes by popcount, selects maximum shift by unrounded shift then smaller mask, and computes exact signed Shapley effects.
- Evaluate decision flags in the active precedence order and return the first failed-module conclusion from the template.

## Profile: PHO_COUNTY_PANEL_TRANSPORT_V1

Module order: publication balanced panel, delete-state two-step GMM, state-blocked nested elastic net, restricted-null state wild bootstrap, cross-fold grouped conformal, county trajectory PCA clustering, source-group perturbation, controlled decision.

Implementation details:

- Resolve county health and socioeconomic records by active region/year/source/status/value filters. Join county geography and keep only counties complete across every balanced period with valid RUCC and requested socioeconomic fields.
- Create adjacent-change panel rows ordered by county identifier then end period. Derive lagged outcomes, lagged covariates, dynamic changes, end-period indicators, interactions, and RUCC indicators in declared order.
- Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. First step uses identity moment weight. Build state-cluster scores, compute `S`, use the registered Moore-Penrose inverse cutoff for the second-step weight, compute coefficients and Hansen J, then refit both steps for every delete-state diagnostic and jackknife bias correction.
- State-blocked nested elastic net: allocate states to folds by descending retained county counts, assigning to the currently smallest fold with lower fold id ties; sort state codes inside folds. Inside every fit, standardize declared continuous terms by training population moments and leave indicators unchanged. Traverse alpha and l1-ratio grids in declared order, pool inner squared errors, select by smallest unrounded RMSE then smaller alpha then smaller l1 ratio, and pool OOF metrics.
- Wild bootstrap: fit full unpenalized OLS over the common design and state-cluster CR1 for the target term. Fit restricted OLS without the target, use continuous xorshift32 state signs, refit full OLS for each replicate, count absolute-tail exceedances with plus-one p-value, use nearest-rank quantiles, and report requested checkpoints.
- Grouped conformal uses nested elastic-net OOF predictions in analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds, use `min(m,ceil((m+1)*coverage))`, and report fold, state, RUCC-band, prediction-decile, overall, and minimum-state diagnostics.
- County trajectory PCA builds variable-major county trajectories over declared end years, standardizes by population moments, uses covariance `Z'Z/n`, deterministic farthest-first k-means for each candidate k, Euclidean silhouette with singleton value zero, selected k by highest unrounded silhouette then smaller k, and delete-state ARI refits.
- Source-group perturbation removes each declared group of terms one at a time, reuses the corresponding full-model outer-fold selected hyperparameters without retuning, repeats the same preprocessing/solver on remaining terms, records fold RMSEs, pooled deterioration against the full OOF reference, worse-fold counts, and ranks by decreasing unrounded deterioration then declared group order.
- Evaluate all six gates on unrounded values and return the first applicable controlled decision from the active request/template.

## Output Assembly Checklist

Before submitting:

- Confirm every required key from `answer_template.json` is present and no extra narrative surrounds the JSON.
- Validate array lengths, aligned arrays, and cross-field cardinalities from the template.
- Recompute gates from unrounded module results; do not infer a decision from rounded reported values.
- Confirm all finite numbers are rounded to the requested precision and identifiers/enums exactly match the template/request.
- Run a JSON parser over the final object before returning it.
