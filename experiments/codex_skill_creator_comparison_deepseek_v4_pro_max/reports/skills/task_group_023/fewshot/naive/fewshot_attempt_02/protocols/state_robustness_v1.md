## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

State-level reliability-weighted robustness transport audit. Tests whether a
reliability-weighted association between a focal exposure and health outcome
survives six registered algorithmic modules, using five-year panels (typically
2020-2024), delete-cluster jackknife, nested elastic net, wild cluster bootstrap,
grouped conformal calibration, trajectory PCA clustering, and exhaustive
source perturbation with exact Shapley attribution.

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

### 1. Release and cohort

Filter each publication key by effective status, source, value type, validity,
and entity bindings. Select greatest revision, latest release timestamp, then
greatest record id. Suppressed, invalid, blank, or null values are unavailable
and never zero-filled.

Join resolved series by stable entity-time keys and apply effective completeness
fields. Keep the selected outcome direct-record sample_size as a fixed positive
reliability weight throughout, including during source-perturbation refits where
the outcome source changes but the weight stays pinned to the original
direct-record sample size.

Preserve declared entity, time, feature, and cluster order.

### 2. Common weighted linear algebra

**WLS**: For design X, outcome y, and positive weights w: Xw = diag(sqrt(w)) * X,
yw = diag(sqrt(w)) * y. Solve b = (Xw'Xw)^-1 Xw'yw in declared column order.

**HC3**: With h_i = diag(Xw * (Xw'Xw)^-1 * Xw') and ew_i = sqrt(w_i) *
(y_i - X_i * b): V_HC3 = (Xw'Xw)^-1 * Xw' * diag(ew_i^2 / (1 - h_i)^2) *
Xw * (Xw'Xw)^-1. Two-sided Student t with n-k df.

**CR1**: For ordered clusters g and s_g = Xw_g' * ew_g: V_CR1 = [G/(G-1)] *
[(n-1)/(n-k)] * (Xw'Xw)^-1 * sum_g(s_g * s_g') * (Xw'Xw)^-1. Two-sided Student
t with G-1 df.

### 3. Cluster jackknife

Fit the full weighted design, then delete every registered cluster in order and
refit the unchanged design from scratch. For target coefficient b and delete
value b_-g, percent change = 100 * abs((b_-g - b) / b). Choose greatest
unrounded change, tied by earlier cluster order.

For G delete estimates and mean bbar: b_BC = G*b - (G-1)*bbar, SE_JK =
sqrt((G-1)/G * sum_g(b_-g - bbar)^2). Test b_BC / SE_JK two-sided with G-1
Student-t df.

### 4. Nested elastic net

Hold out each registered cluster as an outer fold and each remaining cluster as
an ordered inner fold. Build effective raw, transformed, squared, and
interaction features in declared order.

Inside every fit compute training-only weighted mean mu_j and weighted
population SD sigma_j = sqrt(sum_i w_i * (x_ij - mu_j)^2 / sum_i w_i).
Standardize training and prediction rows with them. Center y by its training
weighted mean without scaling y.

Minimize: sum_i w_i * (y_i - Z_i * b)^2 / (2 * sum_i w_i) + lambda *
[alpha * sum_j |b_j| + (1-alpha) * sum_j b_j^2 / 2].

Cold-start b = 0 for every penalty and fold. In cyclic feature order set rho_j
= sum_i w_i * Z_ij * (y_i - sum_{l!=j} Z_il * b_l) / sum_i w_i, and b_j =
S(rho_j, lambda * alpha) / (1 + lambda * (1-alpha)), with S(a,t) = sign(a) *
max(|a| - t, 0). Stop after a complete cycle when max coefficient change is
below tolerance or at the cycle cap.

For each penalty pool unweighted inner validation squared errors across rows and
take RMSE. Choose smallest RMSE then smaller penalty. Cold-refit on all
outer-training rows and predict the outer holdout. Determine nonzero coefficients
with the effective numerical cutoff. Pool outer predictions in entity order;
report unweighted RMSE, MAE, and R2 = 1 - SSE / sum_i(y_i - full_sample_mean)^2.

### 5. Wild cluster bootstrap (xorshift32)

Studentize the full weighted target coefficient with registered cluster CR1. Fit
the weighted restricted model without the target and retain untransformed fitted
values and residuals in entity order.

Initialize one unsigned 32-bit xorshift state from the effective seed. Each call:
x xor= x << 13, x xor= x >> 17, x xor= x << 5, truncating to unsigned 32 bits
after each xor. Maintain one continuous stream. In each replicate draw once per
cluster in registered order and map low bit one to +1, otherwise -1.

Set y* = restricted_fit + restricted_residual * cluster_sign, refit full weighted
WLS, recompute cluster CR1, and record the absolute studentized target. Record
checkpoints after their completed replicate without resetting.

With effective comparison tolerance delta, count t* >= t_observed - delta and
report (1+count)/(1+B). For sorted x and probability p, type-seven quantile:
h = (B-1)*p, j = floor(h), gamma = h - j, output = (1-gamma)*x[j] +
gamma*x[j+1] with zero-based indexing.

### 6. Grouped conformal calibration

Reuse each outer center prediction and its selected penalty. For outer cluster d,
hold out each other training cluster once, cold-refit the identical weighted
elastic-net algorithm on the remaining clusters, predict the held-out calibration
rows, and pool absolute residuals.

For m sorted calibration scores and effective nominal coverage c, use one-based
r = min(m, ceil((m+1)*c)) and radius q = score[r]. Intervals center plus or
minus q are inclusive.

Report ordered cluster diagnostics. Pool covered and row counts. Weight mean
width by held-out count. Choose worst coverage by smallest fraction then earlier
cluster order.

### 7. Trajectory PCA clustering

Build effective variable-major/time-major blocks in declared order and entity
ASCII order. Standardize each column by active-sample sample SD. Eigendecompose
C = Z'Z/(n-1).

Order eigenvalues descending. For each retained eigenvector, flip sign so its
earliest maximum-absolute loading is positive. Scores = Z times oriented
loadings. Explained ratios divide by the sum of all eigenvalues.

Run squared-Euclidean k-means on the effective leading scores. First center is
the ASCII-first entity. Each next is the entity maximizing distance to its
nearest center, tied by entity code. Assign to nearest center, tied by lower id.
Update by member means until assignments stop changing or the effective cap.

For empty ids in order, move the ASCII-first entity among those farthest from
its assigned center, recompute, and continue.

Stability: For every omitted time block in ascending order, delete that complete
variable block and rebuild scaling, PCA orientation, initialization, and
clustering. Compute ARI against the full assignment. Align refit ids by the
permutation with maximum matches, tied by lexicographically smallest mapped-id
vector, then report aligned changes.

### 8. Exhaustive source perturbation with Shapley

Resolve alternate outcomes with the module's effective release filters and
greatest-revision/latest-release/greatest-id precedence. Order paired entities by
descending absolute alternate-minus-primary difference, tied by entity code.

For index j and every mask from zero through 2^m-1, replace entity j iff
mask & (1 << j) is nonzero. Retain fixed direct reliability weights and design,
then refit WLS and HC3.

Relative shift = 100 * abs((b_mask - b_zero) / b_zero). For each popcount stratum
report scenario count, coefficient range, HC3 p-value range, and mean shift.
Select maximum unrounded shift, tied by smaller mask.

Shapley: For ordered entity j, phi_j = sum_{S not containing j} |S|! *
(m - |S| - 1)! / m! * [b(S union {j}) - b(S)]. Preserve signed phi order and
verify sum_j phi_j = b(all replacements) - b(no replacements) within numerical
tolerance.

### 9. Controlled decision

Complete every module. Evaluate every effective business predicate on unrounded
values. Select the first unsatisfied module only by the listed precedence. Apply
only the effective request's controlled output mapping.
