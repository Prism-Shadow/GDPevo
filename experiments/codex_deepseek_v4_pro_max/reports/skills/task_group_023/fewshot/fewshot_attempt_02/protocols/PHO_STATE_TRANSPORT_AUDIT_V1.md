 # PHO_STATE_TRANSPORT_AUDIT_V1

 State-level six-module algorithmic transportability audit for an
 exposure-outcome-longevity signal across the 50 states plus DC.

 ## Module execution order

 1. `release_resolution_and_cohorts`
 2. `delete_cluster_fixed_effects`
 3. `nested_ridge_division_cv`
 4. `wild_cluster_bootstrap`
 5. `grouped_split_conformal`
 6. `trajectory_pca_clustering`
 7. `source_year_perturbation`
 8. `controlled_decision`

 ## Module methods

 ### release_resolution_and_cohorts

 Filter each requested publication key by the effective status, source, value
 type, validity, and geography bindings.  Select greatest revision, then latest
 release timestamp, then lowest record identifier.  Count selected publications
 before analytic completeness exclusions when requested; suppressed, invalid,
 withdrawn, blank, or null analytic values remain unavailable and are never
 zero-filled.

 Join independently resolved series by the effective stable entity and time
 keys.  Construct each complete, balanced, broad, or dual-source analytic set
 from its effective required fields; preserve entity-code then time order, and
 preserve every declared feature and group order.

 ### delete_cluster_fixed_effects

 **Transform and fit:** On every active refit transform each modeled variable as
 `z_it` minus its active entity mean minus its active time mean plus its active
 grand mean, then solve OLS without an intercept in declared predictor order.  A
 deletion removes the whole cluster, recomputes every mean, and refits from
 scratch in entity-code order.

 **Jackknife:** For G delete estimates `b_-g` and mean `bbar`,
 `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))` and
 `b_BC = G*b - (G-1)*bbar`.  The registered test uses `b / SE_JK` with
 two-sided Student-t and G-1 degrees of freedom.  Select extrema by coefficient,
 then entity code.

 ### nested_ridge_division_cv

 **Folds and scaling:** Hold out one ordered group per outer fold; within each
 outer training set hold out every remaining group once in the same order.  For
 every fit, subtract training-only feature means and divide by training sample
 SD with ddof one, then apply those moments to validation or test rows.

 **Solver:** Center the training outcome, keep the intercept unpenalized,
 initialize coefficients to zero, and cycle in declared feature order for
 objective `mean((y - a - Xb)^2) + lambda * sum_j(b_j^2)`.  Update
 `b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n*lambda)`, where `r` excludes
 feature `j`.  Stop after a full sweep when max coefficient change is below the
 effective tolerance.

 Select the smallest unrounded inner RMSE, breaking ties toward the smaller
 penalty, then refit on all outer-training rows.  Pool squared errors before
 RMSE for outer and pooled metrics.

 ### wild_cluster_bootstrap

 **Method:** PCG32 Webb wild cluster bootstrap-t.

 Fit the full model, compute the observed CR1 t-statistic.  Fit the restricted
 null model and generate synthetic outcomes using restricted fitted values plus
 cluster-weighted restricted residuals multiplied by Webb six-point weights.

 Draw weights with the declared seed and stream; record the t-statistic for each
 replicate.  Count exceedances in declared batches.  Compute plus-one p-value
 as `(exceedance_n + 1) / (replicates + 1)` and bootstrap coefficient mean/SD.
 Report quantiles at the declared probability vector.

 ### grouped_split_conformal

 Use the declared fixed-lambda ridge fit on proper-training splits.  Within each
 census-division fold, sort absolute calibration residuals and compute the
 threshold `qhat = residual[ceil((n_cal+1) * (1-alpha))]`.  Apply to test rows
 and report per-fold and aggregate coverage, mean width, and MAE.

 ### trajectory_pca_clustering

 Build the trajectory feature matrix from declared within-year feature blocks,
 run registered-covariance PCA, initialize k-means centroids from the three
 declared initial-centroid states (using their PC scores), run Lloyd's algorithm
 deterministically to convergence (ties to lower cluster id).

 For leave-year-out stability: omit all features from one year, re-run PCA and
 k-means, compute adjusted Rand index and aligned agreement against the
 full-year labels.  Repeat for every declared leave-year.

 ### source_year_perturbation

 For each combination of declared year-subset sizes, fit the full fixed-effects
 model using both the primary and parallel exposure series.  Compute both
 coefficient vectors, CR1 p-values, and the absolute percent shift between
 primary and parallel coefficients for every subset.

 Report same-sign subset fraction, median/max absolute percent shift, and the
 worst-shift subset.

 ### controlled_decision

 Evaluate all six robustness gates.  The primary classification requires all
 six gates to pass.  Classify according to the effective three-tier rule.

 ## Default robustness gates (overrideable)

 | Gate | Rule |
 |---|---|
 | `delete_cluster_fe` | Full exposure coefficient is negative AND jackknife p-value <= 0.05 |
 | `nested_ridge` | Pooled Q-squared >= 0.85 AND pooled RMSE <= 0.75 |
 | `wild_cluster_bootstrap` | Bootstrap p-value <= 0.05 |
 | `grouped_split_conformal` | Aggregate coverage >= 0.80 AND aggregate mean width <= 3.25 |
 | `trajectory_stability` | Minimum leave-year-out ARI >= 0.75 AND first-two-component cumulative explained ratio >= 0.90 |
 | `source_year_stability` | Same-sign subset fraction >= 0.75 AND median absolute percent shift <= 50 |

 ## Default decision tiers (overrideable)

 | Classification | Condition |
 |---|---|
 | `PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL` | All six gates pass |
 | `ASSOCIATED_LONGEVITY_SIGNAL_WITH_LIMITED_TRANSPORTABILITY` | At least four gates pass but primary rule does not |
 | `NO_TRANSPORTABLE_LONGEVITY_SIGNAL` | All remaining cases |
