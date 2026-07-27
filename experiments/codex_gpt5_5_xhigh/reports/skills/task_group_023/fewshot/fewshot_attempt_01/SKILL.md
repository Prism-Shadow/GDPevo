# Public Health Observatory Algorithmic Audit Skill

Use this skill for Public Health Observatory tasks that provide an
`analysis_request.json`, an `answer_template.json`, and a read-only portal base
URL. The skill is reusable method guidance only. Do not reuse solved values from
training examples: counts, coefficients, p-values, selected states, countries,
clusters, PRNG checkpoints, gate results, classifications, and memberships must
always be recomputed from the effective request and the authorized portal data.

## Activation

Activate the exact profile when the future request has one of these
case-sensitive `protocol_id` values:

- `PHO_STATE_TRANSPORT_AUDIT_V1`
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`
- `PHO_COUNTY_PANEL_TRANSPORT_V1`

Also activate the country burden workflow when the request/template identifies a
country burden revision audit, for example by `template_name:
country_burden_revision_audit_v1` or the combination of `country_labels`,
`burden_indicator_ids`, `panel_outcome_indicator_id`, and
`requested_cluster_count`.

For exact protocol profiles, bind all entities, measures, years, filters,
random seeds, grids, cutoffs, output field names, and decision vocabulary from
the future request. Profiles carry method semantics only.

## Portal Access

Read `environment_access.md` in the task workspace and use only its base URL and
allowed endpoints. Prefer CSV downloads through `/download?dataset=<name>&format=csv`
for full tables, then filter locally with a structured CSV parser. Useful
datasets are:

- `states`: state codes, regions, divisions, state/DC flag.
- `counties`: county FIPS, state, region, RUCC, population and coordinates.
- `countries`: ISO3-like stable IDs, canonical names, portal labels, alternate
  labels, region, income group.
- `state_health`, `state_socioeconomic`, `county_health`,
  `county_socioeconomic`, `country_indicators`, `revisions`.

The portal retains provisional/final status, revisions, timestamps, source and
value types, suppression flags, quality flags, and record IDs. Preserve these
fields until release resolution and audit counts are complete.

## Output Discipline

- Return exactly one JSON object following the future `answer_template.json`.
- Do not include a `protocol_registry_record` or any provenance key unless the
  future template explicitly requires or permits it.
- Preserve every declared order: years, features, coefficients, clusters,
  states, countries, folds, grids, source groups, checkpoints, and decision
  precedence.
- Compute predicates on unrounded values. Round only reported non-integers to
  the request/template precision. Keep integer and Boolean types natural.
- Use JSON `null` for mathematically unavailable values. Never emit `NaN`,
  `Infinity`, or stringified numbers.

## Effective Request Resolution

Before touching data or random generators, build one effective request:

1. Verify the exact `protocol_id` if the task uses a registered protocol.
2. Bind direct request keys to same-named canonical keys.
3. Resolve override aliases: root `<section>_overrides` targets `<section>`;
   `module_overrides.<module>` targets that exact module; `reporting_overrides`
   targets reporting. Strip only the terminal suffix.
4. Apply entries in request document order. Deep-merge objects by exact key;
   replace arrays as whole arrays; replace explicit scalars, strings, Booleans,
   and null only at the exact path.
5. Reject unknown targets, inferred aliases, key renames, array concatenation,
   positional patches, incompatible types, and type coercion.
6. Freeze the effective contract and use it consistently for all cohorts,
   folds, random draws, fits, summaries, and decisions.

## Release And Cohort Rules

Filter each source independently by the effective entity scope, years,
measures/fields, release status, value type, source type, and quality predicates.
Select one publication record per declared entity-time-measure key using the
request's precedence. When a profile gives precedence, use it exactly:

- State longevity and most county workflows: greatest final revision, latest
  release timestamp, then the specified lowest or greatest record identifier.
- State weighted robustness: greatest revision, latest release timestamp, then
  greatest record identifier.
- County panel: highest final revision, then latest release timestamp.
- Country burden: reconcile labels first, then select final country indicator
  records by highest revision, latest release timestamp, and stable record ID.

Suppressed, invalid, withdrawn, blank, null, or scale-break values are
unavailable and are never zero-filled. Count selected publication rows before
analytic completeness exclusions when the template asks for release counts.
Construct complete-case, balanced, broad, strict dual-source, ML, and panel
cohorts only from the effective nonmissing predicates. Preserve entity-code order
unless the request declares another order.

## Shared Numerical Routines

- OLS: solve in declared column order, with or without intercept exactly as
  registered. Use unrounded fitted objects downstream.
- WLS: with positive weights `w`, set `Xw=sqrt(w)*X` and `yw=sqrt(w)*y`; solve
  `(Xw'Xw)^-1 Xw'yw`.
- HC3: use leverage from `Xw`, weighted residuals `sqrt(w_i)*(y_i-X_i*b)`, and
  the standard HC3 sandwich with `(1-h_i)^2`; test with `n-k` Student-t df.
- CR1 cluster covariance: for ordered clusters `g`, scores
  `s_g=X_g' e_g`; apply the registered finite-sample factor and test with
  `G-1` Student-t df.
- Ridge: center outcome as registered, keep intercept unpenalized, standardize
  predictors from training-only moments, select penalty by pooled validation
  squared errors, breaking ties toward the smaller penalty.
- Elastic net: cold-start each fit. Keep intercept unpenalized. Use declared
  feature order, training-only scaling, coordinate descent, declared tolerance
  and sweep/cycle cap. Do not warm-start across penalties unless the effective
  request explicitly says so.
- PCA: build features in declared variable/time order, standardize columns by
  the registered sample or population SD, eigendecompose the covariance/correlation
  matrix, sort eigenpairs descending, and flip each loading so the earliest
  maximum-absolute loading is positive.
- K-means: use deterministic farthest-first initialization unless overridden.
  First center is the smallest entity ID/code; later centers maximize distance
  to the nearest center, with entity-code tie breaks. Assign ties to lower
  cluster ID; update by arithmetic means until unchanged or the cap is reached.
- Adjusted Rand index: compute from the contingency table using combination
  counts. For aligned agreement, choose the permutation with maximum matches,
  breaking ties lexicographically.
- Conformal intervals: sort calibration residuals/scores, use the finite-sample
  rank declared by the protocol, build inclusive symmetric intervals, and
  aggregate coverage/width by the requested row or group weights.
- Wild bootstrap: maintain one continuous PRNG stream. Record checkpoints only
  after the completed replicate; never reset the stream between batches.

## `PHO_STATE_TRANSPORT_AUDIT_V1`

Use this exact profile for state-level adult-obesity/longevity transport audits.

Release/cohorts:
- Resolve state health and socioeconomic series independently by effective
  final filters. Invalid, suppressed, withdrawn, blank, or null values remain
  unavailable.
- Build core balanced, broad reference-year complete-case, and strict
  dual-source cohorts from the effective required fields. Preserve state-code,
  year, feature, and Census division order.

Delete-cluster fixed effects:
- For each active fit, double-demean modeled variables:
  `z_it - entity_mean - time_mean + grand_mean`.
- Fit OLS without intercept in predictor order.
- Delete one state at a time, recompute all means, and refit from scratch in
  state-code order.
- Jackknife: with `G` delete estimates, `bbar=mean(b_-g)`,
  `SE=sqrt((G-1)/G*sum((b_-g-bbar)^2))`, `b_bc=G*b-(G-1)*bbar`.
  Test `b/SE` two-sided with `G-1` df. Select extrema by coefficient, then code.

Nested leave-one-division-out ridge:
- Hold out each ordered division as the outer fold. Inside outer training, hold
  out each remaining division in order.
- Standardize features with training sample SD (`ddof=1`), center training
  outcome, keep intercept unpenalized, and cycle coefficients in feature order.
- Pool inner validation squared errors by row for RMSE; choose smallest RMSE,
  then smaller penalty. Pool one outer prediction per row for RMSE, MAE, and
  `Q^2=1-SSE/SST`.

PCG32 Webb wild cluster bootstrap:
- Use the fixed-effects double-demeaned matrix. Compute observed CR1 and the
  restricted model without the target coefficient.
- PCG32 uses 64-bit wraparound, multiplier `6364136223846793005`, increment
  `2*stream+1`, and the standard XSH-RR output. Map output modulo six to
  `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`.
- Draw once per state in code order for every replicate, set
  `y*=restricted_fit+restricted_residual*weight`, refit unrestricted, recompute
  CR1, studentize, count absolute exceedances, and report plus-one p-value.
  Use nearest-rank quantiles.

Grouped split conformal ridge:
- For each ordered outer division, test on that division. Among remaining
  divisions, choose calibration by greatest row count then ascending division
  name; train on the rest.
- Fit ridge with fixed penalty and the same scaling/solver as nested ridge.
  Rank `ceil((m+1)*(1-alpha))`, capped at `m`, for the absolute calibration
  residual threshold.

Trajectory PCA/clustering:
- Build variable-major/year feature columns from the core balanced cohort,
  standardize by sample SD, use covariance `Z'Z/(n-1)`, deterministic PCA
  orientation, and deterministic three-means.
- For each omitted year block, rebuild PCA, orientation, initialization, and
  clustering; report ARI and aligned agreement.

Source/year perturbation:
- Use the strict dual-source cohort unchanged.
- Enumerate time subsets by increasing requested subset size and lexicographic
  tuple order. Refit complete double-demeaned models for primary and parallel
  source series with CR1 inference.
- Shift is `abs(b_alt-b)/abs(b)*100`. Same sign requires both nonzero and
  identical sign. Worst subset is greatest unrounded shift, then earlier order.

Decision:
- Complete every module, evaluate the request's six gates on unrounded values,
  count passes, and apply the request's controlled decision mapping.

## `PHO_COUNTY_MEDIATION_TRANSPORT_V1`

Use this exact profile for county poverty/physical-inactivity/adult-obesity
mediation transport audits.

Publication/cohorts:
- Filter county health and socioeconomic rows by effective fields and release
  filters. Select one row per entity-time-measure using the declared priority.
- Construct primary-year, balanced-panel, and ML cohorts from nonmissing health,
  socioeconomic, and geography predicates. Preserve county and state order.

Primary mediation models:
- Build total, path-a, and direct/path-b OLS designs from effective exposure,
  mediator, outcome, covariates, transformations, reference categories, and
  column order. Keep the fitted objects for bootstrap and sensitivity.

Difference GMM mediation:
- Create adjacent-change rows in entity then end-period order using effective
  lag structure and instruments.
- For each equation, `W=(Z'Z)^-1` and
  `beta=(X'Z W Z'X)^-1 X'Z W Z'y`.
- With residual `u`, use clustered sandwich scores `Z_g'u_g`. For the indirect
  effect `theta=a*b`, use
  `Var(theta)=b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)` and Student-t cluster df.
- Compute first-stage partial F from full versus reduced RSS. For delete-state
  diagnostics, rebuild rows and refit from scratch.

Nested state ridge:
- Use feature arrays in exact order. Standardize from training arithmetic means
  and population SD; use unit divisor for zero variance.
- Leave one state out externally and internally. Pool county squared errors for
  inner RMSE. Select by unrounded RMSE then smaller penalty; refit and pool OOF.

Paired state wild bootstrap:
- For each target equation, fit the restricted model with only that target
  removed. Generate synthetic outcomes from restricted fit plus state-weighted
  restricted residuals.
- Use unsigned xorshift32 (`x ^= x<<13`, `x ^= x>>17`, `x ^= x<<5`, mask after
  each operation). Odd state is `+1`, even is `-1`.
- Draw once per state in ascending order per replicate and reuse the same state
  signs across paired equations. Use absolute exceedances with plus-one p,
  nearest-rank order statistics, bootstrap-t inversion, and requested checkpoints.

State-grouped conformal:
- Sort states ascending and assign cyclic partitions by index modulo the
  partition count.
- Test each partition, use the preceding partition as calibration, and train on
  the rest. Reduce calibration residuals to one maximum per state. Rank by
  `ceil((m+1)*coverage)`, capped at `m`.

Partial-R2 sensitivity:
- From unrounded baseline `a`, `b`, `SE_b`, and residual df, compute
  `magnitude=SE_b*sqrt(df*rY*rM/(1-rM))`.
- For each direction, `adjusted_b=b-s*magnitude`,
  `adjusted_indirect=a*adjusted_b`, `adjusted_direct=total-adjusted_indirect`,
  and `proportion=adjusted_indirect/total`.
- Enumerate the full declared R2 surface and compute the equal-strength positive
  tipping root from unrounded inputs.

State trajectory PCA:
- Aggregate balanced-panel measures to state-period means in declared feature
  order. Standardize with sample SD, use covariance `Z'Z/(G-1)`, orient PCA, and
  run deterministic farthest-first Lloyd k-means. Rebuild for leave-period ARI.

Decision:
- Evaluate the six effective support predicates after all modules are complete
  and return the first applicable class in the request's precedence order.

## Country Burden Revision Audit

Use this workflow for the country cross-section/panel burden task.

Reconciliation:
- Load `countries`. Resolve every requested label by exact match against
  `portal_label`, `canonical_name`, or the pipe-separated `alternate_labels`.
  Count aliases when the requested label differs from the canonical name.
- Return unique resolved ISO3 identifiers sorted ascending where the template
  asks for set-like lists.

Revision and anomaly audit:
- Load `revisions` for `domain=COUNTRY` and the requested ISO3, years, and
  indicators/outcome. Applied scale corrections are expected to be reflected in
  later final indicator revisions. Non-applied scale corrections are unresolved
  anomalies and should be reported as `ISO3|YEAR|indicator_id` when they touch
  requested analytical cells.
- Separate applicable `APPLIED` event IDs from non-applied event IDs and sort
  each ascending.

Country indicator matrix:
- Select final country indicator records for requested burden indicators and
  panel outcome over the effective cross-section and panel years.
- For the reference-year PCA matrix, mark raw missing requested cells before
  anomaly exclusions, mark unresolved anomaly cells, then impute after quality
  exclusions. Use indicator-wise means from eligible reference-year countries
  unless the future request gives a different imputation rule.
- Standardize burden indicators across countries. Orient PC1 so larger scores
  mean greater burden; all standard burden indicators in this portal are
  `HIGHER_WORSE`.
- Report retained component count from the template/request rule, PC1 variance
  fraction, and top absolute loadings by descending absolute value with
  indicator-ID tie break.

Clusters:
- Run deterministic k-means for candidate counts requested by the template
  (commonly the range 2 through 5) on retained burden scores. Compute Euclidean
  silhouette; singleton silhouettes are zero. Select the highest unrounded
  silhouette, breaking ties toward smaller `k`.
- For the requested three-segment grouping, label clusters by mean PC1 burden:
  lowest as `LOW_BURDEN`, middle as `MIDDLE_BURDEN`, highest as `HIGH_BURDEN`.
  Return high-burden ISO3 IDs sorted ascending.

Region-adjusted panel model:
- For each eligible country-year, compute PC1 burden using the reference PCA
  orientation and comparable standardized inputs. Exclude unresolved anomaly
  cells and rows without outcome.
- Fit OLS of the requested life-expectancy outcome on PC1 burden plus region
  fixed effects, with a normal intercept and one omitted reference region.
  Report coefficient, standard error, two-sided p-value, R-squared, and `true`
  for region fixed effects.
- Advisory rule: significant adverse gradient (`pc1_coefficient < 0` with
  conventional two-sided significance unless overridden) means
  `PRIORITIZE_HIGH_BURDEN_CLUSTER`; adverse but not significant means
  `MONITOR_GRADIENT`; otherwise `NO_ADVERSE_GRADIENT`.

## `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`

Use this exact profile for reliability-weighted state association audits.

Release/cohorts:
- Resolve state direct health, parallel rollup health, and socioeconomic rows by
  effective filters. Select greatest revision, latest release timestamp, then
  greatest record ID. Never replace direct values silently.
- Keep the selected direct outcome sample size as the fixed positive reliability
  weight, including source-perturbation fits, unless the effective request
  overrides the rule.

Weighted linear algebra:
- Use WLS, HC3, and CR1 as defined above. Region indicators and reference levels
  come only from the future request.

Cluster jackknife:
- Fit the full weighted design, then delete each registered cluster in order and
  refit from scratch. Percent change is `100*abs((b_delete-b)/b)`.
- Bias correction uses `b_bc=G*b-(G-1)*mean(delete)`. Test `b_bc/SE_jk` with
  `G-1` df. Most influential cluster is greatest unrounded percent change, then
  earlier cluster order.

Nested weighted elastic net:
- Hold out each registered cluster externally and each remaining cluster
  internally. Build raw, transformed, squared, and interaction features in
  declared order.
- Training-only weighted means and weighted population SDs standardize features.
  Center `y` by the training weighted mean. Objective is weighted SSE over
  `2*sum(w)` plus `lambda*(alpha*L1 + (1-alpha)*L2/2)`.
- Cold-start every fit. Coordinate update:
  `rho_j=sum(w*z_j*r_partial)/sum(w)`,
  `b_j=S(rho_j,lambda*alpha)/(1+lambda*(1-alpha))`.
- Pool unweighted validation/test errors by row for RMSE, MAE, and OOF R2.

Xorshift32 cluster bootstrap:
- Studentize full weighted target with CR1. Fit weighted restricted model
  without target, retain untransformed fit/residuals, and generate
  `y*=fit+residual*cluster_sign`.
- Use unsigned xorshift32, draw clusters in registered order, map low bit one to
  `+1` else `-1`, and keep one continuous stream.
- Count `t* >= observed - tolerance` if a tolerance is effective. Quantiles use
  type-seven interpolation on sorted absolute t values.

Grouped conformal:
- Reuse outer elastic-net center predictions. For each held-out cluster, refit
  each other training cluster as calibration using the same algorithm, pool
  absolute residuals, rank by `ceil((m+1)*coverage)`, and report ordered
  diagnostics. Worst coverage ties by earlier cluster order.

Trajectory PCA:
- Build variable/time blocks in declared order and state ASCII order.
  Standardize by sample SD, use covariance `Z'Z/(n-1)`, orient PCA, and cluster
  on retained scores. Handle empty clusters by moving the ASCII-first farthest
  entity from its assigned center, then continue.
- Leave-one-year/block stability rebuilds the entire PCA and clustering pipeline.

Exhaustive source perturbation:
- Resolve alternate outcome source with its own filters. Order paired entities
  by descending absolute alternate-minus-primary difference, tied by code.
- For every bitmask from zero through `2^m-1`, replace entity `j` iff the bit is
  set, keep direct weights/design, refit WLS and HC3, and summarize by popcount.
- Shift is `100*abs((b_mask-b_zero)/b_zero)`. Select maximum shift by unrounded
  shift, then smaller mask.
- Exact Shapley effect for entity `j` is the weighted sum over coalitions not
  containing `j` of `b(S union j)-b(S)`, with factorial weights. Preserve signed
  order and verify the Shapley sum equals all-replacement minus no-replacement.

Decision:
- Evaluate modules in the request's precedence order and return the first
  unsatisfied controlled conclusion, or the all-robust value if none fail.

## `PHO_COUNTY_PANEL_TRANSPORT_V1`

Use this exact profile for county diagnosed-diabetes dynamics panel audits.

Publication/balanced panel:
- Resolve county health and socioeconomic final records independently using the
  effective priority. Values suppressed, invalid, or missing are incomplete.
- Retain only counties complete for all balanced years and valid geography.
  Build adjacent-change rows ordered by county ID then end period. Derive lagged
  levels, changes, indicators, interactions, and source groups in declared order.

Delete-state two-step GMM:
- Residualize outcome, dynamic regressors, and instruments against intercept
  plus effective baseline terms.
- First step uses identity weighting. Build state scores and second-step moment
  covariance, then the registered Moore-Penrose inverse with the relative
  singular-value cutoff.
- Compute second-step coefficients and Hansen J. Refit both steps after each
  state deletion. Bias-correct with `G*theta_full-(G-1)*mean(theta_delete)`.

State-blocked nested elastic net:
- Allocate states to folds by descending retained entity counts, assigning to
  the currently smallest fold, lower fold ID on equality; sort state codes inside
  folds. Repeat allocation for inner folds within outer training.
- Standardize continuous terms by training population moments; leave indicators
  unchanged. Penalize all non-intercept terms. Cold-start intercept at training
  outcome mean.
- Coordinate descent objective is `SSE/(2n)+alpha*(rho*L1 + .5*(1-rho)*L2)`.
  Update intercept by mean residual, then coefficients in declared order with
  soft-thresholding. Select grid by pooled inner RMSE, then smaller alpha, then
  smaller l1 ratio. Refit and pool OOF metrics.

State wild bootstrap:
- Fit full unpenalized OLS and state-cluster CR1 for the target. Fit restricted
  model without target. Use unsigned xorshift32 in ascending state order, odd
  `+1`, even `-1`, plus-one p-value, nearest-rank quantiles, and requested
  checkpoints.

Cross-fold grouped conformal:
- Use nested elastic-net OOF predictions in original analytic row order. For each
  held-out outer fold, calibrate on absolute OOF residuals from all other folds.
  Rank by `ceil((m+1)*coverage)`, cap at `m`, and build inclusive symmetric
  intervals.
- Report fold, state, RUCC-band, and prediction-decile diagnostics. Prediction
  bins are assigned after sorting by prediction and declared identifiers; signed
  gap is prediction mean minus observation mean.

County trajectory PCA/clustering:
- Build variable-major trajectories in declared variable and end-period order.
  Standardize by population moments and use covariance `Z'Z/n`.
- For each candidate `k`, run deterministic farthest-first k-means; compute
  Euclidean silhouette with singleton zero. Select highest unrounded mean
  silhouette, then smaller `k`.
- For each state deletion, rebuild the trajectory pipeline at selected `k` and
  compare retained labels with ARI. Report median and minimum ARI from unrounded
  values.

Source-group perturbation:
- For each declared source group and outer fold, remove exactly that group's
  terms and reuse the full-model selected hyperparameters for that fold without
  retuning.
- Apply the same preprocessing and solver, record outer RMSEs, pool squared
  errors, subtract the full-model OOF RMSE for deterioration, count worse folds,
  and rank groups by decreasing unrounded deterioration with declared-order ties.

Decision:
- Complete all six modules. Evaluate gates on unrounded values and apply the
  request's controlled precedence exactly.
