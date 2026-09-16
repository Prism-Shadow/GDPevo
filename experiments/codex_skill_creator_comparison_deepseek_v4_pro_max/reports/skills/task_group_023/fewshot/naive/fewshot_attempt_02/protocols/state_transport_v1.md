## PHO_STATE_TRANSPORT_AUDIT_V1

State-level algorithmic transport audit. Tests whether a focal exposure is a
transportable signal for a health outcome across 50 states plus DC, using
five-year panels (typically 2020-2024), double-demeaned fixed effects, nested
ridge CV, wild cluster bootstrap, grouped conformal inference, trajectory PCA
clustering, and exhaustive source/year perturbation.

### Module execution order

1. release_resolution_and_cohorts
2. delete_cluster_fixed_effects
3. nested_ridge_division_cv
4. wild_cluster_bootstrap
5. grouped_split_conformal
6. trajectory_pca_clustering
7. source_year_perturbation
8. controlled_decision

### 1. Release resolution and cohorts

Filter each requested publication key by effective status, source, value type,
validity, and geography. Select greatest revision, then latest release
timestamp, then lowest record identifier. Count selected publications before
analytic completeness exclusions.

Join independently resolved series by stable entity and time keys. Construct
each cohort type:

- Core complete (yearly): Complete for outcome, exposure, and all core panel
  variables in that year.
- Core balanced: Core-complete in every analysis year. Preserve entity-code
  order, then time order.
- Broad reference cohort: Reference-year complete cases for outcome and all
  ordered ridge features.
- Strict dual-source cohort: Complete for outcome, primary exposure, parallel
  exposure, and adjustments in every analysis year.

Suppressed, invalid, withdrawn, blank, or null analytic values remain
unavailable and are never zero-filled.

### 2. Delete-cluster fixed effects (jackknife)

Transform panel using double-demeaning: for every variable z_it, compute
z_it - mean_i(z) - mean_t(z) + grand_mean(z). Recompute means after every
cluster deletion. Fit OLS without intercept in declared predictor order.

Delete each cluster (state) in entity-code order, refit from scratch. For G
delete estimates b_-g and mean bbar:

- SE_JK = sqrt((G-1)/G * sum_g(b_-g - bbar)^2)
- b_BC = G * b - (G-1) * bbar

Test b_BC / SE_JK with two-sided Student t, G-1 degrees of freedom. Select
extrema by coefficient value, then entity code.

### 3. Nested ridge division CV

Outer folds hold out one census division at a time in declared division order.
Inner folds: within each outer training set, hold out every remaining division
once in the same order.

For every fit:
- Subtract training-only feature means, divide by training sample SD (ddof=1).
- Apply those moments to validation/test rows.
- Center the training outcome, keep intercept unpenalized.
- Initialize coefficients to zero.
- Cycle features in declared order: update b_j = sum_i x_ij * r_ij / (sum_i
  x_ij^2 + n * lambda), where r excludes feature j.
- Stop when max coefficient change is below tolerance or at the sweep cap.

For each penalty, pool all inner validation squared errors at row level, take
RMSE. Choose smallest RMSE, then smaller penalty. Refit on all outer-training
rows and predict all outer rows. Pool one prediction per eligible row. Report
RMSE, MAE, and Q^2 = 1 - pooled_SSE / full_sample_outcome_SST.

### 4. Wild cluster bootstrap (PCG32 Webb)

Use the same double-demeaned matrix as module 2. Fit unrestricted model,
compute CR1 cluster-robust variance with state clusters, studentize the target
coefficient (t_observed = b / SE_CR1).

Fit restricted model without the target. Retain restricted fitted values and
residuals.

PCG32 generator: 64-bit state, 32-bit output. Increment = 2 * stream + 1.
Initialize state to zero, advance, add seed modulo 2^64, advance. Each advance:
old = state, state = old * 6364136223846793005 + increment mod 2^64,
xorshifted = low32(((old >> 18) xor old) >> 27), rot = old >> 59, output =
rotate_right_32(xorshifted, rot). Map output modulo 6 in order to
[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].

Maintain one continuous generator. For each replicate, draw once per cluster in
entity-code order. Set y* = restricted_fit + restricted_residual *
cluster_weight, refit unrestricted model, recompute CR1, studentize. Record
checkpoints after their completed replicate without resetting the stream.

Count abs(t*) >= abs(t_observed). Report plus-one p-value = (count+1)/(B+1).
Aggregate consecutive replicate batches exactly as bound. For sorted x and
probability p: one-based rank = min(B, ceil(p * B)), output x[rank - 1].

### 5. Grouped split conformal (ridge)

For each ordered outer division (test):
- Among remaining divisions, select calibration by greatest row count, then
  ascending division name.
- Use all others for proper training.

Fit ridge from scratch with the effective fixed penalty and the identical
training-only scaling and solver rules as module 3. Sort m absolute calibration
residuals. With effective alpha, r = min(m, ceil((m+1) * (1-alpha))), q =
score[r]. Intervals are prediction plus or minus q, inclusive.

Report fold coverage, width, and absolute error. Aggregate coverage and width
by outer-test row counts.

### 6. Trajectory PCA clustering

Build columns in effective variable-major/time order. Standardize by
active-column sample SD. Form C = Z'Z / (n-1).

Eigendecomposition by symmetric Jacobi: select largest absolute upper-triangle
off-diagonal, tiebreaking by lower row then column. tau = (Aqq - App) / (2 *
Apq), t = sign_nonnegative(tau) / (abs(tau) + sqrt(1 + tau^2)), c = 1/sqrt(1 +
t^2), s = t * c. Rotate A and eigenvectors. Stop at off-diagonal tolerance or
step cap.

Order components by descending eigenvalue, then original diagonal index. Flip
each loading so the earliest maximum-absolute entry is positive. Scores = Z *
loadings.

K-means (3 clusters): First center = ASCII-first entity. Each next = entity
maximizing distance to nearest center, tiebreak by entity code. Assign to
nearest center, tiebreak by lower working id. Update by member means. Stop when
assignments unchanged or at iteration cap. Canonicalize final ids by centroid
coordinates then working id.

Stability: For each omitted year, rebuild scaling, PCA, orientation,
initialization, and clustering. Compute ARI = (sum_ij C(n_ij, 2) - expected) /
(0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2)) - expected), with expected = sum_i
C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2). Align refit labels by maximum
agreement, tiebreak lexicographically.

### 7. Source/year perturbation

Enumerate effective time subsets by increasing subset size, then lexicographic
tuple order. Keep the strict analytic set unchanged. For each subset, refit the
complete double-demeaned model separately with primary and parallel series,
recomputing CR1 and two-sided G-1-df inference for each fit.

For baseline coefficient b and alternate b_alt: shift = abs(b_alt - b) / abs(b)
* 100. Same-sign requires both nonzero with identical sign. Compute the
ordinary median of ordered shifts. Choose worst subset by greatest unrounded
shift, then earlier subset order.

### 8. Controlled decision

Complete every module. Evaluate every effective business predicate on unrounded
values. Preserve the declared module order for gate reporting. Count satisfied
gates and apply the effective request's controlled decision mapping.
