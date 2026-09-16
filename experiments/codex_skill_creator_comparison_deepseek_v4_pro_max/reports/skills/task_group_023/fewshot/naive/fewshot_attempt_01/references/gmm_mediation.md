# Difference GMM Mediation

## Data Construction

From a balanced panel with entities i and periods t:
1. Create adjacent-change rows: for each entity and each pair of consecutive periods, compute:
   - delta_y = y_{t} - y_{t-1}
   - delta_X = X_{t} - X_{t-1}
   - Retain baseline terms (time-invariant or reference-period values) and period indicators.
2. Order rows by entity code then end-period.
3. Lag structure: use levels from t-2 as instruments for changes from t-1 to t (two-period lag).

## Two-Step GMM Estimator

### Residualization
Within each estimation, residualize the outcome, dynamic regressors, and instruments against the baseline terms (intercept, baseline controls, period indicators). Work with the residualized variables.

### First Step
- Moment conditions: g(theta) = Z' (y - D theta) / n
- Weight matrix: W = I (identity)
- Minimize g(theta)' W g(theta)
- This is 2SLS with instruments Z: theta_1 = (D' Z (Z'Z)^{-1} Z' D)^{-1} D' Z (Z'Z)^{-1} Z' y
- Residuals: u = y - D theta_1

### Second Step
- Cluster scores: S_g = Z_g' u_g for each cluster g
- S = sum_g(S_g * S_g') / n
- W = Moore-Penrose pseudoinverse of S
- Apply declared relative singular-value cutoff: svd(S), keep singular values >= cutoff * max_singular_value
- theta_2 = (D' Z W Z' D)^{-1} D' Z W Z' y

### Hansen J Statistic
J = n * g(theta_2)' W g(theta_2)
Under the null, J ~ chi-squared with (L - K) degrees of freedom, where L = number of instruments and K = number of regressors.

## Multiple Equations

For mediation analysis with two equations (path a and path b):

### Path-a equation
- Outcome: delta_mediator
- Regressors: delta_exposure, plus controls
- Instruments: lagged_exposure, lagged_mediator, plus their interactions with period indicators as declared

### Path-b equation (direct model)
- Outcome: delta_outcome
- Regressors: delta_exposure, delta_mediator, plus controls
- Instruments: lagged_exposure, lagged_mediator, plus interactions

### Cross-Equation Inference for Indirect Effect
- Indirect effect: theta_indirect = a * b
  where a = path-a coefficient on exposure, b = path-b coefficient on mediator
- Variance: Var(theta_indirect) = b^2 * Var(a) + a^2 * Var(b) + 2*a*b * Cov(a, b)
- Cov(a, b) uses the cross-equation cluster score product:
  Cov = correction_factor * (X_a' Z W Z' X_a)^{-1} X_a' Z W * sum_g(Z_g' u_a_g * u_b_g' Z_g) * W Z' X_b (X_b' Z W Z' X_b)^{-1}  [a,b element]
- The correction_factor may be declared (e.g. to account for finite-sample adjustment).

### First-Stage Partial F Statistics
For each equation separately:
1. Fit the full first-stage regression (all instruments).
2. Fit a reduced regression excluding the excluded instruments.
3. F = ((SSE_reduced - SSE_full) / (df_reduced - df_full)) / (SSE_full / df_full)
4. Report for each endogenous variable.

## Delete-One-State Diagnostics

For each state in ascending order:
1. Remove all rows belonging to that state.
2. Rebuild the change rows from scratch using only the remaining balanced entities.
3. Re-estimate both equations (first step, second step, cross-equation inference).
4. Report: omitted_state, n (remaining observations), indirect_effect, direct_poverty (or direct_exposure coefficient).

## Student-t Inference

Use two-sided Student-t with G-1 degrees of freedom (where G = number of clusters) for all coefficient tests, confidence intervals, and p-values.
