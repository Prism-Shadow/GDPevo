# Statistical Methods Reference

This document describes every statistical method used in PHO algorithmic audits.
Implement exactly as specified; do not substitute library defaults for declared
hyperparameters, random streams, or tie-breaking rules.

## Module Execution Order

Every audit request specifies a module execution order. Complete modules in that
exact sequence. Each module is independent: it uses its own cohort, its own
hyperparameters, and (when applicable) its own random stream initialized from
the declared seed.

## Fixed Effects OLS with Cluster Jackknife

### Demeaning
For entity i at time t with variable x_it:
- Entity mean: xbar_i = mean over t of x_it
- Time mean: xbar_t = mean over i of x_it
- Grand mean: xbar = mean over (i,t) of x_it
- Transformed: x~_it = x_it - xbar_i - xbar_t + xbar

Fit OLS on transformed variables without an intercept, in declared predictor
order. A deletion removes the whole cluster (e.g., one state), recomputes every
mean, and refits from scratch.

### Jackknife Inference
With G delete estimates b_-g and mean bbar:
- SE_JK = sqrt((G-1)/G * sum_g ((b_-g - bbar)^2))
- b_BC = G*b - (G-1)*bbar (bias-corrected)
- t = b_BC / SE_JK, two-sided Student-t with G-1 degrees of freedom

Select extrema (min/max delete coefficient) by coefficient value, then entity code.

## Ridge Regression

### Standardization
Within each fit, compute training-only feature means and sample standard deviations
(ddof=1). Apply those moments to validation/test rows. Center the outcome using the
training mean; do not scale y.

### Solver
Minimize mean((y - a - Xb)^2) + lambda * sum_j(b_j^2).

Update with cyclic coordinate descent in declared feature order:
- r_ij = y_i - a - sum_{l != j} X_il * b_l
- b_j = sum_i X_ij * r_ij / (sum_i X_ij^2 + n * lambda)

Start at b=0, intercept a = training y mean. Stop after a full sweep when max
coefficient change < effective tolerance or at sweep cap.

### Cross-Validation
Outer folds hold out one cluster at a time in declared group order. Within each
outer training set, inner folds hold out each remaining group in the same order.
For each lambda, pool inner validation squared errors across rows then take RMSE.
Select the smallest unrounded RMSE; break ties toward the smaller lambda. Refit
on all outer-training rows and predict held-out rows.

### Pooled Metrics
Pool exactly one OOF prediction per eligible row. Compute:
- RMSE = sqrt(mean(residual^2))
- MAE = mean(|residual|)
- Q^2 = 1 - SSE / SST (SST uses the full-sample outcome mean)
- R^2 (alternative notation) = 1 - SSE / sum_i(y_i - full_mean)^2

## Elastic Net

### Standardization
Same as ridge: training-only weighted mean and weighted population SD
(sigma_j = sqrt(sum_i w_i*(x_ij - mu_j)^2 / sum_i w_i)). Keep intercept
unpenalized. When weights are absent, all w_i = 1.

### Objective
Minimize sum_i w_i*(y_i - Z_i*b)^2 / (2*sum_i w_i) + lambda * (alpha*sum_j|b_j| + (1-alpha)*(sum_j b_j^2)/2).

### Solver
Cold-start all coefficients at zero for every penalty. Never warm-start.
In cyclic feature order:
- rho_j = sum_i w_i * Z_ij * (y_i - sum_{l!=j} Z_il*b_l) / sum_i w_i
- b_j = S(rho_j, lambda*alpha) / (1 + lambda*(1-alpha))
where S(a,t) = sign(a) * max(|a|-t, 0)

Stop after a complete cycle when max coefficient change < effective tolerance or
at cycle cap.

### Cross-Validation and Selection
Pool inner validation squared errors before RMSE (not mean of fold RMSEs).
Select smallest unrounded RMSE, then smaller alpha, then smaller l1_ratio.
Refit on all outer-training rows.

## Weighted Least Squares and Robust Standard Errors

### WLS with Fixed Weights
For design X, outcome y, positive weights w:
- Xw = diag(sqrt(w)) * X
- yw = diag(sqrt(w)) * y
- b = (Xw'Xw)^(-1) * Xw'yw in declared column order

### HC3
With h_i = diag_i(Xw * (Xw'Xw)^(-1) * Xw') and ew_i = sqrt(w_i)*(y_i - X_i*b):
- V_HC3 = (Xw'Xw)^(-1) * Xw' * diag(ew_i^2 / (1-h_i)^2) * Xw * (Xw'Xw)^(-1)
- Two-sided Student-t with n-k residual degrees of freedom

### CR1 (Cluster-Robust)
For ordered clusters g and scores s_g = Xw_g' * ew_g:
- V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw'Xw)^(-1) * sum_g(s_g * s_g') * (Xw'Xw)^(-1)
- Two-sided Student-t with G-1 degrees of freedom

## Two-Way Fixed Effects Demeaning for Panel

For each variable, subtract its entity mean and time mean, then add back the
grand mean. The intercept is omitted from the demeaned regression.

## Difference GMM

### Setup
Create adjacent-change rows in entity then end-period order. Variables are
expressed as first differences (y_it - y_(i,t-1)). Use the declared lag
structure for instruments.

### Two-Step Estimation
First step: g(theta) = Z'(y - D*theta)/n with identity weight.
Compute state-cluster scores s_g = Z_g' * u_g and S = sum_g(s_g * s_g')/n.
Second step: use Moore-Penrose inverse of S with the declared relative
singular-value cutoff. Compute Hansen J = n * g(theta)' * W * g(theta).

### Jackknife Bias Correction
With G state deletions: theta_bc = G*theta_full - (G-1)*mean(theta_delete).

### Indirect Effect (Mediation)
For theta = a*b: Var(theta) = b^2*Var(a) + a^2*Var(b) + 2ab*Cov(a,b).
Confidence intervals use Student-t with cluster degrees of freedom.

### First-Stage Partial F
Compute from full-versus-restricted residual sums of squares using effective
instrument counts.

## PCG32 Wild Cluster Bootstrap

### PRNG
Use unsigned 64-bit state with 32-bit output.
- increment = 2*stream + 1
- Initialize state to 0, advance, add initialization value modulo 2^64, advance.
- Each advance: old = state; state = old * 6364136223846793005 + increment mod 2^64
- xorshifted = low32(((old >> 18) xor old) >> 27)
- rot = old >> 59
- output = rotate_right_32(xorshifted, rot)

Map output modulo 6 in order to weights: [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].

### Bootstrap Procedure
Fit the unrestricted model and compute CR1 for the target coefficient. Fit the
restricted model (without the target coefficient) and retain restricted fitted
values and residuals. For each replicate:
1. Draw one weight per cluster in entity-code order
2. y* = restricted_fit + restricted_residual * cluster_weight
3. Refit unrestricted model, recompute CR1, and studentize

### Checkpoints and Aggregation
Record checkpoints after their completed replicate without resetting the stream.
Count |t*| >= |t_observed|; report p = (1+count)/(1+B).
Compute quantiles via nearest-rank: for probability p and sorted values x,
output x[min(B, ceil(p*B)) - 1] using one-based rank.

## XorShift32 Wild Cluster Bootstrap

### PRNG
Unsigned 32-bit state. Each call:
- x ^= x << 13
- x ^= x >> 17
- x ^= x << 5
Mask to unsigned 32 bits after each xor.

Maintain one continuous stream. Draw once per cluster in ascending cluster order
per replicate; map low bit 1 to +1, 0 to -1.

### Bootstrap Procedure
Same wild bootstrap structure as above but with xorshift32 weights and absolute
t-statistic exceedance counting.

### Quantiles (Type 7)
For sorted x of length B and probability p:
- h = (B-1) * p
- j = floor(h)
- gamma = h - j
- quantile = (1-gamma) * x[j] + gamma * x[j+1] (zero-based indexing)

## Restricted-Null Paired Bootstrap

For paired equations, draw signs once per cluster and reuse the same sign across
all equations. Fit restricted models for each target independently.
Use two-sided absolute exceedances with plus-one p = (count+1)/(B+1).

## PCA (Principal Component Analysis)

### Covariance PCA
Build columns in declared variable-major/time order. Standardize each column
by its sample standard deviation (ddof=1 for states, ddof=0 for counties/countries
per the effective request). Form C = Z'Z/(n-1) or Z'Z/n per the effective divisor.

### Eigenvalue Decomposition
Use symmetric Jacobi iteration:
1. Select the largest absolute upper-triangle off-diagonal. On ties, lower row
   then lower column.
2. tau = (Aqq - App) / (2*Apq)
3. t = sign_nonnegative(tau) / (|tau| + sqrt(1+tau^2))
4. c = 1/sqrt(1+t^2), s = t*c
5. Rotate A and eigenvectors
6. Stop at effective off-diagonal tolerance or step cap

### Ordering and Orientation
Order eigenvalues descending. On ties, the component associated with the larger
original diagonal index comes first.

Flip each eigenvector (loading) so the earliest entry with the maximum absolute
value is positive. Compute scores as Z times oriented loadings.

### Explained Variance
Ratio = eigenvalue / sum(all eigenvalues).
Cumulative is the running sum.

## K-Means Clustering

### Initialization (Deterministic Farthest-First)
1. First center: the ASCII-first entity.
2. Each next center: the entity maximizing distance to its nearest existing
   center. Break ties by entity code.

### Lloyd's Algorithm
- Assign each point to the nearest center (squared Euclidean distance). Break
  ties by lower cluster id.
- Update centers to arithmetic means of members.
- Stop when assignments are unchanged or at the effective iteration cap.
- For empty clusters: move the ASCII-first entity among those farthest from
  their assigned center, then continue.

### Canonicalization
After convergence, reassign cluster ids by sorting centroids on their coordinate
values in dimension order, then by working id for any remaining ties.

### Silhouette
For each point i: a_i = mean distance to points in same cluster, b_i = minimum
mean distance to points in any other cluster. s_i = (b_i - a_i)/max(a_i,b_i).
Singleton cluster: s_i = 0. Average s_i across all points.

## Adjusted Rand Index (ARI)

Given two clusterings with contingency table n_ij:
- sum_ij C(n_ij, 2) is the number of agreed pairs
- expected = sum_i C(a_i,2) * sum_j C(b_j,2) / C(n,2)
- ARI = (sum_ij C(n_ij,2) - expected) / (0.5*(sum_i C(a_i,2) + sum_j C(b_j,2)) - expected)

Align refit labels to reference labels by the permutation maximizing matches;
break ties by the lexicographically smallest mapped-id vector.

## Split Conformal Prediction

### Procedure
For each outer fold, use the declared calibration fold (selecting by the
effective rule: greatest row count then ascending group name, or cyclic
index-based). Fit the model on proper training folds, predict calibration
rows, and sort absolute calibration residuals.

### Interval Construction
With m calibration scores and effective miscoverage alpha:
- r = min(m, ceil((m+1)*(1-alpha))) using one-based rank
- q = score[r]
- Intervals: prediction +/- q (inclusive)

### Aggregation
Compute per-fold coverage (fraction of test rows where true value falls within
intervals) and mean width. Pool for aggregate coverage (total covered / total
test rows) and weighted mean width.

For state-grouped conformal: reduce calibration residuals to one maximum
absolute residual per calibration state before ranking.

## Mediation Sensitivity Surface (Partial R^2)

### Baseline Quantities
From the primary mediation model: path-a coefficient a, path-b coefficient b,
path-b standard error SE_b, and residual degrees of freedom df.

### Magnitude
magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
where rY = r^2_outcome_confounder, rM = r^2_mediator_confounder.

### Adjustment
For each direction (NEGATIVE: subtract, POSITIVE: add):
- adjusted_b = b - sign * magnitude
- adjusted_indirect = a * adjusted_b
- adjusted_direct = total_effect - adjusted_indirect
- proportion = adjusted_indirect / total_effect

Enumerate the complete surface in declared R^2 and direction order.
Equal-strength tipping R^2: the smallest positive root where adjusted_indirect
crosses zero for equal rY = rM.

## Exhaustive Source Perturbation

### Enumeration
For m entities with an alternate source available, enumerate all 2^m combinations.
For each bitmask, replace entity j iff mask & (1<<j) is nonzero. Retain fixed
weights and design; refit the model and recompute inference.

### Aggregation
Relative shift = 100 * |b_mask - b_zero| / |b_zero|.
Report by-popcount stratum summaries and identify the maximum-shift scenario
(greatest unrounded shift, then smaller mask).

### Exact Shapley Attribution
For ordered entity j:
phi_j = sum_{S not containing j} |S|! * (m-|S|-1)! / m! * (b(S ∪ {j}) - b(S))

Verify sum_j phi_j = b(all replacements) - b(no replacements).

## Source Group Perturbation

For each declared source group and each outer fold, remove the group's terms
while reusing the full-model selected hyperparameters without retuning. Apply
the same preprocessing and solver on remaining terms. Compare outer-fold RMSE
values; deterioration = new pooled RMSE - reference pooled RMSE. Rank groups
by decreasing unrounded deterioration, then declared group order.

## Publication Counts and Cohort Construction

### Counting
"Selected" records: the resolved final records, counted per year before
completeness exclusions. A suppressed or null resolved record still counts
as selected but is incomplete for cohort membership.

### Completeness
Apply the effective completeness predicate (e.g., basic-complete requires
non-null values for declared core fields). Entity-year observations satisfying
all conditions form the base for cohort construction.

### Cohort Definitions
- Primary/Reference-Year: complete in the declared reference year.
- Balanced Panel: complete in every declared study year.
- Broad: complete for outcome and all declared features in the reference year.
- Dual-Source/Strict: complete for outcome and both primary and parallel
  exposure sources in every analysis year.
- Machine-Learning: primary-cohort members also complete for declared additional
  measures.

### Exclusions
Report excluded entity codes sorted ascending. The exclusion set is the
universe minus the cohort members — list only entities in the universe
that failed the completeness predicate.
