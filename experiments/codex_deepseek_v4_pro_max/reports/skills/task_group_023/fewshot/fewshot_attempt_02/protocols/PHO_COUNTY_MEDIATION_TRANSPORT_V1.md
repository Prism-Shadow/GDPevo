 # PHO_COUNTY_MEDIATION_TRANSPORT_V1

 County-level mediation transportability audit examining whether a poverty-to-obesity
 signal through a declared mediator survives instrumented changes, out-of-state
 prediction, clustered resampling, grouped calibration, confounding sensitivity, and
 trajectory stability.

 ## Module execution order

 1. `publication_and_linked_cohorts`
 2. `primary_mediation_models`
 3. `difference_gmm_mediation`
 4. `nested_state_ridge`
 5. `paired_state_wild_bootstrap`  (`wild_cluster_bootstrap_t`)
 6. `state_grouped_conformal`
 7. `mediation_sensitivity_surface`
 8. `trajectory_pca_clustering`
 9. `controlled_conclusion`

 ## Module methods

 ### publication_and_linked_cohorts

 Filter each source by effective request fields; select one record per declared
 entity-time-measure key using the declared ordered release priority.  Count
 selected publications before analytic completeness exclusions when requested;
 suppressed or null selected health records remain publication evidence but are
 incomplete.

 Construct primary, balanced-panel, and machine-learning cohorts from effective
 nonmissing and validity predicates; preserve declared entity and state order.

 ### primary_mediation_models

 Build total-effect, path-a, and direct/path-b OLS designs from effective
 exposure, mediator, outcome, covariates, transformations, references, and
 column order.  Use the unrounded fitted objects as the shared source for
 downstream bootstrap and sensitivity modules.

 ### difference_gmm_mediation

 Create adjacent-change rows in entity then end-period order using the effective
 lag structure and equation bindings.

 For each equation use `W = (Z'Z)^-1` and
 `beta = (X'Z W Z'X)^-1 X'Z W Z'y`.

 With residual `u` and cluster scores `q_g = Z_g' u_g`, use the registered
 finite-sample cluster sandwich; for two equations use the corresponding
 cross-cluster score product.

 For indirect effect `theta = a*b` use
 `Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b)`, and Student-t inference
 with cluster degrees of freedom.

 Compute first-stage partial F from full-versus-reduced residual sums of
 squares using effective instrument counts.

 For every delete-state diagnostic, rebuild rows and refit all affected
 equations from scratch in state order.

 ### nested_state_ridge

 Use effective feature arrays in exact order.  Within every fit, standardize
 from training arithmetic means and population standard deviations, with a unit
 divisor for zero variance; apply those moments to held-out rows.

 Fit ridge with an unpenalized intercept by minimizing training SSE plus lambda
 times the squared non-intercept norm.

 Outer validation leaves one state out; each inner validation leaves one
 remaining state out.  Pool county squared errors before RMSE.

 Select the smallest unrounded inner RMSE, breaking equality toward the smaller
 penalty; refit on all outer-training rows and retain complete aligned grids and
 outer diagnostics.  Aggregate OOF metrics from the single prediction assigned
 to every eligible row.

 ### paired_state_wild_bootstrap

 For each target, fit the restricted model with only that target removed.
 Generate synthetic outcomes from restricted fitted values plus state-weighted
 restricted residuals multiplied by Rademacher weights.

 Use XORSHIFT32 PRNG with the declared seed.  Draw one common weight vector per
 replicate and apply it to all equations.  Refit the full system, record all
 observed and bootstrap t-statistics.

 Compute per-equation plus-one p-value and bootstrap-t quantiles.  Record
 checkpoints at declared replicate numbers.

 ### state_grouped_conformal

 Partition states into declared partition-count folds by descending county
 counts.  Within each fold, use augmented ridge predictions as source.

 Sort absolute calibration residuals, compute `qhat` at nearest rank
 `ceil((n_cal+1)*(1-nominal_coverage))`, and construct intervals for test rows.
 Report per-cycle and per-state coverage and width.

 ### mediation_sensitivity_surface

 From the baseline primary models, extract the path-a coefficient, path-b
 coefficient, path-b standard error, and residual degrees of freedom.

 For each declared `r2_mediator` and `r2_outcome` pair and each bias direction
 (NEGATIVE, POSITIVE), compute the adjusted path-b as
 `baseline_path_b - direction_sign * baseline_path_b_se * sqrt(r2_outcome)` and
 the adjusted indirect as `baseline_path_a * adjusted_path_b`.

 The equal-strength tipping R-squared is the value where the adjusted indirect
 would cross zero, assuming equal R-squared on both mediator and outcome.

 ### trajectory_pca_clustering

 Aggregate county data to state means for each declared within-year variable
 block.  Run PCA on the state-level trajectory matrix, retain declared
 components, and cluster states with deterministic k-means.

 For leave-one-year-out stability: remove one year's feature block, re-run PCA
 and k-means, and compute adjusted Rand index.  Report mean and minimum ARI.

 ## Default controlled conclusion flags (overrideable)

 | Flag | Rule |
 |---|---|
 | `difference_gmm_supported` | Stacked indirect 95% interval excludes zero |
 | `nested_ridge_supported` | Augmented pooled RMSE is lower AND augmented RMSE wins in at least 16 states |
 | `bootstrap_supported` | PATH_A and PATH_B bootstrap p-values are both below 0.05 |
 | `grouped_conformal_calibrated` | Overall coverage >= 0.90 AND at least 24 states have coverage >= 0.80 |
 | `sensitivity_robust` | Every POSITIVE row with both R2 values at most 0.08 preserves nonzero baseline indirect-effect sign |
 | `trajectory_stable` | Mean leave-year-out ARI >= 0.60 AND minimum ARI >= 0.40 |

 ## Default decision tiers (overrideable)

 | Classification | Condition |
 |---|---|
 | `CONSISTENT_OBESITY_MEDIATION_AUDIT` | All six flags pass |
 | `PARTIAL_OBESITY_MEDIATION_AUDIT` | At least four flags pass |
 | `FRAGILE_OBESITY_MEDIATION_AUDIT` | At least two flags pass |
 | `NO_OBESITY_MEDIATION_AUDIT` | Otherwise |
