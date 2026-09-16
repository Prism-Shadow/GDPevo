#!/usr/bin/env python3
"""Ridge regression via coordinate descent with training-only standardization.

PHO audits use ridge in nested CV patterns:
- Leave-one-census-division-out (train_001)
- Leave-one-state-out (train_002)
- With reliability weights (train_004 uses elastic net; train_003 uses PCA)

Coordinate descent (one-at-a-time) with fixed intercept handling:
- Center outcome, keep intercept unpenalized.
- Initial coefficients = 0.
- Cycle in declared feature order.
- Update: b_j = sum_i x_ij * r_ij / (sum_i x_ij^2 + n * lambda)
  where r excludes feature j.
- Stop when max coefficient change < tolerance or sweep cap reached.
"""

import math
from typing import Optional


def standardize_training(X_train):
    """Compute training means and sample SDs (ddof=1). Return (X_scaled, means, sds)."""
    n = len(X_train)
    p = len(X_train[0])
    means = [sum(row[j] for row in X_train) / n for j in range(p)]
    sds = []
    for j in range(p):
        var = sum((row[j] - means[j]) ** 2 for row in X_train) / (n - 1)
        sds.append(math.sqrt(var) if var > 1e-15 else 1.0)
    X_scaled = [[(row[j] - means[j]) / sds[j] for j in range(p)] for row in X_train]
    return X_scaled, means, sds


def apply_standardization(X, means, sds):
    """Apply precomputed means and SDs to rows."""
    p = len(X[0])
    return [[(row[j] - means[j]) / sds[j] for j in range(p)] for row in X]


def ridge_coordinate_descent(X, y, lambda_penalty, tol=1e-10, max_sweeps=10000,
                              initial_coef=None):
    """Coordinate-descent ridge regression.

    Args:
        X: feature matrix (n x p), already standardized if needed.
        y: outcome vector (n).
        lambda_penalty: ridge penalty.
        tol: convergence tolerance on max coefficient change.
        max_sweeps: maximum sweeps through all features.

    Returns:
        (coefficients, intercept, n_sweeps)
    """
    n = len(y)
    p = len(X[0])

    # Center outcome
    y_mean = sum(y) / n
    y_centered = [yi - y_mean for yi in y]

    # Initialize coefficients
    if initial_coef is None:
        coef = [0.0] * p
    else:
        coef = list(initial_coef)

    # Precompute column sums of squares
    x2_sums = [sum(X[i][j] ** 2 for i in range(n)) for j in range(p)]

    # Precompute full residuals initially
    residuals = list(y_centered)

    for sweep in range(max_sweeps):
        max_change = 0.0
        for j in range(p):
            # Add feature j's contribution back to residuals
            for i in range(n):
                residuals[i] += coef[j] * X[i][j]

            # Compute numerator: sum_i x_ij * r_ij
            num = sum(X[i][j] * residuals[i] for i in range(n))
            denom = x2_sums[j] + n * lambda_penalty

            new_coef = num / denom if denom > 0 else 0.0

            # Remove new contribution
            for i in range(n):
                residuals[i] -= new_coef * X[i][j]

            change = abs(new_coef - coef[j])
            max_change = max(max_change, change)
            coef[j] = new_coef

        if max_change < tol:
            return coef, y_mean, sweep + 1

    return coef, y_mean, max_sweeps


def ridge_predict(X, coef, intercept):
    """Predict: y = X * coef + intercept."""
    return [sum(X[i][j] * coef[j] for j in range(len(coef))) + intercept for i in range(len(X))]


def rmse(y_true, y_pred):
    """Root mean squared error."""
    n = len(y_true)
    return math.sqrt(sum((y_true[i] - y_pred[i]) ** 2 for i in range(n)) / n)


def mae(y_true, y_pred):
    """Mean absolute error."""
    n = len(y_true)
    return sum(abs(y_true[i] - y_pred[i]) for i in range(n)) / n


def r_squared_oof(y_true, y_pred, y_train):
    """Out-of-fold R^2: 1 - SSE_oof / SST_full_train."""
    sse = sum((y_true[i] - y_pred[i]) ** 2 for i in range(len(y_true)))
    train_mean = sum(y_train) / len(y_train)
    sst = sum((yi - train_mean) ** 2 for yi in y_train)
    return 1.0 - sse / sst if sst > 0 else float('-inf')


def nested_group_cv_ridge(X, y, groups, lambda_grid, outer_group_ids=None):
    """Nested leave-one-group-out CV for ridge.

    For each outer group: hold it out as test.
    Within remaining (training), hold out each inner group once.
    For each lambda: compute inner validation MSE across all inner folds.
    Select lambda with smallest inner RMSE (ties: smaller lambda).
    Refit on all training rows, predict outer test.

    Returns dict with outer results, pooled metrics, lambda grid, etc.
    """
    n = len(y)
    unique_groups = sorted(set(groups))
    if outer_group_ids is None:
        outer_group_ids = list(unique_groups)

    results = []
    all_outer_preds = []
    all_outer_true = []

    for outer_g in outer_group_ids:
        test_idx = [i for i in range(n) if groups[i] == outer_g]
        train_idx = [i for i in range(n) if groups[i] != outer_g]

        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        g_train = [groups[i] for i in train_idx]

        # Training-only standardization
        X_train_sc, means, sds = standardize_training(X_train)

        # Inner CV: for each lambda, compute validation RMSE
        inner_groups = sorted(set(g_train))
        lambda_rmses = []

        for lam in lambda_grid:
            inner_sse = 0.0
            inner_n = 0
            for inner_g in inner_groups:
                val_idx = [i for i, g in enumerate(g_train) if g == inner_g]
                inner_train_idx = [i for i, g in enumerate(g_train) if g != inner_g]

                X_it = [X_train_sc[i] for i in inner_train_idx]
                y_it = [y_train[i] for i in inner_train_idx]
                X_iv = [X_train_sc[i] for i in val_idx]
                y_iv = [y_train[i] for i in val_idx]

                coef, intercept, _ = ridge_coordinate_descent(X_it, y_it, lam)
                preds = ridge_predict(X_iv, coef, intercept)
                inner_sse += sum((y_iv[i] - preds[i]) ** 2 for i in range(len(val_idx)))
                inner_n += len(val_idx)

            inner_rmse = math.sqrt(inner_sse / inner_n) if inner_n > 0 else float('inf')
            lambda_rmses.append(inner_rmse)

        # Select best lambda
        best_idx = 0
        best_rmse = lambda_rmses[0]
        for idx in range(1, len(lambda_rmses)):
            if lambda_rmses[idx] < best_rmse - 1e-12:
                best_idx = idx
                best_rmse = lambda_rmses[idx]
            elif abs(lambda_rmses[idx] - best_rmse) < 1e-12 and lambda_grid[idx] < lambda_grid[best_idx]:
                best_idx = idx

        # Refit on all training, predict test
        coef, intercept, _ = ridge_coordinate_descent(X_train_sc, y_train, lambda_grid[best_idx])
        X_test_sc = apply_standardization([X[i] for i in test_idx], means, sds)
        preds = ridge_predict(X_test_sc, coef, intercept)
        y_test = [y[i] for i in test_idx]

        outer_rmse = rmse(y_test, preds)
        all_outer_preds.extend(preds)
        all_outer_true.extend(y_test)

        results.append({
            'outer_group': outer_g,
            'train_n': len(train_idx),
            'test_n': len(test_idx),
            'inner_rmse_grid': lambda_rmses,
            'selected_lambda': lambda_grid[best_idx],
            'outer_rmse': outer_rmse,
        })

    pooled_rmse = rmse(all_outer_true, all_outer_preds)
    pooled_mae = mae(all_outer_true, all_outer_preds)
    # Q^2 = 1 - SSE / SST_full
    full_mean = sum(y) / len(y)
    sst_full = sum((yi - full_mean) ** 2 for yi in y)
    sse_pooled = sum((all_outer_true[i] - all_outer_preds[i]) ** 2 for i in range(len(all_outer_true)))
    pooled_q2 = 1.0 - sse_pooled / sst_full if sst_full > 0 else float('-inf')

    return {
        'results': results,
        'pooled_rmse': pooled_rmse,
        'pooled_mae': pooled_mae,
        'pooled_q_squared': pooled_q2,
        'outer_rmse': [r['outer_rmse'] for r in results],
        'selected_lambda': [r['selected_lambda'] for r in results],
        'inner_rmse_grid': [r['inner_rmse_grid'] for r in results],
        'outer_train_n': [r['train_n'] for r in results],
        'outer_test_n': [r['test_n'] for r in results],
    }
