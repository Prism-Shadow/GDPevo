#!/usr/bin/env python3
"""Reusable deterministic helpers for Public Health Observatory audit tasks.

The module intentionally contains no task-local values. Bind all variables,
orders, grids, seeds, and thresholds from the active analysis_request.json.
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from itertools import permutations
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover - callers can still use PRNG/quantile helpers.
    np = None


def require_numpy():
    if np is None:
        raise RuntimeError("This helper needs numpy for linear algebra.")
    return np


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def sort_key_text(value: Any) -> str:
    return "" if value is None else str(value)


def rounded_tree(value: Any, places: int) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        out = round(value, places)
        if out == 0 and not math.copysign(1.0, out) < 0:
            return 0.0
        return out
    if isinstance(value, list):
        return [rounded_tree(v, places) for v in value]
    if isinstance(value, dict):
        return {k: rounded_tree(v, places) for k, v in value.items()}
    return value


def select_latest_record(
    rows: Iterable[Mapping[str, Any]],
    key_fields: Sequence[str],
    priority: Sequence[Tuple[str, str]],
) -> Dict[Tuple[Any, ...], Mapping[str, Any]]:
    """Select one record per key using priority like [('revision','max'), ('released_at','max')]."""
    selected: Dict[Tuple[Any, ...], Mapping[str, Any]] = {}

    def norm(row: Mapping[str, Any], field: str) -> Any:
        val = row.get(field)
        num = parse_number(val)
        return num if num is not None else sort_key_text(val)

    def better(new: Mapping[str, Any], old: Mapping[str, Any]) -> bool:
        for field, direction in priority:
            a, b = norm(new, field), norm(old, field)
            if a == b:
                continue
            return a > b if direction == "max" else a < b
        return False

    for row in rows:
        key = tuple(row.get(k) for k in key_fields)
        if key not in selected or better(row, selected[key]):
            selected[key] = row
    return selected


def finite(value: Any) -> bool:
    x = parse_number(value)
    return x is not None and math.isfinite(x)


def valid_observation(row: Mapping[str, Any], value_field: str = "value") -> bool:
    if str(row.get("suppression_flag", "0")).strip() in {"1", "true", "True"}:
        return False
    q = str(row.get("quality_flag", "") or "").upper()
    if q in {"INVALID", "INVALID_SCALE", "WITHDRAWN"}:
        return False
    return finite(row.get(value_field))


def design_matrix(records: Sequence[Mapping[str, Any]], columns: Sequence[str], intercept: bool = False):
    npx = require_numpy()
    data = []
    for row in records:
        vals = [1.0] if intercept else []
        vals.extend(float(row[c]) for c in columns)
        data.append(vals)
    return npx.asarray(data, dtype=float)


def solve_linear(a, b, rcond: float = 1e-12):
    npx = require_numpy()
    a = npx.asarray(a, dtype=float)
    b = npx.asarray(b, dtype=float)
    try:
        return npx.linalg.solve(a, b)
    except npx.linalg.LinAlgError:
        return npx.linalg.pinv(a, rcond=rcond) @ b


def ols_fit(x, y, rcond: float = 1e-12):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    y = npx.asarray(y, dtype=float)
    beta = solve_linear(x.T @ x, x.T @ y, rcond=rcond)
    fitted = x @ beta
    resid = y - fitted
    return {"coef": beta, "fitted": fitted, "resid": resid}


def wls_fit(x, y, w, rcond: float = 1e-12):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    y = npx.asarray(y, dtype=float)
    w = npx.asarray(w, dtype=float)
    sw = npx.sqrt(w)
    xw = x * sw[:, None]
    beta = solve_linear(xw.T @ xw, xw.T @ (y * sw), rcond=rcond)
    fitted = x @ beta
    return {"coef": beta, "fitted": fitted, "resid": y - fitted}


def fitted_resid(x, y, beta):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    y = npx.asarray(y, dtype=float)
    beta = npx.asarray(beta, dtype=float)
    fitted = x @ beta
    return fitted, y - fitted


def hc3_cov(x, y, beta, weights=None, rcond: float = 1e-12):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    y = npx.asarray(y, dtype=float)
    beta = npx.asarray(beta, dtype=float)
    if weights is None:
        xw = x
        ew = y - x @ beta
    else:
        w = npx.asarray(weights, dtype=float)
        sw = npx.sqrt(w)
        xw = x * sw[:, None]
        ew = sw * (y - x @ beta)
    xtx_inv = npx.linalg.pinv(xw.T @ xw, rcond=rcond)
    h = npx.sum((xw @ xtx_inv) * xw, axis=1)
    meat = xw.T @ ((ew * ew / ((1.0 - h) ** 2))[:, None] * xw)
    return xtx_inv @ meat @ xtx_inv


def cr1_cov(x, y, beta, clusters: Sequence[Any], weights=None, rcond: float = 1e-12):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    y = npx.asarray(y, dtype=float)
    beta = npx.asarray(beta, dtype=float)
    if weights is None:
        xw = x
        ew = y - x @ beta
    else:
        w = npx.asarray(weights, dtype=float)
        sw = npx.sqrt(w)
        xw = x * sw[:, None]
        ew = sw * (y - x @ beta)
    n, k = xw.shape
    groups = list(dict.fromkeys(clusters))
    g_count = len(groups)
    xtx_inv = npx.linalg.pinv(xw.T @ xw, rcond=rcond)
    meat = npx.zeros((k, k), dtype=float)
    for g in groups:
        idx = [i for i, c in enumerate(clusters) if c == g]
        score = xw[idx].T @ ew[idx]
        meat += npx.outer(score, score)
    factor = (g_count / (g_count - 1.0)) * ((n - 1.0) / (n - k))
    return factor * (xtx_inv @ meat @ xtx_inv)


def student_t_two_sided(t_stat: float, df: int) -> float:
    t = abs(float(t_stat))
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    return min(1.0, max(0.0, _regularized_beta(0.5 * df, 0.5, x)))


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    log_bt += a * math.log(x) + b * math.log1p(-x)
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _beta_cf(a, b, x) / a
    return 1.0 - bt * _beta_cf(b, a, 1.0 - x) / b


def _beta_cf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 3e-14) -> float:
    tiny = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def double_demean(records: Sequence[Mapping[str, Any]], entity_key: str, time_key: str, columns: Sequence[str]):
    """Return double-demeaned rows for columns in original record order."""
    out = []
    grand = {c: sum(float(r[c]) for r in records) / len(records) for c in columns}
    by_entity: Dict[Any, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    by_time: Dict[Any, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        for c in columns:
            by_entity[r[entity_key]][c].append(float(r[c]))
            by_time[r[time_key]][c].append(float(r[c]))
    ent_mean = {g: {c: sum(v) / len(v) for c, v in cols.items()} for g, cols in by_entity.items()}
    time_mean = {t: {c: sum(v) / len(v) for c, v in cols.items()} for t, cols in by_time.items()}
    for r in records:
        out.append([float(r[c]) - ent_mean[r[entity_key]][c] - time_mean[r[time_key]][c] + grand[c] for c in columns])
    return require_numpy().asarray(out, dtype=float)


def jackknife_summary(full_coef: float, delete_coefs: Sequence[float]) -> Dict[str, float]:
    vals = [float(v) for v in delete_coefs]
    g = len(vals)
    bbar = sum(vals) / g
    se = math.sqrt((g - 1.0) / g * sum((v - bbar) ** 2 for v in vals))
    return {"delete_mean": bbar, "bias_corrected": g * full_coef - (g - 1.0) * bbar, "se": se}


def rmse(y, pred) -> float:
    npx = require_numpy()
    y = npx.asarray(y, dtype=float)
    pred = npx.asarray(pred, dtype=float)
    return float(npx.sqrt(npx.mean((y - pred) ** 2)))


def mae(y, pred) -> float:
    npx = require_numpy()
    return float(npx.mean(npx.abs(npx.asarray(y, dtype=float) - npx.asarray(pred, dtype=float))))


def r_squared(y, pred) -> float:
    npx = require_numpy()
    y = npx.asarray(y, dtype=float)
    pred = npx.asarray(pred, dtype=float)
    sse = float(npx.sum((y - pred) ** 2))
    sst = float(npx.sum((y - npx.mean(y)) ** 2))
    return 1.0 - sse / sst


def standardize_train(x, ddof: int = 1, weights=None, cols: Optional[Sequence[int]] = None):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    z = x.copy()
    cols = list(range(x.shape[1])) if cols is None else list(cols)
    mu = npx.zeros(x.shape[1], dtype=float)
    sigma = npx.ones(x.shape[1], dtype=float)
    if weights is None:
        for j in cols:
            mu[j] = float(npx.mean(x[:, j]))
            sigma[j] = float(npx.std(x[:, j], ddof=ddof))
            if sigma[j] == 0:
                sigma[j] = 1.0
            z[:, j] = (x[:, j] - mu[j]) / sigma[j]
    else:
        w = npx.asarray(weights, dtype=float)
        sw = float(npx.sum(w))
        for j in cols:
            mu[j] = float(npx.sum(w * x[:, j]) / sw)
            sigma[j] = float(npx.sqrt(npx.sum(w * (x[:, j] - mu[j]) ** 2) / sw))
            if sigma[j] == 0:
                sigma[j] = 1.0
            z[:, j] = (x[:, j] - mu[j]) / sigma[j]
    return z, mu, sigma


def apply_standardization(x, mu, sigma, cols: Optional[Sequence[int]] = None):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    z = x.copy()
    cols = list(range(x.shape[1])) if cols is None else list(cols)
    for j in cols:
        z[:, j] = (x[:, j] - mu[j]) / sigma[j]
    return z


def ridge_cd(z, y, lam: float, tol: float = 1e-10, max_sweeps: int = 10000):
    npx = require_numpy()
    z = npx.asarray(z, dtype=float)
    y = npx.asarray(y, dtype=float)
    yc = y - npx.mean(y)
    n, p = z.shape
    beta = npx.zeros(p, dtype=float)
    col_ss = npx.sum(z * z, axis=0)
    for sweep in range(1, max_sweeps + 1):
        max_change = 0.0
        for j in range(p):
            partial = yc - z @ beta + z[:, j] * beta[j]
            new_b = float(npx.sum(z[:, j] * partial) / (col_ss[j] + n * lam))
            max_change = max(max_change, abs(new_b - beta[j]))
            beta[j] = new_b
        if max_change < tol:
            return beta, sweep
    return beta, max_sweeps


def soft_threshold(a: float, t: float) -> float:
    if a > t:
        return a - t
    if a < -t:
        return a + t
    return 0.0


def elastic_net_cd(
    z,
    y,
    lam: float,
    l1_ratio: float,
    weights=None,
    tol: float = 1e-10,
    max_cycles: int = 10000,
    update_intercept: bool = True,
):
    npx = require_numpy()
    z = npx.asarray(z, dtype=float)
    y = npx.asarray(y, dtype=float)
    n, p = z.shape
    if weights is None:
        w = npx.ones(n, dtype=float)
    else:
        w = npx.asarray(weights, dtype=float)
    wsum = float(npx.sum(w))
    intercept = float(npx.sum(w * y) / wsum)
    beta = npx.zeros(p, dtype=float)
    for cycle in range(1, max_cycles + 1):
        max_change = 0.0
        if update_intercept:
            resid = y - intercept - z @ beta
            delta_a = float(npx.sum(w * resid) / wsum)
            intercept += delta_a
            max_change = max(max_change, abs(delta_a))
        for j in range(p):
            partial = y - intercept - z @ beta + z[:, j] * beta[j]
            rho = float(npx.sum(w * z[:, j] * partial) / wsum)
            denom = float(npx.sum(w * z[:, j] * z[:, j]) / wsum + lam * (1.0 - l1_ratio))
            new_b = soft_threshold(rho, lam * l1_ratio) / denom
            max_change = max(max_change, abs(new_b - beta[j]))
            beta[j] = new_b
        if max_change < tol:
            return intercept, beta, cycle
    return intercept, beta, max_cycles


def xorshift32_next(state: int) -> int:
    x = state & 0xFFFFFFFF
    x ^= (x << 13) & 0xFFFFFFFF
    x &= 0xFFFFFFFF
    x ^= (x >> 17) & 0xFFFFFFFF
    x &= 0xFFFFFFFF
    x ^= (x << 5) & 0xFFFFFFFF
    return x & 0xFFFFFFFF


def xorshift32_sign(state: int) -> Tuple[int, int]:
    state = xorshift32_next(state)
    return state, (1 if state & 1 else -1)


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((int(stream) << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.random_u32()
        self.state = (self.state + int(seed)) & 0xFFFFFFFFFFFFFFFF
        self.random_u32()

    def random_u32(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF

    def bounded(self, n: int) -> int:
        return self.random_u32() % n


WEBB_WEIGHTS = [
    -math.sqrt(1.5),
    -1.0,
    -math.sqrt(0.5),
    math.sqrt(0.5),
    1.0,
    math.sqrt(1.5),
]


def pcg32_webb_indices(seed: int, stream: int, replicate_count: int, cluster_count: int) -> List[List[int]]:
    rng = PCG32(seed, stream)
    return [[rng.bounded(6) for _ in range(cluster_count)] for _ in range(replicate_count)]


def nearest_rank(values: Sequence[float], p: float) -> float:
    xs = sorted(float(v) for v in values)
    if not xs:
        return float("nan")
    rank = min(len(xs), int(math.ceil(p * len(xs))))
    return xs[max(0, rank - 1)]


def type7_quantile(values: Sequence[float], p: float) -> float:
    xs = sorted(float(v) for v in values)
    if not xs:
        return float("nan")
    if len(xs) == 1:
        return xs[0]
    h = (len(xs) - 1) * p
    j = int(math.floor(h))
    gamma = h - j
    if j + 1 >= len(xs):
        return xs[-1]
    return (1.0 - gamma) * xs[j] + gamma * xs[j + 1]


def conformal_radius(abs_residuals: Sequence[float], coverage: float) -> Tuple[int, float]:
    scores = sorted(float(v) for v in abs_residuals)
    m = len(scores)
    rank = min(m, int(math.ceil((m + 1) * coverage)))
    return rank, scores[rank - 1]


def pca_covariance(x, ddof: int = 1):
    npx = require_numpy()
    x = npx.asarray(x, dtype=float)
    mu = npx.mean(x, axis=0)
    sd = npx.std(x, axis=0, ddof=ddof)
    sd[sd == 0] = 1.0
    z = (x - mu) / sd
    denom = x.shape[0] - ddof
    cov = (z.T @ z) / denom
    eigvals, eigvecs = npx.linalg.eigh(cov)
    order = npx.argsort(-eigvals)
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    for j in range(eigvecs.shape[1]):
        col = eigvecs[:, j]
        idx = int(npx.where(npx.abs(col) == npx.max(npx.abs(col)))[0][0])
        if col[idx] < 0:
            eigvecs[:, j] = -col
    scores = z @ eigvecs
    ratios = eigvals / npx.sum(eigvals)
    return {"z": z, "mean": mu, "sd": sd, "eigenvalues": eigvals, "loadings": eigvecs, "scores": scores, "explained": ratios}


def kmeans_farthest_first(points, ids: Sequence[Any], k: int, max_iter: int = 100, canonicalize: bool = False):
    npx = require_numpy()
    pts = npx.asarray(points, dtype=float)
    ids = list(ids)
    n = len(ids)
    centers_idx = [min(range(n), key=lambda i: sort_key_text(ids[i]))]
    while len(centers_idx) < k:
        best = None
        for i in range(n):
            if i in centers_idx:
                continue
            d = min(float(npx.sum((pts[i] - pts[c]) ** 2)) for c in centers_idx)
            cand = (d, sort_key_text(ids[i]), i)
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                best = cand
        if best is None:
            raise ValueError("cluster count cannot exceed number of distinct center candidates")
        centers_idx.append(best[2])
    centers = pts[centers_idx].copy()
    labels = npx.full(n, -1, dtype=int)
    updates = 0
    for _ in range(max_iter):
        new_labels = npx.zeros(n, dtype=int)
        for i in range(n):
            dists = [float(npx.sum((pts[i] - c) ** 2)) for c in centers]
            new_labels[i] = min(range(k), key=lambda j: (dists[j], j))
        if npx.array_equal(new_labels, labels):
            break
        labels = new_labels
        updates += 1
        for j in range(k):
            members = pts[labels == j]
            if len(members):
                centers[j] = npx.mean(members, axis=0)
    if canonicalize:
        order = sorted(range(k), key=lambda j: tuple(float(v) for v in centers[j]) + (j,))
        remap = {old: new for new, old in enumerate(order)}
        centers = centers[order]
        labels = npx.asarray([remap[int(v)] for v in labels], dtype=int)
    return {"centers": centers, "labels": labels + 1, "initial_ids": [ids[i] for i in centers_idx], "updates": updates}


def adjusted_rand_index(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    pairs = list(zip(labels_a, labels_b))
    n = len(pairs)
    if n < 2:
        return 1.0
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    cab = Counter(pairs)

    def comb2(x: int) -> int:
        return x * (x - 1) // 2

    sum_ij = sum(comb2(v) for v in cab.values())
    sum_a = sum(comb2(v) for v in ca.values())
    sum_b = sum(comb2(v) for v in cb.values())
    total = comb2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    if denom == 0:
        return 1.0 if labels_a == labels_b else 0.0
    return (sum_ij - expected) / denom


def align_labels(reference: Sequence[int], candidate: Sequence[int]) -> Tuple[List[int], float]:
    ref = list(reference)
    cand = list(candidate)
    labels = sorted(set(cand))
    target = sorted(set(ref))
    best = None
    for perm in permutations(target, len(labels)):
        mapping = dict(zip(labels, perm))
        aligned = [mapping[v] for v in cand]
        matches = sum(1 for a, b in zip(ref, aligned) if a == b)
        key = (matches, tuple(aligned))
        if best is None or key[0] > best[0] or (key[0] == best[0] and key[1] < best[1]):
            best = (matches, tuple(aligned))
    return list(best[1]), best[0] / len(ref)


def silhouette_mean(points, labels: Sequence[Any]) -> float:
    npx = require_numpy()
    pts = npx.asarray(points, dtype=float)
    labels = list(labels)
    n = len(labels)
    dmat = npx.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2))
    out = []
    for i, lab in enumerate(labels):
        same = [j for j, v in enumerate(labels) if v == lab and j != i]
        if not same:
            out.append(0.0)
            continue
        a = float(npx.mean(dmat[i, same]))
        b = min(float(npx.mean(dmat[i, [j for j, v in enumerate(labels) if v == other]])) for other in set(labels) if other != lab)
        out.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return float(npx.mean(out))


def state_blocked_folds(count_by_state: Mapping[str, int], fold_count: int) -> List[List[str]]:
    loads = [0] * fold_count
    folds: List[List[str]] = [[] for _ in range(fold_count)]
    for state, count in sorted(count_by_state.items(), key=lambda kv: (-kv[1], kv[0])):
        j = min(range(fold_count), key=lambda idx: (loads[idx], idx))
        folds[j].append(state)
        loads[j] += int(count)
    return [sorted(f) for f in folds]


def shapley_values(mask_to_value: Mapping[int, float], m: int) -> List[float]:
    fact = math.factorial
    denom = fact(m)
    phi = [0.0] * m
    for j in range(m):
        bit = 1 << j
        acc = 0.0
        for mask, value in mask_to_value.items():
            if mask & bit:
                continue
            size = int(mask).bit_count()
            weight = fact(size) * fact(m - size - 1) / denom
            acc += weight * (mask_to_value[mask | bit] - value)
        phi[j] = acc
    return phi


def decision_first_failed(flags: Mapping[str, bool], precedence: Sequence[str], pass_value: str, fail_prefix: str) -> Dict[str, str]:
    for key in precedence:
        if not flags[key]:
            return {"first_failed_module": key, "conclusion": f"{fail_prefix}{key}"}
    return {"first_failed_module": "NONE", "conclusion": pass_value}
