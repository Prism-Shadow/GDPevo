# Shared numerical conventions

All formulas use the effective request's bindings (cohort, variables, order, weights, cluster definition). **Compute on unrounded values; round only when reporting.** This file defines the method; the request supplies every task-local value.

## Weighted linear algebra (when reliability weights apply)

- **WLS:** for design X, outcome y, positive weights w, set Xw = diag(sqrt(w))·X and yw = diag(sqrt(w))·y; solve b = (Xw'Xw)^-1·Xw'yw in declared column order.
- **HC3:** with h_i = diag(Xw·(Xw'Xw)^-1·Xw') and ew_i = sqrt(w_i)·(y_i − X_i·b), V_HC3 = (Xw'Xw)^-1·Xw'·diag(ew_i^2/(1−h_i)^2)·Xw·(Xw'Xw)^-1. Two-sided Student-t with n−k residual df.
- **CR1 (cluster-robust):** for ordered clusters g with s_g = Xw_g'·ew_g, V_CR1 = [G/(G−1)]·[(n−1)/(n−k)]·(Xw'Xw)^-1·[Σ_g s_g·s_g']·(Xw'Xw)^-1. Two-sided Student-t with G−1 df.

## Two-way fixed effects (when declared)

- Active transform: z_it − entity_mean − time_mean + grand_mean (recompute every mean per active refit/deletion), then OLS without intercept in declared predictor order.
- A deletion removes the whole cluster, recomputes every mean, and refits from scratch in entity-code order.

## Jackknife (delete-one-cluster)

- For G delete estimates b_−g and their mean bbar: SE_JK = sqrt((G−1)/G · Σ_g (b_−g − bbar)^2); bias-corrected b_BC = G·b − (G−1)·bbar.
- Test b/SE_JK (or b_BC/SE_JK per the request) two-sided Student-t with G−1 df.
- Percent change for a deletion: 100·abs((b_−g − b)/b). Select extrema/worst by the requested statistic (coefficient or percent change), then by entity/cluster code.
- Delete-state bias-corrected variants (GMM/mediation): theta_bc = G·theta_full − (G−1)·mean(theta_delete); retain maximum absolute delete-state shifts.

## Nested grouped ridge / elastic-net CV

- **Folds.** Outer fold = hold out one declared group (division/state); inner fold = hold out one remaining group, in the same declared order. (State-blocked variant with a fixed fold count: allocate states by descending retained-entity counts to the currently smallest fold, lower fold id on ties; repeat allocation inside each outer-training set.)
- **Scaling.** Within every fit, standardize from training-only moments: subtract training mean, divide by training SD (ddof per the request: sample SD ddof=1 is typical; population SD ddof=0 appears in weighted/county variants). Apply those moments to validation/test rows. Keep the intercept unpenalized; center y by its training mean (do not scale y). Leave declared indicator terms unstandardized when the request says so.
- **Objective.**
  - Ridge: minimize training SSE + lambda·Σ_j b_j^2 (intercept unpenalized).
  - Elastic net: minimize SSE/(2n) + alpha·(rho·Σ|b_j| + 0.5·(1−rho)·Σ b_j^2), with rho = l1_ratio.
- **Solver.** Cold-start b=0 (intercept at training y mean) for every penalty and fold — never warm-start. Cyclic coordinate descent in declared feature order:
  - Ridge: b_j = Σ_i x_ij·r_ij / (Σ_i x_ij^2 + n·lambda), r excludes feature j (weighted form: replace sums with weighted sums and n with Σ w_i).
  - Elastic net: b_j = S(rho_j, alpha·rho) / (mean(x_j^2) + alpha·(1−rho)), where rho_j is the mean (weighted) partial-residual correlation and S(a,t)=sign(a)·max(|a|−t,0); update the intercept by the mean residual each sweep.
  - Stop after a full sweep when max coefficient change < effective tolerance, or at the effective sweep/cycle cap. Record coordinate-cycle counts when requested.
- **Selection.** For each penalty, pool inner validation squared errors across rows (not the mean of fold RMSEs) and take RMSE. Choose smallest RMSE, then smaller penalty (ridge) / smaller alpha then smaller l1_ratio (elastic net). Refit on all outer-training rows; predict the outer holdout.
- **Aggregation.** Pool exactly one outer prediction per eligible row (in entity order). Report unweighted RMSE, MAE, and R^2 = 1 − SSE / Σ_i (y_i − full_sample_unweighted_mean)^2 (or 1 − SSE/SST per the request). Determine nonzero coefficients with the request's numerical cutoff.

## Wild cluster bootstrap-t

- **Observed.** Studentize the full target coefficient with cluster CR1 (or HC3 when no clustering): t_obs = b / SE.
- **Restricted null.** Fit the restricted model with only the target removed; retain untransformed fitted values and residuals in entity order.
- **Draws.** Set y* = restricted_fit + restricted_residual·cluster_weight. Refit the unrestricted model, recompute CR1, studentize the target. Draw once per cluster in registered/entity-code order per replicate. Maintain **one continuous stream**; record checkpoints only **after** their completed replicate, without resetting.
- **PRNG families (use the one the request declares):**
  - *xorshift32* (unsigned 32-bit): each next call does x ^= x<<13; x ^= x>>17; x ^= x<<5, masking to unsigned 32 bits after every xor. Map low bit 1 (odd) → +1, else −1.
  - *PCG32* (64-bit state, 32-bit output): increment = 2·stream+1; init state 0, advance, add the declared init value mod 2^64, advance. Advance: old=state; state = old·6364136223846793005 + increment mod 2^64; xorshifted = low32(((old>>18) xor old)>>27); rot = old>>59; output = rotate_right_32(xorshifted, rot). Map output mod 6 → [−sqrt(3/2), −1, −sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].
  - For paired/multi-equation bootstraps, reuse the same cluster sign across the paired equations.
- **Test.** Count abs(t*) ≥ abs(t_obs) (or ≥ t_obs − delta with the effective comparison tolerance) and report plus-one p = (1 + count)/(1 + B). Report batch exceedance counts when the request asks for batches.
- **Quantiles.** Use the request's quantile rule: nearest-rank (one-based rank min(B, ceil(p·B))) or type-seven (h=(B−1)·p, j=floor(h), gamma=h−j, (1−gamma)·x[j] + gamma·x[j+1], zero-based). Bootstrap-t inversion uses the observed SE.

## Grouped split conformal

- **Partition.** For each ordered outer group as test: choose calibration by greatest row count then ascending group name (or the registered preceding cyclic partition), and use all others for proper training. (Cyclic variant: assign groups by index mod partition_count; calibration = preceding partition.) Fit ridge/elastic-net from scratch with the fixed penalty and the identical training-only scaling/solver.
- **Rank interval.** Sort m absolute calibration residuals. With miscoverage alpha and coverage c = 1−alpha, one-based r = min(m, ceil((m+1)·c)); radius q = score[r]. Intervals prediction ± q are inclusive. (County/row-level variants reduce calibration residuals to one maximum-absolute residual per calibration state, then use k = min(m, ceil((m+1)·c)).)
- **Aggregation.** Report fold coverage, width, and absolute error; aggregate coverage and width by outer-test row counts (weight mean width by held-out count). Worst = smallest coverage fraction, then earlier group order. Also report per-state and per-band (e.g. RUCC) coverage and prediction-decile calibration when requested.

## Trajectory PCA + deterministic k-means + stability

- **Matrix.** Build columns in effective variable-major/time-major (or time-major/variable) order, in declared order and entity ASCII order. Standardize each column by active-sample SD. Form C = Z'Z/(n−1) (county/weighted variants may use /n).
- **Eigensolver.** Symmetric Jacobi: repeatedly select the largest absolute upper-triangle off-diagonal (tie by lower row then column); tau = (Aqq − App)/(2·Apq); t = sign_nonneg(tau)/(|tau| + sqrt(1+tau^2)); c = 1/sqrt(1+t^2); s = t·c; rotate A and eigenvectors; stop at the effective off-diagonal tolerance or step cap. Order components by descending eigenvalue then original diagonal index. Explained ratios divide by the sum of all eigenvalues.
- **Orientation.** Flip each retained loading so its earliest maximum-absolute entry is positive. Scores = Z · oriented loadings.
- **k-means.** Squared-Euclidean Lloyd on the effective leading scores.
  - Initialization: first center = ASCII-first entity; each next center = entity maximizing distance to its nearest center, tie by entity code. (Alternative: smallest entity id, then farthest-first.)
  - Assignment: nearest center, tie by lower cluster id. Update: arithmetic member means. Stop when assignments unchanged or at the effective iteration cap. For empty clusters, move the ASCII-first entity among those farthest from its assigned center, recompute, continue. Canonicalize final ids by centroid coordinates then working id.
  - Candidate-k selection (when requested): compute Euclidean silhouette (singleton value 0); select largest unrounded mean silhouette, then smaller k.
- **Stability.** For each omitted time block (leave-year-out) or deleted cluster (delete-state) in ascending/declared order, delete that complete variable block/entity set and rebuild scaling, PCA orientation, initialization, and clustering from scratch. Compute adjusted Rand index (ARI) from the contingency table: ARI = (Σ_ij C(n_ij,2) − expected) / (0.5·(Σ_i C(a_i,2) + Σ_j C(b_j,2)) − expected), expected = Σ_i C(a_i,2)·Σ_j C(b_j,2) / C(n,2). Align refit labels by the permutation with maximum agreement, tie by lexicographically smallest mapped-id vector; report aligned changes. Summaries: minimum ARI, median ARI, mean ARI — whichever the request declares.

## Mediation / GMM (when declared)

- **Mediation designs.** Build total-effect, path-a (exposure→mediator), and direct/path-b (exposure+mediator→outcome) OLS designs from effective exposure/mediator/outcome/covariates/transformations/references/column order. Use unrounded fitted objects as the shared source for bootstrap and sensitivity.
- **Indirect effect** theta = a·b: Var(theta) = b^2·Var(a) + a^2·Var(b) + 2·a·b·Cov(a,b); Student-t with cluster df. First-stage partial F from full-vs-reduced residual SS using effective instrument counts.
- **Difference/linear GMM.** Create adjacent-change rows in entity then end-period order using the effective lag structure. For each equation use W=(Z'Z)^-1 and beta=(X'ZWZ'X)^-1·X'ZWZ'y. Cluster sandwich from cluster scores q_g = Z_g'·u_g; cross-equation uses the cross-cluster score product. Hansen J = n·g(theta)'·W·g(theta). Apply the declared relative singular-value cutoff to every pseudoinverse. Delete-cluster refits rebuild rows and refit all affected equations/steps from scratch in cluster order.

## Partial-R^2 sensitivity surface (when declared)

- From unrounded baseline a, b, SE_b, and residual df: magnitude = SE_b·sqrt(df·rY·rM/(1−rM)).
- For each declared direction (NEGATIVE/POSITIVE) and each (r2_mediator, r2_outcome) pair: adjusted_b = b − s·magnitude; adjusted_indirect = a·adjusted_b; adjusted_direct = total − adjusted_indirect; proportion = adjusted_indirect/total.
- Enumerate the complete surface in declared R2 then direction order. Compute the equal-strength positive tipping root from unrounded inputs.

## Source perturbation

- **Year/subset perturbation.** Enumerate effective time subsets by increasing requested subset size then lexicographic tuple order. Keep the strict analytic set unchanged. For each subset refit the double-demeaned model separately with primary and parallel series, recomputing CR1 and two-sided G−1-df inference. shift = 100·abs(b_alt − b)/abs(b); same-sign requires both nonzero with identical sign. Median of ordered shifts. Worst by greatest unrounded shift, then earlier subset order.
- **Source-group deletion (no retune).** For every source group and outer fold in declared order, remove exactly the group's terms and reuse that fold's full-model selected hyperparameters without retuning; apply the same preprocessing/solver; pool squared errors; deterioration = pooled_rmse − full_oof_rmse. Count folds worse than the corresponding full-model fold; rank groups by decreasing unrounded deterioration, then declared order.
- **Exhaustive direct-vs-rollup source perturbation.** Resolve alternate outcomes with the module's effective release filters and greatest-revision/latest-release/(greatest-or-lowest)-id precedence. Order paired entities by descending absolute alternate-minus-primary difference, tie by entity code. For index j and every mask 0..2^m−1, replace entity j iff mask&(1<<j); retain fixed direct reliability weights and design; refit WLS + HC3. Relative shift = 100·abs((b_mask − b_zero)/b_zero). For each popcount stratum report scenario count, coefficient range, HC3 p-value range, mean shift. Select maximum unrounded shift, tie by smaller mask. **Exact Shapley:** phi_j = Σ_{S not containing j} |S|!·(m−|S|−1)!/m! · [b(S∪{j}) − b(S)]; preserve signed order; verify Σ_j phi_j = b(all replacements) − b(no replacements) within numerical tolerance.

## Decision

- Complete every evidence module first.
- Evaluate every effective business predicate (gate) on **unrounded** values.
- Two controlled-decision shapes:
  - *Count-threshold classification:* count satisfied gates; apply the request's mapping (e.g. all-pass / at-least-N-pass / otherwise) in declared precedence.
  - *First-failed-module:* in the request's module precedence, the first unsatisfied module determines the conclusion (a "passed" value when all pass, otherwise a conclusion naming that first failed module, using the request's declared vocabulary); NONE/empty when all pass.
- Preserve the listed module order for gate reporting. Apply only the effective request's controlled output mapping and tie/precedence rules.
