# PHO Protocol Profiles

Reusable algorithmic audit protocol profiles. Each profile is keyed by its exact `protocol_id` and carries canonical method specifications for every audit module. When a future request matches a known `protocol_id`, use the profile's module descriptions as the authoritative algorithm specification.

## Activation rule

A profile activates **only** when the future request's `protocol_id` is an exact case-sensitive string match. Family membership, a similar name, or similar subject matter is not a match.

## Override resolution (all profiles)

Every profile defines how a future request can override inherited defaults. The rules are shared across all protocols:

1. Start from the registered method profile and any inherited canonical defaults for this exact protocol version.
2. A direct future-request key targets the canonical root key of the identical name. Inside a named canonical section or module, a direct child key targets only the identical child path.
3. A root key named `<section>_overrides` targets canonical `<section>` after stripping the terminal `_overrides` suffix. `module_overrides.<module_name>` targets that exact top-level module. `reporting_overrides` targets `reporting`.
4. Apply resolved entries in request document order. Objects recursively merge by exact key. Arrays replace whole arrays — never concatenate or merge by position. Explicit scalars, strings, booleans, and null replace only their exact paths. Absent paths inherit unchanged.
5. No array concatenation, positional patch, inferred alias, key renaming, or type coercion is allowed. Reject unknown targets and incompatible types before evidence resolution.
6. Task-local direct bindings and resolved overrides take precedence over inherited values at the same path.
7. Resolve one effective request before any data access, folding, random draw, fit, aggregation, or decision, and use it consistently in every module.

## Instance boundary (all profiles)

Protocol profiles carry **method semantics only**. The following are always taken from the effective future request:

- Entities, measures, and geographic scope
- Calendar scope (years, reference year, panel start/end)
- Source filters (release status, value type, source type)
- Random seed, stream, replicate schedule
- Hyperparameter grid values
- Business decision cutoffs and gate predicates
- Requested labels and output vocabulary
- Reporting precision

Never carry task-local values or solved analytical values across invocations. Recompute all evidence and outputs for the future invocation.

---

## Profile: PHO_STATE_TRANSPORT_AUDIT_V1

State-level algorithmic transportability audit with six modules.

### Module execution order

1. release_resolution_and_cohorts
2. delete_cluster_fixed_effects
3. nested_ridge_division_cv
4. wild_cluster_bootstrap
5. grouped_split_conformal
6. trajectory_pca_clustering
7. source_year_perturbation
8. controlled_decision

### Module: release_resolution_and_cohorts

Filter each requested publication key by the effective status, source, value type, validity, and geography bindings. Select greatest revision, then latest release timestamp, then lowest record identifier. Count selected publications before analytic completeness exclusions when requested; suppressed, invalid, withdrawn, blank, or null analytic values remain unavailable and are never zero-filled.

Join independently resolved series by the effective stable entity and time keys. Construct each complete, balanced, broad, or dual-source analytic set from its effective required fields; preserve entity-code then time order, and preserve every declared feature and group order.

### Module: delete_cluster_fixed_effects

**Transform.** On every active refit transform each modeled variable as z_it minus its active entity mean minus its active time mean plus its active grand mean, then solve OLS without an intercept in declared predictor order. A deletion removes the whole cluster, recomputes every mean, and refits from scratch in entity-code order.

**Jackknife inference.** For G delete estimates b_-g and mean bbar, SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2)) and b_BC = G*b - (G-1)*bbar. The registered test uses b/SE_JK with two-sided Student t and G-1 degrees of freedom. Select extrema by coefficient, then entity code.

### Module: nested_ridge_division_cv

**Folds and scaling.** Hold out one ordered group per outer fold; within each outer training set hold out every remaining group once in the same order. For every fit, subtract training-only feature means and divide by training sample SD with ddof one, then apply those moments to validation or test rows.

**Solver.** Center the training outcome, keep the intercept unpenalized, initialize coefficients to zero, and cycle in declared feature order for objective mean((y - a - Xb)^2) + lambda * sum_j(b_j^2). Update b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n*lambda), where r excludes feature j. Stop after a full sweep when max coefficient change is below the effective solver tolerance or at the effective sweep cap.

**Selection and aggregation.** For each penalty pool all inner validation squared errors at row level, take RMSE, choose the smallest RMSE and then the smaller penalty, refit on all outer-training rows, and predict all outer rows. Pool exactly one outer prediction per eligible row; compute RMSE, MAE, and Q^2 = 1 - pooled SSE / full-sample outcome SST.

### Module: wild_cluster_bootstrap

**Observed and restricted.** Use the same double-demeaned matrix as the fixed-effects module. For cluster scores s_g = X_g' * e_g, compute V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g(s_g * s_g') * (X'X)^-1. Studentize the full target coefficient, then fit the restricted model without the target and retain restricted fitted values and residuals.

**PCG32 PRNG.** Use unsigned wraparound with a 64-bit state and 32-bit output. Let increment = 2*stream + 1; initialize state to zero, advance, add the effective initialization value modulo 2^64, and advance. Each advance: old = state, state = old * 6364136223846793005 + increment mod 2^64; xorshifted = low32(((old>>18) xor old)>>27); rot = old>>59; output = rotate_right_32(xorshifted, rot). Map output modulo six in order to [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].

**Draw, fit, and test.** Maintain one continuous generator. For every replicate draw once per cluster in entity-code order, set y* = restricted_fit + restricted_residual * cluster_weight, refit the unrestricted model, recompute CR1, and studentize. Checkpoints are recorded only after their completed replicate, without resetting the stream. Count abs(t*) >= abs(t_observed) and report (1 + count)/(1 + B). Aggregate consecutive replicate batches exactly as bound. For sorted values x and probability p, nearest-rank output is x[min(B, ceil(p*B)) - 1] using one-based rank.

### Module: grouped_split_conformal

**Partition and fit.** For each ordered outer group, use it as test; among remaining groups choose calibration by greatest row count then ascending group name, and use all others for proper training. Fit ridge from scratch with the effective fixed penalty and the identical training-only scaling and solver rules.

**Rank, interval, and aggregate.** Sort m absolute calibration residuals. With effective miscoverage alpha, use one-based r = min(m, ceil((m+1)*(1-alpha))) and q = score[r]. Intervals prediction +/- q are inclusive. Report fold coverage, width, and absolute error, then aggregate coverage and width by outer-test row counts.

### Module: trajectory_pca_clustering

**PCA.** Build columns in effective variable-major/time order, standardize by active-column sample SD, and form C = Z'Z/(n-1). In symmetric Jacobi, select the largest absolute upper-triangle off-diagonal, tying by lower row then column; tau = (Aqq - App)/(2*Apq); t = sign_nonnegative(tau)/(abs(tau) + sqrt(1 + tau^2)); c = 1/sqrt(1 + t^2); s = t*c; rotate A and eigenvectors; stop at the effective off-diagonal tolerance or step cap. Order components by descending eigenvalue then original diagonal index; flip each loading so the earliest maximum-absolute entry is positive; scores are Z times loadings.

**Clustering.** Run squared-Euclidean k-means on the effective leading scores. First center is the ASCII-first entity; each next is the entity maximizing distance to its nearest center, tied by entity code. Assign to nearest center, tied by lower working id; update by member means; stop when assignments are unchanged or at the effective cap. Canonicalize final ids by centroid coordinates then working id.

**Stability.** For each omitted time block in ascending order, rebuild scaling, PCA, orientation, initialization, and clustering. Compute adjusted Rand index from the contingency table. Align refit labels by maximum agreement, tying to the lexicographically smallest permutation.

### Module: source_year_perturbation

**Enumeration and refit.** Enumerate effective time subsets by increasing requested subset size and lexicographic tuple order. Keep the effective strict analytic set unchanged. For each subset refit the complete double-demeaned model separately with primary and parallel series, recomputing CR1 and two-sided G-1-df inference for each fit.

**Aggregation.** For baseline coefficient b and alternate b_alt, shift = abs(b_alt - b)/abs(b)*100; same-sign requires both nonzero with identical sign. Compute the ordinary median of ordered shifts. Choose the worst by greatest unrounded shift, then earlier subset order.

### Module: controlled_decision

Complete every module, evaluate every effective business predicate on unrounded values, preserve the listed module order for gate reporting, count satisfied predicates, and apply only the effective request's controlled decision mapping and tie/precedence rules.

---

## Profile: PHO_COUNTY_MEDIATION_TRANSPORT_V1

County-level mediation transport audit with eight modules.

### Module execution order

1. publication_and_linked_cohorts
2. primary_mediation_models
3. difference_gmm_mediation
4. nested_state_ridge
5. paired_state_wild_bootstrap
6. state_grouped_conformal
7. partial_r2_sensitivity
8. state_trajectory_pca_clustering
9. controlled_precedence

### Module: publication_and_linked_cohorts

Filter each source by effective request fields; select one record per declared entity-time-measure key using the declared ordered release priority. Count selected publications before analytic completeness exclusions when requested; suppressed or null selected health records remain publication evidence but are incomplete. Construct primary, balanced-panel, and machine-learning cohorts from effective nonmissing and validity predicates; preserve declared entity and state order.

### Module: primary_mediation_models

Build total-effect, path-a, and direct/path-b OLS designs from effective exposure, mediator, outcome, covariates, transformations, references, and column order. Use the unrounded fitted objects as the shared source for downstream bootstrap and sensitivity modules.

### Module: difference_gmm_mediation

Create adjacent-change rows in entity then end-period order using the effective lag structure and equation bindings. For each equation use W = (Z'Z)^-1 and beta = (X'Z W Z'X)^-1 X'Z W Z'y. With residual u and cluster score q_g = Z_g' u_g, use the registered finite-sample cluster sandwich; for two equations use the corresponding cross-cluster score product. For indirect theta = a*b use Var(theta) = b^2 Var(a) + a^2 Var(b) + 2ab Cov(a,b), and Student-t inference with cluster degrees of freedom. Compute first-stage partial F from full-versus-reduced residual sums of squares using effective instrument counts. For every delete-state diagnostic, rebuild rows and refit all affected equations from scratch in state order.

### Module: nested_state_ridge

Use effective feature arrays in exact order. Within every fit, standardize from training arithmetic means and population standard deviations, with a unit divisor for zero variance; apply those moments to held-out rows. Fit ridge with an unpenalized intercept by minimizing training SSE plus lambda times the squared non-intercept norm. Outer validation leaves one state out; each inner validation leaves one remaining state out. Pool county squared errors before RMSE. Select the smallest unrounded inner RMSE, breaking equality toward the smaller penalty; refit on all outer-training rows and retain complete aligned grids and outer diagnostics. Aggregate OOF metrics from the single prediction assigned to every eligible row.

### Module: paired_state_wild_bootstrap

For each target, fit the restricted model with only that target removed; form synthetic outcomes from restricted fitted values plus cluster-weighted restricted residuals, then refit unrestricted models and recompute CR1 t statistics. Use unsigned xorshift32: x ^= x<<13, x ^= x>>17, x ^= x<<5, masking to 32 bits after each operation. Map odd state to +1 and even state to -1. Maintain one continuous stream; draw once per state in ascending state order per replicate and reuse the same state sign across the paired equations. Use two-sided absolute exceedances with plus-one p = (count+1)/(B+1). Use nearest-rank order statistics for declared probabilities and bootstrap-t inversion with the observed standard error. Record checkpoints only after the listed replicate is complete, using the current PRNG state and that replicate statistics.

### Module: state_grouped_conformal

Index states in ascending order and assign cyclic partitions by index modulo the effective partition count. For each test partition, use the registered preceding calibration partition and remaining partitions for proper training. Reduce calibration residuals to one maximum absolute residual per calibration state. Use k = min(m, ceil((m+1)*coverage)) and the one-based kth state maximum. Build symmetric inclusive intervals; aggregate county coverage and width by cycle and state, using declared order for worst-state selection.

### Module: partial_r2_sensitivity

From unrounded baseline a, b, SE_b, and residual df, compute magnitude = SE_b * sqrt(df * rY * rM / (1 - rM)). For each declared direction use adjusted_b = b - s*magnitude, adjusted_indirect = a * adjusted_b, adjusted_direct = total - adjusted_indirect, and proportion = adjusted_indirect/total. Enumerate the complete effective surface in declared R2 and direction order; compute the equal-strength positive tipping root from unrounded inputs.

### Module: state_trajectory_pca_clustering

Aggregate effective balanced-panel measures to state-period means in declared feature order. Standardize across states with sample standard deviations and use covariance Z'Z/(G-1). Sort eigenpairs descending; orient each eigenvector so the earliest maximum-absolute loading is positive; score with the oriented loadings. Run deterministic farthest-first Lloyd k-means using the effective cluster count, lower cluster id on assignment equality, arithmetic centroid updates, unchanged-label plus registered center-tolerance convergence, and the registered iteration cap. For every leave-period stability fit, rebuild standardization, PCA orientation, seeds, and clusters from scratch; compare labels with adjusted Rand index.

### Module: controlled_precedence

Complete every evidence module first. Evaluate effective business predicates on unrounded values, count supported predicates, and return the first applicable controlled class in the effective precedence order.

---

## Profile: PHO_STATE_ROBUSTNESS_TRANSPORT_V1

State-level robustness/transport audit with reliability weights and six modules.

### Module execution order

1. release_and_cohort
2. common_weighted_linear_algebra
3. cluster_jackknife
4. nested_elastic_net
5. wild_cluster_bootstrap
6. grouped_conformal
7. trajectory_pca_clustering
8. exhaustive_source_perturbation
9. controlled_decision

### Module: release_and_cohort

Filter each publication key by effective status, source, value type, validity, and entity bindings; select greatest revision, latest release timestamp, then greatest record id. Suppressed, invalid, blank, or null values are unavailable and never zero-filled. Unless overridden, keep the selected direct outcome-record sample size as fixed positive reliability weight even when replacing outcome source. Join resolved series by stable entity-time keys and apply effective completeness fields. Preserve declared entity, time, feature, and cluster order.

### Module: common_weighted_linear_algebra

**WLS.** For design X, outcome y, and positive weights w, set Xw = diag(sqrt(w))*X and yw = diag(sqrt(w))*y, then solve b = (Xw' Xw)^-1 Xw' yw in declared column order.

**HC3.** With h_i = diag(Xw (Xw' Xw)^-1 Xw') and ew_i = sqrt(w_i)*(y_i - X_i b), V_HC3 = (Xw' Xw)^-1 Xw' diag(ew_i^2/(1 - h_i)^2) Xw (Xw' Xw)^-1. Use two-sided Student t with n-k residual degrees of freedom.

**CR1.** For ordered clusters g and s_g = Xw_g' ew_g, V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw' Xw)^-1 * sum_g(s_g s_g') * (Xw' Xw)^-1. Use two-sided Student t with G-1 degrees of freedom.

### Module: cluster_jackknife

Fit the full weighted design, then delete every registered cluster in order and refit the unchanged design from scratch. For target coefficient b and delete value b_-g, percent change = 100*abs((b_-g - b)/b); choose greatest unrounded change, tied by earlier cluster order. For G delete estimates and mean bbar, b_BC = G*b - (G-1)*bbar and SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2)). Test b_BC/SE_JK two-sided with G-1 Student-t degrees of freedom.

### Module: nested_elastic_net

**Folds and features.** Hold out each registered cluster as an outer fold and each remaining cluster as an ordered inner fold. Build effective raw, transformed, squared, and interaction features in declared order.

**Scaling and objective.** Inside every fit compute training-only weighted mean mu_j and weighted population SD sigma_j = sqrt(sum_i w_i*(x_ij - mu_j)^2 / sum_i w_i), standardize training and prediction rows with them, and center y by its training weighted mean without scaling y. Minimize sum_i w_i*(y_i - Z_i b)^2/(2*sum_i w_i) + lambda * [alpha*sum_j abs(b_j) + (1-alpha)*sum_j b_j^2/2].

**Solver.** Cold-start b = 0 for every penalty and fold; never warm-start. In cyclic feature order set rho_j = sum_i w_i*Z_ij*(y_i - sum_{l!=j} Z_il*b_l)/sum_i w_i and b_j = S(rho_j, lambda*alpha)/(1 + lambda*(1-alpha)), with S(a,t) = sign(a)*max(abs(a)-t, 0). Stop after a complete cycle when max coefficient change is below the effective tolerance or at the effective cycle cap.

**Selection and aggregation.** For each penalty pool unweighted inner validation squared errors across rows and take RMSE, not the mean of fold RMSEs. Choose smallest RMSE then smaller penalty, cold-refit on all outer-training rows, and predict the outer holdout. Determine nonzero coefficients with the effective numerical cutoff. Pool outer predictions in entity order; report unweighted RMSE, MAE, and R^2 = 1 - SSE/sum_i(y_i - full_sample_unweighted_mean)^2.

### Module: wild_cluster_bootstrap

**Observed and restricted.** Studentize the full weighted target coefficient with registered cluster CR1, then fit the weighted restricted model without the target and retain untransformed fitted values and residuals in entity order.

**PRNG and draw.** Initialize one unsigned 32-bit xorshift state from the effective random binding. Each next call: x ^= x<<13, x ^= x>>17, x ^= x<<5, truncating to unsigned 32 bits after every xor. Maintain one continuous stream; in each replicate draw once per cluster in registered order and map low bit one to +1, otherwise -1.

**Refit, test, and quantiles.** Set y* = restricted_fit + restricted_residual * cluster_sign, refit full weighted WLS, recompute cluster CR1, and record the absolute studentized target. Record checkpoints after their completed replicate without resetting. With effective comparison tolerance delta, count t* >= t_observed - delta and report (1+count)/(1+B). For sorted x and probability p, type-seven quantile uses h = (B-1)*p, j = floor(h), gamma = h - j, and (1-gamma)*x[j] + gamma*x[j+1] with zero-based indexing.

### Module: grouped_conformal

**Calibration.** Reuse each outer center prediction and its selected penalty. For outer cluster d, hold out each other training cluster once, cold-refit the identical weighted elastic-net algorithm on the remaining clusters, predict the held-out calibration rows, and pool absolute residuals.

**Rank, interval, and aggregation.** For m sorted calibration scores and effective nominal coverage c, use one-based r = min(m, ceil((m+1)*c)) and radius q = score[r]. Intervals center +/- q are inclusive. Report ordered cluster diagnostics, pool covered and row counts, weight mean width by held-out count, and choose worst coverage by smallest fraction then earlier cluster order.

### Module: trajectory_pca_clustering

**PCA.** Build the effective variable-major/time-major blocks in declared order and entity ASCII order, standardize each column by active-sample sample SD, and eigendecompose C = Z'Z/(n-1). Order eigenvalues descending; for each retained eigenvector flip sign so its earliest maximum-absolute loading is positive. Scores equal Z times oriented loadings; explained ratios divide by the sum of all eigenvalues.

**Clustering (Lloyd k-means).** Run squared-Euclidean k-means on the effective leading scores. First center is the ASCII-first entity; each next is the entity maximizing distance to its nearest center, tied by entity code. Assign to nearest center, tied by lower id, and update by member means until assignments stop changing or the effective cap is reached. For empty ids in order, move the ASCII-first entity among those farthest from its assigned center, recompute, and continue.

**Stability.** For every omitted time block in ascending order, delete that complete variable block and rebuild scaling, PCA orientation, initialization, and clustering. Compute adjusted Rand index against the full assignment. Align refit ids by the permutation with maximum matches, tied by lexicographically smallest mapped-id vector, then report aligned changes.

### Module: exhaustive_source_perturbation

**Selection, order, and scenarios.** Resolve alternate outcomes with the module's effective release filters and greatest-revision/latest-release/greatest-id precedence. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. For index j and every mask from zero through 2^m - 1, replace entity j iff mask & (1<<j) is nonzero; retain fixed direct reliability weights and design, then refit WLS and HC3.

**Aggregation and ties.** Relative shift = 100*abs((b_mask - b_zero)/b_zero). For each popcount stratum report scenario count, coefficient range, HC3 p-value range, and mean shift. Select maximum unrounded shift, tied by smaller mask. Evaluate scenario stability only with the effective predicate.

**Shapley.** For ordered entity j, phi_j = sum_{S not containing j} |S|!*(m-|S|-1)!/m! * [b(S union {j}) - b(S)]. Preserve signed phi order and verify sum_j phi_j = b(all replacements) - b(no replacements) within numerical tolerance.

### Module: controlled_decision

Complete every module, evaluate every effective business predicate on unrounded values, and select the first unsatisfied module only by the listed precedence. Apply only the effective request's controlled output mapping.

---

## Profile: PHO_COUNTY_PANEL_TRANSPORT_V1

County-level panel transport audit with dynamic panel models and seven modules.

### Module execution order

1. publication_balanced_panel
2. delete_state_two_step_gmm
3. state_blocked_nested_elastic_net
4. state_wild_cluster_bootstrap_t
5. cross_fold_grouped_conformal
6. county_trajectory_pca_clustering
7. source_group_perturbation
8. controlled_precedence

### Module: publication_balanced_panel

Filter effective county health and socioeconomic sources independently; resolve one final record per declared key using effective release priority. Treat selected suppressed, invalid, or missing values as incomplete, never zero; retain only entities complete across every effective balanced period with valid geography attributes. Create adjacent-change rows ordered by entity identifier then end period; derive lagged levels, dynamic changes, reference indicators, and interactions in declared order.

### Module: delete_state_two_step_gmm

**Residualization.** Within every full or delete-state fit, residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms.

**Two-step GMM.** First-step moments are g(theta) = Z'(y - D theta)/n with identity weight. Build state scores s_g = Z_g' u_g and S = sum_g(s_g s_g')/n; second-step weight is the registered Moore-Penrose inverse of S. Compute second-step theta from the weighted linear moments and Hansen J = n * g(theta)' W g(theta). Apply the registered relative singular-value cutoff to every pseudoinverse.

**Jackknife.** Refit both steps after each state deletion in state order. With G clusters use theta_bc = G*theta_full - (G-1)*mean(theta_delete), and retain maximum absolute delete-state shifts.

### Module: state_blocked_nested_elastic_net

**Fold allocation.** Allocate states by descending retained-entity counts, assigning each to the currently smallest fold and using lower fold id on equality; sort state codes within folds and repeat allocation inside each outer-training set.

**Standardization and objective.** Within each fit standardize declared continuous columns from training population moments, leave indicators unchanged, apply training moments to held-out rows, and keep the intercept unpenalized. Minimize SSE/(2n) + alpha * (rho*sum|beta_j| + 0.5*(1-rho)*sum beta_j^2). Cold-start coefficients at zero and intercept at the training outcome mean.

**Solver.** In each cyclic sweep update the intercept by mean residual, then beta_j = soft_threshold(mean(x_j * r_partial), alpha*rho)/(mean(x_j^2) + alpha*(1-rho)) in declared coefficient order. Stop at the registered maximum-change tolerance or sweep cap.

**Selection.** Traverse the effective grid in declared outer/inner order. Pool inner squared errors before RMSE; select by smallest unrounded RMSE, then smaller alpha, then smaller l1 ratio. Refit outer models and pool OOF metrics.

### Module: state_wild_cluster_bootstrap_t

**Observed and restricted.** Fit full unpenalized OLS and state-cluster CR1 for the target. Fit the restricted model without the target and generate synthetic outcomes from restricted fitted values plus state-weighted restricted residuals.

**PRNG.** Use unsigned xorshift32 with shifts 13, 17, 5 and 32-bit masking after every xor. Maintain one continuous stream, drawing states in ascending order; odd maps to +1 and even to -1.

**Test and checkpoints.** Refit the full model and recompute CR1 each replicate. Use absolute-tail exceedances, plus-one p = (count+1)/(B+1), and nearest-rank order statistics at effective probabilities. Record each requested checkpoint after completing its state draws and t statistic.

### Module: cross_fold_grouped_conformal

Use outer OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. With m calibration rows use rank min(m, ceil((m+1)*coverage)); build symmetric inclusive intervals. Report fold, state, effective rurality-band, and decile calibration diagnostics. Assign prediction deciles after sorting by prediction and declared identifiers; compute signed gap as prediction mean minus observation mean. Use unrounded group coverages for minima and decision predicates; round only reported fields.

### Module: county_trajectory_pca_clustering

**Trajectory construction.** Build variable-major entity trajectories in declared variable and end-period order. Standardize each feature by population moments; use covariance Z'Z/n.

**PCA.** Sort eigenpairs descending and orient each loading so its earliest maximum-absolute element is positive; use the effective retained scores.

**Clustering grid.** For each effective candidate k, initialize at the smallest entity id then add the point farthest from its nearest center, breaking equality by entity id. Assign equality to lower cluster id; update arithmetic centers until unchanged labels and registered center tolerance, or the iteration cap. Compute Euclidean silhouette with singleton value zero; select largest unrounded mean silhouette, then smaller k.

**State-deletion stability.** For each state deletion, rebuild the full trajectory pipeline at selected k and compare retained labels with adjusted Rand index; report ordered refits and stability summaries.

### Module: source_group_perturbation

For every source group and outer fold in declared order, remove exactly the group terms and reuse that fold full-model selected hyperparameters without retuning. Apply the same remaining-term preprocessing and solver, retain all outer-fold RMSEs, pool their squared errors, and subtract full-model OOF RMSE for deterioration. Count folds worse than corresponding full-model folds. Rank groups by decreasing unrounded deterioration, then declared group order.

### Module: controlled_precedence

Complete all evidence modules. Evaluate effective gates on unrounded values and return the first applicable controlled decision in effective precedence order.
