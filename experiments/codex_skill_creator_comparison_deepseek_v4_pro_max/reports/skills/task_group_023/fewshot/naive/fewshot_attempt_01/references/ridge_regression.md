# Ridge Regression with Nested Cross-Validation

## Folds

- Outer loop: hold out one group at a time in declared group order.
- Inner loop (within each outer training set): hold out each remaining group once in the same order.

## Training-Only Standardization

For each fit, using only training rows:
1. Compute training mean mu_j and training sample standard deviation sigma_j for each feature j.
   - sigma_j = sqrt(sum_i(x_ij - mu_j)^2 / n_train)  [population SD, ddof=0 unless otherwise specified]
   - If sigma_j == 0, set sigma_j = 1 to avoid division by zero.
2. Standardize: z_ij = (x_ij - mu_j) / sigma_j for training rows.
3. Apply the same mu_j and sigma_j to validation/test rows.
4. Center the training outcome: yc_i = y_i - mean_train(y).
5. Do not scale the outcome.

## Coordinate Descent Solver

Objective: minimize mean((yc - Xz * b)^2) + lambda * sum_j(b_j^2)  [no intercept column]
Or with intercept: minimize mean((yc - a - Xz * b)^2) + lambda * sum_j(b_j^2)

Algorithm:
1. Initialize all coefficients to 0. If including intercept a, initialize a = mean_train(yc).
2. For each feature j in declared order:
   - Compute partial residual r_i = yc_i - a - sum_{l != j} Xz_il * b_l
   - Compute rho_j = sum_i(Xz_ij * r_i) / n
   - Update b_j = rho_j / (sum_i(Xz_ij^2) / n + lambda)
3. If including intercept, update a = mean_train(yc - Xz * b).
4. After a full sweep over all features, check max absolute coefficient change.
5. Stop when max change < tolerance (typically 1e-6) or at sweep cap (typically 1000-2000).
6. Ties for stopping: use the earlier state.

## Lambda Selection

For each inner validation fold, pool all validation squared errors at the row level, compute RMSE = sqrt(SSE / n_val). Choose lambda with smallest unrounded inner RMSE. Tie-break: smaller lambda.

After selection, refit on all outer-training rows with the chosen lambda, and predict all outer test rows.

## Aggregation

Pool exactly one outer prediction per eligible row. Compute:
- pooled_rmse = sqrt(sum_i(y_i - yhat_i)^2 / n)
- pooled_mae = sum_i|y_i - yhat_i| / n
- pooled_q_squared = 1 - SSE_pooled / SST_full_sample
  where SST_full_sample = sum_i(y_i - mean_all(y))^2

## Weighted Variant

With observation weights w_i:
- Training means: mu_j = sum_i(w_i * x_ij) / sum_i(w_i)
- Training SD: sigma_j = sqrt(sum_i(w_i * (x_ij - mu_j)^2) / sum_i(w_i))
- Objective: sum_i(w_i * (yc_i - prediction_i)^2) / (2 * sum_i(w_i)) + lambda * sum_j(b_j^2)
- Rho_j = sum_i(w_i * Xz_ij * r_i) / sum_i(w_i)
- Update: b_j = rho_j / (sum_i(w_i * Xz_ij^2) / sum_i(w_i) + lambda)
- Pooled RMSE/MAE are unweighted on test rows unless otherwise specified
