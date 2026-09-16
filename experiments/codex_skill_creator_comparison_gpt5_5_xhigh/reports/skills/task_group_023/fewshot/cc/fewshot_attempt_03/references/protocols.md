# Public Health Observatory Protocol Reference

This reference captures reusable method semantics only. It must not be used as a source of solved values. Bind all entities, fields, dates, sources, seeds, grids, cutoffs, labels, output names, and business predicates from the effective future request.

## Portal Datasets

Typical read-only endpoints:

- `GET /catalog`
- `GET /geographies/states`
- `GET /geographies/counties`
- `GET /geographies/countries`
- `GET /data/state-health`
- `GET /data/state-socioeconomic`
- `GET /data/county-health`
- `GET /data/county-socioeconomic`
- `GET /data/country-indicators`
- `GET /data/revisions`
- `GET /methodology`
- `GET /download?dataset=<dataset>&format=csv`

Observed table families:

- `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`.
- `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, population and coordinates.
- `countries`: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`.
- `state_health`: publication rows with `observation_id`, state, year, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, suppression/quality flags, `released_at`.
- `state_socioeconomic`: state-year release rows with socioeconomic fields, `record_id`, `revision`, quality and release metadata.
- `county_health`: county-year health publication rows with `observation_id`, county/state/region, `measure_id`, `value_type`, `release_status`, `revision`, `value`, CI, population, suppression/quality flags, `released_at`.
- `county_socioeconomic`: county-year socioeconomic releases with `record_id`, county/state/region, fields, population, quality and release metadata.
- `country_indicators`: country-year-indicator rows with `observation_id`, `country_label`, `iso3`, `indicator_id`, `release_status`, `revision`, `value`, `unit`, `quality_flag`, `released_at`.
- `revisions`: `revision_event_id`, `domain`, `entity_id`, `field_id`, `effective_year`, old/new values, `status`, `issued_at`, reason and note.

## Effective Request And Overrides

For exact protocol profiles:

1. Verify the `protocol_id` exactly. Similar titles or family identifiers do not activate a profile.
2. Start from the matching profile and its defaults.
3. A direct root key updates the canonical root key with the identical name. Inside a named section/module, a direct child key updates only the identical child path.
4. A root key named `<section>_overrides` targets canonical `<section>`. `module_overrides.<module_name>` targets that exact module. `reporting_overrides` targets reporting.
5. Merge objects recursively by exact key. Replace arrays whole. Replace scalar/string/Boolean/null values only at their exact paths.
6. Reject unknown targets, incompatible types, inferred aliases, renamed keys, array concatenation, and positional patches.
7. Freeze the effective contract before evidence access, folding, fitting, random draws, aggregation, or decisions.

## Shared Statistical Primitives

- **OLS/WLS**: keep columns in declared order; keep intercept unpenalized when present. For WLS use `sqrt(weight)` transformed design/outcome.
- **HC3**: compute leverage from the weighted design and use `e_i^2/(1-h_i)^2`.
- **CR1**: cluster scores are design transpose times residual by cluster. Apply the finite-sample factor declared by the protocol, typically `G/(G-1) * (n-1)/(n-k)`.
- **Two-way fixed effects**: double-demean active variables by entity and time, add the active grand mean, then fit without intercept.
- **Ridge**: standardize using training-only moments, center training outcome, leave intercept unpenalized, choose the smallest pooled validation RMSE with smaller penalty as tie-breaker unless overridden.
- **Elastic net**: cold-start each fold/penalty; cyclic coordinate descent; pool row errors for validation RMSE; tie-break in declared grid order or explicit smaller-penalty rules.
- **Bootstrap**: restricted-null synthetic outcomes use restricted fitted values plus cluster-weighted residuals. Maintain one continuous PRNG stream. Record checkpoints after completed replicates.
- **Conformal**: use sorted absolute residuals, the declared finite-sample rank, inclusive symmetric intervals, and row-weighted aggregation unless a protocol specifies state maxima.
- **PCA**: build columns in declared order, standardize with the active sample, eigendecompose covariance, sort descending, orient by earliest maximum-absolute loading positive, score with oriented loadings.
- **K-means**: use deterministic farthest-first initialization and protocol tie-breakers. Rebuild from scratch for every stability refit.
- **Adjusted Rand index**: compute from contingency counts; for aligned agreement, choose the label permutation with maximum matches and the protocol's lexicographic tie-breaker.
- **Controlled decisions**: compute every module first, evaluate gates on unrounded values, then apply the request's precedence/classification mapping.

## PHO_STATE_TRANSPORT_AUDIT_V1

Use only for exact `protocol_id: PHO_STATE_TRANSPORT_AUDIT_V1`.

Module order:

1. `release_resolution_and_cohorts`
2. `delete_cluster_fixed_effects`
3. `nested_ridge_division_cv`
4. `wild_cluster_bootstrap`
5. `grouped_split_conformal`
6. `trajectory_pca_clustering`
7. `source_year_perturbation`
8. `controlled_decision`

Reusable method details:

- Resolve final releases by effective status, source, value type, validity, and geography bindings. Select greatest revision, latest release timestamp, then the protocol-specified record-id tie-breaker. Count selected publications before analytic exclusions when requested.
- Join independently resolved series by stable entity and time keys. Construct complete/balanced/broad/dual-source cohorts from effective required fields. Preserve entity-code, time, feature, and group order.
- Fixed-effects module: double-demean each modeled variable in each active refit. Delete one whole state at a time and recompute all means. Jackknife `SE=sqrt((G-1)/G*sum((b_-g-bbar)^2))`; bias correction `G*b-(G-1)*bbar`; test `b/SE` with two-sided Student t on `G-1` df. Extremes tie by coefficient then entity code.
- Nested ridge by division: outer folds hold out one census division; inner folds hold out one remaining division. Use training-only feature means and sample SD with ddof one. Coordinate-descent ridge minimizes mean squared error plus `lambda * sum(beta^2)` with an unpenalized intercept.
- PCG32 Webb bootstrap: implement 64-bit PCG32 with stream increment `2*stream+1`, map output modulo six to Webb weights in declared order, draw clusters in entity-code order, and use plus-one absolute t exceedance p-values plus nearest-rank quantiles.
- Grouped split conformal: for each ordered outer group, choose calibration among remaining groups by greatest row count then ascending group name. Rank is `min(m, ceil((m+1)*(1-alpha)))`.
- Trajectory PCA/clustering: build variable-major/time feature blocks, use Jacobi/eigendecomposition semantics equivalent to covariance PCA, farthest-first three-means, canonicalize final ids by centroid coordinates, and compute leave-year-out ARI/agreement in declared year order.
- Source-year perturbation: enumerate requested time subsets by increasing size then lexicographic tuple order. Keep strict analytic set unchanged. Refit primary and parallel fixed-effects models, compute CR1 p-values, percent shifts, same-sign summary, median shift, and worst subset by unrounded shift then subset order.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Use only for exact `protocol_id: PHO_COUNTY_MEDIATION_TRANSPORT_V1`.

Module order:

1. `publication_and_linked_cohorts`
2. `primary_mediation_models`
3. `difference_gmm_mediation`
4. `nested_state_ridge`
5. `paired_state_wild_bootstrap`
6. `state_grouped_conformal`
7. `partial_r2_sensitivity`
8. `state_trajectory_pca_clustering`
9. `controlled_precedence`

Reusable method details:

- Filter county health and socioeconomic sources by effective fields; select one record per entity-time-measure key using the declared ordered release priority.
- Build primary, balanced-panel, and machine-learning cohorts from the request's completeness predicates. Treat suppressed or null selected health records as incomplete, not zero.
- Create adjacent-change GMM rows in entity then end-period order. For each equation use `W=(Z'Z)^-1` and `beta=(X' Z W Z' X)^-1 X' Z W Z' y`. Use state-cluster sandwich scores and cross-equation scores for indirect-effect delta inference.
- First-stage partial F comes from full versus reduced residual sums of squares using effective instrument counts.
- Delete-state diagnostics rebuild rows and refit affected equations from scratch in state order.
- Nested state ridge uses exact base and augmented feature arrays. Standardize from training arithmetic means and population SD, with unit divisor for zero variance. Fit unpenalized intercept ridge by SSE plus lambda squared-norm penalty. Pool county squared errors before RMSE. Tie-break to smaller penalty.
- Paired state wild bootstrap uses unsigned xorshift32 with shifts 13,17,5; odd state maps to +1 and even to -1. Draw once per state in ascending order per replicate and reuse signs across paired equations. Use plus-one absolute exceedance p-values and nearest-rank order statistics.
- State grouped conformal indexes states in ascending order, assigns cyclic partitions by index modulo partition count, uses the preceding calibration partition, reduces calibration residuals to one maximum per calibration state, and ranks state maxima by requested coverage.
- Partial-R2 sensitivity uses unrounded baseline path-a, path-b, path-b SE, and residual df. For each mediator/outcome R2 pair and direction, adjust path-b, indirect, direct, and proportion in declared order. Compute the equal-strength positive tipping root from unrounded values.
- State trajectory PCA clusters state-period means of requested measures; orient loadings, use deterministic farthest-first k-means, and compute leave-period ARI after rebuilding the pipeline.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Use only for exact `protocol_id: PHO_STATE_ROBUSTNESS_TRANSPORT_V1`.

Module order:

1. `release_and_cohort`
2. `common_weighted_linear_algebra`
3. `cluster_jackknife`
4. `nested_elastic_net`
5. `wild_cluster_bootstrap`
6. `grouped_conformal`
7. `trajectory_pca_clustering`
8. `exhaustive_source_perturbation`
9. `controlled_decision`

Reusable method details:

- Resolve state records by effective filters and greatest revision/latest release/protocol record-id tie-breaker. Suppressed, invalid, blank, or null values are unavailable. Keep the selected direct outcome sample size as fixed positive reliability weight unless overridden.
- WLS uses square-root weights. HC3 and CR1 follow the shared formulas with the weighted design and residuals.
- Cluster jackknife deletes each registered census division in order. Percent change is `100*abs((b_delete-b_full)/b_full)`. Bias-correct and test `b_BC/SE_JK` with `G-1` df. Choose most influential by greatest unrounded percent change then earlier cluster order.
- Nested weighted elastic net holds out each registered cluster as outer fold and each remaining cluster as ordered inner fold. Feature construction follows raw, transformed, squared, and interaction order. Weighted standardization uses training weighted population SD. Objective is weighted squared error over total weight plus elastic-net penalty. Cold-start every penalty/fold.
- Weighted bootstrap uses restricted-null xorshift32 signs over registered clusters. Refit full WLS, recompute cluster CR1, count `t* >= t_observed - delta` if a tolerance is declared, and use type-seven quantiles where specified.
- Grouped conformal reuses outer predictions and selected penalties. For each held-out cluster, build calibration residuals by refitting on all other training clusters. Rank by nominal coverage and report ordered cluster diagnostics.
- Trajectory PCA/clustering uses declared variable/time blocks, ASCII entity order, sample SDs, farthest-first k-means over leading scores, empty-cluster handling when specified, and leave-year ARI with aligned assignment changes.
- Exhaustive source perturbation resolves alternate outcomes, orders paired entities by descending absolute alternate-primary difference then code, enumerates all replacement masks, refits WLS/HC3 with fixed direct reliability weights, summarizes by popcount, selects maximum unrounded shift by smaller mask, and computes exact signed Shapley effects.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Use only for exact `protocol_id: PHO_COUNTY_PANEL_TRANSPORT_V1`.

Module order:

1. `publication_balanced_panel`
2. `delete_state_two_step_gmm`
3. `state_blocked_nested_elastic_net`
4. `state_wild_cluster_bootstrap_t`
5. `cross_fold_grouped_conformal`
6. `county_trajectory_pca_clustering`
7. `source_group_perturbation`
8. `controlled_precedence`

Reusable method details:

- Resolve county health and socioeconomic final records independently. Retain counties complete across every balanced period with valid geography attributes. Create adjacent-change rows ordered by entity id then end period; derive lagged levels, changes, indicators, and interactions in declared order.
- Delete-state two-step GMM residualizes outcome, dynamic regressors, and instruments against intercept plus baseline terms. First-step moments use identity weight; second-step weight is the Moore-Penrose inverse of state score covariance using the registered singular-value cutoff. Hansen J is `n*g(theta)'Wg(theta)`. Refit both steps for each state deletion and compute bias-corrected coefficients.
- State-blocked nested elastic net allocates states by descending retained-entity counts to the smallest fold, lower fold id on equality; sort states within folds and repeat inside each outer-training set. Standardize continuous columns from training population moments; indicators unchanged; intercept unpenalized. Grid selection pools inner squared errors, then tie-breaks by smaller alpha and smaller l1 ratio.
- Wild cluster bootstrap fits unpenalized OLS and state CR1 for the target, restricted model without the target, then xorshift32 signs over states in ascending order. Use absolute-tail plus-one p-values and nearest-rank quantiles.
- Cross-fold grouped conformal uses outer OOF predictions. For each held-out fold, calibrate on absolute residuals from all other folds, rank by declared coverage, and report fold, state, rurality-band, and prediction-bin diagnostics. Prediction bins are assigned after sorting by prediction and declared identifiers.
- County trajectory PCA builds variable-major entity trajectories over declared end years, uses population-moment standardization and covariance `Z'Z/n`, evaluates candidate k by deterministic k-means and Euclidean silhouette, selects largest unrounded mean silhouette then smaller k, and computes delete-state ARIs after rebuilding the full pipeline.
- Source-group perturbation removes one declared source group at a time, reuses each fold's full-model selected hyperparameters without retuning, refits with remaining terms, pools RMSE, subtracts the full-model OOF RMSE for deterioration, counts worse folds, and ranks by decreasing unrounded deterioration then declared group order.

## Country Burden Revision Audits Without A Protocol ID

When the request is a country burden/revision audit rather than an exact PHO protocol:

- Reconcile requested labels against `countries.canonical_name`, `portal_label`, and `alternate_labels`; produce unique ISO3 identifiers in the template's requested order or sorted order.
- Resolve country indicators by requested year(s), indicator ids, final releases, revision priority, and quality flags.
- Use `/data/revisions` to distinguish applicable `APPLIED` revision events from non-applied statuses. Pending or withdrawn notices do not authorize replacement.
- Treat unresolved scale-break/anomaly cells as unavailable for modeling. Count raw missing cells before anomaly exclusions and count imputed cells after exclusions if the task requests imputation.
- For burden PCA, align indicators by requested order, orient PC1 so higher burden indicators have the requested burden direction, report top absolute loadings with the template tie-breaker, and keep all PCA rows traceable to stable ISO3 identifiers.
- For country clustering, evaluate requested or candidate k values with deterministic k-means and silhouette; label ordered burden segments by PC1/centroid burden.
- For panel association, build country-year rows over the requested period, include requested fixed effects, and report coefficient, standard error, p-value, and R-squared using unrounded computations.
- Select the advisory only through the requested controlled rule.
