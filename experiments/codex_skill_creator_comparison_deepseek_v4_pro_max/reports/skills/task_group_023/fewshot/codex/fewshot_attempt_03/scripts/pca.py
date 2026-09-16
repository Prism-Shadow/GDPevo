#!/usr/bin/env python3
"""PCA via symmetric Jacobi method as used in PHO trajectory audits.

- Covariance matrix C = Z'Z / (n-1) where Z is standardized.
- Symmetric Jacobi: pick largest absolute upper-triangle off-diagonal.
  Tie-break: lower row, then lower column.
  tau = (A_qq - A_pp) / (2 * A_pq)
  t = sign_nonnegative(tau) / (abs(tau) + sqrt(1 + tau^2))
  c = 1 / sqrt(1 + t^2); s = t * c
  Rotate A and eigenvectors.
  Stop at effective off-diagonal tolerance or step cap.

- Order components by descending eigenvalue, then original diagonal index.
- Flip each loading so the earliest maximum-absolute entry is positive.
- Scores = Z * loadings.
"""

import math


def standardize_columns(X):
    """Standardize each column to sample SD (ddof=1). Return (Z, means, sds)."""
    n = len(X)
    p = len(X[0])
    means = [sum(X[i][j] for i in range(n)) / n for j in range(p)]
    Z = []
    sds = []
    for j in range(p):
        var = sum((X[i][j] - means[j]) ** 2 for i in range(n)) / (n - 1)
        sd = math.sqrt(var) if var > 1e-15 else 1.0
        sds.append(sd)
    Z = [[(X[i][j] - means[j]) / sds[j] for j in range(p)] for i in range(n)]
    return Z, means, sds


def symmetric_jacobi_pca(X, tol=1e-12, max_iters=100):
    """Full PCA via symmetric Jacobi.

    Args:
        X: data matrix (n x p), will be standardized internally.
        tol: off-diagonal tolerance.
        max_iters: maximum Jacobi sweeps.

    Returns:
        (eigenvalues, loadings, scores, total_variance)
        eigenvalues: sorted descending
        loadings: p x p, each column is a loading vector
        scores: n x p, each column is a component score
    """
    Z, _, _ = standardize_columns(X)
    n = len(Z)
    p = len(Z[0])

    # Covariance matrix
    C = [[0.0] * p for _ in range(p)]
    for i in range(n):
        for j in range(p):
            for k in range(p):
                C[j][k] += Z[i][j] * Z[i][k]
    for j in range(p):
        for k in range(p):
            C[j][k] /= (n - 1)

    # Eigenvectors init to identity
    V = [[1.0 if i == j else 0.0 for j in range(p)] for i in range(p)]

    for _ in range(max_iters):
        # Find largest off-diagonal |A_pq|
        max_val = 0.0
        p_idx, q_idx = -1, -1
        for i in range(p):
            for j in range(i + 1, p):
                if abs(C[i][j]) > max_val:
                    max_val = abs(C[i][j])
                    p_idx, q_idx = i, j

        if max_val < tol:
            break

        # Compute Jacobi rotation
        App = C[p_idx][p_idx]
        Aqq = C[q_idx][q_idx]
        Apq = C[p_idx][q_idx]

        theta = (Aqq - App) / (2.0 * Apq)
        t = 1.0 / (abs(theta) + math.sqrt(1.0 + theta * theta))
        if theta < 0:
            t = -t

        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c

        # Rotate C
        for i in range(p):
            if i != p_idx and i != q_idx:
                aip = C[i][p_idx]
                aiq = C[i][q_idx]
                C[i][p_idx] = c * aip - s * aiq
                C[p_idx][i] = C[i][p_idx]
                C[i][q_idx] = s * aip + c * aiq
                C[q_idx][i] = C[i][q_idx]

        C[p_idx][p_idx] = c * c * App + s * s * Aqq - 2 * c * s * Apq
        C[q_idx][q_idx] = s * s * App + c * c * Aqq + 2 * c * s * Apq
        C[p_idx][q_idx] = 0.0
        C[q_idx][p_idx] = 0.0

        # Rotate eigenvectors
        for i in range(p):
            vip = V[i][p_idx]
            viq = V[i][q_idx]
            V[i][p_idx] = c * vip - s * viq
            V[i][q_idx] = s * vip + c * viq

    # Extract eigenvalues (diagonal of C)
    eigenvalues = [C[i][i] for i in range(p)]

    # Order by descending eigenvalue, then by original diagonal index
    indices = sorted(range(p), key=lambda i: (-eigenvalues[i], i))
    eigenvalues = [eigenvalues[i] for i in indices]
    loadings = [[V[j][i] for i in indices] for j in range(p)]

    # Flip: earliest maximum-absolute entry positive
    for k in range(p):
        col_k = [loadings[j][k] for j in range(p)]
        # Find position of max absolute
        max_abs = 0.0
        max_pos = 0
        for j in range(p):
            if abs(col_k[j]) > max_abs + 1e-15:
                max_abs = abs(col_k[j])
                max_pos = j
        if col_k[max_pos] < 0:
            for j in range(p):
                loadings[j][k] = -loadings[j][k]

    # Scores: Z * loadings (loadings are p x p)
    scores = [[0.0] * p for _ in range(n)]
    for i in range(n):
        for k in range(p):
            scores[i][k] = sum(Z[i][j] * loadings[j][k] for j in range(p))

    return eigenvalues, loadings, scores


def pca_summary(eigenvalues):
    """Compute explained variance ratios and cumulative."""
    total = sum(eigenvalues)
    ratios = [v / total for v in eigenvalues]
    cumulative = [sum(ratios[:i+1]) for i in range(len(ratios))]
    return ratios, cumulative
