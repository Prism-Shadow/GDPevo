 # PHO_COUNTY_PANEL_TRANSPORT_V1

 County-level panel dynamics audit with six-algorithm verification for
 diagnosed-diabetes dynamics models.  Uses balanced county panels with
 change-on-level GMM estimation, nested elastic net, wild cluster bootstrap,
 grouped conformal calibration, trajectory PCA, and source-group perturbation.

 ## Module execution order

 1. `publication_balanced_panel`
 2. `delete_state_two_step_gmm`
 3. `state_blocked_nested_elastic_net`
 4. `state_wild_cluster_bootstrap_t`
 5. `grouped_conformal_calibration`
 6. `trajectory_pca_clustering`
 7. `source_group_perturbation`
 8. `controlled_decision`

 ## Module methods

 ### publication_balanced_panel

 Filter effective county health and socioeconomic sources independently; resolve
 one final record per declared key using effective release priority.  Treat
 selected suppressed, invalid, or missing values as incomplete, never zero;
 retain only entities complete across every effective balanced period with valid
 geography attributes.

 Create adjacent-change rows ordered by entity identifier then end period;
 derive lagged levels, dynamic changes, reference indicators, and interactions
 in declared order.

 ### delete_state_two_step_gmm

 Within every full or delete-state fit, residualize outcome, dynamic regressors,
 and instruments against intercept plus effective baseline terms.

 First-step moments are `g(theta) = Z'(y - D theta) / n` with identity weight.
 Build state scores `s_g = Z_g' u_g` and
 `S = sum_g(s_g s_g') / n`; second-step weight is the registered Moore-Penrose
 inverse of S.

 Compute second-step theta from the weighted linear moments and Hansen
 `J = n * g(theta)' W g(theta)`.  Apply the registered relative singular-value
 cutoff to every pseudoinverse.

 Refit both steps after each state deletion in state order.  With G clusters use
 `theta_bc = G*theta_full - (G-1)*mean(theta_delete)`, and retain maximum
 absolute delete-state shifts.

 ### state_blocked_nested_elastic_net

 Allocate states by descending retained-entity counts, assigning each to the
 currently smallest fold and using lower fold id on equality; sort state codes
 within folds and repeat allocation inside each outer-training set.

 Within each fit standardize declared continuous columns from training population
 moments, leave indicators unchanged, apply training moments to held-out rows,
 and keep the intercept unpenalized.

 Minimize `SSE/(2n) + alpha * (rho * sum|beta_j| + 0.5*(1-rho) * sum(beta_j^2))`.
 Cold-start coefficients at zero and intercept at the training outcome mean.

 In each cyclic sweep update the intercept by mean residual, then
 `beta_j = S(mean(x_j * r_partial), alpha*rho) / (mean(x_j^2) + alpha*(1-rho))`
 in declared coefficient order.  Stop at the registered max-change tolerance or
 sweep cap.

 Traverse the effective grid in declared outer/inner order.  Pool inner squared
 errors before RMSE; select by smallest unrounded RMSE, then smaller alpha, then
 smaller l1 ratio.  Refit outer models and pool OOF metrics.

 ### state_wild_cluster_bootstrap_t

 Fit full unpenalized OLS and state-cluster CR1 for the target.  Fit the
 restricted model without the target and generate synthetic outcomes from
 restricted fitted values plus state-weighted restricted residuals multiplied by
 Rademacher weights.

 Use XORSHIFT32 PRNG with declared seed.  For each declared replicate draw one
 weight vector, refit the full model on the synthetic outcome, and record the
 CR1 t-statistic.  Count absolute tail exceedances.

 Report checkpoint PRNG states and t-values at declared replicate numbers, the
 plus-one p-value, and bootstrap-t quantiles at declared probabilities.

 ### grouped_conformal_calibration

 Use nested elastic-net outer OOF predictions as the source.  For each outer
 fold, sort absolute calibration residuals, compute the threshold at nearest
 rank `ceil((n_cal+1) * (1-nominal_coverage))`, and construct intervals for
 held-out rows.

 Report per-fold diagnostics, per-state coverage, per-RUCC-band coverage,
 per-prediction-decile calibration (prediction mean, observation mean, signed
 gap), overall coverage, and minimum state coverage.

 ### trajectory_pca_clustering

 Build the county-level trajectory feature matrix from declared within-year
 variable blocks across all trajectory end years.  Run PCA, retain declared
 components, and cluster counties with deterministic k-means across the
 candidate cluster count grid.

 Select the best cluster count by average silhouette score.  For delete-state
 stability: remove all counties in one state, re-run PCA and k-means on the
 retained counties, and compute adjusted Rand index.  Report median and minimum
 ARI.

 ### source_group_perturbation

 For each declared ordered source group, remove its terms from the design, reuse
 the full model's selected hyperparameters without retuning, and refit using the
 nested elastic-net outer-fold structure.

 Report per-outer-fold RMSE, pooled RMSE, RMSE deterioration vs. full model
 reference, worse-fold count, and deterioration rank (1 = largest
 deterioration).

 ## Default decision rule (overrideable)

 | Gate | Rule |
 |---|---|
 | Gate 1 | Bias-corrected poverty_change GMM coefficient > 0.04 |
 | Gate 2 | Elastic-net OOF RMSE < 0.85 |
 | Gate 3 | Wild-bootstrap plus-one p-value < 0.06 |
 | Gate 4 | Overall grouped-conformal coverage >= 0.89 |
 | Gate 5 | Median delete-state clustering ARI >= 0.70 |
 | Gate 6 | poverty_dynamics deletion RMSE deterioration >= 0.006 |

 ## Default decision tiers (overrideable)

 | Classification | Condition |
 |---|---|
 | `DEPLOY_DIABETES_DYNAMICS` | All six gates pass |
 | `REVIEW_DIABETES_DYNAMICS` | Four or five gates pass |
 | `RETAIN_LAGGED_DIABETES` | Otherwise |
