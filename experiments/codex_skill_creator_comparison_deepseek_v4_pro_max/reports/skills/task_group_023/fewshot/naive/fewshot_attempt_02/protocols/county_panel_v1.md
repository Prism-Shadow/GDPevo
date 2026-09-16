## PHO_COUNTY_PANEL_TRANSPORT_V1

County-level panel dynamics transport audit. Tests whether a West/Northeast
county diagnosed-diabetes dynamics model is reproducible, transportable,
calibrated, and stable, using balanced four-year county panels, delete-state
two-step GMM, state-blocked nested elastic net, wild cluster bootstrap,
cross-fold grouped conformal, county trajectory PCA clustering, and
source-group perturbation.

### Module execution order

1. publication_balanced_panel
2. delete_state_two_step_gmm
3. state_blocked_nested_elastic_net
4. state_wild_cluster_bootstrap_t
5. cross_fold_grouped_conformal
6. county_trajectory_pca_clustering
7. source_group_perturbation
8. controlled_precedence

### 1. Publication and balanced panel

Filter effective county health and socioeconomic sources independently. Resolve
one final record per declared key using effective release priority: highest final
revision, then latest release timestamp.

Treat selected suppressed, invalid, or missing values as incomplete, never zero.
Retain only entities complete across every effective balanced period with valid
geography attributes (RUCC 1-9).

Create adjacent-change rows ordered by entity identifier then end period. Derive
lagged levels, dynamic changes, reference indicators, and interactions in
declared order.

### 2. Delete-state two-step GMM

Within every full or delete-state fit, residualize outcome, dynamic regressors,
and instruments against intercept plus effective baseline terms.

First-step moments: g(theta) = Z'(y - D theta) / n with identity weight W = I.
Build state scores s_g = Z_g' u_g and S = sum_g(s_g s_g') / n. Second-step
weight is the registered Moore-Penrose inverse of S (relative singular-value
cutoff for near-singular matrices).

Compute second-step theta from the weighted linear moments. Hansen J = n *
g(theta)' W g(theta). Apply the registered relative singular-value cutoff to
every pseudoinverse.

Refit both steps after each state deletion in state order. With G clusters:
theta_bc = G * theta_full - (G-1) * mean(theta_delete). Retain maximum absolute
delete-state shifts.

### 3. State-blocked nested elastic net

Allocate states by descending retained-entity counts, assigning each to the
currently smallest fold, using lower fold id on equality. Sort state codes
within folds. Repeat allocation inside each outer-training set for inner folds.

Within each fit, standardize declared continuous columns from training population
moments, leave indicators unchanged, apply training moments to held-out rows.
Keep the intercept unpenalized.

Minimize SSE/(2n) + alpha * (rho * sum|beta_j| + 0.5 * (1-rho) * sum beta_j^2).
Cold-start coefficients at zero and intercept at the training outcome mean.

In each cyclic sweep update the intercept by mean residual, then beta_j =
soft_threshold(mean(x_j * r_partial), alpha * rho) / (mean(x_j^2) + alpha *
(1-rho)) in declared coefficient order. Stop at the registered maximum-change
tolerance or sweep cap.

Traverse the effective grid in declared outer/inner order. Pool inner squared
errors before RMSE. Select by smallest unrounded RMSE, then smaller alpha, then
smaller l1 ratio. Refit outer models and pool OOF metrics.

### 4. State wild cluster bootstrap t

Fit full unpenalized OLS and state-cluster CR1 for the target. Fit the restricted
model without the target and generate synthetic outcomes from restricted fitted
values plus state-weighted restricted residuals.

Use unsigned xorshift32 with shifts 13, 17, 5 and 32-bit masking after each xor.
Maintain one continuous stream, drawing states in ascending order. Odd maps to +1
and even to -1.

Refit the full model and recompute CR1 each replicate. Use absolute-tail
exceedances, plus-one p = (count+1)/(B+1), and nearest-rank order statistics at
effective probabilities.

Record each requested checkpoint after completing its state draws and t
statistic.

### 5. Cross-fold grouped conformal

Use outer OOF predictions in original analytic-row order. For each held-out fold,
calibrate on absolute OOF residuals from all other folds.

With m calibration rows, use rank = min(m, ceil((m+1) * coverage)). Build
symmetric inclusive intervals.

Report fold, state, effective rurality-band, and rank-defined prediction-bin
diagnostics. Assign prediction bins after sorting by prediction and declared
identifiers. Compute signed gap as prediction mean minus observation mean.

Use unrounded group coverages for minima and decision predicates. Round only
reported fields.

### 6. County trajectory PCA clustering

Build variable-major entity trajectories in declared variable and end-period
order. Standardize each feature by population moments. Use covariance Z'Z/n.

Sort eigenpairs descending and orient each loading so its earliest
maximum-absolute element is positive. Use the effective retained scores.

For each effective candidate k, initialize at the smallest entity id then add the
point farthest from its nearest center, breaking equality by entity id. Assign
equality to lower cluster id. Update arithmetic centers until unchanged labels
and registered center tolerance, or the iteration cap.

Compute Euclidean silhouette with singleton value zero. Select largest unrounded
mean silhouette, then smaller k.

For each state deletion, rebuild the full trajectory pipeline at selected k and
compare retained labels with adjusted Rand index. Report ordered refits and
stability summaries.

### 7. Source-group perturbation

For every source group and outer fold in declared order, remove exactly the group
terms and reuse that fold full-model selected hyperparameters without retuning.

Apply the same remaining-term preprocessing and solver. Retain all outer-fold
RMSEs, pool their squared errors, and subtract full-model OOF RMSE for
deterioration.

Count folds worse than corresponding full-model folds. Rank groups by decreasing
unrounded deterioration, then declared group order.

### 8. Controlled precedence

Complete all evidence modules. Evaluate effective gates on unrounded values and
return the first applicable controlled decision in effective precedence order.
