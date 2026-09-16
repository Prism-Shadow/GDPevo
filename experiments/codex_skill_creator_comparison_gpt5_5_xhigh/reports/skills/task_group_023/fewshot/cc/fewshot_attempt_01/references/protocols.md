# PHO Audit Protocol Notes

These notes capture reusable method semantics only. Bind all entities, measures,
years, grids, seeds, thresholds, labels, and output field names from the current
task's `analysis_request.json` and `answer_template.json`.

## Override Resolution

For exact registered protocols, resolve one effective request before evidence
access or computation.

- Direct root keys target identical canonical root keys.
- A root `<section>_overrides` targets canonical `<section>`.
- `module_overrides.<module_name>` targets the exact named module.
- Objects deep-merge by exact key; arrays replace whole arrays; explicit scalar,
  string, boolean, or null values replace only their exact path.
- Reject inferred aliases, type coercion, positional array patches, and unknown
  targets.

## Release And Cohort Rules

- Resolve health and socioeconomic releases independently.
- Count selected publication rows before analytic exclusions when requested.
- Treat suppressed records, invalid quality flags, withdrawn records, blank
  strings, and null analytic values as unavailable.
- Use stable geography identifiers for joins: state abbreviation, county FIPS, or
  ISO3 as applicable.
- Preserve entity ASCII order unless the request declares a different registered
  order.

Identifier tie direction is protocol-specific. `PHO_STATE_TRANSPORT_AUDIT_V1`
uses lowest record identifier after greatest revision and latest release.
`PHO_STATE_ROBUSTNESS_TRANSPORT_V1` uses greatest record identifier after
greatest revision and latest release. Other requests should be read literally;
when only a priority list is given, document the deterministic direction used.

## PHO_STATE_TRANSPORT_AUDIT_V1

Route only on exact `protocol_id`.

Modules:

- `release_resolution_and_cohorts`: filter by effective final status, source,
  value type, validity, and geography. Build core balanced, broad reference, and
  strict dual-source cohorts from the effective completeness fields.
- `delete_cluster_fixed_effects`: double-demean outcome and predictors by state
  and year. Fit OLS without intercept. For every state deletion, recompute all
  means and refit. Jackknife uses delete estimates, `sqrt((G-1)/G * sum((b_g -
  mean_b)^2))`, bias correction `G*b_full - (G-1)*mean_b`, and a two-sided
  Student-t test with `G - 1` degrees of freedom.
- `nested_ridge_division_cv`: leave one census division out. Within each outer
  training set, leave one remaining division out for inner validation. Use
  training-only sample-SD scaling, an unpenalized centered intercept, cyclic
  coordinate descent, row-pooled inner RMSE, and tie toward smaller lambda.
- `wild_cluster_bootstrap`: use the same fixed-effect transformed design, CR1
  cluster inference, a restricted model without the target coefficient, PCG32
  with the requested seed/stream, Webb six-point weights, plus-one p-values, and
  nearest-rank requested quantiles.
- `grouped_split_conformal`: for each outer division, choose calibration from
  remaining divisions by greatest row count then ascending name. Fit ridge on
  proper training rows. Use nearest-rank absolute calibration residuals and
  aggregate coverage/width by held-out row counts.
- `trajectory_pca_clustering`: build variable-major/year features, sample-SD
  standardize, covariance PCA, deterministic farthest-first k-means, canonical
  cluster ids, and leave-year-out adjusted Rand stability.
- `source_year_perturbation`: keep the strict cohort fixed; enumerate year
  subsets by requested sizes and lexicographic order; refit primary and parallel
  fixed-effect models with CR1 inference; summarize same-sign and percent-shift
  stability.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Route only on exact `protocol_id`.

Modules:

- `publication_and_linked_cohorts`: select one record per county-year-measure
  key using the request's release priority. Basic completeness requires selected
  health values, required socioeconomic fields, and valid RUCC. Build primary,
  balanced-panel, and machine-learning cohorts from the effective predicates.
- `primary_mediation_models`: construct total-effect, path-a, and direct/path-b
  OLS designs from the request's exposure, mediator, outcome, covariates,
  transformations, RUCC reference dummies, and column order. Keep unrounded fits
  for bootstrap and sensitivity.
- `difference_gmm_mediation`: create adjacent-change rows in county/end-period
  order. Estimate each equation with `W=(Z'Z)^-1` and `beta=(X' Z W Z' X)^-1 X'
  Z W Z' y`. Use state-cluster sandwich scores; for indirect `a*b`, combine
  variances and covariance by the delta method. Refit every delete-state
  diagnostic from scratch.
- `nested_state_ridge`: leave one state out, then leave one remaining state out
  inside the outer training set. Use feature maps in exact order, training-only
  arithmetic means and population SDs, unpenalized intercept, row-pooled RMSE,
  and tie toward smaller penalty.
- `wild_cluster_bootstrap_t`: fit target-specific restricted-null models for the
  three primary-year OLS equations. Use unsigned xorshift32, paired state signs
  reused across equations, continuous stream, plus-one p-values, nearest-rank
  order statistics, and bootstrap-t intervals.
- `state_grouped_conformal`: assign states cyclically by ascending state index to
  the requested partition count. Use the preceding partition for calibration and
  the rest for proper training. Reduce calibration residuals to one maximum per
  calibration state, then use the requested finite-sample coverage rank.
- `mediation_sensitivity_surface`: from unrounded baseline path-a, path-b,
  path-b SE, and residual df, enumerate every requested R2 pair and bias
  direction. Use the partial-R2 magnitude formula and compute adjusted indirect,
  direct, and proportion values in declared order.
- `trajectory_pca_clustering`: aggregate balanced counties to state-year means,
  standardize by sample SD, use covariance PCA, orient components, deterministic
  k-means, and leave-year-out ARI.
- `controlled_precedence`: evaluate every declared support predicate on
  unrounded values and return the first applicable class in request order.

## Country Burden Revision Audit

Use this route for country requests without a registered protocol profile that
ask for country label reconciliation, revision history, a reference-year burden
PCA, burden clusters, and a region-adjusted life-expectancy panel model.

Expected method:

- Reconcile each requested label to one country using canonical name, portal
  label, and alternate-label lists. Count aliases when the requested label is not
  the canonical name. Return unique ISO3 values sorted when the template asks for
  set-like output.
- Pull `country_indicators`, `countries`, and `revisions`.
- For requested indicators and years, filter to final/current usable records,
  apply APPLIED revision notices, retain non-APPLIED notices only for audit
  reporting, and keep unresolved scale-break/anomaly cells out of analytic use.
- For the reference-year matrix, count raw missing cells first, then anomaly
  cells, then impute excluded/missing requested indicator cells. Use a simple,
  reproducible imputation rule derived from available same-indicator peer values
  unless the request states a stricter rule; report imputed cell count.
- Orient burden indicators so larger PC1 scores mean higher burden. Standardize
  columns, run covariance/correlation PCA consistently, orient PC1 to positive
  burden loadings, and report top absolute loadings with indicator-id tie breaks.
- Fit deterministic k-means for candidate counts 2 through 5, compute average
  Euclidean silhouette with singleton silhouette zero, and pick largest
  unrounded silhouette with smaller `k` as tie break.
- For requested three-segment output, order clusters by mean PC1 burden and map
  to low, middle, and high burden labels.
- For panel modeling, project country-year burden features using the reference
  orientation or a documented full-panel reconstruction, then regress life
  expectancy on PC1 burden plus region fixed effects. Report the PC1 coefficient,
  standard error, p-value, R-squared, and advisory from the request's controlled
  rule.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Route only on exact `protocol_id`.

Modules:

- `release_and_cohort`: select final state records by effective health and
  socioeconomic filters. Use selected direct outcome sample size as the fixed
  reliability weight, including source perturbation fits.
- `common_weighted_linear_algebra`: WLS solves on `sqrt(w) X` and `sqrt(w) y`.
  HC3 uses weighted leverage and residual df `n-k`. CR1 uses ordered cluster
  scores and finite-sample factor `[G/(G-1)] * [(n-1)/(n-k)]`.
- `cluster_jackknife`: fit full WLS, delete each census division in registered
  order, refit unchanged design, compute percent change, jackknife SE,
  bias-corrected coefficient, and t test on the bias-corrected target.
- `nested_elastic_net`: outer and inner folds leave registered divisions out.
  Build declared raw, log, square, and interaction features. Standardize with
  training weighted population moments, center outcome by weighted mean, use
  cold-start cyclic coordinate descent, row-pooled inner RMSE, and tie toward
  smaller lambda.
- `wild_cluster_bootstrap`: fit weighted restricted-null model without target.
  Use unsigned xorshift32, one continuous stream, division-order signs, absolute
  studentized targets, plus-one p-values, and type-seven quantiles.
- `grouped_conformal`: reuse outer center predictions and selected penalties.
  For each held-out division, produce calibration residuals by leave-one-other
  division refits, use nearest-rank coverage radius, and pool diagnostics by
  held-out counts.
- `trajectory_pca_clustering`: build declared variable/year blocks, sample-SD
  standardize, orient PCA, cluster on retained scores, handle empty clusters by
  moving the ASCII-first farthest member, and report leave-year-out aligned
  changes plus ARI.
- `exhaustive_source_perturbation`: order replacement-eligible states by
  descending absolute alternate-minus-primary outcome difference, tied by code.
  Enumerate all masks, keep direct reliability weights, refit WLS with HC3,
  summarize popcount strata and maximum shift, then compute exact signed Shapley
  coefficient changes in the registered order.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Route only on exact `protocol_id`.

Modules:

- `publication_balanced_panel`: resolve county health and socioeconomic records,
  require final status, nonsuppressed values, valid RUCC, and complete balanced
  years. Create adjacent-change rows ordered by county then end period.
- `delete_state_two_step_gmm`: residualize outcome, dynamic regressors, and
  instruments against intercept plus baseline terms. First step uses identity
  weighting. Build state scores, compute `S`, use the registered Moore-Penrose
  inverse cutoff for second-step weighting, compute Hansen J, and refit every
  delete-state case. Bias correction uses the delete-state jackknife formula.
- `state_blocked_nested_elastic_net`: allocate states to folds by descending
  retained county counts, assigning to the smallest current fold with lower fold
  id ties. Standardize continuous terms by training population moments, leave
  indicators unchanged, cold-start all candidates, pool inner row errors, and
  select by RMSE then smaller alpha then smaller l1 ratio.
- `state_wild_cluster_bootstrap_t`: fit unpenalized OLS and state-cluster CR1,
  then restricted-null synthetic outcomes with unsigned xorshift32 state signs,
  absolute-tail plus-one p-values, nearest-rank quantiles, and checkpoint states.
- `cross_fold_grouped_conformal`: use outer OOF predictions. For each held-out
  fold, calibrate on all other folds' absolute OOF residuals. Report fold,
  state, RUCC-band, and prediction-decile diagnostics. Prediction deciles are
  assigned after sorting by prediction and declared identifiers.
- `county_trajectory_pca_clustering`: build variable-major county trajectories
  by declared variable/end-year order, population-standardize, use covariance
  `Z'Z/n`, orient loadings, run deterministic farthest-first k-means for every
  candidate k, select by largest mean silhouette then smaller k, and delete each
  state for ARI stability.
- `source_group_perturbation`: for each declared source group and outer fold,
  remove exactly that group's terms and reuse the full-model selected
  hyperparameters without retuning. Pool RMSE, compute deterioration versus the
  full model, count worse folds, and rank by decreasing deterioration with
  declared-order ties.
