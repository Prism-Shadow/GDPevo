"""Pure-Python linear algebra utilities. No numpy/scipy required."""

import math
import random as _random

# ── Matrix operations ──────────────────────────────────────────────────────

def mat_mul(A, B):
    """Multiply matrices A (m×n) and B (n×p)."""
    m, n = len(A), len(A[0])
    nb, p = len(B), len(B[0])
    if n != nb:
        raise ValueError(f"Shape mismatch: ({m},{n}) × ({nb},{p})")
    result = [[0.0]*p for _ in range(m)]
    for i in range(m):
        Ai = A[i]
        Ri = result[i]
        for k in range(n):
            aik = Ai[k]
            if aik != 0:
                Bk = B[k]
                for j in range(p):
                    Ri[j] += aik * Bk[j]
    return result

def mat_transpose(A):
    """Transpose matrix A (m×n) → (n×m)."""
    if not A: return []
    m, n = len(A), len(A[0])
    return [[A[i][j] for i in range(m)] for j in range(n)]

def mat_add(A, B):
    """Add matrices A + B."""
    m, n = len(A), len(A[0])
    return [[A[i][j] + B[i][j] for j in range(n)] for i in range(m)]

def mat_sub(A, B):
    """Subtract matrices A - B."""
    m, n = len(A), len(A[0])
    return [[A[i][j] - B[i][j] for j in range(n)] for i in range(m)]

def mat_scale(A, s):
    """Scale matrix A by scalar s."""
    return [[aij * s for aij in row] for row in A]

def eye(n):
    """Identity matrix n×n."""
    I = [[0.0]*n for _ in range(n)]
    for i in range(n):
        I[i][i] = 1.0
    return I

def mat_copy(A):
    """Deep copy of matrix A."""
    return [row[:] for row in A]

def col_vector(vals):
    """Convert list to column vector (n×1)."""
    return [[x] for x in vals]

def row_vector(vals):
    """Convert list to row vector (1×n)."""
    return [list(vals)]

def flatten_col(v):
    """Flatten column vector to list."""
    return [row[0] for row in v]

# ── Linear system solving ──────────────────────────────────────────────────

def solve(A, b):
    """Solve Ax = b using Gaussian elimination with partial pivoting.
    A is n×n, b is n×1 or n-list. Returns x as column vector."""
    n = len(A)
    # Create augmented matrix
    if isinstance(b[0], list):
        b_col = [b[i][0] for i in range(n)]
    else:
        b_col = list(b)

    aug = [A[i][:] + [b_col[i]] for i in range(n)]

    for col in range(n):
        # Partial pivoting
        max_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[max_row][col]) < 1e-15:
            continue
        if max_row != col:
            aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot

        for row in range(n):
            if row != col and abs(aug[row][col]) > 1e-15:
                factor = aug[row][col]
                for j in range(col, n + 1):
                    aug[row][j] -= factor * aug[col][j]

    x = [[aug[i][n]] for i in range(n)]
    return x

def lstsq(A, b):
    """Least squares: solve (A^T A)x = A^T b."""
    At = mat_transpose(A)
    AtA = mat_mul(At, A)
    Atb = mat_mul(At, b)

    # Cholesky with regularization if needed
    try:
        x = solve_cholesky(AtA, Atb)
    except:
        # Fall back to Gaussian elimination with ridge
        n = len(AtA)
        reg = mat_add(AtA, mat_scale(eye(n), 1e-10))
        x = solve(reg, Atb)
    return x

def solve_cholesky(A, b):
    """Solve Ax = b where A is symmetric positive definite via Cholesky.
    A is n×n, b is n×1."""
    n = len(A)
    L = [[0.0]*n for _ in range(n)]

    # Cholesky decomposition A = L L^T
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][j] = math.sqrt(max(1e-15, A[i][i] - s))
            else:
                L[i][j] = (A[i][j] - s) / L[j][j]

    # Forward substitute Ly = b
    y = [0.0]*n
    for i in range(n):
        s = sum(L[i][j] * y[j] for j in range(i))
        y[i] = (b[i][0] - s) / L[i][i]

    # Back substitute L^T x = y
    x = [0.0]*n
    for i in range(n-1, -1, -1):
        s = sum(L[j][i] * x[j] for j in range(i+1, n))
        x[i] = (y[i] - s) / L[i][i]

    return [[v] for v in x]

def pinv(A):
    """Moore-Penrose pseudoinverse."""
    At = mat_transpose(A)
    AtA = mat_mul(At, A)
    n = len(AtA)
    try:
        AtA_inv = mat_inv_cholesky(AtA)
    except:
        AtA_reg = mat_add(AtA, mat_scale(eye(n), 1e-10))
        AtA_inv = mat_inv_cholesky(AtA_reg)
    return mat_mul(AtA_inv, At)

def mat_inv_cholesky(A):
    """Inverse of symmetric positive definite matrix via Cholesky."""
    n = len(A)
    I = eye(n)
    inv = []
    for j in range(n):
        col = solve_cholesky(A, [[I[i][j]] for i in range(n)])
        inv.append(flatten_col(col))
    return mat_transpose(inv)

# ── Statistics ─────────────────────────────────────────────────────────────

def mean(vals):
    """Arithmetic mean."""
    if not vals: return 0.0
    return sum(vals) / len(vals)

def variance(vals, ddof=1):
    """Sample variance."""
    n = len(vals)
    if n <= ddof: return 0.0
    m = mean(vals)
    return sum((v - m)**2 for v in vals) / (n - ddof)

def std(vals, ddof=1):
    """Sample standard deviation."""
    return math.sqrt(variance(vals, ddof))

def cov(x, y):
    """Sample covariance."""
    n = len(x)
    if n <= 1: return 0.0
    mx, my = mean(x), mean(y)
    return sum((x[i]-mx)*(y[i]-my) for i in range(n)) / (n - 1)

def corr(x, y):
    """Pearson correlation."""
    if len(x) <= 1: return 0.0
    sx, sy = std(x), std(y)
    if sx == 0 or sy == 0: return 0.0
    return cov(x, y) / (sx * sy)

def quantile(data, q):
    """Sample quantile. q in [0, 1]."""
    if not data: return 0.0
    s = sorted(data)
    n = len(s)
    idx = q * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac

# ── Random number generators ───────────────────────────────────────────────

class PCG32:
    """PCG32 random number generator."""
    def __init__(self, seed, stream=0):
        self.state = 0
        self.stream = (stream | 1) & 0xFFFFFFFF
        self.state = (self.state * 6364136223846793005 + self.stream) & 0xFFFFFFFFFFFFFFFF
        self.state = (self.state * 6364136223846793005 + seed) & 0xFFFFFFFFFFFFFFFF
        self.next()  # discard first

    def next(self):
        old = self.state
        self.state = (old * 6364136223846793005 + self.stream) & 0xFFFFFFFFFFFFFFFF
        xor_shifted = ((old >> 18) ^ old) >> 27
        rot = old >> 59
        result = ((xor_shifted >> rot) | (xor_shifted << ((-rot) & 31))) & 0xFFFFFFFF
        return result, result / 0x100000000

class XorShift32:
    """XorShift32 random number generator."""
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF
        if self.state == 0:
            self.state = 2463534242

    def next(self):
        x = self.state & 0xFFFFFFFF
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x
        return x, x / 0x100000000

# ── OLS regression ─────────────────────────────────────────────────────────

def ols_fit(X, y):
    """Ordinary least squares. X: list of lists (n×k), y: list or list of lists (n×1).
    Returns (beta, residuals, sigma2, XtX_inv)."""
    n, k = len(X), len(X[0])
    if isinstance(y[0], list):
        y_col = [[yi[0]] for yi in y]
    else:
        y_col = [[v] for v in y]

    Xt = mat_transpose(X)
    XtX = mat_mul(Xt, X)

    try:
        beta = solve_cholesky(XtX, mat_mul(Xt, y_col))
    except:
        XtX_reg = mat_add(XtX, mat_scale(eye(k), 1e-10))
        beta = solve(XtX_reg, mat_mul(Xt, y_col))

    beta_flat = flatten_col(beta)
    y_fit = [sum(X[i][j] * beta_flat[j] for j in range(k)) for i in range(n)]
    y_obs = flatten_col(y_col)
    resid = [y_obs[i] - y_fit[i] for i in range(n)]

    rss = sum(r**2 for r in resid)
    dof = max(1, n - k)
    sigma2 = rss / dof

    cov_beta = mat_scale(mat_inv_cholesky(XtX), sigma2) if sigma2 > 0 else [[0.0]*k for _ in range(k)]

    return {
        'beta': beta_flat,
        'fitted': y_fit,
        'residuals': resid,
        'sigma2': sigma2,
        'rss': rss,
        'n': n,
        'k': k,
        'dof': dof,
        'XtX_inv': mat_inv_cholesky(XtX),
        'cov_beta': cov_beta
    }

def cluster_cr1_se(X, y, fit_result, clusters):
    """CR1 cluster-robust standard errors.
    clusters: list of cluster indices (0..G-1) for each observation."""
    n, k = len(X), len(X[0])
    G = max(clusters) + 1
    beta = fit_result['beta']
    resid = fit_result['residuals']
    XtX_inv = fit_result['XtX_inv']

    correction = (G / max(G-1, 1)) * ((n - 1) / max(n - k, 1))

    meat = [[0.0]*k for _ in range(k)]
    for g in range(G):
        idx = [i for i, c in enumerate(clusters) if c == g]
        if not idx: continue
        for i_idx in idx:
            for j_idx in idx:
                ri = resid[i_idx]
                rj = resid[j_idx]
                Xi = X[i_idx]
                Xj = X[j_idx]
                for a in range(k):
                    for b in range(k):
                        meat[a][b] += Xi[a] * ri * Xj[b] * rj

    V = mat_mul(mat_mul(XtX_inv, meat), XtX_inv)
    V = mat_scale(V, correction)

    se = [math.sqrt(max(0, V[i][i])) for i in range(k)]
    return se

# ── Ridge regression ───────────────────────────────────────────────────────

def ridge_fit(X, y, lam):
    """Ridge regression: beta = (X^T X + lam*I)^{-1} X^T y."""
    n, k = len(X), len(X[0])
    XtX = mat_mul(mat_transpose(X), X)
    reg = mat_add(XtX, mat_scale(eye(k), lam))
    if isinstance(y[0], list):
        y_col = y
    else:
        y_col = [[v] for v in y]
    try:
        beta = solve_cholesky(reg, mat_mul(mat_transpose(X), y_col))
    except:
        beta = solve(reg, mat_mul(mat_transpose(X), y_col))
    return flatten_col(beta)

# ── PCA ─────────────────────────────────────────────────────────────────────

def power_iteration(A, n_components=2, max_iter=1000):
    """Power iteration for top eigenvectors of symmetric matrix A."""
    n = len(A)
    components = []

    A_work = mat_copy(A)

    for comp in range(n_components):
        # Initialize random vector
        v = [1.0] * n
        for iteration in range(max_iter):
            Av = [sum(A_work[i][j] * v[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x*x for x in Av))
            if norm < 1e-15:
                break
            v_new = [x / norm for x in Av]
            # Check convergence
            diff = math.sqrt(sum((v_new[i] - v[i])**2 for i in range(n)))
            v = v_new
            if diff < 1e-12:
                break

        # Eigenvalue (Rayleigh quotient)
        Av = [sum(A_work[i][j] * v[j] for j in range(n)) for i in range(n)]
        eigenvalue = sum(v[i] * Av[i] for i in range(n))
        components.append((eigenvalue, v))

        # Deflate: A = A - lambda * v * v^T
        for i in range(n):
            for j in range(n):
                A_work[i][j] -= eigenvalue * v[i] * v[j]

    return components

# ── k-means clustering ─────────────────────────────────────────────────────

def kmeans(X, k, max_iter=300, init_centroids=None, random_seed=42):
    """k-means clustering. X: list of points (each is a list of coordinates).
    Returns {'labels': [...], 'centroids': [...], 'sizes': [...], 'iterations': int}."""
    n = len(X)
    if n == 0:
        return {'labels': [], 'centroids': [], 'sizes': [], 'iterations': 0}

    d = len(X[0])

    # Initialize centroids
    if init_centroids is not None:
        centroids = [list(c) for c in init_centroids]
    else:
        rng = _random.Random(random_seed)
        centroids = [list(X[rng.randint(0, n-1)])]
        for _ in range(1, k):
            # k-means++ initialization
            dists = [min(sum((X[i][j] - c[j])**2 for j in range(d)) for c in centroids) for i in range(n)]
            total = sum(dists)
            if total == 0:
                centroids.append(list(X[_ % n]))
            else:
                r = rng.random() * total
                cum = 0
                chosen = 0
                for i, dist in enumerate(dists):
                    cum += dist
                    if cum >= r:
                        chosen = i
                        break
                centroids.append(list(X[chosen]))

    labels = [0] * n

    for iteration in range(max_iter):
        # Assign points to nearest centroid
        changed = False
        for i in range(n):
            best_k = min(range(k), key=lambda kk: sum((X[i][j] - centroids[kk][j])**2 for j in range(d)))
            if best_k != labels[i]:
                labels[i] = best_k
                changed = True

        if not changed:
            break

        # Update centroids
        centroids = [[0.0]*d for _ in range(k)]
        counts = [0] * k
        for i in range(n):
            ci = labels[i]
            counts[ci] += 1
            for j in range(d):
                centroids[ci][j] += X[i][j]
        for ci in range(k):
            if counts[ci] > 0:
                for j in range(d):
                    centroids[ci][j] /= counts[ci]

    sizes = [0] * k
    for l in labels:
        sizes[l] += 1

    return {
        'labels': labels,
        'centroids': centroids,
        'sizes': sizes,
        'iterations': iteration + 1
    }

def adjusted_rand_index(labels1, labels2):
    """Compute Adjusted Rand Index between two clusterings."""
    n = len(labels1)
    if n <= 1: return 1.0

    # Contingency table
    labs1 = sorted(set(labels1))
    labs2 = sorted(set(labels2))
    ct = {}
    for l1 in labs1:
        for l2 in labs2:
            ct[(l1, l2)] = 0
    for i in range(n):
        ct[(labels1[i], labels2[i])] += 1

    # Row and column sums
    row_sum = {}
    for l1 in labs1:
        row_sum[l1] = sum(ct[(l1, l2)] for l2 in labs2)
    col_sum = {}
    for l2 in labs2:
        col_sum[l2] = sum(ct[(l1, l2)] for l1 in labs1)

    # Compute ARI
    sum_comb = sum(ct[(l1,l2)] * (ct[(l1,l2)] - 1) // 2 for l1 in labs1 for l2 in labs2)
    sum_rows = sum(row_sum[l1] * (row_sum[l1] - 1) // 2 for l1 in labs1)
    sum_cols = sum(col_sum[l2] * (col_sum[l2] - 1) // 2 for l2 in labs2)

    total = n * (n - 1) // 2
    expected = sum_rows * sum_cols / total if total > 0 else 0

    denominator = (sum_rows + sum_cols) / 2 - expected
    if denominator == 0: return 1.0

    return (sum_comb - expected) / denominator

# ── t-distribution ─────────────────────────────────────────────────────────

def t_cdf(x, df):
    """CDF of Student's t distribution (approximation)."""
    if df <= 0: return 0.5
    # Use regularized incomplete beta function via continued fraction
    # Or use the approximation from Abramowitz & Stegun
    a = df / 2.0
    b = 0.5
    s = df / (df + x * x)

    # Incomplete beta via continued fraction
    if x == 0: return 0.5

    # Normal approximation for large df
    if df > 100:
        from math import erf
        return 0.5 * (1 + erf(x / math.sqrt(2)))

    # For smaller df, use the exact formula
    ib = 1.0 - reg_beta_inc(a, b, s)
    if x > 0:
        return 1.0 - 0.5 * ib
    else:
        return 0.5 * ib

def reg_beta_inc(a, b, x, max_iter=200):
    """Regularized incomplete beta function I_x(a,b)."""
    if x == 0: return 0.0
    if x == 1: return 1.0

    # Compute via continued fraction
    # Using Lentz's method
    tiny = 1e-30
    f = 1.0
    C = 1.0
    D = 1.0

    for m in range(1, max_iter):
        mm = m // 2
        if m % 2 == 1:
            # odd term
            d = -(a + mm) * (a + b + mm) * x / ((a + 2*mm) * (a + 2*mm + 1))
        else:
            # even term
            d = mm * (b - mm) * x / ((a + 2*mm - 1) * (a + 2*mm))

        D = 1.0 + d * D
        if abs(D) < tiny: D = tiny
        C = 1.0 + d / C
        if abs(C) < tiny: C = tiny
        D = 1.0 / D

        delta = C * D
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break

    # Front factor
    log_front = a * math.log(x) + b * math.log(1.0 - x) - math.log(a)
    log_front -= _log_beta(a, b)

    return math.exp(log_front) * f

def _log_beta(a, b):
    """Log beta function."""
    from math import lgamma
    return lgamma(a) + lgamma(b) - lgamma(a + b)
