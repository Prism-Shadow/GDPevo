"""
Ridge and elastic-net coordinate-descent solvers with standardization.

Supports both weighted and unweighted variants. Each fit centers y
and standardizes X from training-only moments.
"""

import math


def soft_threshold(a, t):
    """Soft-thresholding: sign(a) * max(|a| - t, 0)."""
    if a > t:
        return a - t
    elif a < -t:
        return a + t
    return 0.0


def fit_ridge(X, y, penalty, weights=None, tol=1e-8, max_sweeps=10000):
    """
    Fit ridge regression with coordinate descent.

    Args:
        X: n x k feature matrix (list-of-lists).
        y: n-element outcome vector.
        penalty: lambda (L2 penalty coefficient).
        weights: optional positive weight vector (None = unit weights).
        tol: convergence tolerance on max coefficient change.
        max_sweeps: maximum number of full coordinate sweeps.

    Returns:
        (intercept, coefficients) where coefficients is a k-element list.
    """
    n = len(X)
    k = len(X[0]) if n > 0 else 0

    if n == 0:
        return 0.0, [0.0] * k

    w = weights if weights is not None else [1.0] * n
    w_sum = sum(w)

    # Standardize X and center y
    Z, mu, sigma = _standardize(X, w)
    y_center, y_bar = _center_y(y, w)

    # Intercept starts at y_bar
    intercept = y_bar
    b = [0.0] * k

    # Precompute weighted column norms
    col_norms = [0.0] * k
    for j in range(k):
        col_norms[j] = sum(w[i] * Z[i][j] * Z[i][j] for i in range(n)) / w_sum

    for _sweep in range(max_sweeps):
        max_change = 0.0

        for j in range(k):
            # Compute partial residual dot product for column j
            rho = 0.0
            for i in range(n):
                residual = y_center[i] - intercept
                for l in range(k):
                    if l != j:
                        residual -= b[l] * Z[i][l]
                rho += w[i] * Z[i][j] * residual
            rho /= w_sum

            b_new = rho / (col_norms[j] + penalty)
            change = abs(b_new - b[j])
            if change > max_change:
                max_change = change
            b[j] = b_new

        # Update intercept
        residual_sum = 0.0
        for i in range(n):
            pred = sum(b[l] * Z[i][l] for l in range(k))
            residual_sum += w[i] * (y_center[i] - pred)
        intercept = residual_sum / w_sum

        if max_change < tol:
            break

    # Unstandardize coefficients for raw X
    coefs_raw = [0.0] * k
    for j in range(k):
        if sigma[j] > 0:
            coefs_raw[j] = b[j] / sigma[j]

    # Adjust intercept to work with raw X
    intercept_raw = y_bar - sum(coefs_raw[j] * mu[j] for j in range(k))

    return intercept_raw, coefs_raw


def fit_elastic_net(X, y, penalty, alpha, weights=None, tol=1e-8, max_sweeps=10000):
    """
    Fit elastic net with coordinate descent.

    Args:
        X: n x k feature matrix.
        y: n-element outcome vector.
        penalty: lambda (overall penalty coefficient).
        alpha: L1 ratio (0 = ridge, 1 = lasso).
        weights: optional positive weight vector.
        tol: convergence tolerance.
        max_sweeps: maximum sweeps.

    Returns:
        (intercept, coefficients).
    """
    n = len(X)
    k = len(X[0]) if n > 0 else 0

    if n == 0:
        return 0.0, [0.0] * k

    w = weights if weights is not None else [1.0] * n
    w_sum = sum(w)

    Z, mu, sigma = _standardize(X, w)
    y_center, y_bar = _center_y(y, w)

    intercept = y_bar
    b = [0.0] * k

    col_norms = [0.0] * k
    for j in range(k):
        col_norms[j] = sum(w[i] * Z[i][j] * Z[i][j] for i in range(n)) / w_sum

    l1_penalty = penalty * alpha
    l2_penalty = penalty * (1.0 - alpha)

    for _sweep in range(max_sweeps):
        max_change = 0.0

        for j in range(k):
            rho = 0.0
            for i in range(n):
                residual = y_center[i] - intercept
                for l in range(k):
                    if l != j:
                        residual -= b[l] * Z[i][l]
                rho += w[i] * Z[i][j] * residual
            rho /= w_sum

            b_new = soft_threshold(rho, l1_penalty) / (col_norms[j] + l2_penalty)
            change = abs(b_new - b[j])
            if change > max_change:
                max_change = change
            b[j] = b_new

        # Update intercept
        residual_sum = 0.0
        for i in range(n):
            pred = sum(b[l] * Z[i][l] for l in range(k))
            residual_sum += w[i] * (y_center[i] - pred)
        intercept = residual_sum / w_sum

        if max_change < tol:
            break

    coefs_raw = [0.0] * k
    for j in range(k):
        if sigma[j] > 0:
            coefs_raw[j] = b[j] / sigma[j]

    intercept_raw = y_bar - sum(coefs_raw[j] * mu[j] for j in range(k))

    return intercept_raw, coefs_raw


def _standardize(X, weights):
    """Compute weighted mean, population std, and standardized matrix."""
    n = len(X)
    k = len(X[0]) if n > 0 else 0
    w_sum = sum(weights)

    mu = [0.0] * k
    sigma = [0.0] * k
    for j in range(k):
        mu_j = sum(weights[i] * X[i][j] for i in range(n)) / w_sum
        var_j = sum(weights[i] * (X[i][j] - mu_j) ** 2 for i in range(n)) / w_sum
        sigma_j = math.sqrt(var_j) if var_j > 1e-30 else 1.0
        mu[j] = mu_j
        sigma[j] = sigma_j

    Z = [[0.0] * k for _ in range(n)]
    for i in range(n):
        for j in range(k):
            Z[i][j] = (X[i][j] - mu[j]) / sigma[j]

    return Z, mu, sigma


def _center_y(y, weights):
    """Compute weighted mean and centered y."""
    n = len(y)
    w_sum = sum(weights)
    y_bar = sum(weights[i] * y[i] for i in range(n)) / w_sum
    y_center = [y[i] - y_bar for i in range(n)]
    return y_center, y_bar
