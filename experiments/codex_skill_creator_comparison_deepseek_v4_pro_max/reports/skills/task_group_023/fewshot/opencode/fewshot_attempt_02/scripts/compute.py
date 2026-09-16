"""
PHO Audit Solver — Deterministic statistical compute functions.

All algorithms are implemented from first principles (pure Python + math).
No numpy, scipy, sklearn, or any external library is used.
Results are bitwise-reproducible given identical inputs, seed, and order.
"""

import math
import random


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def mean(values):
    """Arithmetic mean of a sequence."""
    n = len(values)
    if n == 0:
        return 0.0
    return sum(values) / n


def sample_sd(values, ddof=1):
    """Sample standard deviation."""
    n = len(values)
    if n <= ddof:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - ddof))


def pearson_r(x, y):
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    mx = mean(x)
    my = mean(y)
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (sx * sy)


def soft_threshold(x, t):
    """Soft-thresholding operator for elastic net."""
    if x > t:
        return x - t
    elif x < -t:
        return x + t
    else:
        return 0.0


# ---------------------------------------------------------------------------
# OLS
# ---------------------------------------------------------------------------

def ols_no_intercept(X, y):
    """
    Ordinary least squares without intercept.
    X: list of lists (n rows x k columns), each row is a list of feature values.
    y: list of length n.
    Returns list b of length k.
    Solves via normal equations X'X b = X'y.
    """
    n = len(y)
    if n == 0:
        return []
    k = len(X[0]) if X else 0
    if k == 0:
        return []

    # X'X
    XtX = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            s = 0.0
            for r in range(n):
                s += X[r][i] * X[r][j]
            XtX[i][j] = s

    # X'y
    Xty = [0.0] * k
    for i in range(k):
        s = 0.0
        for r in range(n):
            s += X[r][i] * y[r]
        Xty[i] = s

    # Solve via Gaussian elimination with partial pivoting
    aug = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for col in range(k):
        # Partial pivot
        max_row = max(range(col, k), key=lambda r: abs(aug[r][col]))
        if abs(aug[max_row][col]) < 1e-14:
            continue
        aug[col], aug[max_row] = aug[max_row], aug[col]
        pivot = aug[col][col]
        for j in range(col, k + 1):
            aug[col][j] /= pivot
        for r in range(k):
            if r != col and abs(aug[r][col]) > 1e-14:
                factor = aug[r][col]
                for j in range(col, k + 1):
                    aug[r][j] -= factor * aug[col][j]

    return [row[k] for row in aug]


def ols_fitted_values(X, b):
    """Compute fitted values y_hat = X @ b."""
    return [sum(xi[j] * b[j] for j in range(len(b))) for xi in X]


def ols_residuals(X, y, b):
    """Compute residuals e = y - X @ b."""
    y_hat = ols_fitted_values(X, b)
    return [yi - yh for yi, yh in zip(y, y_hat)]


def ols_sse(X, y, b):
    """Sum of squared errors."""
    e = ols_residuals(X, y, b)
    return sum(ei * ei for ei in e)


# ---------------------------------------------------------------------------
# Student t distribution CDF (ACM Algorithm 395)
# ---------------------------------------------------------------------------

def _t_cdf(t, df):
    """CDF of Student's t distribution using the incomplete beta function."""
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    # Regularized incomplete beta I_x(df/2, 0.5)
    # For large df, approximate with normal
    if df > 100:
        # Normal approximation
        z = t * (1.0 - 1.0 / (4.0 * df)) / math.sqrt(1.0 + t * t / (2.0 * df))
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    ib = _incbeta(0.5 * df, 0.5, x)
    return 0.5 * (1.0 + math.copysign(1.0, t) * (1.0 - ib))


def _incbeta(a, b, x, max_iter=200, eps=1e-14):
    """Continued fraction computation of regularized incomplete beta I_x(a,b)."""
    if x < 0.0 or x > 1.0:
        raise ValueError("x must be in [0, 1]")
    if x == 0.0 or x == 1.0:
        return x

    # Use continued fraction for x > (a+1)/(a+b+2); otherwise use symmetry
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _cont_frac(a, b, x, max_iter, eps) / a

    return 1.0 - front * _cont_frac(b, a, 1.0 - x, max_iter, eps) / b


def _cont_frac(a, b, x, max_iter, eps):
    """Lentz's continued fraction for incomplete beta."""
    f = 1.0
    C = 1.0
    D = 1.0
    tiny = 1e-30

    for m in range(1, max_iter + 1):
        mm2 = 2 * m

        # d_{2m} = m(b-m)*x / ((a+2m-1)(a+2m))
        d_num = m * (b - m) * x
        d_den = (a + mm2 - 1) * (a + mm2)
        D = d_den + d_num * D
        if D < tiny:
            D = tiny
        D = 1.0 / D

        C = d_den + d_num / C
        if C < tiny:
            C = tiny

        delta = C * D
        f *= delta

        # d_{2m+1} = -(a+m)(a+b+m)*x / ((a+2m)(a+2m+1))
        d_num2 = -(a + m) * (a + b + m) * x
        d_den2 = (a + mm2) * (a + mm2 + 1)
        D = d_den2 + d_num2 * D
        if D < tiny:
            D = tiny
        D = 1.0 / D

        C = d_den2 + d_num2 / C
        if C < tiny:
            C = tiny

        delta = C * D
        f *= delta

        if abs(delta - 1.0) < eps:
            return f

    return f


def t_p_value(t_stat, df, two_sided=True):
    """p-value from t statistic."""
    if df <= 0:
        return 1.0
    if not math.isfinite(t_stat):
        return 1.0
    cdf_val = _t_cdf(abs(t_stat), df)
    p = 2.0 * (1.0 - cdf_val) if two_sided else (1.0 - cdf_val)
    return max(0.0, min(1.0, p))


# ---------------------------------------------------------------------------
# Within transformation (double demeaning)
# ---------------------------------------------------------------------------

def within_transform(y, X, entity_ids, time_ids):
    """
    Apply double-demeaning: z_it - entity_mean(z) - time_mean(z) + grand_mean(z).

    Returns (y_transformed, X_transformed) where each is a list of rows.

    y: list of outcome values (length n)
    X: list of lists (n x k), each row is feature values
    entity_ids: list of entity identifiers (length n)
    time_ids: list of time identifiers (length n)
    """
    n = len(y)
    k = len(X[0]) if X else 0

    # Collect all variables
    Z = [row[:] + [y[i]] for i, row in enumerate(X)]  # n x (k+1), last col is y

    # Compute entity means
    entity_means = {}
    entity_counts = {}
    for i, eid in enumerate(entity_ids):
        if eid not in entity_means:
            entity_means[eid] = [0.0] * (k + 1)
            entity_counts[eid] = 0
        for j in range(k + 1):
            entity_means[eid][j] += Z[i][j]
        entity_counts[eid] += 1
    for eid in entity_means:
        cnt = entity_counts[eid]
        for j in range(k + 1):
            entity_means[eid][j] /= cnt

    # Compute time means
    time_means = {}
    time_counts = {}
    for i, tid in enumerate(time_ids):
        if tid not in time_means:
            time_means[tid] = [0.0] * (k + 1)
            time_counts[tid] = 0
        for j in range(k + 1):
            time_means[tid][j] += Z[i][j]
        time_counts[tid] += 1
    for tid in time_means:
        cnt = time_counts[tid]
        for j in range(k + 1):
            time_means[tid][j] /= cnt

    # Compute grand means
    grand_means = [0.0] * (k + 1)
    for i in range(n):
        for j in range(k + 1):
            grand_means[j] += Z[i][j]
    for j in range(k + 1):
        grand_means[j] /= n

    # Transform
    Zt = []
    for i in range(n):
        eid = entity_ids[i]
        tid = time_ids[i]
        row = []
        for j in range(k + 1):
            val = Z[i][j] - entity_means[eid][j] - time_means[tid][j] + grand_means[j]
            row.append(val)
        Zt.append(row)

    Yt = [row[k] for row in Zt]
    Xt = [[row[j] for j in range(k)] for row in Zt]

    return Yt, Xt


# ---------------------------------------------------------------------------
# Jackknife
# ---------------------------------------------------------------------------

def jackknife(X, y, cluster_ids, coef_index=0):
    """
    Delete-one-cluster jackknife for a double-demeaned OLS model.

    Returns dict with:
      full_coef, delete_coefs (list), delete_entities (list, parallel),
      mean_coef, se, t_stat, p_value, bias_corrected_coef,
      min_coef, min_entity, max_coef, max_entity
    """
    n = len(y)
    k = len(X[0]) if X else 0

    # Full model
    b_full = ols_no_intercept(X, y)
    full_coef = b_full[coef_index] if k > coef_index else 0.0

    # Group observations by cluster
    clusters = {}
    for i, cid in enumerate(cluster_ids):
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(i)
    cluster_list = sorted(clusters.keys())

    G = len(cluster_list)
    if G == 0:
        return {}

    b_delete = []
    entities = list(cluster_list)

    for g in cluster_list:
        keep_idx = [i for i in range(n) if cluster_ids[i] != g]
        X_sub = [X[i] for i in keep_idx]
        y_sub = [y[i] for i in keep_idx]
        b = ols_no_intercept(X_sub, y_sub)
        b_delete.append(b[coef_index] if k > coef_index else 0.0)

    bbar = mean(b_delete)
    se_jk = math.sqrt((G - 1) / G * sum((bg - bbar) ** 2 for bg in b_delete))
    b_bc = G * full_coef - (G - 1) * bbar

    if se_jk < 1e-14:
        t_stat = 0.0
        p_val = 1.0
    else:
        t_stat = b_bc / se_jk
        p_val = t_p_value(abs(t_stat), G - 1)

    min_idx = min(range(G), key=lambda i: b_delete[i])
    max_idx = max(range(G), key=lambda i: b_delete[i])

    return {
        "full_coef": full_coef,
        "delete_coefs": b_delete,
        "delete_entities": entities,
        "mean_coef": bbar,
        "se": se_jk,
        "t_stat": t_stat,
        "p_value": p_val,
        "bias_corrected_coef": b_bc,
        "min_coef": b_delete[min_idx],
        "min_entity": entities[min_idx],
        "max_coef": b_delete[max_idx],
        "max_entity": entities[max_idx],
    }


# ---------------------------------------------------------------------------
# Ridge regression via coordinate descent
# ---------------------------------------------------------------------------

def ridge_coordinate_descent(X, y, lam, max_iter=10000, tol=1e-6):
    """
    Ridge regression via coordinate descent.
    X: n x k list of lists.
    y: length n list (should be centered if intercept desired).
    lam: penalty lambda (>= 0).
    Returns b (length k), with intercept NOT included in b.
    Use separately: intercept = mean(y - X @ b).
    """
    n = len(y)
    if n == 0:
        return []
    k = len(X[0]) if X else 0
    if k == 0:
        return []

    b = [0.0] * k
    # Precompute column sums of squares
    x2 = [sum(xi[j] ** 2 for xi in X) for j in range(k)]
    # Precompute r (residual) = y - X@b initially = y
    r = y[:]

    for cycle in range(max_iter):
        max_change = 0.0
        for j in range(k):
            # Compute r_ij for feature j
            b_old = b[j]
            # Add back current contribution
            for i in range(n):
                r[i] += X[i][j] * b_old
            # Compute numerator
            num = sum(X[i][j] * r[i] for i in range(n))
            denom = x2[j] + n * lam
            if denom < 1e-14:
                b_new = 0.0
            else:
                b_new = num / denom
            b[j] = b_new
            # Update r
            for i in range(n):
                r[i] -= X[i][j] * b_new
            change = abs(b_new - b_old)
            if change > max_change:
                max_change = change
        if max_change < tol:
            break

    return b


# ---------------------------------------------------------------------------
# Elastic net via coordinate descent
# ---------------------------------------------------------------------------

def elastic_net_coordinate_descent(X, y, lam, alpha, l1_ratio,
                                    penalized_mask=None,
                                    max_iter=10000, tol=1e-6):
    """
    Elastic net via coordinate descent.
    Objective: 1/(2n) * SSE + lam * (l1_ratio * L1 + 0.5*(1-l1_ratio)*L2)
    Equivalent to: 1/(2n)*SSE + alpha * L1 + 0.5*lam*(1-l1_ratio)*L2

    Here lam is the total penalty weight, alpha = lam * l1_ratio for the L1 part.
    Actually the objective is:
        (1/(2n))*sum(y - a - Xb)^2 + lam*(l1_ratio*sum|b_j| + 0.5*(1-l1_ratio)*sum(b_j^2))

    X: n x k, y: centered (length n).
    penalized_mask: None means all penalized, else list of bool (length k).
    Returns b (length k).
    """
    n = len(y)
    if n == 0:
        return []
    k = len(X[0]) if X else 0
    if k == 0:
        return []

    if penalized_mask is None:
        penalized_mask = [True] * k

    b = [0.0] * k
    x2 = [sum(xi[j] ** 2 for xi in X) for j in range(k)]
    r = y[:]

    for cycle in range(max_iter):
        max_change = 0.0
        for j in range(k):
            b_old = b[j]
            for i in range(n):
                r[i] += X[i][j] * b_old

            num = (1.0 / n) * sum(X[i][j] * r[i] for i in range(n))

            if penalized_mask[j]:
                denom = x2[j] / n + lam * (1.0 - l1_ratio)
                if denom < 1e-14:
                    b_new = 0.0
                else:
                    b_ols = num / denom
                    threshold = lam * l1_ratio / denom
                    b_new = soft_threshold(b_ols, threshold)
            else:
                # No penalty (intercept-like)
                denom = x2[j]
                if denom < 1e-14:
                    b_new = 0.0
                else:
                    b_new = n * num / denom

            b[j] = b_new
            for i in range(n):
                r[i] -= X[i][j] * b_new
            change = abs(b_new - b_old)
            if change > max_change:
                max_change = change
        if max_change < tol:
            break

    return b


# ---------------------------------------------------------------------------
# Standardization helpers
# ---------------------------------------------------------------------------

def standardize_train(X_train):
    """
    Compute training-only standardization moments.
    Returns (X_scaled, means, sds) where each is list of length k.
    Means and sds to be applied to test/val sets.
    """
    n = len(X_train)
    if n == 0:
        return X_train, [], []
    k = len(X_train[0]) if X_train else 0
    means = [mean([row[j] for row in X_train]) for j in range(k)]
    sds = [sample_sd([row[j] for row in X_train], ddof=1) for j in range(k)]
    X_scaled = []
    for row in X_train:
        scaled_row = []
        for j in range(k):
            if sds[j] > 1e-14:
                scaled_row.append((row[j] - means[j]) / sds[j])
            else:
                scaled_row.append(0.0)
        X_scaled.append(scaled_row)
    return X_scaled, means, sds


def apply_standardization(X, means, sds):
    """Apply pre-computed standardization moments to X."""
    k = len(X[0]) if X else 0
    if not means or not sds:
        return X
    X_scaled = []
    for row in X:
        scaled_row = []
        for j in range(k):
            if sds[j] > 1e-14:
                scaled_row.append((row[j] - means[j]) / sds[j])
            else:
                scaled_row.append(0.0)
        X_scaled.append(scaled_row)
    return X_scaled


# ---------------------------------------------------------------------------
# CR1 cluster-robust variance
# ---------------------------------------------------------------------------

def cr1_variance(X, residuals, cluster_ids, coef_index=0):
    """
    CR1 cluster-robust variance for a given coefficient index.
    X: n x k design matrix.
    residuals: length n list.
    cluster_ids: length n list.
    Returns (se, t_stat, V_CR1_matrix).

    V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * inv(X'X) * sum_g(s_g*s_g') * inv(X'X)
    where s_g = X_g' * e_g
    """
    n = len(residuals)
    k = len(X[0]) if X else 0
    if n == 0 or k == 0:
        return 0.0, 0.0, []

    # Group by cluster
    clusters = {}
    for i, cid in enumerate(cluster_ids):
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(i)
    cluster_list = sorted(clusters.keys())
    G = len(cluster_list)

    # X'X inverse
    XtX = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            s = 0.0
            for r in range(n):
                s += X[r][i] * X[r][j]
            XtX[i][j] = s

    XtX_inv = _matrix_inverse(XtX)

    # Meat: sum_g s_g * s_g'
    meat = [[0.0] * k for _ in range(k)]
    for g in cluster_list:
        indices = clusters[g]
        sg = [0.0] * k
        for j in range(k):
            sg[j] = sum(X[i][j] * residuals[i] for i in indices)
        for p in range(k):
            for q in range(k):
                meat[p][q] += sg[p] * sg[q]

    # Scale
    scale = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0

    # V_CR1 = scale * inv(X'X) * meat * inv(X'X)
    # First: temp = inv(X'X) * meat
    temp = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            s = 0.0
            for m in range(k):
                s += XtX_inv[i][m] * meat[m][j]
            temp[i][j] = s

    V = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            s = 0.0
            for m in range(k):
                s += temp[i][m] * XtX_inv[m][j]
            V[i][j] = s * scale

    if coef_index < k:
        var_j = V[coef_index][coef_index]
        se = math.sqrt(max(0.0, var_j))
    else:
        var_j = 0.0
        se = 0.0

    return se, V


def _matrix_inverse(A):
    """Invert a square matrix via Gaussian elimination."""
    n = len(A)
    # Augment with identity
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        # Pivot
        max_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[max_row][col]) < 1e-14:
            # Singular — return identity as fallback
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        aug[col], aug[max_row] = aug[max_row], aug[col]
        pivot = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= pivot
        for r in range(n):
            if r != col:
                factor = aug[r][col]
                if abs(factor) > 1e-14:
                    for j in range(col, 2 * n):
                        aug[r][j] -= factor * aug[col][j]
    return [row[n:] for row in aug]


# ---------------------------------------------------------------------------
# PCG32 PRNG
# ---------------------------------------------------------------------------

def pcg32_init(seed, stream=0):
    """Initialize PCG32 PRNG. Returns state dict."""
    increment = (2 * stream + 1) & 0xFFFFFFFFFFFFFFFF
    state = 0
    # Advance once
    state = (state * 6364136223846793005 + increment) & 0xFFFFFFFFFFFFFFFF
    state = (state + (seed & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
    # Advance again
    state = (state * 6364136223846793005 + increment) & 0xFFFFFFFFFFFFFFFF
    return {"state": state, "inc": increment}


def pcg32_advance(rng):
    """Advance PCG32 and return 32-bit output."""
    old = rng["state"]
    rng["state"] = (old * 6364136223846793005 + rng["inc"]) & 0xFFFFFFFFFFFFFFFF
    xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
    rot = (old >> 59) & 0x1F
    return ((xorshifted >> rot) | (xorshifted << (32 - rot))) & 0xFFFFFFFF


def pcg32_weight(rng):
    """Draw a PCG32 weight mapped to [-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5)]."""
    v = pcg32_advance(rng) % 6
    weights = [-math.sqrt(3.0 / 2.0), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(3.0 / 2.0)]
    return weights[v]


def pcg32_state(rng):
    """Return current PRNG state as integer."""
    return rng["state"]


# ---------------------------------------------------------------------------
# XORSHIFT32 PRNG
# ---------------------------------------------------------------------------

def xorshift32_init(seed):
    """Initialize XORSHIFT32 and return state dict."""
    s = seed & 0xFFFFFFFF
    if s == 0:
        s = 1
    return {"state": s}


def xorshift32_advance(rng):
    """Advance XORSHIFT32 and return 32-bit output."""
    x = rng["state"]
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= (x >> 17) & 0xFFFFFFFF
    x ^= (x << 5) & 0xFFFFFFFF
    rng["state"] = x & 0xFFFFFFFF
    return rng["state"]


def xorshift32_weight(rng):
    """
    Draw a XORSHIFT32 bootstrap weight.
    Map output lower 4 bits to 11 values: {-2,-1,0,1,2,3,4,5,6,7,8}.
    Discard values >= 11.
    """
    weights = [-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
    while True:
        v = xorshift32_advance(rng)
        idx = v & 0xF  # lower 4 bits: 0-15
        if idx < 11:
            return weights[idx]


def xorshift32_state(rng):
    """Return current PRNG state."""
    return rng["state"]


# ---------------------------------------------------------------------------
# Wild cluster bootstrap
# ---------------------------------------------------------------------------

def wild_cluster_bootstrap(X, y, cluster_ids, cluster_order, target_idx,
                           prng_type, seed, stream, B,
                           quantile_probs, checkpoint_reps):
    """
    Wild cluster bootstrap-t.

    X: n x k design matrix (double-demeaned).
    y: n outcome vector (double-demeaned).
    cluster_ids: list of cluster IDs (length n).
    cluster_order: ordered list of cluster IDs.
    target_idx: index of coefficient to test.
    prng_type: "PCG32" or "XORSHIFT32".
    seed: integer.
    stream: integer (PCG32 only).
    B: number of bootstrap replicates.
    quantile_probs: list of probabilities for quantiles.
    checkpoint_reps: list of replicate numbers to checkpoint.

    Returns dict with observed stats, bootstrap results, quantiles, checkpoints.
    """
    n = len(y)
    k = len(X[0]) if X else 0

    # Fit unrestricted model
    b_full = ols_no_intercept(X, y)
    b_target = b_full[target_idx] if target_idx < k else 0.0

    # CR1 SE for unrestricted
    e_full = ols_residuals(X, y, b_full)
    se_obs, V_obs = cr1_variance(X, e_full, cluster_ids, target_idx)
    t_obs = b_target / se_obs if se_obs > 1e-14 else 0.0

    # Fit restricted model (without target predictor)
    X_rest = [[row[j] for j in range(k) if j != target_idx] for row in X]
    b_rest = ols_no_intercept(X_rest, y)
    y_rest = ols_fitted_values(X_rest, b_rest)
    e_rest = [y[i] - y_rest[i] for i in range(n)]

    # Initialize PRNG
    if prng_type == "PCG32":
        rng = pcg32_init(seed, stream)
        draw_weight = pcg32_weight
        get_state = pcg32_state
    elif prng_type == "XORSHIFT32":
        rng = xorshift32_init(seed)
        draw_weight = xorshift32_weight
        get_state = xorshift32_state
    else:
        raise ValueError(f"Unknown PRNG type: {prng_type}")

    # Map observations to ordered clusters
    cluster_to_indices = {}
    for i, cid in enumerate(cluster_ids):
        cluster_to_indices.setdefault(cid, []).append(i)

    t_boot = []
    checkpoints = []
    checkpoint_set = set(checkpoint_reps)
    exceedance_count = 0

    for rep in range(1, B + 1):
        # Draw weights per cluster
        y_star = [0.0] * n
        for cid in cluster_order:
            w = draw_weight(rng)
            for i in cluster_to_indices.get(cid, []):
                y_star[i] = y_rest[i] + e_rest[i] * w

        # Refit unrestricted on y_star
        b_star = ols_no_intercept(X, y_star)
        b_star_target = b_star[target_idx] if target_idx < k else 0.0

        # CR1 SE
        e_star = ols_residuals(X, y_star, b_star)
        se_star, _ = cr1_variance(X, e_star, cluster_ids, target_idx)
        t_star = b_star_target / se_star if se_star > 1e-14 else 0.0

        t_boot.append(t_star)

        if abs(t_star) >= abs(t_obs):
            exceedance_count += 1

        if rep in checkpoint_set:
            checkpoints.append({
                "replicate": rep,
                "prng_state": get_state(rng),
                "bootstrap_t": t_star,
            })

    # Sort and compute quantiles
    t_sorted = sorted(t_boot)

    def nearest_rank(p):
        idx = min(B, int(math.ceil(p * B))) - 1
        return t_sorted[max(0, idx)]

    quantiles = [nearest_rank(p) for p in quantile_probs]

    p_value = (1.0 + exceedance_count) / (1.0 + B)

    return {
        "observed_coefficient": b_target,
        "observed_cr1_se": se_obs,
        "observed_t": t_obs,
        "bootstrap_t_values": t_boot,
        "exceedance_count": exceedance_count,
        "p_value": p_value,
        "bootstrap_coef_mean": mean([b_target] * B),  # used for reporting
        "bootstrap_coef_sd": sample_sd(t_boot, ddof=1),
        "quantile_probs": quantile_probs,
        "quantiles": quantiles,
        "checkpoints": checkpoints,
        "final_prng_state": get_state(rng),
    }


# ---------------------------------------------------------------------------
# PCA via covariance matrix and Jacobi eigendecomposition
# ---------------------------------------------------------------------------

def pca_jacobi(Z, max_iter=100, tol=1e-10, step_cap=1000, n_components=None):
    """
    PCA on standardized data Z (n x p) via covariance matrix + Jacobi.

    Z: list of lists, already standardized (mean 0, sd 1 per column).
    Returns dict with eigenvalues, explained ratios, loadings, scores.
    """
    n = len(Z)
    if n == 0:
        return {"eigenvalues": [], "explained_ratios": [], "loadings": [], "scores": []}
    p = len(Z[0]) if Z else 0
    if p == 0:
        return {"eigenvalues": [], "explained_ratios": [], "loadings": [], "scores": []}

    # Covariance matrix C = Z'Z / (n-1)
    C = [[0.0] * p for _ in range(p)]
    for i in range(p):
        for j in range(i, p):
            s = sum(Z[r][i] * Z[r][j] for r in range(n))
            C[i][j] = s / (n - 1)
            C[j][i] = C[i][j]

    # Eigenvectors (identity matrix initially)
    V = [[1.0 if i == j else 0.0 for j in range(p)] for i in range(p)]

    steps = 0
    for _ in range(step_cap):
        # Find largest off-diagonal in upper triangle
        max_val = 0.0
        max_i = 0
        max_j = 1
        for i in range(p):
            for j in range(i + 1, p):
                av = abs(C[i][j])
                if av > max_val:
                    max_val = av
                    max_i = i
                    max_j = j
                elif av == max_val:
                    if i < max_i or (i == max_i and j < max_j):
                        max_i = i
                        max_j = j

        if max_val < tol:
            break
        steps += 1
        if steps > max_iter:
            break

        p_idx = max_i
        q_idx = max_j

        # Jacobi rotation
        App = C[p_idx][p_idx]
        Aqq = C[q_idx][q_idx]
        Apq = C[p_idx][q_idx]

        if abs(Apq) < 1e-16:
            continue

        tau = (Aqq - App) / (2.0 * Apq)
        if tau >= 0:
            t_val = 1.0 / (tau + math.sqrt(1.0 + tau * tau))
        else:
            t_val = 1.0 / (tau - math.sqrt(1.0 + tau * tau))
        c_val = 1.0 / math.sqrt(1.0 + t_val * t_val)
        s_val = t_val * c_val

        # Rotate C
        for i in range(p):
            if i != p_idx and i != q_idx:
                a_ip = C[i][p_idx]
                a_iq = C[i][q_idx]
                C[i][p_idx] = c_val * a_ip - s_val * a_iq
                C[p_idx][i] = C[i][p_idx]
                C[i][q_idx] = s_val * a_ip + c_val * a_iq
                C[q_idx][i] = C[i][q_idx]
        C[p_idx][p_idx] = c_val * c_val * App - 2.0 * s_val * c_val * Apq + s_val * s_val * Aqq
        C[q_idx][q_idx] = s_val * s_val * App + 2.0 * s_val * c_val * Apq + c_val * c_val * Aqq
        C[p_idx][q_idx] = 0.0
        C[q_idx][p_idx] = 0.0

        # Rotate eigenvectors
        for i in range(p):
            v_ip = V[i][p_idx]
            v_iq = V[i][q_idx]
            V[i][p_idx] = c_val * v_ip - s_val * v_iq
            V[i][q_idx] = s_val * v_ip + c_val * v_iq

    # Extract eigenvalues from diagonal
    eigenvalues = [C[i][i] for i in range(p)]

    # Sort: descending eigenvalue, then original diagonal index
    idx_eig = list(range(p))
    idx_eig.sort(key=lambda i: (-eigenvalues[i], i))

    sorted_eigenvalues = [eigenvalues[i] for i in idx_eig]
    sorted_eigenvectors = [[V[r][i] for i in idx_eig] for r in range(p)]

    # Flip loadings: for each component, earliest max-abs entry should be positive
    loadings = sorted_eigenvectors[:]  # p x p (rows=features, cols=components)
    for j in range(p):
        # Find earliest index with max absolute value
        max_abs = 0.0
        max_idx = 0
        for i in range(p):
            av = abs(loadings[i][j])
            if av > max_abs:
                max_abs = av
                max_idx = i
        if loadings[max_idx][j] < 0:
            for i in range(p):
                loadings[i][j] = -loadings[i][j]

    # Compute scores
    scores = [[0.0] * p for _ in range(n)]
    for r in range(n):
        for j in range(p):
            s = 0.0
            for i in range(p):
                s += Z[r][i] * loadings[i][j]
            scores[r][j] = s

    # Explained variance ratios
    total_var = sum(eigenvalues)
    explained_ratios = [ev / total_var for ev in sorted_eigenvalues] if total_var > 0 else [0.0] * p

    if n_components is not None:
        nc = min(n_components, p)
    else:
        nc = p

    return {
        "eigenvalues": sorted_eigenvalues[:nc],
        "explained_ratios": explained_ratios[:nc],
        "loadings": [loadings[i][:nc] for i in range(p)],
        "loadings_transposed": [[loadings[i][j] for i in range(p)] for j in range(nc)],
        "scores": [[scores[r][j] for j in range(nc)] for r in range(n)],
    }


# ---------------------------------------------------------------------------
# K-means clustering
# ---------------------------------------------------------------------------

def kmeans(X, k_clusters, max_iter=100, entity_labels=None):
    """
    K-means clustering with deterministic initialization.

    X: n x d list of lists (scores).
    k_clusters: number of clusters.
    entity_labels: optional list of entity codes for deterministic init and tie-breaking.
      First centroid = ASCII-first entity label.
      Subsequent centroids = entity maximizing min distance to existing centroid,
      tie-broken by ASCII-first entity label.

    Returns dict with labels, centroids, sizes, inertia, iterations.
    """
    n = len(X)
    if n == 0:
        return {"labels": [], "centroids": [], "sizes": [], "inertia": 0.0, "iterations": 0}
    d = len(X[0]) if X else 0
    if d == 0:
        return {"labels": [0] * n, "centroids": [[0.0]], "sizes": [n], "inertia": 0.0, "iterations": 0}

    k = min(k_clusters, n)

    # Deterministic initialization
    if entity_labels is not None and k > 0:
        # Sort to get ASCII-first
        sorted_entities = sorted(range(n), key=lambda i: str(entity_labels[i]))
        centroids = [X[sorted_entities[0]][:]]
        for _ in range(1, k):
            best = -1
            best_max_min = -1.0
            for idx in range(n):
                if any(all(abs(X[idx][j] - c[j]) < 1e-14 for j in range(d)) for c in centroids):
                    continue
                min_dist = min(sum((X[idx][j] - c[j]) ** 2 for j in range(d)) for c in centroids)
                if min_dist > best_max_min + 1e-14:
                    best_max_min = min_dist
                    best = idx
                elif abs(min_dist - best_max_min) < 1e-14 and best >= 0:
                    if str(entity_labels[idx]) < str(entity_labels[best]):
                        best = idx
            if best >= 0:
                centroids.append(X[best][:])
            else:
                # Fallback: pick first unassigned
                for idx in range(n):
                    if not any(all(abs(X[idx][j] - c[j]) < 1e-14 for j in range(d)) for c in centroids):
                        centroids.append(X[idx][:])
                        break
    else:
        centroids = [X[i % n][:] for i in range(k)]

    labels = [0] * n
    for iteration in range(max_iter):
        # Assign
        changed = False
        for i in range(n):
            best_c = 0
            best_dist = sum((X[i][j] - centroids[0][j]) ** 2 for j in range(d))
            for c in range(1, k):
                dist = sum((X[i][j] - centroids[c][j]) ** 2 for j in range(d))
                if dist < best_dist - 1e-14:
                    best_dist = dist
                    best_c = c
            if labels[i] != best_c:
                changed = True
                labels[i] = best_c

        if not changed:
            break

        # Update
        counts = [0] * k
        new_centroids = [[0.0] * d for _ in range(k)]
        for i in range(n):
            c = labels[i]
            counts[c] += 1
            for j in range(d):
                new_centroids[c][j] += X[i][j]
        for c in range(k):
            if counts[c] > 0:
                for j in range(d):
                    new_centroids[c][j] /= counts[c]
            else:
                new_centroids[c] = centroids[c][:]

        centroids = new_centroids

    # Canonicalize labels: order by centroid coordinates, then working id
    centroid_order = sorted(range(k), key=lambda c: tuple(centroids[c]))
    label_map = {old: new for new, old in enumerate(centroid_order)}
    labels = [label_map[l] for l in labels]
    centroids = [centroids[old] for old in centroid_order]

    sizes = [labels.count(c) for c in range(k)]
    inertia = sum(
        sum((X[i][j] - centroids[labels[i]][j]) ** 2 for j in range(d))
        for i in range(n)
    )

    return {
        "labels": labels,
        "centroids": centroids,
        "sizes": sizes,
        "inertia": inertia,
        "iterations": iteration + 1,
    }


def silhouette_score(X, labels):
    """Compute average silhouette score."""
    n = len(X)
    if n == 0:
        return 0.0
    k = max(labels) + 1 if labels else 0
    if k < 2:
        return 0.0
    d = len(X[0]) if X else 0

    cluster_members = [[] for _ in range(k)]
    for i, c in enumerate(labels):
        cluster_members[c].append(i)

    sil_sum = 0.0
    for i in range(n):
        ci = labels[i]
        # a(i): mean distance to own cluster
        own = cluster_members[ci]
        if len(own) <= 1:
            continue
        a_i = sum(
            math.sqrt(sum((X[i][j] - X[m][j]) ** 2 for j in range(d)))
            for m in own if m != i
        ) / (len(own) - 1)

        # b(i): min mean distance to other clusters
        b_i = float("inf")
        for cj in range(k):
            if cj == ci or not cluster_members[cj]:
                continue
            d_mean = sum(
                math.sqrt(sum((X[i][j] - X[m][j]) ** 2 for j in range(d)))
                for m in cluster_members[cj]
            ) / len(cluster_members[cj])
            if d_mean < b_i:
                b_i = d_mean

        if b_i == float("inf"):
            continue
        sil_sum += (b_i - a_i) / max(a_i, b_i)

    return sil_sum / n


# ---------------------------------------------------------------------------
# Adjusted Rand Index
# ---------------------------------------------------------------------------

def adjusted_rand_index(labels_a, labels_b):
    """Compute ARI between two label lists."""
    n = len(labels_a)
    if n != len(labels_b) or n == 0:
        return 0.0

    # Build contingency table
    unique_a = sorted(set(labels_a))
    unique_b = sorted(set(labels_b))
    a_to_idx = {a: i for i, a in enumerate(unique_a)}
    b_to_idx = {b: i for i, b in enumerate(unique_b)}

    Ra = len(unique_a)
    Cb = len(unique_b)
    table = [[0] * Cb for _ in range(Ra)]
    for i in range(n):
        table[a_to_idx[labels_a[i]]][b_to_idx[labels_b[i]]] += 1

    a_sums = [sum(row) for row in table]
    b_sums = [sum(table[r][c] for r in range(Ra)) for c in range(Cb)]

    def comb2(x):
        return x * (x - 1) // 2

    sum_comb_ij = sum(comb2(table[r][c]) for r in range(Ra) for c in range(Cb))
    sum_comb_a = sum(comb2(s) for s in a_sums)
    sum_comb_b = sum(comb2(s) for s in b_sums)

    expected = (sum_comb_a * sum_comb_b) / comb2(n) if comb2(n) > 0 else 0.0
    numerator = sum_comb_ij - expected
    denominator = 0.5 * (sum_comb_a + sum_comb_b) - expected

    if denominator == 0.0:
        return 0.0
    return numerator / denominator


# ---------------------------------------------------------------------------
# Conformal prediction helpers
# ---------------------------------------------------------------------------

def conformal_threshold(calib_residuals, alpha):
    """Compute conformal threshold q from calibration absolute residuals."""
    m = len(calib_residuals)
    if m == 0:
        return 0.0, 0
    sorted_res = sorted(abs(r) for r in calib_residuals)
    r_rank = min(m, int(math.ceil((m + 1) * (1.0 - alpha))))
    q = sorted_res[r_rank - 1]
    return q, r_rank


def conformal_coverage(y_true, y_pred, q):
    """Compute coverage fraction (how many true values fall in pred ± q)."""
    n = len(y_true)
    if n == 0:
        return 0.0
    covered = sum(1 for i in range(n) if abs(y_true[i] - y_pred[i]) <= q)
    return covered / n


def conformal_mean_width(q):
    """Mean interval width (2q)."""
    return 2.0 * q


# ---------------------------------------------------------------------------
# RMSE, MAE, R-squared
# ---------------------------------------------------------------------------

def rmse(y_true, y_pred):
    n = len(y_true)
    if n == 0:
        return 0.0
    return math.sqrt(sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)) / n)


def mae(y_true, y_pred):
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum(abs(yt - yp) for yt, yp in zip(y_true, y_pred)) / n


def r_squared_oof(y_true, y_pred, y_full=None):
    """
    Out-of-fold R-squared: 1 - SSE_oof / SST_full.
    If y_full is provided, SST is computed from it; otherwise from y_true.
    """
    n = len(y_true)
    if n == 0:
        return 0.0
    y_ref = y_full if y_full is not None else y_true
    ym = mean(y_ref)
    sse = sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred))
    sst = sum((yr - ym) ** 2 for yr in y_ref)
    if sst == 0:
        return 0.0
    return 1.0 - sse / sst


# ---------------------------------------------------------------------------
# Permutation-based label alignment for ARI
# ---------------------------------------------------------------------------

def align_labels(ref_labels, new_labels):
    """
    Align new_labels to ref_labels by maximizing agreement.
    For ties, choose the lexicographically smallest permutation mapping.
    Returns aligned copy of new_labels.
    """
    ref_set = sorted(set(ref_labels))
    new_set = sorted(set(new_labels))

    if len(ref_set) != len(new_set):
        return new_labels[:]

    k = len(ref_set)
    # Build overlap matrix
    overlap = [[0] * k for _ in range(k)]
    for i in range(len(ref_labels)):
        ref_idx = ref_set.index(ref_labels[i])
        new_idx = new_set.index(new_labels[i])
        overlap[ref_idx][new_idx] += 1

    # Try all permutations of new labels to find max agreement
    import itertools
    best_perm = tuple(range(k))
    best_agree = -1
    for perm in itertools.permutations(range(k)):
        agree = sum(overlap[i][perm[i]] for i in range(k))
        if agree > best_agree:
            best_agree = agree
            best_perm = perm
        elif agree == best_agree and perm < best_perm:
            best_perm = perm

    mapping = {new_set[old]: ref_set[new_idx] for old, new_idx in enumerate(best_perm)}
    return [mapping[l] for l in new_labels]


# ---------------------------------------------------------------------------
# Cholesky decomposition (for GMM)
# ---------------------------------------------------------------------------

def cholesky(A):
    """Cholesky decomposition of symmetric positive definite matrix A."""
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][j] = math.sqrt(max(0.0, A[i][i] - s))
            else:
                denom = L[j][j]
                if abs(denom) > 1e-14:
                    L[i][j] = (A[i][j] - s) / denom
                else:
                    L[i][j] = 0.0
    return L


def solve_triangular(L, b, lower=True, transpose=False):
    """Solve Lx = b or L'x = b where L is triangular."""
    n = len(L)
    x = [0.0] * n
    if lower and not transpose:
        for i in range(n):
            s = b[i]
            for j in range(i):
                s -= L[i][j] * x[j]
            x[i] = s / L[i][i] if abs(L[i][i]) > 1e-14 else 0.0
    elif lower and transpose:
        for i in range(n - 1, -1, -1):
            s = b[i]
            for j in range(i + 1, n):
                s -= L[j][i] * x[j]
            x[i] = s / L[i][i] if abs(L[i][i]) > 1e-14 else 0.0
    elif not lower and not transpose:
        for i in range(n - 1, -1, -1):
            s = b[i]
            for j in range(i + 1, n):
                s -= L[i][j] * x[j]
            x[i] = s / L[i][i] if abs(L[i][i]) > 1e-14 else 0.0
    else:
        for i in range(n):
            s = b[i]
            for j in range(i):
                s -= L[j][i] * x[j]
            x[i] = s / L[i][i] if abs(L[i][i]) > 1e-14 else 0.0
    return x


def solve_psd(A, b):
    """Solve Ax = b for symmetric positive definite A via Cholesky."""
    L = cholesky(A)
    y = solve_triangular(L, b, lower=True, transpose=False)
    x = solve_triangular(L, y, lower=True, transpose=True)
    return x


# ---------------------------------------------------------------------------
# Median
# ---------------------------------------------------------------------------

def median(values):
    """Compute median of a sequence."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    else:
        return (s[n // 2 - 1] + s[n // 2]) / 2.0
