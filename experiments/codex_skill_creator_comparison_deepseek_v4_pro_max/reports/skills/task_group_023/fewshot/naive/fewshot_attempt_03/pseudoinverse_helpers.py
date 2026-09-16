"""
Moore-Penrose pseudoinverse with relative singular-value cutoff.

Used by two-step GMM to invert the moment covariance matrix S.
Only singular values >= cutoff * max_singular_value are retained;
their reciprocals form the pseudoinverse.
"""

import math


def pseudoinverse(A, relative_cutoff=1e-12):
    """
    Compute Moore-Penrose pseudoinverse via SVD with relative cutoff.

    Args:
        A: 2D list-of-lists (square symmetric matrix).
        relative_cutoff: Singular values below cutoff * max_sv are dropped.

    Returns:
        2D list-of-lists pseudoinverse.
    """
    n = len(A)
    # Compute eigendecomposition of symmetric A (A = V * D * V')
    # For a symmetric positive-semidefinite matrix, eigenvalues = singular values.
    eigenvalues, eigenvectors = _eigen_symmetric(A)

    max_ev = max(eigenvalues)
    cutoff = relative_cutoff * max_ev if max_ev > 0 else 0

    # Build pseudoinverse: V * D+ * V'
    result = [[0.0] * n for _ in range(n)]
    for k in range(n):
        if eigenvalues[k] >= cutoff:
            inv_ev = 1.0 / eigenvalues[k]
            for i in range(n):
                for j in range(n):
                    result[i][j] += eigenvectors[i][k] * inv_ev * eigenvectors[j][k]

    return result


def _eigen_symmetric(A):
    """
    Compute eigenvalues and eigenvectors of a symmetric matrix using Jacobi iteration.

    Returns:
        eigenvalues: list of n values sorted descending.
        eigenvectors: n x n matrix where column k is the eigenvector for eval k.
    """
    n = len(A)
    # Initialize eigenvectors to identity
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    # Working copy of A
    M = [row[:] for row in A]

    max_iter = 100 * n * n
    tol = 1e-12

    for _ in range(max_iter):
        # Find largest off-diagonal (upper triangle)
        p, q = 0, 1
        max_off = abs(M[0][1])
        for i in range(n):
            for j in range(i + 1, n):
                if abs(M[i][j]) > max_off:
                    max_off = abs(M[i][j])
                    p, q = i, j

        if max_off < tol:
            break

        # Compute rotation
        if abs(M[p][q]) < 1e-30:
            continue

        theta = (M[q][q] - M[p][p]) / (2.0 * M[p][q])
        if theta >= 0:
            t = 1.0 / (theta + math.sqrt(1.0 + theta * theta))
        else:
            t = -1.0 / (-theta + math.sqrt(1.0 + theta * theta))

        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c

        # Apply rotation
        # Update rows/cols p and q
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

        # Update eigenvectors
        for i in range(n):
            v_ip = V[i][p]
            v_iq = V[i][q]
            V[i][p] = c * v_ip - s * v_iq
            V[i][q] = s * v_ip + c * v_iq

    # Extract eigenvalues from diagonal
    eigenvalues = [M[i][i] for i in range(n)]

    # Sort descending and reorder eigenvectors
    order = sorted(range(n), key=lambda i: eigenvalues[i], reverse=True)
    eigenvalues = [eigenvalues[i] for i in order]
    V_sorted = [[V[i][k] for k in order] for i in range(n)]

    # Ensure eigenvalues are non-negative (numerical cleanup)
    eigenvalues = [max(ev, 0.0) for ev in eigenvalues]

    return eigenvalues, V_sorted
