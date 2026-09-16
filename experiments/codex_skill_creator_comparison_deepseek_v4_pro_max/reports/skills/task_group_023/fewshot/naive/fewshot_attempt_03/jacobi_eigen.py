"""
Symmetric Jacobi eigendecomposition.

Computes all eigenvalues and eigenvectors of a real symmetric matrix
using the classical Jacobi rotation method.
"""

import math


def jacobi_eigen(A, tol=1e-12, max_iter=None):
    """
    Compute eigendecomposition of symmetric matrix A via Jacobi method.

    Args:
        A: n x n symmetric matrix (list-of-lists).
        tol: Convergence tolerance on max off-diagonal.
        max_iter: Maximum iterations (default: 100 * n^2).

    Returns:
        eigenvalues: list of n values sorted descending.
        eigenvectors: n x n list-of-lists, column k = eigenvector for eval k.
    """
    n = len(A)
    if max_iter is None:
        max_iter = 100 * n * n

    # Working copy
    M = [row[:] for row in A]
    # Eigenvectors initialized to identity
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for _iter in range(max_iter):
        # Find largest off-diagonal element in upper triangle
        p, q = 0, 1
        max_off = abs(M[0][1]) if n > 1 else 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(M[i][j])
                if val > max_off:
                    max_off = val
                    p, q = i, j

        if max_off < tol:
            break

        # Prevent division by zero
        if abs(M[p][q]) < 1e-30:
            continue

        # Compute Jacobi rotation
        theta = (M[q][q] - M[p][p]) / (2.0 * M[p][q])
        if theta >= 0:
            t = 1.0 / (theta + math.sqrt(1.0 + theta * theta))
        else:
            t = -1.0 / (-theta + math.sqrt(1.0 + theta * theta))

        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c

        # Apply rotation to matrix M
        for i in range(n):
            if i != p and i != q:
                m_ip = M[i][p]
                m_iq = M[i][q]
                M[i][p] = c * m_ip - s * m_iq
                M[p][i] = M[i][p]
                M[i][q] = s * m_ip + c * m_iq
                M[q][i] = M[i][q]

        m_pp = M[p][p]
        m_qq = M[q][q]
        m_pq = M[p][q]

        M[p][p] = c * c * m_pp + s * s * m_qq - 2.0 * s * c * m_pq
        M[q][q] = s * s * m_pp + c * c * m_qq + 2.0 * s * c * m_pq
        M[p][q] = 0.0
        M[q][p] = 0.0

        # Accumulate eigenvectors
        for i in range(n):
            v_ip = V[i][p]
            v_iq = V[i][q]
            V[i][p] = c * v_ip - s * v_iq
            V[i][q] = s * v_ip + c * v_iq

    # Extract eigenvalues from diagonal
    eigenvalues = [M[i][i] for i in range(n)]

    # Sort descending
    order = sorted(range(n), key=lambda i: abs(eigenvalues[i]), reverse=True)
    eigenvalues_sorted = [eigenvalues[i] for i in order]
    V_sorted = [[V[i][k] for k in order] for i in range(n)]

    return eigenvalues_sorted, V_sorted
