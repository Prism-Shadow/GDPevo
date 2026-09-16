# Elastic Net with Nested Cross-Validation

## Folds and Standardization

Same fold structure and training-only standardization rules as ridge regression. See [ridge_regression.md](ridge_regression.md).

## Objective

Minimize: sum_i(w_i * (yc_i - prediction_i)^2) / (2 * sum_i(w_i)) + lambda * [alpha * sum_j|b_j| + (1-alpha)/2 * sum_j(b_j^2)]

When weights are uniform, the denominator 2n is used.

## Coordinate Descent Updates

Intercept (unpenalized): a = mean_train(yc - Xz * b)

For each penalized coefficient j in declared order:
- rho_j = sum_i(w_i * Xz_ij * r_partial_i) / sum_i(w_i)
  where r_partial_i = yc_i - a - sum_{l != j} Xz_il * b_l
- denom = sum_i(w_i * Xz_ij^2) / sum_i(w_i) + lambda * (1 - alpha)
- b_j = S(rho_j, lambda * alpha) / denom
  where S(a, t) = sign(a) * max(|a| - t, 0)

## Solver Settings

- Cold-start all coefficients at 0 for every (lambda, alpha, l1_ratio) combination. Never warm-start between penalties.
- Intercept initialized to training outcome mean.
- Stop after a complete cycle when max absolute coefficient change < tolerance (typically 1e-6) or at sweep cap.
- Do not penalize the intercept.

## Grid Selection

Traverse the declared grid in outer then inner order. For each candidate (alpha, l1_ratio):
1. For each inner fold, fit on inner-training rows, predict inner-validation rows.
2. Pool all inner validation squared errors across folds, compute RMSE.
3. Select the combination with smallest unrounded inner RMSE.
4. Tie-break: smaller alpha, then smaller l1_ratio.

## Nonzero Count

After selection and outer refit, count coefficients with absolute value > numerical cutoff (typically 1e-8). The intercept is not counted.

## Outer Aggregation

Same as ridge: pool one prediction per eligible row, compute unweighted RMSE, MAE, and R^2 = 1 - SSE / sum_i(y_i - mean_all(y))^2.

## Predicted Values for Downstream Use

When conformal modules reuse elastic-net outer predictions, use the predictions from the selected-penalty outer refits in the original row order. These are the same predictions used to compute pooled OOF metrics.
