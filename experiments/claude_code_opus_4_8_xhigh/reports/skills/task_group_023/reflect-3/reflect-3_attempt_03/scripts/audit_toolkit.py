"""
Reusable, dependency-light helpers for PHO registered-audit tasks.

Endpoint-free and task-agnostic: every function operates on data you have already
loaded (lists of dict rows, arrays). Adapt to the exact method names, seeds, grids, and
orders declared in the current task's analysis_request.json. Nothing here encodes a
specific task's answer.

`numpy` is used by the statistical helpers; the resolution/PRNG/Shapley helpers are
pure Python. Install numpy/scipy if unavailable.
"""
from __future__ import annotations
import itertools, math
from collections import defaultdict


# ----------------------------------------------------------------------------- #
# 1. Final-release resolution                                                    #
# ----------------------------------------------------------------------------- #
def resolve_final(rows, revision_key="revision", released_key="released_at",
                  id_key="observation_id", status_key="release_status",
                  final_value="FINAL"):
    """Pick the governing record from candidate rows for ONE cell.

    Keep only final-status rows, then take the highest revision, breaking ties by
    latest released_at then id. Returns the chosen row dict or None. Group your table
    by the cell key first (e.g. (entity, year, measure, value_type, source_type))."""
    finals = [r for r in rows if r.get(status_key) == final_value]
    if not finals:
        return None
    finals.sort(key=lambda r: (int(r[revision_key]), str(r.get(released_key, "")),
                               str(r.get(id_key, ""))))
    return finals[-1]


def usable_value(row, invalid_flags=("SUPPRESSED", "INVALID", "INVALID_SCALE",
                                     "WITHDRAWN"), value_key="value",
                 suppression_key="suppression_flag", quality_key="quality_flag"):
    """Return float value if non-suppressed and non-null, else None (never zero-fill)."""
    if row is None:
        return None
    if str(row.get(suppression_key, "0")) == "1":
        return None
    if row.get(quality_key) in invalid_flags:
        return None
    v = row.get(value_key)
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def group_by_cell(rows, key_fields):
    """Group rows into {cell_key_tuple: [rows]} for resolve_final()."""
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in key_fields)].append(r)
    return g


def complete_case_years(entities, years, is_complete):
    """{year: [entities complete that year]} given a predicate is_complete(entity, year)."""
    return {y: [e for e in entities if is_complete(e, y)] for y in years}


def balanced_panel(entities, years, is_complete):
    """Entities complete in EVERY year (sorted)."""
    return sorted(e for e in entities if all(is_complete(e, y) for y in years))


# ----------------------------------------------------------------------------- #
# 2. Reference PRNGs (match the named generator exactly)                         #
# ----------------------------------------------------------------------------- #
class XorShift32:
    """32-bit xorshift (Marsaglia). Reproduces XORSHIFT32 streams."""
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF or 0x9E3779B9

    def next_u32(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17)
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state

    def uniform(self):
        return self.next_u32() / 4294967296.0


class PCG32:
    """Minimal PCG32 (O'Neill). seq/stream selects the sequence constant."""
    MULT = 6364136223846793005
    def __init__(self, seed, seq=1):
        self.inc = ((seq << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.state = 0
        self.next_u32()
        self.state = (self.state + (seed & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
        self.next_u32()

    def next_u32(self):
        old = self.state
        self.state = (old * self.MULT + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF

    def uniform(self):
        return self.next_u32() / 4294967296.0


def rademacher(u):
    """±1 from a uniform draw."""
    return 1.0 if u < 0.5 else -1.0


def webb6(u):
    """Webb 6-point weight from a uniform draw (equal 1/6 buckets)."""
    b = min(5, int(u * 6))
    return [-math.sqrt(1.5), -1.0, -math.sqrt(0.5),
            math.sqrt(0.5), 1.0, math.sqrt(1.5)][b]


# ----------------------------------------------------------------------------- #
# 3. Regression, jackknife, conformal, bootstrap p-value                         #
# ----------------------------------------------------------------------------- #
def ols(X, y):
    import numpy as np
    return np.linalg.lstsq(np.asarray(X, float), np.asarray(y, float), rcond=None)[0]


def wls(X, y, w):
    """Weighted least squares beta = (X'WX)^-1 X'W y."""
    import numpy as np
    X = np.asarray(X, float); y = np.asarray(y, float); w = np.asarray(w, float)
    XtW = X.T * w
    return np.linalg.solve(XtW @ X, XtW @ y)


def hc3_se(X, y, beta, w=None):
    """HC3 robust standard errors. Unweighted:
        cov = (X'WX)^-1 [ Σ w_i x_i x_i' (r_i/(1-h_i))^2 ] (X'WX)^-1
    with w_i = 1 for OLS; leverages h_i from the (weighted) hat matrix."""
    import numpy as np
    X = np.asarray(X, float); y = np.asarray(y, float)
    n, k = X.shape
    w = np.ones(n) if w is None else np.asarray(w, float)
    XtW = X.T * w
    bread = np.linalg.inv(XtW @ X)
    resid = y - X @ beta
    h = np.clip(np.einsum("ij,jk,ik->i", X, bread, XtW.T) * w, None, 0.9999)
    adj = (resid / (1 - h)) ** 2
    meat = (X * (w * adj)[:, None]).T @ X
    cov = bread @ meat @ bread
    return np.sqrt(np.diag(cov))


def jackknife(theta_full, theta_deletes):
    """Delete-one jackknife SE, mean, and bias-corrected estimate."""
    import numpy as np
    d = np.asarray(theta_deletes, float); n = len(d); m = d.mean()
    se = math.sqrt((n - 1) / n * np.sum((d - m) ** 2))
    bias_corrected = n * theta_full - (n - 1) * m
    return {"mean": float(m), "se": se, "bias_corrected": float(bias_corrected)}


def nearest_rank_quantile(residuals, coverage):
    """Finite-sample conformal threshold: the ceil((n+1)*coverage)-th smallest abs resid."""
    r = sorted(abs(x) for x in residuals)
    n = len(r)
    rank = math.ceil((n + 1) * coverage)
    return r[min(rank, n) - 1], rank


def plus_one_p_value(observed_abs_t, boot_abs_t):
    """(1 + #{|t*| >= |t_obs|}) / (B + 1)."""
    exceed = sum(1 for t in boot_abs_t if t >= observed_abs_t)
    return exceed, (1 + exceed) / (len(boot_abs_t) + 1)


# ----------------------------------------------------------------------------- #
# 4. PCA, deterministic k-means, adjusted Rand index                             #
# ----------------------------------------------------------------------------- #
def covariance_pca(X, standardize=False, ddof=1, sign_fix=True):
    """Center (optionally standardize), eigendecompose covariance. Returns
    (eigenvalues desc, eigenvectors as columns, scores)."""
    import numpy as np
    X = np.asarray(X, float)
    mu = X.mean(0); Z = X - mu
    if standardize:
        Z = Z / X.std(0, ddof=0)
    C = np.cov(Z, rowvar=False, ddof=ddof)
    w, V = np.linalg.eigh(C)
    idx = np.argsort(w)[::-1]; w = w[idx]; V = V[:, idx]
    if sign_fix:
        for j in range(V.shape[1]):
            if V[np.argmax(np.abs(V[:, j])), j] < 0:
                V[:, j] = -V[:, j]
    return w, V, Z @ V


def kmeans_deterministic(P, k, max_iter=100):
    """Farthest-first init (start from point farthest from mean) + Lloyd updates.
    Returns (labels, centroids, initial_indices). Deterministic given P."""
    import numpy as np
    P = np.asarray(P, float); n = len(P)
    mean = P.mean(0)
    init = [int(np.argmax(((P - mean) ** 2).sum(1)))]
    for _ in range(k - 1):
        d = np.min([((P - P[c]) ** 2).sum(1) for c in init], axis=0)
        init.append(int(np.argmax(d)))
    C = P[init].copy(); labels = np.full(n, -1)
    for _ in range(max_iter):
        new = np.argmin(((P[:, None, :] - C[None, :, :]) ** 2).sum(2), axis=1)
        if (new == labels).all():
            break
        labels = new
        for j in range(k):
            if (labels == j).any():
                C[j] = P[labels == j].mean(0)
    return labels, C, init


def adjusted_rand_index(a, b):
    """ARI between two label assignments."""
    ab = defaultdict(int); A = defaultdict(int); B = defaultdict(int)
    for x, y in zip(a, b):
        ab[(x, y)] += 1; A[x] += 1; B[y] += 1
    comb2 = lambda m: m * (m - 1) // 2
    sum_ab = sum(comb2(v) for v in ab.values())
    sa = sum(comb2(v) for v in A.values()); sb = sum(comb2(v) for v in B.values())
    n = len(a); tot = comb2(n)
    if tot == 0:
        return 1.0
    exp = sa * sb / tot; mx = (sa + sb) / 2
    return 1.0 if mx == exp else (sum_ab - exp) / (mx - exp)


def aligned_agreement(labels_full, labels_alt, k):
    """Fraction of items keeping the same cluster under the best label permutation."""
    best = 0
    for perm in itertools.permutations(range(k)):
        best = max(best, sum(1 for a, b in zip(labels_full, labels_alt)
                             if perm[a] == b))
    return best / len(labels_full)


# ----------------------------------------------------------------------------- #
# 5. Exact Shapley over a small swap set                                         #
# ----------------------------------------------------------------------------- #
def exact_shapley(members, coef_of_subset):
    """Exact Shapley values for M members. coef_of_subset(frozenset)->float refits the
    target coefficient with exactly that subset swapped. Sum of Shapley values equals
    coef(all) - coef(none)."""
    M = len(members); phi = {m: 0.0 for m in members}
    fact = math.factorial
    for m in members:
        others = [x for x in members if x != m]
        for r in range(len(others) + 1):
            weight = fact(r) * fact(M - r - 1) / fact(M)
            for combo in itertools.combinations(others, r):
                S = frozenset(combo)
                phi[m] += weight * (coef_of_subset(S | {m}) - coef_of_subset(S))
    return phi
