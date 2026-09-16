# Statistical Methods Reference

This document captures the reusable statistical building blocks shared across PHO protocol profiles. Each method is described with enough detail to implement correctly from scratch in a clean solver context.

## Linear Algebra Foundations

### Ordinary Least Squares (OLS)

Given design matrix X (n x k) and outcome vector y (n x 1):

b = (X'X)^(-1) * X'y

With residual e = y - Xb, classic variance:

V_OLS = s^2 * (X'X)^(-1) where s^2 = e'e / (n - k)

Two-sided Student-t: t = b_j / sqrt(V[j,j]) with n - k df.

### Weighted Least Squares (WLS)

Given positive weights w (n x 1):

Xw = diag(sqrt(w)) * X
yw = diag(sqrt(w)) * y
b = (Xw'Xw)^(-1) * Xw'yw

### HC3 Heteroskedasticity-Consistent Variance

With WLS in weighted space:

h_i = diag(Xw * (Xw'Xw)^(-1) * Xw')
ew_i = sqrt(w_i) * (y_i - X_i*b)
V_HC3 = (Xw'Xw)^(-1) * Xw' * diag(ew_i^2 / (1 - h_i)^2) * Xw * (Xw'Xw)^(-1)

### CR1 Cluster-Robust Variance

For ordered clusters g = 1..G, let Xw_g and ew_g be the rows in cluster g:

s_g = Xw_g' * ew_g

V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw'Xw)^(-1) * sum_g(s_g * s_g') * (Xw'Xw)^(-1)

Inference with two-sided Student-t and G-1 df.

### Clustered Standard Errors (Unweighted)

Same as CR1 but in unweighted space: X_g and e_g instead of Xw_g and ew_g.

V_cluster = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^(-1) * sum_g(s_g * s_g') * (X'X)^(-1)
where s_g = X_g' * e_g.

## Fixed Effects and Transformations

### Double-Demeaning (Two-Way Fixed Effects)

For each variable z_it:

1. Entity mean: zbar_i = mean_t(z_it)
2. Time mean: zbar_t = mean_i(z_it)
3. Grand mean: zbar = mean_{i,t}(z_it)
4. Transformed: ztilde_it = z_it - zbar_i - zbar_t + zbar

Solve OLS on transformed variables without intercept. On every refit (e.g., after deleting a cluster), recompute all means from the active dataset.

### Within Transformation (One-Way Fixed Effects)

ztilde_it = z_it - zbar_i

### Jackknife Variance

For G delete-one-cluster estimates b_-g and their mean bbar:

SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))
b_BC = G * b - (G-1) * bbar  (bias-corrected)

Test b/SE_JK with two-sided Student-t and G-1 df.

Percent change: 100 * abs((b_-g - b) / b)

## Ridge Regression

### Standard Ridge (Unweighted)

Minimize: mean((y - a - Xb)^2) + lambda * sum_j(b_j^2)

Center y by training mean. Keep intercept a unpenalized (a = mean(y) when all x are centered). Initialize b = 0.

Coordinate descent: for each feature j in declared order:
r_ij = y_i - a - sum_{l != j} x_il * b_l
b_j = sum_i(x_ij * r_ij) / (sum_i(x_ij^2) + n * lambda)

Stop when max absolute coefficient change < tolerance or sweep cap reached.

### Standardization

For ridge and elastic net (training-only):
mu_j = mean_i(x_ij) over training rows
sigma_j = std_i(x_ij) over training rows (population SD = sqrt(mean((x - mu)^2)), or sample SD with ddof=1 as specified)
z_ij = (x_ij - mu_j) / sigma_j (if sigma_j == 0, z_ij = 0)

Apply same mu_j and sigma_j to validation/test rows.

## Elastic Net (Weighted)

Minimize: sum_i w_i * (y_i - Z_i*b)^2 / (2 * sum_i w_i) + lambda * [alpha * sum_j |b_j| + (1-alpha)/2 * sum_j b_j^2]

where Z includes standardized continuous features and unstandardized indicators.

Cold-start all coefficients at zero. Intercept = training weighted mean of y (unpenalized).

Coordinate descent per cycle in declared feature order:
rho_j = sum_i w_i * Z_ij * (y_i - sum_{l != j} Z_il * b_l) / sum_i w_i
b_j = S(rho_j, lambda * alpha) / (1 + lambda * (1 - alpha))

Soft threshold: S(a, t) = sign(a) * max(|a| - t, 0)

Stop when max coefficient change < tolerance or sweep cap reached.

## Elastic Net (Unweighted)

Same as above with all w_i = 1. Objective:

SSE / (2n) + alpha * (rho * sum_j |beta_j| + 0.5 * (1-rho) * sum_j beta_j^2)

where rho is L1 ratio. Coordinate update:
beta_j = S(mean(x_j * r_partial), alpha * rho) / (mean(x_j^2) + alpha * (1 - rho))

## GMM (Generalized Method of Moments)

### First Step

Given instruments Z (n x L), regressors D (n x p), outcome y:

Residualize y, D, and Z against baseline terms (intercept + baseline X).

g(theta) = Z'(y - D*theta) / n

Weight = identity: W = I

theta_1 = (D'Z * Z'D)^(-1) * D'Z * Z'y

### Second Step

u = y - D*theta_1
For state clusters: s_g = Z_g' * u_g
S = sum_g(s_g * s_g') / n
W = pseudoinv(S) with relative singular-value cutoff

theta_2 = (D'Z * W * Z'D)^(-1) * D'Z * W * Z'y

### Hansen J Statistic

J = n * g(theta_2)' * W * g(theta_2)

### Difference GMM

For a change model with lagged instruments, each equation uses its own instrument set. Process equations independently then combine indirect effect via delta method:

theta = a * b
Var(theta) = b^2 * Var(a) + a^2 * Var(b) + 2ab * Cov(a,b)

## Wild Cluster Bootstrap

### PCG32 Generator

64-bit state, 32-bit output. Initialize:
increment = 2 * stream + 1
state = 0; advance once; state = (state + seed) mod 2^64

Advance:
old = state
state = (old * 6364136223846793005 + increment) mod 2^64
xorshifted = low32(((old >> 18) xor old) >> 27)
rot = old >> 59
output = rotate_right_32(xorshifted, rot)

Map output mod 6 to: [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]

### xorshift32 Generator

32-bit unsigned state. Each call:
x ^= x << 13; x &= 0xFFFFFFFF
x ^= x >> 17; x &= 0xFFFFFFFF
x ^= x << 5; x &= 0xFFFFFFFF
return x

For wild bootstrap signs: low bit 1 → +1, low bit 0 → -1.
Or: odd state_code → +1, even state_code → -1 (depending on protocol).

### Bootstrap Procedure

1. Fit unrestricted model, compute target coefficient b and t = b / SE_CR1
2. Fit restricted model (without target variable), obtain fitted values yhat_r and residuals e_r
3. For each replicate B:
   - Draw cluster-level weights/signs
   - y* = yhat_r + e_r * weight
   - Fit unrestricted model on (X, y*)
   - Compute t* = b* / SE*_CR1
4. p-value = (1 + count(|t*| >= |t|)) / (1 + B)  [absolute/two-sided]
   or p-value = (1 + count(t* >= t)) / (1 + B)  [one-sided, depending on protocol]

### Quantile Computation

Nearest-rank (one-based): for sorted x[1..B] and probability p:
index = min(B, ceil(p * B))
return x[index - 1] (zero-based)

Type-7 (default R style): for sorted x[0..B-1] and probability p:
h = (B - 1) * p
j = floor(h)
gamma = h - j
return (1 - gamma) * x[j] + gamma * x[j+1] (if j+1 < B, else x[B-1])

## Conformal Inference

### Split Conformal

1. Split data into proper training I1, calibration I2, test I3
2. Fit model on I1, predict on all
3. Sort calibration absolute residuals: scores = sorted(|y_i - yhat_i| for i in I2)
4. m = len(scores)
5. r = min(m, ceil((m+1) * (1 - alpha)))
6. q = scores[r-1] (one-based r)
7. Prediction interval for test point i: [yhat_i - q, yhat_i + q] (inclusive)

### Grouped Split Conformal

Calibration group = group(s) with most rows, tie by ascending group name.
For each outer fold: proper_training = all groups except test and calibration.

### Cross-Fold Conformal

Calibrate on OOF residuals from all folds except the one being tested.

### State-Grouped Conformal

Reduce calibration residuals to one maximum absolute residual per calibration state.
k = min(m_states, ceil((m_states+1) * coverage))
q = k-th state's maximum absolute residual (one-based)

## PCA (Principal Component Analysis)

### Covariance PCA

1. Standardize columns: z_j = (x_j - mu_j) / sigma_j (sample SD)
2. C = Z'Z / (n-1)  [or Z'Z/n for population covariance]
3. Eigendecompose C

### Jacobi Eigendecomposition (Symmetric)

Repeat until max |off-diagonal| < tolerance or step cap:
1. Find (p, q) with largest |C[p,q]| for p < q; tie by lower p, then lower q
2. theta = (C[q,q] - C[p,p]) / (2 * C[p,q])
3. t = sign(theta) / (|theta| + sqrt(1 + theta^2))
    [use sign_nonnegative: t = 1/(|theta| + sqrt(1+theta^2)) if theta >= 0, -1/(|theta| + sqrt(1+theta^2)) if theta < 0]
4. c = 1 / sqrt(1 + t^2); s = t * c
5. Apply rotation to C and eigenvectors

### Ordering and Orientation

- Sort eigenvalues descending
- If eigenvalues tie, preserve original column order
- For each retained eigenvector, flip sign so its earliest element with maximum absolute value is positive
- Scores = Z * oriented_loadings

### Variance Explained

explained_ratio_j = lambda_j / sum(lambda)
cumulative = sum_{l=1..k} explained_ratio_l

## K-Means Clustering

### Deterministic Farthest-First Initialization

1. First center = entity with smallest ASCII/lexicographic code
2. Each subsequent center = entity maximizing minimum squared-Euclidean distance to existing centers; tie by entity code

### Lloyd Iteration

Repeat until assignments unchanged or iteration cap:
1. Assign each point to nearest center by squared Euclidean distance; tie to lower cluster id
2. Update centers as arithmetic mean of members
3. If a cluster becomes empty: select the entity farthest from its assigned center (ASCII-first among ties); move it; recompute.

### Canonicalization

After convergence, reorder cluster ids by centroid coordinates (lexicographic), maintaining original ids as a stable mapping.

### Silhouette Score

For point i in cluster C_I:
a(i) = mean distance to points in C_I
b(i) = min_{J != I} mean distance to points in C_J
s(i) = (b(i) - a(i)) / max(a(i), b(i))  [singleton cluster: s(i) = 0]
Average over all points.

### Adjusted Rand Index

Given two partitions U and V with contingency table n_ij:

a_i = sum_j n_ij (row sums for U)
b_j = sum_i n_ij (col sums for V)

expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)
maximum = (sum_i C(a_i, 2) + sum_j C(b_j, 2)) / 2

ARI = (sum_ij C(n_ij, 2) - expected) / (maximum - expected)

where C(x, 2) = x * (x-1) / 2.

For stability alignment: find permutation mapping refit ids to reference ids maximizing total agreement; tie to lexicographically smallest mapped-id vector.

## Mediation Sensitivity (Partial R^2)

Given baseline:
- a = path-a coefficient (exposure -> mediator)
- b = path-b coefficient (mediator -> outcome)
- SE_b = standard error of b
- df = residual degrees of freedom of outcome model

magnitude = SE_b * sqrt(df * rY * rM / (1 - rM))
where rY = outcome confounder partial R^2, rM = mediator confounder partial R^2.

For direction s (POSITIVE: s=+1, NEGATIVE: s=-1):
adjusted_b = b - s * magnitude
adjusted_indirect = a * adjusted_b
adjusted_direct = total - adjusted_indirect
proportion = adjusted_indirect / total

Tipping point: solve for r^2 where b - SE_b * sqrt(df * r^2 * r^2 / (1 - r^2)) = 0 (equal-strength case rY = rM = r^2).

## Source Perturbation

### Exhaustive Enumeration

For M entities with alternate source, enumerate all 2^M subsets.
For each mask m from 0 to 2^M-1:
- Replace entity j iff (m >> j) & 1 is nonzero
- Refit model

shift = 100 * abs((b_mask - b_baseline) / b_baseline)

### Exact Shapley Values

For ordered entity j:
phi_j = sum_{S subset without j} |S|! * (M-|S|-1)! / M! * [b(S union {j}) - b(S)]

Verify: sum_j phi_j = b(all_replaced) - b(none_replaced)

## Trajectory PCA

### Variable-Major/Time-Major Feature Construction

For variables v_1..v_V and time blocks t_1..t_T, construct columns in order:
v_1_t_1, v_1_t_2, ..., v_1_t_T, v_2_t_1, ..., v_V_t_T

### Log Features

When feature semantics declares log transformation (e.g., log(diagnosed_diabetes_sample_size), log_income):
Use natural log of the unscaled underlying value.

## Panel Construction

### Adjacent-Change Panel

For entity i with observations across consecutive periods:
row for end period t: outcome_change = y_it - y_{i,t-1}, plus analogous changes for all dynamic variables.

Lagged levels come from the base period (t-1 or earlier as declared).

Reference indicators: for RUCC, create dummies RUCC_2 through RUCC_9 with RUCC_1 as reference.
For end-period dummies: indicator for each end year except the reference.

### Balanced Panel

Only include entities that are complete (all required variables nonmissing) in every panel year.
