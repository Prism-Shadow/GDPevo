 # PHO_STATE_ROBUSTNESS_TRANSPORT_V1

 State-level reliability-weighted six-module robustness transport audit with
 cluster-based diagnostics.

 ## Module execution order

 1. `release_and_cohort`
 2. `common_weighted_linear_algebra`
 3. `cluster_jackknife`
 4. `nested_elastic_net`
 5. `wild_cluster_bootstrap`
 6. `grouped_conformal`
 7. `trajectory_pca_clustering`
 8. `exhaustive_source_perturbation`
 9. `controlled_decision`

 ## Module methods

 ### release_and_cohort

 Filter each publication key by effective status, source, value type, validity,
 and entity bindings; select greatest revision, latest release timestamp, then
 greatest record id.  Suppressed, invalid, blank, or null values are unavailable
 and never zero-filled.

 Join resolved series by stable entity-time keys and apply effective
 completeness fields.  Unless overridden, keep the selected direct
 outcome-record sample size as fixed positive reliability weight even when
 replacing outcome source.  Preserve declared entity, time, feature, and
 cluster order.

 ### common_weighted_linear_algebra

 **WLS:** For design X, outcome y, and positive weights w,
 `Xw = diag(sqrt(w)) * X`, `yw = diag(sqrt(w)) * y`, then
 `b = (Xw' Xw)^-1 Xw' yw` in declared column order.

 **HC3:** With `h_i = diag(Xw (Xw' Xw)^-1 Xw')` and
 `ew_i = sqrt(w_i)(y_i - X_i b)`,
 `V_HC3 = (Xw' Xw)^-1 Xw' diag(ew_i^2 / (1-h_i)^2) Xw (Xw' Xw)^-1`.
 Use two-sided Student-t with n-k residual degrees of freedom.

 **CR1:** For ordered clusters g and `s_g = Xw_g' ew_g`,
 `V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw' Xw)^-1 * sum_g(s_g s_g') * (Xw' Xw)^-1`.
 Use two-sided Student-t with G-1 degrees of freedom.

 ### cluster_jackknife

 Fit the full weighted design, then delete every registered cluster in order and
 refit the unchanged design from scratch.  For target coefficient b and delete
 value `b_-g`, percent change is `100 * abs((b_-g - b) / b)`; choose greatest
 unrounded change, tied by earlier cluster order.

 For G delete estimates and mean `bbar`,
 `b_BC = G*b - (G-1)*bbar` and
 `SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))`.
 Test `b_BC / SE_JK` two-sided with G-1 Student-t degrees of freedom.

 ### nested_elastic_net

 **Folds and features:** Hold out each registered cluster as an outer fold and
 each remaining cluster as an ordered inner fold.  Build effective raw,
 transformed, squared, and interaction features in declared order.

 **Scaling and objective:** Inside every fit compute training-only weighted mean
 and weighted population SD `sigma_j = sqrt(sum_i w_i*(x_ij-mu_j)^2 / sum_i w_i)`,
 standardize training and prediction rows with them, and center y by its
 training weighted mean without scaling y.  Minimize
 `sum_i w_i*(y_i-Z_i*b)^2 / (2*sum_i w_i) + lambda * [alpha*sum_j|b_j| + (1-alpha)*sum_j(b_j^2)/2]`.

 **Solver:** Cold-start b=0 for every penalty and fold; never warm-start.
 In cyclic feature order set
 `rho_j = sum_i w_i*Z_ij*(y_i - sum_{l!=j} Z_il*b_l) / sum_i w_i` and
 `b_j = S(rho_j, lambda*alpha) / (1 + lambda*(1-alpha))`,
 with `S(a,t) = sign(a)*max(|a|-t, 0)`.  Stop after a complete cycle when max
 coefficient change is below the effective tolerance or at the sweep cap.
 Select by smallest inner RMSE, then smaller alpha, then numerically smaller
 chosen penalty.

 ### wild_cluster_bootstrap

 Use XORSHIFT32 restricted-null wild cluster bootstrap-t.

 Fit the full weighted model and compute the observed absolute HC3 t-statistic.
 Fit the restricted model without the target term, generate synthetic outcomes
 from restricted fitted values plus cluster-weighted restricted residuals
 multiplied by Rademacher weights.

 Record checkpoints at declared replicate numbers (PRNG state and absolute
 cluster t).  Count exceedances and compute plus-one p-value.  Report
 bootstrap-t quantiles at the declared probability vector.

 ### grouped_conformal

 Use the nested elastic-net outer OOF predictions as source.  Within each
 division, sort absolute calibration residuals and compute the threshold at
 nearest rank `ceil((n_cal+1) * (1-nominal_coverage))`.  Apply to held-out rows
 and report per-division and pooled coverage, mean interval width, and worst
 division.

 ### trajectory_pca_clustering

 Build the trajectory feature matrix from declared within-year feature blocks,
 run registered-covariance PCA, retain the declared number of components,
 initialize centroids from declared initial states, and run deterministic
 Lloyd's algorithm.

 For leave-one-year-out stability: omit one year's feature block, re-run PCA
 and k-means, and compute adjusted Rand index.  Report all five ARI values and
 the minimum.

 ### exhaustive_source_perturbation

 Identify all entities where both the baseline direct source and replacement
 (e.g., county rollup) source resolve as eligible.  Enumerate all 2^M
 combinations of replacing the baseline with the replacement for each entity.

 For each scenario refit the full weighted model and record the target
 coefficient and HC3 p-value.  Report by-replacement-count strata, the
 maximum-shift scenario, and exact Shapley effects computed by weighted marginal
 contributions over the full coalition lattice.

 ## Default decision rule (overrideable)

 | Flag | Rule |
 |---|---|
 | `cluster_jackknife_supported` | Bias-corrected coefficient is positive, jackknife p < 0.05, AND max delete-cluster percent change <= 25 |
 | `nested_prediction_stable` | Pooled outer OOF R-squared >= 0.55 |
 | `wild_bootstrap_supported` | Plus-one p-value <= 0.05 |
 | `grouped_conformal_supported` | Pooled coverage >= 0.85 |
 | `trajectory_stable` | Minimum leave-one-year ARI >= 0.55 |
 | `source_exhaustive_stable` | Every scenario is stable AND max absolute percent shift <= 25 |

 ## Default decision tiers (overrideable)

 | Classification | Condition |
 |---|---|
 | `ROBUST_ACROSS_REGISTERED_MODULES` | All six flags pass |
 | `NOT_ROBUST_AT_<FIRST_FAILED_MODULE>` | First failed module in precedence order |
