## PHO_COUNTY_MEDIATION_TRANSPORT_V1

County-level mediation transport audit. Tests whether a focal exposure (e.g.
poverty) mediates through a specified mediator (e.g. physical inactivity) to an
outcome (e.g. adult obesity), using four-year county panels, difference-GMM
mediation, nested state-out ridge prediction, wild cluster bootstrap,
state-grouped conformal calibration, partial-R2 sensitivity surface, and state
trajectory PCA clustering.

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

### 1. Publication and linked cohorts

Filter each source by effective request fields. Select one record per declared
entity-time-measure key using ordered release priority (greatest revision, then
latest release timestamp, then lowest record id).

Count selected publications before analytic completeness exclusions when
requested. Suppressed or null selected health records remain publication
evidence but are incomplete.

Construct primary (reference-year basic-complete), balanced-panel (all four
years), and machine-learning (primary plus additional socioeconomic fields)
cohorts from effective nonmissing and validity predicates. Preserve declared
entity and state order.

### 2. Primary mediation models

Build total-effect, path-a, and direct/path-b OLS designs from effective
exposure, mediator, outcome, covariates, transformations, references, and
column order. Use the unrounded fitted objects as the shared source for
downstream bootstrap and sensitivity modules.

The total-effect model regresses outcome on exposure and all primary terms.
Path-a regresses mediator on exposure and all primary terms. The direct model
regresses outcome on exposure, mediator, and all primary terms. Path-b
coefficient is from the direct model's mediator term.

### 3. Difference-GMM mediation

Create adjacent-change rows in entity then end-period order using the effective
lag structure and equation bindings. For each equation use W = (Z'Z)^-1 and
beta = (X'Z W Z'X)^-1 X'Z W Z'y.

With residual u and cluster score q_g = Z_g' u_g, use the registered
finite-sample cluster sandwich. For two equations, use the corresponding
cross-cluster score product for covariance.

For indirect effect theta = a * b: Var(theta) = b^2 * Var(a) + a^2 * Var(b)
+ 2ab * Cov(a,b). Use Student-t inference with cluster degrees of freedom.

Compute first-stage partial F from full-versus-reduced residual sums of squares
using effective instrument counts.

For every delete-state diagnostic, rebuild rows and refit all affected
equations from scratch in state order.

### 4. Nested state-out ridge

Use effective feature arrays in exact order. Within every fit, standardize from
training arithmetic means and population standard deviations, with a unit
divisor for zero variance. Apply those moments to held-out rows.

Fit ridge with unpenalized intercept, minimizing training SSE plus lambda times
squared non-intercept norm.

Outer validation leaves one state out. Each inner validation leaves one
remaining state out. Pool county squared errors before RMSE.

Select the smallest unrounded inner RMSE, breaking equality toward the smaller
penalty. Refit on all outer-training rows and retain complete aligned grids and
outer diagnostics. Aggregate OOF metrics from the single prediction assigned to
every eligible row.

### 5. Paired state wild bootstrap

For each target, fit the restricted model with only that target removed. Form
synthetic outcomes from restricted fitted values plus cluster-weighted
restricted residuals, then refit unrestricted models and recompute CR1 t
statistics.

Use unsigned xorshift32: x xor= x << 13, x xor= x >> 17, x xor= x << 5,
masking to 32 bits after each operation. Map odd state to +1 and even state to
-1.

Maintain one continuous stream. Draw once per state in ascending state order per
replicate and reuse the same state sign across the paired equations.

Use two-sided absolute exceedances with plus-one p = (count+1)/(B+1). Use
nearest-rank order statistics for declared probabilities and bootstrap-t
inversion with the observed standard error. Record checkpoints only after the
listed replicate is complete, using the current PRNG state and that replicate
statistics.

### 6. State-grouped conformal

Index states in ascending order and assign cyclic partitions by index modulo the
effective partition count (typically 5).

For each test partition, use the registered preceding calibration partition and
remaining partitions for proper training.

Reduce calibration residuals to one maximum absolute residual per calibration
state. Use k = min(m, ceil((m+1) * coverage)) and the one-based kth state
maximum.

Build symmetric inclusive intervals. Aggregate county coverage and width by
cycle and state, using declared order for worst-state selection.

### 7. Partial-R2 mediation sensitivity

From unrounded baseline a, b, SE_b, and residual df, compute magnitude = SE_b *
sqrt(df * rY * rM / (1 - rM)).

For each declared direction use adjusted_b = b - sign * magnitude,
adjusted_indirect = a * adjusted_b, adjusted_direct = total - adjusted_indirect,
and proportion = adjusted_indirect / total.

Enumerate the complete effective surface in declared R2 and direction order.
Compute the equal-strength positive tipping root from unrounded inputs.

### 8. State trajectory PCA clustering

Aggregate effective balanced-panel measures to state-period means in declared
feature order. Standardize across states with sample standard deviations and use
covariance Z'Z/(G-1).

Sort eigenpairs descending. Orient each eigenvector so the earliest
maximum-absolute loading is positive. Score with the oriented loadings.

Run deterministic farthest-first Lloyd k-means using the effective cluster count
(typically 3), lower cluster id on assignment equality, arithmetic centroid
updates, unchanged-label plus registered center-tolerance convergence, and the
registered iteration cap.

For every leave-period stability fit, rebuild standardization, PCA orientation,
seeds, and clusters from scratch. Compare labels with adjusted Rand index.

### 9. Controlled precedence

Complete every evidence module first. Evaluate effective business predicates on
unrounded values. Count supported predicates and return the first applicable
controlled class in the effective precedence order.
