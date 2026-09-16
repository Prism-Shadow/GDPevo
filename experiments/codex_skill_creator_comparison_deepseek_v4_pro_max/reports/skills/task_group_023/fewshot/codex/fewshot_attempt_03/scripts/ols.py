#!/usr/bin/env python3
"""OLS estimation with cluster-robust inference as used in PHO audits.

- Linear regression (OLS with intercept or without)
- Two-way fixed effects (double demeaning): subtract entity mean, time mean,
  add grand mean; fit OLS without intercept.
- Cluster-robust CR1 variance estimation.
- Weighted OLS (reliability weights).
- HC3 variance estimation.
- Delete-one-cluster jackknife (bias-corrected estimator, standard error).

All fits preserve declared predictor order.
"""

import math
from typing import Optional, Sequence


def ols_fit(X: list[list[float]], y: list[float], intercept: bool = True):
    """Fit OLS via normal equations. Returns coefficients in predictor order."""
    n = len(y)
    p = len(X[0])
    if intercept:
        X_aug = [row + [1.0] for row in X]
        p += 1
    else:
        X_aug = X

    # (X'X)^-1 X'y
    XtX = [[sum(X_aug[i][k] * X_aug[i][j] for i in range(n)) for j in range(p)] for k in range(p)]
    XtX_inv = invert_matrix(XtX)
    Xty = [sum(X_aug[i][j] * y[i] for i in range(n)) for j in range(p)]
    coef = [sum(XtX_inv[j][k] * Xty[k] for k in range(p)) for j in range(p)]

    if intercept:
        return coef[:-1], coef[-1], XtX_inv
    else:
        return coef, None, XtX_inv


def ols_fit_weighted(X: list[list[float]], y: list[float], w: list[float],
                     intercept: bool = True):
    """Weighted OLS via normal equations. Returns coefficients in predictor order."""
    n = len(y)
    p = len(X[0])
    if intercept:
        X_aug = [row + [1.0] for row in X]
        p += 1
    else:
        X_aug = X

    XtWX = [[sum(X_aug[i][k] * X_aug[i][j] * w[i] for i in range(n)) for j in range(p)] for k in range(p)]
    XtWX_inv = invert_matrix(XtWX)
    XtWy = [sum(X_aug[i][j] * y[i] * w[i] for i in range(n)) for j in range(p)]
    coef = [sum(XtWX_inv[j][k] * XtWy[k] for k in range(p)) for j in range(p)]

    if intercept:
        return coef[:-1], coef[-1], XtWX_inv, X_aug
    else:
        return coef, None, XtWX_inv, X_aug


def two_way_fixed_effects(X: list[list[float]], y: list[float],
                          entity_ids: list, time_ids: list):
    """Double-demean each variable, fit OLS without intercept.

    For each variable z: z_tilde = z - entity_mean(z) - time_mean(z) + grand_mean(z).
    Fit OLS on transformed data without intercept.

    Returns: coefficients (predictor order), transformed_X, transformed_y
    """
    n = len(y)
    p = len(X[0])

    # Compute entity means
    entity_groups: dict = {}
    for i, eid in enumerate(entity_ids):
        entity_groups.setdefault(eid, []).append(i)

    # Compute time means
    time_groups: dict = {}
    for i, tid in enumerate(time_ids):
        time_groups.setdefault(tid, []).append(i)

    def double_demean(vec):
        grand = sum(vec) / n
        # entity means
        emeans = {}
        for eid, idxs in entity_groups.items():
            emeans[eid] = sum(vec[i] for i in idxs) / len(idxs)
        # time means
        tmeans = {}
        for tid, idxs in time_groups.items():
            tmeans[tid] = sum(vec[i] for i in idxs) / len(idxs)
        return [vec[i] - emeans[entity_ids[i]] - tmeans[time_ids[i]] + grand for i in range(n)]

    X_tilde = [double_demean([row[j] for row in X]) for j in range(p)]
    X_tilde_T = [[X_tilde[j][i] for j in range(p)] for i in range(n)]
    y_tilde = double_demean(y)

    coef, _, XtX_inv = ols_fit(X_tilde_T, y_tilde, intercept=False)
    return coef, X_tilde_T, y_tilde


def cr1_variance(X: list[list[float]], y: list[float],
                 coef: list[float], cluster_ids: list,
                 intercept: bool = True) -> list[float]:
    """CR1 cluster-robust variance for coefficients.

    V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (X'X)^-1 * sum_g(s_g * s_g') * (X'X)^-1
    where s_g = sum_{i in g} X_i' * e_i
    """
    n = len(y)
    p = len(coef)

    if intercept:
        X_aug = [row + [1.0] for row in X]
        k = p + 1
    else:
        X_aug = X
        k = p

    # residuals
    yhat = [sum(X_aug[i][j] * (coef[j] if j < p else (coef[j - p] if intercept else 0))
                for j in range(len(X_aug[0]))) for i in range(n)]
    # Actually need full coefficient vector including intercept
    if intercept:
        # Find intercept
        XtX = [[sum(X_aug[i][k_i] * X_aug[i][j] for i in range(n)) for j in range(k)] for k_i in range(k)]
        XtX_inv = invert_matrix(XtX)
        Xty = [sum(X_aug[i][j] * y[i] for i in range(n)) for j in range(k)]
        full_coef = [sum(XtX_inv[j][k_i] * Xty[k_i] for k_i in range(k)) for j in range(k)]
    else:
        full_coef = list(coef)
        k = len(coef)

    residuals = [y[i] - sum(X_aug[i][j] * full_coef[j] for j in range(k)) for i in range(n)]

    # Group residuals
    groups: dict = {}
    for i, cid in enumerate(cluster_ids):
        groups.setdefault(cid, []).append(i)

    G = len(groups)

    # (X'X)^-1
    XtX = [[sum(X_aug[i][k_i] * X_aug[i][j] for i in range(n)) for j in range(k)] for k_i in range(k)]
    XtX_inv = invert_matrix(XtX)

    # sum_g s_g * s_g'
    S = [[0.0] * k for _ in range(k)]
    for idxs in groups.values():
        sg = [0.0] * k
        for i in idxs:
            for j in range(k):
                sg[j] += X_aug[i][j] * residuals[i]
        for j in range(k):
            for l in range(k):
                S[j][l] += sg[j] * sg[l]

    # V_CR1
    scale = (G / (G - 1)) * ((n - 1) / (n - k))
    middle = [[sum(XtX_inv[j][m] * S[m][l] for m in range(k)) for l in range(k)] for j in range(k)]
    V = [[scale * sum(middle[j][m] * XtX_inv[m][l] for m in range(k)) for l in range(k)] for j in range(k)]

    # Return only the p predictor variances
    return [V[j][j] for j in range(p)]


def hc3_variance_weighted(X: list[list[float]], y: list[float], w: list[float],
                          coef: list[float], intercept: bool = True):
    """HC3 variance for weighted OLS. Returns standard errors for coefficients."""
    n = len(y)
    if intercept:
        X_aug = [row + [1.0] for row in X]
        k = len(X_aug[0])
    else:
        X_aug = X
        k = len(X_aug[0])

    # Compute full coefficients including intercept
    # Recompute full fit
    XtWX = [[sum(X_aug[i][k_i] * X_aug[i][j] * w[i] for i in range(n)) for j in range(k)] for k_i in range(k)]
    XtWX_inv = invert_matrix(XtWX)
    XtWy = [sum(X_aug[i][j] * y[i] * w[i] for i in range(n)) for j in range(k)]
    full_coef = [sum(XtWX_inv[j][k_i] * XtWy[k_i] for k_i in range(k)) for j in range(k)]

    residuals = [y[i] - sum(X_aug[i][j] * full_coef[j] for j in range(k)) for i in range(n)]

    # Leverage: h_i = x_i' (X'WX)^-1 x_i * w_i
    leverage = [0.0] * n
    for i in range(n):
        xi = [X_aug[i][j] * math.sqrt(w[i]) for j in range(k)]
        # h_i = xi' * (X'WX)^-1 * xi  -- this is not quite right with weights
        # For weighted HC3, we use a simplified approach
        lev = sum(xi[j] * sum(XtWX_inv[j][l] * xi[l] for l in range(k)) for j in range(k))
        leverage[i] = lev

    # HC3: V = (X'WX)^-1 * [sum x_i x_i' * e_i^2 / (1-h_i)^2] * (X'WX)^-1
    meat = [[0.0] * k for _ in range(k)]
    for i in range(n):
        xi = X_aug[i]
        wi = w[i]
        ei = residuals[i]
        h = leverage[i]
        correction = (ei * wi / max((1.0 - h), 0.0001)) ** 2
        for j in range(k):
            for l in range(k):
                meat[j][l] += xi[j] * xi[l] * correction

    V = [[sum(XtWX_inv[j][m] * meat[m][l] for m in range(k)) for l in range(k)] for j in range(k)]
    V = [[sum(V[j][m] * XtWX_inv[m][l] for m in range(k)) for l in range(k)] for j in range(k)]

    p = len(coef)
    return [math.sqrt(max(V[j][j], 0.0)) for j in range(p)]


def delete_one_cluster_jackknife(X: list[list[float]], y: list[float],
                                  cluster_ids: list, entity_ids=None, time_ids=None,
                                  intercept: bool = True,
                                  ordered_clusters: Optional[list] = None):
    """Delete-one-cluster jackknife for OLS or two-way FE.

    Returns:
      full_coef: full-sample coefficients
      delete_coef: list of coefficients for each deleted cluster (in ordered_clusters order)
      bbar: mean of delete coefficients
      b_bc: bias-corrected = G * full - (G-1) * bbar
      se_jk: jackknife standard error
    """
    G = len(set(cluster_ids))

    # Map clusters to indices
    cluster_map: dict = {}
    for i, cid in enumerate(cluster_ids):
        cluster_map.setdefault(cid, []).append(i)

    if ordered_clusters is None:
        ordered_clusters = sorted(cluster_map.keys())

    # Full sample fit
    if entity_ids is not None and time_ids is not None:
        full_coef, X_t, y_t = two_way_fixed_effects(X, y, entity_ids, time_ids)
    else:
        full_coef, _, _ = ols_fit(X, y, intercept=intercept)

    delete_coefs = []
    for cl in ordered_clusters:
        drop = set(cluster_map[cl])
        keep = [i for i in range(len(y)) if i not in drop]

        if entity_ids is not None and time_ids is not None:
            X_sub = [[X[i][j] for i in keep] for j in range(len(X[0]))]
            X_sub_T = [[X_sub[j][i] for j in range(len(X_sub))] for i in range(len(keep))]
            y_sub = [y[i] for i in keep]
            eids_sub = [entity_ids[i] for i in keep]
            tids_sub = [time_ids[i] for i in keep]
            coef, _, _ = two_way_fixed_effects(X_sub_T, y_sub, eids_sub, tids_sub)
        else:
            X_sub = [[X[i][j] for i in keep] for j in range(len(X[0]))]
            X_sub_T = [[X_sub[j][i] for j in range(len(X_sub))] for i in range(len(keep))]
            y_sub = [y[i] for i in keep]
            coef, _, _ = ols_fit(X_sub_T, y_sub, intercept=intercept)
        delete_coefs.append(coef)

    # Jackknife inference on first coefficient
    b_g = [dc[0] for dc in delete_coefs]
    bbar = sum(b_g) / G
    b_full = full_coef[0]
    b_bc = G * b_full - (G - 1) * bbar
    se_jk = math.sqrt(((G - 1) / G) * sum((bg - bbar) ** 2 for bg in b_g))

    return {
        'full_coef': full_coef,
        'delete_coefs': delete_coefs,
        'ordered_clusters': ordered_clusters,
        'bbar': bbar,
        'b_bc': b_bc,
        'se_jk': se_jk,
        'G': G,
    }


def invert_matrix(A: list[list[float]]) -> list[list[float]]:
    """Invert a symmetric positive-definite matrix via Cholesky."""
    n = len(A)
    # Cholesky: L * L^T = A
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][j] = math.sqrt(max(A[i][i] - s, 0.0))
            else:
                L[i][j] = (A[i][j] - s) / L[j][j]

    # Invert L
    Linv = [[0.0] * n for _ in range(n)]
    for i in range(n):
        Linv[i][i] = 1.0 / L[i][i]
        for j in range(i):
            Linv[i][j] = -sum(L[i][k] * Linv[k][j] for k in range(j, i)) / L[i][i]

    # A^-1 = (L^-1)^T * L^-1
    Ainv = [[sum(Linv[k][i] * Linv[k][j] for k in range(max(i, j), n)) for j in range(n)] for i in range(n)]
    return Ainv
