# Fixed-Effects OLS with Delete-One Jackknife

## Double-Demeaning Transformation

Given panel data with entities i and time periods t:
- For each variable v_it, compute:
  - v_bar_i = mean of v for entity i (across active observations)
  - v_bar_t = mean of v for period t (across active entities)
  - v_bar = grand mean of v across all active observations
- Transformed: v_tilde_it = v_it - v_bar_i - v_bar_t + v_bar

Repeat for the outcome and every predictor. The transformation is recomputed from scratch after every cluster deletion.

## OLS Without Intercept

Fit y_tilde = X_tilde * b + epsilon by OLS without an intercept column. The coefficient vector b has length equal to the number of predictors, in declared order.

## Delete-One-Cluster Jackknife

For G clusters in declared order:
1. Delete all rows belonging to cluster g.
2. Recompute the double-demeaned matrix using only the remaining rows.
3. Fit OLS without intercept.
4. Record b_-g (the coefficient vector from the delete-g fit).
5. For the target coefficient, compute percent change = 100 * abs((b_-g - b_full) / b_full).

## Jackknife Inference

For delete estimates b_-g and their mean bbar = (1/G) * sum_g(b_-g):
- SE_JK = sqrt((G-1)/G * sum_g((b_-g - bbar)^2))
- Bias-corrected coefficient: b_BC = G * b_full - (G-1) * bbar
- t_statistic = b_BC / SE_JK
- Two-sided p-value from Student-t distribution with G-1 degrees of freedom

## Extrema Selection

- Minimum delete coefficient: smallest coefficient, tie-broken by state code ascending
- Maximum delete coefficient: largest coefficient, tie-broken by state code ascending
- Most influential cluster: greatest absolute percent change, tie-broken by earlier cluster order

## Reliability-Weighted Variant

When reliability weights w_i are declared (e.g. sample_size):
- Apply weights in the OLS: Xw = diag(sqrt(w)) * X, yw = diag(sqrt(w)) * y
- Apply the same reliability weights throughout jackknife refits
- Weights are fixed per observation and do not change across deletions
